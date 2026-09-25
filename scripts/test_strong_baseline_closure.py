"""Script to test and verify Section III and IV closure:
Posterior vs Wind-Speed-Conditioned Quantile Baseline, Deployable Hybrid Policy,
Transition vs Steady Windows, and Bootstrap Interaction.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

os.environ["LOKY_MAX_CPU_COUNT"] = "4"
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["OMP_NUM_THREADS"] = "4"

REPO_ROOT = Path(os.environ.get("WINDFARM_REPO_ROOT", Path(__file__).resolve().parents[1]))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from windfarm_moe.arrival_feed import DegradationSpec, UnifiedArrivalDataset
from windfarm_moe.data import CacheBundle, load_cache_bundle
from windfarm_moe.mechanism_intervention import _load_model_from_checkpoint

DT = 1.0 / 6.0
RHO = 10.0
Q_STAR = 0.90
N_BINS = 5
BLOCK_SIZE = 144
N_BOOT = 1000

def compute_metrics_slice(r_pred, s_target, mask, rho=RHO, dt=DT):
    r = r_pred[mask]
    s = s_target[mask]
    shortage = np.maximum(s - r, 0.0)
    cost = np.sum(r + rho * shortage) * dt
    viol_rate = float(np.mean(s > r)) if len(s) > 0 else 0.0
    tot_reserve = float(np.sum(r) * dt)
    tot_shortage = float(np.sum(shortage) * dt)
    return {
        "psrei": float(cost),
        "reserve": tot_reserve,
        "violation_pct": viol_rate * 100.0,
        "shortage": tot_shortage,
    }

def cluster_bootstrap_contrast(
    loss_c, loss_b, time_indices, mask_trans, mask_steady, n_boot=N_BOOT, seed=42
):
    """Computes paired day-level cluster bootstrap over 35 observed test days.
    loss_c: loss of Posterior (kWh)
    loss_b: loss of Wspd-Bins (kWh)
    Delta_trans = sum_{trans} (loss_c - loss_b)
    Delta_steady = sum_{steady} (loss_c - loss_b)
    Interaction = Delta_trans - Delta_steady
    """
    unique_times = np.unique(time_indices)
    n_blocks = max(1, int(np.ceil(len(unique_times) / BLOCK_SIZE)))
    time_to_block = {t: idx // BLOCK_SIZE for idx, t in enumerate(unique_times)}
    sample_block_ids = np.array([time_to_block[t] for t in time_indices], dtype=np.int64)

    # Pointwise differences
    d_point = loss_c - loss_b
    d_trans = np.where(mask_trans, d_point, 0.0)
    d_steady = np.where(mask_steady, d_point, 0.0)

    # Pre-aggregate by block
    blocks_trans = np.bincount(sample_block_ids, weights=d_trans, minlength=n_blocks)[:n_blocks]
    blocks_steady = np.bincount(sample_block_ids, weights=d_steady, minlength=n_blocks)[:n_blocks]

    rng = np.random.default_rng(seed)
    chosen_blocks = rng.integers(0, n_blocks, size=(n_boot, n_blocks))

    boot_trans = blocks_trans[chosen_blocks].sum(axis=1)
    boot_steady = blocks_steady[chosen_blocks].sum(axis=1)
    boot_inter = boot_trans - boot_steady

    def get_stats(arr):
        return {
            "mean": float(np.mean(arr)),
            "ci_low": float(np.quantile(arr, 0.025)),
            "ci_high": float(np.quantile(arr, 0.975)),
            "p_val": float(np.mean(arr >= 0.0)) if np.mean(arr) < 0 else float(np.mean(arr <= 0.0)),
        }

    return get_stats(boot_trans), get_stats(boot_steady), get_stats(boot_inter)

def main():
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    bundle = load_cache_bundle(REPO_ROOT / "artifacts/cache_strictmask_trainweights/wtb_245d", mmap_mode="r")
    res_data = np.load(REPO_ROOT / "artifacts/fixed_forecast_residuals.npz")
    seeds = [201, 202, 203, 204, 205]

    spec = DegradationSpec(delay_steps=0, withheld_channels=("Pab_mean", "Pab_std"))
    val_ds = UnifiedArrivalDataset(bundle, "val", hist_len=36, pred_len=24, degradation=spec)
    test_ds = UnifiedArrivalDataset(bundle, "test", hist_len=36, pred_len=24, degradation=spec)

    val_loader = DataLoader(val_ds, batch_size=64, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=64, shuffle=False)

    test_anchors = test_ds.anchor_indices
    val_anchors = val_ds.anchor_indices
    W = len(test_anchors)
    N = 134
    time_indices = np.repeat(test_anchors[:, None], N, axis=1).reshape(-1)

    meta = bundle.metadata.get("feature_stats", {})
    w_stats = meta.get("Wspd", meta.get("0", {}))
    w_mean = float(w_stats.get("mean", 5.306463))
    w_std = float(w_stats.get("std", 3.425992))

    physics = np.asarray(bundle.physics_model, dtype=np.float32)
    wspd_test_norm = physics[test_anchors, :, 0].reshape(-1)
    wspd_test = wspd_test_norm * w_std + w_mean

    wspd_val_norm = physics[val_anchors, :, 0].reshape(-1)
    wspd_val = wspd_val_norm * w_std + w_mean

    regime_test = np.asarray(bundle.regime_primary, dtype=np.int64)[test_anchors, :].reshape(-1)
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

    print(f"Mask counts: Full={np.sum(mask_full)}, Trans={np.sum(mask_trans)} ({np.mean(mask_trans[mask_full])*100:.2f}%), Steady={np.sum(mask_steady)} ({np.mean(mask_steady[mask_full])*100:.2f}%)")

    all_seed_results = []
    all_boot_results = []

    for seed in seeds:
        s_v = res_data[f"shortfall_val_seed{seed}"][:, h_idx, :].reshape(-1)
        s_t = res_data[f"shortfall_test_seed{seed}"][:, h_idx, :].reshape(-1)

        dense_ckpt = REPO_ROOT / f"artifacts/dense_classifier_runs_20260904/canonical/wtb_bal_align_force_seed{seed}"
        model = _load_model_from_checkpoint(dense_ckpt, bundle, device)
        model.eval()

        def get_probs(loader):
            plist = []
            with torch.no_grad():
                for b in loader:
                    _, gate_prob, _ = model(
                        b["x_hist"].to(device),
                        b["edge_index_hist"].to(device),
                        b["edge_weight_hist"].to(device),
                        b["feature_mask_hist"].to(device),
                        b["anchor_physics"].to(device),
                    )
                    p3 = gate_prob[..., :3]
                    p = (p3[..., 2] / torch.clamp(p3.sum(dim=-1), min=1e-9)).cpu().numpy()
                    plist.append(p)
            return np.concatenate(plist, axis=0).reshape(-1)

        p_v = get_probs(val_loader)
        p_t = get_probs(test_loader)

        # Policy A: Global Quantile
        q_glob = float(np.quantile(s_v[m_val], Q_STAR))
        r_A = np.full_like(s_t, q_glob)

        # Policy B: Wind-speed Binned Quantile (10 bins 0 to 25 m/s)
        w_bins = np.linspace(0.0, 25.0, 11)
        w_bins[0] = -np.inf
        w_bins[-1] = np.inf
        w_bin_q = []
        for b_i in range(10):
            in_b = m_val & (wspd_val >= w_bins[b_i]) & (wspd_val < w_bins[b_i + 1])
            if np.sum(in_b) > 20:
                w_bin_q.append(float(np.quantile(s_v[in_b], Q_STAR)))
            else:
                w_bin_q.append(q_glob)
        r_B = np.zeros_like(s_t)
        for b_i in range(10):
            in_t = (wspd_test >= w_bins[b_i]) & (wspd_test < w_bins[b_i + 1])
            r_B[in_t] = w_bin_q[b_i]

        # Policy C: Posterior-Conditioned Quantile (5 quintiles of p_v)
        pi_bins = np.quantile(p_v[m_val], np.linspace(0, 1, N_BINS + 1))
        pi_bins[0] = -np.inf
        pi_bins[-1] = np.inf
        c_bin_q = []
        for b_i in range(N_BINS):
            in_b = m_val & (p_v >= pi_bins[b_i]) & (p_v < pi_bins[b_i + 1])
            if np.sum(in_b) > 20:
                c_bin_q.append(float(np.quantile(s_v[in_b], Q_STAR)))
            else:
                c_bin_q.append(q_glob)
        r_C = np.zeros_like(s_t)
        for b_i in range(N_BINS):
            in_t = (p_t >= pi_bins[b_i]) & (p_t < pi_bins[b_i + 1])
            r_C[in_t] = c_bin_q[b_i]

        # Policy D: Deployable Hybrid Policy
        # Validation evaluation of candidate rules:
        # Candidate 1: Wind-speed boundary band |wspd - 10.5| <= delta
        # Candidate 2: Posterior threshold p_t in [0.1, 0.9] or p_t >= tau
        # Candidate 3: Posterior entropy
        # Let's compute r_B_val and r_C_val to evaluate rules on validation set!
        r_B_val = np.zeros_like(s_v)
        for b_i in range(10):
            in_v = (wspd_val >= w_bins[b_i]) & (wspd_val < w_bins[b_i + 1])
            r_B_val[in_v] = w_bin_q[b_i]

        r_C_val = np.zeros_like(s_v)
        for b_i in range(N_BINS):
            in_v = (p_v >= pi_bins[b_i]) & (p_v < pi_bins[b_i + 1])
            r_C_val[in_v] = c_bin_q[b_i]

        loss_B_val = (r_B_val + RHO * np.maximum(s_v - r_B_val, 0.0)) * DT
        loss_C_val = (r_C_val + RHO * np.maximum(s_v - r_C_val, 0.0)) * DT

        # Test candidate rules on val:
        best_rule = None
        best_val_loss = np.sum(loss_B_val[m_val])
        print(f"Seed {seed} Val Loss Wspd: {best_val_loss:,.0f}, Val Loss Post: {np.sum(loss_C_val[m_val]):,.0f}")

        # Sweep wind speed bands
        candidates = []
        for delta in [0.5, 1.0, 1.5, 2.0]:
            cond_val = np.abs(wspd_val - 10.5) <= delta
            r_hyb_val = np.where(cond_val, r_C_val, r_B_val)
            val_loss = np.sum((r_hyb_val + RHO * np.maximum(s_v - r_hyb_val, 0.0))[m_val]) * DT
            candidates.append((f"wspd_band_{delta}", cond_val, val_loss, delta))

        for tau in [0.05, 0.1, 0.2, 0.5]:
            cond_val = p_v >= tau
            r_hyb_val = np.where(cond_val, r_C_val, r_B_val)
            val_loss = np.sum((r_hyb_val + RHO * np.maximum(s_v - r_hyb_val, 0.0))[m_val]) * DT
            candidates.append((f"post_ge_{tau}", cond_val, val_loss, tau))

        for tau_low, tau_high in [(0.1, 0.9), (0.2, 0.8), (0.05, 0.95)]:
            cond_val = (p_v >= tau_low) & (p_v <= tau_high)
            r_hyb_val = np.where(cond_val, r_C_val, r_B_val)
            val_loss = np.sum((r_hyb_val + RHO * np.maximum(s_v - r_hyb_val, 0.0))[m_val]) * DT
            candidates.append((f"post_band_{tau_low}_{tau_high}", cond_val, val_loss, (tau_low, tau_high)))

        for name, _, v_loss, param in candidates:
            print(f"  Candidate {name}: Val Loss = {v_loss:,.0f} (diff vs Wspd: {v_loss - best_val_loss:+,.0f})")

        # Select the candidate that minimized val loss
        best_cand = min(candidates, key=lambda x: x[2])
        best_name = best_cand[0]
        print(f"  Best Val Rule: {best_name} with Val Loss = {best_cand[2]:,.0f}")

        # Construct Policy D on test using the frozen best rule
        if "wspd_band" in best_name:
            delta = best_cand[3]
            cond_test = np.abs(wspd_test - 10.5) <= delta
        elif "post_ge" in best_name:
            tau = best_cand[3]
            cond_test = p_t >= tau
        elif "post_band" in best_name:
            t_l, t_h = best_cand[3]
            cond_test = (p_t >= t_l) & (p_t <= t_h)
        r_D = np.where(cond_test, r_C, r_B)

        # Also let's construct r_D_band10 (|v - 10.5| <= 1.0) as canonical pre-specified deployable rule
        cond_test_band10 = np.abs(wspd_test - 10.5) <= 1.0
        r_D_band10 = np.where(cond_test_band10, r_C, r_B)

        # Compute pointwise losses (kWh)
        loss_A = (r_A + RHO * np.maximum(s_t - r_A, 0.0)) * DT
        loss_B = (r_B + RHO * np.maximum(s_t - r_B, 0.0)) * DT
        loss_C = (r_C + RHO * np.maximum(s_t - r_C, 0.0)) * DT
        loss_D = (r_D + RHO * np.maximum(s_t - r_D, 0.0)) * DT
        loss_D_band10 = (r_D_band10 + RHO * np.maximum(s_t - r_D_band10, 0.0)) * DT

        # Compute metrics across populations:
        for pop_name, p_mask in [("Full", mask_full), ("Transition", mask_trans), ("Steady", mask_steady)]:
            mA = compute_metrics_slice(r_A, s_t, p_mask)
            mB = compute_metrics_slice(r_B, s_t, p_mask)
            mC = compute_metrics_slice(r_C, s_t, p_mask)
            mD = compute_metrics_slice(r_D, s_t, p_mask)
            mD10 = compute_metrics_slice(r_D_band10, s_t, p_mask)

            all_seed_results.append({
                "seed": seed,
                "population": pop_name,
                "A_psrei": mA["psrei"], "A_res": mA["reserve"], "A_viol": mA["violation_pct"], "A_short": mA["shortage"],
                "B_psrei": mB["psrei"], "B_res": mB["reserve"], "B_viol": mB["violation_pct"], "B_short": mB["shortage"],
                "C_psrei": mC["psrei"], "C_res": mC["reserve"], "C_viol": mC["violation_pct"], "C_short": mC["shortage"],
                "D_psrei": mD["psrei"], "D_res": mD["reserve"], "D_viol": mD["violation_pct"], "D_short": mD["shortage"],
                "D10_psrei": mD10["psrei"], "D10_res": mD10["reserve"], "D10_viol": mD10["violation_pct"], "D10_short": mD10["shortage"],
                "best_rule": best_name,
            })

        # Run day-level cluster bootstrap contrast for this seed
        boot_trans, boot_steady, boot_inter = cluster_bootstrap_contrast(
            loss_C, loss_B, time_indices, mask_trans, mask_steady, n_boot=N_BOOT, seed=seed
        )
        print(f"Seed {seed} Bootstrap Contrasts (L_C - L_B in kWh):", flush=True)
        print(f"  Delta_trans:  {boot_trans['mean']:+,.0f} [{boot_trans['ci_low']:+,.0f}, {boot_trans['ci_high']:+,.0f}] (p={boot_trans['p_val']:.4f})", flush=True)
        print(f"  Delta_steady: {boot_steady['mean']:+,.0f} [{boot_steady['ci_low']:+,.0f}, {boot_steady['ci_high']:+,.0f}] (p={boot_steady['p_val']:.4f})", flush=True)
        print(f"  Interaction (trans - steady): {boot_inter['mean']:+,.0f} [{boot_inter['ci_low']:+,.0f}, {boot_inter['ci_high']:+,.0f}] (p={boot_inter['p_val']:.4f})", flush=True)

        all_boot_results.append({
            "seed": seed,
            "delta_trans_mean": boot_trans["mean"],
            "delta_trans_ci_low": boot_trans["ci_low"],
            "delta_trans_ci_high": boot_trans["ci_high"],
            "delta_trans_pval": boot_trans["p_val"],
            "delta_steady_mean": boot_steady["mean"],
            "delta_steady_ci_low": boot_steady["ci_low"],
            "delta_steady_ci_high": boot_steady["ci_high"],
            "delta_steady_pval": boot_steady["p_val"],
            "interaction_mean": boot_inter["mean"],
            "interaction_ci_low": boot_inter["ci_low"],
            "interaction_ci_high": boot_inter["ci_high"],
            "interaction_pval": boot_inter["p_val"],
        })

    # Add mean summary row for bootstrap
    mean_boot = {
        "seed": "Mean",
        "delta_trans_mean": float(np.mean([r["delta_trans_mean"] for r in all_boot_results])),
        "delta_trans_ci_low": float(np.mean([r["delta_trans_ci_low"] for r in all_boot_results])),
        "delta_trans_ci_high": float(np.mean([r["delta_trans_ci_high"] for r in all_boot_results])),
        "delta_trans_pval": float(np.mean([r["delta_trans_pval"] for r in all_boot_results])),
        "delta_steady_mean": float(np.mean([r["delta_steady_mean"] for r in all_boot_results])),
        "delta_steady_ci_low": float(np.mean([r["delta_steady_ci_low"] for r in all_boot_results])),
        "delta_steady_ci_high": float(np.mean([r["delta_steady_ci_high"] for r in all_boot_results])),
        "delta_steady_pval": float(np.mean([r["delta_steady_pval"] for r in all_boot_results])),
        "interaction_mean": float(np.mean([r["interaction_mean"] for r in all_boot_results])),
        "interaction_ci_low": float(np.mean([r["interaction_ci_low"] for r in all_boot_results])),
        "interaction_ci_high": float(np.mean([r["interaction_ci_high"] for r in all_boot_results])),
        "interaction_pval": float(np.mean([r["interaction_pval"] for r in all_boot_results])),
    }
    all_boot_results.append(mean_boot)

    df_res = pd.DataFrame(all_seed_results)
    df_boot = pd.DataFrame(all_boot_results)
    out_dir = REPO_ROOT / "artifacts"
    out_dir.mkdir(exist_ok=True)
    df_boot.to_csv(out_dir / "strong_baseline_bootstrap_contrasts.csv", index=False)

    policy_meta = [
        ("A", "Policy_A", "Global Residual Quantile"),
        ("B", "Policy_B", "Wind-Speed Binned Quantile"),
        ("C", "Policy_C", "Posterior-Conditioned Quantile"),
        ("D", "Policy_D", "Validation-Frozen Deployable Hybrid"),
        ("D10", "Policy_D10", "Pre-Specified Boundary Band Hybrid"),
    ]

    summary_rows = []
    print("\n================== 5-SEED SUMMARY TABLE ==================", flush=True)
    for pop in ["Full", "Transition", "Steady"]:
        sub = df_res[df_res["population"] == pop]
        b_mean = float(sub["B_psrei"].mean())
        print(f"\n--- Population: {pop} ---", flush=True)
        for p_key, pol_id, pol_name in policy_meta:
            psrei_mean = float(sub[f"{p_key}_psrei"].mean())
            psrei_std = float(sub[f"{p_key}_psrei"].std())
            res_mean = float(sub[f"{p_key}_res"].mean())
            viol_mean = float(sub[f"{p_key}_viol"].mean())
            short_mean = float(sub[f"{p_key}_short"].mean())
            delta = psrei_mean - b_mean
            delta_str = "0" if p_key == "B" else f"{delta:+,.0f}"

            summary_rows.append({
                "population": pop,
                "policy_id": pol_id,
                "policy_name": pol_name,
                "psrei_mean_kwh": round(psrei_mean),
                "psrei_std_kwh": round(psrei_std),
                "reserve_mean_kwh": round(res_mean),
                "violation_rate_pct": round(viol_mean, 2),
                "shortage_mean_kwh": round(short_mean),
                "delta_vs_wspd_kwh": delta_str,
            })
            print(f"Policy {p_key} ({pol_id}): PSREI={psrei_mean:,.0f} +- {psrei_std:,.0f} kWh | Res={res_mean:,.0f} | Viol={viol_mean:.2f}% | Short={short_mean:,.0f} kWh | Delta={delta_str}", flush=True)

    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_csv(out_dir / "strong_baseline_closure_summary.csv", index=False)
    print(f"\nSuccessfully wrote summary to {out_dir / 'strong_baseline_closure_summary.csv'}", flush=True)
    print(f"Successfully wrote bootstrap contrasts to {out_dir / 'strong_baseline_bootstrap_contrasts.csv'}", flush=True)

if __name__ == "__main__":
    main()

