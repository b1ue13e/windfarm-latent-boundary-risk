"""Orchestrator to deploy, train, evaluate, and retrieve Capacity-Matched Dense Backbone Ablation on Node 2.

Node 2: 6x RTX 4090 GPUs at port 25979 (host 192.168.17.251 / 192.168.1.139).
Runs 5 seeds (201-205) in parallel across GPUs 0-4.
Full Pipeline:
1. Sync scripts to Node 2.
2. Launch training of 5 seeds in parallel on GPUs 0-4.
3. Monitor training progress until all seeds finish.
4. Launch 30-condition phase scan evaluation on GPUs 0-4.
5. Monitor evaluation progress until all seeds finish.
6. Retrieve artifacts to local repo.
7. Aggregate into dedicated summary artifact/table:
   `artifacts/single_task_dense_vs_multitask_moe_ablation.csv`
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
import paramiko
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

NODE2_HOST = os.environ.get("NODE2_HOST", "192.168.17.251")
NODE2_PORT = int(os.environ.get("NODE2_PORT", "25979"))
NODE2_USER = os.environ.get("NODE2_USER", "root")
NODE2_PWD = os.environ.get("NODE2_PWD", "061022")
REMOTE_ROOT = os.environ.get("REMOTE_ROOT", "/root/paper3_audit_rerun_20260830")
SEEDS = [201, 202, 203, 204, 205]

FILES_TO_SYNC = [
    "scripts/train_capacity_matched_dense_wtb.py",
    "scripts/eval_single_task_dense_phase_scan.py",
    "scripts/decisive_fair_risk_benchmark.py",
    "scripts/run_boundary_phase_scan.py",
]


def get_client() -> paramiko.SSHClient:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(NODE2_HOST, port=NODE2_PORT, username=NODE2_USER, password=NODE2_PWD, timeout=20)
    return ssh


def sync_files():
    print("=== 1. SYNCING TRAINING & EVALUATION SCRIPTS TO NODE 2 ===", flush=True)
    ssh = get_client()
    sftp = ssh.open_sftp()
    for rel in FILES_TO_SYNC:
        local = REPO_ROOT / rel
        remote = f"{REMOTE_ROOT}/{rel.replace(os.sep, '/')}"
        remote_dir = "/".join(remote.split("/")[:-1])
        ssh.exec_command(f"mkdir -p {remote_dir}")
        sftp.put(str(local), remote)
        print(f"  Synced {rel} -> {remote}", flush=True)
    sftp.close()
    ssh.close()
    print("Sync completed successfully.\n", flush=True)


def launch_training():
    print("=== 2. LAUNCHING 5 SEEDS DENSE TRAINING IN PARALLEL ON NODE 2 (GPUs 0-4) ===", flush=True)
    ssh = get_client()
    ssh.exec_command(f"mkdir -p {REMOTE_ROOT}/logs/dense_training {REMOTE_ROOT}/artifacts/capacity_matched_dense_wtb")

    launch_cmds = []
    for gpu_id, seed in enumerate(SEEDS):
        log_path = f"{REMOTE_ROOT}/logs/dense_training/seed{seed}.log"
        launch_cmds.append(
            f"( CUDA_VISIBLE_DEVICES={gpu_id} ./run_env.sh python3 -u scripts/train_capacity_matched_dense_wtb.py "
            f"--seed {seed} --device cuda:0 --epochs 20 --patience 5 --output-base artifacts/capacity_matched_dense_wtb > {log_path} 2>&1 & )"
        )
    full_cmd = f"cd {REMOTE_ROOT} && " + " ; ".join(launch_cmds)
    stdin, stdout, stderr = ssh.exec_command(full_cmd)
    stdout.channel.recv_exit_status()
    ssh.close()
    print("All 5 seeds launched concurrently on GPUs 0-4.\n", flush=True)


def monitor_training(poll_interval: int = 15):
    print("=== 3. MONITORING DENSE TRAINING ===", flush=True)
    t0 = time.time()
    while True:
        all_done = True
        status_lines = []
        ssh = get_client()
        for gpu_id, seed in enumerate(SEEDS):
            log_path = f"{REMOTE_ROOT}/logs/dense_training/seed{seed}.log"
            stdin, stdout, stderr = ssh.exec_command(f"ps aux | grep 'train_capacity_matched_dense_wtb.py --seed {seed}' | grep -v grep | wc -l")
            count = int(stdout.read().decode().strip() or "0")
            stdin, stdout, stderr = ssh.exec_command(f"tail -n 1 {log_path} 2>/dev/null")
            last_line = stdout.read().decode().strip()
            if count > 0:
                all_done = False
                status_lines.append(f"  GPU {gpu_id} (Seed {seed}): TRAINING | {last_line[:70]}")
            else:
                status_lines.append(f"  GPU {gpu_id} (Seed {seed}): FINISHED | {last_line[:70]}")
        ssh.close()

        elapsed = int(time.time() - t0)
        print(f"[{elapsed}s elapsed]", flush=True)
        for l in status_lines:
            print(l, flush=True)
        print("-" * 50, flush=True)

        if all_done:
            print(f"All 5 seeds finished training in {elapsed}s!\n", flush=True)
            break
        time.sleep(poll_interval)


def launch_evaluation():
    print("=== 4. LAUNCHING 5 SEEDS PHASE SCAN EVALUATION ON NODE 2 (GPUs 0-4) ===", flush=True)
    ssh = get_client()
    ssh.exec_command(f"mkdir -p {REMOTE_ROOT}/logs/dense_eval {REMOTE_ROOT}/artifacts/single_task_dense_vs_multitask_moe_scan")

    launch_cmds = []
    for gpu_id, seed in enumerate(SEEDS):
        log_path = f"{REMOTE_ROOT}/logs/dense_eval/seed{seed}.log"
        out_dir = f"artifacts/single_task_dense_vs_multitask_moe_scan/parts/seed{seed}"
        launch_cmds.append(
            f"( CUDA_VISIBLE_DEVICES={gpu_id} ./run_env.sh python3 -u scripts/eval_single_task_dense_phase_scan.py "
            f"--farm wtb --seeds {seed} --device cuda:0 --output-dir {out_dir} > {log_path} 2>&1 & )"
        )
    full_cmd = f"cd {REMOTE_ROOT} && " + " ; ".join(launch_cmds)
    stdin, stdout, stderr = ssh.exec_command(full_cmd)
    stdout.channel.recv_exit_status()
    ssh.close()
    print("All 5 evaluation jobs launched concurrently on GPUs 0-4.\n", flush=True)


def monitor_evaluation(poll_interval: int = 15):
    print("=== 5. MONITORING PHASE SCAN EVALUATION ===", flush=True)
    t0 = time.time()
    while True:
        all_done = True
        status_lines = []
        ssh = get_client()
        for gpu_id, seed in enumerate(SEEDS):
            log_path = f"{REMOTE_ROOT}/logs/dense_eval/seed{seed}.log"
            stdin, stdout, stderr = ssh.exec_command(f"ps aux | grep 'eval_single_task_dense_phase_scan.py --farm wtb --seeds {seed}' | grep -v grep | wc -l")
            count = int(stdout.read().decode().strip() or "0")
            stdin, stdout, stderr = ssh.exec_command(f"tail -n 1 {log_path} 2>/dev/null")
            last_line = stdout.read().decode().strip()
            if count > 0:
                all_done = False
                status_lines.append(f"  GPU {gpu_id} (Seed {seed}): EVALUATING | {last_line[:70]}")
            else:
                status_lines.append(f"  GPU {gpu_id} (Seed {seed}): FINISHED | {last_line[:70]}")
        ssh.close()

        elapsed = int(time.time() - t0)
        print(f"[{elapsed}s elapsed]", flush=True)
        for l in status_lines:
            print(l, flush=True)
        print("-" * 50, flush=True)

        if all_done:
            print(f"All 5 seeds finished evaluation in {elapsed}s!\n", flush=True)
            break
        time.sleep(poll_interval)


def retrieve_artifacts():
    print("=== 6. RETRIEVING ARTIFACTS FROM NODE 2 ===", flush=True)
    local_base = REPO_ROOT / "artifacts" / "single_task_dense_vs_multitask_moe_scan"
    local_base.mkdir(parents=True, exist_ok=True)

    ssh = get_client()
    sftp = ssh.open_sftp()
    for seed in SEEDS:
        remote_seed_dir = f"{REMOTE_ROOT}/artifacts/single_task_dense_vs_multitask_moe_scan/parts/seed{seed}"
        local_seed_dir = local_base / "parts" / f"seed{seed}"
        local_seed_dir.mkdir(parents=True, exist_ok=True)

        try:
            files = sftp.listdir(remote_seed_dir)
            for f in files:
                rem_f = f"{remote_seed_dir}/{f}"
                loc_f = local_seed_dir / f
                sftp.get(rem_f, str(loc_f))
                print(f"  Downloaded {f} for Seed {seed} ({loc_f.stat().st_size} bytes)", flush=True)
        except Exception as e:
            print(f"  Error retrieving seed {seed}: {e}", flush=True)

        # Retrieve training summary if present
        try:
            rem_sum = f"{REMOTE_ROOT}/artifacts/capacity_matched_dense_wtb/wtb_dense_seed{seed}/training_summary.json"
            loc_sum = REPO_ROOT / "artifacts" / "capacity_matched_dense_wtb" / f"wtb_dense_seed{seed}" / "training_summary.json"
            loc_sum.parent.mkdir(parents=True, exist_ok=True)
            sftp.get(rem_sum, str(loc_sum))
            print(f"  Downloaded training summary for Seed {seed}", flush=True)
        except Exception:
            pass

    sftp.close()
    ssh.close()
    print("Artifact retrieval completed.\n", flush=True)


def merge_and_aggregate():
    print("=== 7. AGGREGATING RESULTS ACROSS ALL 5 SEEDS ===", flush=True)
    local_base = REPO_ROOT / "artifacts" / "single_task_dense_vs_multitask_moe_scan"
    parts_dirs = [local_base / "parts" / f"seed{s}" for s in SEEDS]

    scan_dfs = []
    abs_dfs = []
    for s, pdir in zip(SEEDS, parts_dirs):
        scan_f = pdir / "phase_scan_results_by_seed.csv"
        abs_f = pdir / "phase_scan_risk_coverage_by_seed.csv"
        if scan_f.exists():
            df_s = pd.read_csv(scan_f)
            df_s["seed"] = s
            scan_dfs.append(df_s)
        if abs_f.exists():
            df_a = pd.read_csv(abs_f)
            df_a["seed"] = s
            abs_dfs.append(df_a)

    if not scan_dfs:
        print("No scan result files found to merge!", flush=True)
        return

    full_scan = pd.concat(scan_dfs, ignore_index=True)
    full_scan.to_csv(local_base / "phase_scan_results_by_seed.csv", index=False)

    full_abs = pd.concat(abs_dfs, ignore_index=True) if abs_dfs else pd.DataFrame()
    if not full_abs.empty:
        full_abs.to_csv(local_base / "phase_scan_risk_coverage_by_seed.csv", index=False)

    # 1. Main Ablation Summary Table (mirrors Table 3 across all 30 conditions)
    agg_scan = full_scan.groupby(["lead_step", "lead_minutes", "lag_steps", "lag_minutes", "channel_mode"]).agg({
        "phys_clean_cost": ["mean", "std"],
        "phys_clean_shortage": ["mean", "std"],
        "phys_clean_viol": ["mean", "std"],
        "phys_recal_cost": ["mean", "std"],
        "phys_recal_shortage": ["mean", "std"],
        "phys_recal_viol": ["mean", "std"],
        "moe_frozen_cost": ["mean", "std"],
        "moe_frozen_shortage": ["mean", "std"],
        "moe_frozen_viol": ["mean", "std"],
        "moe_routed_cost": ["mean", "std"],
        "moe_routed_shortage": ["mean", "std"],
        "moe_routed_viol": ["mean", "std"],
        "dense_frozen_cost": ["mean", "std"],
        "dense_frozen_shortage": ["mean", "std"],
        "dense_frozen_viol": ["mean", "std"],
        "dense_vs_moe_frozen_cost_ratio": ["mean", "std"],
        "dense_vs_moe_routed_cost_ratio": ["mean", "std"],
    }).reset_index()

    # Flatten column names
    agg_scan.columns = [
        "_".join(col).strip("_") if isinstance(col, tuple) else col
        for col in agg_scan.columns
    ]

    target_artifact = REPO_ROOT / "artifacts" / "single_task_dense_vs_multitask_moe_ablation.csv"
    agg_scan.to_csv(target_artifact, index=False)
    print(f"\n[TARGET ARTIFACT WRITTEN] {target_artifact}", flush=True)

    # Also save dedicated risk-coverage aggregate (mirrors Table 4)
    if not full_abs.empty:
        agg_abs = full_abs.groupby(["model", "lead_step", "lag_steps", "channel_mode", "coverage"]).agg({
            "realized_coverage": ["mean", "std"],
            "accepted_violation_rate": ["mean", "std"],
            "fleet_violation_rate": ["mean", "std"],
            "fleet_total_cost": ["mean", "std"],
            "fleet_shortage_mwh": ["mean", "std"],
            "random_fleet_viol": ["mean", "std"],
            "random_fleet_cost": ["mean", "std"],
            "uniform_alpha": ["mean", "std"],
            "uniform_fleet_viol": ["mean", "std"],
            "uniform_fleet_cost": ["mean", "std"],
            "uniform_val_alpha": ["mean", "std"],
            "uniform_val_fleet_viol": ["mean", "std"],
            "uniform_val_fleet_cost": ["mean", "std"],
        }).reset_index()
        agg_abs.columns = [
            "_".join(col).strip("_") if isinstance(col, tuple) else col
            for col in agg_abs.columns
        ]
        abs_target = REPO_ROOT / "artifacts" / "single_task_dense_vs_multitask_moe_risk_coverage.csv"
        agg_abs.to_csv(abs_target, index=False)
        print(f"[RISK COVERAGE ARTIFACT WRITTEN] {abs_target}", flush=True)


if __name__ == "__main__":
    if "--merge-only" in sys.argv:
        merge_and_aggregate()
    elif "--retrieve-only" in sys.argv:
        retrieve_artifacts()
        merge_and_aggregate()
    elif "--eval-only" in sys.argv:
        sync_files()
        launch_evaluation()
        monitor_evaluation()
        retrieve_artifacts()
        merge_and_aggregate()
    else:
        sync_files()
        launch_training()
        monitor_training()
        launch_evaluation()
        monitor_evaluation()
        retrieve_artifacts()
        merge_and_aggregate()
