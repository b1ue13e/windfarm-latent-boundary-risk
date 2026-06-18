$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot

$outputDir = 'artifacts/strictmask_combined_reviewer_stats_uncapped_per_example'
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
python main.py reviewer-stat-pack --dataset wtb --root-dir . --output-dir $outputDir --suite-dir artifacts/strictmask_validation_wtb_full --suite-dir artifacts/strictmask_baseline_rerun_wtb_full --suite-dir artifacts/strictmask_ablation_rerun_wtb_full --cache-dir artifacts/cache_strictmask/wtb_245d --split test --models "Graph WaveNet,PatchTST,Physics-Aligned MoE,MoE + L_bal + L_align + L_force" --reference-model "MoE + L_bal + L_align + L_force" --baseline-models "Graph WaveNet,PatchTST,Physics-Aligned MoE" --bootstrap-samples 1000 --permutation-samples 1000 --max-per-example-rows 0 --max-paired-examples 100000 --top-k-failures 24
python main.py reviewer-stat-pack-guard --pack-dir $outputDir --output-dir artifacts/strictmask_combined_reviewer_stats_uncapped_per_example_guard --min-runs 20 --required-models "Graph WaveNet,PatchTST,Physics-Aligned MoE,MoE + L_bal + L_align + L_force" --required-seeds 201,202,203,204,205
