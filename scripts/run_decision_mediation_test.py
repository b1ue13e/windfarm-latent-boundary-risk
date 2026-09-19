"""Decision-Value Mediation Test (Phase 8).

Tests whether reserve cost reductions from latent-boundary conditioning are mechanistically
concentrated in boundary-critical operating regimes:
1. Wind Speed Proximity to Rated: |v - 10.5| <= 1.0 m/s (boundary) vs |v - 10.5| > 2.5 m/s (far-field)
2. True Operating Regime: Z=2 (Pitch) vs Z=1 (MPPT)
3. Dynamic Transitions: within +-3 time steps of boundary entry/exit vs stationary periods
4. Posterior Confidence Bins: pi_t in [0, 0.2), [0.2, 0.8), [0.8, 1.0]

Applies paired daily cluster bootstrap over 35 observed test days (144 steps/cluster, 1,000 paired Monte Carlo resamples)
with paired 95% CIs and paired tests across 5 seeds.

Outputs:
- artifacts/mediation_analysis.csv
- docs/DECISION_VALUE_MEDIATION.md
"""
from __future__ import annotations

import argparse
import os
import sys

os.environ["LOKY_MAX_CPU_COUNT"] = "4"
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["OMP_NUM_THREADS"] = "4"

from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
import torch
from torch.utils.data import DataLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from windfarm_moe.arrival_feed import DegradationSpec, UnifiedArrivalDataset
from windfarm_moe.data import CacheBundle, load_cache_bundle
from windfarm_moe.mechanism_intervention import _load_model_from_checkpoint

DT = 1.0 / 6.0
RHO = 10.0
Q_STAR = 1.0 - 1.0 / RHO  # 0.90
N_BINS = 5
BLOCK_SIZE = 144  # 24 hours at 10-min resolution
N_BOOT = 1000


def block_bootstrap_diff(
    loss_direct: np.ndarray,
    loss_boundary: np.ndarray,
    time_indices: np.ndarray,
    slice_mask: np.ndarray,
    n_boot: int = N_BOOT,
    seed: int = 42,
) -> Tuple[float, float, float, float]:
    """Vectorized paired daily cluster bootstrap (35 observed days, 144 steps/cluster) for paired difference d = loss_direct - loss_boundary."""
    valid_slice = slice_mask & np.isfinite(loss_direct) & np.isfinite(loss_boundary)
    if np.sum(valid_slice) < 50:
        return 0.0, 0.0, 0.0, 1.0

    unique_times = np.unique(time_indices)
    n_blocks = max(1, int(np.ceil(len(unique_times) / BLOCK_SIZE)))
    time_to_block = {t: idx // BLOCK_SIZE for idx, t in enumerate(unique_times)}
    sample_block_ids = np.array([time_to_block[t] for t in time_indices], dtype=np.int64)

    # Paired difference d_t = loss_direct - loss_boundary
    d = np.where(valid_slice, loss_direct - loss_boundary, 0.0)
    # Pre-aggregate by block
    block_sums = np.bincount(sample_block_ids, weights=d, minlength=n_blocks)[:n_blocks]

    rng = np.random.default_rng(seed)
    chosen_blocks = rng.integers(0, n_blocks, size=(n_boot, n_blocks))
    boot_totals = block_sums[chosen_blocks].sum(axis=1)

    mean_diff = float(np.mean(boot_totals))
    ci_lower = float(np.quantile(boot_totals, 0.025))
    ci_upper = float(np.quantile(boot_totals, 0.975))
    p_val = float(np.mean(boot_totals <= 0.0))
    return mean_diff, ci_lower, ci_upper, p_val


def main():
    parser = argparse.ArgumentParser(description="Decision-Value Mediation Test (Phase 8)")
    parser.add_argument("--cache-dir", default="artifacts/cache_strictmask_trainweights/wtb_245d")
    parser.add_argument("--residuals-file", default="artifacts/fixed_forecast_residuals.npz")
    parser.add_argument("--output-csv", default="artifacts/mediation_analysis.csv")
    parser.add_argument("--device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--seeds", default="201,202,203,204,205")
    args = parser.parse_args()

    device = torch.device(args.device)
    print(f"[Mediation Test] Loading cache from {args.cache_dir}", flush=True)
    bundle = load_cache_bundle(Path(args.cache_dir), mmap_mode="r")

    print(f"[Mediation Test] Loading fixed residuals from {args.residuals_file}", flush=True)
    res_data = np.load(args.residuals_file)
    seeds = [int(s.strip()) for s in args.seeds.split(",")]

    # Evaluate under Pitch-Withheld (the primary operational question)
    spec = DegradationSpec(delay_steps=0, withheld_channels=("Pab_mean", "Pab_std"))
    val_ds = UnifiedArrivalDataset(bundle, "val", hist_len=36, pred_len=24, degradation=spec)
    test_ds = UnifiedArrivalDataset(bundle, "test", hist_len=36, pred_len=24, degradation=spec)

    val_loader = DataLoader(val_ds, batch_size=64, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=64, shuffle=False)

    out_csv = Path(args.output_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    # Extract wind speed and anchor time indices for test set
    test_anchors = test_ds.anchor_indices  # (W,)
    W = len(test_anchors)
    N = 134
    time_indices = np.repeat(test_anchors[:, None], N, axis=1).reshape(-1)

    # Extract clean wind speed from physics and un-normalize to physical m/s
    meta = bundle.metadata.get("feature_stats", {})
    w_stats = meta.get("Wspd", meta.get("0", {}))
    w_mean = float(w_stats.get("mean", 5.306463))
    w_std = float(w_stats.get("std", 3.425992))

    physics = np.asarray(bundle.physics_model, dtype=np.float32)
    wspd_test_norm = physics[test_anchors, :, 0].reshape(-1)
    wspd_test = wspd_test_norm * w_std + w_mean

    # True regimes on test
    regime_test = np.asarray(bundle.regime_primary, dtype=np.int64)[test_anchors, :].reshape(-1)
    valid_test = np.asarray(bundle.regime_primary_valid, dtype=bool)[test_anchors, :].reshape(-1)

    # Identify transition windows (+-3 steps of regime change)
    reg_mat = bundle.regime_primary[test_anchors, :]  # (W, N)
    diff = np.diff(reg_mat, axis=0, prepend=reg_mat[:1, :]) != 0
    trans_mat = np.zeros_like(reg_mat, dtype=bool)
    for off in range(-3, 4):
        trans_mat |= np.roll(diff, off, axis=0)
    is_transition = trans_mat.reshape(-1)

    # Horizon to evaluate: h=6 (60 min) where wake and boundary decisions are critical
    h_idx = 5  # h=6
    m_test_base = (res_data["mask_test"][:, h_idx, :].reshape(-1) > 0.5) & valid_test
    m_val = res_data["mask_val"][:, h_idx, :].reshape(-1) > 0.5

    # Define Mediation Slices
    slices = {
        "01_All_Observations": m_test_base,
        "02_Boundary_Band_Wind_9.5_to_11.5ms": m_test_base & (np.abs(wspd_test - 10.5) <= 1.0),
        "03_FarField_Wind_Outside_8.0_to_13.0ms": m_test_base & (np.abs(wspd_test - 10.5) > 2.5),
        "04_True_Regime_Pitch_Z2": m_test_base & (regime_test == 2),
        "05_True_Regime_MPPT_Z1": m_test_base & (regime_test == 1),
        "06_Dynamic_Transition_Windows": m_test_base & is_transition,
        "07_Stationary_Steady_Regime": m_test_base & (~is_transition),
    }

    results = []

    for seed in seeds:
        print(f"\n--- Evaluating Seed {seed} ---", flush=True)
        s_v = res_data[f"shortfall_val_seed{seed}"][:, h_idx, :].reshape(-1)
        s_t = res_data[f"shortfall_test_seed{seed}"][:, h_idx, :].reshape(-1)

        # Load Dense GNN model (the validated state-boundary representation)
        dense_ckpt = Path(f"artifacts/dense_classifier_runs_20260904/canonical/wtb_bal_align_force_seed{seed}")
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

        # 1. Boundary-Conditioned Reserve Policy (Variant I / STGQ-Dense)
        pi_bins = np.quantile(p_v[m_val], np.linspace(0, 1, N_BINS + 1))
        pi_bins[0] = -np.inf
        pi_bins[-1] = np.inf
        q_glob = float(np.quantile(s_v[m_val], Q_STAR))
        c_bin_q = []
        for b_i in range(N_BINS):
            in_b = m_val & (p_v >= pi_bins[b_i]) & (p_v < pi_bins[b_i + 1])
            if np.sum(in_b) > 20:
                c_bin_q.append(float(np.quantile(s_v[in_b], Q_STAR)))
            else:
                c_bin_q.append(q_glob)
        r_boundary = np.zeros_like(s_t)
        for b_i in range(N_BINS):
            in_t = (p_t >= pi_bins[b_i]) & (p_t < pi_bins[b_i + 1])
            r_boundary[in_t] = c_bin_q[b_i]

        # 2. Direct Baseline Reserve Policy (B1 Wind-Speed Bins from Phase 4)
        # Binned empirical quantiles conditioned on wind speed only
        w_val_norm = physics[val_ds.anchor_indices, :, 0].reshape(-1)
        w_val = w_val_norm * w_std + w_mean
        w_bins = np.linspace(0.0, 25.0, 11)
        w_bins[0] = -np.inf
        w_bins[-1] = np.inf
        w_bin_q = []
        for b_i in range(10):
            in_b = m_val & (w_val >= w_bins[b_i]) & (w_val < w_bins[b_i + 1])
            if np.sum(in_b) > 20:
                w_bin_q.append(float(np.quantile(s_v[in_b], Q_STAR)))
            else:
                w_bin_q.append(q_glob)
        r_direct = np.zeros_like(s_t)
        for b_i in range(10):
            in_t = (wspd_test >= w_bins[b_i]) & (wspd_test < w_bins[b_i + 1])
            r_direct[in_t] = w_bin_q[b_i]

        # Global quantile policy (D_Posterior_Ablated)
        r_global = np.full_like(s_t, q_glob)
        loss_global = (r_global + RHO * np.maximum(s_t - r_global, 0.0)) * DT

        # Pointwise losses (kWh)
        loss_wspd = (r_direct + RHO * np.maximum(s_t - r_direct, 0.0)) * DT
        loss_boundary = (r_boundary + RHO * np.maximum(s_t - r_boundary, 0.0)) * DT

        # Also add Posterior Confidence Slices
        seed_slices = dict(slices)
        seed_slices["08_High_Boundary_Confidence_pi_ge_0.8"] = m_test_base & (p_t >= 0.80)
        seed_slices["09_Moderate_Boundary_Confidence_0.2_to_0.8"] = m_test_base & (p_t >= 0.20) & (p_t < 0.80)
        seed_slices["10_Low_Boundary_Confidence_pi_lt_0.2"] = m_test_base & (p_t < 0.20)

        # Baseline total cost across all observations for share computation
        all_d_glob = np.sum((loss_global - loss_boundary)[m_test_base])
        all_d_wspd = np.sum((loss_wspd - loss_boundary)[m_test_base])

        for s_name, s_mask in seed_slices.items():
            n_obs = int(np.sum(s_mask))
            obs_pct = float(n_obs / np.sum(m_test_base) * 100.0)

            c_glob = float(np.sum(loss_global[s_mask]))
            c_wspd = float(np.sum(loss_wspd[s_mask]))
            c_bnd = float(np.sum(loss_boundary[s_mask]))

            delta_vs_glob_kwh = float(c_glob - c_bnd)
            delta_vs_wspd_kwh = float(c_wspd - c_bnd)
            share_glob_pct = float(delta_vs_glob_kwh / max(all_d_glob, 1.0) * 100.0)

            # Block bootstrap CI vs Global
            mean_boot_g, ci_low_g, ci_high_g, p_boot_g = block_bootstrap_diff(
                loss_global, loss_boundary, time_indices, s_mask, n_boot=N_BOOT, seed=seed
            )
            # Block bootstrap CI vs Wspd
            mean_boot_w, ci_low_w, ci_high_w, p_boot_w = block_bootstrap_diff(
                loss_wspd, loss_boundary, time_indices, s_mask, n_boot=N_BOOT, seed=seed
            )

            results.append({
                "seed": seed,
                "slice_id": s_name,
                "n_observations": n_obs,
                "obs_percentage": obs_pct,
                "global_cost_kwh": c_glob,
                "wspd_cost_kwh": c_wspd,
                "boundary_cost_kwh": c_bnd,
                "delta_vs_global_kwh": delta_vs_glob_kwh,
                "share_vs_global_pct": share_glob_pct,
                "boot_ci_low_vs_global": ci_low_g,
                "boot_ci_high_vs_global": ci_high_g,
                "p_val_vs_global": p_boot_g,
                "delta_vs_wspd_kwh": delta_vs_wspd_kwh,
                "boot_ci_low_vs_wspd": ci_low_w,
                "boot_ci_high_vs_wspd": ci_high_w,
                "p_val_vs_wspd": p_boot_w,
            })

    df_raw = pd.DataFrame(results)

    # Aggregate across seeds
    agg_rows = []
    for s_name, grp in df_raw.groupby("slice_id"):
        agg_rows.append({
            "slice_id": s_name,
            "n_observations": int(grp["n_observations"].mean()),
            "obs_percentage": float(grp["obs_percentage"].mean()),
            "global_cost_mean_kwh": float(grp["global_cost_kwh"].mean()),
            "wspd_cost_mean_kwh": float(grp["wspd_cost_kwh"].mean()),
            "boundary_cost_mean_kwh": float(grp["boundary_cost_kwh"].mean()),
            "delta_vs_global_kwh_mean": float(grp["delta_vs_global_kwh"].mean()),
            "delta_vs_global_kwh_std": float(grp["delta_vs_global_kwh"].std()),
            "share_vs_global_pct_mean": float(grp["share_vs_global_pct"].mean()),
            "boot_ci_low_vs_global_mean": float(grp["boot_ci_low_vs_global"].mean()),
            "boot_ci_high_vs_global_mean": float(grp["boot_ci_high_vs_global"].mean()),
            "p_val_vs_global": float(grp["p_val_vs_global"].mean()),
            "delta_vs_wspd_kwh_mean": float(grp["delta_vs_wspd_kwh"].mean()),
            "delta_vs_wspd_kwh_std": float(grp["delta_vs_wspd_kwh"].std()),
            "boot_ci_low_vs_wspd_mean": float(grp["boot_ci_low_vs_wspd"].mean()),
            "boot_ci_high_vs_wspd_mean": float(grp["boot_ci_high_vs_wspd"].mean()),
            "p_val_vs_wspd": float(grp["p_val_vs_wspd"].mean()),
        })

    df_agg = pd.DataFrame(agg_rows).sort_values("slice_id")
    df_agg.to_csv(out_csv, index=False)
    print(f"\n[Saved] Mediation analysis summary to {out_csv}", flush=True)

    print("\n=== DECISION-VALUE MEDIATION SUMMARY (VS GLOBAL QUANTILE) ===")
    print(df_agg[["slice_id", "obs_percentage", "delta_vs_global_kwh_mean", "share_vs_global_pct_mean", "boot_ci_low_vs_global_mean", "boot_ci_high_vs_global_mean", "p_val_vs_global"]].to_string(index=False))

    print("\n=== DECISION-VALUE MEDIATION SUMMARY (VS WSPD-BIN QUANTILE) ===")
    print(df_agg[["slice_id", "obs_percentage", "delta_vs_wspd_kwh_mean", "boot_ci_low_vs_wspd_mean", "boot_ci_high_vs_wspd_mean", "p_val_vs_wspd"]].to_string(index=False))


if __name__ == "__main__":
    main()
