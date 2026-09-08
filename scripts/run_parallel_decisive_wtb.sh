#!/usr/bin/env bash
set -e
cd /root/paper3_audit_rerun_20260830
mkdir -p logs/decisive_benchmark_v1

echo "Launching Seeds 202-205 on 4x RTX 4090..."
CUDA_VISIBLE_DEVICES=0 ./run_env.sh python3 scripts/decisive_fair_risk_benchmark.py --farm wtb --seeds 202 --device cuda:0 --output-dir artifacts/decisive_benchmark_v1/risk_layer_benchmark/wtb_parts/seed202 > logs/decisive_benchmark_v1/wtb_seed202.log 2>&1 &
P202=$!

CUDA_VISIBLE_DEVICES=1 ./run_env.sh python3 scripts/decisive_fair_risk_benchmark.py --farm wtb --seeds 203 --device cuda:0 --output-dir artifacts/decisive_benchmark_v1/risk_layer_benchmark/wtb_parts/seed203 > logs/decisive_benchmark_v1/wtb_seed203.log 2>&1 &
P203=$!

CUDA_VISIBLE_DEVICES=2 ./run_env.sh python3 scripts/decisive_fair_risk_benchmark.py --farm wtb --seeds 204 --device cuda:0 --output-dir artifacts/decisive_benchmark_v1/risk_layer_benchmark/wtb_parts/seed204 > logs/decisive_benchmark_v1/wtb_seed204.log 2>&1 &
P204=$!

CUDA_VISIBLE_DEVICES=3 ./run_env.sh python3 scripts/decisive_fair_risk_benchmark.py --farm wtb --seeds 205 --device cuda:0 --output-dir artifacts/decisive_benchmark_v1/risk_layer_benchmark/wtb_parts/seed205 > logs/decisive_benchmark_v1/wtb_seed205.log 2>&1 &
P205=$!

echo "Waiting for PIDs: $P202 $P203 $P204 $P205"
wait $P202 $P203 $P204 $P205
echo "Seeds 202-205 completed successfully!"
