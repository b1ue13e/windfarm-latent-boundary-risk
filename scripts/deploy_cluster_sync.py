import os
from pathlib import Path
import paramiko

FILES_TO_SYNC = [
    "scripts/launch_25329_4gpu.sh",
    "scripts/launch_25979_6gpu.sh",
    "scripts/launch_kelmarsh_benchmark.sh",
    "scripts/launch_penmanshiel_benchmark.sh",
    "scripts/remote_risk_layer_benchmark.py",
    "scripts/remote_matched_modular_baseline.py",
    "scripts/run_cluster_5seed_hard_gate.py",
    "src/__init__.py",
    "src/decision/__init__.py",
    "src/decision/bess_rolling_dispatch.py",
]

def sync_to_server(port):
    print(f"\n==================== SYNCING TO SERVER {port} ====================")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.17.251", port=port, username="root", password="061022", timeout=15)
    sftp = ssh.open_sftp()
    remote_root = "/root/paper3_audit_rerun_20260830"

    for rel_path in FILES_TO_SYNC:
        local_path = Path(rel_path)
        if not local_path.exists():
            print(f"Warning: {local_path} does not exist locally!")
            continue

        remote_path = f"{remote_root}/{rel_path.replace(os.sep, '/')}"
        remote_dir = "/".join(remote_path.split("/")[:-1])

        # Ensure directory exists on remote
        stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
        stdout.read()

        sftp.put(str(local_path), remote_path)
        if rel_path.endswith(".sh"):
            ssh.exec_command(f"chmod +x {remote_path}")
        print(f"Uploaded {rel_path} -> {remote_path}")

    # Verify key injected lines
    stdin, stdout, stderr = ssh.exec_command(
        f"grep -n 'rated-wind' {remote_root}/scripts/launch_kelmarsh_benchmark.sh {remote_root}/scripts/launch_penmanshiel_benchmark.sh"
    )
    print("Verification of rated-wind:\n", stdout.read().decode())

    stdin, stdout, stderr = ssh.exec_command(
        f"grep -n 'dataloader-workers' {remote_root}/scripts/remote_risk_layer_benchmark.py"
    )
    print("Verification of dataloader-workers:\n", stdout.read().decode())

    sftp.close()
    ssh.close()
    print(f"Server {port} sync completed successfully.")

if __name__ == "__main__":
    for p in [25329, 25979]:
        sync_to_server(p)
