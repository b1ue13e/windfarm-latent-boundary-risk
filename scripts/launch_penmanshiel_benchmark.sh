#!/usr/bin/env bash
set -e
export LD_PRELOAD='/opt/hpcx/ucx/lib/libucm.so.0 /opt/hpcx/ucx/lib/libucs.so.0 /opt/hpcx/ucx/lib/libuct.so.0 /opt/hpcx/ucx/lib/libucp.so.0'
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

echo "==================== LAUNCHING PENMANSHIEL BENCHMARK (NODE 25979) ===================="
echo "Time: $(date)"

# GPU 0: h=1, seeds 201, 202
(
for s in 201 202; do
    echo "Starting Penmanshiel h=1 Seed $s on GPU 0..."
    python3 scripts/remote_risk_layer_benchmark.py \
      --farm penmanshiel \
      --cache-dir "$CACHE" \
      --routed-checkpoint-pattern "$CKPT" \
      --dense-checkpoint-pattern "" \
      --seeds "$s" \
      --device cuda:0 \
      --lead-step 0 \
      --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h1/run_seed_$s \
      --n-boot 1000 > logs/penmanshiel_bench/h1_seed_$s.log 2>&1
done
) &
PID_GPU0=$!

# GPU 1: h=1, seeds 203, 204
(
for s in 203 204; do
    echo "Starting Penmanshiel h=1 Seed $s on GPU 1..."
    python3 scripts/remote_risk_layer_benchmark.py \
      --farm penmanshiel \
      --cache-dir "$CACHE" \
      --routed-checkpoint-pattern "$CKPT" \
      --dense-checkpoint-pattern "" \
      --seeds "$s" \
      --device cuda:1 \
      --lead-step 0 \
      --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h1/run_seed_$s \
      --n-boot 1000 > logs/penmanshiel_bench/h1_seed_$s.log 2>&1
done
) &
PID_GPU1=$!

# GPU 2: h=1, seed 205
(
for s in 205; do
    echo "Starting Penmanshiel h=1 Seed $s on GPU 2..."
    python3 scripts/remote_risk_layer_benchmark.py \
      --farm penmanshiel \
      --cache-dir "$CACHE" \
      --routed-checkpoint-pattern "$CKPT" \
      --dense-checkpoint-pattern "" \
      --seeds "$s" \
      --device cuda:2 \
      --lead-step 0 \
      --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h1/run_seed_$s \
      --n-boot 1000 > logs/penmanshiel_bench/h1_seed_$s.log 2>&1
done
) &
PID_GPU2=$!

# GPU 3: h=6, seeds 201, 202
(
for s in 201 202; do
    echo "Starting Penmanshiel h=6 Seed $s on GPU 3..."
    python3 scripts/remote_risk_layer_benchmark.py \
      --farm penmanshiel \
      --cache-dir "$CACHE" \
      --routed-checkpoint-pattern "$CKPT" \
      --dense-checkpoint-pattern "" \
      --seeds "$s" \
      --device cuda:3 \
      --lead-step 5 \
      --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h6/run_seed_$s \
      --n-boot 1000 > logs/penmanshiel_bench/h6_seed_$s.log 2>&1
done
) &
PID_GPU3=$!

# GPU 4: h=6, seeds 203, 204
(
for s in 203 204; do
    echo "Starting Penmanshiel h=6 Seed $s on GPU 4..."
    python3 scripts/remote_risk_layer_benchmark.py \
      --farm penmanshiel \
      --cache-dir "$CACHE" \
      --routed-checkpoint-pattern "$CKPT" \
      --dense-checkpoint-pattern "" \
      --seeds "$s" \
      --device cuda:4 \
      --lead-step 5 \
      --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h6/run_seed_$s \
      --n-boot 1000 > logs/penmanshiel_bench/h6_seed_$s.log 2>&1
done
) &
PID_GPU4=$!

# GPU 5: h=6, seed 205
(
for s in 205; do
    echo "Starting Penmanshiel h=6 Seed $s on GPU 5..."
    python3 scripts/remote_risk_layer_benchmark.py \
      --farm penmanshiel \
      --cache-dir "$CACHE" \
      --routed-checkpoint-pattern "$CKPT" \
      --dense-checkpoint-pattern "" \
      --seeds "$s" \
      --device cuda:5 \
      --lead-step 5 \
      --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h6/run_seed_$s \
      --n-boot 1000 > logs/penmanshiel_bench/h6_seed_$s.log 2>&1
done
) &
PID_GPU5=$!

wait $PID_GPU0 $PID_GPU1 $PID_GPU2 $PID_GPU3 $PID_GPU4 $PID_GPU5

echo "All Penmanshiel runs completed! Running cross-seed merge for h1 and h6..."
python3 scripts/merge_phase3_results.py \
  --input-root artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h1 \
  --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h1

python3 scripts/merge_phase3_results.py \
  --input-root artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h6 \
  --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h6

echo "PENMANSHIEL BENCHMARK FULLY COMPLETE AT $(date)!"
