#!/usr/bin/env bash
set -euo pipefail
cd /root/paper3_audit_rerun_20260830

if [ -d "/opt/hpcx/ucx/lib" ]; then
  export LD_PRELOAD='/opt/hpcx/ucx/lib/libucm.so.0 /opt/hpcx/ucx/lib/libucs.so.0 /opt/hpcx/ucx/lib/libuct.so.0 /opt/hpcx/ucx/lib/libucp.so.0'
fi
export PYTHONPATH=.
export PYTHONUNBUFFERED=1
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
export MPLBACKEND=Agg

OUT_ROOT="artifacts/clean_evidence_v2/risk_layer_benchmark/h6_lead6"
LOG_DIR="logs/phase3_h6"
mkdir -p "$OUT_ROOT" "$LOG_DIR"

run_seed_h6() {
  local seed=$1
  local gpu=$2
  echo "[GPU $gpu] Starting Seed $seed (h=6) at $(date +%H:%M:%S)"
  python3 scripts/remote_risk_layer_benchmark.py \
    --seeds "$seed" \
    --device "cuda:$gpu" \
    --lead-step 5 \
    --dataloader-workers 0 \
    --output-dir "$OUT_ROOT/run_seed_${seed}" \
    --n-boot 1000 \
    > "$LOG_DIR/seed_${seed}.log" 2>&1
  echo "[GPU $gpu] Completed Seed $seed (h=6) at $(date +%H:%M:%S)"
}

run_seed_h24() {
  local seed=$1
  local gpu=$2
  local h24_root="artifacts/clean_evidence_v2/risk_layer_benchmark/h24_lead24"
  mkdir -p "$h24_root"
  echo "[GPU $gpu] Starting Seed $seed (h=24) at $(date +%H:%M:%S)"
  python3 scripts/remote_risk_layer_benchmark.py \
    --seeds "$seed" \
    --device "cuda:$gpu" \
    --lead-step 23 \
    --dataloader-workers 0 \
    --output-dir "$h24_root/run_seed_${seed}" \
    --n-boot 1000 \
    > "$LOG_DIR/seed_${seed}_h24.log" 2>&1
  echo "[GPU $gpu] Completed Seed $seed (h=24) at $(date +%H:%M:%S)"
}

# Throttled execution on 25979: concurrency <= 2 to prevent 45.9GB cgroup OOM
echo "=== Batch 1 (max 2 concurrent) ==="
run_seed_h6 201 0 &
run_seed_h6 202 1 &
wait

echo "=== Batch 2 (max 2 concurrent) ==="
run_seed_h6 203 2 &
run_seed_h6 204 3 &
wait

echo "=== Batch 3 (max 2 concurrent) ==="
run_seed_h6 205 4 &
run_seed_h24 201 5 &
wait

echo "ALL GPUS ON 25979 COMPLETED AT $(date +%H:%M:%S)"

python3 scripts/merge_phase3_results.py --input-root "$OUT_ROOT" --output-dir "$OUT_ROOT"
echo "H=6 MERGE COMPLETED AT $(date +%H:%M:%S)"
