import subprocess

def run_ssh(cmd, port="25329", host="root@192.168.17.251"):
    proc = subprocess.run(
        ["ssh", "-p", str(port), host, cmd],
        capture_output=True,
        text=True
    )
    return proc.stdout, proc.stderr, proc.returncode

def run_remote_python(code: str, port="25329", host="root@192.168.17.251"):
    clean_code = code.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    proc = subprocess.run(
        ["ssh", "-p", str(port), host, "/root/paper3_audit_rerun_20260830/run_env.sh", "python3", "-"],
        input=clean_code,
        capture_output=True,
    )
    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = proc.stderr.decode("utf-8", errors="replace")
    return stdout, stderr, proc.returncode

if __name__ == "__main__":
    code = """
import torch
p = "/root/paper3_audit_rerun_20260830/artifacts/dense_classifier_runs_20260904/canonical/wtb_bal_align_force_seed201/best_model.pt"
ckpt = torch.load(p, map_location="cpu")
print("keys:", list(ckpt.keys()))
print("mode:", ckpt["train_config"].get("mode"))
"""
    out, err, _ = run_remote_python(code)
    print("OUTPUT:", out)
    if err:
        print("ERR:", err)

