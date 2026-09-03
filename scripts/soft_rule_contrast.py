"""Experiment A (breakthrough probe): learned soft posterior vs softened rule bins.

The final-review attack: soft-gate-bin uses P(pitch) from the gate, which is
highly correlated with the physical threshold. If binning by *continuous
physical quantities* (wind speed, distance to rated wind, pitch angle)
reproduces the reserve saving, the contribution is merely "softening the
threshold", not "learning".

Pre-registered decision criterion:
  - soft-gate-bin must beat EVERY soft-rule strategy with a seed-paired 95%
    CI for total cost that excludes zero -> the learned posterior has an
    increment over softened rules.
  - otherwise the pricing contribution downgrades to "continuous binning".

Protocol: identical to uncertainty_binning_reserve.py (boundary band
|Wspd-10.5|<=1, horizon cells, validation-frozen quintile edges, rho=10,
5 seeds, seed-paired bootstrap CIs).
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


def degrade_physics(anchor, seed, delay=0, noise=None):
    """Degrade Wspd/Pab readings (raw standardized space) identically to the
    fair-degradation audit: issue-time delay via lag, noise via Gaussian."""
    out = anchor.copy()
    wspd = out[..., 0].copy()
    pab = out[..., 1].copy()
    rng = np.random.default_rng(1729 + seed * 1009 + delay * 7 + (0 if noise is None else int(noise[0] * 100 + noise[1] * 10)))
    if delay > 0:
        wspd = np.concatenate([wspd[:delay], wspd[:-delay]], axis=0)
        pab = np.concatenate([pab[:delay], pab[:-delay]], axis=0)
    if noise is not None:
        wspd = wspd + rng.normal(0.0, float(noise[0]), size=wspd.shape)
        pab = pab + rng.normal(0.0, float(noise[1]), size=pab.shape)
    out[..., 0] = wspd
    out[..., 1] = pab
    return out


def shortfall_cells(pred, target, mask):
    return np.where(mask, np.maximum(pred - target, 0.0), np.nan)


def anchor_fields(gate, regime, anchor, rated_wind, band):
    p3 = gate[..., :3]
    p_pitch = p3[..., 2] / np.maximum(p3.sum(axis=-1), 1e-9)
    wspd = anchor[..., 0]
    pab = anchor[..., 1]
    in_band = np.abs(wspd - rated_wind) <= band
    valid_anchor = np.isin(regime, [1, 2]) & in_band
    fields = {
        "gate_ppitch": p_pitch,
        "wspd": wspd,
        "pab": pab,
        "dist": np.abs(wspd - rated_wind),
    }
    return fields, valid_anchor, regime


def broadcast(bin_anchor, H):
    return np.repeat(bin_anchor[:, None, :], H, axis=1)


def policy_bins(name, fields, regime, val_anchor, edges=None):
    if name == "global":
        return np.zeros_like(regime, dtype=int), None
    if name == "physical-bin":
        return np.where(regime == 2, 1, 0), None
    key = {
        "soft-gate-bin": "gate_ppitch",
        "soft-wspd-bin": "wspd",
        "soft-dist-bin": "dist",
        "soft-pab-bin": "pab",
    }[name]
    values = fields[key]
    if edges is None:
        edges = np.quantile(values[val_anchor], np.linspace(0, 1, N_BINS + 1)[1:-1])
    return np.clip(np.searchsorted(edges, values), 0, N_BINS - 1), edges


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
    policies = ["global", "physical-bin", "soft-gate-bin", "soft-wspd-bin", "soft-dist-bin", "soft-pab-bin"]

    rows = []
    for seed in [int(s) for s in args.seeds.split(",")]:
        run_dir = Path(args.suite_root) / args.run_pattern.format(seed=seed)
        pv, tv, mv, rv_, gv, av = load_split(run_dir, "val")
        pt, tt, mt, rt_, gt, at = load_split(run_dir, "test")
        s_val = shortfall_cells(pv, tv, mv)
        s_test = shortfall_cells(pt, tt, mt)
        H = s_val.shape[1]

        # clean comparison
        f_v, va_v, reg_v = anchor_fields(gv, rv_, av, args.rated_wind, args.band)
        f_t, va_t, reg_t = anchor_fields(gt, rt_, at, args.rated_wind, args.band)
        cell_v = broadcast(va_v, H)
        cell_t = broadcast(va_t, s_test.shape[1])

        for pol in policies:
            bin_v, edges = policy_bins(pol, f_v, reg_v, va_v)
            bin_t, _ = policy_bins(pol, f_t, reg_t, va_t, edges=edges)
            bin_v_c = broadcast(bin_v, H)
            bin_t_c = broadcast(bin_t, s_test.shape[1])
            for rho in rhos:
                reserves = fit_policy(s_val, cell_v, bin_v_c, rho)
                m = eval_policy(s_test, cell_t, bin_t_c, reserves, rho)
                m.update({"seed": seed, "policy": pol, "rho": rho, "condition": "clean"})
                rows.append(m)

        # degraded comparison: soft-pab-bin and soft-wspd-bin bins fitted on
        # VALIDATION with clean physics but applied on TEST with degraded
        # physics readings (fair-degradation semantics; the gate posterior is
        # not recomputed, matching the saved-route audit).
        for delay, noise, label in [(1, None, "delay1"), (3, None, "delay3"), (6, None, "delay6"), (0, (1.0, 2.0), "noise_strong")]:
            at_d = degrade_physics(at, seed, delay=delay, noise=noise)
            f_td, va_td, reg_td = anchor_fields(gt, rt_, at_d, args.rated_wind, args.band)
            va_td = va_td & va_t
            for pol in ["soft-pab-bin", "soft-wspd-bin", "soft-gate-bin"]:
                bin_v, edges = policy_bins(pol, f_v, reg_v, va_v)
                bin_td, _ = policy_bins(pol, f_td, reg_td, va_td, edges=edges)
                bin_v_c = broadcast(bin_v, H)
                bin_td_c = broadcast(bin_td, s_test.shape[1])
                for rho in rhos:
                    reserves = fit_policy(s_val, cell_v, bin_v_c, rho)
                    m = eval_policy(s_test, cell_t, bin_td_c, reserves, rho)
                    m.update({"seed": seed, "policy": pol, "rho": rho, "condition": label})
                    rows.append(m)
        print(f"seed {seed} done", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "soft_rule_contrast_by_seed.csv", index=False)

    rng = np.random.default_rng(42)
    summary = []
    clean = df[df["condition"] == "clean"]
    for rho in rhos:
        sub = clean[clean["rho"] == rho]
        for strat in ["soft-gate-bin", "soft-wspd-bin", "soft-dist-bin", "soft-pab-bin"]:
            for base in ["global", "physical-bin"]:
                for metric in ["total_cost", "violation_rate", "shortage", "reserve"]:
                    wide = sub.pivot(index="seed", columns="policy", values=metric)
                    d = (wide[strat] - wide[base]).dropna().to_numpy()
                    boots = rng.choice(d, size=(20000, d.size), replace=True).mean(axis=1)
                    summary.append({
                        "rho": rho, "metric": metric, "strategy": strat, "baseline": base,
                        "condition": "clean",
                        "delta_mean": float(d.mean()),
                        "ci_low": float(np.percentile(boots, 2.5)),
                        "ci_high": float(np.percentile(boots, 97.5)),
                        "n_seeds": int(d.size),
                    })
    for label in ["delay1", "delay3", "delay6", "noise_strong"]:
        sub = df[(df["condition"] == label) & (df["rho"] == rhos[0])]
        clean_sub = clean[clean["rho"] == rhos[0]]
        for strat in ["soft-pab-bin", "soft-wspd-bin", "soft-gate-bin"]:
            for base in ["soft-gate-bin"]:
                for metric in ["total_cost"]:
                    wide = sub.pivot(index="seed", columns="policy", values=metric)
                    cwide = clean_sub.pivot(index="seed", columns="policy", values=metric)
                    d = (wide[strat] - wide[base]).dropna().to_numpy()
                    boots = rng.choice(d, size=(20000, d.size), replace=True).mean(axis=1)
                    summary.append({
                        "rho": rhos[0], "metric": metric, "strategy": strat, "baseline": base,
                        "condition": label,
                        "delta_mean": float(d.mean()),
                        "ci_low": float(np.percentile(boots, 2.5)),
                        "ci_high": float(np.percentile(boots, 97.5)),
                        "n_seeds": int(d.size),
                    })
    sdf = pd.DataFrame(summary)
    sdf.to_csv(out_dir / "soft_rule_contrast_paired_summary.csv", index=False)
    print(sdf.to_string(index=False))
    print()
    print("=== policy means at rho=10 (clean) ===")
    print(clean[clean["rho"] == 10].groupby("policy")[["total_cost", "violation_rate", "reserve", "shortage"]].mean().to_string())
    print()
    print("=== policy means at rho=10 by degradation ===")
    print(df[df["rho"] == 10].groupby(["condition", "policy"])["total_cost"].mean().to_string())
    print("SOFT_RULE_CONTRAST_DONE")


if __name__ == "__main__":
    main()
