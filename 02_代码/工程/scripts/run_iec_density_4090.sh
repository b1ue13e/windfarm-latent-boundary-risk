#!/usr/bin/env bash
set -e

export LD_PRELOAD='/opt/hpcx/ucx/lib/libucm.so.0 /opt/hpcx/ucx/lib/libucs.so.0 /opt/hpcx/ucx/lib/libuct.so.0 /opt/hpcx/ucx/lib/libucp.so.0'
export PYTHONPATH='/root/paper3_audit_rerun_20260830'
export PYTHONUNBUFFERED=1

REPO_ROOT="/root/paper3_audit_rerun_20260830"
OUT_DIR="$REPO_ROOT/artifacts/iec_density_rolling_eval"
mkdir -p "$OUT_DIR"

echo "=== [Master Dispatcher] Launching 4x RTX 4090 Multi-Year Rolling Evaluation ==="
date

# Function to run worker on assigned GPU
run_worker() {
    local gpu_id=$1
    local seeds=$2
    local log_file="$OUT_DIR/worker_gpu${gpu_id}.log"
    echo "[GPU ${gpu_id}] Starting evaluation for seeds: ${seeds} -> ${log_file}"
    
    # 1. Kelmarsh 9-year rolling evaluation
    python3 "$REPO_ROOT/scripts/remote_iec_density_multiyear_eval.py" \
        --repo-root "$REPO_ROOT" \
        --farm "kelmarsh" \
        --gpu-id "$gpu_id" \
        --seeds "$seeds" \
        --output-dir "$OUT_DIR" \
        --batch-size 256 >> "$log_file" 2>&1
        
    # 2. La Haute Borne multi-quarter rolling evaluation
    python3 "$REPO_ROOT/scripts/remote_iec_density_multiyear_eval.py" \
        --repo-root "$REPO_ROOT" \
        --farm "la_haute_borne" \
        --gpu-id "$gpu_id" \
        --seeds "$seeds" \
        --output-dir "$OUT_DIR" \
        --batch-size 256 >> "$log_file" 2>&1
        
    # 3. Penmanshiel 8.6-year rolling evaluation
    python3 "$REPO_ROOT/scripts/remote_iec_density_multiyear_eval.py" \
        --repo-root "$REPO_ROOT" \
        --farm "penmanshiel" \
        --gpu-id "$gpu_id" \
        --seeds "$seeds" \
        --output-dir "$OUT_DIR" \
        --batch-size 256 >> "$log_file" 2>&1
        
    echo "[GPU ${gpu_id}] Completed all tasks!"
}

# Dispatch concurrently across 4x RTX 4090
run_worker 0 "201" &
PID0=$!

run_worker 1 "202" &
PID1=$!

run_worker 2 "203" &
PID2=$!

run_worker 3 "204,205" &
PID3=$!

echo "Dispatched background PIDs: GPU0=$PID0, GPU1=$PID1, GPU2=$PID2, GPU3=$PID3"

# Wait for all workers to finish
wait $PID0
echo "GPU 0 finished."
wait $PID1
echo "GPU 1 finished."
wait $PID2
echo "GPU 2 finished."
wait $PID3
echo "GPU 3 finished."

echo "=== All GPU workers completed successfully! Aggregating results... ==="
python3 "$REPO_ROOT/scripts/aggregate_iec_density_eval.py" --output-dir "$OUT_DIR"

echo "=== Pipeline finished! ==="
date
