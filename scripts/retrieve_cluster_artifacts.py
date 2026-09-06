import os
from pathlib import Path
import paramiko

CLUSTERS = [
    {
        "port": 25329,
        "dirs": [
            "artifacts/clean_evidence_v2/risk_layer_benchmark/h1_lead1",
            "artifacts/clean_evidence_v2/risk_layer_benchmark/kelmarsh_h1",
            "artifacts/clean_evidence_v2/risk_layer_benchmark/kelmarsh_h6",
            "logs/phase3_h1",
            "logs/kelmarsh_bench",
        ]
    },
    {
        "port": 25979,
        "dirs": [
            "artifacts/clean_evidence_v2/risk_layer_benchmark/h6_lead6",
            "artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h1",
            "artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h6",
            "logs/phase3_h6",
            "logs/penmanshiel_bench",
        ]
    }
]

def download_remote_dir(sftp, remote_dir, local_dir):
    local_dir.mkdir(parents=True, exist_ok=True)
    try:
        items = sftp.listdir_attr(remote_dir)
    except Exception as e:
        print(f"Cannot list remote dir {remote_dir}: {e}")
        return

    for item in items:
        r_path = f"{remote_dir}/{item.filename}"
        l_path = local_dir / item.filename
        if item.st_mode & 0o040000:  # Directory
            download_remote_dir(sftp, r_path, l_path)
        else:
            # File
            try:
                sftp.get(r_path, str(l_path))
                # print(f"  Downloaded: {l_path}")
            except Exception as e:
                print(f"  Failed downloading {r_path}: {e}")

def retrieve_all():
    local_root = Path("e:/论文3")
    for cluster in CLUSTERS:
        port = cluster["port"]
        print(f"\n==================== RETRIEVING FROM NODE {port} ====================")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect("192.168.17.251", port=port, username="root", password="061022", timeout=15)
            sftp = ssh.open_sftp()
            for rel_d in cluster["dirs"]:
                r_dir = f"/root/paper3_audit_rerun_20260830/{rel_d}"
                l_dir = local_root / rel_d
                print(f"Syncing: {r_dir} -> {l_dir}")
                download_remote_dir(sftp, r_dir, l_dir)
            sftp.close()
            ssh.close()
            print(f"Completed download from node {port}.")
        except Exception as e:
            print(f"Error on node {port}: {e}")

if __name__ == "__main__":
    retrieve_all()
