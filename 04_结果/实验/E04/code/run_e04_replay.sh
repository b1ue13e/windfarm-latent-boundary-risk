#!/usr/bin/env bash
set -euo pipefail
source /home/junyu/miniconda3/bin/activate grokking
REPO=/lstr/sahara/minlpml/junyu/paper3_raw_replay_20261015
cd "$REPO"
export WINDFARM_REPO_ROOT="$REPO"
export STRONG_BASELINE_OUTPUT_DIR="artifacts/raw_replay_20261015_v2/e04_strong_baseline_replay_v1"
python scripts/test_strong_baseline_closure.py \
  --cache-dir "$REPO/artifacts/raw_replay_20261015_v2/cache_wtb" \
  --residuals-file "$REPO/artifacts/raw_replay_20261015_v2/fixed_forecast_residuals.npz" \
  --runs-pattern "$REPO/artifacts/raw_replay_20261015_v2/models/dense_classifier/seed{seed}" \
  --device cuda:0
