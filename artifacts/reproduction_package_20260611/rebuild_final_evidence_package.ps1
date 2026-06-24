$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot

$finalRoot = 'artifacts/final_evidence_package'
$manifestDir = Join-Path $finalRoot 'manifest'
$exportDir = Join-Path $finalRoot 'export'
New-Item -ItemType Directory -Force -Path $manifestDir | Out-Null
New-Item -ItemType Directory -Force -Path $exportDir | Out-Null

$tables = @(
  'artifacts/strict_wtb_evidence_sources_20260609/tables/strict_wtb_seed_metrics.csv',
  'artifacts/strict_wtb_evidence_sources_20260609/tables/strict_wtb_summary.csv',
  'artifacts/strict_wtb_evidence_sources_20260609/tables/strict_wtb_mechanism_effects.csv',
  'artifacts/strict_wtb_evidence_sources_20260609/tables/strict_wtb_placebo_effects.csv',
  'artifacts/strict_wtb_evidence_sources_20260609/tables/strict_wtb_boundary_slice_effects.csv',
  'artifacts/strict_wtb_evidence_sources_20260609/tables/strict_wtb_time_forward_shift_effects.csv',
  'artifacts/strict_wtb_evidence_sources_20260609/generated/table_strict_wtb_late_shift_diagnostics.tex',
  'artifacts/strict_wtb_evidence_sources_20260609/generated/table_strict_wtb_seed_metrics.tex',
  'artifacts/strict_wtb_evidence_sources_20260609/generated/table_strict_wtb_mechanism_effects.tex',
  'artifacts/strict_wtb_evidence_sources_20260609/generated/table_strict_wtb_placebo_effects.tex',
  'artifacts/strict_wtb_evidence_sources_20260609/generated/table_strict_wtb_boundary_slice.tex',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_summary.csv',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_operational_windows.csv',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_boundary_slices.csv',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_boundary_slices.tex',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_system_baselines.csv',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_system_baselines.tex',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_cost_ratio_sensitivity.csv',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_cost_ratio_sensitivity.tex',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_horizon_time_sensitivity.csv',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_horizon_time_sensitivity.tex',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_horizon_quantile_whatif.csv',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_horizon_quantile_whatif.tex',
  'artifacts/reserve_quantile_baseline/reserve_quantile_baseline.csv',
  'artifacts/reserve_quantile_baseline/reserve_quantile_baseline.tex',
  'artifacts/reserve_toy_operational_cost/reserve_toy_operational_cost.csv',
  'artifacts/reserve_toy_operational_cost/reserve_toy_operational_cost.tex',
  'artifacts/anchor_stress_guard/anchor_stress_summary.csv',
  'artifacts/anchor_stress_guard/anchor_stress_summary.tex',
  'artifacts/operational_baselines_wtb_strictmask/wtb_operational_baselines.csv',
  'artifacts/operational_baselines_wtb_strictmask/table_wtb_operational_baselines.tex',
  'artifacts/strictmask_combined_reviewer_stats/paired_effects_summary.csv',
  'artifacts/strictmask_combined_reviewer_stats/paired_multiplicity_table.csv',
  'artifacts/strictmask_combined_reviewer_stats/efficiency_fairness_table.csv',
  'artifacts/threshold_label_validity_audit_wtb_strictmask/threshold_label_validity_summary.csv',
  'artifacts/threshold_label_validity_audit_wtb_strictmask/table_threshold_label_validity.tex',
  'artifacts/external_wind_guard/external_wind_run_status.csv',
  'artifacts/external_wind_guard/external_wind_cache_status.csv',
  'artifacts/external_wind_portability_rescue/external_wind_recalibration_summary.csv',
  'artifacts/external_wind_portability_rescue/table_external_recalibration.tex',
  'artifacts/external_wind_small_calibration_adaptation/adaptation_summary.csv',
  'artifacts/external_wind_small_calibration_adaptation/table_external_small_calibration_adaptation.tex',
  'artifacts/applied_energy_diagnostics/dispatch_reserve_main_table.csv',
  'artifacts/applied_energy_diagnostics/table_dispatch_reserve_main.tex',
  'artifacts/applied_energy_diagnostics/cost_ratio_sensitivity_readable.csv',
  'artifacts/applied_energy_diagnostics/table_cost_ratio_sensitivity_readable.tex',
  'artifacts/applied_energy_diagnostics/system_value_envelope.csv',
  'artifacts/applied_energy_diagnostics/table_system_value_envelope.tex',
  'artifacts/applied_energy_diagnostics/reserve_paired_statistics.csv',
  'artifacts/applied_energy_diagnostics/table_reserve_paired_statistics.tex',
  'artifacts/applied_energy_diagnostics/reserve_coverage_reliability.csv',
  'artifacts/applied_energy_diagnostics/table_reserve_coverage_reliability.tex',
  'artifacts/applied_energy_diagnostics/cost_ratio_energy_system_assumptions.csv',
  'artifacts/applied_energy_diagnostics/table_cost_ratio_energy_system_assumptions.tex',
  'artifacts/applied_energy_diagnostics/anchor_only_rule_router_main_table.csv',
  'artifacts/applied_energy_diagnostics/table_anchor_only_rule_router_main.tex',
  'artifacts/applied_energy_diagnostics/compute_deployment_cost_table.csv',
  'artifacts/applied_energy_diagnostics/table_compute_deployment_cost.tex',
  'artifacts/applied_energy_diagnostics/operational_case_explanation.csv',
  'artifacts/applied_energy_diagnostics/table_operational_case_explanation.tex',
  'artifacts/applied_energy_diagnostics/claim_boundary_applied_energy.csv',
  'artifacts/applied_energy_diagnostics/table_claim_boundary_applied_energy.tex',
  'artifacts/applied_energy_diagnostics/quasi_external_deployment_drill_summary.csv',
  'artifacts/applied_energy_diagnostics/table_quasi_external_deployment_drill.tex',
  'artifacts/applied_energy_diagnostics/external_site_transfer_failure_table.csv',
  'artifacts/applied_energy_diagnostics/table_external_site_transfer_failure.tex'
) -join ','
$sources = @(
  'artifacts/strict_wtb_evidence_sources_20260609/strict_wtb_evidence_manifest.json',
  'artifacts/strict_wtb_evidence_sources_20260609/tables/strict_wtb_mechanism_raw.csv',
  'artifacts/strict_wtb_evidence_sources_20260609/tables/strict_wtb_placebo_raw.csv',
  'artifacts/strict_wtb_evidence_sources_20260609/tables/strict_wtb_boundary_slice_summary.csv',
  'artifacts/strict_wtb_evidence_sources_20260609/tables/strict_wtb_time_forward_summary.csv',
  'artifacts/strict_wtb_evidence_sources_20260609/tables/strict_wtb_time_forward_shift_diagnostics.csv',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_raw_runs.csv',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_daily_costs.csv',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_gate_loss.csv',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_cost_ratio_sensitivity.csv',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_boundary_slices.csv',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_horizon_time_sensitivity.csv',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_horizon_quantile_whatif.csv',
  'artifacts/reserve_quantile_baseline/reserve_quantile_baseline.json',
  'artifacts/reserve_quantile_baseline/reserve_quantile_baseline_comparison.csv',
  'artifacts/reserve_quantile_baseline/reserve_quantile_baseline_bootstrap.csv',
  'artifacts/reserve_toy_operational_cost/reserve_toy_operational_cost.json',
  'artifacts/anchor_stress_guard/anchor_stress_run_status.csv',
  'artifacts/anchor_stress_guard/anchor_stress_cache_status.csv',
  'artifacts/threshold_label_validity_audit_wtb_strictmask/threshold_label_validity_raw.csv',
  'artifacts/threshold_label_validity_audit_wtb_strictmask/control_taxonomy.csv',
  'artifacts/operational_baselines_wtb_strictmask/operational_baseline_config.json',
  'artifacts/strictmask_combined_reviewer_stats/per_example_manifest.csv',
  'artifacts/strictmask_combined_reviewer_stats/paired_effects_raw.csv',
  'artifacts/strictmask_combined_reviewer_stats/paired_multiplicity_table.csv',
  'artifacts/external_wind_portability_rescue/external_wind_recalibration_raw.csv',
  'artifacts/external_wind_portability_rescue/external_wind_recalibration_guard.json',
  'artifacts/external_wind_small_calibration_adaptation/adaptation_raw.csv',
  'artifacts/external_wind_small_calibration_adaptation/adaptation_guard.json',
  'artifacts/external_wind_full_manifest/external_wind_source_manifest.csv',
  'artifacts/external_wind_full_manifest/external_wind_source_manifest.json',
  'artifacts/external_wind_source_guard/external_wind_source_status.csv',
  'artifacts/external_wind_inspection/external_wind_scada_inspection.csv',
  'artifacts/external_wind_inspection/external_wind_scada_inspection.json',
  'artifacts/external_wind_protocol/external_wind_protocol.json',
  'artifacts/external_wind_protocol/external_wind_commands.ps1',
  'artifacts/external_wind_protocol/external_wind_reviewer_pack_commands.ps1',
  'artifacts/applied_energy_diagnostics/operational_decision_curve.csv',
  'artifacts/applied_energy_diagnostics/new_wind_farm_deployment_checklist.csv',
  'artifacts/applied_energy_diagnostics/reserve_coverage_reliability.csv',
  'artifacts/applied_energy_diagnostics/quasi_external_deployment_drill_raw.csv',
  'artifacts/applied_energy_diagnostics/README.md'
) -join ','
$figures = @(
  'artifacts/paper_assets/figures/figure1_architecture.pdf',
  'artifacts/paper_assets/figures/figure1_architecture.png',
  'artifacts/paper_assets/figures/figure1_architecture.svg',
  'artifacts/paper_assets/figures/figure2_data_boundary.pdf',
  'artifacts/paper_assets/figures/figure3_summary_results.pdf',
  'artifacts/paper_assets/figures/figure4_routing_evidence.pdf',
  'artifacts/paper_assets/figures/figure5_case_studies.pdf',
  'artifacts/paper_assets/figures/figure6_ablation_tradeoff.pdf',
  'artifacts/applied_energy_diagnostics/operational_decision_curve.png',
  'artifacts/applied_energy_diagnostics/boundary_reserve_system_workflow.png',
  'artifacts/applied_energy_diagnostics/new_wind_farm_deployment_checklist.png',
  'artifacts/applied_energy_diagnostics/graphical_abstract_applied_energy.png'
) -join ','
$guards = @(
  'artifacts/strict_ablation_evidence_guard_wtb_strictmask/strict_ablation_evidence_guard.json',
  'artifacts/strict_threshold_controls_evidence_guard_wtb_strictmask/threshold_controls_evidence_guard.json',
  'artifacts/threshold_label_validity_audit_wtb_strictmask/threshold_label_validity_guard.json',
  'artifacts/decision_reserve_wtb_operational_windows_guard/reserve_decision_guard.json',
  'artifacts/anchor_stress_guard/anchor_stress_guard.json',
  'artifacts/strictmask_combined_reviewer_stats_guard/reviewer_stat_pack_guard.json',
  'artifacts/boundary_negative_controls_wtb/boundary_negative_controls_guard.json',
  'artifacts/mechanism_behavior_pack_wtb/mechanism_behavior_pack_guard.json',
  'artifacts/external_wind_guard/external_wind_guard.json',
  'artifacts/external_wind_portability_rescue/external_wind_recalibration_guard.json',
  'artifacts/external_wind_small_calibration_adaptation/adaptation_guard.json',
  'artifacts/final_evidence_freeze_guard/evidence_freeze_guard.json'
) -join ','

# capped preview for the artifact package. Run generate_uncapped_per_example_reviewer_stats.ps1 for the full per-example table.
python main.py reviewer-stat-pack --dataset wtb --root-dir . --output-dir artifacts/strictmask_combined_reviewer_stats --suite-dir artifacts/strictmask_validation_wtb_full --suite-dir artifacts/strictmask_baseline_rerun_wtb_full --suite-dir artifacts/strictmask_ablation_rerun_wtb_full --cache-dir artifacts/cache_strictmask/wtb_245d --split test --models "Graph WaveNet,PatchTST,Physics-Aligned MoE,MoE + L_bal + L_align + L_force" --reference-model "MoE + L_bal + L_align + L_force" --baseline-models "Graph WaveNet,PatchTST,Physics-Aligned MoE" --bootstrap-samples 1000 --permutation-samples 1000 --max-per-example-rows 200000 --max-paired-examples 100000 --top-k-failures 24
python main.py reviewer-stat-pack-guard --pack-dir artifacts/strictmask_combined_reviewer_stats --output-dir artifacts/strictmask_combined_reviewer_stats_guard --min-runs 20 --required-models "Graph WaveNet,PatchTST,Physics-Aligned MoE,MoE + L_bal + L_align + L_force" --required-seeds 201,202,203,204,205
python main.py time-forward-audit --dataset wtb --root-dir . --run-table artifacts/strictmask_combined_reviewer_stats/reviewer_stat_pack_run_table.csv --cache-dir artifacts/cache_strictmask/wtb_245d --output-dir artifacts/time_forward_wtb_strictmask_full --models "MoE + L_bal + L_align + L_force" --num-blocks 4 --bootstrap-samples 1000
python main.py strict-evidence-export --dataset wtb --root-dir . --output-dir artifacts/strict_wtb_evidence_sources_20260609 --strict-suite-dir artifacts/strictmask_validation_wtb_full --mechanism-dir artifacts/mechanism_gate_wtb_strictmask_full --placebo-dir artifacts/routing_placebo_wtb_strictmask_full --time-forward-dir artifacts/time_forward_wtb_strictmask_full --boundary-slice-dir artifacts/boundary_slice_wtb_strictmask_full --model "MoE + L_bal + L_align + L_force"
python main.py operational-baselines --dataset wtb --root-dir . --cache-dir artifacts/cache_strictmask/wtb_245d --output-dir artifacts/operational_baselines_wtb_strictmask --baselines persistence,power_curve,xgboost_lag,lightgbm_lag,dlinear --max-train-samples 120000 --max-dlinear-samples 80000 --tree-estimators 80 --seed 42
python main.py threshold-label-validity-audit --dataset wtb --root-dir . --cache-dir artifacts/cache_strictmask/wtb_245d --run-table artifacts/strictmask_combined_reviewer_stats/reviewer_stat_pack_run_table.csv --output-dir artifacts/threshold_label_validity_audit_wtb_strictmask --models "MoE + L_bal + L_align + L_force" --rated-wind-grid 10.0,10.5,11.0 --pitch-threshold-grid 1.5,2.0,2.5 --seeds 201,202,203,204,205
python main.py reserve-decision --dataset wtb --root-dir . --run-table artifacts/strictmask_combined_reviewer_stats/reviewer_stat_pack_run_table.csv --cache-dir artifacts/cache_strictmask/wtb_245d --output-dir artifacts/decision_reserve_wtb_operational_windows --strata boundary,non_boundary,late_period,mppt_to_pitch,pitch_to_mppt,high_ramp,low_ramp --bootstrap-samples 1000 --skip-plots
python main.py reserve-decision-guard --dataset wtb --decision-dir artifacts/decision_reserve_wtb_operational_windows --output-dir artifacts/decision_reserve_wtb_operational_windows_guard
python main.py reserve-probabilistic-baseline --dataset wtb --root-dir . --run-table artifacts/paper_assets/tables/wtb_test_aggregated_runs.csv --cache-dir artifacts/cache_strictmask/wtb_245d --output-dir artifacts/reserve_quantile_baseline --cost-ratios 2,5,10,20,50 --main-ratio 10 --bootstrap-samples 1000
python main.py toy-operational-cost --dataset wtb --root-dir . --decision-dir artifacts/decision_reserve_wtb_operational_windows --probabilistic-dir artifacts/reserve_quantile_baseline --output-dir artifacts/reserve_toy_operational_cost --main-ratio 10
python main.py anchor-stress-cache --dataset wtb --root-dir . --source-cache-dir artifacts/cache_strictmask/wtb_245d --output-cache-root artifacts/cache_anchor_stress --variants no_patv,lagged_patv,no_pab_mean,lagged_pab_wspd
python main.py anchor-stress-guard --suite-root artifacts/anchor_stress_runs --cache-root artifacts/cache_anchor_stress --output-dir artifacts/anchor_stress_guard --variants no_patv,lagged_patv,no_pab_mean,lagged_pab_wspd --seeds 201,202,203
python main.py external-wind-source-guard --dataset external_wind --root-dir . --output-dir artifacts/external_wind_source_guard --manifest-path artifacts/external_wind_full_manifest/external_wind_source_manifest.csv --min-files 31 --min-total-bytes 10000000000 --farms kelmarsh,penmanshiel
python main.py external-wind-guard --dataset external_wind --root-dir . --output-dir artifacts/external_wind_guard --cache-dirs artifacts/cache_external_wind/external_wind_kelmarsh_chronological,artifacts/cache_external_wind/external_wind_penmanshiel_chronological,artifacts/cache_external_wind/external_wind_kelmarsh_to_penmanshiel_leave_one_farm_out,artifacts/cache_external_wind/external_wind_penmanshiel_to_kelmarsh_leave_one_farm_out --suite-dir artifacts/external_wind_runs --seeds 201,202,203,204,205
python main.py external-wind-portability-rescue --dataset external_wind --root-dir . --output-dir artifacts/external_wind_portability_rescue --cache-dirs artifacts/cache_external_wind/external_wind_kelmarsh_chronological,artifacts/cache_external_wind/external_wind_penmanshiel_chronological,artifacts/cache_external_wind/external_wind_kelmarsh_to_penmanshiel_leave_one_farm_out,artifacts/cache_external_wind/external_wind_penmanshiel_to_kelmarsh_leave_one_farm_out --suite-dir artifacts/external_wind_runs --seeds 201,202,203,204,205
python main.py external-wind-small-calibration-adaptation --dataset external_wind --root-dir . --output-dir artifacts/external_wind_small_calibration_adaptation --suite-dir artifacts/external_wind_runs --seeds 201,202,203,204,205 --required-models "Physics-Aligned MoE,MoE + L_bal + L_align + L_force" --calibration-anchor-steps 288 --max-calibration-cells 50000 --max-test-cells 200000
python main.py paper-export --dataset wtb --root-dir . --cache-root artifacts/cache_strictmask --output-dir artifacts/paper_assets --wtb-suite-dir artifacts/strictmask_baseline_rerun_wtb_full --wtb-suite-dir artifacts/strictmask_ablation_rerun_wtb_full --era5-suite-dir artifacts/cloud_revision/era5/20260525_163247/main --era5-suite-dir artifacts/era5_baseline_expansion_20260529
python main.py evidence-freeze-guard --paper-path paper_draft.md --compiled-tex paper_draft_compiled.tex --paper-assets-dir artifacts/paper_assets --final-package-dir artifacts/final_evidence_package --paired-effects artifacts/strictmask_combined_reviewer_stats/paired_effects_summary.csv --output-dir artifacts/final_evidence_freeze_guard
$manifestPath = Join-Path $manifestDir 'evidence_manifest_final.json'
python main.py final-evidence-manifest --dataset wtb --root-dir . --output-dir $manifestDir --run-table artifacts/strictmask_combined_reviewer_stats/reviewer_stat_pack_run_table.csv --cache-dir artifacts/cache_strictmask/wtb_245d --source-artifacts $sources --table-outputs $tables --figure-outputs $figures --guard-paths $guards --external-guard artifacts/external_wind_guard/external_wind_guard.json --external-source-guard artifacts/external_wind_source_guard/external_wind_source_guard.json --split-id strict-cache --seeds 201,202,203,204,205 --models "Graph WaveNet,PatchTST,Physics-Aligned MoE,MoE + L_bal + L_align + L_force"
python main.py final-table-export --dataset wtb --root-dir . --manifest-path $manifestPath --output-dir $exportDir
python main.py reproducibility-manifest --output-dir artifacts/reproducibility_manifest_final --root-dir . --hash-max-mb 25
python main.py science-readiness-dashboard --output-dir artifacts/science_readiness_dashboard_20260611 --root-dir . --threshold-controls-evidence-guard artifacts/strict_threshold_controls_evidence_guard_wtb_strictmask/threshold_controls_evidence_guard.json --reviewer-pack-guard artifacts/strictmask_combined_reviewer_stats_guard/reviewer_stat_pack_guard.json --reviewer-pack-config artifacts/strictmask_combined_reviewer_stats/reviewer_stat_pack_config.json --external-wind-guard artifacts/external_wind_guard/external_wind_guard.json --external-wind-source-guard artifacts/external_wind_source_guard/external_wind_source_guard.json --final-evidence-manifest artifacts/final_evidence_package/manifest/evidence_manifest_final.json --reproducibility-manifest artifacts/reproducibility_manifest_final/reproducibility_manifest.json
