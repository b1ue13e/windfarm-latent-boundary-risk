"""Export EXP-01 native day-block evaluation arrays and verify reconstruction precision.

Loads saved pitch-masked gates from artifacts/exp01_pitchmasked_v4, reproduces pointwise
reserve costs against Site-Local Wspd-Bins baselines, verifies sum precision vs
exp01_pitchmasked_v3_seed_results.csv, and exports:
artifacts/exp01_pitchmasked_v4/exp01_native_day_blocks_v4.npz
"""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.hierarchical_bootstrap import compute_hierarchical_joint_bootstrap
from windfarm_moe.data import load_cache_bundle

FARMS = {
    "penmanshiel": ("Penmanshiel", "artifacts/cache_signature_penmanshiel/external_wind_penmanshiel_obs_window_canonical"),
    "kelmarsh": ("Kelmarsh", "artifacts/cache_signature_kelmarsh/external_wind_kelmarsh_obs_window_canonical"),
}
RHO = 10.0
DT = 1.0 / 6.0
BLOCK_SIZE = 144
TAU = 0.90


def fit_bins(values, s, mask, bins, min_n=30):
    edges = np.unique(np.quantile(values[mask], np.linspace(0, 1, bins + 1)[1:-1]))
    assignment = np.digitize(values, edges)
    global_q = float(np.quantile(s[mask], TAU))
    qs = np.array([
        float(np.quantile(s[(assignment == b) & mask], TAU))
        if np.sum((assignment == b) & mask) >= min_n else global_q
        for b in range(len(edges) + 1)
    ])
    return edges, qs


def block_eval(s, rc, rb, mask, anchors):
    ordered = np.unique(anchors)
    indices = np.array([int(np.searchsorted(ordered, a)) // BLOCK_SIZE for a in anchors])
    n = int(indices.max()) + 1
    valid = mask & np.isfinite(s) & np.isfinite(rc) & np.isfinite(rb)
    
    point_c = (rc + RHO * np.maximum(s - rc, 0)) * DT
    point_b = (rb + RHO * np.maximum(s - rb, 0)) * DT
    diff = point_c - point_b
    
    delta = np.bincount(indices, weights=np.where(valid, diff, 0).sum(axis=1), minlength=n)
    cost_c = np.bincount(indices, weights=np.where(valid, point_c, 0).sum(axis=1), minlength=n)
    cost_b = np.bincount(indices, weights=np.where(valid, point_b, 0).sum(axis=1), minlength=n)
    counts = np.bincount(indices, weights=valid.sum(axis=1), minlength=n)
    return delta, cost_c, cost_b, counts


def main():
    v4_dir = REPO_ROOT / "artifacts" / "exp01_pitchmasked_v4"
    seed_csv = v4_dir / "exp01_pitchmasked_v3_seed_results.csv"
    if not seed_csv.exists():
        raise FileNotFoundError(f"Missing {seed_csv}")
    
    df_expected = pd.read_csv(seed_csv)
    
    seeds = [201, 202, 203, 204, 205]
    npz_data = {}
    reconstructed_rows = []
    
    for farm, (display, cache_rel) in FARMS.items():
        bundle = load_cache_bundle(REPO_ROOT / cache_rel, mmap_mode="r")
        physics_names = bundle.metadata.get("physics_names", [])
        wspd_idx = physics_names.index("Wspd") if "Wspd" in physics_names else 0
        pred_len = int(bundle.metadata["pred_len"])
        
        for seed in seeds:
            run_dir = REPO_ROOT / f"artifacts/external_wind_runs/{farm}/chronological/external_wind_full_seed{seed}"
            val_anchor = np.load(run_dir / "val_metrics/anchor_index.npy")
            test_anchor = np.load(run_dir / "test_metrics/anchor_index.npy")
            
            val_target = np.stack([np.asarray(bundle.target[a+1:a+1+pred_len]) for a in val_anchor])
            test_target = np.stack([np.asarray(bundle.target[a+1:a+1+pred_len]) for a in test_anchor])
            val_mask = np.stack([np.asarray(bundle.target_mask[a+1:a+1+pred_len]) for a in val_anchor]).astype(bool)
            test_mask = np.stack([np.asarray(bundle.target_mask[a+1:a+1+pred_len]) for a in test_anchor]).astype(bool)
            
            vp = np.load(run_dir / "val_metrics/pred.npy")
            tp = np.load(run_dir / "test_metrics/pred.npy")
            val_wspd = np.asarray(bundle.physics_model[val_anchor, :, wspd_idx])
            test_wspd = np.asarray(bundle.physics_model[test_anchor, :, wspd_idx])
            
            val_gate = np.load(v4_dir / f"{farm}_seed{seed}_val_gate_pitchmasked.npy")
            test_gate = np.load(v4_dir / f"{farm}_seed{seed}_test_gate_pitchmasked.npy")
            
            for lead, horizon in ((0, "h=1"), (5, "h=6")):
                sv = np.maximum(vp[:, lead, :] - val_target[:, lead, :], 0)
                st = np.maximum(tp[:, lead, :] - test_target[:, lead, :], 0)
                mv, mt = val_mask[:, lead, :], test_mask[:, lead, :]
                
                # Fit 10-bin Wspd baseline on validation
                w_edges, wq = fit_bins(val_wspd, sv, mv, 10)
                w_reserve = wq[np.clip(np.digitize(test_wspd, w_edges), 0, len(wq)-1)]
                
                # Fit 5-bin Gate baseline on validation
                gv = val_gate[..., 2]
                gt = test_gate[..., 2]
                g_edges, gq = fit_bins(gv, sv, mv, 5)
                g_reserve = gq[np.clip(np.digitize(gt, g_edges), 0, len(gq)-1)]
                
                valid = mt & np.isfinite(st)
                delta, cost_c, cost_b, counts = block_eval(st, g_reserve, w_reserve, valid, test_anchor)
                
                # Store block arrays
                prefix = f"{farm}_{horizon}_seed{seed}"
                npz_data[f"{prefix}_delta"] = delta
                npz_data[f"{prefix}_cost_c"] = cost_c
                npz_data[f"{prefix}_cost_b"] = cost_b
                npz_data[f"{prefix}_count"] = counts
                
                # Verify match against expected
                exp_row = df_expected[(df_expected["farm_id"] == farm) & (df_expected["seed"] == seed) & (df_expected["horizon"] == horizon)].iloc[0]
                rec_cost_c = float(cost_c.sum())
                rec_cost_b = float(cost_b.sum())
                rec_delta = float(delta.sum())
                rec_n = int(counts.sum())
                
                err_c = abs(rec_cost_c - exp_row["psrei_kwh"])
                err_b = abs(rec_cost_b - exp_row["baseline_psrei_kwh"])
                err_d = abs(rec_delta - exp_row["delta_psrei_kwh"])
                assert err_c < 0.1, f"Cost C mismatch for {prefix}: {err_c}"
                assert err_b < 0.1, f"Cost B mismatch for {prefix}: {err_b}"
                assert err_d < 0.1, f"Delta mismatch for {prefix}: {err_d}"
                assert rec_n == int(exp_row["n_evaluated_cells"]), f"Cell count mismatch for {prefix}: {rec_n} vs {exp_row['n_evaluated_cells']}"
                
                reconstructed_rows.append({
                    "farm": farm, "horizon": horizon, "seed": seed,
                    "delta_kwh": rec_delta, "cells": rec_n,
                    "mean_delta_per_cell_kwh": rec_delta / rec_n
                })
    
    out_npz = v4_dir / "exp01_native_day_blocks_v4.npz"
    np.savez_compressed(out_npz, **npz_data)
    print(f"Successfully exported {len(npz_data)} arrays to {out_npz}")
    
    # Verify hierarchical bootstrap reproduces joint statistics
    joint_csv = v4_dir / "exp01_pitchmasked_v3_joint_statistics.csv"
    df_joint_exp = pd.read_csv(joint_csv)
    for (farm, horizon), grp in pd.DataFrame(reconstructed_rows).groupby(["farm", "horizon"]):
        seeds_deltas = {s: npz_data[f"{farm}_{horizon}_seed{s}_delta"] for s in seeds}
        j = compute_hierarchical_joint_bootstrap(seeds_deltas, n_boot=5000, two_stage_resample=True, random_seed=20261014)
        exp_j = df_joint_exp[(df_joint_exp["farm_id"] == farm) & (df_joint_exp["horizon"] == horizon)].iloc[0]
        err_m = abs(j["joint_mean"] - exp_j["mean_delta_psrei_kwh"])
        print(f"Hierarchical bootstrap check for {farm} {horizon}: Mean={j['joint_mean']:.1f} kWh (expected {exp_j['mean_delta_psrei_kwh']:.1f}, err={err_m:.2f}), P(delta<=0)={j['joint_p_non_inferior']:.4f}")
        assert err_m < 0.1, f"Joint mean mismatch for {farm} {horizon}: {err_m}"


if __name__ == "__main__":
    main()
