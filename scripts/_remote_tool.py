import subprocess
import sys

def run_remote(cmd: str, host="root@192.168.17.251", port="25329"):
    proc = subprocess.run(
        ["ssh", "-p", port, host, "python3", "-"],
        input=cmd,
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    print("STDOUT:\n", proc.stdout)
    if proc.stderr:
        print("STDERR:\n", proc.stderr)
    return proc.returncode

def run_bash(bash_cmd: str, host="root@192.168.17.251", port="25329"):
    proc = subprocess.run(
        ["ssh", "-p", port, host, "bash", "-s"],
        input=bash_cmd,
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    print("STDOUT:\n", proc.stdout)
    if proc.stderr:
        print("STDERR:\n", proc.stderr)
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
