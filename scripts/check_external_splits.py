from pathlib import Path
import json
import numpy as np

# Check splits in metadata or scripts
for farm, cache_dir in [
    ("Penmanshiel", Path("artifacts/cache_signature_penmanshiel/external_wind_penmanshiel_obs_window_canonical")),
    ("Kelmarsh", Path("artifacts/cache_signature_kelmarsh/external_wind_kelmarsh_obs_window_canonical")),
]:
    print(f"=== Split check for {farm} ===")
    meta = json.loads((cache_dir / "metadata.json").read_text(encoding="utf-8"))
    print("Keys in metadata:", list(meta.keys()))
    if "split" in meta:
        print("split:", meta["split"])
    if "data_split" in meta:
        print("data_split:", meta["data_split"])
    if "train_slice" in meta:
        print("train_slice:", meta["train_slice"])

# Check existing benchmark directories or scripts to see how splits were chosen
print("\n=== Checking existing run folders ===")
for p in [
    Path("artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h1"),
    Path("artifacts/signature_gate_farms_runs_20260903/penmanshiel"),
    Path("artifacts/signature_gate_farms_runs_20260903/kelmarsh"),
    Path("artifacts/external_wind_runs/penmanshiel/chronological"),
    Path("artifacts/external_wind_runs/kelmarsh/chronological"),
]:
    if p.exists():
        subdirs = [x.name for x in p.iterdir() if x.is_dir()][:5]
        files = [x.name for x in p.iterdir() if x.is_file()][:5]
        print(f"{p}: subdirs={subdirs}, files={files}")
    else:
        print(f"{p} DOES NOT EXIST")
