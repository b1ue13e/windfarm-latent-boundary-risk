"""Build and Freeze Fixed Forecast Residuals across 5 seeds and 6 horizons.

Phase 3 Contract:
- Freezes canonical point forecast yhat_fixed_t from the clean-trained STGNN model across seeds 201-205.
- Computes identical shortfall residuals: s_{t, h} = max(yhat_fixed_{t, h} - y_{t, h}, 0)
- Preserves all horizons h in [1, 2, 3, 4, 5, 6] (leads 0 to 5).
- Saves frozen tensors into artifacts/fixed_forecast_residuals.npz and metadata JSON.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
from torch.utils.data import DataLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from windfarm_moe.data import CacheBundle, RegimeWindowDataset, load_cache_bundle
from windfarm_moe.mechanism_intervention import _load_model_from_checkpoint


def main():
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"[Fixed Target Isolation] Using device: {device}")

    cache_path = Path("artifacts/cache_strictmask_trainweights/wtb_245d")
    bundle = load_cache_bundle(cache_path, mmap_mode="r")
    seeds = [201, 202, 203, 204, 205]
    horizons = [0, 1, 2, 3, 4, 5]  # h = 1 to 6 (10m to 60m)

    val_ds = RegimeWindowDataset(bundle, "val", hist_len=36, pred_len=24)
    test_ds = RegimeWindowDataset(bundle, "test", hist_len=36, pred_len=24)

    val_loader = DataLoader(val_ds, batch_size=64, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=64, shuffle=False, num_workers=0)

    print(f"Validation windows: {len(val_ds)}, Test windows: {len(test_ds)}, Turbines: 134")

    # Storage dicts
    out_arrays: Dict[str, np.ndarray] = {}
    metrics_summary: List[Dict[str, object]] = []

    for seed in seeds:
        ckpt_path = Path(f"artifacts/trainweight_full_rerun_20260830/wtb_full_seed{seed}")
        print(f"\n--- Loading Seed {seed} from {ckpt_path} ---")
        model = _load_model_from_checkpoint(ckpt_path, bundle, device)
        model.eval()

        for split_name, loader in [("val", val_loader), ("test", test_loader)]:
            yhat_list, ytrue_list, mask_list = [], [], []
            anchor_idx_list, z_label_list = [], []

            t0 = time.time()
            with torch.no_grad():
                for batch in loader:
                    x_hist = batch["x_hist"].to(device)
                    edge_index = batch["edge_index_hist"].to(device)
                    edge_weight = batch["edge_weight_hist"].to(device)
                    feature_mask = batch["feature_mask_hist"].to(device)
                    anchor_phys = batch["anchor_physics"].to(device)
                    target = batch["target"].numpy()  # (B, 24, N)
                    target_mask = batch["target_mask"].numpy()  # (B, 24, N)
                    anchor_idx = batch["anchor_index"].numpy()
                    z_label = batch["regime_primary"].numpy()  # (B, N)
                    z_valid = batch["regime_primary_valid"].numpy()

                    pred, _, aux = model(x_hist, edge_index, edge_weight, feature_mask, anchor_phys)
                    pred_np = pred[:, :6, :].cpu().numpy()  # Extract h=1..6 (B, 6, N)
                    target_np = target[:, :6, :]
                    mask_np = target_mask[:, :6, :]

                    yhat_list.append(pred_np)
                    ytrue_list.append(target_np)
                    mask_list.append(mask_np)
                    anchor_idx_list.append(anchor_idx)
                    z_label_list.append(z_label)

            yhat_arr = np.concatenate(yhat_list, axis=0)      # (T_split, 6, 134)
            ytrue_arr = np.concatenate(ytrue_list, axis=0)    # (T_split, 6, 134)
            mask_arr = np.concatenate(mask_list, axis=0)      # (T_split, 6, 134)
            anchor_arr = np.concatenate(anchor_idx_list, axis=0)
            z_arr = np.concatenate(z_label_list, axis=0)      # (T_split, 134)

            # Shortfall residual s = max(yhat - ytrue, 0) masked
            shortfall_arr = np.maximum(yhat_arr - ytrue_arr, 0.0) * mask_arr

            # Store in output dict
            out_arrays[f"yhat_{split_name}_seed{seed}"] = yhat_arr
            out_arrays[f"shortfall_{split_name}_seed{seed}"] = shortfall_arr

            if f"ytrue_{split_name}" not in out_arrays:
                out_arrays[f"ytrue_{split_name}"] = ytrue_arr
                out_arrays[f"mask_{split_name}"] = mask_arr
                out_arrays[f"anchor_indices_{split_name}"] = anchor_arr
                out_arrays[f"z_label_{split_name}"] = z_arr

            # Metrics per horizon
            for h_idx in range(6):
                h_step = h_idx + 1
                valid_mask = mask_arr[:, h_idx, :] > 0.5
                y_p = yhat_arr[:, h_idx, :][valid_mask]
                y_t = ytrue_arr[:, h_idx, :][valid_mask]
                rmse = float(np.sqrt(np.mean((y_p - y_t) ** 2)))
                mae = float(np.mean(np.abs(y_p - y_t)))
                mean_shortfall = float(np.mean(shortfall_arr[:, h_idx, :][valid_mask]))

                metrics_summary.append({
                    "seed": seed,
                    "split": split_name,
                    "horizon_step": h_step,
                    "horizon_minutes": h_step * 10,
                    "rmse": rmse,
                    "mae": mae,
                    "mean_shortfall_kw": mean_shortfall,
                })

            print(f"[{split_name.upper()} Seed {seed}] Processed {len(yhat_arr)} windows in {time.time()-t0:.2f}s. "
                  f"h=1 RMSE: {metrics_summary[-6]['rmse']:.2f}, h=6 RMSE: {metrics_summary[-1]['rmse']:.2f}")

    out_file = Path("artifacts/fixed_forecast_residuals.npz")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_file, **out_arrays)
    print(f"\n[Saved] Compressed residuals to {out_file} (Size: {out_file.stat().st_size / (1024*1024):.2f} MB)")

    meta_file = Path("artifacts/fixed_forecast_residuals_meta.json")
    meta = {
        "seeds": seeds,
        "horizons_steps": [1, 2, 3, 4, 5, 6],
        "horizons_minutes": [10, 20, 30, 40, 50, 60],
        "turbines": 134,
        "val_windows": len(val_ds),
        "test_windows": len(test_ds),
        "metrics": metrics_summary,
    }
    meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[Saved] Metadata to {meta_file}")


if __name__ == "__main__":
    main()
