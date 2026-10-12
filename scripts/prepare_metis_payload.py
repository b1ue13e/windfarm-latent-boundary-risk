"""Prepares a compact payload archive containing strictly required inputs for EXP-02.
"""
import tarfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
output_tar = REPO_ROOT / "exp02_metis_payload.tar.gz"

print(f"Creating payload archive at: {output_tar}")
with tarfile.open(output_tar, "w:gz") as tar:
    # 1. Code
    for py_file in (REPO_ROOT / "windfarm_moe").glob("**/*.py"):
        rel = py_file.relative_to(REPO_ROOT)
        tar.add(py_file, arcname=str(rel).replace("\\", "/"))
    tar.add(REPO_ROOT / "scripts/run_exp02_zero_privileged_supervision.py", arcname="scripts/run_exp02_zero_privileged_supervision.py")

    # 2. Cache bundle (required files only)
    cache_dir = REPO_ROOT / "artifacts/cache_strictmask_trainweights/wtb_245d"
    for name in ["metadata.json", "physics_model.npy", "features.npy", "regime_primary.npy", "regime_primary_valid.npy"]:
        p = cache_dir / name
        if p.exists():
            tar.add(p, arcname=f"artifacts/cache_strictmask_trainweights/wtb_245d/{name}")

    # 3. Residuals
    res_file = REPO_ROOT / "artifacts/fixed_forecast_residuals.npz"
    if res_file.exists():
        tar.add(res_file, arcname="artifacts/fixed_forecast_residuals.npz")

    # 4. Oracle STGQ gate_prob only
    oracle_dir = REPO_ROOT / "artifacts/strictmask_ablation_rerun_wtb_full"
    for seed_dir in oracle_dir.glob("wtb_bal_align_seed*"):
        for sub in ["val_metrics", "test_metrics"]:
            gate = seed_dir / sub / "gate_prob.npy"
            if gate.exists():
                tar.add(gate, arcname=f"artifacts/strictmask_ablation_rerun_wtb_full/{seed_dir.name}/{sub}/gate_prob.npy")

print(f"Payload created successfully! Size: {output_tar.stat().st_size / 1e6:.2f} MB")
