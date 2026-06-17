from __future__ import annotations

from pathlib import Path
import gzip
from typing import Any, Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .paper import aggregate_runs, collect_suite_run_dirs
from .utils import ensure_dir, load_json, save_json


REVIEWER_STAT_REQUIRED_FILES = (
    "reviewer_stat_pack_config.json",
    "reviewer_stat_pack_run_table.csv",
    "per_example_manifest.csv",
    "per_example_predictions.csv.gz",
    "paired_effects_raw.csv",
    "paired_effects_summary.csv",
    "paired_multiplicity_table.csv",
    "efficiency_fairness_table.csv",
    "failure_cases_gate_correct_bad.csv",
    "failure_cases_gate_correct_bad.png",
    "failure_cases_boundary_gate_correct_bad.csv",
    "failure_cases_boundary_gate_correct_bad.png",
    "reviewer_stat_pack_report.md",
)

REVIEWER_STAT_OPTIONAL_EMPTY_FILES = {
    "failure_cases_gate_correct_bad.csv",
    "failure_cases_gate_correct_bad.png",
    "failure_cases_boundary_gate_correct_bad.csv",
    "failure_cases_boundary_gate_correct_bad.png",
}


def _parse_filter(values: Iterable[str] | str | None) -> set[str]:
    if values is None:
        return set()
    tokens = values.split(",") if isinstance(values, str) else list(values)
    return {str(token).strip() for token in tokens if str(token).strip()}


def _parse_int_filter(values: Iterable[int] | str | None) -> set[int]:
    if values is None:
        return set()
    tokens = values.split(",") if isinstance(values, str) else list(values)
    parsed: set[int] = set()
    for token in tokens:
        text = str(token).strip()
        if not text:
            continue
        parsed.add(int(float(text)))
    return parsed


def _resolve_run_dir(raw_path: Any, root_dir: Path) -> Path:
    run_dir = Path(str(raw_path))
    return run_dir if run_dir.is_absolute() else root_dir / run_dir


def _load_or_build_run_table(
    dataset: str,
    root_dir: Path,
    output_dir: Path,
    run_table: Path | str | None,
    suite_dirs: Iterable[Path | str] | None,
    split: str,
) -> pd.DataFrame:
    if run_table:
        df = pd.read_csv(run_table)
    else:
        labeled: list[tuple[str, Path]] = []
        for suite_dir in suite_dirs or []:
            labeled.extend(collect_suite_run_dirs(root_dir / Path(suite_dir), dataset))
        if not labeled:
            raise ValueError("reviewer-stat-pack requires --run-table or at least one --suite-dir.")
        table_dir = ensure_dir(output_dir / "_run_table")
        df = aggregate_runs(dataset, labeled, table_dir, split=split)
    if "run_dir" not in df.columns:
        raise ValueError("Run table must include a run_dir column.")
    return df


def _load_valid_mask(metrics_dir: Path, regime: np.ndarray) -> np.ndarray:
    valid_path = metrics_dir / "regime_primary_valid.npy"
    if valid_path.exists():
        return np.load(valid_path).astype(bool)
    return np.ones_like(regime, dtype=bool)


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


def _node_ids(cache_dir: Path | None, num_nodes: int) -> np.ndarray:
    if cache_dir is not None:
        path = cache_dir / "node_ids.npy"
        if path.exists():
            values = np.asarray(np.load(path)).reshape(-1)
            if values.size == num_nodes:
                return values
    return np.arange(num_nodes, dtype=np.int64)


def _run_per_example_frame(
    row: pd.Series,
    root_dir: Path,
    split: str,
    steps_per_hour: int,
    node_ids: np.ndarray | None = None,
) -> pd.DataFrame:
    run_dir = _resolve_run_dir(row["run_dir"], root_dir)
    metrics_dir = run_dir / f"{split}_metrics"
    required = ["pred.npy", "target.npy", "mask.npy", "regime_primary.npy", "anchor_index.npy"]
    if any(not (metrics_dir / name).exists() for name in required):
        return pd.DataFrame()

    pred = np.asarray(np.load(metrics_dir / "pred.npy", mmap_mode="r"), dtype=np.float64)
    target = np.asarray(np.load(metrics_dir / "target.npy", mmap_mode="r"), dtype=np.float64)
    mask = np.asarray(np.load(metrics_dir / "mask.npy", mmap_mode="r"), dtype=np.float64)
    regime = np.asarray(np.load(metrics_dir / "regime_primary.npy"), dtype=np.int16)
    valid = _load_valid_mask(metrics_dir, regime)
    anchor_index = np.asarray(np.load(metrics_dir / "anchor_index.npy"), dtype=np.int64)

    if pred.ndim != 3 or target.shape != pred.shape or mask.shape != pred.shape:
        raise ValueError(f"Prediction arrays in {metrics_dir} must have shape [windows, horizon, nodes].")
    windows, _, num_nodes = pred.shape
    if regime.shape != (windows, num_nodes):
        raise ValueError(f"regime_primary.npy in {metrics_dir} must have shape [windows, nodes].")

    obs = mask.sum(axis=1)
    err = np.nan_to_num(pred - target, nan=0.0)
    abs_error_sum = (np.abs(err) * mask).sum(axis=1)
    squared_error_sum = ((err**2) * mask).sum(axis=1)
    safe_obs = np.maximum(obs, 1.0)
    mae = abs_error_sum / safe_obs
    mse = squared_error_sum / safe_obs
    rmse = np.sqrt(mse)
    target_mean = (np.nan_to_num(target, nan=0.0) * mask).sum(axis=1) / safe_obs
    pred_mean = (np.nan_to_num(pred, nan=0.0) * mask).sum(axis=1) / safe_obs

    flat_size = windows * num_nodes
    node_index = np.tile(np.arange(num_nodes, dtype=np.int64), windows)
    anchors = np.repeat(anchor_index, num_nodes)
    node_values = np.tile(node_ids if node_ids is not None else np.arange(num_nodes, dtype=np.int64), windows)
    switch = _switch_selector(regime, steps_per_hour)

    data: dict[str, Any] = {
        "dataset": row.get("dataset", ""),
        "model": row.get("model", ""),
        "seed": row.get("seed", ""),
        "variant_key": row.get("variant_key", ""),
        "experiment_group": row.get("experiment_group", ""),
        "run_dir": str(run_dir),
        "split": split,
        "window_idx": np.repeat(np.arange(windows, dtype=np.int64), num_nodes),
        "anchor_index": anchors,
        "node_idx": node_index,
        "node_id": node_values,
        "regime_primary": regime.reshape(flat_size),
        "regime_primary_valid": valid.reshape(flat_size).astype(np.int8),
        "switch_window": switch.reshape(flat_size).astype(np.int8),
        "valid_count": obs.reshape(flat_size),
        "target_mean": target_mean.reshape(flat_size),
        "pred_mean": pred_mean.reshape(flat_size),
        "mae": mae.reshape(flat_size),
        "mse": mse.reshape(flat_size),
        "rmse": rmse.reshape(flat_size),
    }

    anchor_physics_path = metrics_dir / "anchor_physics.npy"
    if anchor_physics_path.exists():
        anchor_physics = np.asarray(np.load(anchor_physics_path, mmap_mode="r"), dtype=np.float64)
        if anchor_physics.shape[:2] == (windows, num_nodes) and anchor_physics.shape[-1] >= 2:
            data["wspd_anchor"] = anchor_physics[..., 0].reshape(flat_size)
            data["pab_mean_anchor"] = anchor_physics[..., 1].reshape(flat_size)

    gate_path = metrics_dir / "gate_prob.npy"
    if gate_path.exists():
        gate = np.asarray(np.load(gate_path, mmap_mode="r"), dtype=np.float64)
        num_classes = max(1, min(gate.shape[-1], int(np.nanmax(regime)) + 1 if regime.size else 1))
        supervised_gate = gate[..., :num_classes]
        gate_label = supervised_gate.argmax(axis=-1)
        gate_confidence = supervised_gate.max(axis=-1)
        gate_valid = valid & (regime >= 0) & (regime < num_classes)
        data["gate_label"] = gate_label.reshape(flat_size)
        data["gate_confidence"] = gate_confidence.reshape(flat_size)
        data["gate_correct"] = (gate_valid & (gate_label == regime)).reshape(flat_size).astype(np.int8)
    else:
        data["gate_label"] = np.full(flat_size, -1, dtype=np.int16)
        data["gate_confidence"] = np.full(flat_size, np.nan, dtype=np.float32)
        data["gate_correct"] = np.zeros(flat_size, dtype=np.int8)

    frame = pd.DataFrame(data)
    frame = frame[pd.to_numeric(frame["valid_count"], errors="coerce") > 0.0].reset_index(drop=True)
    return frame


def _write_per_example_file(
    run_table: pd.DataFrame,
    root_dir: Path,
    cache_dir: Path | None,
    output_dir: Path,
    split: str,
    steps_per_hour: int,
    max_rows: int,
) -> pd.DataFrame:
    output_path = output_dir / "per_example_predictions.csv.gz"
    summaries: list[dict[str, Any]] = []
    written = 0
    header = True
    with gzip.open(output_path, "wt", encoding="utf-8", newline="") as handle:
        for _, row in run_table.iterrows():
            run_dir = _resolve_run_dir(row["run_dir"], root_dir)
            metrics_dir = run_dir / f"{split}_metrics"
            pred_path = metrics_dir / "pred.npy"
            if not pred_path.exists():
                continue
            pred_shape = np.load(pred_path, mmap_mode="r").shape
            ids = _node_ids(cache_dir, int(pred_shape[-1])) if pred_shape else None
            frame = _run_per_example_frame(row, root_dir, split, steps_per_hour, node_ids=ids)
            if frame.empty:
                continue
            if max_rows > 0 and written + len(frame) > max_rows:
                frame = frame.iloc[: max(0, max_rows - written)].copy()
            if frame.empty:
                break
            frame.to_csv(handle, index=False, header=header)
            header = False
            written += len(frame)
            summaries.append(
                {
                    "model": row.get("model", ""),
                    "seed": row.get("seed", ""),
                    "variant_key": row.get("variant_key", ""),
                    "run_dir": str(run_dir),
                    "rows": int(len(frame)),
                    "mean_rmse": float(pd.to_numeric(frame["rmse"], errors="coerce").mean()),
                    "mean_gate_correct": float(pd.to_numeric(frame["gate_correct"], errors="coerce").mean()),
                }
            )
            if max_rows > 0 and written >= max_rows:
                break
    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(output_dir / "per_example_manifest.csv", index=False)
    return summary_df


def _sample_pair_arrays(
    ref: np.ndarray,
    cmp: np.ndarray,
    max_examples: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, int]:
    ref = np.asarray(ref, dtype=np.float64)
    cmp = np.asarray(cmp, dtype=np.float64)
    finite = np.isfinite(ref) & np.isfinite(cmp)
    ref = ref[finite]
    cmp = cmp[finite]
    original_n = int(ref.size)
    if max_examples > 0 and ref.size > max_examples:
        idx = rng.choice(ref.size, size=int(max_examples), replace=False)
        ref = ref[idx]
        cmp = cmp[idx]
    return ref, cmp, original_n


def _paired_bootstrap_rmse_delta(
    ref_mse: np.ndarray,
    cmp_mse: np.ndarray,
    samples: int,
    rng: np.random.Generator,
) -> tuple[float, float]:
    if ref_mse.size == 0:
        return float("nan"), float("nan")
    if ref_mse.size == 1 or samples <= 0:
        delta = float(np.sqrt(ref_mse.mean()) - np.sqrt(cmp_mse.mean()))
        return delta, delta
    draws = np.empty(int(samples), dtype=np.float64)
    n = ref_mse.size
    for i in range(int(samples)):
        idx = rng.integers(0, n, size=n)
        draws[i] = np.sqrt(ref_mse[idx].mean()) - np.sqrt(cmp_mse[idx].mean())
    return float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))


def _paired_bootstrap_mean_ci(values: np.ndarray, samples: int, rng: np.random.Generator) -> tuple[float, float]:
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return float("nan"), float("nan")
    if values.size == 1 or samples <= 0:
        return float(values.mean()), float(values.mean())
    draws = np.empty(int(samples), dtype=np.float64)
    for index in range(int(samples)):
        sample = rng.integers(0, values.size, size=values.size)
        draws[index] = values[sample].mean()
    return float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))


def _paired_permutation_pvalue(
    diff: np.ndarray,
    samples: int,
    rng: np.random.Generator,
) -> float:
    diff = np.asarray(diff, dtype=np.float64)
    diff = diff[np.isfinite(diff)]
    if diff.size == 0:
        return float("nan")
    observed = abs(float(diff.mean()))
    if samples <= 0 or diff.size == 1:
        return float("nan")
    hits = 0
    n = diff.size
    for _ in range(int(samples)):
        signs = rng.choice(np.array([-1.0, 1.0]), size=n)
        if abs(float((diff * signs).mean())) >= observed:
            hits += 1
    return float((hits + 1) / (int(samples) + 1))


def _metric_from_row_or_json(row: pd.Series, root_dir: Path, split: str, metric: str) -> float:
    if metric in row.index:
        value = pd.to_numeric(pd.Series([row.get(metric)]), errors="coerce").iloc[0]
        if pd.notna(value):
            return float(value)
    metrics_path = _resolve_run_dir(row["run_dir"], root_dir) / f"{split}_metrics" / "metrics.json"
    if not metrics_path.exists():
        return float("nan")
    metrics = load_json(metrics_path)
    gate = metrics.get("gate_alignment", {})
    value = gate.get(metric)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _paired_effects(
    run_table: pd.DataFrame,
    root_dir: Path,
    split: str,
    steps_per_hour: int,
    reference_model: str,
    baseline_models: set[str],
    bootstrap_samples: int,
    permutation_samples: int,
    max_examples: int,
    rated_wind: float,
    boundary_band: float,
    seed: int,
) -> pd.DataFrame:
    if run_table.empty or "model" not in run_table.columns:
        return pd.DataFrame()
    reference = run_table[run_table["model"].astype(str) == reference_model].copy()
    comparators = run_table[run_table["model"].astype(str) != reference_model].copy()
    if baseline_models:
        comparators = comparators[comparators["model"].astype(str).isin(baseline_models)].copy()
    if reference.empty or comparators.empty:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(seed)
    for comparator_model, comparator_group in comparators.groupby("model", dropna=False, sort=False):
        model_rows: list[dict[str, Any]] = []
        for _, ref_row in reference.iterrows():
            seed_value = ref_row.get("seed", "")
            cmp_seed = comparator_group[comparator_group["seed"].astype(str) == str(seed_value)].copy()
            if cmp_seed.empty:
                continue
            cmp_row = cmp_seed.iloc[0]
            ref_frame = _run_per_example_frame(ref_row, root_dir, split, steps_per_hour)
            cmp_frame = _run_per_example_frame(cmp_row, root_dir, split, steps_per_hour)
            if ref_frame.empty or cmp_frame.empty:
                continue
            cmp_cols = ["anchor_index", "node_idx", "mse", "rmse", "mae", "switch_window"]
            for optional in ["wspd_anchor", "regime_primary_valid"]:
                if optional in cmp_frame.columns:
                    cmp_cols.append(optional)
            merged = ref_frame.merge(
                cmp_frame[cmp_cols],
                on=["anchor_index", "node_idx"],
                how="inner",
                suffixes=("_reference", "_comparator"),
            )
            if merged.empty:
                continue
            boundary_selector = np.zeros(len(merged), dtype=bool)
            if "wspd_anchor_reference" in merged.columns and "wspd_anchor_comparator" in merged.columns:
                ref_boundary = (
                    pd.to_numeric(merged["wspd_anchor_reference"], errors="coerce")
                    .sub(float(rated_wind))
                    .abs()
                    .le(float(boundary_band))
                    & pd.to_numeric(merged.get("regime_primary_valid_reference", 0), errors="coerce").eq(1)
                )
                cmp_boundary = (
                    pd.to_numeric(merged["wspd_anchor_comparator"], errors="coerce")
                    .sub(float(rated_wind))
                    .abs()
                    .le(float(boundary_band))
                    & pd.to_numeric(merged.get("regime_primary_valid_comparator", 0), errors="coerce").eq(1)
                )
                boundary_selector = (ref_boundary | cmp_boundary).to_numpy(dtype=bool)
            for slice_name, selector in {
                "overall": np.ones(len(merged), dtype=bool),
                "switch_window": merged["switch_window_reference"].astype(bool).to_numpy()
                | merged["switch_window_comparator"].astype(bool).to_numpy(),
                "boundary_band": boundary_selector,
            }.items():
                subset = merged.loc[selector]
                if subset.empty:
                    continue
                ref_mse, cmp_mse, original_n = _sample_pair_arrays(
                    subset["mse_reference"].to_numpy(),
                    subset["mse_comparator"].to_numpy(),
                    max_examples=max_examples,
                    rng=rng,
                )
                if ref_mse.size == 0:
                    continue
                delta_mse = ref_mse - cmp_mse
                rmse_reference = float(np.sqrt(ref_mse.mean()))
                rmse_comparator = float(np.sqrt(cmp_mse.mean()))
                ci_low, ci_high = _paired_bootstrap_rmse_delta(ref_mse, cmp_mse, bootstrap_samples, rng)
                model_rows.append(
                    {
                        "reference_model": reference_model,
                        "comparator_model": comparator_model,
                        "seed": seed_value,
                        "split": split,
                        "slice": slice_name,
                        "metric": "rmse",
                        "n_pairs_original": original_n,
                        "n_pairs_used": int(ref_mse.size),
                        "rmse_reference": rmse_reference,
                        "rmse_comparator": rmse_comparator,
                        "delta_rmse_reference_minus_comparator": rmse_reference - rmse_comparator,
                        "delta_rmse_ci_low": ci_low,
                        "delta_rmse_ci_high": ci_high,
                        "mean_mse_delta_reference_minus_comparator": float(delta_mse.mean()),
                        "paired_permutation_p_mse": _paired_permutation_pvalue(delta_mse, permutation_samples, rng),
                    }
                )
            for metric in ["nmi", "ari"]:
                ref_value = _metric_from_row_or_json(ref_row, root_dir, split, metric)
                cmp_value = _metric_from_row_or_json(cmp_row, root_dir, split, metric)
                if not np.isfinite(ref_value) or not np.isfinite(cmp_value):
                    missing_side = []
                    if not np.isfinite(ref_value):
                        missing_side.append("reference")
                    if not np.isfinite(cmp_value):
                        missing_side.append("comparator")
                    model_rows.append(
                        {
                            "reference_model": reference_model,
                            "comparator_model": comparator_model,
                            "seed": seed_value,
                            "split": split,
                            "slice": "gate_alignment",
                            "metric": metric,
                            "status": "not_applicable_missing_gate_metric",
                            "missing_gate_metric_side": ",".join(missing_side),
                            "n_pairs_original": 0,
                            "n_pairs_used": 0,
                            "value_reference": ref_value,
                            "value_comparator": cmp_value,
                            "delta_reference_minus_comparator": float("nan"),
                            "paired_permutation_p_value": float("nan"),
                        }
                    )
                    continue
                diff = ref_value - cmp_value
                model_rows.append(
                    {
                        "reference_model": reference_model,
                        "comparator_model": comparator_model,
                        "seed": seed_value,
                        "split": split,
                        "slice": "gate_alignment",
                        "metric": metric,
                        "status": "tested",
                        "missing_gate_metric_side": "",
                        "n_pairs_original": 1,
                        "n_pairs_used": 1,
                        "value_reference": ref_value,
                        "value_comparator": cmp_value,
                        "delta_reference_minus_comparator": diff,
                        "paired_permutation_p_value": float("nan"),
                    }
                )
        rows.extend(model_rows)
    effects = pd.DataFrame(rows)
    if effects.empty:
        return effects
    summary_rows: list[dict[str, Any]] = []
    if "metric" not in effects.columns:
        effects["metric"] = "rmse"
    effects["metric"] = effects["metric"].fillna("rmse").replace("", "rmse")
    group_cols = ["reference_model", "comparator_model", "split", "slice", "metric"]
    for keys, group in effects.groupby(group_cols, dropna=False, sort=False):
        out = {column: value for column, value in zip(group_cols, keys)}
        out["n_seed_pairs"] = int(len(group))
        out["n_tested_seed_pairs"] = int(pd.to_numeric(group.get("n_pairs_used"), errors="coerce").fillna(0).gt(0).sum())
        statuses = sorted({str(value) for value in group.get("status", pd.Series(["tested"])).fillna("tested")})
        out["status"] = "tested" if statuses == ["tested"] else ";".join(statuses)
        if out["metric"] in {"nmi", "ari"}:
            deltas = pd.to_numeric(group.get("delta_reference_minus_comparator"), errors="coerce").dropna().to_numpy()
            ci_low, ci_high = _paired_bootstrap_mean_ci(deltas, bootstrap_samples, rng)
            out["value_reference_mean"] = float(pd.to_numeric(group.get("value_reference"), errors="coerce").mean())
            out["value_comparator_mean"] = float(pd.to_numeric(group.get("value_comparator"), errors="coerce").mean())
            out["delta_reference_minus_comparator_mean"] = float(np.nanmean(deltas)) if deltas.size else float("nan")
            out["delta_reference_minus_comparator_std"] = float(np.nanstd(deltas)) if deltas.size > 1 else 0.0
            out["delta_reference_minus_comparator_ci_low"] = ci_low
            out["delta_reference_minus_comparator_ci_high"] = ci_high
            out["paired_permutation_p_value"] = _paired_permutation_pvalue(deltas, permutation_samples, rng)
            missing_sides = sorted(
                {
                    str(value)
                    for value in group.get("missing_gate_metric_side", pd.Series(dtype=str)).fillna("")
                    if str(value)
                }
            )
            out["missing_gate_metric_side"] = ";".join(missing_sides)
            summary_rows.append(out)
            continue
        for metric in [
            "rmse_reference",
            "rmse_comparator",
            "delta_rmse_reference_minus_comparator",
            "mean_mse_delta_reference_minus_comparator",
            "paired_permutation_p_mse",
        ]:
            values = pd.to_numeric(group[metric], errors="coerce").dropna()
            out[f"{metric}_mean"] = float(values.mean()) if not values.empty else float("nan")
            out[f"{metric}_std"] = float(values.std(ddof=0)) if len(values) > 1 else 0.0
        summary_rows.append(out)
    summary = pd.DataFrame(summary_rows)
    return effects, summary


def _benjamini_hochberg(p_values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(p_values, errors="coerce")
    adjusted = pd.Series(np.nan, index=numeric.index, dtype=float)
    finite = numeric.dropna().clip(lower=0.0, upper=1.0)
    if finite.empty:
        return adjusted
    ordered = finite.sort_values()
    ranks = np.arange(1, len(ordered) + 1, dtype=np.float64)
    raw = ordered.to_numpy(dtype=np.float64) * float(len(ordered)) / ranks
    monotone = np.minimum.accumulate(raw[::-1])[::-1]
    monotone = np.clip(monotone, 0.0, 1.0)
    adjusted.loc[ordered.index] = monotone
    return adjusted


def _paired_multiplicity_table(paired_summary: pd.DataFrame, alpha: float = 0.05) -> pd.DataFrame:
    if paired_summary.empty:
        return pd.DataFrame(
            columns=[
                "family",
                "reference_model",
                "comparator_model",
                "split",
                "slice",
                "metric",
                "raw_p_value",
                "p_value_bh",
                "reject_fdr_0p05",
                "correction",
                "n_hypotheses",
            ]
        )
    rows: list[dict[str, Any]] = []
    for _, row in paired_summary.iterrows():
        metric = str(row.get("metric", "rmse"))
        if metric == "rmse":
            p_value = pd.to_numeric(pd.Series([row.get("paired_permutation_p_mse_mean")]), errors="coerce").iloc[0]
        else:
            p_value = pd.to_numeric(pd.Series([row.get("paired_permutation_p_value")]), errors="coerce").iloc[0]
        rows.append(
            {
                "family": f"{row.get('split', '')}:{row.get('slice', '')}:{metric}",
                "reference_model": row.get("reference_model", ""),
                "comparator_model": row.get("comparator_model", ""),
                "split": row.get("split", ""),
                "slice": row.get("slice", ""),
                "metric": metric,
                "raw_p_value": p_value,
                "correction": "Benjamini-Hochberg FDR",
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    adjusted_frames: list[pd.DataFrame] = []
    for family, group in out.groupby("family", dropna=False, sort=False):
        corrected = group.copy()
        corrected["p_value_bh"] = _benjamini_hochberg(corrected["raw_p_value"])
        corrected["reject_fdr_0p05"] = corrected["p_value_bh"].le(float(alpha)).fillna(False).astype(int)
        corrected["n_hypotheses"] = int(pd.to_numeric(corrected["raw_p_value"], errors="coerce").notna().sum())
        adjusted_frames.append(corrected)
    result = pd.concat(adjusted_frames, ignore_index=True) if adjusted_frames else out
    return result.sort_values(["family", "raw_p_value", "comparator_model"], na_position="last").reset_index(drop=True)


def _fill_efficiency_from_runs(df: pd.DataFrame, root_dir: Path, split: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        out = row.to_dict()
        run_dir = _resolve_run_dir(row["run_dir"], root_dir)
        summary_path = run_dir / "training_summary.json"
        metrics_path = run_dir / f"{split}_metrics" / "metrics.json"
        def set_missing(key: str, value: Any) -> None:
            if value is None:
                return
            if key not in out or pd.isna(out.get(key)):
                out[key] = value

        if summary_path.exists():
            summary = load_json(summary_path)
            set_missing("parameter_count", summary.get("parameter_count"))
            set_missing("total_train_seconds", summary.get("total_train_seconds"))
            set_missing("best_epoch", summary.get("best_epoch"))
        if metrics_path.exists():
            metrics = load_json(metrics_path)
            efficiency = metrics.get("efficiency", {})
            set_missing("eval_seconds", efficiency.get("eval_seconds"))
            set_missing("num_windows", efficiency.get("num_windows"))
            set_missing("windows_per_second", efficiency.get("windows_per_second"))
        rows.append(out)
    return pd.DataFrame(rows)


def _efficiency_table(df: pd.DataFrame, root_dir: Path, split: str) -> pd.DataFrame:
    df = _fill_efficiency_from_runs(df, root_dir, split)
    if df.empty or "model" not in df.columns:
        return pd.DataFrame()
    metric_cols = [
        "parameter_count",
        "total_train_seconds",
        "eval_seconds",
        "num_windows",
        "windows_per_second",
        "best_epoch",
    ]
    rows: list[dict[str, Any]] = []
    for model, group in df.groupby("model", dropna=False, sort=False):
        out: dict[str, Any] = {"model": model, "n_runs": int(len(group))}
        for metric in metric_cols:
            values = pd.to_numeric(group.get(metric, pd.Series(dtype=float)), errors="coerce").dropna()
            out[f"{metric}_mean"] = float(values.mean()) if not values.empty else float("nan")
            out[f"{metric}_std"] = float(values.std(ddof=0)) if len(values) > 1 else 0.0
        if np.isfinite(out.get("total_train_seconds_mean", np.nan)):
            out["train_hours_mean"] = float(out["total_train_seconds_mean"]) / 3600.0
        rows.append(out)
    return pd.DataFrame(rows)


def _failure_cases(
    run_table: pd.DataFrame,
    root_dir: Path,
    split: str,
    steps_per_hour: int,
    reference_model: str,
    top_k: int,
) -> pd.DataFrame:
    if top_k <= 0 or run_table.empty or "model" not in run_table.columns:
        return pd.DataFrame()
    rows = run_table[run_table["model"].astype(str) == reference_model].copy()
    frames: list[pd.DataFrame] = []
    for _, row in rows.iterrows():
        frame = _run_per_example_frame(row, root_dir, split, steps_per_hour)
        if frame.empty or "gate_correct" not in frame.columns:
            continue
        frame = frame[(frame["switch_window"] == 1) & (frame["gate_correct"] == 1)].copy()
        if frame.empty:
            continue
        frames.append(frame.nlargest(top_k, "rmse"))
    if not frames:
        return pd.DataFrame()
    failures = pd.concat(frames, ignore_index=True).nlargest(top_k, "rmse").reset_index(drop=True)
    return failures


def _boundary_failure_cases(
    run_table: pd.DataFrame,
    root_dir: Path,
    split: str,
    steps_per_hour: int,
    reference_model: str,
    top_k: int,
    rated_wind: float,
    boundary_band: float,
) -> pd.DataFrame:
    if top_k <= 0 or run_table.empty or "model" not in run_table.columns:
        return pd.DataFrame()
    rows = run_table[run_table["model"].astype(str) == reference_model].copy()
    frames: list[pd.DataFrame] = []
    for _, row in rows.iterrows():
        frame = _run_per_example_frame(row, root_dir, split, steps_per_hour)
        required = {"gate_correct", "wspd_anchor", "pab_mean_anchor"}
        if frame.empty or not required.issubset(frame.columns):
            continue
        mppt_or_pitch = frame["regime_primary"].isin([1, 2])
        boundary = (pd.to_numeric(frame["wspd_anchor"], errors="coerce") - float(rated_wind)).abs() <= float(
            boundary_band
        )
        selector = mppt_or_pitch & boundary & (frame["regime_primary_valid"] == 1) & (frame["gate_correct"] == 1)
        frame = frame[selector].copy()
        if frame.empty:
            continue
        frame["boundary_rated_wind"] = float(rated_wind)
        frame["boundary_band"] = float(boundary_band)
        frames.append(frame.nlargest(top_k, "rmse"))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).nlargest(top_k, "rmse").reset_index(drop=True)


def _plot_failure_cases(failures: pd.DataFrame, output_path: Path, root_dir: Path, split: str, max_panels: int = 6) -> None:
    if failures.empty:
        fig, ax = plt.subplots(figsize=(8, 2.5))
        ax.axis("off")
        ax.text(
            0.5,
            0.5,
            "No gate-correct forecast-bad cases in this protocol unit.",
            ha="center",
            va="center",
            fontsize=11,
        )
        fig.tight_layout()
        fig.savefig(output_path, dpi=180)
        plt.close(fig)
        return
    cases = failures.head(max_panels).copy()
    fig, axes = plt.subplots(len(cases), 1, figsize=(8, max(2.4, 2.0 * len(cases))), squeeze=False)
    for ax, (_, case) in zip(axes[:, 0], cases.iterrows()):
        run_dir = _resolve_run_dir(case["run_dir"], root_dir)
        metrics_dir = run_dir / f"{split}_metrics"
        pred = np.load(metrics_dir / "pred.npy", mmap_mode="r")
        target = np.load(metrics_dir / "target.npy", mmap_mode="r")
        mask = np.load(metrics_dir / "mask.npy", mmap_mode="r")
        window_idx = int(case["window_idx"])
        node_idx = int(case["node_idx"])
        x = np.arange(1, pred.shape[1] + 1)
        valid = np.asarray(mask[window_idx, :, node_idx], dtype=bool)
        ax.plot(x[valid], np.asarray(target[window_idx, :, node_idx])[valid], label="target", linewidth=1.8)
        ax.plot(x[valid], np.asarray(pred[window_idx, :, node_idx])[valid], label="prediction", linewidth=1.5)
        physics_text = ""
        if "wspd_anchor" in case and pd.notna(case.get("wspd_anchor")):
            physics_text = f" Wspd={float(case['wspd_anchor']):.2f}"
        ax.set_title(
            f"{case['model']} seed={case['seed']} anchor={int(case['anchor_index'])} "
            f"node={int(case['node_idx'])} rmse={float(case['rmse']):.2f}{physics_text}",
            fontsize=9,
        )
        ax.set_xlabel("forecast horizon")
        ax.set_ylabel("target")
        ax.grid(alpha=0.25)
    axes[0, 0].legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _write_report(
    output_dir: Path,
    per_example_summary: pd.DataFrame,
    paired_summary: pd.DataFrame,
    multiplicity: pd.DataFrame,
    efficiency: pd.DataFrame,
    failures: pd.DataFrame,
    boundary_failures: pd.DataFrame,
    reference_model: str,
) -> None:
    lines = [
        "# Reviewer statistics pack",
        "",
        "This pack reads saved predictions; it does not retrain models.",
        "",
        "## Outputs",
        "",
        "- per_example_predictions.csv.gz: per-window-node prediction error rows.",
        "- paired_effects_raw.csv and paired_effects_summary.csv: paired model comparisons by seed.",
        "- paired_multiplicity_table.csv: Benjamini-Hochberg FDR correction over paired-test families.",
        "- efficiency_fairness_table.csv: parameters, training time, evaluation time, and throughput.",
        "- failure_cases_gate_correct_bad.csv: switch-window cases where the gate is correct but forecast error is high.",
        "- failure_cases_boundary_gate_correct_bad.csv: rated-wind boundary-band cases where the gate is correct but forecast error is high.",
        "",
    ]
    lines.extend(["## Current counts", ""])
    lines.append(f"- Reference model: {reference_model}.")
    lines.append(f"- Per-example run rows summarized: {len(per_example_summary)}.")
    lines.append(f"- Paired summary rows: {len(paired_summary)}.")
    lines.append(f"- Multiplicity-correction rows: {len(multiplicity)}.")
    lines.append(f"- Efficiency rows: {len(efficiency)}.")
    lines.append(f"- Failure cases: {len(failures)}.")
    lines.append(f"- Boundary failure cases: {len(boundary_failures)}.")
    if not paired_summary.empty:
        lines.extend(["", "## Paired interpretation", ""])
        lines.append("Delta RMSE is reference minus comparator; negative values favor the reference model.")
        for _, row in paired_summary.iterrows():
            metric = str(row.get("metric", "rmse"))
            status = str(row.get("status", "tested"))
            if metric == "rmse":
                lines.append(
                    f"- {row['slice']} vs {row['comparator_model']}: "
                    f"delta RMSE {row['delta_rmse_reference_minus_comparator_mean']:.4f} "
                    f"+/- {row['delta_rmse_reference_minus_comparator_std']:.4f}; "
                    f"seed pairs {int(row['n_seed_pairs'])}."
                )
            else:
                delta = pd.to_numeric(pd.Series([row.get("delta_reference_minus_comparator_mean")]), errors="coerce").iloc[0]
                if pd.notna(delta):
                    lines.append(
                        f"- {row['slice']} {metric} vs {row['comparator_model']}: "
                        f"delta {delta:.4f}; seed pairs {int(row['n_tested_seed_pairs'])}."
                    )
                else:
                    lines.append(
                        f"- {row['slice']} {metric} vs {row['comparator_model']}: {status}; "
                        f"tested seed pairs {int(row.get('n_tested_seed_pairs', 0))}."
                    )
    if not multiplicity.empty:
        lines.extend(["", "## Multiple comparisons", ""])
        lines.append("P values are corrected within split/slice/metric families using Benjamini-Hochberg FDR.")
    (output_dir / "reviewer_stat_pack_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_reviewer_stat_pack(
    dataset: str,
    output_dir: Path | str,
    root_dir: Path | str = ".",
    run_table: Path | str | None = None,
    suite_dirs: Iterable[Path | str] | None = None,
    cache_dir: Path | str | None = None,
    split: str = "test",
    models: Iterable[str] | str | None = None,
    reference_model: str = "MoE + L_bal + L_align + L_force",
    baseline_models: Iterable[str] | str | None = None,
    steps_per_hour: int = 6,
    bootstrap_samples: int = 1000,
    permutation_samples: int = 1000,
    max_per_example_rows: int = 0,
    max_paired_examples: int = 100000,
    top_k_failures: int = 12,
    rated_wind: float = 10.5,
    boundary_band: float = 1.0,
    seed: int = 42,
) -> Path:
    output_dir = ensure_dir(output_dir)
    root_dir = Path(root_dir)
    cache_path = Path(cache_dir) if cache_dir else None
    df = _load_or_build_run_table(
        dataset=dataset,
        root_dir=root_dir,
        output_dir=output_dir,
        run_table=run_table,
        suite_dirs=suite_dirs,
        split=split,
    )
    model_filter = _parse_filter(models)
    if model_filter and "model" in df.columns:
        df = df[df["model"].astype(str).isin(model_filter)].copy()
    df.to_csv(output_dir / "reviewer_stat_pack_run_table.csv", index=False)

    per_example_summary = _write_per_example_file(
        run_table=df,
        root_dir=root_dir,
        cache_dir=cache_path,
        output_dir=output_dir,
        split=split,
        steps_per_hour=steps_per_hour,
        max_rows=int(max_per_example_rows),
    )
    paired = _paired_effects(
        run_table=df,
        root_dir=root_dir,
        split=split,
        steps_per_hour=steps_per_hour,
        reference_model=reference_model,
        baseline_models=_parse_filter(baseline_models),
        bootstrap_samples=bootstrap_samples,
        permutation_samples=permutation_samples,
        max_examples=max_paired_examples,
        rated_wind=rated_wind,
        boundary_band=boundary_band,
        seed=seed,
    )
    if isinstance(paired, tuple):
        paired_raw, paired_summary = paired
    else:
        paired_raw = pd.DataFrame()
        paired_summary = pd.DataFrame()
    paired_raw.to_csv(output_dir / "paired_effects_raw.csv", index=False)
    paired_summary.to_csv(output_dir / "paired_effects_summary.csv", index=False)
    multiplicity = _paired_multiplicity_table(paired_summary)
    multiplicity.to_csv(output_dir / "paired_multiplicity_table.csv", index=False)

    efficiency = _efficiency_table(df, root_dir, split)
    efficiency.to_csv(output_dir / "efficiency_fairness_table.csv", index=False)

    failures = _failure_cases(
        run_table=df,
        root_dir=root_dir,
        split=split,
        steps_per_hour=steps_per_hour,
        reference_model=reference_model,
        top_k=top_k_failures,
    )
    failures.to_csv(output_dir / "failure_cases_gate_correct_bad.csv", index=False)
    _plot_failure_cases(failures, output_dir / "failure_cases_gate_correct_bad.png", root_dir, split)
    boundary_failures = _boundary_failure_cases(
        run_table=df,
        root_dir=root_dir,
        split=split,
        steps_per_hour=steps_per_hour,
        reference_model=reference_model,
        top_k=top_k_failures,
        rated_wind=rated_wind,
        boundary_band=boundary_band,
    )
    boundary_failures.to_csv(output_dir / "failure_cases_boundary_gate_correct_bad.csv", index=False)
    _plot_failure_cases(
        boundary_failures,
        output_dir / "failure_cases_boundary_gate_correct_bad.png",
        root_dir,
        split,
    )

    save_json(
        output_dir / "reviewer_stat_pack_config.json",
        {
            "dataset": dataset,
            "root_dir": str(root_dir),
            "run_table": str(run_table) if run_table else "",
            "suite_dirs": [str(path) for path in (suite_dirs or [])],
            "cache_dir": str(cache_path) if cache_path else "",
            "split": split,
            "models": sorted(model_filter),
            "reference_model": reference_model,
            "baseline_models": sorted(_parse_filter(baseline_models)),
            "steps_per_hour": int(steps_per_hour),
            "bootstrap_samples": int(bootstrap_samples),
            "permutation_samples": int(permutation_samples),
            "max_per_example_rows": int(max_per_example_rows),
            "max_paired_examples": int(max_paired_examples),
            "top_k_failures": int(top_k_failures),
            "rated_wind": float(rated_wind),
            "boundary_band": float(boundary_band),
            "seed": int(seed),
            "n_runs": int(len(df)),
            "n_per_example_run_summaries": int(len(per_example_summary)),
            "n_paired_rows": int(len(paired_raw)),
            "n_paired_multiplicity_rows": int(len(multiplicity)),
            "n_failure_cases": int(len(failures)),
            "n_boundary_failure_cases": int(len(boundary_failures)),
        },
    )
    _write_report(output_dir, per_example_summary, paired_summary, multiplicity, efficiency, failures, boundary_failures, reference_model)
    return output_dir


def _csv_rows(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    try:
        return int(len(pd.read_csv(path)))
    except pd.errors.EmptyDataError:
        return 0


def run_reviewer_stat_pack_guard(
    pack_dir: Path | str,
    output_dir: Path | str,
    min_runs: int = 20,
    min_paired_rows: int = 1,
    min_multiplicity_rows: int = 1,
    min_per_example_runs: int = 1,
    min_failure_cases: int = 1,
    min_boundary_failure_cases: int = 1,
    required_models: Iterable[str] | str | None = None,
    required_seeds: Iterable[int] | str | None = None,
) -> Path:
    pack_dir = Path(pack_dir)
    output_dir = ensure_dir(output_dir)
    config_path = pack_dir / "reviewer_stat_pack_config.json"
    config = load_json(config_path) if config_path.exists() else {}
    required_model_set = _parse_filter(required_models)
    required_seed_set = _parse_int_filter(required_seeds)

    file_rows: list[dict[str, Any]] = []
    for name in REVIEWER_STAT_REQUIRED_FILES:
        path = pack_dir / name
        is_csv = path.suffix == ".csv"
        file_rows.append(
            {
                "file": name,
                "path": str(path),
                "exists": path.exists(),
                "bytes": int(path.stat().st_size) if path.exists() else 0,
                "rows": _csv_rows(path) if is_csv else None,
            }
        )
    file_df = pd.DataFrame(file_rows)
    file_df.to_csv(output_dir / "reviewer_stat_pack_file_status.csv", index=False)

    required_files_exist = bool(file_df["exists"].all()) if not file_df.empty else False
    nonempty_required_df = file_df[~file_df["file"].isin(REVIEWER_STAT_OPTIONAL_EMPTY_FILES)]
    required_files_nonempty = bool((nonempty_required_df["bytes"] > 0).all()) if not nonempty_required_df.empty else False
    csv_rows = {str(row["file"]): int(row["rows"]) for _, row in file_df.dropna(subset=["rows"]).iterrows()}
    run_table_path = pack_dir / "reviewer_stat_pack_run_table.csv"
    run_table_df = pd.read_csv(run_table_path) if run_table_path.exists() else pd.DataFrame()
    observed_models = (
        set(run_table_df.get("model", pd.Series(dtype=str)).dropna().astype(str))
        if not run_table_df.empty
        else set()
    )
    observed_seeds = (
        {int(value) for value in pd.to_numeric(run_table_df.get("seed", pd.Series(dtype=float)), errors="coerce").dropna()}
        if not run_table_df.empty
        else set()
    )
    model_seed_pairs: set[tuple[str, int]] = set()
    if not run_table_df.empty and {"model", "seed"}.issubset(run_table_df.columns):
        for _, row in run_table_df.iterrows():
            seed_value = pd.to_numeric(pd.Series([row.get("seed")]), errors="coerce").iloc[0]
            if pd.isna(seed_value):
                continue
            model_seed_pairs.add((str(row.get("model", "")), int(seed_value)))
    missing_models = sorted(required_model_set.difference(observed_models))
    missing_seeds = sorted(required_seed_set.difference(observed_seeds))
    missing_model_seed_pairs = sorted(
        f"{model} seed {seed}"
        for model in sorted(required_model_set)
        for seed in sorted(required_seed_set)
        if (model, seed) not in model_seed_pairs
    )
    checks = {
        "pack_dir_exists": pack_dir.exists(),
        "config_exists": config_path.exists(),
        "required_files_exist": required_files_exist,
        "required_files_nonempty": required_files_nonempty,
        "n_runs_at_least_min_runs": int(config.get("n_runs", 0)) >= int(min_runs) if config else False,
        "paired_rows_at_least_min": int(config.get("n_paired_rows", 0)) >= int(min_paired_rows) if config else False,
        "multiplicity_rows_at_least_min": int(config.get("n_paired_multiplicity_rows", 0)) >= int(min_multiplicity_rows)
        if config
        else False,
        "per_example_runs_at_least_min": int(config.get("n_per_example_run_summaries", 0)) >= int(min_per_example_runs)
        if config
        else False,
        "failure_cases_at_least_min": int(config.get("n_failure_cases", 0)) >= int(min_failure_cases) if config else False,
        "boundary_failure_cases_at_least_min": int(config.get("n_boundary_failure_cases", 0))
        >= int(min_boundary_failure_cases)
        if config
        else False,
        "paired_summary_nonempty": csv_rows.get("paired_effects_summary.csv", 0) >= int(min_paired_rows),
        "paired_multiplicity_table_nonempty": csv_rows.get("paired_multiplicity_table.csv", 0)
        >= int(min_multiplicity_rows),
        "efficiency_table_nonempty": csv_rows.get("efficiency_fairness_table.csv", 0) > 0,
        "per_example_manifest_nonempty": csv_rows.get("per_example_manifest.csv", 0) >= int(min_per_example_runs),
        "failure_cases_nonempty": csv_rows.get("failure_cases_gate_correct_bad.csv", 0) >= int(min_failure_cases),
        "boundary_failure_cases_nonempty": csv_rows.get("failure_cases_boundary_gate_correct_bad.csv", 0)
        >= int(min_boundary_failure_cases),
        "failure_cases_file_present": bool(
            required_files_exist and "failure_cases_gate_correct_bad.csv" in set(file_df.loc[file_df["exists"], "file"].astype(str))
        ),
        "boundary_failure_cases_file_present": bool(
            required_files_exist
            and "failure_cases_boundary_gate_correct_bad.csv" in set(file_df.loc[file_df["exists"], "file"].astype(str))
        ),
        "required_models_present": (not required_model_set) or not missing_models,
        "required_seeds_present": (not required_seed_set) or not missing_seeds,
        "required_model_seed_matrix_complete": (not required_model_set or not required_seed_set)
        or not missing_model_seed_pairs,
    }
    structure_keys = [
        "pack_dir_exists",
        "config_exists",
        "required_files_exist",
        "required_files_nonempty",
        "paired_rows_at_least_min",
        "multiplicity_rows_at_least_min",
        "per_example_runs_at_least_min",
        "paired_summary_nonempty",
        "paired_multiplicity_table_nonempty",
        "efficiency_table_nonempty",
        "per_example_manifest_nonempty",
        "failure_cases_file_present",
        "boundary_failure_cases_file_present",
        "required_models_present",
        "required_seeds_present",
        "required_model_seed_matrix_complete",
    ]
    if not checks["pack_dir_exists"] or not checks["config_exists"] or not checks["required_files_exist"]:
        status = "blocked_missing_reviewer_stat_pack_files"
    elif not all(bool(checks[key]) for key in structure_keys):
        status = "blocked_incomplete_reviewer_stat_pack"
    elif not checks["n_runs_at_least_min_runs"]:
        status = "preliminary_available"
    else:
        status = "complete_ready_for_reviewer_statistics"

    report = {
        "status": status,
        "checks": checks,
        "pack_dir": str(pack_dir),
        "min_runs": int(min_runs),
        "n_runs": int(config.get("n_runs", 0)) if config else 0,
        "n_paired_rows": int(config.get("n_paired_rows", 0)) if config else 0,
        "n_paired_multiplicity_rows": int(config.get("n_paired_multiplicity_rows", 0)) if config else 0,
        "n_per_example_run_summaries": int(config.get("n_per_example_run_summaries", 0)) if config else 0,
        "n_failure_cases": int(config.get("n_failure_cases", 0)) if config else 0,
        "n_boundary_failure_cases": int(config.get("n_boundary_failure_cases", 0)) if config else 0,
        "required_models": sorted(required_model_set),
        "required_seeds": sorted(required_seed_set),
        "observed_models": sorted(observed_models),
        "observed_seeds": sorted(observed_seeds),
        "missing_required_models": missing_models,
        "missing_required_seeds": missing_seeds,
        "missing_required_model_seed_pairs": missing_model_seed_pairs,
        "paths": {
            "config": str(config_path),
            "file_status_csv": str(output_dir / "reviewer_stat_pack_file_status.csv"),
        },
    }
    save_json(output_dir / "reviewer_stat_pack_guard.json", report)

    lines = [
        "# Reviewer statistics pack guard",
        "",
        f"Status: `{status}`",
        "",
        "This guard verifies that reviewer-facing statistics include per-example rows, paired tests, efficiency data, and gate-correct failure cases.",
        "",
        "## Counts",
        "",
        f"- Runs: `{report['n_runs']}` / minimum `{int(min_runs)}`",
        f"- Paired rows: `{report['n_paired_rows']}`",
        f"- Multiplicity rows: `{report['n_paired_multiplicity_rows']}`",
        f"- Per-example run summaries: `{report['n_per_example_run_summaries']}`",
        f"- Failure cases: `{report['n_failure_cases']}`",
        f"- Boundary failure cases: `{report['n_boundary_failure_cases']}`",
        "",
        "## Checks",
        "",
    ]
    for key, value in checks.items():
        lines.append(f"- {key}: `{bool(value)}`")
    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_dir
