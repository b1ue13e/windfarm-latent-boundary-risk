from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from torch.utils.data import DataLoader

from .config import ModelConfig
from .data import CacheBundle, RegimeWindowDataset, load_cache_bundle
from .model import RegimeAwareForecaster
from .utils import ensure_dir, load_json, save_json, to_device


DEFAULT_INTERVENTIONS = (
    "actual",
    "anchor_boundary_zero",
    "anchor_boundary_wrong_threshold_shift",
    "anchor_random_physics",
    "anchor_wspd_only",
    "anchor_pab_only",
    "anchor_boundary_node_shuffle",
    "anchor_boundary_global_shuffle",
    "anchor_wake_zero",
    "anchor_all_zero",
    "history_boundary_zero",
    "history_boundary_missing",
    "history_nonboundary_zero",
)

MECHANISM_GATE_DEFAULT_INTERVENTIONS = (
    "actual",
    "anchor_boundary_zero",
    "anchor_boundary_wrong_threshold_shift",
    "anchor_random_physics",
    "anchor_wspd_only",
    "anchor_pab_only",
    "anchor_boundary_node_shuffle",
    "anchor_boundary_global_shuffle",
    "anchor_wake_zero",
    "anchor_all_zero",
)

RUN_TABLE_COLUMNS = [
    "dataset",
    "model",
    "run_dir",
    "seed",
    "variant_key",
    "experiment_group",
]

CHECKPOINT_REPLAY_COLUMNS = [
    "dataset",
    "model",
    "seed",
    "variant_key",
    "experiment_group",
    "run_dir",
    "split",
    "replay_status",
    "overall_rmse",
    "reference_overall_rmse",
    "reference_overall_rmse_abs_diff",
    "switch_rmse",
    "reference_switch_rmse",
    "nmi",
    "reference_nmi",
    "reference_nmi_abs_diff",
    "ari",
    "reference_ari",
]

MECHANISM_RAW_COLUMNS = [
    "dataset",
    "model",
    "seed",
    "variant_key",
    "experiment_group",
    "run_dir",
    "split",
    "intervention",
    "intervention_type",
    "feature_indices",
    "physics_indices",
    "physics_keep_indices",
    "physics_node_shuffle_indices",
    "physics_global_shuffle_indices",
    "physics_random_shuffle_indices",
    "physics_shift_indices",
    "physics_shift_value",
    "dominant_flip_rate",
    "mean_gate_l1",
    "reference_metrics_present",
    "reference_overall_rmse",
    "reference_switch_rmse",
    "reference_nmi",
    "reference_ari",
    "reference_overall_rmse_abs_diff",
    "reference_nmi_abs_diff",
    "replay_status",
    "overall_mae",
    "overall_rmse",
    "switch_mae",
    "switch_rmse",
    "pitch_control_mae",
    "pitch_control_rmse",
    "nmi",
    "ari",
    "expert_usage_entropy",
]


@dataclass(frozen=True)
class InterventionSpec:
    name: str
    intervention_type: str
    feature_indices: tuple[int, ...] = ()
    physics_indices: tuple[int, ...] = ()
    physics_keep_indices: tuple[int, ...] = ()
    physics_node_shuffle_indices: tuple[int, ...] = ()
    physics_global_shuffle_indices: tuple[int, ...] = ()
    physics_random_shuffle_indices: tuple[int, ...] = ()
    physics_shift_indices: tuple[int, ...] = ()
    physics_shift_value: float = 0.0
    mask_features: bool = False


def _parse_tokens(raw: Iterable[str] | str | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        tokens = raw.split(",")
    else:
        tokens = list(raw)
    return [str(token).strip() for token in tokens if str(token).strip()]


def _index_many(names: list[str], wanted: Iterable[str]) -> tuple[int, ...]:
    lookup = {name: idx for idx, name in enumerate(names)}
    return tuple(lookup[name] for name in wanted if name in lookup)


def build_wtb_intervention_specs(
    feature_names: list[str],
    physics_names: list[str],
    selected: Iterable[str] | str | None = None,
) -> list[InterventionSpec]:
    boundary_features = _index_many(feature_names, ["Wspd", "Pab_mean"])
    nonboundary_features = _index_many(feature_names, ["Etmp", "Itmp"])
    boundary_physics = _index_many(physics_names, ["Wspd", "Pab_mean"])
    wspd_physics = _index_many(physics_names, ["Wspd"])
    pab_physics = _index_many(physics_names, ["Pab_mean"])
    wake_physics = _index_many(physics_names, ["wake_score"])
    all_physics = tuple(range(len(physics_names)))
    specs = {
        "actual": InterventionSpec("actual", "positive"),
        "anchor_boundary_zero": InterventionSpec(
            "anchor_boundary_zero",
            "anchor_physics_intervention",
            physics_indices=boundary_physics,
        ),
        "anchor_wspd_zero": InterventionSpec(
            "anchor_wspd_zero",
            "anchor_physics_intervention",
            physics_indices=wspd_physics,
        ),
        "anchor_pab_zero": InterventionSpec(
            "anchor_pab_zero",
            "anchor_physics_intervention",
            physics_indices=pab_physics,
        ),
        "anchor_patv_zero": InterventionSpec(
            "anchor_patv_zero",
            "anchor_physics_intervention",
            physics_indices=_index_many(physics_names, ["Patv"]),
        ),
        "anchor_boundary_wrong_threshold_shift": InterventionSpec(
            "anchor_boundary_wrong_threshold_shift",
            "anchor_physics_wrong_threshold_control",
            physics_shift_indices=boundary_physics,
            physics_shift_value=1.0,
        ),
        "anchor_random_physics": InterventionSpec(
            "anchor_random_physics",
            "anchor_physics_random_anchor_control",
            physics_random_shuffle_indices=all_physics,
        ),
        "anchor_wspd_only": InterventionSpec(
            "anchor_wspd_only",
            "anchor_physics_single_channel",
            physics_keep_indices=wspd_physics,
        ),
        "anchor_pab_only": InterventionSpec(
            "anchor_pab_only",
            "anchor_physics_single_channel",
            physics_keep_indices=pab_physics,
        ),
        "anchor_boundary_node_shuffle": InterventionSpec(
            "anchor_boundary_node_shuffle",
            "anchor_physics_distribution_control",
            physics_node_shuffle_indices=boundary_physics,
        ),
        "anchor_boundary_global_shuffle": InterventionSpec(
            "anchor_boundary_global_shuffle",
            "anchor_physics_distribution_control",
            physics_global_shuffle_indices=boundary_physics,
        ),
        "anchor_wake_zero": InterventionSpec(
            "anchor_wake_zero",
            "anchor_physics_control",
            physics_indices=wake_physics,
        ),
        "anchor_all_zero": InterventionSpec(
            "anchor_all_zero",
            "anchor_physics_intervention",
            physics_indices=all_physics,
        ),
        "history_boundary_zero": InterventionSpec(
            "history_boundary_zero",
            "history_feature_intervention",
            feature_indices=boundary_features,
        ),
        "history_boundary_missing": InterventionSpec(
            "history_boundary_missing",
            "history_feature_mask_intervention",
            feature_indices=boundary_features,
            mask_features=True,
        ),
        "history_nonboundary_zero": InterventionSpec(
            "history_nonboundary_zero",
            "history_feature_control",
            feature_indices=nonboundary_features,
        ),
    }
    selected_names = _parse_tokens(selected) or list(DEFAULT_INTERVENTIONS)
    missing = [name for name in selected_names if name not in specs]
    if missing:
        raise ValueError("Unknown intervention(s): " + ", ".join(missing))
    return [specs[name] for name in selected_names]


def _resolve_run_dir(raw_path: Any, root_dir: Path) -> Path:
    run_dir = Path(str(raw_path))
    if run_dir.is_absolute():
        return run_dir
    return root_dir / run_dir


def _model_filter(models: Iterable[str] | str | None) -> set[str]:
    return set(_parse_tokens(models))


def _truthy_all(values: pd.Series, expected: str) -> bool:
    if values.empty:
        return False
    return bool((values.astype(str) == expected).all())


def _resolve_replay_gate_status(audit_df: pd.DataFrame) -> str:
    if audit_df.empty:
        return "no_audited_runs"
    statuses = audit_df.get("replay_status", pd.Series(dtype=str)).dropna().astype(str)
    if statuses.empty:
        return "no_replay_status"
    if (statuses == "checkpoint_mismatch").any():
        return "checkpoint_mismatch"
    if (statuses == "missing_reference").any():
        return "missing_reference"
    if _truthy_all(statuses, "matches_reference"):
        return "passed"
    return "mixed_or_unknown"


def build_run_table_from_suite(
    suite_dir: Path | str,
    output_path: Path | str,
    dataset: str = "wtb",
    split: str = "test",
    models: Iterable[str] | str | None = None,
    variant_keys: Iterable[str] | str | None = None,
    experiment_groups: Iterable[str] | str | None = None,
) -> Path:
    from .paper import aggregate_runs, collect_suite_run_dirs

    suite_dir = Path(suite_dir)
    output_path = Path(output_path)
    ensure_dir(output_path.parent)
    labeled_run_dirs = collect_suite_run_dirs(suite_dir, dataset)
    aggregate_dir = ensure_dir(output_path.parent / "_aggregated_suite_runs")
    df = aggregate_runs(dataset, labeled_run_dirs, aggregate_dir, split=split)
    if df.empty:
        df = pd.DataFrame(columns=RUN_TABLE_COLUMNS)
    model_filter = _model_filter(models)
    if model_filter and "model" in df.columns:
        df = df[df["model"].astype(str).isin(model_filter)].copy()
    variant_filter = set(_parse_tokens(variant_keys))
    if variant_filter and "variant_key" in df.columns:
        df = df[df["variant_key"].astype(str).isin(variant_filter)].copy()
    group_filter = set(_parse_tokens(experiment_groups))
    if group_filter and "experiment_group" in df.columns:
        df = df[df["experiment_group"].astype(str).isin(group_filter)].copy()
    for column in RUN_TABLE_COLUMNS:
        if column not in df.columns:
            df[column] = pd.Series(dtype=object)
    df.to_csv(output_path, index=False)
    return output_path


def _load_model_from_checkpoint(run_dir: Path, bundle: CacheBundle, device: torch.device) -> RegimeAwareForecaster:
    checkpoint_path = run_dir / "best_model.pt"
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Missing checkpoint: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location=device)
    model_config = ModelConfig(**checkpoint["model_config"])
    train_config = checkpoint["train_config"]
    model = RegimeAwareForecaster(
        feature_dim=int(bundle.features.shape[-1]),
        pred_len=int(bundle.metadata["pred_len"]),
        mode=str(train_config["mode"]),
        config=model_config,
    ).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model


def _masked_metrics(pred: np.ndarray, target: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    pred = np.nan_to_num(pred.astype(np.float64), nan=0.0)
    target = np.nan_to_num(target.astype(np.float64), nan=0.0)
    weight = mask.astype(np.float64)
    denom = max(float(weight.sum()), 1.0)
    mae = float((np.abs(pred - target) * weight).sum() / denom)
    rmse = float(np.sqrt((((pred - target) ** 2) * weight).sum() / denom))
    return {"mae": mae, "rmse": rmse}


def _switch_selector(regime_primary: np.ndarray, steps_per_hour: int) -> np.ndarray:
    switch_window = 3 * int(steps_per_hour)
    selector = np.zeros_like(regime_primary, dtype=bool)
    if regime_primary.shape[0] <= 1:
        return selector
    changes = regime_primary[1:] != regime_primary[:-1]
    rows, nodes = np.where(changes)
    for row, node in zip(rows, nodes):
        lo = max(0, row + 1 - switch_window)
        hi = min(regime_primary.shape[0], row + 2 + switch_window)
        selector[lo:hi, node] = True
    return selector


def _apply_intervention(batch: dict[str, torch.Tensor], spec: InterventionSpec) -> dict[str, torch.Tensor]:
    if spec.name == "actual":
        return batch
    mutated = dict(batch)
    if spec.feature_indices:
        x_hist = mutated["x_hist"].clone()
        x_hist[..., list(spec.feature_indices)] = 0.0
        mutated["x_hist"] = x_hist
        if spec.mask_features:
            feature_mask = mutated["feature_mask_hist"].clone()
            feature_mask[..., list(spec.feature_indices)] = 0.0
            mutated["feature_mask_hist"] = feature_mask
    if spec.physics_keep_indices:
        anchor_physics = mutated["anchor_physics"].clone()
        keep = set(int(index) for index in spec.physics_keep_indices)
        zero_indices = [index for index in range(anchor_physics.shape[-1]) if index not in keep]
        if zero_indices:
            anchor_physics[..., zero_indices] = 0.0
        mutated["anchor_physics"] = anchor_physics
    if spec.physics_indices:
        anchor_physics = mutated["anchor_physics"].clone()
        anchor_physics[..., list(spec.physics_indices)] = 0.0
        mutated["anchor_physics"] = anchor_physics
    if spec.physics_node_shuffle_indices:
        anchor_physics = mutated["anchor_physics"].clone()
        indices = list(spec.physics_node_shuffle_indices)
        anchor_physics[..., indices] = torch.roll(anchor_physics[..., indices], shifts=1, dims=1)
        mutated["anchor_physics"] = anchor_physics
    if spec.physics_global_shuffle_indices:
        anchor_physics = mutated["anchor_physics"].clone()
        indices = list(spec.physics_global_shuffle_indices)
        values = anchor_physics[..., indices]
        flat = values.reshape(-1, len(indices))
        anchor_physics[..., indices] = torch.roll(flat, shifts=17, dims=0).reshape_as(values)
        mutated["anchor_physics"] = anchor_physics
    if spec.physics_random_shuffle_indices:
        anchor_physics = mutated["anchor_physics"].clone()
        indices = list(spec.physics_random_shuffle_indices)
        values = anchor_physics[..., indices]
        flat = values.reshape(-1, len(indices))
        if flat.shape[0] > 1:
            order = torch.arange(flat.shape[0], device=flat.device)
            perm = (order * 37 + 17) % flat.shape[0]
            if torch.unique(perm).numel() != flat.shape[0]:
                perm = torch.roll(order, shifts=17)
            flat = flat[perm]
        anchor_physics[..., indices] = flat.reshape_as(values)
        mutated["anchor_physics"] = anchor_physics
    if spec.physics_shift_indices:
        anchor_physics = mutated["anchor_physics"].clone()
        indices = list(spec.physics_shift_indices)
        anchor_physics[..., indices] = anchor_physics[..., indices] + float(spec.physics_shift_value)
        mutated["anchor_physics"] = anchor_physics
    return mutated


def _evaluate_intervention(
    model: RegimeAwareForecaster,
    loader: DataLoader,
    bundle: CacheBundle,
    device: torch.device,
    spec: InterventionSpec,
) -> dict[str, Any]:
    pred_batches: list[np.ndarray] = []
    target_batches: list[np.ndarray] = []
    mask_batches: list[np.ndarray] = []
    regime_batches: list[np.ndarray] = []
    valid_batches: list[np.ndarray] = []
    gate_batches: list[np.ndarray] = []

    with torch.no_grad():
        for batch in loader:
            batch = to_device(batch, device)
            batch = _apply_intervention(batch, spec)
            pred, gate_prob, _ = model(
                batch["x_hist"],
                batch["edge_index_hist"],
                batch["edge_weight_hist"],
                batch["feature_mask_hist"],
                batch["anchor_physics"],
            )
            pred_batches.append(pred.cpu().numpy())
            target_batches.append(batch["target"].cpu().numpy())
            mask_batches.append(batch["target_mask"].cpu().numpy())
            regime_batches.append(batch["regime_primary"].cpu().numpy())
            valid_batches.append(batch["regime_primary_valid"].cpu().numpy())
            if gate_prob is not None:
                gate_batches.append(gate_prob.cpu().numpy())

    if not pred_batches:
        return {"overall_mae": float("nan"), "overall_rmse": float("nan")}

    pred = np.concatenate(pred_batches, axis=0)
    target = np.concatenate(target_batches, axis=0)
    mask = np.concatenate(mask_batches, axis=0)
    regime = np.concatenate(regime_batches, axis=0)
    valid = np.concatenate(valid_batches, axis=0).astype(bool)
    overall = _masked_metrics(pred, target, mask)
    switch = _masked_metrics(
        pred,
        target,
        mask * _switch_selector(regime, int(bundle.metadata.get("steps_per_hour", 6)))[:, None, :],
    )
    row: dict[str, Any] = {
        "overall_mae": overall["mae"],
        "overall_rmse": overall["rmse"],
        "switch_mae": switch["mae"],
        "switch_rmse": switch["rmse"],
    }
    names = list(bundle.metadata.get("primary_regime_names", []))
    if "pitch_control" in names:
        pitch_id = names.index("pitch_control")
        pitch = _masked_metrics(pred, target, mask * (regime == pitch_id)[:, None, :])
        row["pitch_control_mae"] = pitch["mae"]
        row["pitch_control_rmse"] = pitch["rmse"]

    if gate_batches:
        gate_prob = np.concatenate(gate_batches, axis=0)
        primary_num_classes = int(bundle.metadata["primary_num_classes"])
        gate_label = gate_prob[..., :primary_num_classes].argmax(axis=-1)
        flat_true = regime[valid]
        flat_pred = gate_label[valid]
        row.update(
            {
                "nmi": float(normalized_mutual_info_score(flat_true, flat_pred)) if flat_true.size else float("nan"),
                "ari": float(adjusted_rand_score(flat_true, flat_pred)) if flat_true.size else float("nan"),
                "expert_usage_entropy": float(
                    -np.sum(
                        np.clip(gate_prob.mean(axis=(0, 1)), 1e-12, None)
                        * np.log(np.clip(gate_prob.mean(axis=(0, 1)), 1e-12, None))
                    )
                ),
                "gate_prob": gate_prob,
                "gate_label": gate_label,
                "valid": valid,
            }
        )
    return row


def _without_arrays(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in {"gate_prob", "gate_label", "valid"}}


def _reference_test_metrics(run_dir: Path, split: str) -> dict[str, Any]:
    empty_reference = {
        "reference_metrics_present": False,
        "reference_overall_rmse": None,
        "reference_switch_rmse": None,
        "reference_nmi": None,
        "reference_ari": None,
    }
    metrics_path = run_dir / f"{split}_metrics" / "metrics.json"
    if not metrics_path.exists():
        return empty_reference
    metrics = load_json(metrics_path)
    gate = metrics.get("gate_alignment", {})
    return {
        "reference_metrics_present": True,
        "reference_overall_rmse": metrics.get("overall", {}).get("rmse"),
        "reference_switch_rmse": metrics.get("switch_window", {}).get("rmse"),
        "reference_nmi": gate.get("nmi"),
        "reference_ari": gate.get("ari"),
    }


def _summarize(raw_df: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "overall_rmse",
        "switch_rmse",
        "pitch_control_rmse",
        "nmi",
        "ari",
        "dominant_flip_rate",
        "mean_gate_l1",
    ]
    rows: list[dict[str, Any]] = []
    if raw_df.empty:
        return pd.DataFrame()
    for keys, group in raw_df.groupby(["dataset", "model", "intervention", "intervention_type"], dropna=False, sort=False):
        dataset, model, intervention, intervention_type = keys
        row = {
            "dataset": dataset,
            "model": model,
            "intervention": intervention,
            "intervention_type": intervention_type,
            "n_runs": int(len(group)),
        }
        for metric in metrics:
            values = pd.to_numeric(group.get(metric), errors="coerce").dropna()
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
    actual = raw_df[raw_df["intervention"] == "actual"].copy()
    controls = raw_df[raw_df["intervention"] != "actual"].copy()
    if actual.empty or controls.empty:
        return pd.DataFrame()
    key_cols = ["dataset", "model", "run_dir"]
    merged = controls.merge(
        actual[key_cols + ["overall_rmse", "switch_rmse", "pitch_control_rmse", "nmi", "ari"]],
        on=key_cols,
        suffixes=("_intervention", "_actual"),
    )
    rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(seed)
    for keys, group in merged.groupby(["dataset", "model", "intervention", "intervention_type"], dropna=False, sort=False):
        dataset, model, intervention, intervention_type = keys
        delta_rmse = group["overall_rmse_intervention"].to_numpy(dtype=float) - group["overall_rmse_actual"].to_numpy(dtype=float)
        delta_switch = group["switch_rmse_intervention"].to_numpy(dtype=float) - group["switch_rmse_actual"].to_numpy(dtype=float)
        delta_pitch = group["pitch_control_rmse_intervention"].to_numpy(dtype=float) - group[
            "pitch_control_rmse_actual"
        ].to_numpy(dtype=float)
        drop_nmi = group["nmi_actual"].to_numpy(dtype=float) - group["nmi_intervention"].to_numpy(dtype=float)
        drop_ari = group["ari_actual"].to_numpy(dtype=float) - group["ari_intervention"].to_numpy(dtype=float)
        rmse_mean, rmse_low, rmse_high = _bootstrap_ci(delta_rmse, rng, bootstrap_samples)
        switch_mean, switch_low, switch_high = _bootstrap_ci(delta_switch, rng, bootstrap_samples)
        pitch_mean, pitch_low, pitch_high = _bootstrap_ci(delta_pitch, rng, bootstrap_samples)
        nmi_mean, nmi_low, nmi_high = _bootstrap_ci(drop_nmi, rng, bootstrap_samples)
        ari_mean, ari_low, ari_high = _bootstrap_ci(drop_ari, rng, bootstrap_samples)
        rows.append(
            {
                "dataset": dataset,
                "model": model,
                "intervention": intervention,
                "intervention_type": intervention_type,
                "n_runs": int(len(group)),
                "delta_overall_rmse_mean": rmse_mean,
                "delta_overall_rmse_ci_low": rmse_low,
                "delta_overall_rmse_ci_high": rmse_high,
                "delta_switch_rmse_mean": switch_mean,
                "delta_switch_rmse_ci_low": switch_low,
                "delta_switch_rmse_ci_high": switch_high,
                "delta_pitch_control_rmse_mean": pitch_mean,
                "delta_pitch_control_rmse_ci_low": pitch_low,
                "delta_pitch_control_rmse_ci_high": pitch_high,
                "drop_nmi_mean": nmi_mean,
                "drop_nmi_ci_low": nmi_low,
                "drop_nmi_ci_high": nmi_high,
                "drop_ari_mean": ari_mean,
                "drop_ari_ci_low": ari_low,
                "drop_ari_ci_high": ari_high,
            }
        )
    return pd.DataFrame(rows)


def _write_report(summary_df: pd.DataFrame, effects_df: pd.DataFrame, output_path: Path) -> None:
    lines = [
        "# Mechanism intervention audit",
        "",
        "This audit reloads trained WTB MoE checkpoints and replays the test split after targeted physical-variable interventions.",
        "",
    ]
    if summary_df.empty:
        lines.append("No runs were evaluated.")
    else:
        raw_path = output_path.parent / "mechanism_intervention_raw.csv"
        mismatch_note = ""
        if raw_path.exists():
            raw_df = pd.read_csv(raw_path)
            actual_status = raw_df.loc[raw_df["intervention"] == "actual", "replay_status"].dropna().astype(str)
            if (actual_status == "checkpoint_mismatch").any() or (actual_status == "missing_reference").any():
                mismatch_note = (
                    "Warning: at least one actual replay lacks saved reference metrics or does not match them. "
                    "Treat intervention effects as diagnostic until checkpoints are regenerated and pass replay consistency."
                )
        if mismatch_note:
            lines.extend(["## Replay Consistency", "", mismatch_note, ""])
        actual = summary_df[summary_df["intervention"] == "actual"]
        lines.extend(["## Actual replay", ""])
        for _, row in actual.iterrows():
            lines.append(
                f"- {row['model']}: RMSE {row['overall_rmse_mean']:.4f}; "
                f"NMI/ARI {row['nmi_mean']:.4f} / {row['ari_mean']:.4f}; n={int(row['n_runs'])}."
            )
        if not effects_df.empty:
            lines.extend(["", "## Intervention effects", ""])
            for _, row in effects_df.iterrows():
                lines.append(
                    f"- {row['model']} under {row['intervention']}: "
                    f"Delta RMSE {row['delta_overall_rmse_mean']:.4f} "
                    f"[{row['delta_overall_rmse_ci_low']:.4f}, {row['delta_overall_rmse_ci_high']:.4f}], "
                    f"drop NMI {row['drop_nmi_mean']:.4f} "
                    f"[{row['drop_nmi_ci_low']:.4f}, {row['drop_nmi_ci_high']:.4f}]."
                )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_mechanism_intervention_audit(
    run_table: Path | str,
    cache_dir: Path | str,
    output_dir: Path | str,
    root_dir: Path | str = ".",
    split: str = "test",
    models: Iterable[str] | str | None = None,
    interventions: Iterable[str] | str | None = None,
    batch_size: int = 128,
    seed: int = 42,
    bootstrap_samples: int = 1000,
    device: str = "auto",
) -> Path:
    root_dir = Path(root_dir)
    output_dir = ensure_dir(output_dir)
    try:
        run_df = pd.read_csv(run_table)
    except pd.errors.EmptyDataError:
        run_df = pd.DataFrame(columns=RUN_TABLE_COLUMNS)
    model_filter = _model_filter(models)
    if model_filter and "model" in run_df.columns:
        run_df = run_df[run_df["model"].astype(str).isin(model_filter)].copy()
    if run_df.empty:
        raw_df = pd.DataFrame(columns=MECHANISM_RAW_COLUMNS)
        summary_df = pd.DataFrame()
        effects_df = pd.DataFrame()
        raw_df.to_csv(output_dir / "mechanism_intervention_raw.csv", index=False)
        summary_df.to_csv(output_dir / "mechanism_intervention_summary.csv", index=False)
        effects_df.to_csv(output_dir / "mechanism_intervention_effects.csv", index=False)
        save_json(
            output_dir / "mechanism_intervention_config.json",
            {
                "run_table": str(run_table),
                "cache_dir": str(cache_dir),
                "root_dir": str(root_dir),
                "split": split,
                "models": sorted(model_filter),
                "interventions": _parse_tokens(interventions) or list(DEFAULT_INTERVENTIONS),
                "batch_size": int(batch_size),
                "seed": int(seed),
                "bootstrap_samples": int(bootstrap_samples),
                "device": device,
                "n_raw_rows": 0,
            },
        )
        _write_report(summary_df, effects_df, output_dir / "mechanism_intervention_report.md")
        return output_dir

    bundle = load_cache_bundle(cache_dir, mmap_mode="r")
    feature_names = list(bundle.metadata.get("feature_names", []))
    physics_names = list(bundle.metadata.get("physics_names", []))
    specs = build_wtb_intervention_specs(feature_names, physics_names, interventions)
    if device == "auto":
        torch_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        torch_device = torch.device(device)

    dataset = RegimeWindowDataset(bundle, split, int(bundle.metadata["hist_len"]), int(bundle.metadata["pred_len"]))
    loader = DataLoader(dataset, batch_size=int(batch_size), shuffle=False, num_workers=0, pin_memory=torch_device.type == "cuda")
    rows: list[dict[str, Any]] = []
    for _, run_row in run_df.iterrows():
        run_dir = _resolve_run_dir(run_row["run_dir"], root_dir)
        if not (run_dir / "best_model.pt").exists():
            continue
        model = _load_model_from_checkpoint(run_dir, bundle, torch_device)
        reference = _reference_test_metrics(run_dir, split)
        actual_metrics: dict[str, Any] | None = None
        for spec in specs:
            metrics = _evaluate_intervention(model, loader, bundle, torch_device, spec)
            if spec.name == "actual":
                actual_metrics = metrics
                flip_rate = 0.0
                mean_gate_l1 = 0.0
                reference_overall_rmse = reference.get("reference_overall_rmse")
                reference_nmi = reference.get("reference_nmi")
                reference_missing = not bool(reference.get("reference_metrics_present")) or reference_overall_rmse is None
                rmse_abs_diff = (
                    abs(float(metrics["overall_rmse"]) - float(reference_overall_rmse))
                    if reference_overall_rmse is not None and np.isfinite(metrics.get("overall_rmse", np.nan))
                    else float("nan")
                )
                nmi_abs_diff = (
                    abs(float(metrics.get("nmi", np.nan)) - float(reference_nmi))
                    if reference_nmi is not None and np.isfinite(metrics.get("nmi", np.nan))
                    else float("nan")
                )
                replay_status = (
                    "missing_reference"
                    if reference_missing
                    else (
                        "matches_reference"
                        if (
                            np.isfinite(rmse_abs_diff)
                            and rmse_abs_diff <= 1e-3
                            and (not np.isfinite(nmi_abs_diff) or nmi_abs_diff <= 1e-6)
                        )
                        else "checkpoint_mismatch"
                    )
                )
            elif actual_metrics is not None and "gate_label" in metrics and "gate_label" in actual_metrics:
                valid = actual_metrics["valid"]
                flip_rate = float(np.mean(metrics["gate_label"][valid] != actual_metrics["gate_label"][valid]))
                mean_gate_l1 = float(np.abs(metrics["gate_prob"] - actual_metrics["gate_prob"]).mean())
                rmse_abs_diff = float("nan")
                nmi_abs_diff = float("nan")
                replay_status = ""
            else:
                flip_rate = float("nan")
                mean_gate_l1 = float("nan")
                rmse_abs_diff = float("nan")
                nmi_abs_diff = float("nan")
                replay_status = ""
            rows.append(
                {
                    "dataset": run_row.get("dataset", bundle.metadata.get("dataset", "")),
                    "model": run_row.get("model", ""),
                    "seed": run_row.get("seed", ""),
                    "variant_key": run_row.get("variant_key", ""),
                    "experiment_group": run_row.get("experiment_group", ""),
                    "run_dir": str(run_dir),
                    "split": split,
                    "intervention": spec.name,
                    "intervention_type": spec.intervention_type,
                    "feature_indices": "|".join(str(index) for index in spec.feature_indices),
                    "physics_indices": "|".join(str(index) for index in spec.physics_indices),
                    "physics_keep_indices": "|".join(str(index) for index in spec.physics_keep_indices),
                    "physics_node_shuffle_indices": "|".join(str(index) for index in spec.physics_node_shuffle_indices),
                    "physics_global_shuffle_indices": "|".join(str(index) for index in spec.physics_global_shuffle_indices),
                    "physics_random_shuffle_indices": "|".join(str(index) for index in spec.physics_random_shuffle_indices),
                    "physics_shift_indices": "|".join(str(index) for index in spec.physics_shift_indices),
                    "physics_shift_value": float(spec.physics_shift_value),
                    "dominant_flip_rate": flip_rate,
                    "mean_gate_l1": mean_gate_l1,
                    **reference,
                    "reference_overall_rmse_abs_diff": rmse_abs_diff,
                    "reference_nmi_abs_diff": nmi_abs_diff,
                    "replay_status": replay_status,
                    **_without_arrays(metrics),
                }
            )
        model.to("cpu")
        del model
        if torch_device.type == "cuda":
            torch.cuda.empty_cache()

    raw_df = pd.DataFrame(rows)
    for column in MECHANISM_RAW_COLUMNS:
        if column not in raw_df.columns:
            raw_df[column] = pd.Series(dtype=object)
    summary_df = _summarize(raw_df)
    effects_df = _paired_effects(raw_df, bootstrap_samples=bootstrap_samples, seed=seed)
    raw_df.to_csv(output_dir / "mechanism_intervention_raw.csv", index=False)
    summary_df.to_csv(output_dir / "mechanism_intervention_summary.csv", index=False)
    effects_df.to_csv(output_dir / "mechanism_intervention_effects.csv", index=False)
    save_json(
        output_dir / "mechanism_intervention_config.json",
        {
            "run_table": str(run_table),
            "cache_dir": str(cache_dir),
            "root_dir": str(root_dir),
            "split": split,
            "models": sorted(model_filter),
            "interventions": [spec.name for spec in specs],
            "batch_size": int(batch_size),
            "seed": int(seed),
            "bootstrap_samples": int(bootstrap_samples),
            "device": str(torch_device),
            "n_raw_rows": int(len(raw_df)),
        },
    )
    _write_report(summary_df, effects_df, output_dir / "mechanism_intervention_report.md")
    return output_dir


def run_checkpoint_replay_audit(
    run_table: Path | str,
    cache_dir: Path | str,
    output_dir: Path | str,
    root_dir: Path | str = ".",
    split: str = "test",
    models: Iterable[str] | str | None = None,
    batch_size: int = 512,
    device: str = "auto",
) -> Path:
    output_dir = ensure_dir(output_dir)
    replay_dir = ensure_dir(output_dir / "_replay_actual_tmp")
    run_mechanism_intervention_audit(
        run_table=run_table,
        cache_dir=cache_dir,
        output_dir=replay_dir,
        root_dir=root_dir,
        split=split,
        models=models,
        interventions="actual",
        batch_size=batch_size,
        bootstrap_samples=0,
        device=device,
    )
    try:
        raw_df = pd.read_csv(replay_dir / "mechanism_intervention_raw.csv")
    except pd.errors.EmptyDataError:
        raw_df = pd.DataFrame()
    available = [column for column in CHECKPOINT_REPLAY_COLUMNS if column in raw_df.columns]
    audit_df = raw_df[available].copy() if available else pd.DataFrame(columns=CHECKPOINT_REPLAY_COLUMNS)
    for column in CHECKPOINT_REPLAY_COLUMNS:
        if column not in audit_df.columns:
            audit_df[column] = pd.Series(dtype=object)
    audit_df = audit_df[CHECKPOINT_REPLAY_COLUMNS]
    audit_df.to_csv(output_dir / "checkpoint_replay_audit.csv", index=False)
    summary_rows = []
    if not audit_df.empty:
        for keys, group in audit_df.groupby(["dataset", "model", "replay_status"], dropna=False, sort=False):
            dataset, model, replay_status = keys
            summary_rows.append(
                {
                    "dataset": dataset,
                    "model": model,
                    "replay_status": replay_status,
                    "n_runs": int(len(group)),
                    "max_overall_rmse_abs_diff": float(
                        pd.to_numeric(group.get("reference_overall_rmse_abs_diff"), errors="coerce").max()
                    ),
                    "max_nmi_abs_diff": float(pd.to_numeric(group.get("reference_nmi_abs_diff"), errors="coerce").max()),
                }
            )
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(output_dir / "checkpoint_replay_summary.csv", index=False)
    save_json(
        output_dir / "checkpoint_replay_config.json",
        {
            "run_table": str(run_table),
            "cache_dir": str(cache_dir),
            "root_dir": str(root_dir),
            "split": split,
            "models": _parse_tokens(models),
            "batch_size": int(batch_size),
            "device": device,
            "n_runs": int(len(audit_df)),
            "n_mismatches": int((audit_df.get("replay_status", pd.Series(dtype=str)) == "checkpoint_mismatch").sum()),
            "n_missing_references": int(
                (audit_df.get("replay_status", pd.Series(dtype=str)) == "missing_reference").sum()
            ),
        },
    )
    lines = [
        "# Checkpoint replay audit",
        "",
        "This gate replays `best_model.pt` on the requested split and compares it with saved reference metrics.",
        "",
    ]
    if audit_df.empty:
        lines.append("No checkpoints were audited.")
    else:
        mismatch_count = int((audit_df["replay_status"] == "checkpoint_mismatch").sum())
        missing_count = int((audit_df["replay_status"] == "missing_reference").sum())
        lines.append(f"- Audited runs: {len(audit_df)}")
        lines.append(f"- Checkpoint mismatches: {mismatch_count}")
        lines.append(f"- Missing reference metrics: {missing_count}")
        if mismatch_count:
            lines.append("- Do not use affected checkpoints for intervention evidence until they are regenerated.")
        if missing_count:
            lines.append("- Missing-reference checkpoints are loadable diagnostics only until final test metrics are written.")
    (output_dir / "checkpoint_replay_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_dir


def run_mechanism_evidence_gate(
    suite_dir: Path | str,
    cache_dir: Path | str,
    output_dir: Path | str,
    root_dir: Path | str = ".",
    dataset: str = "wtb",
    split: str = "test",
    models: Iterable[str] | str | None = "MoE + L_bal + L_align + L_force",
    variant_keys: Iterable[str] | str | None = "bal_align_force",
    experiment_groups: Iterable[str] | str | None = "ablation",
    interventions: Iterable[str] | str | None = None,
    batch_size: int = 512,
    bootstrap_samples: int = 1000,
    seed: int = 42,
    device: str = "auto",
    run_intervention_on_pass: bool = True,
) -> Path:
    output_dir = ensure_dir(output_dir)
    run_table = build_run_table_from_suite(
        suite_dir=suite_dir,
        output_path=output_dir / "mechanism_gate_run_table.csv",
        dataset=dataset,
        split=split,
        models=models,
        variant_keys=variant_keys,
        experiment_groups=experiment_groups,
    )
    replay_dir = run_checkpoint_replay_audit(
        run_table=run_table,
        cache_dir=cache_dir,
        output_dir=output_dir / "checkpoint_replay",
        root_dir=root_dir,
        split=split,
        models=models,
        batch_size=batch_size,
        device=device,
    )
    audit_path = replay_dir / "checkpoint_replay_audit.csv"
    audit_df = pd.read_csv(audit_path) if audit_path.exists() else pd.DataFrame()
    gate_status = _resolve_replay_gate_status(audit_df)
    intervention_dir: Path | None = None
    selected_interventions = _parse_tokens(interventions) or list(MECHANISM_GATE_DEFAULT_INTERVENTIONS)
    if gate_status == "passed" and run_intervention_on_pass:
        intervention_dir = run_mechanism_intervention_audit(
            run_table=run_table,
            cache_dir=cache_dir,
            output_dir=output_dir / "mechanism_intervention",
            root_dir=root_dir,
            split=split,
            models=models,
            interventions=selected_interventions,
            batch_size=batch_size,
            seed=seed,
            bootstrap_samples=bootstrap_samples,
            device=device,
        )
    config = {
        "suite_dir": str(suite_dir),
        "cache_dir": str(cache_dir),
        "root_dir": str(root_dir),
        "dataset": dataset,
        "split": split,
        "models": _parse_tokens(models),
        "variant_keys": _parse_tokens(variant_keys),
        "experiment_groups": _parse_tokens(experiment_groups),
        "interventions": selected_interventions,
        "batch_size": int(batch_size),
        "bootstrap_samples": int(bootstrap_samples),
        "seed": int(seed),
        "device": device,
        "run_intervention_on_pass": bool(run_intervention_on_pass),
        "run_table": str(run_table),
        "checkpoint_replay_dir": str(replay_dir),
        "mechanism_intervention_dir": str(intervention_dir) if intervention_dir else None,
        "gate_status": gate_status,
        "n_audited_runs": int(len(audit_df)),
        "n_matches": int((audit_df.get("replay_status", pd.Series(dtype=str)) == "matches_reference").sum()),
        "n_mismatches": int((audit_df.get("replay_status", pd.Series(dtype=str)) == "checkpoint_mismatch").sum()),
        "n_missing_references": int((audit_df.get("replay_status", pd.Series(dtype=str)) == "missing_reference").sum()),
    }
    save_json(output_dir / "mechanism_evidence_gate_config.json", config)
    lines = [
        "# Mechanism Evidence Gate",
        "",
        "This gate decides whether reloaded WTB checkpoints can support mechanism-intervention evidence.",
        "",
        f"- Gate status: `{gate_status}`",
        f"- Audited runs: {config['n_audited_runs']}",
        f"- Matches: {config['n_matches']}",
        f"- Checkpoint mismatches: {config['n_mismatches']}",
        f"- Missing reference metrics: {config['n_missing_references']}",
        f"- Run table: `{run_table}`",
        f"- Checkpoint replay directory: `{replay_dir}`",
    ]
    if intervention_dir is not None:
        lines.append(f"- Mechanism intervention directory: `{intervention_dir}`")
        lines.append("")
        lines.append("Result: mechanism-intervention evidence was generated because every audited checkpoint matched its saved reference metrics.")
    elif gate_status != "passed":
        lines.append("")
        lines.append("Result: mechanism-intervention evidence was not generated. Regenerate complete corrected runs until every audited checkpoint reports `matches_reference`.")
    else:
        lines.append("")
        lines.append("Result: replay gate passed, but intervention execution was disabled by configuration.")
    (output_dir / "mechanism_evidence_gate_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_dir
