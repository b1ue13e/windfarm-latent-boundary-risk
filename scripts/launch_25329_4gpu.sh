#!/usr/bin/env bash
set -euo pipefail
cd /root/paper3_audit_rerun_20260830

export LD_PRELOAD='/opt/hpcx/ucx/lib/libucm.so.0 /opt/hpcx/ucx/lib/libucs.so.0 /opt/hpcx/ucx/lib/libuct.so.0 /opt/hpcx/ucx/lib/libucp.so.0'
export PYTHONPATH=.
export PYTHONUNBUFFERED=1
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
export MPLBACKEND=Agg

OUT_ROOT="artifacts/clean_evidence_v2/risk_layer_benchmark/h1_lead1"
LOG_DIR="logs/phase3_h1"
mkdir -p "$OUT_ROOT" "$LOG_DIR"

run_seed() {
  local seed=$1
  local gpu=$2
  echo "[GPU $gpu] Starting Seed $seed (h=1) at $(date +%H:%M:%S)"
  python3 scripts/remote_risk_layer_benchmark.py \
    --seeds "$seed" \
    --device "cuda:$gpu" \
    --lead-step 0 \
    --output-dir "$OUT_ROOT/run_seed_${seed}" \
    --n-boot 1000 \
    > "$LOG_DIR/seed_${seed}.log" 2>&1
  echo "[GPU $gpu] Completed Seed $seed (h=1) at $(date +%H:%M:%S)"
}

# 4 GPUs on 25329
(run_seed 201 0 && run_seed 205 0) &
run_seed 202 1 &
run_seed 203 2 &
run_seed 204 3 &

wait
echo "ALL SEEDS FOR H=1 COMPLETED AT $(date +%H:%M:%S)"

python3 scripts/merge_phase3_results.py --input-root "$OUT_ROOT" --output-dir "$OUT_ROOT"
echo "H=1 MERGE COMPLETED AT $(date +%H:%M:%S)"
