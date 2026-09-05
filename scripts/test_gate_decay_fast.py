import sys
from pathlib import Path
import json, time
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
from scipy.stats import wasserstein_distance

from windfarm_moe.config import ModelConfig
from windfarm_moe.data import load_cache_bundle
from windfarm_moe.model import RegimeAwareForecaster
from windfarm_moe.utils import to_device
from scripts.remote_iec_density_multiyear_eval import WindowedDataset, run_inference_on_slice

def evaluate_gate_decay(farm="kelmarsh", seed=201, gpu_id=0):
    repo = Path("/root/paper3_audit_rerun_20260830")
    device = torch.device(f"cuda:{gpu_id}")
    
    if farm == "kelmarsh":
        cache_dir = repo / "artifacts/cache_external_wind/external_wind_kelmarsh_chronological"
        model_root = repo / "artifacts/signature_gate_farms_runs_20260903/kelmarsh/canonical"
        steps_per_year = 52560
        years = 9
    else:
        cache_dir = repo / "artifacts/cache_external_wind/external_wind_penmanshiel_chronological"
        model_root = repo / "artifacts/signature_gate_farms_runs_20260903/penmanshiel/canonical"
        steps_per_year = 52560
        years = 9

    print(f"Loading {farm} cache...")
    bundle = load_cache_bundle(cache_dir)
    num_steps = bundle.features.shape[0]
    num_turbines = bundle.features.shape[1]
    
    ckpt_path = model_root / f"wtb_bal_align_force_seed{seed}" / "best_model.pt"
    ckpt = torch.load(ckpt_path, map_location="cpu")
    mcfg = ModelConfig(**ckpt["model_config"])
    model = RegimeAwareForecaster(
        feature_dim=bundle.features.shape[-1],
        pred_len=24,
        mode="moe_full_no_aux",
        config=mcfg,
    ).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    print(f"Running inference on all {num_steps} steps...")
    t0 = time.time()
    inf = run_inference_on_slice(model, bundle, 0, num_steps, device, batch_size=512)
    print(f"Inference done in {time.time() - t0:.2f}s")

    gates = inf["gate"] # shape (N_anchors, N_turbines, 4)
    anchors = inf["anchor_idx"]
    anchor_to_local = {a: i for i, a in enumerate(anchors)}

    regime_primary = bundle.regime_primary
    regime_valid = bundle.regime_valid > 0.5

    # Group by year
    year_data = []
    for y in range(years):
        t_start = y * steps_per_year
        t_end = min((y + 1) * steps_per_year, num_steps)
        step_indices = [anchor_to_local[s] for s in range(t_start, t_end) if s in anchor_to_local]
        if not step_indices:
            continue
        g_y = gates[step_indices] # (T_y, N_turbines, 4)
        anc_y = anchors[step_indices]
        
        # Ground truth regimes for these anchors
        reg_y = regime_primary[anc_y]
        val_y = regime_valid[anc_y]
        
        p_pitch_y = g_y[..., 2].flatten()
        pred_reg_y = np.argmax(g_y, axis=-1).flatten()
        true_reg_y = reg_y.flatten()
        valid_mask_y = val_y.flatten()
        
        # Filter valid
        sel = valid_mask_y & (true_reg_y >= 0)
        nmi_gt = normalized_mutual_info_score(true_reg_y[sel], pred_reg_y[sel])
        ari_gt = adjusted_rand_score(true_reg_y[sel], pred_reg_y[sel])
        
        year_data.append({
            "year": y + 1,
            "calendar_year": 2016 + y,
            "nmi_gt": nmi_gt,
            "ari_gt": ari_gt,
            "p_pitch": p_pitch_y,
            "pred_reg": pred_reg_y,
        })
        print(f"Year {y+1} ({2016+y}): NMI={nmi_gt:.4f}, ARI={ari_gt:.4f}")

    # Relative to Year 1 (baseline)
    base_p_pitch = year_data[0]["p_pitch"]
    base_nmi = year_data[0]["nmi_gt"]
    results = []
    for yd in year_data:
        w_dist = wasserstein_distance(yd["p_pitch"], base_p_pitch)
        inv_w = 1.0 / (1.0 + w_dist)
        rel_nmi = yd["nmi_gt"] / base_nmi
        results.append({
            "farm": farm,
            "seed": seed,
            "year": yd["year"],
            "calendar_year": yd["calendar_year"],
            "nmi_ground_truth": yd["nmi_gt"],
            "relative_nmi": rel_nmi,
            "wasserstein_dist": w_dist,
            "inverse_wasserstein": inv_w,
            "ari_ground_truth": yd["ari_gt"],
        })
        print(f"Year {yd['year']} ({yd['calendar_year']}): Rel-NMI={rel_nmi:.4f}, W1={w_dist:.4f}, Inv-W={inv_w:.4f}")

    return results

if __name__ == "__main__":
    res_km = evaluate_gate_decay("kelmarsh", 201, 0)
    res_pm = evaluate_gate_decay("penmanshiel", 201, 0)
