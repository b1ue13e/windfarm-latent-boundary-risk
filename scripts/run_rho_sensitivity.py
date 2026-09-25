"""Decisive Economic Sensitivity with Policy Re-Optimization Script (Phase 8).

Evaluates Newsvendor optimal reserve calibration q*(rho) = 1 - 1/rho across rho in [2, 5, 10, 15, 20, 30, 40, 50, 75, 100].
Calibrates empirical quantiles on VALIDATION DATA ONLY for each method, freezes policies, and evaluates realized
economic performance (R, U, Violation, PSREI, Delta PSREI) on the 35-day test split.
Outputs: artifacts/matched_budget/reoptimized_rho_sensitivity.csv
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd

os.environ["LOKY_MAX_CPU_COUNT"] = "4"
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["OMP_NUM_THREADS"] = "4"

REPO_ROOT = Path(os.environ.get("WINDFARM_REPO_ROOT", Path(__file__).resolve().parents[1]))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from windfarm_moe.arrival_feed import DegradationSpec, UnifiedArrivalDataset
from windfarm_moe.data import load_cache_bundle

DT = 1.0 / 6.0
N_W_BINS = 10
N_PI_BINS = 5
SEEDS = [201, 202, 203, 204, 205]
RHO_GRID = [2.0, 5.0, 10.0, 15.0, 20.0, 30.0, 40.0, 50.0, 75.0, 100.0]

def main():
    out_dir = REPO_ROOT / "artifacts/matched_budget"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print("=== Starting Policy Re-Optimization rho Sensitivity Evaluation (Phase 8) ===", flush=True)
    
    bundle = load_cache_bundle(REPO_ROOT / "artifacts/cache_strictmask_trainweights/wtb_245d", mmap_mode="r")
    res_data = np.load(REPO_ROOT / "artifacts/fixed_forecast_residuals.npz")
    
    spec = DegradationSpec(delay_steps=0, withheld_channels=("Pab_mean", "Pab_std"))
    val_ds = UnifiedArrivalDataset(bundle, "val", hist_len=36, pred_len=24, degradation=spec)
    test_ds = UnifiedArrivalDataset(bundle, "test", hist_len=36, pred_len=24, degradation=spec)
    
    test_anchors = test_ds.anchor_indices
    val_anchors = val_ds.anchor_indices
    
    meta = bundle.metadata.get("feature_stats", {})
    w_stats = meta.get("Wspd", meta.get("0", {}))
    w_mean = float(w_stats.get("mean", 5.306463))
    w_std = float(w_stats.get("std", 3.425992))
    
    physics = np.asarray(bundle.physics_model, dtype=np.float32)
    wspd_test = physics[test_anchors, :, 0].reshape(-1) * w_std + w_mean
    wspd_val = physics[val_anchors, :, 0].reshape(-1) * w_std + w_mean
    
    valid_test = np.asarray(bundle.regime_primary_valid, dtype=bool)[test_anchors, :].reshape(-1)
    
    reg_mat = bundle.regime_primary[test_anchors, :]
    diff = np.diff(reg_mat, axis=0, prepend=reg_mat[:1, :]) != 0
    # Bounded non-circular temporal dilation for +/- 3 steps (no circular wrap-around)
    trans_mat = diff.copy()
    for off in range(1, 4):
        trans_mat[off:, :] |= diff[:-off, :]
        trans_mat[:-off, :] |= diff[off:, :]
    is_transition = trans_mat.reshape(-1)
    
    h_idx = 5  # h=6
    m_test = (res_data["mask_test"][:, h_idx, :].reshape(-1) > 0.5) & valid_test
    m_val = res_data["mask_val"][:, h_idx, :].reshape(-1) > 0.5
    
    mask_full = m_test
    mask_trans = m_test & is_transition
    mask_steady = m_test & (~is_transition)
    
    slices = {
        "Transition": mask_trans,
        "Steady": mask_steady,
        "Full": mask_full,
    }
    
    # Load cached probabilities
    prob_path = out_dir / "cached_posterior_probs.npz"
    assert prob_path.exists(), f"Cached probabilities not found at {prob_path}. Run run_matched_budget_frontier.py first."
    prob_data = np.load(prob_path)
    
    w_bins = np.linspace(0.0, 25.0, N_W_BINS + 1)
    w_bins[0] = -np.inf
    w_bins[-1] = np.inf
    
    reopt_rows = []
    
    for rho in RHO_GRID:
        q_star = 1.0 - 1.0 / rho
        print(f"\nEvaluating rho = {rho:.1f} (Nominal fractile q* = {q_star:.4f})", flush=True)
        
        for seed in SEEDS:
            s_v = res_data[f"shortfall_val_seed{seed}"][:, h_idx, :].reshape(-1)
            s_t = res_data[f"shortfall_test_seed{seed}"][:, h_idx, :].reshape(-1)
            p_v = prob_data[f"p_val_seed{seed}"]
            p_t = prob_data[f"p_test_seed{seed}"]
            
            # 1. Calibrate Policy B for this q_star on val
            q_glob = float(np.quantile(s_v[m_val], q_star))
            w_bin_q = []
            for b_i in range(N_W_BINS):
                in_b = m_val & (wspd_val >= w_bins[b_i]) & (wspd_val < w_bins[b_i + 1])
                if np.sum(in_b) > 20:
                    w_bin_q.append(float(np.quantile(s_v[in_b], q_star)))
                else:
                    w_bin_q.append(q_glob)
            
            r_B = np.zeros_like(s_t)
            for b_i in range(N_W_BINS):
                in_t = (wspd_test >= w_bins[b_i]) & (wspd_test < w_bins[b_i + 1])
                r_B[in_t] = w_bin_q[b_i]
                
            # 2. Calibrate Policy C for this q_star on val
            pi_bins = np.quantile(p_v[m_val], np.linspace(0, 1, N_PI_BINS + 1))
            pi_bins[0] = -np.inf
            pi_bins[-1] = np.inf
            c_bin_q = []
            for b_i in range(N_PI_BINS):
                in_b = m_val & (p_v >= pi_bins[b_i]) & (p_v < pi_bins[b_i + 1])
                if np.sum(in_b) > 20:
                    c_bin_q.append(float(np.quantile(s_v[in_b], q_star)))
                else:
                    c_bin_q.append(q_glob)
            
            r_C = np.zeros_like(s_t)
            for b_i in range(N_PI_BINS):
                in_t = (p_t >= pi_bins[b_i]) & (p_t < pi_bins[b_i + 1])
                r_C[in_t] = c_bin_q[b_i]
                
            for slice_name, s_mask in slices.items():
                r_b_sub = r_B[s_mask]
                r_c_sub = r_C[s_mask]
                s_t_sub = s_t[s_mask]
                
                u_b = np.maximum(s_t_sub - r_b_sub, 0.0)
                u_c = np.maximum(s_t_sub - r_c_sub, 0.0)
                
                R_b = float(np.sum(r_b_sub) * DT)
                R_c = float(np.sum(r_c_sub) * DT)
                U_b = float(np.sum(u_b) * DT)
                U_c = float(np.sum(u_c) * DT)
                
                V_b = float(np.mean(s_t_sub > r_b_sub) * 100.0)
                V_c = float(np.mean(s_t_sub > r_c_sub) * 100.0)
                
                C_b = float(np.sum(r_b_sub + rho * u_b) * DT)
                C_c = float(np.sum(r_c_sub + rho * u_c) * DT)
                
                delta_C = C_c - C_b
                delta_R = R_c - R_b
                delta_U = U_c - U_b
                delta_V = V_c - V_b
                
                reopt_rows.append({
                    "seed": seed,
                    "slice": slice_name,
                    "rho": rho,
                    "q_star": q_star,
                    "R_base_kwh": R_b,
                    "R_post_kwh": R_c,
                    "delta_R_kwh": delta_R,
                    "U_base_kwh": U_b,
                    "U_post_kwh": U_c,
                    "delta_U_kwh": delta_U,
                    "V_base_pct": V_b,
                    "V_post_pct": V_c,
                    "delta_V_pct": delta_V,
                    "PSREI_base_kwh": C_b,
                    "PSREI_post_kwh": C_c,
                    "delta_PSREI_kwh": delta_C,
                    "preferred_policy": "Posterior" if delta_C < 0 else "Baseline (Wspd-Bins)",
                })

    df_reopt = pd.DataFrame(reopt_rows)
    
    # Summary mean across seeds
    mean_rows = []
    for slice_name in ["Transition", "Steady", "Full"]:
        for rho in RHO_GRID:
            sub = df_reopt[(df_reopt["slice"] == slice_name) & (df_reopt["rho"] == rho)]
            mean_dict = {
                "seed": "Mean",
                "slice": slice_name,
                "rho": rho,
                "q_star": float(sub["q_star"].iloc[0]),
            }
            for col in sub.columns:
                if col not in ["seed", "slice", "rho", "q_star", "preferred_policy"]:
                    mean_dict[col] = float(sub[col].mean())
            mean_dict["preferred_policy"] = "Posterior" if mean_dict["delta_PSREI_kwh"] < 0 else "Baseline (Wspd-Bins)"
            mean_rows.append(mean_dict)
            if slice_name == "Transition":
                print(f"  [Trans Mean rho={rho:3.0f}] Delta R={mean_dict['delta_R_kwh']:+,.0f} | Delta U={mean_dict['delta_U_kwh']:+,.0f} | Delta PSREI={mean_dict['delta_PSREI_kwh']:+,.0f} kWh -> {mean_dict['preferred_policy']}", flush=True)

    df_reopt_all = pd.concat([df_reopt, pd.DataFrame(mean_rows)], ignore_index=True)
    df_reopt_all.to_csv(out_dir / "reoptimized_rho_sensitivity.csv", index=False)
    print(f"\nSaved re-optimized rho sensitivity to {out_dir / 'reoptimized_rho_sensitivity.csv'}", flush=True)

if __name__ == "__main__":
    main()
