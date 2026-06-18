from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, confusion_matrix, normalized_mutual_info_score

from .utils import ensure_dir, load_json, save_json


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


def _switch_selector(regime: np.ndarray, steps_per_hour: int) -> np.ndarray:
    window = max(1, 3 * int(steps_per_hour))
    selector = np.zeros_like(regime, dtype=bool)
    if regime.shape[0] <= 1:
        return selector
    changes = regime[1:] != regime[:-1]
    rows, nodes = np.where(changes)
    for row, node in zip(rows, nodes):
        lo = max(0, row + 1 - window)
        hi = min(regime.shape[0], row + 2 + window)
        selector[lo:hi, node] = True
    return selector


def _block_ids_from_anchor(anchor_index: np.ndarray, num_blocks: int) -> np.ndarray:
    anchors = np.asarray(anchor_index, dtype=np.int64).reshape(-1)
    if anchors.size == 0:
        return np.empty((0,), dtype=np.int16)
    num_blocks = max(1, int(num_blocks))
    order = np.argsort(anchors, kind="stable")
    rank = np.empty_like(order)
    rank[order] = np.arange(anchors.size)
    block_ids = np.floor(rank * num_blocks / anchors.size).astype(np.int16) + 1
    return np.minimum(block_ids, num_blocks).astype(np.int16)


def _block_label(block_id: int, num_blocks: int) -> str:
    if block_id == 1:
        return "early"
    if block_id == num_blocks:
        return "late"
    return f"middle_{block_id}"


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


def _gate_alignment(
    gate_prob: np.ndarray | None,
    regime: np.ndarray,
    valid: np.ndarray,
) -> dict[str, Any]:
    if gate_prob is None:
        return {
            "n_valid_gate": 0,
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
    return {
        "n_valid_gate": int(flat_true.size),
        "nmi": float(normalized_mutual_info_score(flat_true, flat_pred)) if flat_true.size else float("nan"),
        "ari": float(adjusted_rand_score(flat_true, flat_pred)) if flat_true.size else float("nan"),
        "confusion_trace": int(np.trace(conf)),
        "confusion_total": int(conf.sum()),
    }


def _audit_one_run(
    row: pd.Series,
    root_dir: Path,
    split: str,
    num_blocks: int,
    steps_per_hour: int,
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

    block_ids = _block_ids_from_anchor(anchor_index, num_blocks)
    switch = _switch_selector(regime, steps_per_hour)
    regime_names = ["idle", "mppt", "pitch_control", "transition"]
    rows: list[dict[str, Any]] = []
    for block_id in range(1, int(num_blocks) + 1):
        block_mask = block_ids == block_id
        if not block_mask.any():
            continue
        block_pred = pred[block_mask]
        block_target = target[block_mask]
        block_obs_mask = mask[block_mask]
        overall = _masked_metrics(block_pred, block_target, block_obs_mask)
        switch_metrics = _masked_metrics(
            block_pred,
            block_target,
            block_obs_mask * switch[block_mask][:, None, :],
        )
        block_regime = regime[block_mask]
        block_valid = valid[block_mask]
        block_gate = gate_prob[block_mask] if gate_prob is not None else None
        alignment = _gate_alignment(block_gate, block_regime, block_valid)
        out: dict[str, Any] = {
            "dataset": row.get("dataset", ""),
            "model": row.get("model", ""),
            "seed": row.get("seed", ""),
            "variant_key": row.get("variant_key", ""),
            "experiment_group": row.get("experiment_group", ""),
            "run_dir": str(run_dir),
            "split": split,
            "block_id": int(block_id),
            "block_label": _block_label(block_id, int(num_blocks)),
            "num_blocks": int(num_blocks),
            "n_windows": int(block_mask.sum()),
            "anchor_start": int(np.asarray(anchor_index)[block_mask].min()),
            "anchor_end": int(np.asarray(anchor_index)[block_mask].max()),
            "overall_mae": overall["mae"],
            "overall_rmse": overall["rmse"],
            "switch_mae": switch_metrics["mae"],
            "switch_rmse": switch_metrics["rmse"],
            **alignment,
        }
        if "pitch_control" in regime_names:
            pitch_id = regime_names.index("pitch_control")
            pitch_mask = block_obs_mask * (block_regime == pitch_id)[:, None, :]
            pitch = _masked_metrics(block_pred, block_target, pitch_mask)
            out["pitch_control_mae"] = pitch["mae"]
            out["pitch_control_rmse"] = pitch["rmse"]
        rows.append(out)
    return rows


def _summarize(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty:
        return pd.DataFrame()
    group_cols = ["dataset", "model", "block_id", "block_label", "num_blocks"]
    metric_cols = [
        "overall_mae",
        "overall_rmse",
        "switch_mae",
        "switch_rmse",
        "pitch_control_mae",
        "pitch_control_rmse",
        "nmi",
        "ari",
        "n_valid_gate",
        "n_windows",
    ]
    rows: list[dict[str, Any]] = []
    for keys, group in raw_df.groupby(group_cols, dropna=False, sort=False):
        out = {column: value for column, value in zip(group_cols, keys)}
        out["n_runs"] = int(len(group))
        out["anchor_start_min"] = int(pd.to_numeric(group["anchor_start"]).min())
        out["anchor_end_max"] = int(pd.to_numeric(group["anchor_end"]).max())
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


def _load_cache_physics(cache_dir: Path | None) -> tuple[np.ndarray | None, dict[str, Any], int, int]:
    if cache_dir is None:
        return None, {}, 0, 1
    metadata_path = cache_dir / "metadata.json"
    physics_path = cache_dir / "physics.npy"
    if not metadata_path.exists() or not physics_path.exists():
        return None, {}, 0, 1
    metadata = load_json(metadata_path)
    physics = np.load(physics_path)
    physics_names = [str(name) for name in metadata.get("physics_names", [])]
    wspd_idx = physics_names.index("Wspd") if "Wspd" in physics_names else 0
    pab_idx = physics_names.index("Pab_mean") if "Pab_mean" in physics_names else 1
    return physics, metadata, wspd_idx, pab_idx


def _continuous_distance(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    a = np.sort(a[np.isfinite(a)])
    b = np.sort(b[np.isfinite(b)])
    if a.size == 0 or b.size == 0:
        return float("nan"), float("nan")
    values = np.sort(np.unique(np.concatenate([a, b])))
    if values.size == 0:
        return float("nan"), float("nan")
    cdf_a = np.searchsorted(a, values, side="right") / float(a.size)
    cdf_b = np.searchsorted(b, values, side="right") / float(b.size)
    ks = float(np.max(np.abs(cdf_a - cdf_b)))
    q = np.linspace(0.0, 1.0, 101)
    wasserstein = float(np.mean(np.abs(np.quantile(a, q) - np.quantile(b, q))))
    return ks, wasserstein


def _regime_share_metrics(regime: np.ndarray, valid: np.ndarray) -> dict[str, float]:
    valid = np.asarray(valid, dtype=bool)
    regime = np.asarray(regime)
    counts = []
    denom = max(int(valid.sum()), 1)
    for regime_id in range(4):
        counts.append(float(((regime == regime_id) & valid).sum() / denom))
    return {
        "idle_share": counts[0],
        "mppt_share": counts[1],
        "pitch_control_share": counts[2],
        "transition_share": counts[3],
    }


def _categorical_distances(early: pd.Series, late: pd.Series) -> tuple[float, float]:
    early_arr = pd.to_numeric(early, errors="coerce").to_numpy(dtype=np.float64)
    late_arr = pd.to_numeric(late, errors="coerce").to_numpy(dtype=np.float64)
    if early_arr.size == 0 or late_arr.size == 0:
        return float("nan"), float("nan")
    early_arr = np.nan_to_num(early_arr, nan=0.0)
    late_arr = np.nan_to_num(late_arr, nan=0.0)
    early_arr = early_arr / max(float(early_arr.sum()), 1e-12)
    late_arr = late_arr / max(float(late_arr.sum()), 1e-12)
    tv = float(0.5 * np.abs(late_arr - early_arr).sum())
    midpoint = 0.5 * (early_arr + late_arr)

    def kl(p: np.ndarray, q: np.ndarray) -> float:
        mask = p > 0
        return float((p[mask] * np.log(p[mask] / np.maximum(q[mask], 1e-12))).sum())

    jsd = float(0.5 * kl(early_arr, midpoint) + 0.5 * kl(late_arr, midpoint))
    return tv, jsd


def _shift_diagnostic_one_run(
    row: pd.Series,
    *,
    root_dir: Path,
    split: str,
    num_blocks: int,
    steps_per_hour: int,
    cache_physics: np.ndarray | None,
    wspd_idx: int,
    pab_idx: int,
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
    block_ids = _block_ids_from_anchor(anchor_index, num_blocks)
    switch = _switch_selector(regime, steps_per_hour)

    physics = None
    if cache_physics is not None:
        try:
            physics = np.asarray(cache_physics[np.asarray(anchor_index, dtype=np.int64)])
        except (IndexError, ValueError, TypeError):
            physics = None
    rows: list[dict[str, Any]] = []
    safe_target = np.nan_to_num(np.asarray(target, dtype=np.float64), nan=0.0)
    obs_mask = np.asarray(mask, dtype=np.float64)
    aggregate_power = np.sum(safe_target * obs_mask, axis=2)
    abs_ramp = np.abs(aggregate_power[:, -1] - aggregate_power[:, 0]) if aggregate_power.shape[1] > 1 else np.zeros(aggregate_power.shape[0])
    for block_id in range(1, int(num_blocks) + 1):
        block_mask = block_ids == block_id
        if not block_mask.any():
            continue
        block_pred = pred[block_mask]
        block_target = target[block_mask]
        block_obs_mask = mask[block_mask]
        block_regime = regime[block_mask]
        block_valid = valid[block_mask]
        overall = _masked_metrics(block_pred, block_target, block_obs_mask)
        switch_metrics = _masked_metrics(block_pred, block_target, block_obs_mask * switch[block_mask][:, None, :])
        pitch_metrics = _masked_metrics(block_pred, block_target, block_obs_mask * (block_regime == 2)[:, None, :])
        alignment = _gate_alignment(gate_prob[block_mask] if gate_prob is not None else None, block_regime, block_valid)
        target_values = np.asarray(block_target)[np.asarray(block_obs_mask, dtype=bool)]
        regime_shares = _regime_share_metrics(block_regime, block_valid)
        boundary_share = float((np.isin(block_regime, [1, 2]) & block_valid & switch[block_mask]).sum() / max(int(block_valid.sum()), 1))
        out: dict[str, Any] = {
            "dataset": row.get("dataset", ""),
            "model": row.get("model", ""),
            "seed": row.get("seed", ""),
            "variant_key": row.get("variant_key", ""),
            "experiment_group": row.get("experiment_group", ""),
            "run_dir": str(run_dir),
            "split": split,
            "block_id": int(block_id),
            "block_label": _block_label(block_id, int(num_blocks)),
            "n_windows": int(block_mask.sum()),
            "anchor_start": int(np.asarray(anchor_index)[block_mask].min()),
            "anchor_end": int(np.asarray(anchor_index)[block_mask].max()),
            "overall_rmse": overall["rmse"],
            "switch_rmse": switch_metrics["rmse"],
            "pitch_control_rmse": pitch_metrics["rmse"],
            "nmi": alignment["nmi"],
            "ari": alignment["ari"],
            "mask_valid_rate": float(np.asarray(block_obs_mask, dtype=bool).mean()),
            "regime_valid_rate": float(np.asarray(block_valid, dtype=bool).mean()),
            "target_power_mean": float(np.nanmean(target_values)) if target_values.size else float("nan"),
            "target_power_std": float(np.nanstd(target_values)) if target_values.size else float("nan"),
            "abs_ramp_mean": float(np.nanmean(abs_ramp[block_mask])),
            "abs_ramp_p90": float(np.nanquantile(abs_ramp[block_mask], 0.90)),
            "boundary_share": boundary_share,
            **regime_shares,
        }
        if physics is not None:
            block_physics = physics[block_mask]
            wspd = np.asarray(block_physics[..., wspd_idx], dtype=np.float64)
            pab = np.asarray(block_physics[..., pab_idx], dtype=np.float64)
            out["wspd_mean"] = float(np.nanmean(wspd))
            out["wspd_std"] = float(np.nanstd(wspd))
            out["pab_mean"] = float(np.nanmean(pab))
            out["pab_std"] = float(np.nanstd(pab))
        else:
            out["wspd_mean"] = float("nan")
            out["wspd_std"] = float("nan")
            out["pab_mean"] = float("nan")
            out["pab_std"] = float("nan")
        rows.append(out)
    return rows


def _shift_effects(diagnostics_df: pd.DataFrame, bootstrap_samples: int, seed: int) -> pd.DataFrame:
    if diagnostics_df.empty:
        return pd.DataFrame()
    first = diagnostics_df[diagnostics_df["block_id"] == 1].copy()
    last_block = int(pd.to_numeric(diagnostics_df["block_id"]).max())
    last = diagnostics_df[diagnostics_df["block_id"] == last_block].copy()
    if first.empty or last.empty:
        return pd.DataFrame()
    key_cols = ["dataset", "model", "run_dir"]
    metric_cols = [
        "overall_rmse",
        "switch_rmse",
        "pitch_control_rmse",
        "nmi",
        "ari",
        "wspd_mean",
        "pab_mean",
        "target_power_mean",
        "abs_ramp_mean",
        "mask_valid_rate",
        "regime_valid_rate",
        "boundary_share",
        "idle_share",
        "mppt_share",
        "pitch_control_share",
        "transition_share",
    ]
    merged = last.merge(first[key_cols + metric_cols], on=key_cols, how="inner", suffixes=("_late", "_early"))
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for keys, group in merged.groupby(["dataset", "model"], dropna=False, sort=False):
        dataset, model = keys
        out: dict[str, Any] = {
            "dataset": dataset,
            "model": model,
            "comparison": f"block_{last_block}_minus_block_1",
            "n_runs": int(len(group)),
        }
        for metric in metric_cols:
            delta = pd.to_numeric(group[f"{metric}_late"], errors="coerce").to_numpy() - pd.to_numeric(
                group[f"{metric}_early"], errors="coerce"
            ).to_numpy()
            mean, low, high = _bootstrap_ci(delta, rng, bootstrap_samples)
            out[f"delta_{metric}_mean"] = mean
            out[f"delta_{metric}_ci_low"] = low
            out[f"delta_{metric}_ci_high"] = high
            ks, wasserstein = _continuous_distance(group[f"{metric}_early"], group[f"{metric}_late"])
            out[f"{metric}_ks"] = ks
            out[f"{metric}_wasserstein"] = wasserstein
        share_metrics = ["idle_share", "mppt_share", "pitch_control_share", "transition_share"]
        early_share = pd.Series([pd.to_numeric(group[f"{metric}_early"], errors="coerce").mean() for metric in share_metrics])
        late_share = pd.Series([pd.to_numeric(group[f"{metric}_late"], errors="coerce").mean() for metric in share_metrics])
        tv, jsd = _categorical_distances(early_share, late_share)
        out["regime_share_total_variation"] = tv
        out["regime_share_jensen_shannon"] = jsd
        rows.append(out)
    return pd.DataFrame(rows)


def _write_shift_tex(effects_df: pd.DataFrame, output_path: Path) -> Path:
    lines = [
        "\\begin{tabular}{lrrrr}",
        "\\toprule",
        "Model & Delta RMSE & Delta ramp & Regime TV & Delta NMI \\\\",
        "\\midrule",
    ]
    if not effects_df.empty:
        for _, row in effects_df.iterrows():
            lines.append(
                f"{_latex_escape(str(row.get('model', '')))} & "
                f"{_fmt(row.get('delta_overall_rmse_mean'))} & "
                f"{_fmt(row.get('delta_abs_ramp_mean_mean'))} & "
                f"{_fmt(row.get('regime_share_total_variation'))} & "
                f"{_fmt(row.get('delta_nmi_mean'))} \\\\"
            )
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _fmt(value: Any, digits: int = 4) -> str:
    try:
        value_float = float(value)
    except (TypeError, ValueError):
        return ""
    if not np.isfinite(value_float):
        return ""
    return f"{value_float:.{digits}f}"


def _latex_escape(value: str) -> str:
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


def _shift_guard(
    diagnostics_df: pd.DataFrame,
    effects_df: pd.DataFrame,
    *,
    output_dir: Path,
) -> dict[str, Any]:
    required_diag = {
        "wspd_mean",
        "pab_mean",
        "target_power_mean",
        "abs_ramp_mean",
        "mask_valid_rate",
        "regime_valid_rate",
        "boundary_share",
        "mppt_share",
        "pitch_control_share",
        "overall_rmse",
        "switch_rmse",
        "pitch_control_rmse",
        "nmi",
        "ari",
    }
    required_effect = {
        "delta_overall_rmse_mean",
        "delta_switch_rmse_mean",
        "delta_nmi_mean",
        "wspd_mean_ks",
        "pab_mean_ks",
        "target_power_mean_ks",
        "abs_ramp_mean_ks",
        "regime_share_total_variation",
        "regime_share_jensen_shannon",
    }
    checks = {
        "diagnostics_rows_present": not diagnostics_df.empty,
        "diagnostics_required_columns_present": required_diag.issubset(diagnostics_df.columns),
        "effects_rows_present": not effects_df.empty,
        "effects_required_columns_present": required_effect.issubset(effects_df.columns),
        "late_rmse_degradation_recorded": bool(
            not effects_df.empty and (pd.to_numeric(effects_df["delta_overall_rmse_mean"], errors="coerce") > 0.0).any()
        ),
        "routing_semantics_reported": bool(not effects_df.empty and "delta_nmi_mean" in effects_df.columns),
        "distribution_shift_metrics_reported": bool(not effects_df.empty and required_effect.issubset(effects_df.columns)),
    }
    status = "passed_late_period_shift_diagnostics" if all(checks.values()) else "blocked_late_period_shift_diagnostics"
    report = {
        "status": status,
        "checks": checks,
        "paths": {
            "diagnostics_csv": str(output_dir / "time_forward_shift_diagnostics.csv"),
            "effects_csv": str(output_dir / "time_forward_shift_effects.csv"),
            "tex_table": str(output_dir / "table_strict_wtb_late_shift_diagnostics.tex"),
            "guard_json": str(output_dir / "time_forward_shift_guard.json"),
        },
    }
    return report


def _late_vs_early_effects(raw_df: pd.DataFrame, bootstrap_samples: int, seed: int) -> pd.DataFrame:
    if raw_df.empty:
        return pd.DataFrame()
    first = raw_df[raw_df["block_id"] == 1].copy()
    last_block = int(pd.to_numeric(raw_df["block_id"]).max())
    last = raw_df[raw_df["block_id"] == last_block].copy()
    if first.empty or last.empty:
        return pd.DataFrame()
    key_cols = ["dataset", "model", "run_dir"]
    metric_cols = ["overall_rmse", "switch_rmse", "pitch_control_rmse", "nmi", "ari"]
    merged = last.merge(
        first[key_cols + metric_cols],
        on=key_cols,
        how="inner",
        suffixes=("_late", "_early"),
    )
    rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(seed)
    for keys, group in merged.groupby(["dataset", "model"], dropna=False, sort=False):
        dataset, model = keys
        out: dict[str, Any] = {
            "dataset": dataset,
            "model": model,
            "comparison": f"block_{last_block}_minus_block_1",
            "n_runs": int(len(group)),
        }
        for metric in metric_cols:
            delta = pd.to_numeric(group[f"{metric}_late"], errors="coerce").to_numpy() - pd.to_numeric(
                group[f"{metric}_early"], errors="coerce"
            ).to_numpy()
            mean, low, high = _bootstrap_ci(delta, rng, bootstrap_samples)
            out[f"delta_{metric}_mean"] = mean
            out[f"delta_{metric}_ci_low"] = low
            out[f"delta_{metric}_ci_high"] = high
            if metric.endswith("rmse"):
                out[f"prob_late_{metric}_worse"] = float(np.mean(delta > 0.0)) if delta.size else float("nan")
            else:
                out[f"prob_late_{metric}_lower"] = float(np.mean(delta < 0.0)) if delta.size else float("nan")
        rows.append(out)
    return pd.DataFrame(rows)


def _write_report(summary_df: pd.DataFrame, effects_df: pd.DataFrame, output_path: Path) -> None:
    lines = [
        "# Time-forward holdout audit",
        "",
        "This audit slices saved split predictions into contiguous anchor-time blocks and compares late-test behavior with early-test behavior.",
        "",
    ]
    if summary_df.empty:
        lines.append("No saved prediction runs were available for the requested audit.")
    else:
        lines.extend(["## Block summaries", ""])
        for _, row in summary_df.iterrows():
            lines.append(
                f"- {row['model']} block {int(row['block_id'])} ({row['block_label']}): "
                f"RMSE {row['overall_rmse_mean']:.4f} +/- {row['overall_rmse_std']:.4f}; "
                f"switch RMSE {row['switch_rmse_mean']:.4f} +/- {row['switch_rmse_std']:.4f}; "
                f"NMI {row['nmi_mean']:.4f} +/- {row['nmi_std']:.4f}; "
                f"ARI {row['ari_mean']:.4f} +/- {row['ari_std']:.4f}; n={int(row['n_runs'])}."
            )
        if not effects_df.empty:
            lines.extend(["", "## Late-vs-early effects", ""])
            for _, row in effects_df.iterrows():
                lines.append(
                    f"- {row['model']} {row['comparison']}: "
                    f"Delta RMSE {row['delta_overall_rmse_mean']:.4f} "
                    f"[{row['delta_overall_rmse_ci_low']:.4f}, {row['delta_overall_rmse_ci_high']:.4f}]; "
                    f"Delta switch RMSE {row['delta_switch_rmse_mean']:.4f} "
                    f"[{row['delta_switch_rmse_ci_low']:.4f}, {row['delta_switch_rmse_ci_high']:.4f}]; "
                    f"Delta NMI {row['delta_nmi_mean']:.4f} "
                    f"[{row['delta_nmi_ci_low']:.4f}, {row['delta_nmi_ci_high']:.4f}]."
                )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_time_forward_audit(
    run_table: Path | str,
    output_dir: Path | str,
    root_dir: Path | str = ".",
    cache_dir: Path | str | None = None,
    split: str = "test",
    models: Iterable[str] | str | None = None,
    num_blocks: int = 4,
    steps_per_hour: int = 6,
    bootstrap_samples: int = 1000,
    seed: int = 42,
) -> Path:
    root_dir = Path(root_dir)
    output_dir = ensure_dir(output_dir)
    run_table = Path(run_table)
    cache_path = Path(cache_dir) if cache_dir else None
    cache_physics, cache_metadata, wspd_idx, pab_idx = _load_cache_physics(cache_path)
    df = pd.read_csv(run_table)
    if "run_dir" not in df.columns:
        raise ValueError("Time-forward audit requires a run table with a run_dir column.")

    model_filter = _parse_model_filter(models)
    if model_filter and "model" in df.columns:
        df = df[df["model"].astype(str).isin(model_filter)].copy()

    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        rows.extend(
            _audit_one_run(
                row=row,
                root_dir=root_dir,
                split=split,
                num_blocks=num_blocks,
                steps_per_hour=steps_per_hour,
            )
        )

    raw_df = pd.DataFrame(rows)
    summary_df = _summarize(raw_df)
    effects_df = _late_vs_early_effects(raw_df, bootstrap_samples=bootstrap_samples, seed=seed)
    shift_rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        shift_rows.extend(
            _shift_diagnostic_one_run(
                row=row,
                root_dir=root_dir,
                split=split,
                num_blocks=num_blocks,
                steps_per_hour=steps_per_hour,
                cache_physics=cache_physics,
                wspd_idx=wspd_idx,
                pab_idx=pab_idx,
            )
        )
    shift_df = pd.DataFrame(shift_rows)
    shift_effects_df = _shift_effects(shift_df, bootstrap_samples=bootstrap_samples, seed=seed)

    raw_df.to_csv(output_dir / "time_forward_raw.csv", index=False)
    summary_df.to_csv(output_dir / "time_forward_summary.csv", index=False)
    effects_df.to_csv(output_dir / "time_forward_effects.csv", index=False)
    shift_df.to_csv(output_dir / "time_forward_shift_diagnostics.csv", index=False)
    shift_effects_df.to_csv(output_dir / "time_forward_shift_effects.csv", index=False)
    _write_shift_tex(shift_effects_df, output_dir / "table_strict_wtb_late_shift_diagnostics.tex")
    shift_guard = _shift_guard(shift_df, shift_effects_df, output_dir=output_dir)
    save_json(output_dir / "time_forward_shift_guard.json", shift_guard)
    save_json(
        output_dir / "time_forward_config.json",
        {
            "run_table": str(run_table),
            "root_dir": str(root_dir),
            "cache_dir": str(cache_path) if cache_path else None,
            "split": split,
            "models": sorted(model_filter),
            "num_blocks": int(num_blocks),
            "steps_per_hour": int(steps_per_hour),
            "bootstrap_samples": int(bootstrap_samples),
            "seed": int(seed),
            "n_raw_rows": int(len(raw_df)),
            "n_summary_rows": int(len(summary_df)),
            "n_effect_rows": int(len(effects_df)),
            "n_shift_diagnostic_rows": int(len(shift_df)),
            "n_shift_effect_rows": int(len(shift_effects_df)),
            "cache_physics_loaded": cache_physics is not None,
            "cache_metadata": {
                "dataset": cache_metadata.get("dataset", "") if cache_metadata else "",
                "physics_names": cache_metadata.get("physics_names", []) if cache_metadata else [],
            },
        },
    )
    _write_report(summary_df, effects_df, output_dir / "time_forward_report.md")
    return output_dir
