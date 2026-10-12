import json
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from pathlib import Path

# Parameters
RHO = 10.0
CRITICAL_FRACTILE = 0.90  # 1 - 1/rho
DT = 1.0 / 6.0  # 10 minutes in hours
N_WSPD_BINS = 10

def load_metrics_bundle(run_dir: Path, split: str):
    d = run_dir / f"{split}_metrics"
    pred = np.load(d / "pred.npy")        # (T, 24, N)
    target = np.load(d / "target.npy")    # (T, 24, N)
    mask = np.load(d / "mask.npy") > 0.5  # (T, 24, N)
    anc = np.load(d / "anchor_physics.npy") # (T, N, 4)
    gate = np.load(d / "gate_prob.npy") if (d / "gate_prob.npy").exists() else None # (T, N, 4)
    time_idx = np.load(d / "anchor_index.npy") if (d / "anchor_index.npy").exists() else np.arange(pred.shape[0])
    return {
        "pred": pred,
        "target": target,
        "mask": mask,
        "anchor": anc,
        "gate": gate,
        "time": time_idx,
    }

print("Testing prototype metrics loading...")
p_trans = Path("artifacts/signature_gate_farms_runs_20260903/penmanshiel/canonical/wtb_bal_align_force_seed201")
val_data = load_metrics_bundle(p_trans, "val")
test_data = load_metrics_bundle(p_trans, "test")

print("Val pred shape:", val_data["pred"].shape, "Test pred shape:", test_data["pred"].shape)
print("Val anchor shape:", val_data["anchor"].shape, "Test anchor shape:", test_data["anchor"].shape)
