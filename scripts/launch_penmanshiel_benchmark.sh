#!/usr/bin/env bash
set -e

if [ -d "/opt/hpcx/ucx/lib" ]; then
  export LD_PRELOAD='/opt/hpcx/ucx/lib/libucm.so.0 /opt/hpcx/ucx/lib/libucs.so.0 /opt/hpcx/ucx/lib/libuct.so.0 /opt/hpcx/ucx/lib/libucp.so.0'
fi
export PYTHONPATH=.
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export PYTHONUNBUFFERED=1
cd /root/paper3_audit_rerun_20260830

mkdir -p logs/penmanshiel_bench
mkdir -p artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h1
mkdir -p artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h6

CACHE="artifacts/cache_signature_penmanshiel/external_wind_penmanshiel_obs_window_canonical"
CKPT="artifacts/signature_gate_farms_runs_20260903/penmanshiel/canonical/wtb_bal_align_force_seed{seed}"
DENSE_CKPT="artifacts/dense_classifier_runs_20260904/canonical/wtb_bal_align_force_seed{seed}"

echo "==================== LAUNCHING PENMANSHIEL BENCHMARK (NODE 25979) ===================="
echo "Time: $(date)"

# Phase 1: Horizon 1 (h=1) throttled to max 2 concurrent processes to prevent cgroup OOM
echo "=== Starting Penmanshiel h=1 ==="
(
for s in 201 202 203; do
    echo "Starting Penmanshiel h=1 Seed $s on GPU 0..."
    python3 scripts/remote_risk_layer_benchmark.py \
      --farm penmanshiel \
      --cache-dir "$CACHE" \
      --routed-checkpoint-pattern "$CKPT" \
      --dense-checkpoint-pattern "$DENSE_CKPT" \
      --rated-wind 14.5 \
      --band 1.0 \
      --dataloader-workers 0 \
      --seeds "$s" \
      --device cuda:0 \
      --lead-step 0 \
      --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h1/run_seed_$s \
      --n-boot 1000 > logs/penmanshiel_bench/h1_seed_$s.log 2>&1
done
) &
PID_H1_A=$!

(
for s in 204 205; do
    echo "Starting Penmanshiel h=1 Seed $s on GPU 1..."
    python3 scripts/remote_risk_layer_benchmark.py \
      --farm penmanshiel \
      --cache-dir "$CACHE" \
      --routed-checkpoint-pattern "$CKPT" \
      --dense-checkpoint-pattern "$DENSE_CKPT" \
      --rated-wind 14.5 \
      --band 1.0 \
      --dataloader-workers 0 \
      --seeds "$s" \
      --device cuda:1 \
      --lead-step 0 \
      --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h1/run_seed_$s \
      --n-boot 1000 > logs/penmanshiel_bench/h1_seed_$s.log 2>&1
done
) &
PID_H1_B=$!

wait $PID_H1_A $PID_H1_B
echo "Penmanshiel h=1 all seeds completed at $(date)!"

# Phase 2: Horizon 6 (h=6) throttled to max 2 concurrent processes
echo "=== Starting Penmanshiel h=6 ==="
(
for s in 201 202 203; do
    echo "Starting Penmanshiel h=6 Seed $s on GPU 2..."
    python3 scripts/remote_risk_layer_benchmark.py \
      --farm penmanshiel \
      --cache-dir "$CACHE" \
      --routed-checkpoint-pattern "$CKPT" \
      --dense-checkpoint-pattern "$DENSE_CKPT" \
      --rated-wind 14.5 \
      --band 1.0 \
      --dataloader-workers 0 \
      --seeds "$s" \
      --device cuda:2 \
      --lead-step 5 \
      --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h6/run_seed_$s \
      --n-boot 1000 > logs/penmanshiel_bench/h6_seed_$s.log 2>&1
done
) &
PID_H6_A=$!

(
for s in 204 205; do
    echo "Starting Penmanshiel h=6 Seed $s on GPU 3..."
    python3 scripts/remote_risk_layer_benchmark.py \
      --farm penmanshiel \
      --cache-dir "$CACHE" \
      --routed-checkpoint-pattern "$CKPT" \
      --dense-checkpoint-pattern "$DENSE_CKPT" \
      --rated-wind 14.5 \
      --band 1.0 \
      --dataloader-workers 0 \
      --seeds "$s" \
      --device cuda:3 \
      --lead-step 5 \
      --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h6/run_seed_$s \
      --n-boot 1000 > logs/penmanshiel_bench/h6_seed_$s.log 2>&1
done
) &
PID_H6_B=$!

wait $PID_H6_A $PID_H6_B
echo "Penmanshiel h=6 all seeds completed at $(date)!"

echo "All Penmanshiel runs completed! Running cross-seed merge for h1 and h6..."
python3 scripts/merge_phase3_results.py \
  --input-root artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h1 \
  --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h1

python3 scripts/merge_phase3_results.py \
  --input-root artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h6 \
  --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h6

echo "PENMANSHIEL BENCHMARK FULLY COMPLETE AT $(date)!"
