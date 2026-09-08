"""Orchestrator to deploy, run, retrieve, and merge the 5-seed decisive fair risk benchmark.

Uses 25329 (4x RTX 4090: seeds 201, 202, 203, 204) and 25979 (RTX 4090: seed 205)
to execute all 5 seeds in parallel.
"""
import os
import sys
import time
from pathlib import Path
import paramiko

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FILES_TO_SYNC = [
    "scripts/decisive_fair_risk_benchmark.py",
    "scripts/merge_benchmark_seeds.py",
    "tests/test_decisive_risk_benchmark.py",
    "windfarm_moe/arrival_feed.py",
]

SERVERS = {
    25329: {"host": "192.168.17.251", "port": 25329, "user": "root", "pwd": "061022", "seeds": [201, 202, 203, 204]},
    25979: {"host": "192.168.17.251", "port": 25979, "user": "root", "pwd": "061022", "seeds": [205]},
}

REMOTE_ROOT = "/root/paper3_audit_rerun_20260830"


def get_client(port: int) -> paramiko.SSHClient:
    cfg = SERVERS[port]
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(cfg["host"], port=cfg["port"], username=cfg["user"], password=cfg["pwd"], timeout=20)
    return ssh


def sync_files():
    print("=== 1. SYNCING FILES TO REMOTE SERVERS ===")
    for port in SERVERS:
        print(f"Syncing to server port {port}...")
        ssh = get_client(port)
        sftp = ssh.open_sftp()
        for rel in FILES_TO_SYNC:
            local = REPO_ROOT / rel
            remote = f"{REMOTE_ROOT}/{rel.replace(os.sep, '/')}"
            remote_dir = "/".join(remote.split("/")[:-1])
            ssh.exec_command(f"mkdir -p {remote_dir}")
            sftp.put(str(local), remote)
            print(f"  [{port}] Synced {rel} -> {remote}")
        sftp.close()
        ssh.close()
    print("Sync completed successfully.\n")


def launch_jobs():
    print("=== 2. LAUNCHING 5 SEEDS IN PARALLEL ===")
    procs = []
    for port, cfg in SERVERS.items():
        ssh = get_client(port)
        # Ensure log and output dirs
        ssh.exec_command(f"mkdir -p {REMOTE_ROOT}/logs/decisive_fair_risk {REMOTE_ROOT}/artifacts/decisive_fair_risk")
        for idx, seed in enumerate(cfg["seeds"]):
            gpu_id = idx  # On 25329: 0, 1, 2, 3; on 25979: 0
            log_path = f"{REMOTE_ROOT}/logs/decisive_fair_risk/wtb_seed{seed}.log"
            out_dir = f"artifacts/decisive_fair_risk/wtb_parts/seed{seed}"
            cmd = (
                f"cd {REMOTE_ROOT} && "
                f"nohup env CUDA_VISIBLE_DEVICES={gpu_id} ./run_env.sh python3 scripts/decisive_fair_risk_benchmark.py "
                f"--farm wtb --seeds {seed} --device cuda:0 --output-dir {out_dir} > {log_path} 2>&1 & echo $!"
            )
            stdin, stdout, stderr = ssh.exec_command(cmd)
            pid = stdout.read().decode().strip()
            print(f"  Server {port} (GPU {gpu_id}): Seed {seed} launched with PID {pid} -> {log_path}")
        ssh.close()
    print("All jobs launched!\n")


def monitor_jobs():
    print("=== 3. MONITORING RUNNING JOBS ===")
    t0 = time.time()
    while True:
        all_done = True
        status_lines = []
        for port, cfg in SERVERS.items():
            ssh = get_client(port)
            for seed in cfg["seeds"]:
                log_path = f"{REMOTE_ROOT}/logs/decisive_fair_risk/wtb_seed{seed}.log"
                stdin, stdout, stderr = ssh.exec_command(f"ps aux | grep 'seeds {seed}' | grep -v grep | wc -l")
                count = int(stdout.read().decode().strip() or "0")
                stdin, stdout, stderr = ssh.exec_command(f"tail -n 1 {log_path} 2>/dev/null")
                last_line = stdout.read().decode().strip()
                if count > 0:
                    all_done = False
                    status_lines.append(f"  [{port}] Seed {seed}: RUNNING ({last_line[:50]})")
                else:
                    status_lines.append(f"  [{port}] Seed {seed}: FINISHED ({last_line[:50]})")
            ssh.close()

        elapsed = int(time.time() - t0)
        print(f"[{elapsed}s elapsed]")
        for l in status_lines:
            print(l)
        print("-" * 50)

        if all_done:
            print(f"All seeds finished in {elapsed}s!\n")
            break
        time.sleep(15)


def retrieve_artifacts():
    print("=== 4. RETRIEVING ARTIFACTS ===")
    local_base = REPO_ROOT / "artifacts" / "decisive_fair_risk"
    local_base.mkdir(parents=True, exist_ok=True)

    for port, cfg in SERVERS.items():
        ssh = get_client(port)
        sftp = ssh.open_sftp()
        for seed in cfg["seeds"]:
            remote_seed_dir = f"{REMOTE_ROOT}/artifacts/decisive_fair_risk/wtb_parts/seed{seed}/wtb"
            local_seed_dir = local_base / "wtb_parts" / f"seed{seed}" / "wtb"
            local_seed_dir.mkdir(parents=True, exist_ok=True)

            try:
                files = sftp.listdir(remote_seed_dir)
                for f in files:
                    rem_f = f"{remote_seed_dir}/{f}"
                    loc_f = local_seed_dir / f
                    sftp.get(rem_f, str(loc_f))
                    print(f"  Downloaded {f} for Seed {seed} ({loc_f.stat().st_size} bytes)")
            except Exception as e:
                print(f"  Error retrieving seed {seed} from {port}: {e}")

            # Also retrieve log file
            try:
                rem_log = f"{REMOTE_ROOT}/logs/decisive_fair_risk/wtb_seed{seed}.log"
                local_log_dir = REPO_ROOT / "logs" / "decisive_fair_risk"
                local_log_dir.mkdir(parents=True, exist_ok=True)
                loc_log = local_log_dir / f"wtb_seed{seed}.log"
                sftp.get(rem_log, str(loc_log))
                print(f"  Downloaded log for Seed {seed}")
            except Exception as e:
                print(f"  Could not download log for seed {seed}: {e}")

        sftp.close()
        ssh.close()
    print("Artifact retrieval completed.\n")


def merge_and_report():
    print("=== 5. MERGING ALL SEEDS LOCALLY ===")
    from scripts.merge_benchmark_seeds import merge_seeds
    out_dir = REPO_ROOT / "artifacts" / "decisive_fair_risk" / "wtb"
    base_dir = out_dir
    parts_dirs = [REPO_ROOT / "artifacts" / "decisive_fair_risk" / "wtb_parts" / f"seed{s}" / "wtb" for s in [201, 202, 203, 204, 205]]
    merge_seeds("wtb", base_dir, parts_dirs, out_dir)

    # Also copy summary files to top-level artifacts/decisive_fair_risk/
    top_dir = REPO_ROOT / "artifacts" / "decisive_fair_risk"
    for name in ["benchmark_report.md", "route_dispatch_verdict.json", "decisive_cross_seed_aggregate.csv", "decisive_results_by_seed.csv"]:
        src = out_dir / name
        dst = top_dir / name
        if src.exists():
            dst.write_bytes(src.read_bytes())
            print(f"Copied {name} to {dst}")


if __name__ == "__main__":
    if "--merge-only" in sys.argv:
        merge_and_report()
    else:
        sync_files()
        launch_jobs()
        monitor_jobs()
        retrieve_artifacts()
        merge_and_report()
