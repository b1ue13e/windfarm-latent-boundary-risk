#!/usr/bin/env bash
set -e

export LD_PRELOAD='/opt/hpcx/ucx/lib/libucm.so.0 /opt/hpcx/ucx/lib/libucs.so.0 /opt/hpcx/ucx/lib/libuct.so.0 /opt/hpcx/ucx/lib/libucp.so.0'
export PYTHONPATH='/root/paper3_audit_rerun_20260830'
export PYTHONUNBUFFERED=1

REPO="/root/paper3_audit_rerun_20260830"
OUT_DIR="$REPO/artifacts/multiyear_gate_representation_audit"
mkdir -p "$OUT_DIR"

echo "=== Launching 4x RTX 4090 Gate Representation Stability Evaluation ==="
date

# Kelmarsh seeds on GPU 0 and GPU 1
python3 "$REPO/scripts/remote_gate_representation_decay.py"     --farm kelmarsh --seeds 201,202,203 --gpu-id 0 --output-dir "$OUT_DIR" > "$OUT_DIR/worker_km_gpu0.log" 2>&1 &
PID0=$!

python3 "$REPO/scripts/remote_gate_representation_decay.py"     --farm kelmarsh --seeds 204,205 --gpu-id 1 --output-dir "$OUT_DIR" > "$OUT_DIR/worker_km_gpu1.log" 2>&1 &
PID1=$!

# Penmanshiel seeds on GPU 2 and GPU 3
python3 "$REPO/scripts/remote_gate_representation_decay.py"     --farm penmanshiel --seeds 201,202,203 --gpu-id 2 --output-dir "$OUT_DIR" > "$OUT_DIR/worker_pm_gpu2.log" 2>&1 &
PID2=$!

python3 "$REPO/scripts/remote_gate_representation_decay.py"     --farm penmanshiel --seeds 204,205 --gpu-id 3 --output-dir "$OUT_DIR" > "$OUT_DIR/worker_pm_gpu3.log" 2>&1 &
PID3=$!

echo "Dispatched: PID0=$PID0 (KM 201-203), PID1=$PID1 (KM 204-205), PID2=$PID2 (PM 201-203), PID3=$PID3 (PM 204-205)"

wait $PID0
echo "GPU 0 finished."
wait $PID1
echo "GPU 1 finished."
wait $PID2
echo "GPU 2 finished."
wait $PID3
echo "GPU 3 finished."

echo "Aggregating all workers..."
python3 -c "
import pandas as pd
from pathlib import Path

out_dir = Path('$OUT_DIR')
dfs = [pd.read_csv(f) for f in out_dir.glob('*_gate_decay.csv')]
if dfs:
    df = pd.concat(dfs, ignore_index=True).drop_duplicates()
    df.to_csv(out_dir / 'gate_representation_decay_raw.csv', index=False)
    
    # Compute mean and standard error / 95% CI across seeds
    num_cols = ['nmi_ground_truth', 'relative_nmi', 'wasserstein_pitch', 'inverse_wasserstein_pitch', 'mean_wasserstein_all', 'inverse_wasserstein_all', 'total_variation_share']
    grouped = df.groupby(['farm', 'year_idx', 'calendar_year'])[num_cols].agg(['mean', 'std', 'count']).reset_index()
    grouped.columns = ['_'.join(c).strip('_') for c in grouped.columns]
    grouped.to_csv(out_dir / 'gate_representation_decay_summary.csv', index=False)
    print('Aggregated summary saved!')
    print(grouped.to_string())
"
date
