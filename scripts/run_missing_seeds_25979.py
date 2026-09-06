import time
import paramiko

def run_missing_seeds():
    print("==================== CONNECTING TO NODE 25979 ====================")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.17.251", port=25979, username="root", password="061022", timeout=15)

    # First verify environment and LD_PRELOAD
    check_cmd = "python3 -c 'import torch; print(torch.cuda.is_available(), torch.cuda.device_count())'"
    stdin, stdout, stderr = ssh.exec_command(f"cd /root/paper3_audit_rerun_20260830 && {check_cmd}")
    print(f"CUDA check: {stdout.read().decode().strip()}")

    # Run seed 201 sequentially, then seed 204
    for seed, gpu in [(201, 0), (204, 1)]:
        print(f"\n>>> Starting Seed {seed} on GPU {gpu} at {time.strftime('%X')}...")
        cmd = f"""cd /root/paper3_audit_rerun_20260830 && \
if [ -d "/opt/hpcx/ucx/lib" ]; then
  export LD_PRELOAD='/opt/hpcx/ucx/lib/libucm.so.0 /opt/hpcx/ucx/lib/libucs.so.0 /opt/hpcx/ucx/lib/libuct.so.0 /opt/hpcx/ucx/lib/libucp.so.0'
fi
export PYTHONPATH=.
export PYTHONUNBUFFERED=1
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
export MPLBACKEND=Agg

python3 scripts/remote_risk_layer_benchmark.py \
  --seeds {seed} \
  --device "cuda:{gpu}" \
  --lead-step 5 \
  --dataloader-workers 0 \
  --output-dir "artifacts/clean_evidence_v2/risk_layer_benchmark/h6_lead6/run_seed_{seed}" \
  --n-boot 1000 \
  > "logs/phase3_h6/seed_{seed}.log" 2>&1
"""
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        print(f">>> Seed {seed} finished with exit code {exit_status} at {time.strftime('%X')}")

        # Check log tail
        stdin, stdout, stderr = ssh.exec_command(f"tail -n 15 /root/paper3_audit_rerun_20260830/logs/phase3_h6/seed_{seed}.log")
        print(f"Log tail for seed {seed}:\n{stdout.read().decode()}")

        if exit_status != 0:
            print(f"ERROR: Seed {seed} failed!")
            ssh.close()
            return False

    print("\n>>> Merging results on 25979 for h6_lead6...")
    merge_cmd = """cd /root/paper3_audit_rerun_20260830 && \
python3 scripts/merge_phase3_results.py \
  --input-root artifacts/clean_evidence_v2/risk_layer_benchmark/h6_lead6 \
  --output-dir artifacts/clean_evidence_v2/risk_layer_benchmark/h6_lead6
"""
    stdin, stdout, stderr = ssh.exec_command(merge_cmd)
    exit_status = stdout.channel.recv_exit_status()
    print(f">>> Merge exit code: {exit_status}\n{stdout.read().decode()}\n{stderr.read().decode()}")

    ssh.close()
    return True

if __name__ == "__main__":
    run_missing_seeds()
