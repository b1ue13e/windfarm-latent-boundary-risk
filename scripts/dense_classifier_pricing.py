"""K4: dense-classifier-head posterior pricing vs gate posterior vs soft rule.

The jointly-learned-but-not-routed posterior (same encoder, dense forecast
head, softmax classifier head) is evaluated with the identical soft-bin
reserve protocol. Decision:

  - If dense-classifier soft bins price as well as soft-gate-bin, the
    increment belongs to joint learning, not to MoE routing.
  - If dense-classifier soft bins price worse (toward the GBDT level),
    the MoE routing structure itself carries the pricing increment.

Strategies: soft-pab-bin / soft-gate-bin / soft-dense-bin (P(pitch) quintiles)
and entropy-gate-bin / entropy-dense-bin (uncertainty quintiles).
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


def broadcast(bin_anchor, H):
    return np.repeat(bin_anchor[:, None, :], H, axis=1)


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
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate-suite-root", required=True)
    ap.add_argument("--dense-suite-root", required=True)
    ap.add_argument("--gate-run-pattern", default="wtb_bal_align_force_seed{seed}")
    ap.add_argument("--dense-run-pattern", default="wtb_bal_align_force_seed{seed}")
    ap.add_argument("--seeds", default="201,202,203,204,205")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--rated-wind", type=float, default=10.5)
    ap.add_argument("--band", type=float, default=1.0)
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for seed in [int(s) for s in args.seeds.split(",")]:
        gdir = Path(args.gate_suite_root) / args.gate_run_pattern.format(seed=seed)
        ddir = Path(args.dense_suite_root) / args.dense_run_pattern.format(seed=seed)
        pv, tv, mv, rv_, gv, av = load_split(gdir, "val")
        pt, tt, mt, rt_, gt, at = load_split(gdir, "test")
        dpv, dtv, dmv, drv_, dgv, dav = load_split(ddir, "val")
        dpt, dtt, dmt, drt_, dgt, dat = load_split(ddir, "test")
        s_val = shortfall_cells(pv, tv, mv)
        s_test = shortfall_cells(pt, tt, mt)
        H = s_val.shape[1]

        def pp_ent(g):
            p3 = g[..., :3]
            pp = p3[..., 2] / np.maximum(p3.sum(axis=-1), 1e-9)
            ent = -(p3 * np.log(np.clip(p3, 1e-9, None))).sum(axis=-1)
            return pp, ent

        gpp_v, gent_v = pp_ent(gv)
        gpp_t, gent_t = pp_ent(gt)
        dpp_v, dent_v = pp_ent(dgv)
        dpp_t, dent_t = pp_ent(dgt)
        wspd_v, pab_v = av[..., 0], av[..., 1]
        wspd_t, pab_t = at[..., 0], at[..., 1]
        va_v = np.isin(rv_, [1, 2]) & (np.abs(wspd_v - args.rated_wind) <= args.band)
        va_t = np.isin(rt_, [1, 2]) & (np.abs(wspd_t - args.rated_wind) <= args.band)
        cell_v = broadcast(va_v, H)
        cell_t = broadcast(va_t, s_test.shape[1])

        policies = {
            "soft-pab-bin": (pab_v, pab_t),
            "soft-gate-bin": (gpp_v, gpp_t),
            "soft-dense-bin": (dpp_v, dpp_t),
            "entropy-gate-bin": (gent_v, gent_t),
            "entropy-dense-bin": (dent_v, dent_t),
        }
        for pol, (vals_v, vals_t) in policies.items():
            edges = np.quantile(vals_v[va_v], np.linspace(0, 1, N_BINS + 1)[1:-1])
            bin_v = np.clip(np.searchsorted(edges, vals_v), 0, N_BINS - 1)
            bin_t = np.clip(np.searchsorted(edges, vals_t), 0, N_BINS - 1)
            reserves = fit_policy(s_val, cell_v, broadcast(bin_v, H), 10.0)
            m = eval_policy(s_test, cell_t, broadcast(bin_t, s_test.shape[1]), reserves, 10.0)
            m.update({"seed": seed, "policy": pol})
            rows.append(m)
        print(f"seed {seed} done", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "dense_pricing_by_seed.csv", index=False)
    print()
    print("=== policy means at rho=10 ===")
    print(df.groupby("policy")[["total_cost", "violation_rate", "reserve", "shortage"]].mean().to_string())
    print("DENSE_PRICING_DONE")


if __name__ == "__main__":
    main()
