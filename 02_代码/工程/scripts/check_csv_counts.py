import paramiko

for port in [25329, 25979]:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.17.251', port=port, username='root', password='061022')
    stdin, stdout, stderr = ssh.exec_command('for f in /root/paper3_audit_rerun_20260830/artifacts/clean_evidence_v2/risk_layer_benchmark/*/run_seed_*/results_by_seed.csv; do wc -l "$f"; done')
    print(f'=== PORT {port} CSV LINE COUNTS ===')
    print(stdout.read().decode())
    ssh.close()
