import subprocess
from pathlib import Path

local_dir = Path("artifacts/multiyear_gate_representation_audit")
local_dir.mkdir(parents=True, exist_ok=True)

remote_host = "root@192.168.17.251"
port = "25329"
remote_dir = "/root/paper3_audit_rerun_20260830/artifacts/multiyear_gate_representation_audit"

files = [
    "gate_representation_decay_summary.csv",
    "gate_representation_decay_raw.csv",
]

for f in files:
    cmd = [
        "scp",
        "-P", port,
        f"{remote_host}:{remote_dir}/{f}",
        str(local_dir / f),
    ]
    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print(f"Successfully pulled {f} -> {local_dir / f}")
    else:
        print(f"Error pulling {f}: {res.stderr}")

remote_scripts_dir = "/root/paper3_audit_rerun_20260830/scripts"
local_scripts_dir = Path("scripts")
script_files = [
    "remote_gate_representation_decay.py",
    "run_gate_decay_4090.sh",
]

for sf in script_files:
    cmd = [
        "scp",
        "-P", port,
        f"{remote_host}:{remote_scripts_dir}/{sf}",
        str(local_scripts_dir / sf),
    ]
    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print(f"Successfully pulled {sf} -> {local_scripts_dir / sf}")
    else:
        print(f"Error pulling {sf}: {res.stderr}")
