from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, confusion_matrix, normalized_mutual_info_score

from .utils import ensure_dir, save_json


DEFAULT_TEMPORAL_SHIFTS = (18, 144)


def _resolve_run_dir(raw_path: Any, root_dir: Path) -> Path:
    run_dir = Path(str(raw_path))
    if run_dir.is_absolute():
        return run_dir
    return root_dir / run_dir


def _parse_model_filter(models: Iterable[str] | str | None) -> set[str]:
    if models is None:
        return set()
    if isinstance(models, str):
        tokens = models.split(",")
    else:
        tokens = list(models)
    return {str(token).strip() for token in tokens if str(token).strip()}


def _load_valid_mask(metrics_dir: Path, regime: np.ndarray) -> np.ndarray:
    valid_path = metrics_dir / "regime_primary_valid.npy"
    if not valid_path.exists():
        return np.ones_like(regime, dtype=bool)
    return np.load(valid_path).astype(bool)


def _infer_num_classes(gate_prob: np.ndarray, regime: np.ndarray, valid: np.ndarray) -> int:
    valid_labels = np.asarray(regime[valid], dtype=np.int64)
    if valid_labels.size == 0:
        return min(1, int(gate_prob.shape[-1]))
    label_classes = int(valid_labels.max()) + 1
    return max(1, min(int(gate_prob.shape[-1]), label_classes))


def _gate_label(gate_prob: np.ndarray, num_classes: int) -> np.ndarray:
    supervised_gate = np.asarray(gate_prob[..., :num_classes], dtype=np.float64)
    return supervised_gate.argmax(axis=-1).astype(np.int16)


def _score_alignment(
    true_label: np.ndarray,
    gate_label: np.ndarray,
    valid: np.ndarray,
    num_classes: int,
) -> dict[str, Any]:
    valid = np.asarray(valid, dtype=bool) & (true_label >= 0) & (true_label < num_classes)
    flat_true = np.asarray(true_label[valid], dtype=np.int64)
    flat_pred = np.asarray(gate_label[valid], dtype=np.int64)
    labels = list(range(num_classes))
    conf = confusion_matrix(flat_true, flat_pred, labels=labels) if flat_true.size else np.zeros((num_classes, num_classes))
    return {
        "n_valid": int(flat_true.size),
        "nmi": float(normalized_mutual_info_score(flat_true, flat_pred)) if flat_true.size else float("nan"),
        "ari": float(adjusted_rand_score(flat_true, flat_pred)) if flat_true.size else float("nan"),
        "confusion_trace": int(np.trace(conf)),
        "confusion_total": int(conf.sum()),
    }


def _temporal_shift(label: np.ndarray, valid: np.ndarray, shift_steps: int) -> tuple[np.ndarray, np.ndarray]:
    shift_steps = int(shift_steps)
    shifted = np.roll(label, shift=shift_steps, axis=0)
    shifted_valid = np.roll(valid, shift=shift_steps, axis=0).astype(bool)
    if shift_steps > 0:
        shifted_valid[:shift_steps, :] = False
    elif shift_steps < 0:
        shifted_valid[shift_steps:, :] = False
    return shifted, shifted_valid


def _node_permutation(label: np.ndarray, valid: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    permutation = rng.permutation(label.shape[1])
    return label[:, permutation], valid[:, permutation]


def _within_time_shuffle(label: np.ndarray, valid: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    shuffled = np.array(label, copy=True)
    shuffled_valid = np.array(valid, copy=True)
    for row in range(label.shape[0]):
        permutation = rng.permutation(label.shape[1])
        shuffled[row] = label[row, permutation]
        shuffled_valid[row] = valid[row, permutation]
    return shuffled, shuffled_valid


def _global_label_shuffle(label: np.ndarray, valid: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    shuffled = np.array(label, copy=True)
    flat_label = shuffled.reshape(-1)
    flat_valid = valid.reshape(-1).astype(bool)
    positions = np.flatnonzero(flat_valid)
    if positions.size > 1:
        flat_label[positions] = rng.permutation(flat_label[positions])
    return shuffled, np.array(valid, copy=True)


def _control_labels(
    regime: np.ndarray,
    valid: np.ndarray,
    temporal_shifts: Iterable[int],
    rng: np.random.Generator,
) -> list[tuple[str, str, int | None, np.ndarray, np.ndarray]]:
    controls: list[tuple[str, str, int | None, np.ndarray, np.ndarray]] = [
        ("actual", "positive", None, regime, valid),
    ]
    for shift in temporal_shifts:
        shifted, shifted_valid = _temporal_shift(regime, valid, int(shift))
        controls.append((f"temporal_shift_{int(shift)}", "temporal_placebo", int(shift), shifted, shifted_valid))
    node_label, node_valid = _node_permutation(regime, valid, rng)
    controls.append(("node_permutation", "spatial_placebo", None, node_label, node_valid))
    within_label, within_valid = _within_time_shuffle(regime, valid, rng)
    controls.append(("within_time_shuffle", "spatial_placebo", None, within_label, within_valid))
    global_label, global_valid = _global_label_shuffle(regime, valid, rng)
    controls.append(("global_shuffle", "permutation_placebo", None, global_label, global_valid))
    return controls


def _audit_one_run(
    row: pd.Series,
    root_dir: Path,
    split: str,
    temporal_shifts: Iterable[int],
    rng: np.random.Generator,
) -> list[dict[str, Any]]:
    run_dir = _resolve_run_dir(row["run_dir"], root_dir)
    metrics_dir = run_dir / f"{split}_metrics"
    gate_path = metrics_dir / "gate_prob.npy"
    regime_path = metrics_dir / "regime_primary.npy"
    if not gate_path.exists() or not regime_path.exists():
        return []

    gate_prob = np.load(gate_path, mmap_mode="r")
    regime = np.load(regime_path)
    valid = _load_valid_mask(metrics_dir, regime)
    num_classes = _infer_num_classes(gate_prob, regime, valid)
    gate_label = _gate_label(gate_prob, num_classes)
    rows: list[dict[str, Any]] = []
    for condition, control_type, shift_steps, label, label_valid in _control_labels(regime, valid, temporal_shifts, rng):
        metrics = _score_alignment(label, gate_label, label_valid, num_classes)
        rows.append(
            {
                "dataset": row.get("dataset", ""),
                "model": row.get("model", ""),
                "seed": row.get("seed", ""),
                "variant_key": row.get("variant_key", ""),
                "experiment_group": row.get("experiment_group", ""),
                "run_dir": str(run_dir),
                "split": split,
                "condition": condition,
                "control_type": control_type,
                "shift_steps": shift_steps,
                "num_classes": num_classes,
                **metrics,
            }
        )
    return rows


def _summarize_raw(raw_df: pd.DataFrame) -> pd.DataFrame:
    metric_cols = ["nmi", "ari", "n_valid", "confusion_trace", "confusion_total"]
    rows: list[dict[str, Any]] = []
    if raw_df.empty:
        return pd.DataFrame()
    group_cols = ["dataset", "model", "condition", "control_type", "shift_steps"]
    for keys, group in raw_df.groupby(group_cols, dropna=False, sort=False):
        row = {column: value for column, value in zip(group_cols, keys)}
        row["n_runs"] = int(len(group))
        for metric in metric_cols:
            values = pd.to_numeric(group[metric], errors="coerce").dropna()
            row[f"{metric}_mean"] = float(values.mean()) if not values.empty else float("nan")
            row[f"{metric}_std"] = float(values.std(ddof=0)) if len(values) > 1 else 0.0
        rows.append(row)
    return pd.DataFrame(rows)


def _bootstrap_ci(values: np.ndarray, rng: np.random.Generator, samples: int) -> tuple[float, float, float]:
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return float("nan"), float("nan"), float("nan")
    if values.size == 1 or samples <= 0:
        mean = float(values.mean())
        return mean, mean, mean
    draws = rng.choice(values, size=(int(samples), values.size), replace=True).mean(axis=1)
    return float(values.mean()), float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))


def _paired_effects(raw_df: pd.DataFrame, bootstrap_samples: int, seed: int) -> pd.DataFrame:
    if raw_df.empty:
        return pd.DataFrame()
    actual = raw_df[raw_df["condition"] == "actual"].copy()
    controls = raw_df[raw_df["condition"] != "actual"].copy()
    if actual.empty or controls.empty:
        return pd.DataFrame()
    key_cols = ["dataset", "model", "run_dir"]
    merged = controls.merge(
        actual[key_cols + ["nmi", "ari"]],
        on=key_cols,
        how="inner",
        suffixes=("_control", "_actual"),
    )
    rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(seed)
    for keys, group in merged.groupby(["dataset", "model", "condition", "control_type", "shift_steps"], dropna=False, sort=False):
        dataset, model, condition, control_type, shift_steps = keys
        delta_nmi = pd.to_numeric(group["nmi_actual"], errors="coerce").to_numpy() - pd.to_numeric(
            group["nmi_control"], errors="coerce"
        ).to_numpy()
        delta_ari = pd.to_numeric(group["ari_actual"], errors="coerce").to_numpy() - pd.to_numeric(
            group["ari_control"], errors="coerce"
        ).to_numpy()
        nmi_mean, nmi_low, nmi_high = _bootstrap_ci(delta_nmi, rng, bootstrap_samples)
        ari_mean, ari_low, ari_high = _bootstrap_ci(delta_ari, rng, bootstrap_samples)
        rows.append(
            {
                "dataset": dataset,
                "model": model,
                "control_condition": condition,
                "control_type": control_type,
                "shift_steps": shift_steps,
                "n_runs": int(len(group)),
                "delta_nmi_mean": nmi_mean,
                "delta_nmi_ci_low": nmi_low,
                "delta_nmi_ci_high": nmi_high,
                "prob_actual_nmi_higher": float(np.mean(delta_nmi > 0.0)) if delta_nmi.size else float("nan"),
                "delta_ari_mean": ari_mean,
                "delta_ari_ci_low": ari_low,
                "delta_ari_ci_high": ari_high,
                "prob_actual_ari_higher": float(np.mean(delta_ari > 0.0)) if delta_ari.size else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def _write_report(summary_df: pd.DataFrame, effects_df: pd.DataFrame, output_path: Path) -> None:
    lines = [
        "# Routing placebo audit",
        "",
        "This audit compares gate-regime agreement against label controls that should not preserve the proposed physical boundary.",
        "",
    ]
    if summary_df.empty:
        lines.append("No gated runs were available for the requested audit.")
    else:
        actual = summary_df[summary_df["condition"] == "actual"].copy()
        lines.append("## Actual alignment")
        lines.append("")
        for _, row in actual.iterrows():
            lines.append(
                f"- {row['model']}: NMI {row['nmi_mean']:.4f} +/- {row['nmi_std']:.4f}; "
                f"ARI {row['ari_mean']:.4f} +/- {row['ari_std']:.4f}; n={int(row['n_runs'])}."
            )
        if not effects_df.empty:
            lines.extend(["", "## Placebo separation", ""])
            strongest = effects_df.sort_values(["model", "delta_nmi_mean"], ascending=[True, False])
            for _, row in strongest.iterrows():
                lines.append(
                    f"- {row['model']} vs {row['control_condition']}: "
                    f"Delta NMI {row['delta_nmi_mean']:.4f} "
                    f"[{row['delta_nmi_ci_low']:.4f}, {row['delta_nmi_ci_high']:.4f}]; "
                    f"Delta ARI {row['delta_ari_mean']:.4f} "
                    f"[{row['delta_ari_ci_low']:.4f}, {row['delta_ari_ci_high']:.4f}]."
                )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_routing_placebo_audit(
    run_table: Path | str,
    output_dir: Path | str,
    root_dir: Path | str = ".",
    split: str = "test",
    models: Iterable[str] | str | None = None,
    temporal_shifts: Iterable[int] = DEFAULT_TEMPORAL_SHIFTS,
    seed: int = 42,
    bootstrap_samples: int = 1000,
) -> Path:
    root_dir = Path(root_dir)
    output_dir = ensure_dir(output_dir)
    run_table = Path(run_table)
    df = pd.read_csv(run_table)
    if "run_dir" not in df.columns:
        raise ValueError("Routing placebo audit requires a run table with a run_dir column.")

    model_filter = _parse_model_filter(models)
    if model_filter and "model" in df.columns:
        df = df[df["model"].astype(str).isin(model_filter)].copy()

    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        rows.extend(_audit_one_run(row, root_dir, split, temporal_shifts, rng))

    raw_df = pd.DataFrame(rows)
    summary_df = _summarize_raw(raw_df)
    effects_df = _paired_effects(raw_df, bootstrap_samples=bootstrap_samples, seed=seed + 1)

    raw_path = output_dir / "routing_placebo_raw.csv"
    summary_path = output_dir / "routing_placebo_summary.csv"
    effects_path = output_dir / "routing_placebo_effects.csv"
    raw_df.to_csv(raw_path, index=False)
    summary_df.to_csv(summary_path, index=False)
    effects_df.to_csv(effects_path, index=False)
    save_json(
        output_dir / "routing_placebo_config.json",
        {
            "run_table": str(run_table),
            "root_dir": str(root_dir),
            "split": split,
            "models": sorted(model_filter),
            "temporal_shifts": [int(shift) for shift in temporal_shifts],
            "seed": int(seed),
            "bootstrap_samples": int(bootstrap_samples),
            "n_raw_rows": int(len(raw_df)),
            "n_summary_rows": int(len(summary_df)),
        },
    )
    _write_report(summary_df, effects_df, output_dir / "routing_placebo_report.md")
    return output_dir
