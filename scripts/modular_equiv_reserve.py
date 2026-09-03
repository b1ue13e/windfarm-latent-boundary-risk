"""Modular-equivalence reserve control: same-backbone classifier-bin vs in-model gate-bin.

Question from the final review: on the *same* boundary-router backbone, can a
modular issue-time classifier reproduce the in-model gate's reserve value?
The classifier is a validation-fit logistic regression on issue-time anchors
(Wspd, Pab_mean), predicting P(pitch) inside the boundary band. Bins:

  - global          one validation-frozen shortfall quantile
  - physical-bin    rule label (MPPT/pitch)
  - gate-bin        gate hard label (argmax over anchored classes)
  - classifier-bin  classifier hard label
  - soft-gate-bin   P(pitch) quintiles from the gate posterior (E3 reference)
  - soft-clf-bin    P(pitch) quintiles from the classifier

Protocol: boundary band |Wspd-10.5|<=1, horizon cells, validation-frozen
quantiles, rho=10, 5 seeds, seed-paired bootstrap CIs.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

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


def anchor_fields(gate, regime, anchor, rated_wind, band):
    p3 = gate[..., :3]
    p_pitch_gate = p3[..., 2] / np.maximum(p3.sum(axis=-1), 1e-9)
    wspd = anchor[..., 0]
    pab = anchor[..., 1]
    in_band = np.abs(wspd - rated_wind) <= band
    valid_anchor = np.isin(regime, [1, 2]) & in_band
    return {"gate_ppitch": p_pitch_gate, "wspd": wspd, "pab": pab}, valid_anchor, regime


def fit_classifier(fields, valid_anchor, regime, seed):
    rng = np.random.default_rng(seed)
    sel = valid_anchor
    X = np.stack([fields["wspd"][sel], fields["pab"][sel]], axis=-1)
    y = (regime[sel] == 2).astype(np.int64)
    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)
    clf = LogisticRegression(max_iter=1000, C=1.0, random_state=int(seed))
    clf.fit(Xs, y)
    return scaler, clf, rng


def classifier_ppitch(fields, scaler, clf):
    X = np.stack([fields["wspd"], fields["pab"]], axis=-1)
    shape = X.shape[:-1]
    flat = scaler.transform(X.reshape(-1, X.shape[-1]))
    return clf.predict_proba(flat)[:, 1].reshape(shape)


def broadcast(bin_anchor, H):
    return np.repeat(bin_anchor[:, None, :], H, axis=1)


def policy_bins(name, fields, regime, val_anchor, clf_ppitch, edges=None):
    if name == "global":
        return np.zeros_like(regime, dtype=int), None
    if name == "physical-bin":
        return np.where(regime == 2, 1, 0), None
    if name == "gate-bin":
        return (fields["gate_ppitch"] >= 0.5).astype(int), None
    if name == "classifier-bin":
        return (clf_ppitch >= 0.5).astype(int), None
    if name in ("soft-gate-bin", "soft-clf-bin"):
        values = fields["gate_ppitch"] if name == "soft-gate-bin" else clf_ppitch
        if edges is None:
            edges = np.quantile(values[val_anchor], np.linspace(0, 1, N_BINS + 1)[1:-1])
        return np.clip(np.searchsorted(edges, values), 0, N_BINS - 1), edges
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
    policies = ["global", "physical-bin", "gate-bin", "classifier-bin", "soft-gate-bin", "soft-clf-bin"]

    rows = []
    for seed in [int(s) for s in args.seeds.split(",")]:
        run_dir = Path(args.suite_root) / args.run_pattern.format(seed=seed)
        pv, tv, mv, rv_, gv, av = load_split(run_dir, "val")
        pt, tt, mt, rt_, gt, at = load_split(run_dir, "test")
        s_val = shortfall_cells(pv, tv, mv)
        s_test = shortfall_cells(pt, tt, mt)
        H = s_val.shape[1]

        f_v, va_v, reg_v = anchor_fields(gv, rv_, av, args.rated_wind, args.band)
        f_t, va_t, reg_t = anchor_fields(gt, rt_, at, args.rated_wind, args.band)
        scaler, clf, _ = fit_classifier(f_v, va_v, reg_v, seed)
        clf_pp_v = classifier_ppitch(f_v, scaler, clf)
        clf_pp_t = classifier_ppitch(f_t, scaler, clf)
        cell_v = broadcast(va_v, H)
        cell_t = broadcast(va_t, s_test.shape[1])

        for pol in policies:
            bin_v, edges = policy_bins(pol, f_v, reg_v, va_v, clf_pp_v)
            bin_t, _ = policy_bins(pol, f_t, reg_t, va_t, clf_pp_t, edges=edges)
            bin_v_c = broadcast(bin_v, H)
            bin_t_c = broadcast(bin_t, s_test.shape[1])
            for rho in rhos:
                reserves = fit_policy(s_val, cell_v, bin_v_c, rho)
                m = eval_policy(s_test, cell_t, bin_t_c, reserves, rho)
                m.update({"seed": seed, "policy": pol, "rho": rho})
                rows.append(m)
        print(f"seed {seed} done", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "modular_equiv_by_seed.csv", index=False)

    rng = np.random.default_rng(42)
    summary = []
    for rho in rhos:
        sub = df[df["rho"] == rho]
        for strat in ["classifier-bin", "soft-clf-bin", "gate-bin", "soft-gate-bin"]:
            for base in ["global", "physical-bin"]:
                for metric in ["total_cost", "violation_rate", "shortage", "reserve"]:
                    wide = sub.pivot(index="seed", columns="policy", values=metric)
                    if strat not in wide or base not in wide:
                        continue
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
    sdf.to_csv(out_dir / "modular_equiv_paired_summary.csv", index=False)
    print(sdf.to_string(index=False))
    print()
    print("=== policy means at rho=10 ===")
    print(df[df["rho"] == 10].groupby("policy")[["total_cost", "violation_rate", "reserve", "shortage"]].mean().to_string())
    print("MODULAR_EQUIV_DONE")


if __name__ == "__main__":
    main()
