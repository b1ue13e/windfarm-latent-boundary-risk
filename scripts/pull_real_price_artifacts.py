"""Pull real-price dynamic settlement artifacts from remote GPU cluster."""
from __future__ import annotations

import subprocess
from pathlib import Path

local_dir = Path("artifacts/dynamic_price_settlement_audit")
local_dir.mkdir(parents=True, exist_ok=True)

remote_host = "root@192.168.17.251"
port = "25329"
remote_dir = "/root/paper3_audit_rerun_20260830/artifacts/dynamic_price_settlement_audit"

files = [
    "kelmarsh_real_price_by_seed.csv",
    "kelmarsh_real_price_paired_summary.csv",
    "penmanshiel_real_price_by_seed.csv",
    "penmanshiel_real_price_paired_summary.csv",
    "table_real_price_dynamic_settlement_a12.tex",
    "worker_km_gpu0.log",
    "worker_km_gpu1.log",
    "worker_pm_gpu2.log",
    "worker_pm_gpu3.log",
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
