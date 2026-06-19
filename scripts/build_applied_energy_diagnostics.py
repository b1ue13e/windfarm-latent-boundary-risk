from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "applied_energy_diagnostics"
DECISION_DIR = ROOT / "artifacts" / "decision_reserve_wtb_operational_windows"
ANCHOR_DIR = ROOT / "artifacts" / "anchor_only_decisive_comparison_20260613"
EXTERNAL_GUARD_DIR = ROOT / "artifacts" / "external_wind_guard"
EXTERNAL_RESCUE_DIR = ROOT / "artifacts" / "external_wind_portability_rescue"
EXTERNAL_ADAPT_DIR = ROOT / "artifacts" / "external_wind_small_calibration_adaptation"
REVIEWER_DIR = ROOT / "artifacts" / "strictmask_combined_reviewer_stats"

DISPLAY_POLICIES = [
    ("Graph WaveNet", "global", "Graph WaveNet/global"),
    ("Graph WaveNet", "physical-bin", "Graph WaveNet/physical-bin"),
    ("Boundary-forced router", "global", "Boundary router/global"),
    ("Boundary-forced router", "gate-bin", "Boundary router/gate-bin"),
]

STAT_CANDIDATES = [
    "Graph WaveNet/physical-bin",
    "PatchTST/global",
    "PatchTST/physical-bin",
    "Physics-Aligned MoE/global",
    "Physics-Aligned MoE/physical-bin",
    "Physics-Aligned MoE/gate-bin",
    "Boundary-forced router/global",
    "Boundary-forced router/physical-bin",
    "Boundary-forced router/gate-bin",
]


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _num(value: Any) -> float:
    out = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(out) if pd.notna(out) else float("nan")


def _fmt(value: Any, digits: int = 2) -> str:
    value_float = _num(value)
    if not np.isfinite(value_float):
        return "NA"
    return f"{value_float:.{digits}f}"


def _fmt_m(value: Any, digits: int = 2) -> str:
    value_float = _num(value)
    if not np.isfinite(value_float):
        return "NA"
    return f"{value_float / 1_000_000.0:.{digits}f}M"


def _fmt_signed_m(value: Any, digits: int = 2) -> str:
    value_float = _num(value)
    if not np.isfinite(value_float):
        return "NA"
    return f"{value_float / 1_000_000.0:+.{digits}f}M"


def _fmt_signed(value: Any, digits: int = 4) -> str:
    value_float = _num(value)
    if not np.isfinite(value_float):
        return "NA"
    return f"{value_float:+.{digits}f}"


def _safe_cell(frame: pd.DataFrame, **conditions: str) -> pd.Series | None:
    if frame.empty:
        return None
    subset = frame.copy()
    for column, value in conditions.items():
        if column not in subset.columns:
            return None
        subset = subset[subset[column].astype(str).eq(str(value))]
    if subset.empty:
        return None
    return subset.iloc[0]


def _delta_outcome(row: pd.Series) -> str:
    cost = _num(row.get("total_cost_mean_delta_vs_model_global"))
    violation = _num(row.get("violation_rate_mean_delta_vs_model_global"))
    shortage = _num(row.get("shortage_energy_mean_delta_vs_model_global"))
    reserve = _num(row.get("reserve_energy_mean_delta_vs_model_global"))
    if all(np.isfinite(value) and value < 0.0 for value in [cost, violation, shortage]):
        if np.isfinite(reserve) and reserve > 0.0:
            return "wins on risk, pays reserve"
        return "operational win"
    if np.isfinite(cost) and cost < 0.0:
        return "cost-only tradeoff"
    if np.isfinite(violation) and violation > 0.0 or np.isfinite(shortage) and shortage > 0.0:
        return "risk loss"
    return "not a win"


def _subset_rows(by_ratio: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if by_ratio.empty:
        return pd.DataFrame()
    frame = by_ratio[
        by_ratio["subset"].astype(str).isin(["full", "boundary"])
        & by_ratio["status"].astype(str).eq("applicable")
    ].copy()
    for subset in ["full", "boundary"]:
        for ratio in sorted(pd.to_numeric(frame["cost_ratio"], errors="coerce").dropna().unique()):
            slice_frame = frame[
                frame["subset"].astype(str).eq(subset)
                & np.isclose(pd.to_numeric(frame["cost_ratio"], errors="coerce").astype(float), float(ratio))
            ].copy()
            for model, policy, label in DISPLAY_POLICIES:
                row = _safe_cell(slice_frame, model=model, policy=policy)
                if row is None:
                    continue
                same_model_global = _safe_cell(slice_frame, model=model, policy="global")
                out = {
                    "subset": subset,
                    "cost_ratio": float(ratio),
                    "policy": label,
                    "model": model,
                    "reserve_policy": policy,
                    "n_runs": int(_num(row.get("n_runs"))),
                    "rmse_mean": _num(row.get("overall_rmse_mean")),
                    "total_cost": _num(row.get("total_cost_mean")),
                    "violation_rate": _num(row.get("violation_rate_mean")),
                    "reserve_energy": _num(row.get("reserve_energy_mean")),
                    "shortage_energy": _num(row.get("shortage_energy_mean")),
                    "best_quantile": str(row.get("best_quantile", "")),
                }
                if same_model_global is not None:
                    for metric in ["total_cost", "violation_rate", "reserve_energy", "shortage_energy"]:
                        col = f"{metric}_mean"
                        out[f"delta_{metric}_vs_same_model_global"] = _num(row.get(col)) - _num(same_model_global.get(col))
                else:
                    for metric in ["total_cost", "violation_rate", "reserve_energy", "shortage_energy"]:
                        out[f"delta_{metric}_vs_same_model_global"] = np.nan
                rows.append(out)
    return pd.DataFrame(rows)


def _main_dispatch_table(by_ratio: pd.DataFrame) -> pd.DataFrame:
    rows = _subset_rows(by_ratio)
    if rows.empty:
        return rows
    main = rows[np.isclose(pd.to_numeric(rows["cost_ratio"], errors="coerce").astype(float), 10.0)].copy()
    main["rmse_penalty_vs_graph_global"] = np.nan
    graph_full = _safe_cell(main, subset="full", policy="Graph WaveNet/global")
    if graph_full is not None:
        graph_rmse = _num(graph_full.get("rmse_mean"))
        main["rmse_penalty_vs_graph_global"] = pd.to_numeric(main["rmse_mean"], errors="coerce") - graph_rmse
    main["decision_reading"] = main.apply(
        lambda row: "system reference"
        if str(row["policy"]) == "Graph WaveNet/global"
        else (
            "physics-stratified graph reference"
            if str(row["policy"]) == "Graph WaveNet/physical-bin"
            else (
                "same-router global reference"
                if str(row["reserve_policy"]) == "global"
                else _delta_outcome(
                    pd.Series(
                        {
                            "total_cost_mean_delta_vs_model_global": row.get(
                                "delta_total_cost_vs_same_model_global"
                            ),
                            "violation_rate_mean_delta_vs_model_global": row.get(
                                "delta_violation_rate_vs_same_model_global"
                            ),
                            "shortage_energy_mean_delta_vs_model_global": row.get(
                                "delta_shortage_energy_vs_same_model_global"
                            ),
                            "reserve_energy_mean_delta_vs_model_global": row.get(
                                "delta_reserve_energy_vs_same_model_global"
                            ),
                        }
                    )
                )
            )
        ),
        axis=1,
    )
    return main.sort_values(["subset", "total_cost", "policy"]).reset_index(drop=True)


def _cost_ratio_table(by_ratio: pd.DataFrame) -> pd.DataFrame:
    rows = _subset_rows(by_ratio)
    if rows.empty:
        return rows
    boundary = rows[rows["subset"].astype(str).eq("boundary")].copy()
    boundary = boundary[boundary["policy"].isin([item[2] for item in DISPLAY_POLICIES])].copy()
    boundary["win_loss"] = boundary.apply(
        lambda row: "reference"
        if str(row["reserve_policy"]) == "global"
        else _delta_outcome(
            pd.Series(
                {
                    "total_cost_mean_delta_vs_model_global": row.get("delta_total_cost_vs_same_model_global"),
                    "violation_rate_mean_delta_vs_model_global": row.get(
                        "delta_violation_rate_vs_same_model_global"
                    ),
                    "shortage_energy_mean_delta_vs_model_global": row.get(
                        "delta_shortage_energy_vs_same_model_global"
                    ),
                    "reserve_energy_mean_delta_vs_model_global": row.get(
                        "delta_reserve_energy_vs_same_model_global"
                    ),
                }
            )
        ),
        axis=1,
    )
    return boundary.sort_values(["cost_ratio", "policy"]).reset_index(drop=True)


def _operational_curve(by_ratio: pd.DataFrame) -> pd.DataFrame:
    rows = _subset_rows(by_ratio)
    if rows.empty:
        return rows
    boundary = rows[rows["subset"].astype(str).eq("boundary")].copy()
    boundary["rmse_penalty_vs_graph_global"] = np.nan
    graph = _safe_cell(boundary, policy="Graph WaveNet/global", cost_ratio="10.0")
    if graph is not None:
        graph_rmse = _num(graph.get("rmse_mean"))
        boundary["rmse_penalty_vs_graph_global"] = pd.to_numeric(boundary["rmse_mean"], errors="coerce") - graph_rmse
    boundary["risk_delta_score"] = (
        pd.to_numeric(boundary["delta_violation_rate_vs_same_model_global"], errors="coerce").fillna(0.0) * 1_000_000.0
        + pd.to_numeric(boundary["delta_shortage_energy_vs_same_model_global"], errors="coerce").fillna(0.0)
    )
    return boundary.sort_values(["cost_ratio", "policy"]).reset_index(drop=True)


def _paired_bootstrap_ci(values: np.ndarray, seed: int = 42, samples: int = 5000) -> tuple[float, float]:
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return float("nan"), float("nan")
    if values.size == 1:
        mean = float(values.mean())
        return mean, mean
    rng = np.random.default_rng(seed)
    draws = np.empty(int(samples), dtype=np.float64)
    for idx in range(draws.size):
        sample = rng.integers(0, values.size, size=values.size)
        draws[idx] = values[sample].mean()
    return float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))


def _paired_sign_permutation_p(values: np.ndarray, seed: int = 43, samples: int = 5000) -> float:
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size <= 1:
        return float("nan")
    observed = abs(float(values.mean()))
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(int(samples)):
        signs = rng.choice(np.array([-1.0, 1.0]), size=values.size)
        if abs(float((values * signs).mean())) >= observed:
            hits += 1
    return float((hits + 1) / (int(samples) + 1))


def _reserve_statistics_table(bootstrap: pd.DataFrame, raw_runs: pd.DataFrame) -> pd.DataFrame:
    if raw_runs.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    metrics = ["total_cost", "violation_rate", "reserve_energy", "shortage_energy"]
    raw = raw_runs[
        raw_runs["subset"].astype(str).eq("full")
        & raw_runs["status"].astype(str).eq("applicable")
        & np.isclose(pd.to_numeric(raw_runs["cost_ratio"], errors="coerce").astype(float), 10.0)
    ].copy()
    base = raw[
        raw["model"].astype(str).eq("Graph WaveNet") & raw["policy"].astype(str).eq("global")
    ].copy()
    for candidate in STAT_CANDIDATES:
        try:
            model, policy = candidate.split("/", 1)
        except ValueError:
            continue
        cand = raw[raw["model"].astype(str).eq(model) & raw["policy"].astype(str).eq(policy)].copy()
        merged = cand.merge(base, on="seed", suffixes=("_candidate", "_baseline"))
        for metric in metrics:
            if merged.empty:
                observed = ci_low = ci_high = prob = p_value = np.nan
                n_pairs = 0
            else:
                diff = (
                    pd.to_numeric(merged[f"{metric}_candidate"], errors="coerce")
                    - pd.to_numeric(merged[f"{metric}_baseline"], errors="coerce")
                ).dropna()
                observed = float(diff.mean()) if not diff.empty else np.nan
                if diff.empty:
                    ci_low = ci_high = prob = p_value = np.nan
                    n_pairs = 0
                else:
                    values = diff.to_numpy(dtype=np.float64)
                    ci_low, ci_high = _paired_bootstrap_ci(values)
                    prob = float((values < 0.0).mean())
                    p_value = _paired_sign_permutation_p(values)
                    n_pairs = int(len(values))
            rows.append(
                {
                    "candidate": candidate,
                    "baseline": "Graph WaveNet/global",
                    "metric": metric,
                    "observed_delta": observed,
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                    "prob_candidate_lower": prob,
                    "paired_sign_permutation_p": p_value,
                    "n_pairs": n_pairs,
                    "interpretation": "candidate lower" if np.isfinite(observed) and observed < 0.0 else "baseline lower",
                }
            )
    return pd.DataFrame(rows)


def _anchor_main_table() -> pd.DataFrame:
    metrics = _read_csv(ANCHOR_DIR / "anchor_only_decisive_metrics.csv")
    degradation = _read_csv(ANCHOR_DIR / "anchor_stress_degradation_summary.csv")
    effects = _read_csv(ANCHOR_DIR / "anchor_stress_degradation_effects.csv")
    if metrics.empty:
        return pd.DataFrame()
    wanted = [
        "MoE + L_bal + L_align + L_force",
        "Anchor-only router",
        "Context-supervised router",
        "Physics-Aligned MoE",
    ]
    rows: list[dict[str, Any]] = []
    strict = metrics[metrics["scenario"].astype(str).eq("strict_test")].copy()
    for model in wanted:
        row = _safe_cell(strict, model=model)
        if row is None:
            continue
        rows.append(
            {
                "model": model,
                "n_runs": int(_num(row.get("n_runs"))),
                "overall_rmse": _num(row.get("overall_rmse_mean")),
                "switch_rmse": _num(row.get("switch_rmse_mean")),
                "pitch_rmse": _num(row.get("pitch_control_rmse_mean")),
                "nmi": _num(row.get("nmi_mean")),
                "ari": _num(row.get("ari_mean")),
                "eval_seconds": _num(row.get("eval_seconds_mean")),
                "train_seconds": _num(row.get("total_train_seconds_mean")),
                "reading": {
                    "MoE + L_bal + L_align + L_force": "trainable responsibility and reserve coupling",
                    "Anchor-only router": "strong semantic rule baseline",
                    "Context-supervised router": "accurate but less boundary-accountable control",
                    "Physics-Aligned MoE": "routed forecasting compromise",
                }.get(model, ""),
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        prop = _safe_cell(out, model="MoE + L_bal + L_align + L_force")
        anchor = _safe_cell(out, model="Anchor-only router")
        if prop is not None and anchor is not None:
            out["delta_pitch_rmse_vs_anchor_only"] = pd.to_numeric(out["pitch_rmse"], errors="coerce") - _num(
                anchor.get("pitch_rmse")
            )
            out["delta_nmi_vs_anchor_only"] = pd.to_numeric(out["nmi"], errors="coerce") - _num(anchor.get("nmi"))
    if not degradation.empty:
        noise_anchor = _safe_cell(
            degradation, scenario="anchor_boundary_noise_0p5std", model="Anchor-only router"
        )
        noise_prop = _safe_cell(
            degradation, scenario="anchor_boundary_noise_0p5std", model="MoE + L_bal + L_align + L_force"
        )
        if noise_anchor is not None and noise_prop is not None:
            out.loc[
                out["model"].astype(str).eq("Anchor-only router"),
                "noise_0p5_overall_rmse_degradation",
            ] = _num(noise_anchor.get("delta_overall_rmse_mean"))
            out.loc[
                out["model"].astype(str).eq("MoE + L_bal + L_align + L_force"),
                "noise_0p5_overall_rmse_degradation",
            ] = _num(noise_prop.get("delta_overall_rmse_mean"))
    if not effects.empty:
        effect = _safe_cell(effects, scenario="anchor_boundary_noise_0p5std")
        if effect is not None:
            out["proposed_minus_anchor_noise_degradation"] = _num(
                effect.get("proposed_minus_anchor_only_delta_overall_rmse_mean")
            )
    return out


def _efficiency_table() -> pd.DataFrame:
    efficiency = _read_csv(REVIEWER_DIR / "efficiency_fairness_table.csv")
    if efficiency.empty:
        return pd.DataFrame()
    aliases = {
        "MoE + L_bal + L_align + L_force": "Boundary-forced router",
        "Physics-Aligned MoE": "Physics-Aligned MoE",
        "Graph WaveNet": "Graph WaveNet",
        "PatchTST": "PatchTST",
    }
    frame = efficiency[efficiency["model"].astype(str).isin(aliases.keys())].copy()
    rows = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "model": aliases[str(row["model"])],
                "n_runs": int(_num(row.get("n_runs"))),
                "parameters": _num(row.get("parameter_count_mean")),
                "train_seconds": _num(row.get("total_train_seconds_mean")),
                "eval_seconds": _num(row.get("eval_seconds_mean")),
                "windows_per_second": _num(row.get("windows_per_second_mean")),
                "deployment_reading": "fastest inference"
                if str(row["model"]) == "PatchTST"
                else (
                    "best strict-cache RMSE, slower"
                    if str(row["model"]) == "Graph WaveNet"
                    else "router adds interpretable responsibility at moderate cost"
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("eval_seconds").reset_index(drop=True)


def _external_negative_table() -> pd.DataFrame:
    guard = _read_json(EXTERNAL_GUARD_DIR / "external_wind_guard.json")
    rescue = _read_json(EXTERNAL_RESCUE_DIR / "rescue_summary.json")
    recal = _read_json(EXTERNAL_RESCUE_DIR / "external_wind_recalibration_guard.json")
    adapt = _read_json(EXTERNAL_ADAPT_DIR / "adaptation_guard.json")
    coverage = _read_csv(EXTERNAL_RESCUE_DIR / "sensor_field_coverage.csv")
    recal_summary = _read_csv(EXTERNAL_RESCUE_DIR / "external_wind_recalibration_summary.csv")
    adapt_summary = _read_csv(EXTERNAL_ADAPT_DIR / "adaptation_summary.csv")

    rows = [
        {
            "evidence_gate": "pre-specified external routing criterion",
            "observed": (
                f"{guard.get('complete_runs', 'NA')}/{guard.get('expected_runs', 'NA')} runs complete; "
                f"mean NMI {_fmt(guard.get('mean_nmi'), 4)} below threshold {_fmt(guard.get('min_nmi'), 2)}; "
                f"mean ARI {_fmt(guard.get('mean_ari'), 4)}"
            ),
            "decision": "failed external-site routing criterion",
            "allowed_claim": "negative boundary-condition evidence only",
        },
        {
            "evidence_gate": "validation-selected local boundary recalibration",
            "observed": (
                f"default test NMI {_fmt(recal.get('mean_default_test_nmi'), 4)} -> "
                f"recalibrated {_fmt(recal.get('mean_recalibrated_test_nmi'), 4)} "
                f"(delta {_fmt_signed(recal.get('mean_test_nmi_recovery'), 4)})"
            ),
            "decision": "small average recovery, not portability",
            "allowed_claim": "local boundary re-estimation is required",
        },
        {
            "evidence_gate": "small calibration-window gate-map adaptation",
            "observed": (
                f"{adapt.get('n_adapted_runs', 'NA')}/{adapt.get('n_routing_runs', 'NA')} routing runs adapted; "
                f"chronological balanced accuracy {_fmt(adapt.get('chronological_adapted_test_balanced_accuracy_mean'), 4)} "
                f"below {_fmt(adapt.get('min_chronological_balanced_accuracy'), 2)}"
            ),
            "decision": "completed negative adaptation diagnostic",
            "allowed_claim": "calibration window is insufficient without held-out pass",
        },
    ]
    if not coverage.empty:
        pen_to_kel = coverage[
            coverage["split_id"].astype(str).eq("leave-one-farm-out")
            & coverage["farm"].astype(str).eq("penmanshiel")
            & coverage["target_farm"].astype(str).eq("kelmarsh")
        ]
        if not pen_to_kel.empty:
            row = pen_to_kel.iloc[0]
            rows.append(
                {
                    "evidence_gate": "sensor and boundary support",
                    "observed": (
                        f"Penmanshiel-to-Kelmarsh leave-one pitch-feature coverage "
                        f"{_fmt(row.get('pitch_feature_coverage'), 4)} and effective boundary cells "
                        f"{_fmt(row.get('effective_boundary_cells'), 0)}"
                    ),
                    "decision": "label not observable in this transfer direction",
                    "allowed_claim": "forbid external physical-router wording",
                }
            )
    if not recal_summary.empty:
        chronological = recal_summary[
            recal_summary["summary_level"].astype(str).eq("split_id+model")
            & recal_summary["split_id"].astype(str).eq("chronological")
            & recal_summary["model"].astype(str).eq("MoE + L_bal + L_align + L_force")
        ]
        if not chronological.empty:
            row = chronological.iloc[0]
            rows.append(
                {
                    "evidence_gate": "chronological-only local recalibration",
                    "observed": (
                        f"boundary router chronological NMI recovery {_fmt_signed(row.get('test_nmi_recovery_mean'), 4)}; "
                        f"held-out test NMI after recalibration {_fmt(row.get('recalibrated_test_nmi_mean'), 4)}"
                    ),
                    "decision": "partial local recovery but still weak",
                    "allowed_claim": "do not generalize beyond locally checked farms",
                }
            )
    if not adapt_summary.empty:
        pen_chrono = adapt_summary[
            adapt_summary["farm"].astype(str).eq("penmanshiel")
            & adapt_summary["split_id"].astype(str).eq("chronological")
            & adapt_summary["model"].astype(str).eq("MoE + L_bal + L_align + L_force")
        ]
        if not pen_chrono.empty:
            row = pen_chrono.iloc[0]
            rows.append(
                {
                    "evidence_gate": "single-site apparent improvement",
                    "observed": (
                        f"Penmanshiel chronological adapted balanced accuracy "
                        f"{_fmt(row.get('adapted_test_balanced_accuracy_mean'), 4)}, "
                        f"but NMI remains {_fmt(row.get('adapted_test_nmi_mean'), 4)}"
                    ),
                    "decision": "not enough for a positive external claim",
                    "allowed_claim": "future work: require held-out criterion before claim",
                }
            )
    return pd.DataFrame(rows)


def _deployment_checklist() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "step": 1,
                "gate": "sensor coverage",
                "pass_condition": "wind speed, active power, availability mask, and pitch/proxy coverage are sufficient",
                "fail_action": "forbid physical routing claim",
            },
            {
                "step": 2,
                "gate": "local boundary calibration",
                "pass_condition": "rated wind, pitch threshold, and boundary band selected on calibration only",
                "fail_action": "treat as boundary-condition diagnostic",
            },
            {
                "step": 3,
                "gate": "held-out routing criterion",
                "pass_condition": "pre-specified NMI/ARI or balanced-accuracy threshold clears on held-out test",
                "fail_action": "local re-estimation required; no generalization wording",
            },
            {
                "step": 4,
                "gate": "reserve audit",
                "pass_condition": "transition-window shortage and violation improve at acceptable reserve-energy cost",
                "fail_action": "do not deploy gate-bin reserve policy",
            },
            {
                "step": 5,
                "gate": "claim decision",
                "pass_condition": "all upstream gates pass",
                "fail_action": "claim allowed only for diagnostics already passed",
            },
        ]
    )


def _claim_boundary_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "claim": "WTB operating-boundary routing accountability",
                "status": "supported",
                "safe_wording": "strict-cache replay, intervention, placebo, spatial holdout, future holdout, and reserve audit support within-WTB boundary routing",
            },
            {
                "claim": "headline forecasting dominance",
                "status": "not supported",
                "safe_wording": "Graph WaveNet and lag-feature baselines remain stronger RMSE forecasters; routed model pays an explicit error penalty",
            },
            {
                "claim": "gate-bin reserve policy",
                "status": "conditional",
                "safe_wording": "use only as a transition-window reserve diagnostic; gate-bin wins at moderate cost ratios and loses in high-ramp or very high-penalty settings",
            },
            {
                "claim": "anchor-only/router-rule replacement",
                "status": "not supported as a straw baseline",
                "safe_wording": "anchor-only is semantically strong; proposed advantage is trainable responsibility, forecast/reserve coupling, and lower anchor-noise brittleness",
            },
            {
                "claim": "external wind-farm portability",
                "status": "not supported",
                "safe_wording": "Kelmarsh/Penmanshiel are negative evidence requiring local boundary re-estimation and held-out routing gates",
            },
            {
                "claim": "future holdout versus post-hoc time-forward",
                "status": "separated",
                "safe_wording": "pre-specified future holdout is citable stress evidence; late test slicing remains failure analysis for distribution shift",
            },
        ]
    )


def _operator_case_table(boundary_slices: pd.DataFrame, reviewer_failures: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    if not boundary_slices.empty:
        mppt_global = _safe_cell(boundary_slices, subset="mppt_to_pitch", model="Boundary-forced router", policy="global")
        mppt_gate = _safe_cell(boundary_slices, subset="mppt_to_pitch", model="Boundary-forced router", policy="gate-bin")
        high_global = _safe_cell(boundary_slices, subset="high_ramp", model="Boundary-forced router", policy="global")
        high_gate = _safe_cell(boundary_slices, subset="high_ramp", model="Boundary-forced router", policy="gate-bin")
        if mppt_global is not None and mppt_gate is not None:
            rows.append(
                {
                    "case": "MPPT-to-pitch reserve",
                    "observed_numbers": (
                        f"global cost {_fmt_m(mppt_global.get('total_cost_mean'))}, violation {_fmt(mppt_global.get('violation_rate_mean'), 4)}, shortage {_fmt_m(mppt_global.get('shortage_energy_mean'))}; "
                        f"gate-bin cost {_fmt_m(mppt_gate.get('total_cost_mean'))}, violation {_fmt(mppt_gate.get('violation_rate_mean'), 4)}, shortage {_fmt_m(mppt_gate.get('shortage_energy_mean'))}"
                    ),
                    "operator_reading": "gate-bin lowers transition-window violation and shortage but costs more reserve",
                    "claim_boundary": "boundary-window diagnostic, not global reserve optimization",
                }
            )
        if high_global is not None and high_gate is not None:
            rows.append(
                {
                    "case": "high-ramp reserve",
                    "observed_numbers": (
                        f"global violation {_fmt(high_global.get('violation_rate_mean'), 4)}, shortage {_fmt_m(high_global.get('shortage_energy_mean'))}, reserve {_fmt_m(high_global.get('reserve_energy_mean'))}; "
                        f"gate-bin violation {_fmt(high_gate.get('violation_rate_mean'), 4)}, shortage {_fmt_m(high_gate.get('shortage_energy_mean'))}, reserve {_fmt_m(high_gate.get('reserve_energy_mean'))}"
                    ),
                    "operator_reading": "gate-bin can look cheaper by carrying too little reserve",
                    "claim_boundary": "failure slice; require ramp-specific checks",
                }
            )
    if not reviewer_failures.empty:
        case = reviewer_failures.iloc[0]
        rows.append(
            {
                "case": "gate-correct but forecast-bad",
                "observed_numbers": (
                    f"model {case.get('model', 'NA')}, seed {case.get('seed', 'NA')}, "
                    f"gate_correct {case.get('gate_correct', 'NA')}, RMSE {_fmt(case.get('rmse'), 2)}"
                ),
                "operator_reading": "right responsibility assignment does not guarantee an accurate value map",
                "claim_boundary": "mechanism accountability, not dispatch-ready point forecasting",
            }
        )
    return pd.DataFrame(rows)


def _write_simple_tex(
    frame: pd.DataFrame,
    path: Path,
    columns: list[tuple[str, str]],
    *,
    resize: bool = False,
) -> None:
    align = "l" * len(columns)
    lines = [f"\\begin{{tabular}}{{{align}}}", "\\toprule"]
    lines.append(" & ".join(_latex_escape(header) for _, header in columns) + " \\\\")
    lines.append("\\midrule")
    for _, row in frame.iterrows():
        values = [_latex_escape(str(row.get(column, ""))) for column, _ in columns]
        lines.append(" & ".join(values) + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    text = "\n".join(lines) + "\n"
    if resize:
        text = "\\resizebox{\\linewidth}{!}{%\n" + text + "}\n"
    path.write_text(text, encoding="utf-8")


def _latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


def _display_main_dispatch(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "Subset": str(row["subset"]),
                "Policy": str(row["policy"]),
                "RMSE penalty": _fmt_signed(row.get("rmse_penalty_vs_graph_global"), 2),
                "Q": str(row.get("best_quantile", "")).replace(";", ", "),
                "Cost": _fmt_m(row.get("total_cost")),
                "Violation": _fmt(row.get("violation_rate"), 4),
                "Reserve": _fmt_m(row.get("reserve_energy")),
                "Shortage": _fmt_m(row.get("shortage_energy")),
                "Reading": str(row.get("decision_reading", "")),
            }
        )
    return pd.DataFrame(rows)


def _display_cost_ratio(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    keep = {
        "Graph WaveNet/global",
        "Graph WaveNet/physical-bin",
        "Boundary router/global",
        "Boundary router/gate-bin",
    }
    for _, row in frame[frame["policy"].astype(str).isin(keep)].iterrows():
        rows.append(
            {
                "Ratio": _fmt(row.get("cost_ratio"), 0),
                "Policy": str(row.get("policy")),
                "Q": str(row.get("best_quantile", "")).replace(";", ", "),
                "Cost": _fmt_m(row.get("total_cost")),
                "Violation": _fmt(row.get("violation_rate"), 4),
                "Reserve": _fmt_m(row.get("reserve_energy")),
                "Shortage": _fmt_m(row.get("shortage_energy")),
                "Vs global": str(row.get("win_loss", "")),
            }
        )
    return pd.DataFrame(rows)


def _display_stats(frame: pd.DataFrame) -> pd.DataFrame:
    priority = frame[
        frame["candidate"].isin(
            [
                "Graph WaveNet/physical-bin",
                "Physics-Aligned MoE/gate-bin",
                "Boundary-forced router/gate-bin",
                "Boundary-forced router/global",
            ]
        )
        & frame["metric"].isin(["total_cost", "violation_rate", "reserve_energy", "shortage_energy"])
    ].copy()
    rows = []
    for _, row in priority.iterrows():
        is_energy = str(row["metric"]) in {"total_cost", "reserve_energy", "shortage_energy"}
        rows.append(
            {
                "Candidate": str(row["candidate"]),
                "Metric": str(row["metric"]),
                "Delta": _fmt_signed_m(row.get("observed_delta")) if is_energy else _fmt_signed(row.get("observed_delta")),
                "95% CI": (
                    f"[{_fmt_signed_m(row.get('ci_low'))}, {_fmt_signed_m(row.get('ci_high'))}]"
                    if is_energy
                    else f"[{_fmt_signed(row.get('ci_low'))}, {_fmt_signed(row.get('ci_high'))}]"
                ),
                "P(lower)": _fmt(row.get("prob_candidate_lower"), 3),
                "Perm p": _fmt(row.get("paired_sign_permutation_p"), 3),
            }
        )
    return pd.DataFrame(rows)


def _display_anchor(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "Model": str(row.get("model")),
                "Overall": _fmt(row.get("overall_rmse"), 2),
                "Pitch": _fmt(row.get("pitch_rmse"), 2),
                "NMI/ARI": f"{_fmt(row.get('nmi'), 4)}/{_fmt(row.get('ari'), 4)}",
                "Noise degrade": _fmt(row.get("noise_0p5_overall_rmse_degradation"), 2),
                "Reading": str(row.get("reading", "")),
            }
        )
    return pd.DataFrame(rows)


def _display_efficiency(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "Model": str(row.get("model")),
                "Params": _fmt(row.get("parameters"), 0),
                "Train h": _fmt(_num(row.get("train_seconds")) / 3600.0, 2),
                "Eval s": _fmt(row.get("eval_seconds"), 2),
                "Win/s": _fmt(row.get("windows_per_second"), 1),
                "Reading": str(row.get("deployment_reading", "")),
            }
        )
    return pd.DataFrame(rows)


def _plot_decision_curve(curve: pd.DataFrame, output_path: Path) -> None:
    if curve.empty:
        return
    fig, ax1 = plt.subplots(figsize=(9.2, 5.4))
    subset = curve[curve["policy"].isin([item[2] for item in DISPLAY_POLICIES])].copy()
    colors = {
        "Graph WaveNet/global": "#2563eb",
        "Graph WaveNet/physical-bin": "#0f766e",
        "Boundary router/global": "#7c2d12",
        "Boundary router/gate-bin": "#dc2626",
    }
    for policy, group in subset.groupby("policy", sort=False):
        group = group.sort_values("cost_ratio")
        ax1.plot(
            group["cost_ratio"],
            group["shortage_energy"] / 1_000_000.0,
            marker="o",
            linewidth=2.0,
            color=colors.get(policy, "#374151"),
            label=f"{policy}: shortage",
        )
    ax1.set_xlabel("Shortage penalty / reserve cost")
    ax1.set_ylabel("Boundary shortage energy (M)")
    ax1.grid(True, alpha=0.25)

    ax2 = ax1.twinx()
    gate = subset[subset["policy"].eq("Boundary router/gate-bin")].sort_values("cost_ratio")
    if not gate.empty:
        ax2.plot(
            gate["cost_ratio"],
            gate["reserve_energy"] / 1_000_000.0,
            marker="s",
            linestyle="--",
            linewidth=1.7,
            color="#111827",
            label="Boundary gate-bin: reserve",
        )
        rmse_penalty = float(pd.to_numeric(gate["rmse_penalty_vs_graph_global"], errors="coerce").dropna().mean())
        ax2.axhline(
            gate["reserve_energy"].mean() / 1_000_000.0,
            linestyle=":",
            color="#6b7280",
            linewidth=1.2,
            label=f"RMSE penalty vs Graph WaveNet: {rmse_penalty:.2f}",
        )
    ax2.set_ylabel("Reserve energy (M)")

    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(
        lines + lines2,
        labels + labels2,
        fontsize=7,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.22),
        ncol=2,
        frameon=True,
    )
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.88))
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_deployment_checklist(checklist: pd.DataFrame, output_path: Path) -> None:
    if checklist.empty:
        return
    fig, ax = plt.subplots(figsize=(10.0, 3.2))
    ax.axis("off")
    x_positions = np.linspace(0.06, 0.94, len(checklist))
    y = 0.55
    for idx, (_, row) in enumerate(checklist.iterrows()):
        x = x_positions[idx]
        ax.text(
            x,
            y,
            f"{int(row['step'])}. {row['gate']}",
            ha="center",
            va="center",
            fontsize=9,
            color="#111827",
            bbox={
                "boxstyle": "round,pad=0.32,rounding_size=0.08",
                "facecolor": "#f8fafc",
                "edgecolor": "#64748b",
                "linewidth": 1.0,
            },
        )
        ax.text(
            x,
            0.20,
            str(row["fail_action"]),
            ha="center",
            va="center",
            fontsize=7,
            color="#7f1d1d",
            wrap=True,
        )
        if idx < len(checklist) - 1:
            ax.annotate(
                "",
                xy=(x_positions[idx + 1] - 0.07, y),
                xytext=(x + 0.07, y),
                arrowprops={"arrowstyle": "->", "lw": 1.3, "color": "#475569"},
            )
    ax.text(
        0.5,
        0.90,
        "New wind-farm deployment gate: allowed claim requires every upstream gate to pass",
        ha="center",
        va="center",
        fontsize=11,
        weight="bold",
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    by_ratio = _read_csv(DECISION_DIR / "reserve_decision_by_ratio.csv")
    raw_runs = _read_csv(DECISION_DIR / "reserve_decision_raw_runs.csv")
    bootstrap = _read_csv(DECISION_DIR / "reserve_decision_bootstrap.csv")
    boundary_slices = _read_csv(DECISION_DIR / "reserve_decision_boundary_slices.csv")
    reviewer_failures = _read_csv(REVIEWER_DIR / "failure_cases_boundary_gate_correct_bad.csv")

    dispatch = _main_dispatch_table(by_ratio)
    cost_ratio = _cost_ratio_table(by_ratio)
    curve = _operational_curve(by_ratio)
    stats = _reserve_statistics_table(bootstrap, raw_runs)
    anchor = _anchor_main_table()
    efficiency = _efficiency_table()
    external = _external_negative_table()
    checklist = _deployment_checklist()
    claims = _claim_boundary_table()
    operator_cases = _operator_case_table(boundary_slices, reviewer_failures)

    outputs = {
        "dispatch_reserve_main_table.csv": dispatch,
        "dispatch_reserve_cost_ratio_table.csv": cost_ratio,
        "cost_ratio_sensitivity_readable.csv": _display_cost_ratio(cost_ratio),
        "operational_decision_curve.csv": curve,
        "reserve_paired_statistics.csv": stats,
        "anchor_only_rule_router_main_table.csv": anchor,
        "compute_deployment_cost_table.csv": efficiency,
        "external_negative_evidence_table.csv": external,
        "external_site_transfer_failure_table.csv": external,
        "new_wind_farm_deployment_checklist.csv": checklist,
        "claim_boundary_applied_energy.csv": claims,
        "operational_case_explanation.csv": operator_cases,
    }
    for filename, frame in outputs.items():
        frame.to_csv(OUT / filename, index=False)

    _write_simple_tex(
        _display_main_dispatch(dispatch),
        OUT / "table_dispatch_reserve_main.tex",
        [
            ("Subset", "Subset"),
            ("Policy", "Policy"),
            ("RMSE penalty", "RMSE penalty"),
            ("Q", "Q"),
            ("Cost", "Cost"),
            ("Violation", "Violation"),
            ("Reserve", "Reserve"),
            ("Shortage", "Shortage"),
            ("Reading", "Reading"),
        ],
        resize=True,
    )
    _write_simple_tex(
        _display_cost_ratio(cost_ratio),
        OUT / "table_cost_ratio_sensitivity_readable.tex",
        [
            ("Ratio", "Ratio"),
            ("Policy", "Policy"),
            ("Q", "Q"),
            ("Cost", "Cost"),
            ("Violation", "Violation"),
            ("Reserve", "Reserve"),
            ("Shortage", "Shortage"),
            ("Vs global", "Vs global"),
        ],
        resize=True,
    )
    _write_simple_tex(
        _display_stats(stats),
        OUT / "table_reserve_paired_statistics.tex",
        [
            ("Candidate", "Candidate"),
            ("Metric", "Metric"),
            ("Delta", "Delta"),
            ("95% CI", "95% CI"),
            ("P(lower)", "P(lower)"),
            ("Perm p", "Perm p"),
        ],
        resize=True,
    )
    _write_simple_tex(
        _display_anchor(anchor),
        OUT / "table_anchor_only_rule_router_main.tex",
        [
            ("Model", "Model"),
            ("Overall", "Overall"),
            ("Pitch", "Pitch"),
            ("NMI/ARI", "NMI/ARI"),
            ("Noise degrade", "Noise degrade"),
            ("Reading", "Reading"),
        ],
        resize=True,
    )
    _write_simple_tex(
        _display_efficiency(efficiency),
        OUT / "table_compute_deployment_cost.tex",
        [
            ("Model", "Model"),
            ("Params", "Params"),
            ("Train h", "Train h"),
            ("Eval s", "Eval s"),
            ("Win/s", "Win/s"),
            ("Reading", "Reading"),
        ],
        resize=True,
    )
    _write_simple_tex(
        external,
        OUT / "table_external_site_transfer_failure.tex",
        [
            ("evidence_gate", "Evidence gate"),
            ("observed", "Observed"),
            ("decision", "Decision"),
            ("allowed_claim", "Allowed claim"),
        ],
        resize=True,
    )
    _write_simple_tex(
        claims,
        OUT / "table_claim_boundary_applied_energy.tex",
        [
            ("claim", "Claim"),
            ("status", "Status"),
            ("safe_wording", "Safe wording"),
        ],
        resize=True,
    )
    _write_simple_tex(
        operator_cases,
        OUT / "table_operational_case_explanation.tex",
        [
            ("case", "Case"),
            ("observed_numbers", "Observed"),
            ("operator_reading", "Operator reading"),
            ("claim_boundary", "Claim boundary"),
        ],
        resize=True,
    )

    _plot_decision_curve(curve, OUT / "operational_decision_curve.png")
    _plot_deployment_checklist(checklist, OUT / "new_wind_farm_deployment_checklist.png")

    report = [
        "# Applied Energy diagnostics",
        "",
        "This package is generated from saved strict-cache artifacts and does not retrain models.",
        "",
        "## Main outputs",
        "",
        "- `dispatch_reserve_main_table.csv` and `table_dispatch_reserve_main.tex`: same-table dispatch/reserve comparison at cost ratio 10.",
        "- `operational_decision_curve.png`: RMSE penalty, reserve energy, and shortage tradeoff on the boundary window.",
        "- `reserve_paired_statistics.csv`: paired bootstrap/permutation-style uncertainty summaries for reserve cost and risk metrics.",
        "- `anchor_only_rule_router_main_table.csv`: formal anchor-only/router-rule comparison.",
        "- `external_negative_evidence_table.csv`: external Kelmarsh/Penmanshiel negative evidence and allowed claims.",
        "- `new_wind_farm_deployment_checklist.png`: deployment gate from sensor coverage to allowed/forbidden claims.",
        "",
        "## Claim summary",
        "",
        "Gate-bin reserve is a conditional transition-window diagnostic. It wins when moderate shortage penalties make boundary shortage and violations worth extra reserve; it loses when high-ramp or very high-penalty settings make the same-model global policy safer.",
    ]
    (OUT / "README.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
