from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "anchor_only_decisive_comparison_20260613"

PROPOSED = "MoE + L_bal + L_align + L_force"
ANCHOR_ONLY = "Anchor-only router"
CONTEXT = "Context-supervised router"
FULL = "Physics-Aligned MoE"


def _read_csv(path: str | Path) -> pd.DataFrame:
    full = ROOT / path
    if not full.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(full)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _read_json(path: str | Path) -> dict[str, Any]:
    full = ROOT / path
    if not full.exists():
        return {}
    return json.loads(full.read_text(encoding="utf-8"))


def _finite_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return out if np.isfinite(out) else float("nan")


def _fmt(value: Any, digits: int = 2) -> str:
    out = _finite_float(value)
    if not np.isfinite(out):
        return "NA"
    return f"{out:.{digits}f}"


def _metric_value(df: pd.DataFrame, scenario: str, model: str, metric: str) -> float:
    if df.empty:
        return float("nan")
    subset = df[(df["scenario"].astype(str) == scenario) & (df["model"].astype(str) == model)]
    if subset.empty:
        return float("nan")
    return _finite_float(subset.iloc[0].get(f"{metric}_mean"))


def _expected_calibration_error(confidence: np.ndarray, correct: np.ndarray, n_bins: int = 10) -> float:
    confidence = np.asarray(confidence, dtype=np.float64)
    correct = np.asarray(correct, dtype=np.float64)
    bins = np.linspace(0.0, 1.0, int(n_bins) + 1)
    ece = 0.0
    for idx in range(int(n_bins)):
        lower = bins[idx]
        upper = bins[idx + 1]
        if idx == int(n_bins) - 1:
            mask = (confidence >= lower) & (confidence <= upper)
        else:
            mask = (confidence >= lower) & (confidence < upper)
        if mask.any():
            ece += float(mask.mean()) * abs(float(correct[mask].mean()) - float(confidence[mask].mean()))
    return float(ece)


def _load_gate_labels(metrics_dir: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    gate = np.load(metrics_dir / "gate_prob.npy", mmap_mode="r")
    regime = np.load(metrics_dir / "regime_primary.npy")
    valid_path = metrics_dir / "regime_primary_valid.npy"
    valid = np.load(valid_path).astype(bool) if valid_path.exists() else np.ones_like(regime, dtype=bool)
    valid_regime = np.asarray(regime[valid], dtype=np.int64)
    num_classes = int(valid_regime.max()) + 1 if valid_regime.size else int(gate.shape[-1])
    num_classes = max(1, min(int(gate.shape[-1]), num_classes))
    probs = np.asarray(gate[..., :num_classes], dtype=np.float32)
    labels = probs.argmax(axis=-1)
    usable = valid & (regime >= 0) & (regime < num_classes) & np.isfinite(probs).all(axis=-1)
    return labels, np.asarray(regime, dtype=np.int64), usable


def _calibration_rows(run_table: pd.DataFrame, scenario: str, split: str = "test") -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if run_table.empty:
        return pd.DataFrame()
    for _, row in run_table.iterrows():
        metrics_dir = ROOT / str(row["run_dir"]) / f"{split}_metrics"
        if not (metrics_dir / "gate_prob.npy").exists() or not (metrics_dir / "regime_primary.npy").exists():
            continue
        gate = np.load(metrics_dir / "gate_prob.npy", mmap_mode="r")
        regime = np.load(metrics_dir / "regime_primary.npy")
        valid_path = metrics_dir / "regime_primary_valid.npy"
        valid = np.load(valid_path).astype(bool) if valid_path.exists() else np.ones_like(regime, dtype=bool)
        valid_regime = np.asarray(regime[valid], dtype=np.int64)
        if valid_regime.size == 0:
            continue
        num_classes = max(1, min(int(gate.shape[-1]), int(valid_regime.max()) + 1))
        probs = np.asarray(gate[..., :num_classes], dtype=np.float32)
        usable = valid & (regime >= 0) & (regime < num_classes) & np.isfinite(probs).all(axis=-1)
        if not usable.any():
            continue
        flat_probs = probs[usable]
        flat_true = np.asarray(regime[usable], dtype=np.int64)
        pred = flat_probs.argmax(axis=-1)
        confidence = flat_probs.max(axis=-1)
        supervised_mass = flat_probs.sum(axis=-1)
        correct = pred == flat_true
        one_hot = np.eye(num_classes, dtype=np.float32)[flat_true]
        rows.append(
            {
                "scenario": scenario,
                "model": row.get("model", ""),
                "seed": row.get("seed", ""),
                "n_gate_cells": int(flat_true.size),
                "gate_accuracy": float(correct.mean()),
                "gate_ece": _expected_calibration_error(confidence, correct),
                "gate_brier": float(((flat_probs - one_hot) ** 2).sum(axis=1).mean()),
                "mean_gate_confidence": float(confidence.mean()),
                "mean_supervised_class_mass": float(supervised_mass.mean()),
                "min_supervised_class_mass": float(supervised_mass.min()),
            }
        )
    return pd.DataFrame(rows)


def _calibration_summary(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame()
    metric_cols = [
        "gate_accuracy",
        "gate_ece",
        "gate_brier",
        "mean_gate_confidence",
        "mean_supervised_class_mass",
        "min_supervised_class_mass",
    ]
    out_rows: list[dict[str, Any]] = []
    for keys, group in rows.groupby(["scenario", "model"], sort=False):
        scenario, model = keys
        out: dict[str, Any] = {"scenario": scenario, "model": model, "n_runs": int(len(group))}
        for metric in metric_cols:
            values = pd.to_numeric(group[metric], errors="coerce").dropna()
            out[f"{metric}_mean"] = float(values.mean()) if not values.empty else float("nan")
            out[f"{metric}_std"] = float(values.std(ddof=0)) if len(values) > 1 else 0.0
        out_rows.append(out)
    return pd.DataFrame(out_rows)


def _responsibility_stability_rows(run_table: pd.DataFrame, scenario: str, split: str = "test") -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if run_table.empty:
        return pd.DataFrame()
    for model, group in run_table.groupby("model", sort=False):
        loaded: list[tuple[Any, np.ndarray, np.ndarray]] = []
        for _, row in group.sort_values("seed").iterrows():
            metrics_dir = ROOT / str(row["run_dir"]) / f"{split}_metrics"
            if not (metrics_dir / "gate_prob.npy").exists() or not (metrics_dir / "regime_primary.npy").exists():
                continue
            labels, _regime, usable = _load_gate_labels(metrics_dir)
            loaded.append((row.get("seed", ""), labels, usable))
        for left_idx in range(len(loaded)):
            for right_idx in range(left_idx + 1, len(loaded)):
                seed_left, labels_left, usable_left = loaded[left_idx]
                seed_right, labels_right, usable_right = loaded[right_idx]
                if labels_left.shape == labels_right.shape and usable_left.shape == usable_right.shape:
                    mask = usable_left & usable_right
                    left = labels_left[mask].ravel()
                    right = labels_right[mask].ravel()
                else:
                    left = labels_left[usable_left].ravel()
                    right = labels_right[usable_right].ravel()
                    n = min(int(left.size), int(right.size))
                    left = left[:n]
                    right = right[:n]
                if left.size == 0 or right.size == 0:
                    continue
                rows.append(
                    {
                        "scenario": scenario,
                        "model": model,
                        "seed_left": seed_left,
                        "seed_right": seed_right,
                        "n_gate_cells": int(min(left.size, right.size)),
                        "pairwise_gate_nmi": float(normalized_mutual_info_score(left, right)),
                        "pairwise_gate_ari": float(adjusted_rand_score(left, right)),
                    }
                )
    return pd.DataFrame(rows)


def _responsibility_stability_summary(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame()
    out_rows: list[dict[str, Any]] = []
    for keys, group in rows.groupby(["scenario", "model"], sort=False):
        scenario, model = keys
        out: dict[str, Any] = {"scenario": scenario, "model": model, "n_seed_pairs": int(len(group))}
        for metric in ["pairwise_gate_nmi", "pairwise_gate_ari"]:
            values = pd.to_numeric(group[metric], errors="coerce").dropna()
            out[f"{metric}_mean"] = float(values.mean()) if not values.empty else float("nan")
            out[f"{metric}_std"] = float(values.std(ddof=0)) if len(values) > 1 else 0.0
        out_rows.append(out)
    return pd.DataFrame(out_rows)


def _metric_summary(
    df: pd.DataFrame,
    scenario: str,
    models: list[str],
    metrics: list[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if df.empty or "model" not in df.columns:
        return rows
    for model in models:
        subset = df[df["model"].astype(str) == model].copy()
        if subset.empty:
            continue
        row: dict[str, Any] = {
            "scenario": scenario,
            "model": model,
            "n_runs": int(len(subset)),
        }
        for metric in metrics:
            if metric in subset.columns:
                values = pd.to_numeric(subset[metric], errors="coerce").dropna()
                row[f"{metric}_mean"] = float(values.mean()) if not values.empty else float("nan")
                row[f"{metric}_std"] = float(values.std(ddof=0)) if len(values) > 1 else 0.0
                continue
            mean_col = f"{metric}_mean"
            if mean_col in subset.columns:
                values = pd.to_numeric(subset[mean_col], errors="coerce").dropna()
                row[f"{metric}_mean"] = float(values.mean()) if not values.empty else float("nan")
                std_col = f"{metric}_std"
                if std_col in subset.columns:
                    std_values = pd.to_numeric(subset[std_col], errors="coerce").dropna()
                    row[f"{metric}_std"] = float(std_values.mean()) if not std_values.empty else 0.0
                else:
                    row[f"{metric}_std"] = 0.0
        rows.append(row)
    return rows


def _delta_rows(summary: pd.DataFrame, scenario: str, comparator: str) -> list[dict[str, Any]]:
    if summary.empty:
        return []
    base = summary[(summary["scenario"] == scenario) & (summary["model"] == PROPOSED)]
    other = summary[(summary["scenario"] == scenario) & (summary["model"] == comparator)]
    if base.empty or other.empty:
        return []
    base_row = base.iloc[0]
    other_row = other.iloc[0]
    rows: list[dict[str, Any]] = []
    for metric in [
        "overall_rmse",
        "switch_rmse",
        "pitch_control_rmse",
        "nmi",
        "ari",
        "expert_usage_entropy",
        "expert_usage_variance",
        "total_train_seconds",
        "eval_seconds",
        "windows_per_second",
    ]:
        bcol = f"{metric}_mean"
        if bcol in summary.columns and pd.notna(base_row.get(bcol)) and pd.notna(other_row.get(bcol)):
            rows.append(
                {
                    "scenario": scenario,
                    "reference_model": PROPOSED,
                    "comparator_model": comparator,
                    "metric": metric,
                    "reference_mean": float(base_row[bcol]),
                    "comparator_mean": float(other_row[bcol]),
                    "reference_minus_comparator": float(base_row[bcol] - other_row[bcol]),
                }
            )
    return rows


def _guard_rows() -> list[dict[str, Any]]:
    guard_specs = [
        (
            "strict_ablation",
            "artifacts/strict_ablation_guard_wtb_strictmask/strict_ablation_guard.json",
            "complete_ready_for_strict_ablation_table",
        ),
        (
            "future_holdout",
            "artifacts/future_holdout_evidence_guard_wtb_strictmask/future_holdout_evidence_guard.json",
            "complete_ready_for_future_holdout_evidence",
        ),
        (
            "spatial_holdout",
            "artifacts/spatial_holdout_evidence_guard_wtb_east/spatial_holdout_evidence_guard.json",
            "complete_ready_for_spatial_holdout_evidence",
        ),
        (
            "wrong_threshold_controls",
            "artifacts/strict_threshold_controls_evidence_guard_wtb_strictmask/threshold_controls_evidence_guard.json",
            "complete_ready_for_threshold_control_evidence",
        ),
    ]
    rows: list[dict[str, Any]] = []
    for name, path, expected in guard_specs:
        guard = _read_json(path)
        rows.append(
            {
                "guard": name,
                "path": path,
                "status": guard.get("status", "missing"),
                "expected_status": expected,
                "complete": guard.get("status") == expected,
                "expected_runs": guard.get("expected_runs"),
                "complete_runs": guard.get("complete_runs"),
                "missing_runs": guard.get("missing_runs"),
            }
        )
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    strict_runs = _read_csv("artifacts/strictmask_ablation_export_20260613/tables/wtb_test_aggregated_runs.csv")
    future_status = _read_csv("artifacts/future_holdout_evidence_guard_wtb_strictmask/future_holdout_run_status.csv")
    spatial_status = _read_csv("artifacts/spatial_holdout_evidence_guard_wtb_east/spatial_holdout_evidence_run_status.csv")
    spatial_eff = _read_csv("artifacts/spatial_holdout_wtb_east_reviewer_stats/efficiency_fairness_table.csv")
    spatial_pairs = _read_csv("artifacts/spatial_holdout_wtb_east_reviewer_stats/paired_effects_summary.csv")
    spatial_failure = _read_csv("artifacts/spatial_holdout_wtb_east_reviewer_stats/failure_cases_gate_correct_bad.csv")
    spatial_boundary_failure = _read_csv(
        "artifacts/spatial_holdout_wtb_east_reviewer_stats/failure_cases_boundary_gate_correct_bad.csv"
    )
    strict_boundary = _read_csv(
        "artifacts/anchor_only_decisive_comparison_20260613/strict_boundary_slice_comparison/boundary_slice_summary.csv"
    )
    strict_boundary_effects = _read_csv(
        "artifacts/anchor_only_decisive_comparison_20260613/strict_boundary_slice_comparison/boundary_slice_effects.csv"
    )
    spatial_boundary = _read_csv(
        "artifacts/anchor_only_decisive_comparison_20260613/spatial_boundary_slice_comparison/boundary_slice_summary.csv"
    )
    spatial_boundary_effects = _read_csv(
        "artifacts/anchor_only_decisive_comparison_20260613/spatial_boundary_slice_comparison/boundary_slice_effects.csv"
    )
    future_boundary = _read_csv("artifacts/future_holdout_wtb_strictmask_boundary_slice/boundary_slice_summary.csv")
    stress_summary = _read_csv("artifacts/anchor_only_decisive_comparison_20260613/anchor_stress_summary.csv")
    stress_degradation = _read_csv(
        "artifacts/anchor_only_decisive_comparison_20260613/anchor_stress_degradation_summary.csv"
    )
    stress_effects = _read_csv(
        "artifacts/anchor_only_decisive_comparison_20260613/anchor_stress_degradation_effects.csv"
    )
    threshold_semantic_guard = _read_json(
        "artifacts/strict_threshold_controls_semantic_guard_wtb_strictmask/threshold_controls_semantic_guard.json"
    )
    threshold_evidence_guard = _read_json(
        "artifacts/strict_threshold_controls_evidence_guard_wtb_strictmask/threshold_controls_evidence_guard.json"
    )
    threshold_semantic_summary = _read_csv(
        "artifacts/strict_threshold_controls_semantic_guard_wtb_strictmask/threshold_controls_semantic_summary.csv"
    )
    threshold_perturbation = _read_csv(
        "artifacts/strict_threshold_controls_evidence_guard_wtb_strictmask/threshold_controls_evidence_perturbation_audit.csv"
    )
    if not threshold_semantic_summary.empty:
        threshold_diagnostic = threshold_semantic_summary.merge(
            threshold_perturbation,
            on="variant_key",
            how="left",
            suffixes=("", "_perturbation"),
        )
    else:
        threshold_diagnostic = pd.DataFrame()
    threshold_diagnostic.to_csv(OUT / "threshold_negative_control_summary.csv", index=False)

    summary_rows: list[dict[str, Any]] = []
    summary_rows.extend(
        _metric_summary(
            strict_runs,
            "strict_test",
            [PROPOSED, ANCHOR_ONLY, CONTEXT, FULL],
            [
                "overall_rmse",
                "switch_rmse",
                "pitch_control_rmse",
                "nmi",
                "ari",
                "expert_usage_entropy",
                "expert_usage_variance",
                "total_train_seconds",
                "eval_seconds",
                "windows_per_second",
            ],
        )
    )
    summary_rows.extend(
        _metric_summary(
            future_status.rename(columns={"label": "model"}),
            "future_holdout",
            [PROPOSED],
            ["overall_rmse", "switch_rmse", "nmi", "ari"],
        )
    )
    summary_rows.extend(
        _metric_summary(
            spatial_status.rename(columns={"label": "model"}),
            "spatial_holdout",
            [PROPOSED, ANCHOR_ONLY, CONTEXT],
            ["overall_rmse", "switch_rmse", "nmi", "ari"],
        )
    )
    summary_rows.extend(
        _metric_summary(
            spatial_eff,
            "spatial_efficiency",
            [PROPOSED, ANCHOR_ONLY, CONTEXT],
            ["total_train_seconds", "eval_seconds", "windows_per_second"],
        )
    )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT / "anchor_only_decisive_metrics.csv", index=False)

    deltas: list[dict[str, Any]] = []
    for scenario in ["strict_test", "spatial_holdout", "spatial_efficiency"]:
        for comparator in [ANCHOR_ONLY, CONTEXT, FULL]:
            deltas.extend(_delta_rows(summary, scenario, comparator))
    pd.DataFrame(deltas).to_csv(OUT / "anchor_only_decisive_deltas.csv", index=False)

    rows: list[dict[str, Any]] = []
    for label, df in [
        ("strict_test", strict_boundary),
        ("spatial_holdout", spatial_boundary),
        ("future_holdout", future_boundary),
    ]:
        if df.empty:
            continue
        subset = df[df["slice"].astype(str) == "boundary_band"].copy()
        for _, source_row in subset.iterrows():
            row = source_row.to_dict()
            row["scenario"] = label
            rows.append(row)
    boundary_summary = pd.DataFrame(rows)
    boundary_summary.to_csv(OUT / "boundary_window_summary.csv", index=False)

    effect_rows: list[dict[str, Any]] = []
    for label, df in [
        ("strict_test", strict_boundary_effects),
        ("spatial_holdout", spatial_boundary_effects),
    ]:
        if df.empty:
            continue
        subset = df[df["comparator_slice"].astype(str) == "nonboundary_valid"].copy()
        for _, source_row in subset.iterrows():
            row = source_row.to_dict()
            row["scenario"] = label
            effect_rows.append(row)
    pd.DataFrame(effect_rows).to_csv(OUT / "boundary_window_effects.csv", index=False)

    strict_model_runs = strict_runs[strict_runs["model"].isin([PROPOSED, ANCHOR_ONLY, CONTEXT])].copy()
    spatial_model_runs = spatial_status.rename(columns={"label": "model"})
    spatial_model_runs = spatial_model_runs[spatial_model_runs["model"].isin([PROPOSED, ANCHOR_ONLY, CONTEXT])].copy()

    calibration_raw = pd.concat(
        [
            _calibration_rows(strict_model_runs, "strict_test"),
            _calibration_rows(spatial_model_runs, "spatial_holdout"),
        ],
        ignore_index=True,
    )
    calibration_raw.to_csv(OUT / "gate_calibration_raw.csv", index=False)
    calibration_summary = _calibration_summary(calibration_raw)
    calibration_summary.to_csv(OUT / "gate_calibration_summary.csv", index=False)

    stability_raw = pd.concat(
        [
            _responsibility_stability_rows(strict_model_runs, "strict_test"),
            _responsibility_stability_rows(spatial_model_runs, "spatial_holdout"),
        ],
        ignore_index=True,
    )
    stability_raw.to_csv(OUT / "responsibility_stability_raw.csv", index=False)
    stability_summary = _responsibility_stability_summary(stability_raw)
    stability_summary.to_csv(OUT / "responsibility_stability_summary.csv", index=False)

    guard_df = pd.DataFrame(_guard_rows())
    guard_df.to_csv(OUT / "guard_status_summary.csv", index=False)

    failure_rows = [
        {
            "pack": "spatial_holdout_reviewer_stats",
            "failure_cases_gate_correct_bad": int(len(spatial_failure)),
            "failure_cases_boundary_gate_correct_bad": int(len(spatial_boundary_failure)),
            "paired_effect_rows": int(len(spatial_pairs)),
        }
    ]
    pd.DataFrame(failure_rows).to_csv(OUT / "failure_case_inventory.csv", index=False)

    strict_anchor = summary[(summary["scenario"] == "strict_test") & (summary["model"] == ANCHOR_ONLY)]
    strict_prop = summary[(summary["scenario"] == "strict_test") & (summary["model"] == PROPOSED)]
    spatial_anchor = summary[(summary["scenario"] == "spatial_holdout") & (summary["model"] == ANCHOR_ONLY)]
    spatial_prop = summary[(summary["scenario"] == "spatial_holdout") & (summary["model"] == PROPOSED)]
    spatial_eff_anchor = summary[(summary["scenario"] == "spatial_efficiency") & (summary["model"] == ANCHOR_ONLY)]
    spatial_eff_prop = summary[(summary["scenario"] == "spatial_efficiency") & (summary["model"] == PROPOSED)]
    spatial_context = summary[(summary["scenario"] == "spatial_holdout") & (summary["model"] == CONTEXT)]

    strict_boundary_anchor = boundary_summary[
        (boundary_summary["scenario"].astype(str) == "strict_test")
        & (boundary_summary["model"].astype(str) == ANCHOR_ONLY)
    ]
    strict_boundary_prop = boundary_summary[
        (boundary_summary["scenario"].astype(str) == "strict_test")
        & (boundary_summary["model"].astype(str) == PROPOSED)
    ]
    spatial_boundary_anchor = boundary_summary[
        (boundary_summary["scenario"].astype(str) == "spatial_holdout")
        & (boundary_summary["model"].astype(str) == ANCHOR_ONLY)
    ]
    spatial_boundary_prop = boundary_summary[
        (boundary_summary["scenario"].astype(str) == "spatial_holdout")
        & (boundary_summary["model"].astype(str) == PROPOSED)
    ]
    future_boundary_prop = boundary_summary[
        (boundary_summary["scenario"].astype(str) == "future_holdout")
        & (boundary_summary["model"].astype(str) == PROPOSED)
    ]

    strict_cal_anchor = calibration_summary[
        (calibration_summary["scenario"].astype(str) == "strict_test")
        & (calibration_summary["model"].astype(str) == ANCHOR_ONLY)
    ]
    strict_cal_prop = calibration_summary[
        (calibration_summary["scenario"].astype(str) == "strict_test")
        & (calibration_summary["model"].astype(str) == PROPOSED)
    ]
    spatial_cal_anchor = calibration_summary[
        (calibration_summary["scenario"].astype(str) == "spatial_holdout")
        & (calibration_summary["model"].astype(str) == ANCHOR_ONLY)
    ]
    spatial_cal_prop = calibration_summary[
        (calibration_summary["scenario"].astype(str) == "spatial_holdout")
        & (calibration_summary["model"].astype(str) == PROPOSED)
    ]

    strict_stab_anchor = stability_summary[
        (stability_summary["scenario"].astype(str) == "strict_test")
        & (stability_summary["model"].astype(str) == ANCHOR_ONLY)
    ]
    strict_stab_prop = stability_summary[
        (stability_summary["scenario"].astype(str) == "strict_test")
        & (stability_summary["model"].astype(str) == PROPOSED)
    ]
    spatial_stab_anchor = stability_summary[
        (stability_summary["scenario"].astype(str) == "spatial_holdout")
        & (stability_summary["model"].astype(str) == ANCHOR_ONLY)
    ]
    spatial_stab_prop = stability_summary[
        (stability_summary["scenario"].astype(str) == "spatial_holdout")
        & (stability_summary["model"].astype(str) == PROPOSED)
    ]

    def val(df: pd.DataFrame, col: str) -> float:
        if df.empty or col not in df.columns:
            return float("nan")
        return float(df.iloc[0][col])

    def stress_val(scenario: str, model: str, metric: str) -> float:
        return _metric_value(stress_summary, scenario, model, metric)

    def stress_deg(scenario: str, model: str, metric: str) -> float:
        if stress_degradation.empty:
            return float("nan")
        subset = stress_degradation[
            (stress_degradation["scenario"].astype(str) == scenario)
            & (stress_degradation["model"].astype(str) == model)
        ]
        column = f"{metric}_mean"
        if subset.empty or column not in subset.columns:
            return float("nan")
        return _finite_float(subset.iloc[0].get(column))

    def stress_effect(scenario: str, column: str) -> float:
        if stress_effects.empty:
            return float("nan")
        subset = stress_effects[stress_effects["scenario"].astype(str) == scenario]
        if subset.empty or column not in subset.columns:
            return float("nan")
        return _finite_float(subset.iloc[0].get(column))

    def nested_value(source: dict[str, Any], *keys: str) -> Any:
        current: Any = source
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    dangerous_runs = 0
    if not threshold_semantic_summary.empty and "dangerous_semantic_runs" in threshold_semantic_summary.columns:
        dangerous_runs = int(pd.to_numeric(threshold_semantic_summary["dangerous_semantic_runs"], errors="coerce").fillna(0).sum())
    max_shared_label_mismatch = float("nan")
    if not threshold_perturbation.empty and "shared_label_mismatch_rate" in threshold_perturbation.columns:
        mismatch = pd.to_numeric(threshold_perturbation["shared_label_mismatch_rate"], errors="coerce").dropna()
        max_shared_label_mismatch = float(mismatch.max()) if not mismatch.empty else float("nan")

    context_overall = val(spatial_context, "overall_rmse_mean")
    report = [
        "# Anchor-only decisive comparison",
        "",
        "This artifact separates the reviewer concern that anchor-only routing can achieve strong NMI/ARI from the stronger claim made for the proposed trainable MoE.",
        "",
        "## Head-to-head result",
        "",
        f"- Strict test semantic agreement: anchor-only NMI/ARI = {_fmt(val(strict_anchor, 'nmi_mean'), 4)}/{_fmt(val(strict_anchor, 'ari_mean'), 4)}; proposed = {_fmt(val(strict_prop, 'nmi_mean'), 4)}/{_fmt(val(strict_prop, 'ari_mean'), 4)}.",
        f"- Strict test forecasting: anchor-only overall/switch/pitch RMSE = {_fmt(val(strict_anchor, 'overall_rmse_mean'))}/{_fmt(val(strict_anchor, 'switch_rmse_mean'))}/{_fmt(val(strict_anchor, 'pitch_control_rmse_mean'))}; proposed = {_fmt(val(strict_prop, 'overall_rmse_mean'))}/{_fmt(val(strict_prop, 'switch_rmse_mean'))}/{_fmt(val(strict_prop, 'pitch_control_rmse_mean'))}.",
        f"- Strict boundary window: anchor-only RMSE/NMI/ARI = {_fmt(val(strict_boundary_anchor, 'rmse_mean'))}/{_fmt(val(strict_boundary_anchor, 'nmi_mean'), 4)}/{_fmt(val(strict_boundary_anchor, 'ari_mean'), 4)}; proposed = {_fmt(val(strict_boundary_prop, 'rmse_mean'))}/{_fmt(val(strict_boundary_prop, 'nmi_mean'), 4)}/{_fmt(val(strict_boundary_prop, 'ari_mean'), 4)}.",
        f"- Future holdout: proposed-only prespecified evidence is complete; no anchor-only future run exists in the current protocol, so this artifact does not claim a future head-to-head win. Proposed future boundary RMSE/NMI/ARI = {_fmt(val(future_boundary_prop, 'rmse_mean'))}/{_fmt(val(future_boundary_prop, 'nmi_mean'), 4)}/{_fmt(val(future_boundary_prop, 'ari_mean'), 4)}.",
        f"- Spatial holdout semantic agreement: anchor-only NMI/ARI = {_fmt(val(spatial_anchor, 'nmi_mean'), 4)}/{_fmt(val(spatial_anchor, 'ari_mean'), 4)}; proposed = {_fmt(val(spatial_prop, 'nmi_mean'), 4)}/{_fmt(val(spatial_prop, 'ari_mean'), 4)}.",
        f"- Spatial holdout forecasting: anchor-only overall/switch RMSE = {_fmt(val(spatial_anchor, 'overall_rmse_mean'))}/{_fmt(val(spatial_anchor, 'switch_rmse_mean'))}; proposed = {_fmt(val(spatial_prop, 'overall_rmse_mean'))}/{_fmt(val(spatial_prop, 'switch_rmse_mean'))}.",
        f"- Spatial boundary window: anchor-only RMSE/NMI/ARI = {_fmt(val(spatial_boundary_anchor, 'rmse_mean'))}/{_fmt(val(spatial_boundary_anchor, 'nmi_mean'), 4)}/{_fmt(val(spatial_boundary_anchor, 'ari_mean'), 4)}; proposed = {_fmt(val(spatial_boundary_prop, 'rmse_mean'))}/{_fmt(val(spatial_boundary_prop, 'nmi_mean'), 4)}/{_fmt(val(spatial_boundary_prop, 'ari_mean'), 4)}.",
        f"- Calibration diagnostic: strict ECE anchor-only/proposed = {_fmt(val(strict_cal_anchor, 'gate_ece_mean'), 4)}/{_fmt(val(strict_cal_prop, 'gate_ece_mean'), 4)}; spatial ECE anchor-only/proposed = {_fmt(val(spatial_cal_anchor, 'gate_ece_mean'), 4)}/{_fmt(val(spatial_cal_prop, 'gate_ece_mean'), 4)}. Because some runs put probability mass on extra experts beyond observed regime labels, this is diagnostic rather than a clean proposed win.",
        f"- Responsibility stability: strict pairwise gate NMI anchor-only/proposed = {_fmt(val(strict_stab_anchor, 'pairwise_gate_nmi_mean'), 4)}/{_fmt(val(strict_stab_prop, 'pairwise_gate_nmi_mean'), 4)}; spatial = {_fmt(val(spatial_stab_anchor, 'pairwise_gate_nmi_mean'), 4)}/{_fmt(val(spatial_stab_prop, 'pairwise_gate_nmi_mean'), 4)}.",
        f"- Spatial efficiency: anchor-only eval seconds/windows per second/train seconds = {_fmt(val(spatial_eff_anchor, 'eval_seconds_mean'))}/{_fmt(val(spatial_eff_anchor, 'windows_per_second_mean'))}/{_fmt(val(spatial_eff_anchor, 'total_train_seconds_mean'))}; proposed = {_fmt(val(spatial_eff_prop, 'eval_seconds_mean'))}/{_fmt(val(spatial_eff_prop, 'windows_per_second_mean'))}/{_fmt(val(spatial_eff_prop, 'total_train_seconds_mean'))}.",
        f"- Spatial failure-case inventory: gate-correct high-error cases = {int(len(spatial_failure))}; boundary gate-correct high-error cases = {int(len(spatial_boundary_failure))}; paired-effect rows = {int(len(spatial_pairs))}.",
        "",
        "## Anchor Perturbation Stress Test",
        "",
        "This replay uses the same strict-cache checkpoints and corrupts only the anchor physics channels at test time. Negative proposed-minus-anchor degradation means the learned router degrades less than anchor-only.",
        "",
        f"- Clean-anchor replay: anchor-only overall/pitch RMSE = {_fmt(stress_val('actual', ANCHOR_ONLY, 'overall_rmse'))}/{_fmt(stress_val('actual', ANCHOR_ONLY, 'pitch_control_rmse'))}; proposed = {_fmt(stress_val('actual', PROPOSED, 'overall_rmse'))}/{_fmt(stress_val('actual', PROPOSED, 'pitch_control_rmse'))}.",
        f"- Boundary anchors missing: RMSE degradation anchor-only/proposed = {_fmt(stress_deg('anchor_boundary_missing', ANCHOR_ONLY, 'delta_overall_rmse'))}/{_fmt(stress_deg('anchor_boundary_missing', PROPOSED, 'delta_overall_rmse'))}; NMI drop anchor-only/proposed = {_fmt(stress_deg('anchor_boundary_missing', ANCHOR_ONLY, 'drop_nmi'), 4)}/{_fmt(stress_deg('anchor_boundary_missing', PROPOSED, 'drop_nmi'), 4)}; seed-paired proposed-minus-anchor overall degradation = {_fmt(stress_effect('anchor_boundary_missing', 'proposed_minus_anchor_only_delta_overall_rmse_mean'))}.",
        f"- Boundary-anchor noise at 0.5 std: RMSE degradation anchor-only/proposed = {_fmt(stress_deg('anchor_boundary_noise_0p5std', ANCHOR_ONLY, 'delta_overall_rmse'))}/{_fmt(stress_deg('anchor_boundary_noise_0p5std', PROPOSED, 'delta_overall_rmse'))}; pitch RMSE degradation anchor-only/proposed = {_fmt(stress_deg('anchor_boundary_noise_0p5std', ANCHOR_ONLY, 'delta_pitch_control_rmse'))}/{_fmt(stress_deg('anchor_boundary_noise_0p5std', PROPOSED, 'delta_pitch_control_rmse'))}; seed-paired proposed-minus-anchor pitch degradation = {_fmt(stress_effect('anchor_boundary_noise_0p5std', 'proposed_minus_anchor_only_delta_pitch_control_rmse_mean'))}.",
        f"- Boundary-fuzzy replay: both routers are effectively unchanged, with seed-paired proposed-minus-anchor overall degradation = {_fmt(stress_effect('boundary_fuzzy', 'proposed_minus_anchor_only_delta_overall_rmse_mean'))}. This scenario is not decisive in the current implementation.",
        "",
        "## Wrong-Threshold Negative Control Gate",
        "",
        f"- Completion: wrong-threshold runs {threshold_evidence_guard.get('complete_runs', 'NA')}/{threshold_evidence_guard.get('expected_runs', 'NA')}; reviewer-stat pack runs {threshold_evidence_guard.get('reviewer_pack_runs', 'NA')}; semantic pairs {threshold_semantic_guard.get('complete_pairs', 'NA')}/{threshold_semantic_guard.get('expected_runs', 'NA')}.",
        f"- Guard status: semantic guard `{threshold_semantic_guard.get('status', 'missing')}`; evidence guard `{threshold_evidence_guard.get('status', 'missing')}`.",
        f"- Semantic extremes: max wrong actual NMI {_fmt(nested_value(threshold_semantic_guard, 'observed', 'max_wrong_actual_nmi'), 4)} versus positive {_fmt(nested_value(threshold_semantic_guard, 'positive_reference', 'actual_nmi_mean'), 4)}; max wrong boundary drop-NMI {_fmt(nested_value(threshold_semantic_guard, 'observed', 'max_wrong_boundary_drop_nmi'), 4)} versus positive {_fmt(nested_value(threshold_semantic_guard, 'positive_reference', 'boundary_drop_nmi_mean'), 4)}.",
        f"- Dangerous semantic-copy runs: {dangerous_runs}. Max shared-valid label-mismatch rate across threshold perturbations: {_fmt(max_shared_label_mismatch, 4)}.",
        "- Interpretation: the current rated-wind/pitch-threshold controls are complete but do not pass the semantic negative-control gate. Their perturbation mainly removes canonical-valid support; it does not relabel shared-valid cells. Do not cite these runs as passed mechanism evidence until a stricter wrong-threshold or label-mismatch control collapses.",
        "",
        "## Interpretation",
        "",
        "Anchor-only is a strong semantic control, not a straw baseline. It wins the strict/spatial NMI and ARI comparison, including the boundary-window NMI/ARI comparison. The proposed model therefore should not be claimed as a universally stronger semantic router.",
        "",
        "The proposed model's defensible advantage is narrower and more useful for the paper: it preserves trainable MoE responsibility assignment, improves the pitch-control slice and spatial held-out-turbine forecasting/efficiency tradeoff against anchor-only, and is far less brittle when boundary anchor channels are noisy. Calibration is not a clean proposed win in the current saved-probability diagnostic. Context-supervised routing is an additional warning: it is strongest on spatial RMSE in this artifact, so the final claim should be framed as mechanism-calibrated routing rather than broad forecasting dominance.",
        "",
        f"For the decisive comparison requested by reviewers: proposed wins over anchor-only on clean pitch-control RMSE by {_fmt(val(strict_anchor, 'pitch_control_rmse_mean') - val(strict_prop, 'pitch_control_rmse_mean'))}, on spatial overall/switch RMSE by {_fmt(val(spatial_anchor, 'overall_rmse_mean') - val(spatial_prop, 'overall_rmse_mean'))}/{_fmt(val(spatial_anchor, 'switch_rmse_mean') - val(spatial_prop, 'switch_rmse_mean'))}, on spatial eval time by {_fmt(val(spatial_eff_anchor, 'eval_seconds_mean') - val(spatial_eff_prop, 'eval_seconds_mean'))} seconds, and under 0.5-std boundary-anchor noise by {_fmt(-stress_effect('anchor_boundary_noise_0p5std', 'proposed_minus_anchor_only_delta_overall_rmse_mean'))} lower overall-RMSE degradation. Anchor-only wins semantic NMI/ARI, strict headline RMSE, and most responsibility-stability diagnostics. Future holdout currently supports only proposed-vs-protocol, not proposed-vs-anchor-only.",
        "",
        "## Output files",
        "",
        "- anchor_only_decisive_metrics.csv",
        "- anchor_only_decisive_deltas.csv",
        "- boundary_window_summary.csv",
        "- boundary_window_effects.csv",
        "- gate_calibration_summary.csv",
        "- responsibility_stability_summary.csv",
        "- guard_status_summary.csv",
        "- failure_case_inventory.csv",
        "- anchor_stress_summary.csv",
        "- anchor_stress_degradation_summary.csv",
        "- anchor_stress_degradation_effects.csv",
        "- threshold_negative_control_summary.csv",
        "",
    ]
    (OUT / "README.md").write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
