#!/bin/bash
set -e
cd /scratch/junyu/exp03_run
export PYTHONPATH=.
PYTHON=/home/junyu/miniconda3/envs/grokking/bin/python

echo "=========================================================="
echo "METIS A100: PRE-FLIGHT VERIFICATION FOR EXP-03"
echo "=========================================================="
$PYTHON -c '
import sys, os, json, torch, numpy as np
print("Python interpreter:", sys.executable)
print("PyTorch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU Device:", torch.cuda.get_device_name(0))
    print("VRAM (GB):", torch.cuda.get_device_properties(0).total_memory / 1e9)
'

echo "=========================================================="
echo "LAUNCHING FULL EXP-03 BENCHMARK (7 DELAYS x 5 SEEDS x 2 HORIZONS)"
echo "=========================================================="
$PYTHON -u scripts/run_exp03_async_benchmark.py \
    --cache-dir artifacts/cache_strictmask_trainweights/wtb_245d \
    --residuals-file artifacts/fixed_forecast_residuals.npz \
    --output-dir artifacts/exp03_async \
    --output-report docs/EXP03_ASYNCHRONOUS_REPORT.md \
    --device cuda

echo "=========================================================="
echo "EXP-03 METIS EXECUTION FINISHED SUCCESSFULLY"
echo "=========================================================="
ls -lh artifacts/exp03_async/psrei_vs_delay.csv docs/EXP03_ASYNCHRONOUS_REPORT.md
