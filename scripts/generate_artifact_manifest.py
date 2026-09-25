#!/usr/bin/env python3
"""Generate artifacts/ARTIFACT_MANIFEST.json with full cryptographic provenance."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def compute_sha256(path: Path) -> str:
    # Normalize CRLF to LF for text artifacts to ensure cross-platform hash reproducibility (Windows vs Linux)
    suffix = path.suffix.lower()
    if suffix in {".csv", ".json", ".txt", ".md", ".tex"}:
        data = path.read_bytes().replace(b"\r\n", b"\n")
        return hashlib.sha256(data).hexdigest()

    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


ARTIFACT_DEFINITIONS = [
    # 1. Physics Baseline Results
    {
        "filename": "artifacts/clean_evidence_v2/risk_layer_benchmark/h1_lead1/results_by_seed.csv",
        "category": "A",
        "generating_script": "scripts/decisive_fair_risk_benchmark.py",
        "upstream_inputs": ["artifacts/cache_signature_trainweight/wtb_245d_canonical"],
        "manuscript_claims_supported": [
            "Clean Physics h=1 PSREI: 589,535 kWh",
            "Clean Physics h=1 standard deviation: 77,390 kWh",
            "Boundary-active cell count: N=13,883",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    {
        "filename": "artifacts/clean_evidence_v2/risk_layer_benchmark/h6_lead6/results_by_seed.csv",
        "category": "A",
        "generating_script": "scripts/decisive_fair_risk_benchmark.py",
        "upstream_inputs": ["artifacts/cache_signature_trainweight/wtb_245d_canonical"],
        "manuscript_claims_supported": [
            "Clean Physics h=6 PSREI: 881,367 kWh",
            "Clean Physics h=6 standard deviation: 95,741 kWh",
            "Clean Physics h=6 violation rate: 6.81%",
            "Delay-6 physics breakdown at h=6: 12.20% violation, 47.41 MWh deficit",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    {
        "filename": "artifacts/direct_quantile_baselines_summary.csv",
        "category": "A",
        "generating_script": "scripts/decisive_fair_risk_benchmark.py",
        "upstream_inputs": ["artifacts/fixed_forecast_residuals.npz"],
        "manuscript_claims_supported": [
            "Table I / Tab 1 Direct Quantile baselines: B3 GBDT breaches 10% target at h=6 (14.98%)",
            "Direct Quantile MLP pinball conservatism: 1,649,721 kWh (0.58% viol)",
            "STGQ-Dense: 991,181 kWh at h=6",
            "STGQ-Routed: 959,027 kWh at h=6",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    # 2. Recalibration Results
    {
        "filename": "artifacts/single_task_dense_vs_multitask_moe_ablation.csv",
        "category": "A",
        "generating_script": "scripts/eval_single_task_dense_phase_scan.py",
        "upstream_inputs": ["artifacts/checkpoints/", "artifacts/cache_signature_trainweight/wtb_245d_canonical"],
        "manuscript_claims_supported": [
            "Delay-6 Physics breakdown at h=1: 24.02% viol, 127.55 MWh deficit",
            "State-conditional recalibration absorbs 55.3% shortage loss (127.6 -> 57.0 MWh)",
            "Recalibrated physics at tau=60: 1,228,609 kWh (9.46% viol)",
            "Pitch-withheld recalibration degradation: 824,393 -> 1,378,900 kWh",
            "Learned recovery tau=0 no-pitch: 755,794 kWh (-68.6k vs recal)",
            "Learned recovery tau=60 no-pitch: 1,330,318 kWh (-48.6k vs recal)",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    {
        "filename": "artifacts/posterior_calibration.csv",
        "category": "A",
        "generating_script": "scripts/audit_posterior_calibration.py",
        "upstream_inputs": ["artifacts/checkpoints/"],
        "manuscript_claims_supported": [
            "All uncalibrated ECE values pass strict gate: max ECE = 3.46% <= 5.00%",
            "State-conditional posterior calibration preserves reliability",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": True,
    },
    # 3. Latent-State Recoverability Metrics
    {
        "filename": "artifacts/active_power_anchor_audit.csv",
        "category": "A",
        "generating_script": "scripts/run_active_power_anchor_audit.py",
        "upstream_inputs": ["artifacts/cache_signature_trainweight/wtb_245d_canonical"],
        "manuscript_claims_supported": [
            "Active power AUROC: 0.988",
            "Active power AUPRC: 0.941",
            "Active power Brier score: 0.0112",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": True,
    },
    {
        "filename": "artifacts/fair_degradation_replay_20260903/fair_degradation_summary.csv",
        "category": "A",
        "generating_script": "scripts/fair_degradation_replay.py",
        "upstream_inputs": ["artifacts/cache_signature_trainweight/wtb_245d_canonical"],
        "manuscript_claims_supported": [
            "Transition window recall gain: 0.416 (Model) vs 0.196 (Rule)",
            "Delay-6 operational degradation bounds",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    {
        "filename": "artifacts/factorial_boundary_ablation_summary.csv",
        "category": "A",
        "generating_script": "scripts/run_factorial_boundary_ablation.py",
        "upstream_inputs": ["artifacts/checkpoints/"],
        "manuscript_claims_supported": [
            "Random posterior negative control exceeds 10% target: 11.41% > 10.0%",
            "MoE vs Dense parity at h=6 pitch-withheld: Dense=15,471,506 kWh vs Routed=15,768,203 kWh",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    {
        "filename": "artifacts/clean_privileged_supervision_ablation.csv",
        "category": "A",
        "generating_script": "scripts/run_clean_privileged_supervision_ablation.py",
        "upstream_inputs": ["artifacts/checkpoints/"],
        "manuscript_claims_supported": [
            "Matched-backbone privileged supervision ablation (lambda_align=5000 vs lambda_align=0)",
            "Decision cost delta CI crosses zero",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": True,
    },
    # 4. Channel Ablations
    {
        "filename": "artifacts/channel_consequence_ablations.csv",
        "category": "A",
        "generating_script": "scripts/run_channel_consequence_ablations.py",
        "upstream_inputs": ["artifacts/cache_signature_trainweight/wtb_245d_canonical"],
        "manuscript_claims_supported": [
            "C2 Active Power confirmed dominant mechanism (Brier=0.0112, NMI=0.461)",
            "C4 Thermal confirmed unable to detect fast transitions (recall=0.0%)",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": True,
    },
    {
        "filename": "artifacts/anchor_stress_guard/anchor_stress_summary.csv",
        "category": "A",
        "generating_script": "scripts/run_anchor_stress_guard.py",
        "upstream_inputs": ["artifacts/cache_signature_trainweight/wtb_245d_canonical"],
        "manuscript_claims_supported": [
            "Consequence channel ablation under anchor stress (no_patv, no_pab_mean, lagged_patv)",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    # 5. Strong Wind-Speed Baseline Closure
    {
        "filename": "artifacts/strong_baseline_closure_summary.csv",
        "category": "A",
        "generating_script": "scripts/test_strong_baseline_closure.py",
        "upstream_inputs": ["artifacts/fixed_forecast_residuals.npz"],
        "manuscript_claims_supported": [
            "Plant-wide posterior cost superiority not supported (+523,044 kWh penalty)",
            "Transition slice risk hedge: lower violation (7.24% vs 8.36%) and lower shortage at higher reserve (+112,739 kWh PSREI)",
            "Steady-state simple baseline remains lower-cost (+410,305 kWh posterior penalty)",
            "Full population: Policy B 84,577,217 kWh vs Policy C 85,100,261 kWh",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": True,
    },
    {
        "filename": "artifacts/strong_baseline_bootstrap_contrasts.csv",
        "category": "A",
        "generating_script": "scripts/test_strong_baseline_closure.py",
        "upstream_inputs": ["artifacts/fixed_forecast_residuals.npz"],
        "manuscript_claims_supported": [
            "Transition-localization interaction: -296,053 kWh (CI [-568,265, -39,429], p=0.002)",
            "Day-block cluster bootstrap statistical significance across 35 observed days",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": True,
    },
    # 6. Matched-Budget Frontier
    {
        "filename": "artifacts/matched_budget/baseline_reproduction.csv",
        "category": "A",
        "generating_script": "scripts/run_matched_budget_frontier.py",
        "upstream_inputs": ["artifacts/matched_budget/cached_posterior_probs.npz"],
        "manuscript_claims_supported": [
            "Reproduced baseline PSREI accounting identity C = R + 10 U closes within 0.001 kWh",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": True,
    },
    {
        "filename": "artifacts/matched_budget/exact_matched_budget_frontier.csv",
        "category": "A",
        "generating_script": "scripts/run_matched_budget_frontier.py",
        "upstream_inputs": ["artifacts/matched_budget/cached_posterior_probs.npz"],
        "manuscript_claims_supported": [
            "Matched-budget frontier: at matched budget (Delta R = 0), posterior shortage increase +5,241 kWh on average",
            "4 of 5 seeds fail to improve shortage at matched budget",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": True,
    },
    {
        "filename": "artifacts/matched_budget/validation_calibrated_frontier.csv",
        "category": "A",
        "generating_script": "scripts/run_matched_budget_frontier.py",
        "upstream_inputs": ["artifacts/matched_budget/cached_posterior_probs.npz"],
        "manuscript_claims_supported": [
            "Validation-calibrated deployable matched-budget frontier confirming shortage non-superiority",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": True,
    },
    {
        "filename": "artifacts/matched_budget/bootstrap_frontier_statistics.csv",
        "category": "A",
        "generating_script": "scripts/run_matched_budget_frontier.py",
        "upstream_inputs": ["artifacts/matched_budget/cached_posterior_probs.npz"],
        "manuscript_claims_supported": [
            "Bootstrap confidence intervals for Delta U(B) and Delta V(B) across 5,000 resamples",
            "Bootstrap probability P(Delta U >= 0) = 0.81",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": True,
    },
    {
        "filename": "artifacts/matched_budget/frontier_auc_summary.csv",
        "category": "A",
        "generating_script": "scripts/run_matched_budget_frontier.py",
        "upstream_inputs": ["artifacts/matched_budget/cached_posterior_probs.npz"],
        "manuscript_claims_supported": [
            "Integrated shortfall AUC difference confirms absence of decision superiority across budget support",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": True,
    },
    {
        "filename": "artifacts/matched_budget/mechanism_reallocation_diagnostic.csv",
        "category": "A",
        "generating_script": "scripts/run_matched_budget_frontier.py",
        "upstream_inputs": ["artifacts/matched_budget/cached_posterior_probs.npz"],
        "manuscript_claims_supported": [
            "Reserve reallocation mechanism diagnostic: lower violation frequency offset by deeper residual shortfalls",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": True,
    },
    {
        "filename": "artifacts/matched_budget/provenance.json",
        "category": "A",
        "generating_script": "scripts/run_matched_budget_frontier.py",
        "upstream_inputs": ["artifacts/matched_budget/cached_posterior_probs.npz"],
        "manuscript_claims_supported": [
            "Campaign MB00-MB13 parameter specification and sample definitions",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": True,
    },
    # 7. Rho Sensitivity
    {
        "filename": "artifacts/matched_budget/frozen_policy_rho_sensitivity.csv",
        "category": "A",
        "generating_script": "scripts/run_rho_sensitivity.py",
        "upstream_inputs": ["artifacts/matched_budget/cached_posterior_probs.npz"],
        "manuscript_claims_supported": [
            "Frozen-policy break-even ratio sweep rho in [1, 100]",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": True,
    },
    {
        "filename": "artifacts/matched_budget/reoptimized_rho_sensitivity.csv",
        "category": "A",
        "generating_script": "scripts/run_rho_sensitivity.py",
        "upstream_inputs": ["artifacts/matched_budget/cached_posterior_probs.npz"],
        "manuscript_claims_supported": [
            "Re-optimized policy rho-sensitivity: absence of economic crossover for any rho >= 5",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": True,
    },
    # 8. External-Site Results & Number Consistency Sources
    {
        "filename": "artifacts/paper_assets/tables/table_main_benchmark.csv",
        "category": "A",
        "generating_script": "scripts/rebuild_applied_energy_diagnostics.py",
        "upstream_inputs": ["artifacts/cache_signature_trainweight/"],
        "manuscript_claims_supported": [
            "Benchmark point forecast RMSE margin: 236.13 +- 8.41 vs 224.34 +- 2.23",
            "Graph WaveNet benchmark comparison on WTB",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    {
        "filename": "artifacts/paper_assets/tables/table_wtb_ablation.csv",
        "category": "A",
        "generating_script": "scripts/rebuild_applied_energy_diagnostics.py",
        "upstream_inputs": ["artifacts/checkpoints/"],
        "manuscript_claims_supported": [
            "MoE + L_bal + L_align + L_force ablation metrics",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    {
        "filename": "artifacts/anchor_stress_early_warning_wtb_strictmask/anchor_stress_early_warning_summary.csv",
        "category": "A",
        "generating_script": "scripts/run_anchor_stress_early_warning.py",
        "upstream_inputs": ["artifacts/cache_signature_trainweight/wtb_245d_canonical"],
        "manuscript_claims_supported": [
            "Early warning label delay steps=6 and availability=0.50 robustness",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    {
        "filename": "artifacts/early_warning_classifier_baseline_wtb/early_warning_classifier_baseline_summary.csv",
        "category": "A",
        "generating_script": "scripts/run_early_warning_classifier_baseline.py",
        "upstream_inputs": ["artifacts/cache_signature_trainweight/wtb_245d_canonical"],
        "manuscript_claims_supported": [
            "Classifier baseline clean live anchor comparison",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    {
        "filename": "artifacts/final_evidence_package/export/tables/early_warning_consequence_audit.csv",
        "category": "A",
        "generating_script": "scripts/build_final_evidence_package.py",
        "upstream_inputs": ["artifacts/cache_signature_trainweight/wtb_245d_canonical"],
        "manuscript_claims_supported": [
            "Consequence audit under delay steps=6",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    {
        "filename": "artifacts/class_weight_boundary_audit/class_weight_sensitivity_summary.csv",
        "category": "A",
        "generating_script": "scripts/run_class_weight_sensitivity.py",
        "upstream_inputs": ["artifacts/cache_signature_trainweight/wtb_245d_canonical"],
        "manuscript_claims_supported": [
            "Train-only class weight sensitivity audit",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    {
        "filename": "artifacts/decision_reserve_trainweight_allclean_20260830/reserve_decision_summary.csv",
        "category": "A",
        "generating_script": "scripts/decisive_fair_risk_benchmark.py",
        "upstream_inputs": ["artifacts/cache_signature_trainweight/wtb_245d_canonical"],
        "manuscript_claims_supported": [
            "Reserve decision summary for boundary subset, cost ratio 10.0",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    {
        "filename": "artifacts/decision_reserve_trainweight_allclean_20260830/reserve_decision_raw_runs.csv",
        "category": "A",
        "generating_script": "scripts/decisive_fair_risk_benchmark.py",
        "upstream_inputs": ["artifacts/cache_signature_trainweight/wtb_245d_canonical"],
        "manuscript_claims_supported": [
            "Same-model reserve statistics across seeds",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    {
        "filename": "artifacts/mechanism_behavior_pack_wtb/gate_transition_lead_lag.csv",
        "category": "A",
        "generating_script": "scripts/build_mechanism_behavior_pack.py",
        "upstream_inputs": ["artifacts/cache_signature_trainweight/wtb_245d_canonical"],
        "manuscript_claims_supported": [
            "Gate transition lead-lag temporal evolution",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    {
        "filename": "artifacts/external_wind_guard_windowfix/external_wind_guard.json",
        "category": "A",
        "generating_script": "scripts/build_cross_farm_generalization.py",
        "upstream_inputs": ["artifacts/cache_signature_kelmarsh", "artifacts/cache_signature_penmanshiel"],
        "manuscript_claims_supported": [
            "Kelmarsh (6 MM92) and Penmanshiel (14 MM82) external validation",
            "Zero-shot directional asymmetry: Kelmarsh -> Penm 0.77 vs reverse 0.34",
            "Turbine count alone does not explain cross-site variation",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    {
        "filename": "artifacts/external_wind_lhb_guard_full_5seed/external_wind_guard.json",
        "category": "A",
        "generating_script": "scripts/build_cross_farm_generalization.py",
        "upstream_inputs": ["artifacts/cache_signature_lhb"],
        "manuscript_claims_supported": [
            "La Haute Borne (LHB 4 MM82) micro-farm overfitting boundary: +43k kWh (CI [-28.7k, +141.2k])",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    {
        "filename": "artifacts/external_wind_lhb_anchor_intervention_full/lhb_anchor_observability_guard.json",
        "category": "A",
        "generating_script": "scripts/build_cross_farm_generalization.py",
        "upstream_inputs": ["artifacts/cache_signature_lhb"],
        "manuscript_claims_supported": [
            "LHB anchor observability guard and intervention",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": False,
    },
    # 9. Decision Mediation
    {
        "filename": "artifacts/mediation_analysis.csv",
        "category": "A",
        "generating_script": "scripts/run_decision_mediation_test.py",
        "upstream_inputs": ["artifacts/fixed_forecast_residuals.npz"],
        "manuscript_claims_supported": [
            "Mediation confirmed: Dynamic transition windows account for 48.4% of total savings (p=0.0000)",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": True,
    },
    # 10. Information Set Contract
    {
        "filename": "artifacts/information_set_manifest.csv",
        "category": "A",
        "generating_script": "scripts/verify_decisive_gate.py",
        "upstream_inputs": ["windfarm_moe/arrival_feed.py"],
        "manuscript_claims_supported": [
            "Information-set symmetry: 819 rows validated, zero forward leakage",
        ],
        "tracked_in_git": True,
        "externally_hosted": False,
        "regenerable": True,
    },
    # 11. Large Essential Derived Artifacts (Category B)
    {
        "filename": "artifacts/fixed_forecast_residuals.npz",
        "category": "B",
        "generating_script": "scripts/run_fixed_target_contract.py",
        "upstream_inputs": ["artifacts/cache_signature_trainweight/wtb_245d_canonical", "wtbdata_245days.csv"],
        "manuscript_claims_supported": [
            "Fixed forecast residuals across 5 seeds and 6 horizons (keys: 28)",
            "Underlies Table I, Table II, direct quantiles, mediation analysis, and strong-baseline closure",
        ],
        "tracked_in_git": False,
        "externally_hosted": True,
        "regenerable": False,
    },
    {
        "filename": "artifacts/matched_budget/cached_posterior_probs.npz",
        "category": "B",
        "generating_script": "scripts/run_matched_budget_frontier.py",
        "upstream_inputs": ["artifacts/checkpoints/", "artifacts/fixed_forecast_residuals.npz"],
        "manuscript_claims_supported": [
            "Precomputed posterior probabilities across 5 seeds for matched-budget campaign (MB00-MB13)",
            "Underlies exact matched-budget frontier, bootstrap CIs, and rho sensitivity",
        ],
        "tracked_in_git": False,
        "externally_hosted": True,
        "regenerable": False,
    },
]


def main():
    manifest_entries = []
    missing_files = []

    for item in ARTIFACT_DEFINITIONS:
        rel = item["filename"]
        fp = REPO_ROOT / rel
        if not fp.exists():
            missing_files.append(rel)
            print(f"  [MISSING] {rel}")
            continue

        size = fp.stat().st_size
        sha = compute_sha256(fp)
        entry = {
            "filename": rel,
            "sha256": sha,
            "size_bytes": size,
            "category": item["category"],
            "generating_script": item["generating_script"],
            "upstream_inputs": item["upstream_inputs"],
            "manuscript_claims_supported": item["manuscript_claims_supported"],
            "tracked_in_git": item["tracked_in_git"],
            "externally_hosted": item["externally_hosted"],
            "regenerable": item["regenerable"],
        }
        manifest_entries.append(entry)
        print(f"  [OK] {rel} ({size:,} bytes, sha256={sha[:12]}...)")

    if missing_files:
        print(f"\nWarning: {len(missing_files)} files defined in manifest are missing from {REPO_ROOT}!")

    out_file = REPO_ROOT / "artifacts" / "ARTIFACT_MANIFEST.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(manifest_entries, indent=2), encoding="utf-8")
    print(f"\nWrote manifest with {len(manifest_entries)} entries to {out_file}")
    return 0 if not missing_files else 1


if __name__ == "__main__":
    raise SystemExit(main())
