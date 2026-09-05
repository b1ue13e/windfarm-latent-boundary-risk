import subprocess
import sys

def run_remote(cmd: str, host="root@192.168.17.251", port="25329"):
    clean_cmd = cmd.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    proc = subprocess.run(
        ["ssh", "-p", port, host, "python3", "-"],
        input=clean_cmd,
        capture_output=True,
    )
    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = proc.stderr.decode("utf-8", errors="replace")
    print("STDOUT:\n", stdout)
    if stderr:
        print("STDERR:\n", stderr)
    return proc.returncode

def run_bash(bash_cmd: str, host="root@192.168.17.251", port="25329"):
    clean_cmd = bash_cmd.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    proc = subprocess.run(
        ["ssh", "-p", port, host, "bash", "-s"],
        input=clean_cmd,
        capture_output=True,
    )
    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = proc.stderr.decode("utf-8", errors="replace")
    print("STDOUT:\n", stdout)
    if stderr:
        print("STDERR:\n", stderr)
    return proc.returncode

if __name__ == "__main__":
    test_code = """
import numpy as np
from pathlib import Path
p = Path("/root/paper3_audit_rerun_20260830/artifacts/trainweight_full_rerun_20260830/wtb_full_seed201/test_metrics")
for f in sorted(p.glob("*.npy")):
    arr = np.load(f, mmap_mode="r")
    print(f"{f.name:25s} shape={str(arr.shape):20s} dtype={arr.dtype}")
"""
    run_remote(test_code)
