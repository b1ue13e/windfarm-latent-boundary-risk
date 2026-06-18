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
  'artifacts/strict_wtb_evidence_sources_20260609/generated/table_strict_wtb_seed_metrics.tex',
  'artifacts/strict_wtb_evidence_sources_20260609/generated/table_strict_wtb_mechanism_effects.tex',
  'artifacts/strict_wtb_evidence_sources_20260609/generated/table_strict_wtb_placebo_effects.tex',
  'artifacts/strict_wtb_evidence_sources_20260609/generated/table_strict_wtb_boundary_slice.tex',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_summary.csv',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_operational_windows.csv',
  'artifacts/operational_baselines_wtb_strictmask/wtb_operational_baselines.csv',
  'artifacts/operational_baselines_wtb_strictmask/table_wtb_operational_baselines.tex',
  'artifacts/strictmask_combined_reviewer_stats/paired_effects_summary.csv',
  'artifacts/strictmask_combined_reviewer_stats/paired_multiplicity_table.csv',
  'artifacts/strictmask_combined_reviewer_stats/efficiency_fairness_table.csv',
  'artifacts/external_wind_guard/external_wind_run_status.csv',
  'artifacts/external_wind_guard/external_wind_cache_status.csv'
) -join ','
$sources = @(
  'artifacts/strict_wtb_evidence_sources_20260609/strict_wtb_evidence_manifest.json',
  'artifacts/strict_wtb_evidence_sources_20260609/tables/strict_wtb_mechanism_raw.csv',
  'artifacts/strict_wtb_evidence_sources_20260609/tables/strict_wtb_placebo_raw.csv',
  'artifacts/strict_wtb_evidence_sources_20260609/tables/strict_wtb_boundary_slice_summary.csv',
  'artifacts/strict_wtb_evidence_sources_20260609/tables/strict_wtb_time_forward_summary.csv',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_raw_runs.csv',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_daily_costs.csv',
  'artifacts/decision_reserve_wtb_operational_windows/reserve_decision_gate_loss.csv',
  'artifacts/operational_baselines_wtb_strictmask/operational_baseline_config.json',
  'artifacts/strictmask_combined_reviewer_stats/per_example_manifest.csv',
  'artifacts/strictmask_combined_reviewer_stats/paired_effects_raw.csv',
  'artifacts/strictmask_combined_reviewer_stats/paired_multiplicity_table.csv',
  'artifacts/external_wind_full_manifest/external_wind_source_manifest.csv',
  'artifacts/external_wind_full_manifest/external_wind_source_manifest.json',
  'artifacts/external_wind_source_guard/external_wind_source_status.csv',
  'artifacts/external_wind_inspection/external_wind_scada_inspection.csv',
  'artifacts/external_wind_inspection/external_wind_scada_inspection.json',
  'artifacts/external_wind_protocol/external_wind_protocol.json',
  'artifacts/external_wind_protocol/external_wind_commands.ps1',
  'artifacts/external_wind_protocol/external_wind_reviewer_pack_commands.ps1'
) -join ','
$figures = @(
  'artifacts/paper_assets/figures/figure1_architecture.pdf',
  'artifacts/paper_assets/figures/figure3_summary_results.pdf',
  'artifacts/paper_assets/figures/figure4_routing_evidence.pdf'
) -join ','
$guards = @(
  'artifacts/strict_ablation_evidence_guard_wtb_strictmask/strict_ablation_evidence_guard.json',
  'artifacts/strict_threshold_controls_evidence_guard_wtb_strictmask/threshold_controls_evidence_guard.json',
  'artifacts/decision_reserve_wtb_operational_windows_guard/reserve_decision_guard.json',
  'artifacts/strictmask_combined_reviewer_stats_guard/reviewer_stat_pack_guard.json',
  'artifacts/boundary_negative_controls_wtb/boundary_negative_controls_guard.json',
  'artifacts/mechanism_behavior_pack_wtb/mechanism_behavior_pack_guard.json',
  'artifacts/external_wind_guard/external_wind_guard.json'
) -join ','

# capped preview for reviewer-facing package. Run generate_uncapped_per_example_reviewer_stats.ps1 for the full per-example table.
python main.py reviewer-stat-pack --dataset wtb --root-dir . --output-dir artifacts/strictmask_combined_reviewer_stats --suite-dir artifacts/strictmask_validation_wtb_full --suite-dir artifacts/strictmask_baseline_rerun_wtb_full --suite-dir artifacts/strictmask_ablation_rerun_wtb_full --cache-dir artifacts/cache_strictmask/wtb_245d --split test --models "Graph WaveNet,PatchTST,Physics-Aligned MoE,MoE + L_bal + L_align + L_force" --reference-model "MoE + L_bal + L_align + L_force" --baseline-models "Graph WaveNet,PatchTST,Physics-Aligned MoE" --bootstrap-samples 1000 --permutation-samples 1000 --max-per-example-rows 200000 --max-paired-examples 100000 --top-k-failures 24
python main.py reviewer-stat-pack-guard --pack-dir artifacts/strictmask_combined_reviewer_stats --output-dir artifacts/strictmask_combined_reviewer_stats_guard --min-runs 20 --required-models "Graph WaveNet,PatchTST,Physics-Aligned MoE,MoE + L_bal + L_align + L_force" --required-seeds 201,202,203,204,205
python main.py operational-baselines --dataset wtb --root-dir . --cache-dir artifacts/cache_strictmask/wtb_245d --output-dir artifacts/operational_baselines_wtb_strictmask --baselines persistence,power_curve,xgboost_lag,lightgbm_lag,dlinear --max-train-samples 120000 --max-dlinear-samples 80000 --tree-estimators 80 --seed 42
python main.py reserve-decision --dataset wtb --root-dir . --run-table artifacts/strictmask_combined_reviewer_stats/reviewer_stat_pack_run_table.csv --cache-dir artifacts/cache_strictmask/wtb_245d --output-dir artifacts/decision_reserve_wtb_operational_windows --strata boundary,non_boundary,late_period --bootstrap-samples 1000 --skip-plots
python main.py reserve-decision-guard --dataset wtb --decision-dir artifacts/decision_reserve_wtb_operational_windows --output-dir artifacts/decision_reserve_wtb_operational_windows_guard
python main.py external-wind-source-guard --dataset external_wind --root-dir . --output-dir artifacts/external_wind_source_guard --manifest-path artifacts/external_wind_full_manifest/external_wind_source_manifest.csv --min-files 31 --min-total-bytes 10000000000 --farms kelmarsh,penmanshiel
python main.py external-wind-guard --dataset external_wind --root-dir . --output-dir artifacts/external_wind_guard --cache-dirs artifacts/cache_external_wind/external_wind_kelmarsh_chronological,artifacts/cache_external_wind/external_wind_penmanshiel_chronological,artifacts/cache_external_wind/external_wind_kelmarsh_to_penmanshiel_leave_one_farm_out,artifacts/cache_external_wind/external_wind_penmanshiel_to_kelmarsh_leave_one_farm_out --suite-dir artifacts/external_wind_runs --seeds 201,202,203,204,205
$manifestPath = Join-Path $manifestDir 'evidence_manifest_final.json'
python main.py final-evidence-manifest --dataset wtb --root-dir . --output-dir $manifestDir --run-table artifacts/strictmask_combined_reviewer_stats/reviewer_stat_pack_run_table.csv --cache-dir artifacts/cache_strictmask/wtb_245d --source-artifacts $sources --table-outputs $tables --figure-outputs $figures --guard-paths $guards --external-guard artifacts/external_wind_guard/external_wind_guard.json --external-source-guard artifacts/external_wind_source_guard/external_wind_source_guard.json --split-id strict-cache --seeds 201,202,203,204,205 --models "Graph WaveNet,PatchTST,Physics-Aligned MoE,MoE + L_bal + L_align + L_force"
python main.py final-table-export --dataset wtb --root-dir . --manifest-path $manifestPath --output-dir $exportDir
python main.py reproducibility-manifest --output-dir artifacts/reproducibility_manifest_final --root-dir . --hash-max-mb 25
python main.py science-readiness-dashboard --output-dir artifacts/science_readiness_dashboard_20260611 --root-dir . --threshold-controls-evidence-guard artifacts/strict_threshold_controls_evidence_guard_wtb_strictmask/threshold_controls_evidence_guard.json --reviewer-pack-guard artifacts/strictmask_combined_reviewer_stats_guard/reviewer_stat_pack_guard.json --reviewer-pack-config artifacts/strictmask_combined_reviewer_stats/reviewer_stat_pack_config.json --external-wind-guard artifacts/external_wind_guard/external_wind_guard.json --external-wind-source-guard artifacts/external_wind_source_guard/external_wind_source_guard.json --final-evidence-manifest artifacts/final_evidence_package/manifest/evidence_manifest_final.json --reproducibility-manifest artifacts/reproducibility_manifest_final/reproducibility_manifest.json
