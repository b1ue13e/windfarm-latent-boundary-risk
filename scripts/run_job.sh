#!/bin/bash
set -e
cd /scratch/junyu/exp03_run
export PYTHONPATH=.
PYTHON=/home/junyu/miniconda3/envs/grokking/bin/python

$PYTHON -u scripts/run_exp03_async_benchmark.py \
    --cache-dir artifacts/cache_strictmask_trainweights/wtb_245d \
    --residuals-file artifacts/fixed_forecast_residuals.npz \
    --output-dir artifacts/exp03_async \
    --output-report docs/EXP03_ASYNCHRONOUS_REPORT.md \
    --device cuda > exp03_full_output.log 2>&1
