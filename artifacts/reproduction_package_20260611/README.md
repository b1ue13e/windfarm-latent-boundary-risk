# Science reproduction package

This package provides reviewer-facing entry points for the current strict-cache evidence workflow.

## Scripts

- `refresh_guards_only.ps1`: refreshes guards, dashboard, reviewer-stat guard, and reproducibility manifest without launching training.
- `run_active_experiment_queues.ps1`: starts or resumes the strict baseline run and the follow-up/extension/future/post-queue finalization queues if they are not already running.
- `artifacts/goal_strict_completion_queue_20260612.ps1`: starts or resumes the current strict-cache ablation queue, waits for it, then runs strict routing-control gates, wrong-threshold controls, reviewer packs, reproducibility manifest, and the Science-readiness dashboard.
- `artifacts/strict_postqueue_finalize_20260611.ps1`: waits for long-running queues, then refreshes final guards, dashboard, manifest, and package metadata.
- `rebuild_submission_artifacts.ps1`: rebuilds strict WTB source tables and refreshes threshold-control, final reviewer, and reproducibility guards.
- `rebuild_final_evidence_package.ps1`: builds the single final evidence manifest and exports reviewer-facing tables, source data, figures, guards, and manifest files.
- `generate_uncapped_per_example_reviewer_stats.ps1`: rebuilds the reviewer-stat pack with `--max-per-example-rows 0` into `artifacts/strictmask_combined_reviewer_stats_uncapped_per_example` for full per-example export.
- `external_wind_protocol.ps1`: delegates to `scripts/run_external_wind_full_evidence.ps1`, reuses validated source manifests, source guards, inspections, and caches when present, writes `external_wind_missing_run_status.csv` plus `external_wind_missing_training_commands.ps1`, and accepts `-RunTraining` for missing 5-seed runs only. Use `-RunAllTrainingCommands` only to deliberately replay the full command matrix.

The default final package includes a capped per-example preview (`--max-per-example-rows 200000`) to keep the reviewer bundle manageable. It is not the complete per-example table; use the uncapped script for the full export.

The current Science-readiness dashboard remains the authority for whether the package is complete enough to cite.
