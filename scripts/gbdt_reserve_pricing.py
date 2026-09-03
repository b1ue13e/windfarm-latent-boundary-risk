"""K3: can a GBDT classifier's soft probability reproduce the reserve pricing
increment of the gate posterior?

Final decision point for the uncertainty-pricing contribution: the MoE gate
outputs P(pitch) and an uncertainty; a GBDT on consequence channels also
outputs P(pitch) and an uncertainty. If GBDT-based soft bins reproduce (or
beat) soft-gate-bin, then the pricing contribution is not MoE-specific.

Strategies (boundary band, validation-frozen, rho=10, 5 seeds):
  - soft-gate-bin  (gate P(pitch) quintiles, reference)
  - soft-pab-bin   (physical pitch quintiles, the winning soft-rule baseline)
  - soft-gbdt-bin  (GBDT P(pitch) quintiles, learned on consequence channels)
  - entropy-gate-bin / entropy-gbdt-bin (uncertainty quintiles from gate / GBDT)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler

from windfarm_moe.data import RegimeWindowDataset, load_cache_bundle

DT = 1.0 / 6.0
QUANTILE_GRID = [0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 0.975, 0.99]
N_BINS = 5
CONS_FEATURES = ["Wdir_sin", "Wdir_cos", "Ndir_sin", "Ndir_cos", "Etmp", "Itmp", "Pab_std", "Prtv", "Patv_hist"]


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


def build_cons_matrix(bundle, split):
    ds = RegimeWindowDataset(bundle, split, int(bundle.metadata["hist_len"]), int(bundle.metadata["pred_len"]))
    anchors = ds.anchor_indices
    names = list(bundle.metadata.get("feature_names", []))
    keep = [names.index(n) for n in CONS_FEATURES]
    features = np.asarray(bundle.features, dtype=np.float64)
    regime = np.asarray(bundle.regime_primary, dtype=np.int64)
    valid = np.asarray(bundle.regime_primary_valid, dtype=bool)
    H = int(bundle.metadata["hist_len"])
    idx = anchors[:, None] - np.arange(H)[None, ::-1]
    wins = features[idx][..., keep]  # (W,H,N,9)
    X = np.concatenate([wins[:, 0, :, :], wins.mean(axis=1), wins.std(axis=1),
                        np.nan_to_num(np.nanmax(wins, axis=1))], axis=2)
    W, N, D = X.shape
    X = X.reshape(W * N, D)
    y = (regime[anchors] == 2).reshape(-1)
    sel = (np.isin(regime[anchors], [1, 2]) & valid[anchors]).reshape(-1)
    return X, y, sel


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
    ap.add_argument("--cache-dir", default="artifacts/cache_strictmask_trainweights/wtb_245d")
    ap.add_argument("--suite-root", required=True)
    ap.add_argument("--run-pattern", default="wtb_bal_align_force_seed{seed}")
    ap.add_argument("--seeds", default="201,202,203,204,205")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--rated-wind", type=float, default=10.5)
    ap.add_argument("--band", type=float, default=1.0)
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = load_cache_bundle(args.cache_dir, mmap_mode="r")
    X_tr, y_tr, sel_tr = build_cons_matrix(bundle, "train")
    X_va, _, _ = build_cons_matrix(bundle, "val")
    X_te, _, _ = build_cons_matrix(bundle, "test")
    scaler = StandardScaler().fit(X_tr)
    gbdt = HistGradientBoostingClassifier(max_iter=300, random_state=0)
    gbdt.fit(scaler.transform(X_tr)[sel_tr], y_tr[sel_tr])
    print("gbdt fitted", flush=True)

    rows = []
    for seed in [int(s) for s in args.seeds.split(",")]:
        run_dir = Path(args.suite_root) / args.run_pattern.format(seed=seed)
        pv, tv, mv, rv_, gv, av = load_split(run_dir, "val")
        pt, tt, mt, rt_, gt, at = load_split(run_dir, "test")
        s_val = shortfall_cells(pv, tv, mv)
        s_test = shortfall_cells(pt, tt, mt)
        H = s_val.shape[1]

        p3 = gv[..., :3]
        gate_pp = p3[..., 2] / np.maximum(p3.sum(axis=-1), 1e-9)
        gate_ent = -(p3 * np.log(np.clip(p3, 1e-9, None))).sum(axis=-1)
        g3t = gt[..., :3]
        gate_pp_t = g3t[..., 2] / np.maximum(g3t.sum(axis=-1), 1e-9)
        gate_ent_t = -(g3t * np.log(np.clip(g3t, 1e-9, None))).sum(axis=-1)
        wspd_v, pab_v = av[..., 0], av[..., 1]
        wspd_t, pab_t = at[..., 0], at[..., 1]
        va_v = np.isin(rv_, [1, 2]) & (np.abs(wspd_v - args.rated_wind) <= args.band)
        va_t = np.isin(rt_, [1, 2]) & (np.abs(wspd_t - args.rated_wind) <= args.band)

        gbdt_va = gbdt.predict_proba(scaler.transform(X_va))[:, 1].reshape(va_v.shape[0], -1)
        gbdt_te = gbdt.predict_proba(scaler.transform(X_te))[:, 1].reshape(va_t.shape[0], -1)
        gbdt_ent_v = -(gbdt_va * np.log(np.clip(gbdt_va, 1e-9, None)) + (1 - gbdt_va) * np.log(np.clip(1 - gbdt_va, 1e-9, None)))
        gbdt_ent_t = -(gbdt_te * np.log(np.clip(gbdt_te, 1e-9, None)) + (1 - gbdt_te) * np.log(np.clip(1 - gbdt_te, 1e-9, None)))

        cell_v = broadcast(va_v, H)
        cell_t = broadcast(va_t, s_test.shape[1])

        policies = {
            "soft-pab-bin": (pab_v, pab_t),
            "soft-gate-bin": (gate_pp, gate_pp_t),
            "soft-gbdt-bin": (gbdt_va, gbdt_te),
            "entropy-gate-bin": (gate_ent, gate_ent_t),
            "entropy-gbdt-bin": (gbdt_ent_v, gbdt_ent_t),
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
    df.to_csv(out_dir / "gbdt_reserve_pricing_by_seed.csv", index=False)
    print()
    print("=== policy means at rho=10 ===")
    print(df.groupby("policy")[["total_cost", "violation_rate", "reserve", "shortage"]].mean().to_string())
    print("GBDT_RESERVE_PRICING_DONE")


if __name__ == "__main__":
    main()
