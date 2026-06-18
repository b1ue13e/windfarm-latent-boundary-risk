from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import json

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, confusion_matrix, normalized_mutual_info_score

from .config import DataConfig
from .regimes import compute_wtb_operation_regime
from .strict_anchor import strict_anchor_mask_report
from .utils import ensure_dir, load_json, save_json


DEFAULT_THRESHOLD_CONTROL_VARIANTS = (
    "sens_rated_7p0",
    "sens_rated_13p0",
    "sens_pitch_0p5",
    "sens_pitch_20p0",
)
DEFAULT_THRESHOLD_VALIDITY_RATED_GRID = (10.0, 10.5, 11.0)
DEFAULT_THRESHOLD_VALIDITY_PITCH_GRID = (1.5, 2.0, 2.5)
DEFAULT_THRESHOLD_CONTROL_SEEDS = (201, 202, 203, 204, 205)
REVIEWER_STAT_REQUIRED_FILES = (
    "reviewer_stat_pack_config.json",
    "reviewer_stat_pack_run_table.csv",
    "per_example_manifest.csv",
    "per_example_predictions.csv.gz",
    "paired_effects_raw.csv",
    "paired_effects_summary.csv",
    "efficiency_fairness_table.csv",
    "failure_cases_gate_correct_bad.csv",
    "failure_cases_gate_correct_bad.png",
    "failure_cases_boundary_gate_correct_bad.csv",
    "failure_cases_boundary_gate_correct_bad.png",
    "reviewer_stat_pack_report.md",
)
DEFAULT_THRESHOLD_SEMANTIC_INTERVENTION = "anchor_boundary_zero"
THRESHOLD_SEMANTIC_REQUIRED_FILES = (
    "threshold_controls_semantic_guard.json",
    "threshold_controls_semantic_pairs.csv",
    "threshold_controls_semantic_summary.csv",
)

THRESHOLD_CONTROL_SPECS: dict[str, dict[str, Any]] = {
    "sens_rated_7p0": {
        "label": "Physics-Aligned MoE",
        "mode": "moe_phys_full",
        "setting_group": "rated_wind",
        "setting_value": 7.0,
        "setting_label": "rated_wind=7.0",
    },
    "sens_rated_13p0": {
        "label": "Physics-Aligned MoE",
        "mode": "moe_phys_full",
        "setting_group": "rated_wind",
        "setting_value": 13.0,
        "setting_label": "rated_wind=13.0",
    },
    "sens_pitch_0p5": {
        "label": "Physics-Aligned MoE",
        "mode": "moe_phys_full",
        "setting_group": "pitch_threshold",
        "setting_value": 0.5,
        "setting_label": "pitch_threshold=0.5",
    },
    "sens_pitch_20p0": {
        "label": "Physics-Aligned MoE",
        "mode": "moe_phys_full",
        "setting_group": "pitch_threshold",
        "setting_value": 20.0,
        "setting_label": "pitch_threshold=20.0",
    },
}


def _parse_variant_keys(values: Iterable[str] | str | None) -> list[str]:
    if values is None:
        tokens = list(DEFAULT_THRESHOLD_CONTROL_VARIANTS)
    elif isinstance(values, str):
        tokens = [token.strip() for token in values.split(",") if token.strip()]
    else:
        tokens = [str(token).strip() for token in values if str(token).strip()]
    unknown = sorted(set(tokens).difference(THRESHOLD_CONTROL_SPECS))
    if unknown:
        available = ", ".join(sorted(THRESHOLD_CONTROL_SPECS))
        raise ValueError(f"Unknown threshold-control variant(s): {', '.join(unknown)}. Available: {available}")
    return tokens


def _parse_seeds(values: Iterable[int] | str | None) -> list[int]:
    if values is None:
        return [int(seed) for seed in DEFAULT_THRESHOLD_CONTROL_SEEDS]
    if isinstance(values, str):
        return [int(token.strip()) for token in values.split(",") if token.strip()]
    return [int(seed) for seed in values]


def _jsonable_bounds(bounds: dict[str, tuple[int, int]] | dict[str, list[int]]) -> dict[str, list[int]]:
    return {str(key): [int(value[0]), int(value[1])] for key, value in bounds.items()}


def _path_status(label: str, path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "label": label,
        "path": str(path),
        "exists": bool(exists),
        "nonempty": bool(exists and path.is_file() and path.stat().st_size > 0),
    }


def _threshold_perturbation_report(
    cache_dir: Path,
    metadata: dict[str, Any],
    variant_keys: list[str],
) -> list[dict[str, Any]]:
    required_paths = [
        cache_dir / "physics.npy",
        cache_dir / "regime_primary.npy",
        cache_dir / "regime_primary_valid.npy",
    ]
    if not all(path.exists() for path in required_paths):
        return [
            {
                "variant_key": variant_key,
                "can_check": False,
                "reason": "physics.npy, regime_primary.npy, or regime_primary_valid.npy is missing",
            }
            for variant_key in variant_keys
        ]
    physics_names = [str(name) for name in metadata.get("physics_names", [])]
    try:
        wspd_idx = physics_names.index("Wspd")
        pab_idx = physics_names.index("Pab_mean")
    except ValueError:
        return [
            {
                "variant_key": variant_key,
                "can_check": False,
                "reason": "Wspd or Pab_mean is missing from physics_names",
            }
            for variant_key in variant_keys
        ]
    physics = np.load(cache_dir / "physics.npy", mmap_mode="r")
    canonical_regime = np.load(cache_dir / "regime_primary.npy", mmap_mode="r")
    canonical_valid = np.load(cache_dir / "regime_primary_valid.npy", mmap_mode="r").astype(bool)
    wspd = np.asarray(physics[..., wspd_idx], dtype=np.float32)
    pab = np.asarray(physics[..., pab_idx], dtype=np.float32)
    default_thresholds = metadata.get("wtb_thresholds", {})
    canonical_rated = float(default_thresholds.get("rated_wind", 10.5))
    canonical_pitch = float(default_thresholds.get("pitch_threshold", 2.0))
    rows: list[dict[str, Any]] = []
    total_valid = int(canonical_valid.sum())
    for variant_key in variant_keys:
        spec = THRESHOLD_CONTROL_SPECS[variant_key]
        rated = canonical_rated
        pitch = canonical_pitch
        if spec["setting_group"] == "rated_wind":
            rated = float(spec["setting_value"])
        elif spec["setting_group"] == "pitch_threshold":
            pitch = float(spec["setting_value"])
        wrong_regime, wrong_valid_float = compute_wtb_operation_regime(wspd, pab, rated_wind=rated, pitch_threshold=pitch)
        wrong_valid = wrong_valid_float.astype(bool)
        shared_valid = canonical_valid & wrong_valid
        dropped = canonical_valid & ~wrong_valid
        label_mismatch = shared_valid & (canonical_regime != wrong_regime)
        row: dict[str, Any] = {
            "variant_key": variant_key,
            "setting_group": spec["setting_group"],
            "setting_value": spec["setting_value"],
            "setting_label": spec["setting_label"],
            "can_check": True,
            "canonical_valid_cells": total_valid,
            "shared_valid_cells": int(shared_valid.sum()),
            "dropped_canonical_valid_cells": int(dropped.sum()),
            "drop_canonical_valid_rate": float(dropped.sum() / max(total_valid, 1)),
            "shared_label_mismatch_cells": int(label_mismatch.sum()),
            "shared_label_mismatch_rate": float(label_mismatch.sum() / max(int(shared_valid.sum()), 1)),
        }
        for regime_id, regime_name in enumerate(["idle", "mppt", "pitch_control"]):
            selector = canonical_valid & (canonical_regime == regime_id)
            denom = int(selector.sum())
            row[f"{regime_name}_canonical_valid_cells"] = denom
            row[f"{regime_name}_drop_rate"] = float((selector & ~wrong_valid).sum() / max(denom, 1))
        rows.append(row)
    return rows


def _float_matches(observed: Any, expected: float, tol: float = 1e-9) -> bool:
    try:
        return abs(float(observed) - float(expected)) <= tol
    except (TypeError, ValueError):
        return False


def _run_complete_status(run_dir: Path, variant_key: str, seed: int) -> dict[str, Any]:
    summary_path = run_dir / "training_summary.json"
    metrics_path = run_dir / "test_metrics" / "metrics.json"
    summary = load_json(summary_path) if summary_path.exists() else {}
    metrics = load_json(metrics_path) if metrics_path.exists() else {}
    spec = THRESHOLD_CONTROL_SPECS[variant_key]
    gate_alignment = metrics.get("gate_alignment", {})
    checks = {
        "summary_exists": summary_path.exists(),
        "metrics_exists": metrics_path.exists(),
        "seed_matches": int(summary.get("seed", -1)) == int(seed) if summary else False,
        "variant_key_matches": str(summary.get("variant_key", "")) == variant_key if summary else False,
        "experiment_group_is_sensitivity": str(summary.get("experiment_group", "")) == "sensitivity" if summary else False,
        "model_mode_matches": str(summary.get("model_mode", "")) == spec["mode"] if summary else False,
        "setting_group_matches": str(summary.get("setting_group", "")) == spec["setting_group"] if summary else False,
        "setting_value_matches": _float_matches(summary.get("setting_value"), float(spec["setting_value"])) if summary else False,
        "overall_rmse_present": "overall" in metrics and "rmse" in metrics.get("overall", {}),
        "switch_rmse_present": "switch_window" in metrics and "rmse" in metrics.get("switch_window", {}),
        "gate_nmi_present": "nmi" in gate_alignment,
        "gate_ari_present": "ari" in gate_alignment,
    }
    complete = all(checks.values())
    return {
        "variant_key": variant_key,
        "label": spec["label"],
        "mode": spec["mode"],
        "setting_group": spec["setting_group"],
        "setting_value": spec["setting_value"],
        "setting_label": spec["setting_label"],
        "seed": int(seed),
        "run_dir": str(run_dir),
        "complete": bool(complete),
        "checks": checks,
        "overall_rmse": metrics.get("overall", {}).get("rmse"),
        "switch_rmse": metrics.get("switch_window", {}).get("rmse"),
        "nmi": gate_alignment.get("nmi"),
        "ari": gate_alignment.get("ari"),
    }


def _read_csv_or_empty(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _first_finite(values: pd.Series | list[Any] | tuple[Any, ...]) -> float | None:
    numeric = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    if numeric.empty:
        return None
    return float(numeric.iloc[0])


def _mean_finite(values: pd.Series | list[Any] | tuple[Any, ...]) -> float | None:
    numeric = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    if numeric.empty:
        return None
    return float(numeric.mean())


def _is_int_like(value: Any) -> bool:
    try:
        int(value)
        return True
    except (TypeError, ValueError):
        return False


def _parse_float_grid(values: Iterable[float] | str | None, default: tuple[float, ...]) -> list[float]:
    if values is None:
        return [float(value) for value in default]
    if isinstance(values, str):
        return [float(token.strip()) for token in values.split(",") if token.strip()]
    return [float(value) for value in values]


def _parse_model_names(values: Iterable[str] | str | None) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, str):
        tokens = values.split(",")
    else:
        tokens = list(values)
    return {str(token).strip() for token in tokens if str(token).strip()}


def _resolve_run_dir(raw_path: Any, root_dir: Path) -> Path:
    run_dir = Path(str(raw_path))
    if run_dir.is_absolute():
        return run_dir
    return root_dir / run_dir


def _threshold_validity_run_rows(
    run_table: Path,
    *,
    root_dir: Path,
    models: Iterable[str] | str | None,
    seeds: Iterable[int] | str | None,
) -> pd.DataFrame:
    df = pd.read_csv(run_table)
    if "run_dir" not in df.columns:
        raise ValueError("threshold-label-validity-audit requires a run table with a run_dir column.")
    model_filter = _parse_model_names(models)
    if model_filter and "model" in df.columns:
        df = df[df["model"].astype(str).isin(model_filter)].copy()
    seed_list = _parse_seeds(seeds)
    if seed_list and "seed" in df.columns:
        numeric_seed = pd.to_numeric(df["seed"], errors="coerce").astype("Int64")
        df = df[numeric_seed.isin([int(seed) for seed in seed_list])].copy()
        df.loc[:, "seed"] = numeric_seed.loc[df.index]
    if df.empty:
        return df
    df = df.copy()
    df.loc[:, "_run_dir_resolved"] = df["run_dir"].map(lambda value: str(_resolve_run_dir(value, root_dir)))

    def priority(path: Any) -> int:
        text = str(path).replace("/", "\\").lower()
        if "strictmask_validation_wtb_full" in text:
            return 0
        if "strictmask_ablation_rerun_wtb_full" in text:
            return 1
        return 2

    df.loc[:, "_priority"] = df["run_dir"].map(priority)
    group_cols = [column for column in ["model", "seed"] if column in df.columns]
    if not group_cols:
        group_cols = ["_run_dir_resolved"]
    df = df.sort_values(["_priority", "_run_dir_resolved"]).drop_duplicates(group_cols, keep="first")
    return df.drop(columns=[column for column in ["_priority", "_run_dir_resolved"] if column in df.columns])


def _threshold_cache_arrays(cache_dir: Path) -> tuple[np.ndarray, dict[str, Any], int, int]:
    metadata = load_json(cache_dir / "metadata.json")
    physics = np.load(cache_dir / "physics.npy", mmap_mode="r")
    physics_names = [str(name) for name in metadata.get("physics_names", [])]
    wspd_idx = physics_names.index("Wspd") if "Wspd" in physics_names else 0
    pab_idx = physics_names.index("Pab_mean") if "Pab_mean" in physics_names else 1
    return physics, metadata, wspd_idx, pab_idx


def _gate_alignment_for_labels(
    gate_prob: np.ndarray,
    labels: np.ndarray,
    valid: np.ndarray,
) -> dict[str, Any]:
    gate_classes = max(1, min(int(gate_prob.shape[-1]), 3))
    gate_label = np.asarray(gate_prob[..., :gate_classes]).argmax(axis=-1)
    usable = np.asarray(valid, dtype=bool) & (labels >= 0) & (labels < gate_classes)
    flat_true = np.asarray(labels[usable], dtype=np.int64)
    flat_pred = np.asarray(gate_label[usable], dtype=np.int64)
    label_ids = list(range(gate_classes))
    conf = (
        confusion_matrix(flat_true, flat_pred, labels=label_ids)
        if flat_true.size
        else np.zeros((gate_classes, gate_classes), dtype=np.int64)
    )
    n_true_classes = int(np.unique(flat_true).size) if flat_true.size else 0
    return {
        "n_valid_gate": int(flat_true.size),
        "n_true_classes": n_true_classes,
        "nmi": float(normalized_mutual_info_score(flat_true, flat_pred)) if n_true_classes >= 2 else float("nan"),
        "ari": float(adjusted_rand_score(flat_true, flat_pred)) if n_true_classes >= 2 else float("nan"),
        "confusion_trace": int(np.trace(conf)),
        "confusion_total": int(conf.sum()),
    }


def _threshold_validity_one_run(
    row: pd.Series,
    *,
    root_dir: Path,
    cache_physics: np.ndarray,
    cache_metadata: dict[str, Any],
    wspd_idx: int,
    pab_idx: int,
    split: str,
    rated_grid: list[float],
    pitch_grid: list[float],
) -> list[dict[str, Any]]:
    run_dir = _resolve_run_dir(row["run_dir"], root_dir)
    metrics_dir = run_dir / f"{split}_metrics"
    required = ["gate_prob.npy", "anchor_index.npy"]
    if any(not (metrics_dir / name).exists() for name in required):
        return []
    gate = np.load(metrics_dir / "gate_prob.npy", mmap_mode="r")
    anchor_index = np.asarray(np.load(metrics_dir / "anchor_index.npy", mmap_mode="r"), dtype=np.int64)
    physics = np.asarray(cache_physics[anchor_index])
    wspd = np.asarray(physics[..., wspd_idx], dtype=np.float32)
    pab = np.asarray(physics[..., pab_idx], dtype=np.float32)
    default_thresholds = cache_metadata.get("wtb_thresholds", {})
    canonical_rated = float(default_thresholds.get("rated_wind", 10.5))
    canonical_pitch = float(default_thresholds.get("pitch_threshold", 2.0))
    canonical_regime, canonical_valid_float = compute_wtb_operation_regime(
        wspd,
        pab,
        rated_wind=canonical_rated,
        pitch_threshold=canonical_pitch,
    )
    canonical_valid = canonical_valid_float.astype(bool)
    canonical_valid_cells = int(canonical_valid.sum())
    total_cells = int(canonical_valid.size)
    rows: list[dict[str, Any]] = []
    for rated in rated_grid:
        for pitch in pitch_grid:
            labels, valid_float = compute_wtb_operation_regime(wspd, pab, rated_wind=float(rated), pitch_threshold=float(pitch))
            valid = valid_float.astype(bool)
            shared_valid = canonical_valid & valid
            label_mismatch = shared_valid & (canonical_regime != labels)
            alignment = _gate_alignment_for_labels(gate, labels, valid)
            row_out: dict[str, Any] = {
                "dataset": row.get("dataset", cache_metadata.get("dataset", "wtb")),
                "model": row.get("model", ""),
                "seed": int(row.get("seed", -1)) if _is_int_like(row.get("seed", -1)) else row.get("seed", ""),
                "variant_key": row.get("variant_key", ""),
                "experiment_group": row.get("experiment_group", ""),
                "run_dir": str(run_dir),
                "split": split,
                "rated_wind": float(rated),
                "pitch_threshold": float(pitch),
                "is_canonical_threshold": bool(
                    abs(float(rated) - canonical_rated) <= 1e-9 and abs(float(pitch) - canonical_pitch) <= 1e-9
                ),
                "canonical_rated_wind": canonical_rated,
                "canonical_pitch_threshold": canonical_pitch,
                "total_cells": total_cells,
                "valid_cells": int(valid.sum()),
                "valid_support_rate": float(valid.sum() / max(total_cells, 1)),
                "canonical_valid_cells": canonical_valid_cells,
                "shared_valid_cells": int(shared_valid.sum()),
                "shared_valid_rate": float(shared_valid.sum() / max(canonical_valid_cells, 1)),
                "shared_label_mismatch_cells": int(label_mismatch.sum()),
                "shared_label_mismatch_rate": float(label_mismatch.sum() / max(int(shared_valid.sum()), 1)),
                **alignment,
            }
            for regime_id, regime_name in enumerate(["idle", "mppt", "pitch_control", "transition"]):
                count = int(((labels == regime_id) & valid).sum())
                row_out[f"{regime_name}_cells"] = count
                row_out[f"{regime_name}_share"] = float(count / max(int(valid.sum()), 1))
            rows.append(row_out)
    return rows


def _summarize_threshold_validity(raw_df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "dataset",
        "model",
        "rated_wind",
        "pitch_threshold",
        "n_runs",
        "nmi_mean",
        "nmi_std",
        "ari_mean",
        "ari_std",
        "shared_valid_rate_mean",
        "shared_label_mismatch_rate_mean",
        "valid_cells_mean",
    ]
    if raw_df.empty:
        return pd.DataFrame(columns=columns)
    group_cols = ["dataset", "model", "rated_wind", "pitch_threshold"]
    metric_cols = [
        "nmi",
        "ari",
        "n_valid_gate",
        "valid_cells",
        "shared_valid_rate",
        "shared_label_mismatch_rate",
        "idle_share",
        "mppt_share",
        "pitch_control_share",
    ]
    rows: list[dict[str, Any]] = []
    for keys, group in raw_df.groupby(group_cols, dropna=False, sort=False):
        out = {column: value for column, value in zip(group_cols, keys)}
        out["n_runs"] = int(len(group))
        for metric in metric_cols:
            values = pd.to_numeric(group.get(metric, pd.Series(dtype=float)), errors="coerce").dropna()
            out[f"{metric}_mean"] = float(values.mean()) if not values.empty else float("nan")
            out[f"{metric}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
        rows.append(out)
    summary = pd.DataFrame(rows)
    for column in columns:
        if column not in summary.columns:
            summary[column] = pd.Series(dtype=object)
    return summary.sort_values(["model", "rated_wind", "pitch_threshold"]).reset_index(drop=True)


def _control_taxonomy_rows(
    *,
    threshold_guard_dir: Path,
    semantic_guard_dir: Path,
    boundary_negative_guard_dir: Path,
    placebo_dir: Path,
) -> list[dict[str, Any]]:
    return [
        {
            "control_name": "strict_anchor_mask",
            "control_family": "mask/threshold control",
            "purpose": "Checks that routing evidence is evaluated only on anchor-valid WTB samples.",
            "evidence_source": str(threshold_guard_dir / "threshold_controls_guard.json"),
            "semantic_negative_control": False,
        },
        {
            "control_name": "threshold_valid_support_overlap",
            "control_family": "mask/threshold control",
            "purpose": "Checks label-support and shared-valid coverage under nearby WTB rated-wind and pitch thresholds.",
            "evidence_source": "threshold_label_validity_raw.csv",
            "semantic_negative_control": False,
        },
        {
            "control_name": "extreme_wrong_threshold_sensitivity",
            "control_family": "mask/threshold control",
            "purpose": "Old extreme wrong-threshold sweeps are retained as sensitivity/mask perturbations, not as the main semantic falsification.",
            "evidence_source": str(threshold_guard_dir / "threshold_controls_guard.json"),
            "semantic_negative_control": False,
        },
        {
            "control_name": "temporal_and_spatial_placebos",
            "control_family": "semantic negative control",
            "purpose": "Temporal shifts, node permutation, within-time shuffle, and global shuffle should not copy actual routing semantics.",
            "evidence_source": str(placebo_dir),
            "semantic_negative_control": True,
        },
        {
            "control_name": "fake_shared_support_boundary_labels",
            "control_family": "semantic negative control",
            "purpose": "Fake boundary labels relabel shared support and must not preserve high agreement plus intervention effects.",
            "evidence_source": str(boundary_negative_guard_dir / "boundary_negative_controls_guard.json"),
            "semantic_negative_control": True,
        },
        {
            "control_name": "wrong_threshold_checkpoint_semantic_guard",
            "control_family": "semantic negative control",
            "purpose": "Wrong-threshold checkpoints must not reproduce canonical routing semantics and boundary-intervention drops.",
            "evidence_source": str(semantic_guard_dir / "threshold_controls_semantic_guard.json"),
            "semantic_negative_control": True,
        },
    ]


def _semantic_negative_control_state(
    *,
    model_names: set[str],
    placebo_dir: Path,
    boundary_negative_guard_dir: Path,
    semantic_guard_dir: Path,
    min_semantic_gap: float,
) -> dict[str, Any]:
    placebo_summary = _read_csv_or_empty(placebo_dir / "routing_placebo_summary.csv")
    actual_nmi = None
    max_control_nmi = None
    placebo_gap_ok = False
    if not placebo_summary.empty and {"condition", "nmi_mean"}.issubset(placebo_summary.columns):
        work = placebo_summary.copy()
        if model_names and "model" in work.columns:
            work = work[work["model"].astype(str).isin(model_names)].copy()
        actual = work[work["condition"].astype(str).eq("actual")].copy()
        controls = work[~work["condition"].astype(str).eq("actual")].copy()
        actual_nmi = _mean_finite(actual.get("nmi_mean", []))
        max_control_nmi = _first_finite([pd.to_numeric(controls.get("nmi_mean", pd.Series(dtype=float)), errors="coerce").max()])
        placebo_gap_ok = (
            actual_nmi is not None
            and max_control_nmi is not None
            and actual_nmi - max_control_nmi >= float(min_semantic_gap)
        )

    boundary_path = boundary_negative_guard_dir / "boundary_negative_controls_guard.json"
    boundary_guard = load_json(boundary_path) if boundary_path.exists() else {}
    boundary_checks = boundary_guard.get("checks", {}) if isinstance(boundary_guard.get("checks"), dict) else {}
    boundary_passed = (
        str(boundary_guard.get("status", "")) == "passed_boundary_negative_controls"
        and bool(boundary_checks.get("each_negative_control_changes_shared_labels", False))
        and bool(boundary_checks.get("no_negative_control_reproduces_high_nmi_or_ari_and_intervention_drop", False))
    )

    semantic_path = semantic_guard_dir / "threshold_controls_semantic_guard.json"
    semantic_guard = load_json(semantic_path) if semantic_path.exists() else {}
    semantic_guard_passed = str(semantic_guard.get("status", "")) == "passed_wrong_threshold_negative_control"
    return {
        "placebo_summary_exists": placebo_summary is not None and not placebo_summary.empty,
        "placebo_actual_nmi_mean": actual_nmi,
        "placebo_max_control_nmi_mean": max_control_nmi,
        "placebo_semantic_gap_ok": bool(placebo_gap_ok),
        "boundary_negative_guard_exists": boundary_path.exists(),
        "boundary_negative_guard_passed": bool(boundary_passed),
        "threshold_semantic_guard_exists": semantic_path.exists(),
        "threshold_semantic_guard_passed": bool(semantic_guard_passed),
        "semantic_negative_control_passed": bool(placebo_gap_ok or boundary_passed or semantic_guard_passed),
    }


def _fmt_metric(value: Any, digits: int = 4) -> str:
    try:
        value_float = float(value)
    except (TypeError, ValueError):
        return ""
    if not np.isfinite(value_float):
        return ""
    return f"{value_float:.{digits}f}"


def _latex_escape(value: Any) -> str:
    return (
        str(value)
        .replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("$", "\\$")
        .replace("#", "\\#")
        .replace("_", "\\_")
        .replace("{", "\\{")
        .replace("}", "\\}")
    )


def _write_threshold_validity_tex(summary_df: pd.DataFrame, output_path: Path) -> Path:
    lines = [
        "\\begin{tabular}{rrrrrr}",
        "\\toprule",
        "Rated wind & Pitch threshold & Runs & NMI & ARI & Shared valid \\\\",
        "\\midrule",
    ]
    if not summary_df.empty:
        for _, row in summary_df.sort_values(["rated_wind", "pitch_threshold"]).iterrows():
            lines.append(
                f"{_fmt_metric(row.get('rated_wind'), digits=1)} & "
                f"{_fmt_metric(row.get('pitch_threshold'), digits=1)} & "
                f"{int(row.get('n_runs', 0))} & "
                f"{_fmt_metric(row.get('nmi_mean'))} $\\pm$ {_fmt_metric(row.get('nmi_std'))} & "
                f"{_fmt_metric(row.get('ari_mean'))} $\\pm$ {_fmt_metric(row.get('ari_std'))} & "
                f"{_fmt_metric(row.get('shared_valid_rate_mean'))} \\\\"
            )
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def run_threshold_label_validity_audit(
    *,
    run_table: Path | str,
    cache_dir: Path | str,
    output_dir: Path | str,
    root_dir: Path | str = ".",
    models: Iterable[str] | str | None = None,
    seeds: Iterable[int] | str | None = None,
    split: str = "test",
    rated_wind_grid: Iterable[float] | str | None = None,
    pitch_threshold_grid: Iterable[float] | str | None = None,
    placebo_dir: Path | str = "artifacts/routing_placebo_wtb_strictmask_full",
    boundary_negative_guard_dir: Path | str = "artifacts/boundary_negative_controls_wtb",
    semantic_guard_dir: Path | str = "artifacts/strict_threshold_controls_semantic_guard_wtb_strictmask",
    threshold_guard_dir: Path | str = "artifacts/strict_threshold_controls_guard_wtb_strictmask",
    min_grid_nmi: float = 0.80,
    max_nmi_drop_from_canonical: float = 0.08,
    max_ari_drop_from_canonical: float = 0.08,
    min_shared_valid_rate: float = 0.95,
    min_semantic_gap: float = 0.10,
) -> Path:
    output_dir = ensure_dir(output_dir)
    root_dir = Path(root_dir)
    run_table = Path(run_table)
    cache_dir = Path(cache_dir)
    rated_grid = _parse_float_grid(rated_wind_grid, DEFAULT_THRESHOLD_VALIDITY_RATED_GRID)
    pitch_grid = _parse_float_grid(pitch_threshold_grid, DEFAULT_THRESHOLD_VALIDITY_PITCH_GRID)
    selected_runs = _threshold_validity_run_rows(run_table, root_dir=root_dir, models=models, seeds=seeds)
    cache_physics, cache_metadata, wspd_idx, pab_idx = _threshold_cache_arrays(cache_dir)

    raw_rows: list[dict[str, Any]] = []
    for _, row in selected_runs.iterrows():
        raw_rows.extend(
            _threshold_validity_one_run(
                row,
                root_dir=root_dir,
                cache_physics=cache_physics,
                cache_metadata=cache_metadata,
                wspd_idx=wspd_idx,
                pab_idx=pab_idx,
                split=split,
                rated_grid=rated_grid,
                pitch_grid=pitch_grid,
            )
        )
    raw_df = pd.DataFrame(raw_rows)
    if not raw_df.empty:
        canonical = raw_df[raw_df["is_canonical_threshold"].astype(bool)].copy()
        canonical_ref = canonical[["model", "seed", "nmi", "ari"]].rename(
            columns={"nmi": "canonical_nmi", "ari": "canonical_ari"}
        )
        raw_df = raw_df.merge(canonical_ref, on=["model", "seed"], how="left")
        raw_df.loc[:, "nmi_drop_from_canonical"] = raw_df["canonical_nmi"] - raw_df["nmi"]
        raw_df.loc[:, "ari_drop_from_canonical"] = raw_df["canonical_ari"] - raw_df["ari"]
        raw_df.loc[:, "conclusion_stable"] = (
            pd.to_numeric(raw_df["nmi"], errors="coerce") >= float(min_grid_nmi)
        ) & (
            pd.to_numeric(raw_df["nmi_drop_from_canonical"], errors="coerce") <= float(max_nmi_drop_from_canonical)
        ) & (
            pd.to_numeric(raw_df["ari_drop_from_canonical"], errors="coerce") <= float(max_ari_drop_from_canonical)
        )
    summary_df = _summarize_threshold_validity(raw_df)
    taxonomy = pd.DataFrame(
        _control_taxonomy_rows(
            threshold_guard_dir=Path(threshold_guard_dir),
            semantic_guard_dir=Path(semantic_guard_dir),
            boundary_negative_guard_dir=Path(boundary_negative_guard_dir),
            placebo_dir=Path(placebo_dir),
        )
    )
    model_names = _parse_model_names(models)
    if not model_names and not selected_runs.empty and "model" in selected_runs.columns:
        model_names = {str(value) for value in selected_runs["model"].dropna().astype(str).tolist()}
    semantic_state = _semantic_negative_control_state(
        model_names=model_names,
        placebo_dir=Path(placebo_dir),
        boundary_negative_guard_dir=Path(boundary_negative_guard_dir),
        semantic_guard_dir=Path(semantic_guard_dir),
        min_semantic_gap=min_semantic_gap,
    )

    raw_df.to_csv(output_dir / "threshold_label_validity_raw.csv", index=False)
    summary_df.to_csv(output_dir / "threshold_label_validity_summary.csv", index=False)
    taxonomy.to_csv(output_dir / "control_taxonomy.csv", index=False)
    _write_threshold_validity_tex(summary_df, output_dir / "table_threshold_label_validity.tex")

    expected_grid_cells = int(len(rated_grid) * len(pitch_grid))
    expected_runs = int(len(selected_runs))
    complete_grid_cells = (
        int(summary_df[["rated_wind", "pitch_threshold"]].drop_duplicates().shape[0]) if not summary_df.empty else 0
    )
    canonical_present = bool(raw_df["is_canonical_threshold"].astype(bool).any()) if not raw_df.empty else False
    support_ok = bool(
        not raw_df.empty
        and pd.to_numeric(raw_df["shared_valid_rate"], errors="coerce").dropna().min() >= float(min_shared_valid_rate)
    )
    conclusion_stable = bool(not raw_df.empty and raw_df["conclusion_stable"].astype(bool).all())
    min_nmi = _first_finite([pd.to_numeric(raw_df.get("nmi", pd.Series(dtype=float)), errors="coerce").min()])
    max_nmi_drop = _first_finite(
        [pd.to_numeric(raw_df.get("nmi_drop_from_canonical", pd.Series(dtype=float)), errors="coerce").max()]
    )
    max_ari_drop = _first_finite(
        [pd.to_numeric(raw_df.get("ari_drop_from_canonical", pd.Series(dtype=float)), errors="coerce").max()]
    )
    checks = {
        "selected_runs_present": expected_runs > 0,
        "all_grid_cells_present": complete_grid_cells == expected_grid_cells and expected_grid_cells == 9,
        "canonical_threshold_present": canonical_present,
        "support_does_not_collapse": support_ok,
        "routing_recovery_conclusion_stable": conclusion_stable,
        "control_taxonomy_separates_mask_and_semantic_controls": bool(
            set(taxonomy["control_family"].astype(str)) == {"mask/threshold control", "semantic negative control"}
        ),
        "semantic_negative_control_passed": bool(semantic_state["semantic_negative_control_passed"]),
    }
    if not checks["selected_runs_present"]:
        status = "blocked_missing_threshold_validity_runs"
    elif not checks["all_grid_cells_present"]:
        status = "blocked_incomplete_threshold_validity_grid"
    elif not checks["canonical_threshold_present"]:
        status = "blocked_missing_canonical_threshold"
    elif not checks["support_does_not_collapse"]:
        status = "blocked_threshold_validity_support_collapse"
    elif not checks["routing_recovery_conclusion_stable"]:
        status = "blocked_threshold_validity_conclusion_changed"
    elif not checks["semantic_negative_control_passed"]:
        status = "blocked_missing_semantic_negative_control"
    else:
        status = "passed_threshold_label_validity_audit"
    report = {
        "status": status,
        "checks": checks,
        "run_table": str(run_table),
        "cache_dir": str(cache_dir),
        "split": split,
        "models": sorted(model_names),
        "seeds": _parse_seeds(seeds),
        "rated_wind_grid": rated_grid,
        "pitch_threshold_grid": pitch_grid,
        "expected_runs": expected_runs,
        "expected_grid_cells": expected_grid_cells,
        "complete_grid_cells": complete_grid_cells,
        "thresholds": {
            "min_grid_nmi": float(min_grid_nmi),
            "max_nmi_drop_from_canonical": float(max_nmi_drop_from_canonical),
            "max_ari_drop_from_canonical": float(max_ari_drop_from_canonical),
            "min_shared_valid_rate": float(min_shared_valid_rate),
            "min_semantic_gap": float(min_semantic_gap),
        },
        "observed": {
            "min_nmi": min_nmi,
            "max_nmi_drop_from_canonical": max_nmi_drop,
            "max_ari_drop_from_canonical": max_ari_drop,
            "min_shared_valid_rate": _first_finite(
                [pd.to_numeric(raw_df.get("shared_valid_rate", pd.Series(dtype=float)), errors="coerce").min()]
            ),
        },
        "semantic_negative_controls": semantic_state,
        "paths": {
            "raw_csv": str(output_dir / "threshold_label_validity_raw.csv"),
            "summary_csv": str(output_dir / "threshold_label_validity_summary.csv"),
            "control_taxonomy_csv": str(output_dir / "control_taxonomy.csv"),
            "tex_table": str(output_dir / "table_threshold_label_validity.tex"),
            "guard_json": str(output_dir / "threshold_label_validity_guard.json"),
        },
    }
    save_json(output_dir / "threshold_label_validity_guard.json", report)
    lines = [
        "# Threshold/label validity audit",
        "",
        f"Status: `{status}`",
        "",
        "This audit re-labels the saved WTB gate outputs across nearby rated-wind and pitch thresholds. It is a label-validity sensitivity check, not a new training run and not the semantic negative control itself.",
        "",
        "## Checks",
        "",
    ]
    for key, value in checks.items():
        lines.append(f"- {key}: `{bool(value)}`")
    lines.extend(
        [
            "",
            "## Control taxonomy",
            "",
            "Mask/threshold controls check support and label-stability; semantic negative controls deliberately break routing semantics.",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_dir


def _complete_pairs_from_mechanism_raw(
    raw_df: pd.DataFrame,
    variant_keys: list[str],
    seed_list: list[int],
    intervention: str = DEFAULT_THRESHOLD_SEMANTIC_INTERVENTION,
) -> pd.DataFrame:
    columns = [
        "variant_key",
        "seed",
        "run_dir",
        "actual_nmi",
        "actual_ari",
        "intervention_nmi",
        "intervention_ari",
        "drop_nmi",
        "drop_ari",
        "actual_replay_status",
        "has_pair",
    ]
    if raw_df.empty:
        return pd.DataFrame(columns=columns)
    work = raw_df.copy()
    if "variant_key" in work.columns:
        work = work[work["variant_key"].astype(str).isin(set(variant_keys))].copy()
    if "seed" in work.columns:
        work["seed"] = pd.to_numeric(work["seed"], errors="coerce").astype("Int64")
        work = work[work["seed"].isin([int(seed) for seed in seed_list])].copy()
    if work.empty:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, Any]] = []
    key_cols = ["variant_key", "seed", "run_dir"]
    for keys, group in work.groupby(key_cols, dropna=False, sort=False):
        variant_key, seed, run_dir = keys
        actual = group[group["intervention"].astype(str) == "actual"].copy()
        perturbed = group[group["intervention"].astype(str) == intervention].copy()
        actual_nmi = _first_finite(actual.get("nmi", []))
        actual_ari = _first_finite(actual.get("ari", []))
        intervention_nmi = _first_finite(perturbed.get("nmi", []))
        intervention_ari = _first_finite(perturbed.get("ari", []))
        replay_status = ""
        if not actual.empty and "replay_status" in actual.columns:
            replay_status = str(actual["replay_status"].dropna().astype(str).iloc[0]) if not actual["replay_status"].dropna().empty else ""
        has_pair = actual_nmi is not None and intervention_nmi is not None
        rows.append(
            {
                "variant_key": str(variant_key),
                "seed": int(seed) if pd.notna(seed) else "",
                "run_dir": str(run_dir),
                "actual_nmi": actual_nmi,
                "actual_ari": actual_ari,
                "intervention_nmi": intervention_nmi,
                "intervention_ari": intervention_ari,
                "drop_nmi": (actual_nmi - intervention_nmi) if has_pair else None,
                "drop_ari": (actual_ari - intervention_ari)
                if actual_ari is not None and intervention_ari is not None
                else None,
                "actual_replay_status": replay_status,
                "has_pair": bool(has_pair),
            }
        )
    pair_df = pd.DataFrame(rows)
    for column in columns:
        if column not in pair_df.columns:
            pair_df[column] = pd.Series(dtype=object)
    return pair_df[columns]


def _summarize_semantic_pairs(pair_df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "variant_key",
        "n_runs",
        "actual_nmi_mean",
        "actual_nmi_std",
        "drop_nmi_mean",
        "drop_nmi_std",
        "actual_ari_mean",
        "drop_ari_mean",
        "dangerous_semantic_runs",
    ]
    if pair_df.empty:
        return pd.DataFrame(columns=columns)
    rows: list[dict[str, Any]] = []
    for variant_key, group in pair_df.groupby("variant_key", dropna=False, sort=False):
        complete = group[group["has_pair"].astype(bool)].copy()
        row: dict[str, Any] = {"variant_key": str(variant_key), "n_runs": int(len(complete))}
        for metric in ["actual_nmi", "drop_nmi", "actual_ari", "drop_ari"]:
            values = pd.to_numeric(complete.get(metric), errors="coerce").dropna()
            row[f"{metric}_mean"] = float(values.mean()) if not values.empty else float("nan")
            row[f"{metric}_std"] = float(values.std(ddof=0)) if len(values) > 1 else 0.0
        row["dangerous_semantic_runs"] = 0
        rows.append(row)
    summary = pd.DataFrame(rows)
    for column in columns:
        if column not in summary.columns:
            summary[column] = pd.Series(dtype=object)
    return summary[columns]


def _load_positive_mechanism_reference(
    positive_mechanism_dir: Path,
    intervention: str = DEFAULT_THRESHOLD_SEMANTIC_INTERVENTION,
) -> dict[str, Any]:
    summary_df = _read_csv_or_empty(positive_mechanism_dir / "mechanism_intervention_summary.csv")
    effects_df = _read_csv_or_empty(positive_mechanism_dir / "mechanism_intervention_effects.csv")
    actual = summary_df[summary_df.get("intervention", pd.Series(dtype=str)).astype(str) == "actual"].copy()
    effect = effects_df[effects_df.get("intervention", pd.Series(dtype=str)).astype(str) == intervention].copy()
    return {
        "actual_nmi_mean": _mean_finite(actual.get("nmi_mean", [])),
        "actual_ari_mean": _mean_finite(actual.get("ari_mean", [])),
        "boundary_drop_nmi_mean": _mean_finite(effect.get("drop_nmi_mean", [])),
        "boundary_drop_ari_mean": _mean_finite(effect.get("drop_ari_mean", [])),
        "n_actual_runs": int(_mean_finite(actual.get("n_runs", [])) or 0),
        "n_effect_runs": int(_mean_finite(effect.get("n_runs", [])) or 0),
        "summary_path": str(positive_mechanism_dir / "mechanism_intervention_summary.csv"),
        "effects_path": str(positive_mechanism_dir / "mechanism_intervention_effects.csv"),
    }


def run_threshold_controls_semantic_guard(
    output_dir: Path | str,
    mechanism_dir: Path | str = "artifacts/strictmask_threshold_controls_mechanism",
    positive_mechanism_dir: Path | str = "artifacts/mechanism_gate_wtb_strictmask_full/mechanism_intervention",
    variant_keys: Iterable[str] | str | None = None,
    seeds: Iterable[int] | str | None = None,
    intervention: str = DEFAULT_THRESHOLD_SEMANTIC_INTERVENTION,
    max_wrong_actual_nmi: float = 0.75,
    max_wrong_boundary_drop_nmi: float = 0.60,
    min_positive_actual_nmi: float = 0.75,
    min_positive_boundary_drop_nmi: float = 0.40,
    min_nmi_gap_from_positive: float = 0.10,
    min_boundary_drop_gap_from_positive: float = 0.10,
) -> Path:
    output_dir = ensure_dir(output_dir)
    mechanism_dir = Path(mechanism_dir)
    positive_mechanism_dir = Path(positive_mechanism_dir)
    variant_key_list = _parse_variant_keys(variant_keys)
    seed_list = _parse_seeds(seeds)
    raw_path = mechanism_dir / "mechanism_intervention_raw.csv"
    raw_df = _read_csv_or_empty(raw_path)
    pair_df = _complete_pairs_from_mechanism_raw(raw_df, variant_key_list, seed_list, intervention=intervention)
    pair_df.to_csv(output_dir / "threshold_controls_semantic_pairs.csv", index=False)
    summary_df = _summarize_semantic_pairs(pair_df)

    expected_runs = int(len(variant_key_list) * len(seed_list))
    complete_pairs = int(pair_df["has_pair"].astype(bool).sum()) if not pair_df.empty else 0
    positive = _load_positive_mechanism_reference(positive_mechanism_dir, intervention=intervention)
    positive_actual_nmi = positive["actual_nmi_mean"]
    positive_boundary_drop_nmi = positive["boundary_drop_nmi_mean"]

    if not pair_df.empty:
        dangerous = (
            pair_df["has_pair"].astype(bool)
            & (pd.to_numeric(pair_df["actual_nmi"], errors="coerce") >= float(max_wrong_actual_nmi))
            & (pd.to_numeric(pair_df["drop_nmi"], errors="coerce") >= float(max_wrong_boundary_drop_nmi))
        )
        pair_df.loc[:, "dangerous_semantic_copy"] = dangerous.astype(bool)
        pair_df.to_csv(output_dir / "threshold_controls_semantic_pairs.csv", index=False)
        danger_by_variant = pair_df.groupby("variant_key", dropna=False)["dangerous_semantic_copy"].sum().to_dict()
        summary_df.loc[:, "dangerous_semantic_runs"] = summary_df["variant_key"].map(
            lambda key: int(danger_by_variant.get(key, 0))
        )
    else:
        summary_df.loc[:, "dangerous_semantic_runs"] = pd.Series(dtype=int)
    summary_df.to_csv(output_dir / "threshold_controls_semantic_summary.csv", index=False)

    max_wrong_actual = _mean_finite([pd.to_numeric(pair_df.get("actual_nmi", pd.Series(dtype=float)), errors="coerce").max()])
    max_wrong_drop = _mean_finite([pd.to_numeric(pair_df.get("drop_nmi", pd.Series(dtype=float)), errors="coerce").max()])
    positive_reference_ready = (
        positive_actual_nmi is not None
        and positive_boundary_drop_nmi is not None
        and positive_actual_nmi >= float(min_positive_actual_nmi)
        and positive_boundary_drop_nmi >= float(min_positive_boundary_drop_nmi)
    )
    nmi_gap_ok = (
        positive_actual_nmi is not None
        and max_wrong_actual is not None
        and positive_actual_nmi - max_wrong_actual >= float(min_nmi_gap_from_positive)
    )
    boundary_drop_gap_ok = (
        positive_boundary_drop_nmi is not None
        and max_wrong_drop is not None
        and positive_boundary_drop_nmi - max_wrong_drop >= float(min_boundary_drop_gap_from_positive)
    )
    no_dangerous_copy = bool(
        pair_df.empty
        or "dangerous_semantic_copy" not in pair_df.columns
        or not pair_df["dangerous_semantic_copy"].astype(bool).any()
    )
    checks = {
        "mechanism_raw_exists": raw_path.exists(),
        "all_expected_semantic_pairs_present": complete_pairs == expected_runs and expected_runs > 0,
        "positive_reference_ready": positive_reference_ready,
        "wrong_threshold_actual_nmi_below_positive": bool(nmi_gap_ok),
        "wrong_threshold_boundary_drop_below_positive": bool(boundary_drop_gap_ok),
        "no_wrong_threshold_run_reproduces_both_semantics": no_dangerous_copy,
    }
    if not checks["mechanism_raw_exists"]:
        status = "blocked_missing_threshold_mechanism_raw"
    elif not checks["all_expected_semantic_pairs_present"]:
        status = "blocked_incomplete_threshold_semantic_pairs"
    elif not checks["positive_reference_ready"]:
        status = "blocked_positive_reference_not_ready"
    elif not checks["wrong_threshold_actual_nmi_below_positive"]:
        status = "failed_wrong_threshold_preserves_canonical_routing"
    elif not checks["wrong_threshold_boundary_drop_below_positive"]:
        status = "failed_wrong_threshold_preserves_intervention_effect"
    elif not checks["no_wrong_threshold_run_reproduces_both_semantics"]:
        status = "failed_wrong_threshold_semantic_copy"
    else:
        status = "passed_wrong_threshold_negative_control"

    report = {
        "status": status,
        "checks": checks,
        "expected_runs": expected_runs,
        "complete_pairs": complete_pairs,
        "variants": variant_key_list,
        "seeds": seed_list,
        "intervention": intervention,
        "thresholds": {
            "max_wrong_actual_nmi": float(max_wrong_actual_nmi),
            "max_wrong_boundary_drop_nmi": float(max_wrong_boundary_drop_nmi),
            "min_positive_actual_nmi": float(min_positive_actual_nmi),
            "min_positive_boundary_drop_nmi": float(min_positive_boundary_drop_nmi),
            "min_nmi_gap_from_positive": float(min_nmi_gap_from_positive),
            "min_boundary_drop_gap_from_positive": float(min_boundary_drop_gap_from_positive),
        },
        "positive_reference": positive,
        "observed": {
            "max_wrong_actual_nmi": max_wrong_actual,
            "max_wrong_boundary_drop_nmi": max_wrong_drop,
            "positive_minus_max_wrong_actual_nmi": (positive_actual_nmi - max_wrong_actual)
            if positive_actual_nmi is not None and max_wrong_actual is not None
            else None,
            "positive_minus_max_wrong_boundary_drop_nmi": (positive_boundary_drop_nmi - max_wrong_drop)
            if positive_boundary_drop_nmi is not None and max_wrong_drop is not None
            else None,
        },
        "paths": {
            "mechanism_raw": str(raw_path),
            "positive_mechanism_dir": str(positive_mechanism_dir),
            "pair_csv": str(output_dir / "threshold_controls_semantic_pairs.csv"),
            "summary_csv": str(output_dir / "threshold_controls_semantic_summary.csv"),
        },
    }
    save_json(output_dir / "threshold_controls_semantic_guard.json", report)
    lines = [
        "# Wrong-threshold semantic negative-control guard",
        "",
        f"Status: `{status}`",
        "",
        "This guard replays wrong-threshold checkpoints against canonical strict-cache labels and checks whether they fail to reproduce the canonical routing semantics and boundary-intervention effect.",
        "",
        "## Completion",
        "",
        f"- Expected paired semantic runs: `{expected_runs}`",
        f"- Complete paired semantic runs: `{complete_pairs}`",
        f"- Tested intervention: `{intervention}`",
        "",
        "## Positive Reference",
        "",
        f"- Actual NMI mean: `{positive_actual_nmi}`",
        f"- Boundary drop-NMI mean: `{positive_boundary_drop_nmi}`",
        "",
        "## Wrong-Threshold Extremes",
        "",
        f"- Max canonical actual NMI: `{max_wrong_actual}`",
        f"- Max canonical boundary drop-NMI: `{max_wrong_drop}`",
        "",
        "## Checks",
        "",
    ]
    for key, value in checks.items():
        lines.append(f"- {key}: `{bool(value)}`")
    lines.append("")
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return output_dir


def run_threshold_controls_guard(
    output_dir: Path | str,
    root_dir: Path | str = ".",
    cache_root: str = "artifacts/cache_strictmask",
    suite_dir: Path | str = "artifacts/strictmask_threshold_controls_wtb",
    train_days: int = 180,
    val_days: int = 30,
    test_days: int = 35,
    hist_len: int = 36,
    pred_len: int = 24,
    variant_keys: Iterable[str] | str | None = None,
    seeds: Iterable[int] | str | None = None,
) -> Path:
    output_dir = ensure_dir(output_dir)
    suite_dir = Path(suite_dir)
    variant_key_list = _parse_variant_keys(variant_keys)
    seed_list = _parse_seeds(seeds)
    config = DataConfig(
        dataset="wtb",
        root_dir=Path(root_dir),
        cache_root=cache_root,
        train_days=int(train_days),
        val_days=int(val_days),
        test_days=int(test_days),
        hist_len=int(hist_len),
        pred_len=int(pred_len),
    )
    expected_bounds = _jsonable_bounds(config.split_bounds())
    cache_dir = config.cache_dir()
    metadata_path = cache_dir / "metadata.json"
    metadata = load_json(metadata_path) if metadata_path.exists() else {}
    cache_bounds = _jsonable_bounds(metadata.get("split_bounds", {})) if metadata else {}
    anchor_report = strict_anchor_mask_report(cache_dir, metadata) if metadata else {"can_check": False}
    perturbation_rows = _threshold_perturbation_report(cache_dir, metadata, variant_key_list) if metadata else []
    pd.DataFrame(perturbation_rows).to_csv(output_dir / "threshold_controls_evidence_perturbation_audit.csv", index=False)
    perturbation_checked = bool(perturbation_rows) and all(bool(row.get("can_check")) for row in perturbation_rows)
    support_perturbation_present = bool(perturbation_rows) and all(
        float(row.get("drop_canonical_valid_rate", 0.0) or 0.0) >= 0.05
        or float(row.get("shared_label_mismatch_rate", 0.0) or 0.0) >= 0.05
        for row in perturbation_rows
    )
    shared_label_perturbation_present = bool(perturbation_rows) and all(
        float(row.get("shared_label_mismatch_rate", 0.0) or 0.0) >= 0.05
        for row in perturbation_rows
    )
    perturbation_rows = _threshold_perturbation_report(cache_dir, metadata, variant_key_list) if metadata else []
    pd.DataFrame(perturbation_rows).to_csv(output_dir / "threshold_controls_perturbation_audit.csv", index=False)
    perturbation_checked = bool(perturbation_rows) and all(bool(row.get("can_check")) for row in perturbation_rows)
    support_perturbation_present = bool(perturbation_rows) and all(
        float(row.get("drop_canonical_valid_rate", 0.0) or 0.0) >= 0.05
        or float(row.get("shared_label_mismatch_rate", 0.0) or 0.0) >= 0.05
        for row in perturbation_rows
    )
    shared_label_perturbation_present = bool(perturbation_rows) and all(
        float(row.get("shared_label_mismatch_rate", 0.0) or 0.0) >= 0.05
        for row in perturbation_rows
    )
    run_status = [
        _run_complete_status(Path(suite_dir) / f"wtb_{variant_key}_seed{seed}", variant_key, seed)
        for variant_key in variant_key_list
        for seed in seed_list
    ]
    complete_runs = int(sum(1 for row in run_status if row["complete"]))
    expected_runs = int(len(run_status))
    missing_runs = expected_runs - complete_runs
    run_df = pd.DataFrame(
        [
            {
                "variant_key": row["variant_key"],
                "label": row["label"],
                "mode": row["mode"],
                "setting_group": row["setting_group"],
                "setting_value": row["setting_value"],
                "setting_label": row["setting_label"],
                "seed": row["seed"],
                "run_dir": row["run_dir"],
                "complete": row["complete"],
                "overall_rmse": row["overall_rmse"],
                "switch_rmse": row["switch_rmse"],
                "nmi": row["nmi"],
                "ari": row["ari"],
                **{f"check_{key}": value for key, value in row["checks"].items()},
            }
            for row in run_status
        ]
    )
    run_df.to_csv(output_dir / "threshold_controls_run_status.csv", index=False)
    required_variants = set(DEFAULT_THRESHOLD_CONTROL_VARIANTS)
    threshold_controls_included = required_variants.issubset(set(variant_key_list))
    checks = {
        "cache_metadata_exists": metadata_path.exists(),
        "cache_bounds_match_requested": cache_bounds == expected_bounds,
        "cache_has_strict_anchor_patch_marker": bool(metadata.get("strict_anchor_mask_patch")),
        "cache_strict_anchor_check_ran": bool(anchor_report.get("can_check")),
        "cache_strict_anchor_violations_zero": anchor_report.get("strict_anchor_violations") == 0,
        "wrong_threshold_control_variants_included": threshold_controls_included,
        "wrong_threshold_perturbation_check_ran": perturbation_checked,
        "wrong_thresholds_create_semantic_perturbation": support_perturbation_present,
        "wrong_thresholds_change_shared_labels": shared_label_perturbation_present,
        "wrong_thresholds_are_mask_only_controls": bool(support_perturbation_present and not shared_label_perturbation_present),
        "all_expected_runs_complete": missing_runs == 0 and expected_runs > 0,
    }
    if not checks["cache_metadata_exists"]:
        status = "blocked_cache_missing"
    elif not checks["cache_bounds_match_requested"]:
        status = "blocked_cache_split_mismatch"
    elif not checks["cache_has_strict_anchor_patch_marker"] or not checks["cache_strict_anchor_violations_zero"]:
        status = "blocked_cache_not_strict_anchor_masked"
    elif not checks["wrong_threshold_control_variants_included"]:
        status = "blocked_missing_wrong_threshold_controls"
    elif not checks["wrong_threshold_perturbation_check_ran"] or not checks["wrong_thresholds_create_semantic_perturbation"]:
        status = "blocked_wrong_thresholds_not_semantic_controls"
    elif missing_runs > 0:
        status = "ready_to_execute_training"
    else:
        status = "complete_ready_for_threshold_control_table"
    report = {
        "status": status,
        "checks": checks,
        "expected_runs": expected_runs,
        "complete_runs": complete_runs,
        "missing_runs": missing_runs,
        "variants": variant_key_list,
        "seeds": seed_list,
        "expected_bounds": expected_bounds,
        "cache_bounds": cache_bounds,
        "anchor_mask_report": anchor_report,
        "threshold_perturbation_summary": perturbation_rows,
        "paths": {
            "cache_metadata": str(metadata_path),
            "suite_dir": str(suite_dir),
            "run_status_csv": str(output_dir / "threshold_controls_run_status.csv"),
            "perturbation_audit_csv": str(output_dir / "threshold_controls_perturbation_audit.csv"),
        },
    }
    save_json(output_dir / "threshold_controls_guard.json", report)
    lines = [
        "# Strict-cache threshold-control guard",
        "",
        f"Status: `{status}`",
        "",
        "This guard prevents missing or legacy threshold-sensitivity rows from being used as mechanism negative controls.",
        "",
        "## Required wrong-threshold controls",
        "",
    ]
    for variant_key in DEFAULT_THRESHOLD_CONTROL_VARIANTS:
        spec = THRESHOLD_CONTROL_SPECS[variant_key]
        lines.append(f"- {variant_key}: `{spec['setting_label']}`")
    lines.extend(["", "## Checks", ""])
    for key, value in checks.items():
        lines.append(f"- {key}: `{bool(value)}`")
    lines.extend(
        [
            "",
            "## Run Completion",
            "",
            f"- Expected runs: `{expected_runs}`",
            f"- Complete runs: `{complete_runs}`",
            f"- Missing or incomplete runs: `{missing_runs}`",
            "",
            "## Threshold Perturbation",
            "",
            f"- Perturbation check ran: `{perturbation_checked}`",
            f"- Support perturbation present: `{support_perturbation_present}`",
            f"- Shared-label perturbation present: `{shared_label_perturbation_present}`",
            "",
            "## Anchor-Mask Report",
            "",
            "```json",
            json.dumps(anchor_report, indent=2),
            "```",
            "",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return output_dir


def run_threshold_controls_evidence_guard(
    output_dir: Path | str,
    root_dir: Path | str = ".",
    cache_root: str = "artifacts/cache_strictmask",
    suite_dir: Path | str = "artifacts/strictmask_threshold_controls_wtb",
    reviewer_pack_dir: Path | str = "artifacts/strictmask_threshold_controls_reviewer_stats",
    semantic_guard_dir: Path | str = "artifacts/strict_threshold_controls_semantic_guard_wtb_strictmask",
    boundary_negative_guard_dir: Path | str = "artifacts/boundary_negative_controls_wtb",
    train_days: int = 180,
    val_days: int = 30,
    test_days: int = 35,
    hist_len: int = 36,
    pred_len: int = 24,
    variant_keys: Iterable[str] | str | None = None,
    seeds: Iterable[int] | str | None = None,
) -> Path:
    output_dir = ensure_dir(output_dir)
    suite_dir = Path(suite_dir)
    reviewer_pack_dir = Path(reviewer_pack_dir)
    semantic_guard_dir = Path(semantic_guard_dir)
    boundary_negative_guard_dir = Path(boundary_negative_guard_dir)
    variant_key_list = _parse_variant_keys(variant_keys)
    seed_list = _parse_seeds(seeds)
    config = DataConfig(
        dataset="wtb",
        root_dir=Path(root_dir),
        cache_root=cache_root,
        train_days=int(train_days),
        val_days=int(val_days),
        test_days=int(test_days),
        hist_len=int(hist_len),
        pred_len=int(pred_len),
    )
    expected_bounds = _jsonable_bounds(config.split_bounds())
    cache_dir = config.cache_dir()
    metadata_path = cache_dir / "metadata.json"
    metadata = load_json(metadata_path) if metadata_path.exists() else {}
    cache_bounds = _jsonable_bounds(metadata.get("split_bounds", {})) if metadata else {}
    anchor_report = strict_anchor_mask_report(cache_dir, metadata) if metadata else {"can_check": False}
    perturbation_rows = _threshold_perturbation_report(cache_dir, metadata, variant_key_list) if metadata else []
    pd.DataFrame(perturbation_rows).to_csv(output_dir / "threshold_controls_evidence_perturbation_audit.csv", index=False)
    perturbation_checked = bool(perturbation_rows) and all(bool(row.get("can_check")) for row in perturbation_rows)
    support_perturbation_present = bool(perturbation_rows) and all(
        float(row.get("drop_canonical_valid_rate", 0.0) or 0.0) >= 0.05
        or float(row.get("shared_label_mismatch_rate", 0.0) or 0.0) >= 0.05
        for row in perturbation_rows
    )
    shared_label_perturbation_present = bool(perturbation_rows) and all(
        float(row.get("shared_label_mismatch_rate", 0.0) or 0.0) >= 0.05
        for row in perturbation_rows
    )
    run_status = [
        _run_complete_status(suite_dir / f"wtb_{variant_key}_seed{seed}", variant_key, seed)
        for variant_key in variant_key_list
        for seed in seed_list
    ]
    complete_runs = int(sum(1 for row in run_status if row["complete"]))
    expected_runs = int(len(run_status))
    missing_runs = expected_runs - complete_runs
    pd.DataFrame(
        [
            {
                "variant_key": row["variant_key"],
                "label": row["label"],
                "mode": row["mode"],
                "setting_group": row["setting_group"],
                "setting_value": row["setting_value"],
                "setting_label": row["setting_label"],
                "seed": row["seed"],
                "run_dir": row["run_dir"],
                "complete": row["complete"],
                "overall_rmse": row["overall_rmse"],
                "switch_rmse": row["switch_rmse"],
                "nmi": row["nmi"],
                "ari": row["ari"],
                **{f"check_{key}": value for key, value in row["checks"].items()},
            }
            for row in run_status
        ]
    ).to_csv(output_dir / "threshold_controls_evidence_run_status.csv", index=False)
    reviewer_file_status = [
        _path_status(f"reviewer_stat_pack/{filename}", reviewer_pack_dir / filename)
        for filename in REVIEWER_STAT_REQUIRED_FILES
    ]
    semantic_file_status = [
        _path_status(f"semantic_guard/{filename}", semantic_guard_dir / filename)
        for filename in THRESHOLD_SEMANTIC_REQUIRED_FILES
    ]
    file_status = reviewer_file_status + semantic_file_status
    pd.DataFrame(file_status).to_csv(output_dir / "threshold_controls_evidence_file_status.csv", index=False)
    reviewer_config_path = reviewer_pack_dir / "reviewer_stat_pack_config.json"
    reviewer_config = load_json(reviewer_config_path) if reviewer_config_path.exists() else {}
    reviewer_runs = int(reviewer_config.get("n_runs", 0)) if reviewer_config else 0
    semantic_guard_path = semantic_guard_dir / "threshold_controls_semantic_guard.json"
    semantic_guard = load_json(semantic_guard_path) if semantic_guard_path.exists() else {}
    semantic_status = str(semantic_guard.get("status", "")) if semantic_guard else ""
    semantic_pairs = int(semantic_guard.get("complete_pairs", 0)) if semantic_guard else 0
    boundary_negative_guard_path = boundary_negative_guard_dir / "boundary_negative_controls_guard.json"
    boundary_negative_guard = load_json(boundary_negative_guard_path) if boundary_negative_guard_path.exists() else {}
    boundary_negative_status = str(boundary_negative_guard.get("status", "")) if boundary_negative_guard else ""
    boundary_negative_checks = boundary_negative_guard.get("checks", {}) if isinstance(boundary_negative_guard.get("checks"), dict) else {}
    boundary_negative_relabels = bool(boundary_negative_checks.get("each_negative_control_changes_shared_labels", False))
    boundary_negative_no_dangerous_copy = bool(
        boundary_negative_checks.get("no_negative_control_reproduces_high_nmi_or_ari_and_intervention_drop", False)
    )
    boundary_negative_passed = (
        boundary_negative_status == "passed_boundary_negative_controls"
        and boundary_negative_relabels
        and boundary_negative_no_dangerous_copy
    )
    required_variants = set(DEFAULT_THRESHOLD_CONTROL_VARIANTS)
    threshold_controls_included = required_variants.issubset(set(variant_key_list))
    semantic_negative_control_passed = semantic_status == "passed_wrong_threshold_negative_control" or boundary_negative_passed
    checks = {
        "cache_metadata_exists": metadata_path.exists(),
        "cache_bounds_match_requested": cache_bounds == expected_bounds,
        "cache_has_strict_anchor_patch_marker": bool(metadata.get("strict_anchor_mask_patch")) if metadata else False,
        "cache_strict_anchor_check_ran": bool(anchor_report.get("can_check")),
        "cache_strict_anchor_violations_zero": anchor_report.get("strict_anchor_violations") == 0,
        "wrong_threshold_control_variants_included": threshold_controls_included,
        "wrong_threshold_perturbation_check_ran": perturbation_checked,
        "wrong_thresholds_create_semantic_perturbation": support_perturbation_present,
        "wrong_thresholds_change_shared_labels": shared_label_perturbation_present,
        "wrong_thresholds_are_mask_only_controls": bool(support_perturbation_present and not shared_label_perturbation_present),
        "all_expected_runs_complete": missing_runs == 0 and expected_runs > 0,
        "all_required_reviewer_files_present": all(row["exists"] and row["nonempty"] for row in reviewer_file_status),
        "all_required_semantic_guard_files_present": all(row["exists"] and row["nonempty"] for row in semantic_file_status),
        "boundary_negative_guard_present": boundary_negative_guard_path.exists(),
        "boundary_negative_guard_passed": boundary_negative_passed,
        "boundary_negative_controls_relabel_shared_labels": boundary_negative_relabels,
        "boundary_negative_controls_no_dangerous_copy": boundary_negative_no_dangerous_copy,
        "reviewer_pack_covers_expected_runs": reviewer_runs >= expected_runs and expected_runs > 0,
        "semantic_guard_passed": semantic_status == "passed_wrong_threshold_negative_control",
        "semantic_negative_control_passed": semantic_negative_control_passed,
        "semantic_guard_covers_expected_runs": semantic_pairs >= expected_runs and expected_runs > 0,
    }
    if not checks["cache_metadata_exists"]:
        status = "blocked_cache_missing"
    elif not checks["cache_bounds_match_requested"]:
        status = "blocked_cache_split_mismatch"
    elif not checks["cache_has_strict_anchor_patch_marker"] or not checks["cache_strict_anchor_violations_zero"]:
        status = "blocked_cache_not_strict_anchor_masked"
    elif not checks["wrong_threshold_control_variants_included"]:
        status = "blocked_missing_wrong_threshold_controls"
    elif not checks["wrong_threshold_perturbation_check_ran"] or not checks["wrong_thresholds_create_semantic_perturbation"]:
        status = "blocked_wrong_thresholds_not_semantic_controls"
    elif missing_runs > 0:
        status = "queued_or_in_progress" if complete_runs > 0 else "ready_to_execute_training"
    elif not checks["all_required_reviewer_files_present"]:
        status = "blocked_missing_threshold_reviewer_pack"
    elif not checks["reviewer_pack_covers_expected_runs"]:
        status = "blocked_threshold_reviewer_pack_incomplete"
    elif not checks["all_required_semantic_guard_files_present"] and not checks["boundary_negative_guard_present"]:
        status = "blocked_missing_threshold_semantic_negative_control"
    elif not checks["semantic_negative_control_passed"]:
        status = "blocked_threshold_semantic_negative_control_not_passed"
    elif checks["semantic_guard_passed"] and not checks["semantic_guard_covers_expected_runs"]:
        status = "blocked_threshold_semantic_negative_control_incomplete"
    else:
        status = "complete_ready_for_threshold_control_evidence"
    report = {
        "status": status,
        "checks": checks,
        "expected_runs": expected_runs,
        "complete_runs": complete_runs,
        "missing_runs": missing_runs,
        "reviewer_pack_runs": reviewer_runs,
        "semantic_guard_status": semantic_status,
        "semantic_guard_pairs": semantic_pairs,
        "boundary_negative_guard_status": boundary_negative_status,
        "boundary_negative_guard_path": str(boundary_negative_guard_path),
        "variants": variant_key_list,
        "seeds": seed_list,
        "expected_bounds": expected_bounds,
        "cache_bounds": cache_bounds,
        "anchor_mask_report": anchor_report,
        "threshold_perturbation_summary": perturbation_rows,
        "paths": {
            "cache_metadata": str(metadata_path),
            "suite_dir": str(suite_dir),
            "reviewer_pack_dir": str(reviewer_pack_dir),
            "semantic_guard_dir": str(semantic_guard_dir),
            "boundary_negative_guard_dir": str(boundary_negative_guard_dir),
            "run_status_csv": str(output_dir / "threshold_controls_evidence_run_status.csv"),
            "file_status_csv": str(output_dir / "threshold_controls_evidence_file_status.csv"),
            "perturbation_audit_csv": str(output_dir / "threshold_controls_evidence_perturbation_audit.csv"),
        },
    }
    save_json(output_dir / "threshold_controls_evidence_guard.json", report)
    lines = [
        "# Strict-cache threshold-control evidence guard",
        "",
        f"Status: `{status}`",
        "",
        "This guard prevents citing wrong-threshold sensitivity controls until all strict-cache runs and reviewer-stat evidence files are complete.",
        "",
        "## Run Completion",
        "",
        f"- Expected runs: `{expected_runs}`",
        f"- Complete runs: `{complete_runs}`",
        f"- Missing or incomplete runs: `{missing_runs}`",
        f"- Reviewer pack runs: `{reviewer_runs}`",
        f"- Semantic guard status: `{semantic_status or 'missing'}`",
        f"- Semantic guard paired runs: `{semantic_pairs}`",
        f"- Boundary negative-control guard status: `{boundary_negative_status or 'missing'}`",
        f"- Threshold perturbation check ran: `{perturbation_checked}`",
        f"- Threshold support perturbation present: `{support_perturbation_present}`",
        f"- Threshold shared-label perturbation present: `{shared_label_perturbation_present}`",
        "",
        "## Checks",
        "",
    ]
    for key, value in checks.items():
        lines.append(f"- {key}: `{bool(value)}`")
    lines.extend(
        [
            "",
            "## Anchor-Mask Report",
            "",
            "```json",
            json.dumps(anchor_report, indent=2),
            "```",
            "",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return output_dir
