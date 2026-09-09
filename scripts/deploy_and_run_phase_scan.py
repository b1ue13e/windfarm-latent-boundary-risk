"""Orchestrator to deploy, run, monitor, and retrieve the Boundary Phase Scan on Node 2 (port 25979).

Uses 5 RTX 4090 GPUs in parallel on Node 2:
- GPU 0: Seed 201
- GPU 1: Seed 202
- GPU 2: Seed 203
- GPU 3: Seed 204
- GPU 4: Seed 205
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
    "scripts/run_boundary_phase_scan.py",
    "scripts/decisive_fair_risk_benchmark.py",
    "windfarm_moe/arrival_feed.py",
]


def get_client() -> paramiko.SSHClient:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(NODE2_HOST, port=NODE2_PORT, username=NODE2_USER, password=NODE2_PWD, timeout=20)
    return ssh


def sync_files():
    print("=== 1. SYNCING BENCHMARK SCRIPTS TO NODE 2 ===")
    ssh = get_client()
    sftp = ssh.open_sftp()
    for rel in FILES_TO_SYNC:
        local = REPO_ROOT / rel
        remote = f"{REMOTE_ROOT}/{rel.replace(os.sep, '/')}"
        remote_dir = "/".join(remote.split("/")[:-1])
        ssh.exec_command(f"mkdir -p {remote_dir}")
        sftp.put(str(local), remote)
        print(f"  Synced {rel} -> {remote}")
    sftp.close()
    ssh.close()
    print("Sync completed successfully.\n")


def launch_jobs():
    print("=== 2. LAUNCHING 5 SEEDS IN PARALLEL ON NODE 2 (GPUs 0-4) ===", flush=True)
    ssh = get_client()
    ssh.exec_command(f"mkdir -p {REMOTE_ROOT}/logs/phase_scan {REMOTE_ROOT}/artifacts/boundary_phase_scan")

    # Launch all 5 seeds in a single detached shell command so paramiko does not block
    launch_cmds = []
    for gpu_id, seed in enumerate(SEEDS):
        log_path = f"{REMOTE_ROOT}/logs/phase_scan/seed{seed}.log"
        out_dir = f"artifacts/boundary_phase_scan/parts/seed{seed}"
        launch_cmds.append(
            f"( CUDA_VISIBLE_DEVICES={gpu_id} ./run_env.sh python3 -u scripts/run_boundary_phase_scan.py "
            f"--farm wtb --seeds {seed} --device cuda:0 --output-dir {out_dir} > {log_path} 2>&1 & )"
        )
    full_cmd = f"cd {REMOTE_ROOT} && " + " ; ".join(launch_cmds)
    stdin, stdout, stderr = ssh.exec_command(full_cmd)
    stdout.channel.recv_exit_status()
    ssh.close()
    print("All 5 seeds launched concurrently on GPUs 0-4.\n", flush=True)


def monitor_jobs():
    print("=== 3. MONITORING RUNNING JOBS ===", flush=True)
    t0 = time.time()
    while True:
        all_done = True
        status_lines = []
        ssh = get_client()
        for gpu_id, seed in enumerate(SEEDS):
            log_path = f"{REMOTE_ROOT}/logs/phase_scan/seed{seed}.log"
            stdin, stdout, stderr = ssh.exec_command(f"ps aux | grep 'run_boundary_phase_scan.py --farm wtb --seeds {seed}' | grep -v grep | wc -l")
            count = int(stdout.read().decode().strip() or "0")
            stdin, stdout, stderr = ssh.exec_command(f"tail -n 1 {log_path} 2>/dev/null")
            last_line = stdout.read().decode().strip()
            if count > 0:
                all_done = False
                status_lines.append(f"  GPU {gpu_id} (Seed {seed}): RUNNING | {last_line[:65]}")
            else:
                status_lines.append(f"  GPU {gpu_id} (Seed {seed}): FINISHED | {last_line[:65]}")
        ssh.close()

        elapsed = int(time.time() - t0)
        print(f"[{elapsed}s elapsed]", flush=True)
        for l in status_lines:
            print(l, flush=True)
        print("-" * 50, flush=True)

        if all_done:
            print(f"All 5 seeds completed successfully in {elapsed}s!\n", flush=True)
            break
        time.sleep(10)


def retrieve_artifacts():
    print("=== 4. RETRIEVING ARTIFACTS FROM NODE 2 ===", flush=True)
    local_base = REPO_ROOT / "artifacts" / "boundary_phase_scan"
    local_base.mkdir(parents=True, exist_ok=True)

    ssh = get_client()
    sftp = ssh.open_sftp()
    for seed in SEEDS:
        remote_seed_dir = f"{REMOTE_ROOT}/artifacts/boundary_phase_scan/parts/seed{seed}/wtb"
        local_seed_dir = local_base / "parts" / f"seed{seed}" / "wtb"
        local_seed_dir.mkdir(parents=True, exist_ok=True)

        try:
            files = sftp.listdir(remote_seed_dir)
            for f in files:
                rem_f = f"{remote_seed_dir}/{f}"
                loc_f = local_seed_dir / f
                sftp.get(rem_f, str(loc_f))
                print(f"  Downloaded {f} for Seed {seed} ({loc_f.stat().st_size} bytes)")
        except Exception as e:
            print(f"  Error retrieving seed {seed}: {e}")

        # Also download log
        try:
            rem_log = f"{REMOTE_ROOT}/logs/phase_scan/seed{seed}.log"
            loc_log = REPO_ROOT / "logs" / "phase_scan" / f"seed{seed}.log"
            loc_log.parent.mkdir(parents=True, exist_ok=True)
            sftp.get(rem_log, str(loc_log))
            print(f"  Downloaded log for Seed {seed}")
        except Exception:
            pass

    sftp.close()
    ssh.close()
    print("Artifact retrieval completed.\n")


def merge_and_aggregate():
    print("=== 5. MERGING RESULTS ACROSS ALL 5 SEEDS ===")
    local_base = REPO_ROOT / "artifacts" / "boundary_phase_scan"
    parts_dirs = [local_base / "parts" / f"seed{s}" / "wtb" for s in SEEDS]

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
        print("No scan result files found to merge!")
        return

    full_scan = pd.concat(scan_dfs, ignore_index=True)
    full_scan.to_csv(local_base / "phase_scan_results_by_seed.csv", index=False)

    full_abs = pd.concat(abs_dfs, ignore_index=True)
    full_abs.to_csv(local_base / "phase_scan_risk_coverage_by_seed.csv", index=False)

    # Aggregate Scan Matrix
    agg_scan = full_scan.groupby(["lead_step", "lead_minutes", "lag_steps", "lag_minutes", "channel_mode"]).agg({
        "phys_clean_cost": ["mean", "std"],
        "phys_clean_shortage": ["mean", "std"],
        "phys_clean_viol": ["mean", "std"],
        "phys_recal_cost": ["mean", "std"],
        "phys_recal_shortage": ["mean", "std"],
        "phys_recal_viol": ["mean", "std"],
        "frozen_cost": ["mean", "std"],
        "frozen_shortage": ["mean", "std"],
        "frozen_viol": ["mean", "std"],
        "routed_cost": ["mean", "std"],
        "routed_shortage": ["mean", "std"],
        "routed_viol": ["mean", "std"],
        "recalibration_sufficient": ["mean"],
        "representation_advantage": ["mean"],
        "refusal_required": ["mean"],
    }).reset_index()
    agg_scan.to_csv(local_base / "phase_scan_cross_seed_aggregate.csv", index=False)

    # Aggregate Risk-Coverage Curves
    agg_abs = full_abs.groupby(["model", "lead_step", "lag_steps", "channel_mode", "coverage"]).agg({
        "realized_coverage": ["mean", "std"],
        "accepted_violation_rate": ["mean", "std"],
        "fleet_violation_rate": ["mean", "std"],
        "fleet_total_cost": ["mean", "std"],
        "fleet_shortage_mwh": ["mean", "std"],
        "fleet_reserve_mwh": ["mean", "std"],
        "random_fleet_viol": ["mean", "std"],
        "random_fleet_cost": ["mean", "std"],
        "random_acc_viol": ["mean", "std"],
        "uniform_alpha": ["mean", "std"],
        "uniform_fleet_viol": ["mean", "std"],
        "uniform_fleet_cost": ["mean", "std"],
    }).reset_index()
    agg_abs.to_csv(local_base / "phase_scan_risk_coverage_aggregate.csv", index=False)

    print(f"\n[ALL MERGED] Successfully generated unified cross-seed aggregates at {local_base}")


if __name__ == "__main__":
    if "--merge-only" in sys.argv:
        merge_and_aggregate()
    elif "--retrieve-only" in sys.argv:
        retrieve_artifacts()
        merge_and_aggregate()
    else:
        sync_files()
        launch_jobs()
        monitor_jobs()
        retrieve_artifacts()
        merge_and_aggregate()
