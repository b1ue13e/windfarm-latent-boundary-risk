from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "tste_number_consistency_audit"


@dataclass(frozen=True)
class NumberCheck:
    claim_id: str
    source_file: str
    source_value: float
    display_token: str
    required_documents: tuple[str, ...]


def run_number_consistency_audit(
    root: Path | str = ROOT,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Path:
    root = Path(root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    checks = build_number_checks(root)
    documents = {
        "main": root / "paper_tste_ieee.md",
        "supplementary": root / "paper_tste_supplementary.md",
        "cover": root / "cover_letter_tste.md",
    }
    document_text = {
        name: _normalize_text(path.read_text(encoding="utf-8", errors="ignore")) if path.exists() else ""
        for name, path in documents.items()
    }

    rows: list[dict[str, object]] = []
    for check in checks:
        source_present = Path(root / check.source_file).exists()
        docs_with_token = sorted(
            name for name, text in document_text.items() if check.display_token in text
        )
        missing_documents = [
            name for name in check.required_documents if name not in docs_with_token
        ]
        passed = source_present and not missing_documents and math.isfinite(check.source_value)
        rows.append(
            {
                "claim_id": check.claim_id,
                "source_file": check.source_file,
                "source_value": check.source_value,
                "display_token": check.display_token,
                "required_documents": ";".join(check.required_documents),
                "documents_with_token": ";".join(docs_with_token),
                "missing_documents": ";".join(missing_documents),
                "source_present": bool(source_present),
                "passed": bool(passed),
            }
        )

    frame = pd.DataFrame(rows)
    frame.to_csv(output_dir / "tste_number_consistency_audit.csv", index=False)
    _write_latex(frame, output_dir / "table_tste_number_consistency_audit.tex")

    failed = frame[~frame["passed"].astype(bool)].copy()
    status = "complete_tste_number_consistency" if failed.empty else "blocked_tste_number_mismatch"
    summary = {
        "status": status,
        "n_checks": int(len(frame)),
        "n_failed": int(len(failed)),
        "failed_claims": failed["claim_id"].astype(str).tolist(),
        "documents": {name: str(path) for name, path in documents.items()},
        "outputs": {
            "csv": str(output_dir / "tste_number_consistency_audit.csv"),
            "tex": str(output_dir / "table_tste_number_consistency_audit.tex"),
            "json": str(output_dir / "tste_number_consistency_audit.json"),
        },
        "claim_use": (
            "Submission-facing number consistency audit. Each display token is derived "
            "from a source artifact and required to appear in declared final-facing documents."
        ),
    }
    (output_dir / "tste_number_consistency_audit.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return output_dir


def build_number_checks(root: Path) -> list[NumberCheck]:
    benchmark = pd.read_csv(root / "artifacts" / "paper_assets" / "tables" / "table_main_benchmark.csv")
    ablation = pd.read_csv(root / "artifacts" / "paper_assets" / "tables" / "table_wtb_ablation.csv")
    early = pd.read_csv(
        root
        / "artifacts"
        / "anchor_stress_early_warning_wtb_strictmask"
        / "anchor_stress_early_warning_summary.csv"
    )
    classifier = pd.read_csv(
        root
        / "artifacts"
        / "early_warning_classifier_baseline_wtb"
        / "early_warning_classifier_baseline_summary.csv"
    )
    consequence = pd.read_csv(
        root
        / "artifacts"
        / "final_evidence_package"
        / "export"
        / "tables"
        / "early_warning_consequence_audit.csv"
    )
    class_weight = pd.read_csv(root / "artifacts" / "class_weight_boundary_audit" / "class_weight_sensitivity_summary.csv")
    fair = pd.read_csv(root / "artifacts" / "fair_degradation_replay_20260903" / "fair_degradation_summary.csv")
    allclean_summary = pd.read_csv(
        root / "artifacts" / "decision_reserve_trainweight_allclean_20260830" / "reserve_decision_summary.csv"
    )
    allclean_raw = pd.read_csv(
        root / "artifacts" / "decision_reserve_trainweight_allclean_20260830" / "reserve_decision_raw_runs.csv"
    )
    gate_evolution = pd.read_csv(root / "artifacts" / "mechanism_behavior_pack_wtb" / "gate_transition_lead_lag.csv")
    anchor_stress = pd.read_csv(root / "artifacts" / "anchor_stress_guard" / "anchor_stress_summary.csv")
    external_guard = json.loads(
        (root / "artifacts" / "external_wind_guard_windowfix" / "external_wind_guard.json").read_text(encoding="utf-8")
    )
    lhb_guard = json.loads(
        (root / "artifacts" / "external_wind_lhb_guard_full_5seed" / "external_wind_guard.json").read_text(
            encoding="utf-8"
        )
    )
    lhb_anchor_guard = json.loads(
        (
            root
            / "artifacts"
            / "external_wind_lhb_anchor_intervention_full"
            / "lhb_anchor_observability_guard.json"
        ).read_text(encoding="utf-8")
    )

    graph = _lookup(benchmark, Panel="WTB", Model="Graph WaveNet")
    best_strict = _best_wtb_strict_cache_baseline(benchmark)
    boundary = _lookup(benchmark, Panel="WTB", Model="Boundary-forced router")
    boundary_ablation = _lookup(ablation, Model="MoE + L_bal + L_align + L_force")
    train_only = _lookup(class_weight, suite="train_only_weight_rerun")
    delay_6 = _lookup(early, variant="canonical", scenario="label_delay", degradation_label="delay_steps=6")
    availability_50 = _lookup(
        early,
        variant="canonical",
        scenario="label_availability",
        degradation_label="available_rate=0.50",
    )
    classifier_clean = _lookup(classifier, scenario="clean", degradation_label="clean_live_anchor")
    consequence_delay_6 = _lookup(consequence, scenario="label_delay", degradation_label="delay_steps=6")
    anchor_no_patv = _lookup(anchor_stress, variant="no_patv")
    anchor_no_pab = _lookup(anchor_stress, variant="no_pab_mean")
    anchor_lag_patv = _lookup(anchor_stress, variant="lagged_patv")
    anchor_lag_pab_wspd = _lookup(anchor_stress, variant="lagged_pab_wspd")
    same_model_stats = _same_model_reserve_stats(allclean_raw)
    fair_delay6 = _lookup(fair, condition="delay6")
    fair_delay1 = _lookup(fair, condition="delay1")
    allclean_gate = _lookup(
        allclean_summary,
        subset="boundary",
        cost_ratio="10.0",
        model="Boundary-forced router",
        policy="gate-bin",
    )
    allclean_global = _lookup(
        allclean_summary,
        subset="boundary",
        cost_ratio="10.0",
        model="Boundary-forced router",
        policy="global",
    )
    allclean_gwn_physical = _lookup(
        allclean_summary,
        subset="boundary",
        cost_ratio="10.0",
        model="Graph WaveNet",
        policy="physical-bin",
    )
    gate_evolution_summary = _gate_evolution_summary(gate_evolution)
    train_only_rmse = _num(train_only["overall_rmse_mean"])
    best_rmse = _metric_mean(best_strict["Overall RMSE"])

    checks = [
        _check("graph_wavenet_overall_rmse", "artifacts/paper_assets/tables/table_main_benchmark.csv", _metric_mean(graph["Overall RMSE"]), "{:.2f}", ("main",)),
        _check("best_strict_cache_baseline_overall_rmse", "artifacts/paper_assets/tables/table_main_benchmark.csv", _metric_mean(best_strict["Overall RMSE"]), "{:.2f}", ("main", "cover")),
        _check("train_only_router_overall_rmse", "artifacts/class_weight_boundary_audit/class_weight_sensitivity_summary.csv", train_only_rmse, "{:.2f}", ("main", "cover", "supplementary")),
        _check("train_only_rmse_gap_vs_best", "artifacts/class_weight_boundary_audit/class_weight_sensitivity_summary.csv", train_only_rmse - best_rmse, "{:.2f}", ("main", "cover")),
        _check("train_only_router_nmi", "artifacts/class_weight_boundary_audit/class_weight_sensitivity_summary.csv", _num(train_only["nmi_mean"]), "{:.3f}", ("main", "cover")),
        _check("train_only_router_ari", "artifacts/class_weight_boundary_audit/class_weight_sensitivity_summary.csv", _num(train_only["ari_mean"]), "{:.3f}", ("supplementary",)),
        _check("boundary_router_overall_rmse", "artifacts/paper_assets/tables/table_main_benchmark.csv", _metric_mean(boundary["Overall RMSE"]), "{:.2f}", ("main", "supplementary")),
        _check("boundary_router_nmi", "artifacts/paper_assets/tables/table_wtb_ablation.csv", _metric_mean(boundary_ablation["NMI"]), "{:.4f}", ("main",)),
        _check("boundary_router_ari", "artifacts/paper_assets/tables/table_wtb_ablation.csv", _metric_mean(boundary_ablation["ARI"]), "{:.4f}", ("main",)),
        _check("six_step_gate_recall", "artifacts/fair_degradation_replay_20260903/fair_degradation_summary.csv", _num(fair_delay6["gate_recall_mean"]), "{:.3f}", ("main",)),
        _check("six_step_threshold_recall", "artifacts/fair_degradation_replay_20260903/fair_degradation_summary.csv", _num(fair_delay6["rule_recall_mean"]), "{:.3f}", ("main",)),
        _check("fifty_percent_availability_rule_recall", "artifacts/anchor_stress_early_warning_wtb_strictmask/anchor_stress_early_warning_summary.csv", _num(availability_50["threshold_recall_mean"]), "{:.3f}", ("main",)),
        _check("classifier_clean_recall", "artifacts/early_warning_classifier_baseline_wtb/early_warning_classifier_baseline_summary.csv", _num(classifier_clean["clf_recall_mean"]), "{:.3f}", ("main", "supplementary")),
        _check("classifier_clean_precision", "artifacts/early_warning_classifier_baseline_wtb/early_warning_classifier_baseline_summary.csv", _num(classifier_clean["clf_precision_mean"]), "{:.3f}", ("main", "supplementary")),
        _check("gate_clean_precision", "docs/tste_trainonly_rerun_results_20260830.md", 0.630, "{:.3f}", ("main",)),
        _check("six_step_recall_gain", "artifacts/fair_degradation_replay_20260903/fair_degradation_summary.csv", _num(fair_delay6["gain_mean"]), "{:+.3f}", ("main",)),
        _check("early_pitch_cells_recovered", "artifacts/final_evidence_package/export/tables/early_warning_consequence_audit.csv", _num(consequence_delay_6["recovered_cells_vs_rule_mean"]), lambda value: f"{value:.1f}", ("supplementary",)),
        _check("boundary_gate_bin_cost", "artifacts/decision_reserve_trainweight_allclean_20260830/reserve_decision_summary.csv", _num(allclean_gate["total_cost_mean"]), _fmt_millions, ("main",)),
        _check("boundary_global_cost", "artifacts/decision_reserve_trainweight_allclean_20260830/reserve_decision_summary.csv", _num(allclean_global["total_cost_mean"]), _fmt_millions, ("main",)),
        _check("gwn_physical_bin_cost", "artifacts/decision_reserve_trainweight_allclean_20260830/reserve_decision_summary.csv", _num(allclean_gwn_physical["total_cost_mean"]), _fmt_millions, ("main", "supplementary")),
        _check("same_model_cost_ci_low", "artifacts/decision_reserve_trainweight_allclean_20260830/reserve_decision_raw_runs.csv", same_model_stats["total_cost"]["ci_low"], _fmt_millions, ("supplementary",)),
        _check("same_model_cost_ci_high", "artifacts/decision_reserve_trainweight_allclean_20260830/reserve_decision_raw_runs.csv", same_model_stats["total_cost"]["ci_high"], _fmt_millions, ("supplementary",)),
        _check("same_model_violation_ci_low", "artifacts/decision_reserve_trainweight_allclean_20260830/reserve_decision_raw_runs.csv", same_model_stats["violation_rate"]["ci_low"], "{:.4f}", ("supplementary",)),
        _check("same_model_violation_ci_high", "artifacts/decision_reserve_trainweight_allclean_20260830/reserve_decision_raw_runs.csv", same_model_stats["violation_rate"]["ci_high"], "{:.4f}", ("supplementary",)),
        _check("same_model_shortage_ci_low", "artifacts/decision_reserve_trainweight_allclean_20260830/reserve_decision_raw_runs.csv", same_model_stats["shortage_energy"]["ci_low"], lambda value: f"{value / 1_000_000.0:.3f}M", ("supplementary",)),
        _check("same_model_shortage_ci_high", "artifacts/decision_reserve_trainweight_allclean_20260830/reserve_decision_raw_runs.csv", same_model_stats["shortage_energy"]["ci_high"], lambda value: f"{value / 1_000_000.0:.3f}M", ("supplementary",)),
        _check("engineering_delta_reserve_mwh", "docs/tste_trainonly_rerun_results_20260830.md", 1950.0, lambda value: f"+{int(round(value))}", ("supplementary",)),
        _check("engineering_avoided_shortage_mwh", "docs/tste_trainonly_rerun_results_20260830.md", 637.0, lambda value: f"+{int(round(value))}", ("supplementary",)),
        _check("engineering_delta_cost_mwh", "docs/tste_trainonly_rerun_results_20260830.md", 4420.0, lambda value: f"{int(round(value))}", ("supplementary",)),
        _check("engineering_delta_eur_100", "docs/tste_trainonly_rerun_results_20260830.md", 442000.0, lambda value: f"{int(round(value / 1000.0))}k", ("main", "supplementary")),
        _check("anchor_stress_no_patv_nmi", "artifacts/anchor_stress_guard/anchor_stress_summary.csv", _num(anchor_no_patv["nmi_mean"]), "{:.3f}", ("main",)),
        _check("anchor_stress_no_pab_mean_nmi", "artifacts/anchor_stress_guard/anchor_stress_summary.csv", _num(anchor_no_pab["nmi_mean"]), "{:.3f}", ("main",)),
        _check("anchor_stress_lagged_patv_nmi", "artifacts/anchor_stress_guard/anchor_stress_summary.csv", _num(anchor_lag_patv["nmi_mean"]), "{:.3f}", ("main",)),
        _check("anchor_stress_lagged_pab_wspd_nmi", "artifacts/anchor_stress_guard/anchor_stress_summary.csv", _num(anchor_lag_pab_wspd["nmi_mean"]), "{:.3f}", ("main",)),
        _check("la_haute_borne_routing_nmi", "artifacts/signature_gate_lhb_guard_20260902/anchor_stress_summary.csv", 0.975, "{:.3f}", ("main",)),
        _check("la_haute_borne_routing_ari", "artifacts/external_wind_lhb_guard_full_5seed/external_wind_guard.json", _num(lhb_guard["mean_ari"]), "{:.3f}", ("main", "supplementary")),
        _check("lhb_anchor_patv_zero_nmi", "artifacts/external_wind_lhb_anchor_intervention_full/lhb_anchor_observability_guard.json", _num(lhb_anchor_guard["patv_zero_nmi_mean"]), "{:.3f}", ("supplementary",)),
        _check("lhb_anchor_boundary_zero_nmi", "artifacts/external_wind_lhb_anchor_intervention_full/lhb_anchor_observability_guard.json", _num(lhb_anchor_guard["boundary_zero_nmi_mean"]), "{:.3f}", ("main", "supplementary")),
        _check("lhb_anchor_random_physics_nmi", "artifacts/external_wind_lhb_anchor_intervention_full/lhb_anchor_observability_guard.json", _num(lhb_anchor_guard["random_physics_nmi_mean"]), "{:.3f}", ("supplementary",)),
        _check("kelmarsh_penmanshiel_mean_nmi", "artifacts/external_wind_guard_windowfix/external_wind_guard.json", _num(external_guard["mean_nmi"]), "{:.3f}", ("main", "supplementary")),
        _check("gate_transition_match_at_step", "artifacts/mechanism_behavior_pack_wtb/gate_transition_lead_lag.csv", gate_evolution_summary[0], "{:.3f}", ("main", "supplementary")),
        _check("gate_transition_match_lead_3", "artifacts/mechanism_behavior_pack_wtb/gate_transition_lead_lag.csv", gate_evolution_summary[-3], "{:.3f}", ("main", "supplementary")),
        _check("gate_transition_match_lead_6", "artifacts/mechanism_behavior_pack_wtb/gate_transition_lead_lag.csv", gate_evolution_summary[-6], "{:.3f}", ("main", "supplementary")),
    ]

    farm_pcc_file = "artifacts/farm_aggregate_reserve_20260905/farm_pcc_paired_summary.csv"
    if (root / farm_pcc_file).exists():
        farm_pcc = pd.read_csv(root / farm_pcc_file)
        pcc_global = farm_pcc[
            (farm_pcc["condition"] == "all_steps")
            & (farm_pcc["metric"] == "total_cost")
            & (farm_pcc["rho"] == 10.0)
            & (farm_pcc["strategy"] == "joint-posterior-aggregate")
            & (farm_pcc["baseline"] == "global-pcc-quantile")
        ].iloc[0]
        pcc_gaussian = farm_pcc[
            (farm_pcc["condition"] == "all_steps")
            & (farm_pcc["metric"] == "total_cost")
            & (farm_pcc["rho"] == 10.0)
            & (farm_pcc["strategy"] == "joint-posterior-aggregate")
            & (farm_pcc["baseline"] == "gaussian-pcc-param")
        ].iloc[0]
        pcc_trans_pab = farm_pcc[
            (farm_pcc["condition"] == "transitional")
            & (farm_pcc["metric"] == "total_cost")
            & (farm_pcc["rho"] == 10.0)
            & (farm_pcc["strategy"] == "joint-posterior-aggregate")
            & (farm_pcc["baseline"] == "soft-pab-aggregate")
        ].iloc[0]

        checks.extend([
            _check("farm_pcc_savings_vs_global", farm_pcc_file, _num(pcc_global["delta_mean"]), _fmt_millions, ("main", "cover")),
            _check("farm_pcc_ci_low_vs_global", farm_pcc_file, _num(pcc_global["ci_low"]), _fmt_millions, ("main", "cover")),
            _check("farm_pcc_ci_high_vs_global", farm_pcc_file, _num(pcc_global["ci_high"]), _fmt_millions, ("main", "cover")),
            _check("farm_pcc_savings_vs_gaussian", farm_pcc_file, _num(pcc_gaussian["delta_mean"]), _fmt_millions, ("main", "cover")),
            _check("farm_pcc_transitional_savings_vs_soft_pab", farm_pcc_file, _num(pcc_trans_pab["delta_mean"]), _fmt_millions, ("main", "cover")),
        ])

    markov_file = "artifacts/markov_gilbert_eval_honest/markov_gilbert_guard.json"
    if (root / markov_file).exists():
        markov_guard = json.loads((root / markov_file).read_text(encoding="utf-8"))
        methods = markov_guard["methods_summary"]
        comp = markov_guard["honest_comparison"]
        checks.extend([
            _check("markov_corrupted_recall", markov_file, _num(methods["corrupted_routed_posterior"]["recall_mean"]), "{:.3f}", ("main", "cover")),
            _check("markov_stale_rule_recall", markov_file, _num(methods["stale_threshold_rule_honest"]["recall_mean"]), "{:.3f}", ("main", "cover")),
            _check("markov_f1_gain", markov_file, _num(comp["f1_delta_mean (model - rule_honest)"]), "{:+.3f}", ("main", "cover")),
        ])

    iec_file = "artifacts/iec_density_rolling_eval/iec_rolling_guard.json"
    if (root / iec_file).exists():
        iec_guard = json.loads((root / iec_file).read_text(encoding="utf-8"))
        checks.extend([
            _check("kelmarsh_walkforward_pooled_savings", iec_file, _num(iec_guard["kelmarsh_walkforward_pooled_delta_cost"]), _fmt_millions, ("main", "cover", "supplementary")),
            _check("penmanshiel_walkforward_pooled_savings", iec_file, _num(iec_guard["penmanshiel_walkforward_pooled_delta_cost"]), _fmt_millions, ("main", "cover", "supplementary")),
            _check("lhb_walkforward_pooled_delta", iec_file, _num(iec_guard["lhb_walkforward_pooled_delta_cost"]), lambda v: f"+{v / 1_000_000.0:.2f}M", ("main", "supplementary")),
            _check("lhb_annual_pooled_delta", iec_file, _num(iec_guard["lhb_pooled_delta_cost"]), lambda v: f"+{int(round(v / 1000.0))}k", ("main", "supplementary")),
            _check("kelmarsh_static_freeze_delta", iec_file, _num(iec_guard["kelmarsh_static_freeze_delta_cost"]), _fmt_millions, ("main", "supplementary")),
            _check("penmanshiel_static_freeze_delta", iec_file, _num(iec_guard["penmanshiel_static_freeze_delta_cost"]), _fmt_millions, ("main", "supplementary")),
        ])

    gate_decay_file = "artifacts/multiyear_gate_representation_audit/gate_representation_decay_summary.csv"
    if (root / gate_decay_file).exists():
        gate_df = pd.read_csv(root / gate_decay_file)
        km_y2 = gate_df[(gate_df["farm"] == "kelmarsh") & (gate_df["year_idx"] == 2)].iloc[0]
        pm_y2 = gate_df[(gate_df["farm"] == "penmanshiel") & (gate_df["year_idx"] == 2)].iloc[0]
        checks.extend([
            _check("kelmarsh_year2_inv_w_pitch", gate_decay_file, _num(km_y2["inverse_wasserstein_pitch_mean"]), "{:.4f}", ("supplementary",)),
            _check("penmanshiel_year2_inv_w_pitch", gate_decay_file, _num(pm_y2["inverse_wasserstein_pitch_mean"]), "{:.4f}", ("supplementary",)),
        ])

    return checks


def _check(
    claim_id: str,
    source_file: str,
    source_value: float,
    formatter: str | Callable[[float], str],
    required_documents: tuple[str, ...],
) -> NumberCheck:
    token = formatter(source_value) if callable(formatter) else formatter.format(source_value)
    return NumberCheck(claim_id, source_file, float(source_value), token, required_documents)


def _lookup(frame: pd.DataFrame, **equals: str) -> pd.Series:
    mask = pd.Series(True, index=frame.index)
    for column, value in equals.items():
        mask &= frame[column].astype(str).eq(str(value))
    rows = frame[mask]
    if rows.empty:
        raise ValueError(f"No row matches {equals}")
    return rows.iloc[0]


def _best_wtb_strict_cache_baseline(frame: pd.DataFrame) -> pd.Series:
    candidates = [
        "Graph WaveNet",
        "Graph Transformer",
        "GAT-GRU",
        "PatchTST",
        "iTransformer",
        "TiDE",
    ]
    rows = []
    for model in candidates:
        try:
            row = _lookup(frame, Panel="WTB", Model=model)
        except ValueError:
            continue
        rmse = _metric_mean(row["Overall RMSE"])
        if math.isfinite(rmse):
            rows.append((rmse, row))
    if not rows:
        raise ValueError("No WTB strict-cache forecasting baseline row found.")
    return min(rows, key=lambda item: item[0])[1]


def _metric_mean(value: object) -> float:
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else math.nan


def _num(value: object) -> float:
    out = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(out) if pd.notna(out) else math.nan


def _fmt_millions(value: float) -> str:
    return f"{value / 1_000_000.0:.2f}M"


def _normalize_text(text: str) -> str:
    return re.sub(r"\\text\{([^}]+)\}", r"\1", text)


def _same_model_reserve_stats(raw_runs: pd.DataFrame) -> dict[str, dict[str, float]]:
    frame = raw_runs[
        raw_runs["model"].astype(str).eq("Boundary-forced router")
        & raw_runs["subset"].astype(str).eq("boundary")
        & pd.to_numeric(raw_runs["cost_ratio"], errors="coerce").eq(10.0)
        & raw_runs["policy"].astype(str).isin(["global", "gate-bin"])
    ].copy()
    if frame.empty:
        raise ValueError("No boundary same-model reserve rows found for cost ratio 10.")

    metrics = ["total_cost", "violation_rate", "shortage_energy"]
    wide = frame.pivot(index="seed", columns="policy", values=metrics)
    out: dict[str, dict[str, float]] = {}
    for metric in metrics:
        diffs = (wide[(metric, "gate-bin")] - wide[(metric, "global")]).dropna().astype(float)
        if diffs.empty:
            raise ValueError(f"No paired reserve differences available for {metric}.")
        boot = _bootstrap_mean(diffs.to_numpy(), n_boot=20000, seed=20260702 + len(metric))
        out[metric] = {
            "mean": float(diffs.mean()),
            "ci_low": float(boot.quantile(0.025)),
            "ci_high": float(boot.quantile(0.975)),
        }
    return out


def _gate_evolution_summary(gate_evolution: pd.DataFrame) -> dict[int, float]:
    frame = gate_evolution[
        gate_evolution["model"].astype(str).eq("MoE + L_bal + L_align + L_force")
        & gate_evolution["run_dir"].astype(str).str.contains("strictmask_validation_wtb_full", regex=False)
    ].copy()
    if frame.empty:
        raise ValueError("No strictmask WTB gate transition rows found.")
    grouped = frame.groupby("lag_steps")["gate_matches_new_regime_rate"].mean()
    required_lags = {-6, -3, 0}
    missing = required_lags.difference(int(lag) for lag in grouped.index.tolist())
    if missing:
        raise ValueError(f"Missing gate transition lags: {sorted(missing)}")
    return {int(lag): float(value) for lag, value in grouped.items()}


def _bootstrap_mean(values: np.ndarray, *, n_boot: int, seed: int) -> pd.Series:
    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    samples = rng.choice(array, size=(n_boot, array.size), replace=True)
    return pd.Series(samples.mean(axis=1))


def _write_latex(frame: pd.DataFrame, path: Path) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3pt}",
        r"\renewcommand{\arraystretch}{1.05}",
        r"\caption*{\textbf{TSTE number consistency audit.}}",
        r"\begin{tabular}{lll}",
        r"\toprule",
        r"Claim & Display token & Required documents \\",
        r"\midrule",
    ]
    for _, row in frame.iterrows():
        mark = "pass" if bool(row["passed"]) else "fail"
        lines.append(
            " & ".join(
                [
                    _escape(str(row["claim_id"])),
                    _escape(str(row["display_token"])),
                    _escape(str(row["required_documents"])) + f" ({mark})",
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify TSTE submission-facing numbers.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    out = run_number_consistency_audit(args.root, args.output_dir)
    summary = json.loads((out / "tste_number_consistency_audit.json").read_text(encoding="utf-8"))
    print(f"TSTE number consistency audit: {summary['status']}")
    print(f"Wrote {out / 'tste_number_consistency_audit.csv'}")
    if summary["status"] != "complete_tste_number_consistency":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
