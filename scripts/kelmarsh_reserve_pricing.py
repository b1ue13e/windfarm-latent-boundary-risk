"""K1: reserve pricing on a pitch-sparse farm (Kelmarsh, 55% pitch coverage).

Decision question: on a farm where blade pitch is only partially observed,
does the routed soft posterior still price reserve risk, while the direct
pitch-quantile binning loses cells?

Strategies inside the Wspd-defined boundary band (|Wspd-10.5|<=1, regime in
{1,2}, valid cells):
  - global:          one validation-frozen quantile
  - soft-gate-bin:   P(pitch) quintiles from the gate posterior (all cells)
  - soft-pab-bin:    Pab quintiles where pitch is observed; unobserved cells
                     fall back to the global quantile (the best a physical
                     reading can do under partial observability)

Protocol: validation-frozen quantiles, rho=10, 5 seeds (canonical runs on the
Kelmarsh observability-window cache), seed-paired bootstrap CIs.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

DT = 1.0 / 6.0
QUANTILE_GRID = [0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 0.975, 0.99]
N_BINS = 5


def load_split(run_dir: Path, split: str):
    d = run_dir / f"{split}_metrics"
    pred = np.load(d / "pred.npy")
    target = np.load(d / "target.npy")
    mask = np.load(d / "mask.npy") > 0.5
    regime = np.load(d / "regime_primary.npy")
    gate = np.load(d / "gate_prob.npy")
    anchor = np.load(d / "anchor_physics.npy")
    return pred, target, mask, regime, gate, anchor


def shortfall_cells(pred, target, mask):
    return np.where(mask, np.maximum(pred - target, 0.0), np.nan)


def fields(gate, regime, anchor, rated_wind, band):
    p3 = gate[..., :3]
    p_pitch = p3[..., 2] / np.maximum(p3.sum(axis=-1), 1e-9)
    wspd = anchor[..., 0]
    pab = anchor[..., 1]
    in_band = np.abs(wspd - rated_wind) <= band
    valid_anchor = np.isin(regime, [1, 2]) & in_band
    pab_observed = (regime == 0) | np.isfinite(pab)  # observed mask approximated by validity elsewhere
    return {"gate_ppitch": p_pitch, "pab": pab}, valid_anchor, regime, pab_observed


def broadcast(bin_anchor, H):
    return np.repeat(bin_anchor[:, None, :], H, axis=1)


def policy_bins(name, fld, regime, val_anchor, pab_obs, edges=None):
    if name == "global":
        return np.zeros_like(regime, dtype=int), None
    if name == "soft-gate-bin":
        values = fld["gate_ppitch"]
        if edges is None:
            edges = np.quantile(values[val_anchor], np.linspace(0, 1, N_BINS + 1)[1:-1])
        return np.clip(np.searchsorted(edges, values), 0, N_BINS - 1), edges
    if name == "soft-pab-bin":
        values = fld["pab"]
        if edges is None:
            edges = np.quantile(values[val_anchor & pab_obs], np.linspace(0, 1, N_BINS + 1)[1:-1])
        bins = np.clip(np.searchsorted(edges, values), 0, N_BINS - 1)
        bins[~pab_obs] = 0  # fall back to the global bin where pitch is unobserved
        return bins, edges
    raise ValueError(name)


def fit_policy(s_val, cell_sel_val, bin_val, rho):
    sel = cell_sel_val & np.isfinite(s_val)
    out = {}
    for b in np.unique(bin_val[cell_sel_val]):
        sb = s_val[sel & (bin_val == b)]
        if sb.size < 50:
            sb = s_val[sel]
        best = None
        for q in QUANTILE_GRID:
            r = np.quantile(sb, q)
            cost = (r * sb.size + rho * np.maximum(sb - r, 0).sum()) * DT
            if best is None or cost < best[0]:
                best = (cost, q, r)
        out[int(b)] = (best[1], best[2])
    return out


def eval_policy(s_test, cell_sel_test, bin_test, reserves, rho):
    sel = cell_sel_test & np.isfinite(s_test)
    s = s_test[sel]
    b = bin_test[sel]
    r = np.array([reserves[int(x)][1] for x in b])
    return {
        "total_cost": float((r.sum() + rho * np.maximum(s - r, 0).sum()) * DT),
        "violation_rate": float(np.mean(s > r)),
        "reserve": float(r.sum() * DT),
        "shortage": float(np.maximum(s - r, 0).sum() * DT),
        "n_cells": int(s.size),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite-root", required=True)
    ap.add_argument("--run-pattern", default="wtb_bal_align_force_seed{seed}")
    ap.add_argument("--seeds", default="201,202,203,204,205")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--rated-wind", type=float, default=10.5)
    ap.add_argument("--band", type=float, default=1.0)
    ap.add_argument("--rhos", default="10")
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rhos = [float(x) for x in args.rhos.split(",")]
    policies = ["global", "soft-gate-bin", "soft-pab-bin"]

    rows = []
    for seed in [int(s) for s in args.seeds.split(",")]:
        run_dir = Path(args.suite_root) / args.run_pattern.format(seed=seed)
        pv, tv, mv, rv_, gv, av = load_split(run_dir, "val")
        pt, tt, mt, rt_, gt, at = load_split(run_dir, "test")
        s_val = shortfall_cells(pv, tv, mv)
        s_test = shortfall_cells(pt, tt, mt)
        H = s_val.shape[1]

        f_v, va_v, reg_v, pobs_v = fields(gv, rv_, av, args.rated_wind, args.band)
        f_t, va_t, reg_t, pobs_t = fields(gt, rt_, at, args.rated_wind, args.band)
        # pitch-observed approximation: pitch channel nonzero after fill
        pobs_v = pobs_v & (av[..., 1] != 0.0)
        pobs_t = pobs_t & (at[..., 1] != 0.0)
        cell_v = broadcast(va_v, H)
        cell_t = broadcast(va_t, s_test.shape[1])

        for pol in policies:
            bin_v, edges = policy_bins(pol, f_v, reg_v, va_v, pobs_v)
            bin_t, _ = policy_bins(pol, f_t, reg_t, va_t, pobs_t, edges=edges)
            bin_v_c = broadcast(bin_v, H)
            bin_t_c = broadcast(bin_t, s_test.shape[1])
            for rho in rhos:
                reserves = fit_policy(s_val, cell_v, bin_v_c, rho)
                m = eval_policy(s_test, cell_t, bin_t_c, reserves, rho)
                m.update({"seed": seed, "policy": pol, "rho": rho})
                rows.append(m)
        print(f"seed {seed} done", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "kelmarsh_reserve_by_seed.csv", index=False)

    rng = np.random.default_rng(42)
    summary = []
    for rho in rhos:
        sub = df[df["rho"] == rho]
        for strat in ["soft-gate-bin", "soft-pab-bin"]:
            for base in ["global", "soft-pab-bin"]:
                if strat == base:
                    continue
                for metric in ["total_cost", "violation_rate", "shortage", "reserve"]:
                    wide = sub.pivot(index="seed", columns="policy", values=metric)
                    d = (wide[strat] - wide[base]).dropna().to_numpy()
                    boots = rng.choice(d, size=(20000, d.size), replace=True).mean(axis=1)
                    summary.append({
                        "rho": rho, "metric": metric, "strategy": strat, "baseline": base,
                        "delta_mean": float(d.mean()),
                        "ci_low": float(np.percentile(boots, 2.5)),
                        "ci_high": float(np.percentile(boots, 97.5)),
                        "n_seeds": int(d.size),
                    })
    sdf = pd.DataFrame(summary)
    sdf.to_csv(out_dir / "kelmarsh_reserve_paired_summary.csv", index=False)
    print(sdf.to_string(index=False))
    print()
    print("=== policy means at rho=10 ===")
    print(df[df["rho"] == 10].groupby("policy")[["total_cost", "violation_rate", "reserve", "shortage"]].mean().to_string())
    print("KELMARSH_RESERVE_DONE")


if __name__ == "__main__":
    main()
