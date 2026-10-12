import torch
from pathlib import Path

# Check checkpoints for Penmanshiel and Kelmarsh
ckpt_paths = [
    ("Transferred Penmanshiel 201", Path("artifacts/signature_gate_farms_runs_20260903/penmanshiel/canonical/wtb_bal_align_force_seed201/best_model.pt")),
    ("Local Penmanshiel 201", Path("artifacts/external_wind_runs/penmanshiel/chronological/external_wind_bal_align_force_seed201/best_model.pt")),
    ("Transferred Kelmarsh 201", Path("artifacts/signature_gate_farms_runs_20260903/kelmarsh/canonical/wtb_bal_align_force_seed201/best_model.pt")),
    ("Local Kelmarsh 201", Path("artifacts/external_wind_runs/kelmarsh/chronological/external_wind_bal_align_force_seed201/best_model.pt")),
]

for label, p in ckpt_paths:
    print(f"=== {label} ===")
    if not p.exists():
        print(f"FILE NOT FOUND: {p}")
        continue
    ckpt = torch.load(p, map_location="cpu")
    print("Checkpoint type:", type(ckpt))
    if isinstance(ckpt, dict):
        print("Keys:", list(ckpt.keys()))
        if "model" in ckpt:
            print("Model keys count:", len(ckpt["model"]))
            sample_keys = list(ckpt["model"].keys())[:8]
            print("Sample model keys:", sample_keys)
        elif "state_dict" in ckpt:
            print("state_dict keys count:", len(ckpt["state_dict"]))
            sample_keys = list(ckpt["state_dict"].keys())[:8]
            print("Sample state_dict keys:", sample_keys)
        else:
            sample_keys = list(ckpt.keys())[:8]
            print("Sample keys:", sample_keys)
    print()
