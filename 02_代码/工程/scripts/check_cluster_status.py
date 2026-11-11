import paramiko

def check_logs_and_artifacts(port):
    print(f"\n==================== CHECKING ARTIFACTS & LOGS ON {port} ====================")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.17.251", port=port, username="root", password="061022", timeout=10)

    # Check logs
    commands = [
        "ls -la /root/paper3_audit_rerun_20260830/logs/* 2>/dev/null",
        "find /root/paper3_audit_rerun_20260830/artifacts/clean_evidence_v2 -name 'results_by_seed.csv' -o -name 'cross_seed_aggregate.csv'",
    ]
    for cmd in commands:
        print(f"\n--- Output of: {cmd} ---")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode())

    # Check tail of recent logs
    tail_cmd = "tail -n 25 /root/paper3_audit_rerun_20260830/logs/*/*.log 2>/dev/null"
    print(f"\n--- Tail of logs in subdirectories ---")
    stdin, stdout, stderr = ssh.exec_command(tail_cmd)
    print(stdout.read().decode()[:4000])

    ssh.close()

if __name__ == "__main__":
    for p in [25329, 25979]:
        check_logs_and_artifacts(p)
