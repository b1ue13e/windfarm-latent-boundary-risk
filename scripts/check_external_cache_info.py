import json
from pathlib import Path
import numpy as np

def inspect_cache(cache_dir: Path, name: str):
    print(f"\n{'='*20} Inspecting {name} {'='*20}")
    print(f"Path: {cache_dir}")
    meta_path = cache_dir / "metadata.json"
    if not meta_path.exists():
        print("metadata.json not found!")
        return
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    print("Metadata keys:", list(meta.keys()))
    if "feature_names" in meta:
        print("Feature names:", meta["feature_names"])
    if "num_nodes" in meta:
        print("Num nodes:", meta["num_nodes"])
    if "split" in meta or "splits" in meta:
        print("Splits:", meta.get("split", meta.get("splits")))
    if "turbines" in meta:
        print("Turbines count:", len(meta["turbines"]))
        
    features = np.load(cache_dir / "features.npy", mmap_mode="r")
    f_mask = np.load(cache_dir / "feature_mask.npy", mmap_mode="r")
    target = np.load(cache_dir / "target.npy", mmap_mode="r")
    t_mask = np.load(cache_dir / "target_mask.npy", mmap_mode="r")
    time_idx = np.load(cache_dir / "time_index.npy", mmap_mode="r")
    
    print(f"Features shape: {features.shape}, dtype: {features.dtype}")
    print(f"Feature mask shape: {f_mask.shape}, dtype: {f_mask.dtype}")
    print(f"Target shape: {target.shape}, dtype: {target.dtype}")
    print(f"Time index shape: {time_idx.shape}, dtype: {time_idx.dtype}")

    # Inspect missingness on test split if known
    # Check feature index for wind speed
    feat_names = meta.get("feature_names", [])
    wspd_idx = None
    for idx, fn in enumerate(feat_names):
        if "wspd" in fn.lower() or "speed" in fn.lower():
            wspd_idx = idx
            break
    print(f"Detected wspd feature index: {wspd_idx} ({feat_names[wspd_idx] if wspd_idx is not None else 'None'})")

    splits = meta.get("split", meta.get("splits", {}))
    test_slice = None
    if "test" in splits:
        t_info = splits["test"]
        if isinstance(t_info, list) and len(t_info) == 2:
            test_slice = slice(t_info[0], t_info[1])
        elif isinstance(t_info, dict) and "start" in t_info and "end" in t_info:
            test_slice = slice(t_info["start"], t_info["end"])
    print(f"Test slice: {test_slice}")

    if test_slice is not None and wspd_idx is not None:
        test_wspd_mask = f_mask[test_slice, :, wspd_idx]
        # Valid is usually 1, missing is 0 (or vice versa? let's check unique values)
        vals, counts = np.unique(test_wspd_mask, return_counts=True)
        print("Test wspd mask distribution:", dict(zip(vals.tolist(), counts.tolist())))
        # Missing rate
        total = test_wspd_mask.size
        # Assuming 1 is valid, 0 is missing:
        valid_cnt = np.sum(test_wspd_mask > 0)
        missing_rate = (total - valid_cnt) / total
        print(f"Test wind speed missing rate: {missing_rate:.4%} (Valid: {valid_cnt}/{total})")
        if missing_rate > 0.20:
            print(">>> WARNING: MISSING RATE EXCEEDS 20% HARD STOP CRITERION! <<<")
        else:
            print(">>> PASS: Missing rate <= 20% hard stop threshold. <<<")

inspect_cache(Path("artifacts/cache_signature_penmanshiel/external_wind_penmanshiel_obs_window_canonical"), "Penmanshiel")
inspect_cache(Path("artifacts/cache_signature_kelmarsh/external_wind_kelmarsh_obs_window_canonical"), "Kelmarsh")
