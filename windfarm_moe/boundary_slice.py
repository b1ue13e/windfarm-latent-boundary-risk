from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, confusion_matrix, normalized_mutual_info_score

from .utils import ensure_dir, load_json, save_json


BOUNDARY_SLICE_NAMES = ("boundary_band", "nonboundary_valid", "mppt_core", "pitch_core")


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


def _masked_metrics(pred: np.ndarray, target: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    weight = np.asarray(mask, dtype=np.float64)
    safe_pred = np.nan_to_num(np.asarray(pred, dtype=np.float64), nan=0.0)
    safe_target = np.nan_to_num(np.asarray(target, dtype=np.float64), nan=0.0)
    denom = max(float(weight.sum()), 1.0)
    mae = (np.abs(safe_pred - safe_target) * weight).sum() / denom
    rmse = np.sqrt((((safe_pred - safe_target) ** 2) * weight).sum() / denom)
    return {"mae": float(mae), "rmse": float(rmse)}


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


def _gate_alignment(gate_prob: np.ndarray | None, regime: np.ndarray, valid: np.ndarray) -> dict[str, Any]:
    if gate_prob is None:
        return {
            "n_valid_gate": 0,
            "n_true_classes": 0,
            "nmi": float("nan"),
            "ari": float("nan"),
            "confusion_trace": 0,
            "confusion_total": 0,
        }
    num_classes = _infer_num_classes(gate_prob, regime, valid)
    gate_label = np.asarray(gate_prob[..., :num_classes]).argmax(axis=-1)
    valid = np.asarray(valid, dtype=bool) & (regime >= 0) & (regime < num_classes)
    flat_true = np.asarray(regime[valid], dtype=np.int64)
    flat_pred = np.asarray(gate_label[valid], dtype=np.int64)
    labels = list(range(num_classes))
    conf = confusion_matrix(flat_true, flat_pred, labels=labels) if flat_true.size else np.zeros((num_classes, num_classes))
    n_true_classes = int(np.unique(flat_true).size) if flat_true.size else 0
    return {
        "n_valid_gate": int(flat_true.size),
        "n_true_classes": n_true_classes,
        "nmi": float(normalized_mutual_info_score(flat_true, flat_pred)) if n_true_classes >= 2 else float("nan"),
        "ari": float(adjusted_rand_score(flat_true, flat_pred)) if n_true_classes >= 2 else float("nan"),
        "confusion_trace": int(np.trace(conf)),
        "confusion_total": int(conf.sum()),
    }


def _load_cache_physics(cache_dir: Path) -> tuple[np.ndarray, dict[str, Any], int, int]:
    metadata = load_json(cache_dir / "metadata.json")
    physics = np.load(cache_dir / "physics.npy", mmap_mode="r")
    physics_names = list(metadata.get("physics_names", []))
    wspd_idx = physics_names.index("Wspd") if "Wspd" in physics_names else 0
    pab_idx = physics_names.index("Pab_mean") if "Pab_mean" in physics_names else 1
    return physics, metadata, wspd_idx, pab_idx


def _slice_masks(
    wspd: np.ndarray,
    pab: np.ndarray,
    regime: np.ndarray,
    valid: np.ndarray,
    rated_wind: float,
    pitch_threshold: float,
    boundary_band: float,
    core_margin: float,
) -> dict[str, np.ndarray]:
    observed = np.isfinite(wspd) & np.isfinite(pab)
    valid = np.asarray(valid, dtype=bool) & observed
    mppt_or_pitch = valid & np.isin(regime, [1, 2])
    boundary = mppt_or_pitch & (np.abs(wspd - float(rated_wind)) <= float(boundary_band))
    return {
        "boundary_band": boundary,
        "nonboundary_valid": mppt_or_pitch & ~boundary,
        "mppt_core": valid & (regime == 1) & (wspd <= float(rated_wind) - float(core_margin)) & (pab < float(pitch_threshold)),
        "pitch_core": valid & (regime == 2) & (wspd >= float(rated_wind) + float(core_margin)) & (pab >= float(pitch_threshold)),
    }


def _audit_one_run(
    row: pd.Series,
    root_dir: Path,
    cache_physics: np.ndarray,
    cache_metadata: dict[str, Any],
    wspd_idx: int,
    pab_idx: int,
    split: str,
    rated_wind: float,
    pitch_threshold: float,
    boundary_band: float,
    core_margin: float,
) -> list[dict[str, Any]]:
    run_dir = _resolve_run_dir(row["run_dir"], root_dir)
    metrics_dir = run_dir / f"{split}_metrics"
    required = ["pred.npy", "target.npy", "mask.npy", "regime_primary.npy", "anchor_index.npy"]
    if any(not (metrics_dir / name).exists() for name in required):
        return []

    pred = np.load(metrics_dir / "pred.npy", mmap_mode="r")
    target = np.load(metrics_dir / "target.npy", mmap_mode="r")
    mask = np.load(metrics_dir / "mask.npy", mmap_mode="r")
    regime = np.load(metrics_dir / "regime_primary.npy")
    valid = _load_valid_mask(metrics_dir, regime)
    anchor_index = np.load(metrics_dir / "anchor_index.npy")
    gate_path = metrics_dir / "gate_prob.npy"
    gate_prob = np.load(gate_path, mmap_mode="r") if gate_path.exists() else None

    physics = np.asarray(cache_physics[np.asarray(anchor_index, dtype=np.int64)])
    wspd = np.asarray(physics[..., wspd_idx], dtype=np.float64)
    pab = np.asarray(physics[..., pab_idx], dtype=np.float64)
    masks = _slice_masks(wspd, pab, regime, valid, rated_wind, pitch_threshold, boundary_band, core_margin)
    regime_names = list(cache_metadata.get("primary_regime_names", ["idle", "mppt", "pitch_control", "transition"]))

    rows: list[dict[str, Any]] = []
    for slice_name in BOUNDARY_SLICE_NAMES:
        selector = masks[slice_name]
        obs_mask = np.asarray(mask) * selector[:, None, :]
        metrics = _masked_metrics(pred, target, obs_mask)
        alignment = _gate_alignment(gate_prob, regime, np.asarray(valid, dtype=bool) & selector)
        out: dict[str, Any] = {
            "dataset": row.get("dataset", cache_metadata.get("dataset", "")),
            "model": row.get("model", ""),
            "seed": row.get("seed", ""),
            "variant_key": row.get("variant_key", ""),
            "experiment_group": row.get("experiment_group", ""),
            "run_dir": str(run_dir),
            "split": split,
            "slice": slice_name,
            "rated_wind": float(rated_wind),
            "pitch_threshold": float(pitch_threshold),
            "boundary_band": float(boundary_band),
            "core_margin": float(core_margin),
            "n_anchor_cells": int(selector.sum()),
            "n_observations": int(obs_mask.sum()),
            "mean_wspd": float(np.nanmean(wspd[selector])) if selector.any() else float("nan"),
            "mean_pab": float(np.nanmean(pab[selector])) if selector.any() else float("nan"),
            "mean_abs_wind_distance": float(np.nanmean(np.abs(wspd[selector] - float(rated_wind)))) if selector.any() else float("nan"),
            **metrics,
            **alignment,
        }
        for regime_id, regime_name in enumerate(regime_names):
            out[f"n_{regime_name}"] = int(((regime == regime_id) & selector).sum())
        rows.append(out)
    return rows


def _summarize(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty:
        return pd.DataFrame()
    group_cols = ["dataset", "model", "slice", "rated_wind", "pitch_threshold", "boundary_band", "core_margin"]
    metric_cols = [
        "mae",
        "rmse",
        "nmi",
        "ari",
        "n_valid_gate",
        "n_anchor_cells",
        "n_observations",
        "mean_wspd",
        "mean_pab",
        "mean_abs_wind_distance",
        "n_idle",
        "n_mppt",
        "n_pitch_control",
        "n_transition",
    ]
    rows: list[dict[str, Any]] = []
    for keys, group in raw_df.groupby(group_cols, dropna=False, sort=False):
        out = {column: value for column, value in zip(group_cols, keys)}
        out["n_runs"] = int(len(group))
        for metric in metric_cols:
            if metric not in group.columns:
                continue
            values = pd.to_numeric(group[metric], errors="coerce").dropna()
            out[f"{metric}_mean"] = float(values.mean()) if not values.empty else float("nan")
            out[f"{metric}_std"] = float(values.std(ddof=0)) if len(values) > 1 else 0.0
        rows.append(out)
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
    boundary = raw_df[raw_df["slice"] == "boundary_band"].copy()
    controls = raw_df[raw_df["slice"] != "boundary_band"].copy()
    if boundary.empty or controls.empty:
        return pd.DataFrame()
    key_cols = ["dataset", "model", "run_dir"]
    metric_cols = ["rmse", "mae", "nmi", "ari"]
    merged = controls.merge(
        boundary[key_cols + metric_cols],
        on=key_cols,
        how="inner",
        suffixes=("_comparator", "_boundary"),
    )
    rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(seed)
    for keys, group in merged.groupby(["dataset", "model", "slice"], dropna=False, sort=False):
        dataset, model, comparator_slice = keys
        out: dict[str, Any] = {
            "dataset": dataset,
            "model": model,
            "comparison": f"boundary_band_minus_{comparator_slice}",
            "comparator_slice": comparator_slice,
            "n_runs": int(len(group)),
        }
        for metric in metric_cols:
            delta = pd.to_numeric(group[f"{metric}_boundary"], errors="coerce").to_numpy() - pd.to_numeric(
                group[f"{metric}_comparator"], errors="coerce"
            ).to_numpy()
            mean, low, high = _bootstrap_ci(delta, rng, bootstrap_samples)
            out[f"delta_{metric}_mean"] = mean
            out[f"delta_{metric}_ci_low"] = low
            out[f"delta_{metric}_ci_high"] = high
            if metric in {"rmse", "mae"}:
                out[f"prob_boundary_{metric}_higher"] = float(np.mean(delta > 0.0)) if delta.size else float("nan")
        rows.append(out)
    return pd.DataFrame(rows)


def _write_report(summary_df: pd.DataFrame, effects_df: pd.DataFrame, output_path: Path) -> None:
    lines = [
        "# Boundary-slice audit",
        "",
        "This audit reads saved strict-mask predictions and measures behavior near the WTB MPPT-to-pitch rated-wind boundary.",
        "",
    ]
    if summary_df.empty:
        lines.append("No saved prediction runs were available for the requested audit.")
    else:
        lines.extend(["## Slice summaries", ""])
        for _, row in summary_df.iterrows():
            nmi = row.get("nmi_mean", float("nan"))
            ari = row.get("ari_mean", float("nan"))
            gate_text = "NMI/ARI not defined for one-class slices"
            if np.isfinite(nmi) and np.isfinite(ari):
                gate_text = f"NMI {nmi:.4f} +/- {row.get('nmi_std', 0.0):.4f}; ARI {ari:.4f} +/- {row.get('ari_std', 0.0):.4f}"
            lines.append(
                f"- {row['model']} {row['slice']}: RMSE {row['rmse_mean']:.4f} +/- {row['rmse_std']:.4f}; "
                f"{gate_text}; anchors {row['n_anchor_cells_mean']:.1f}; n={int(row['n_runs'])}."
            )
        if not effects_df.empty:
            lines.extend(["", "## Boundary-vs-comparator effects", ""])
            for _, row in effects_df.iterrows():
                lines.append(
                    f"- {row['model']} {row['comparison']}: Delta RMSE {row['delta_rmse_mean']:.4f} "
                    f"[{row['delta_rmse_ci_low']:.4f}, {row['delta_rmse_ci_high']:.4f}]."
                )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_boundary_slice_audit(
    run_table: Path | str,
    cache_dir: Path | str,
    output_dir: Path | str,
    root_dir: Path | str = ".",
    split: str = "test",
    models: Iterable[str] | str | None = None,
    rated_wind: float = 10.5,
    pitch_threshold: float = 2.0,
    boundary_band: float = 1.0,
    core_margin: float = 1.0,
    bootstrap_samples: int = 1000,
    seed: int = 42,
) -> Path:
    root_dir = Path(root_dir)
    cache_dir = Path(cache_dir)
    output_dir = ensure_dir(output_dir)
    run_table = Path(run_table)
    df = pd.read_csv(run_table)
    if "run_dir" not in df.columns:
        raise ValueError("Boundary-slice audit requires a run table with a run_dir column.")

    model_filter = _parse_model_filter(models)
    if model_filter and "model" in df.columns:
        df = df[df["model"].astype(str).isin(model_filter)].copy()

    cache_physics, cache_metadata, wspd_idx, pab_idx = _load_cache_physics(cache_dir)
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        rows.extend(
            _audit_one_run(
                row=row,
                root_dir=root_dir,
                cache_physics=cache_physics,
                cache_metadata=cache_metadata,
                wspd_idx=wspd_idx,
                pab_idx=pab_idx,
                split=split,
                rated_wind=rated_wind,
                pitch_threshold=pitch_threshold,
                boundary_band=boundary_band,
                core_margin=core_margin,
            )
        )

    raw_df = pd.DataFrame(rows)
    summary_df = _summarize(raw_df)
    effects_df = _paired_effects(raw_df, bootstrap_samples=bootstrap_samples, seed=seed)

    raw_df.to_csv(output_dir / "boundary_slice_raw.csv", index=False)
    summary_df.to_csv(output_dir / "boundary_slice_summary.csv", index=False)
    effects_df.to_csv(output_dir / "boundary_slice_effects.csv", index=False)
    save_json(
        output_dir / "boundary_slice_config.json",
        {
            "run_table": str(run_table),
            "cache_dir": str(cache_dir),
            "root_dir": str(root_dir),
            "split": split,
            "models": sorted(model_filter),
            "rated_wind": float(rated_wind),
            "pitch_threshold": float(pitch_threshold),
            "boundary_band": float(boundary_band),
            "core_margin": float(core_margin),
            "bootstrap_samples": int(bootstrap_samples),
            "seed": int(seed),
            "n_raw_rows": int(len(raw_df)),
            "n_summary_rows": int(len(summary_df)),
            "n_effect_rows": int(len(effects_df)),
        },
    )
    _write_report(summary_df, effects_df, output_dir / "boundary_slice_report.md")
    return output_dir
