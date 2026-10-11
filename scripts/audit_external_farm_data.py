import json
from pathlib import Path
import numpy as np

farms = [
    ("Penmanshiel", Path("artifacts/cache_signature_penmanshiel/external_wind_penmanshiel_obs_window_canonical")),
    ("Kelmarsh", Path("artifacts/cache_signature_kelmarsh/external_wind_kelmarsh_obs_window_canonical")),
]

for farm, cache_dir in farms:
    print(f"==================== Farm: {farm} ====================")
    meta_path = cache_dir / "metadata.json"
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    print("Number of Turbines:", meta.get("num_turbines"))
    print("Turbine IDs:", meta.get("turbines"))
    print("Feature count:", meta.get("num_features"))
    print("Feature names:", meta.get("feature_names"))
    splits = meta.get("split_info") or meta.get("splits")
    print("Splits info:", splits)

    feats = np.load(cache_dir / "features.npy")
    mask = np.load(cache_dir / "feature_mask.npy")
    target = np.load(cache_dir / "target.npy")
    t_mask = np.load(cache_dir / "target_mask.npy")
    time_idx = np.load(cache_dir / "time_index.npy") if (cache_dir / "time_index.npy").exists() else None

    print(f"Features shape: {feats.shape}, Mask shape: {mask.shape}")
    print(f"Target shape: {target.shape}, Target mask shape: {t_mask.shape}")
    if time_idx is not None:
        print(f"Time index shape: {time_idx.shape}, Range: [{time_idx.min()}, {time_idx.max()}]")

    # Audit missingness per channel
    feature_names = meta.get("feature_names", [f"feat_{i}" for i in range(feats.shape[-1])])
    for idx, fname in enumerate(feature_names):
        m_rate = 1.0 - float(np.mean(mask[..., idx] > 0))
        print(f"  Channel {idx:2d} ({fname:10s}) missingness: {m_rate*100:6.2f}%")

    # Hard stopping check on wind speed (channel 0)
    wspd_missing = 1.0 - float(np.mean(mask[..., 0] > 0))
    print(f"\nHard stopping check: Wind speed missingness = {wspd_missing*100:.2f}%")
    if wspd_missing > 0.20:
        print(f"HARD STOP TRIGGERED: Missing rate {wspd_missing*100:.2f}% exceeds 20% limit for {farm}!")
    else:
        print(f"HARD STOP PASSED: Missing rate {wspd_missing*100:.2f}% is <= 20% limit for {farm}.")
    print()
