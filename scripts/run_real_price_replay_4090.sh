#!/usr/bin/env bash
set -e

export LD_PRELOAD='/opt/hpcx/ucx/lib/libucm.so.0 /opt/hpcx/ucx/lib/libucs.so.0 /opt/hpcx/ucx/lib/libuct.so.0 /opt/hpcx/ucx/lib/libucp.so.0'
export PYTHONPATH='/root/paper3_audit_rerun_20260830'
export PYTHONUNBUFFERED=1

REPO="/root/paper3_audit_rerun_20260830"
OUT_DIR="$REPO/artifacts/dynamic_price_settlement_audit"
ELEXON_DIR="$REPO/artifacts/elexon_bmrs_imbalance"
mkdir -p "$OUT_DIR"

echo "=== Launching 4x RTX 4090 Elexon Dynamic Settlement Replay ==="
date

# Kelmarsh seeds 201-203 on GPU 0
python3 "$REPO/scripts/remote_dynamic_price_settlement_replay.py" \
    --repo-root "$REPO" \
    --farm kelmarsh \
    --seeds 201,202,203 \
    --gpu-id 0 \
    --elexon-dir "$ELEXON_DIR" \
    --output-dir "$OUT_DIR" > "$OUT_DIR/worker_km_gpu0.log" 2>&1 &
PID0=$!

# Kelmarsh seeds 204-205 on GPU 1
python3 "$REPO/scripts/remote_dynamic_price_settlement_replay.py" \
    --repo-root "$REPO" \
    --farm kelmarsh \
    --seeds 204,205 \
    --gpu-id 1 \
    --elexon-dir "$ELEXON_DIR" \
    --output-dir "$OUT_DIR" > "$OUT_DIR/worker_km_gpu1.log" 2>&1 &
PID1=$!

# Penmanshiel seeds 201-203 on GPU 2
python3 "$REPO/scripts/remote_dynamic_price_settlement_replay.py" \
    --repo-root "$REPO" \
    --farm penmanshiel \
    --seeds 201,202,203 \
    --gpu-id 2 \
    --elexon-dir "$ELEXON_DIR" \
    --output-dir "$OUT_DIR" > "$OUT_DIR/worker_pm_gpu2.log" 2>&1 &
PID2=$!

# Penmanshiel seeds 204-205 on GPU 3
python3 "$REPO/scripts/remote_dynamic_price_settlement_replay.py" \
    --repo-root "$REPO" \
    --farm penmanshiel \
    --seeds 204,205 \
    --gpu-id 3 \
    --elexon-dir "$ELEXON_DIR" \
    --output-dir "$OUT_DIR" > "$OUT_DIR/worker_pm_gpu3.log" 2>&1 &
PID3=$!

echo "Dispatched: PID0=$PID0 (KM 201-203), PID1=$PID1 (KM 204-205), PID2=$PID2 (PM 201-203), PID3=$PID3 (PM 204-205)"

wait $PID0
echo "GPU 0 (Kelmarsh seeds 201-203) complete."
wait $PID1
echo "GPU 1 (Kelmarsh seeds 204-205) complete."
wait $PID2
echo "GPU 2 (Penmanshiel seeds 201-203) complete."
wait $PID3
echo "GPU 3 (Penmanshiel seeds 204-205) complete."

echo "Aggregating and computing bootstrap statistics..."
python3 "$REPO/scripts/aggregate_real_price_settlement.py" --dir "$OUT_DIR"

echo "=== Elexon Dynamic Settlement Replay Finished Successfully ==="
date
