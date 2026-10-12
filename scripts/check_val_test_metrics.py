from pathlib import Path
import numpy as np

def check_metrics(d):
    pred = np.load(d / "pred.npy")
    target = np.load(d / "target.npy")
    mask = np.load(d / "mask.npy")
    anc = np.load(d / "anchor_physics.npy")
    gate = np.load(d / "gate_prob.npy") if (d / "gate_prob.npy").exists() else None
    print(f"Directory: {d.parent.name}")
    print(f"  pred: {pred.shape}, target: {target.shape}, mask: {mask.shape}, anc: {anc.shape}")
    if gate is not None:
        print(f"  gate_prob: {gate.shape}")
    # Shortfall
    s = np.maximum(pred - target, 0.0)
    print(f"  Mean shortfall at h=1: {s[:, 0, :][mask[:, 0, :] > 0].mean():.2f} kW")
    print(f"  Mean shortfall at h=6: {s[:, 5, :][mask[:, 5, :] > 0].mean():.2f} kW")
    print(f"  Wspd mean: {anc[..., 0].mean():.2f}, Pab mean: {anc[..., 1].mean():.2f}, Patv mean: {anc[..., 3].mean():.2f}")

for base in [
    Path("artifacts/signature_gate_farms_runs_20260903/penmanshiel/canonical/wtb_bal_align_force_seed201"),
    Path("artifacts/external_wind_runs/penmanshiel/chronological/external_wind_bal_align_force_seed201"),
    Path("artifacts/signature_gate_farms_runs_20260903/kelmarsh/canonical/wtb_bal_align_force_seed201"),
    Path("artifacts/external_wind_runs/kelmarsh/chronological/external_wind_bal_align_force_seed201"),
]:
    print("=== Validation Split ===")
    check_metrics(base / "val_metrics")
    print("=== Test Split ===")
    check_metrics(base / "test_metrics")
    print()
