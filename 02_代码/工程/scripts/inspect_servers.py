import paramiko

def inspect(port):
    print(f"==================== SERVER {port} ====================")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect("192.168.17.251", port=port, username="root", password="061022", timeout=10)
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep -E 'python3|bash' | grep -v grep")
        print("--- Active Processes ---")
        print(stdout.read().decode())

        stdin, stdout, stderr = ssh.exec_command("nvidia-smi")
        print("--- GPU Status ---")
        print(stdout.read().decode())

        stdin, stdout, stderr = ssh.exec_command("ls -lt /root/paper3_audit_rerun_20260830/logs 2>/dev/null | head -n 20")
        print("--- Recent Logs Directory ---")
        print(stdout.read().decode())

        ssh.close()
    except Exception as e:
        print(f"Error on port {port}: {e}")

if __name__ == "__main__":
    for p in [25329, 25979]:
        inspect(p)
