import paramiko

def audit_dirs(port):
    print(f"\n==================== DIRECTORY AUDIT ON {port} ====================")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.17.251", port=port, username="root", password="061022", timeout=10)

    cmd = "find /root/paper3_audit_rerun_20260830/artifacts/clean_evidence_v2/risk_layer_benchmark -maxdepth 3 -type d"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    dirs = stdout.read().decode().strip().splitlines()
    for d in sorted(dirs):
        # count seeds
        stdin, stdout, stderr = ssh.exec_command(f"ls -d {d}/run_seed_* 2>/dev/null")
        seeds = stdout.read().decode().strip().splitlines()
        stdin, stdout, stderr = ssh.exec_command(f"ls -l {d}/results_by_seed.csv 2>/dev/null")
        res = stdout.read().decode().strip()
        print(f"{d} -> {len(seeds)} seed dirs -> combined results: {'YES' if res else 'NO'}")

    ssh.close()

if __name__ == "__main__":
    for p in [25329, 25979]:
        audit_dirs(p)
