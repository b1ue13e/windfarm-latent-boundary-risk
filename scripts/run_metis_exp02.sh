#!/bin/bash
set -e
cd /scratch/junyu/exp02_run
export PYTHONPATH=.
PYTHON=/home/junyu/miniconda3/envs/grokking/bin/python

echo "=========================================================="
echo "METIS A100: PRE-FLIGHT VERIFICATION"
echo "=========================================================="
$PYTHON -c '
import sys, os, json, torch, numpy as np
print("Python interpreter:", sys.executable)
print("PyTorch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU Device:", torch.cuda.get_device_name(0))
    print("VRAM (GB):", torch.cuda.get_device_properties(0).total_memory / 1e9)

from scripts.run_exp02_zero_privileged_supervision import load_exp02_cache
cache = load_exp02_cache("artifacts/cache_strictmask_trainweights/wtb_245d")
print("Data cache verified: nodes =", cache["features"].shape[1], "steps =", cache["features"].shape[0])
'

echo "=========================================================="
echo "LAUNCHING EXP-02: ZERO-PRIVILEGED SUPERVISION BENCHMARK"
echo "=========================================================="
$PYTHON scripts/run_exp02_zero_privileged_supervision.py \
    --cache-dir artifacts/cache_strictmask_trainweights/wtb_245d \
    --residuals-file artifacts/fixed_forecast_residuals.npz \
    --runs-root artifacts/strictmask_ablation_rerun_wtb_full \
    --output-csv artifacts/zero_privileged_supervision_benchmark.csv \
    --output-report docs/ZERO_PRIVILEGED_SUPERVISION_REPORT.md \
    --epochs 12 \
    --device cuda

echo "=========================================================="
echo "EXP-02 EXECUTION FINISHED ON METIS"
echo "=========================================================="
ls -lh artifacts/zero_privileged_supervision_benchmark.csv docs/ZERO_PRIVILEGED_SUPERVISION_REPORT.md
