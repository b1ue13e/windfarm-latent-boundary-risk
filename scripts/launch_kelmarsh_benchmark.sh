#!/usr/bin/env bash
set -e

if [ -d "/opt/hpcx/ucx/lib" ]; then
  export LD_PRELOAD='/opt/hpcx/ucx/lib/libucm.so.0 /opt/hpcx/ucx/lib/libucs.so.0 /opt/hpcx/ucx/lib/libuct.so.0 /opt/hpcx/ucx/lib/libucp.so.0'
fi
export PYTHONPATH=.
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export PYTHONUNBUFFERED=1
cd /root/paper3_audit_rerun_20260830

mkdir -p logs/kelmarsh_bench
mkdir -p artifacts/clean_evidence_v2/risk_layer_benchmark/kelmarsh_h1
mkdir -p artifacts/clean_evidence_v2/risk_layer_benchmark/kelmarsh_h6

CACHE="artifacts/cache_signature_kelmarsh/external_wind_kelmarsh_obs_window_canonical"
CKPT="artifacts/signature_gate_farms_runs_20260903/kelmarsh/canonical/wtb_bal_align_force_seed{seed}"
DENSE_CKPT="artifacts/dense_classifier_runs_20260904/canonical/wtb_bal_align_force_seed{seed}"

echo "==================== LAUNCHING KELMARSH BENCHMARK (NODE 25329) ===================="
echo "Time: $(date)"

# GPU 0: h=1, seeds 201, 202, 203
(
for s in 201 202 203; do
    echo "Starting Kelmarsh h=1 Seed $s on GPU 0..."
    python3 scripts/remote_risk_layer_benchmark.py \
      --farm kelmarsh \
      --cache-dir "$CACHE" \
      --routed-checkpoint-pattern "$CKPT" \
      --dense-checkpoint-pattern "$DENSE_CKPT" \
      --rated-wind 12.5 \
      --band 1.0 \
      --dataloader-workers 0 \
      --seeds "$s" \
      --device cuda:0 \
      --lead-step 0 \
      --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/kelmarsh_h1/run_seed_$s \
      --n-boot 1000 > logs/kelmarsh_bench/h1_seed_$s.log 2>&1
done
) &
PID_GPU0=$!

# GPU 1: h=1, seeds 204, 205
(
for s in 204 205; do
    echo "Starting Kelmarsh h=1 Seed $s on GPU 1..."
    python3 scripts/remote_risk_layer_benchmark.py \
      --farm kelmarsh \
      --cache-dir "$CACHE" \
      --routed-checkpoint-pattern "$CKPT" \
      --dense-checkpoint-pattern "$DENSE_CKPT" \
      --rated-wind 12.5 \
      --band 1.0 \
      --dataloader-workers 0 \
      --seeds "$s" \
      --device cuda:1 \
      --lead-step 0 \
      --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/kelmarsh_h1/run_seed_$s \
      --n-boot 1000 > logs/kelmarsh_bench/h1_seed_$s.log 2>&1
done
) &
PID_GPU1=$!

wait $PID_GPU0 $PID_GPU1

# GPU 2: h=6, seeds 201, 202, 203
(
for s in 201 202 203; do
    echo "Starting Kelmarsh h=6 Seed $s on GPU 2..."
    python3 scripts/remote_risk_layer_benchmark.py \
      --farm kelmarsh \
      --cache-dir "$CACHE" \
      --routed-checkpoint-pattern "$CKPT" \
      --dense-checkpoint-pattern "$DENSE_CKPT" \
      --rated-wind 12.5 \
      --band 1.0 \
      --dataloader-workers 0 \
      --seeds "$s" \
      --device cuda:2 \
      --lead-step 5 \
      --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/kelmarsh_h6/run_seed_$s \
      --n-boot 1000 > logs/kelmarsh_bench/h6_seed_$s.log 2>&1
done
) &
PID_GPU2=$!

# GPU 3: h=6, seeds 204, 205
(
for s in 204 205; do
    echo "Starting Kelmarsh h=6 Seed $s on GPU 3..."
    python3 scripts/remote_risk_layer_benchmark.py \
      --farm kelmarsh \
      --cache-dir "$CACHE" \
      --routed-checkpoint-pattern "$CKPT" \
      --dense-checkpoint-pattern "$DENSE_CKPT" \
      --rated-wind 12.5 \
      --band 1.0 \
      --dataloader-workers 0 \
      --seeds "$s" \
      --device cuda:3 \
      --lead-step 5 \
      --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/kelmarsh_h6/run_seed_$s \
      --n-boot 1000 > logs/kelmarsh_bench/h6_seed_$s.log 2>&1
done
) &
PID_GPU3=$!

wait $PID_GPU2 $PID_GPU3

echo "All Kelmarsh runs completed! Running cross-seed merge for h1 and h6..."
python3 scripts/merge_phase3_results.py \
  --input-root artifacts/clean_evidence_v2/risk_layer_benchmark/kelmarsh_h1 \
  --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/kelmarsh_h1

python3 scripts/merge_phase3_results.py \
  --input-root artifacts/clean_evidence_v2/risk_layer_benchmark/kelmarsh_h6 \
  --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/kelmarsh_h6

echo "KELMARSH BENCHMARK FULLY COMPLETE AT $(date)!"
