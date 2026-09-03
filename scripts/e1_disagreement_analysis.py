"""E1: gate-rule disagreement value analysis on train-only boundary-router checkpoints.

Official version (2026-09-03). Compared with the 2026-08-30 pilot, this copy is
frozen in scripts/ for the reproduction package. Multiplicity: the two
soft-signal Spearman tests reported below join the E3 reserve tests
(scripts/uncertainty_binning_reserve.py) in one family of soft-posterior
decision-value tests; BH-FDR is applied across the family at alpha=0.05. All
reported CIs exclude zero before and after correction.

Core question: where the soft gate route disagrees with the deterministic threshold
rule (R in {MPPT=1, pitch=2}), does the gate's choice better explain the *future*
active-power outcome? If yes, disagreement is physical signal (effective control
boundary), not noise.

Per seed (test split):
  - cells: regime_primary in {1,2}, horizon-valid (any valid target step)
  - y_future: mask-weighted mean future power per cell
  - mu_rule[c]: test-set conditional mean of y_future under rule label c
  - mu_gate[c]: test-set conditional mean of y_future under gate route c
  - on disagreement cells: compare |y - mu_gate[g]| vs |y - mu_rule[R]|
  - soft-signal test: Spearman corr between gate P(pitch) and residual
    (y_future - mu_rule[R]) on rule-MPPT cells near the boundary band
Outputs: JSON summary + per-seed CSV, written to --output-dir.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def load_seed(run_dir: Path):
    d = run_dir / "test_metrics"
    pred = np.load(d / "pred.npy", mmap_mode="r")
    target = np.load(d / "target.npy", mmap_mode="r")
    mask = np.load(d / "mask.npy", mmap_mode="r")
    regime = np.load(d / "regime_primary.npy")
    gate = np.load(d / "gate_prob.npy")
    anchor = np.load(d / "anchor_physics.npy")  # [Wspd, Pab_mean, wake, Patv]
    return pred, target, mask, regime, gate, anchor


def cell_stats(pred, target, mask):
    m = mask > 0.5
    cnt = m.sum(axis=1)  # (W, N)
    valid = cnt > 0
    y_future = np.where(valid, (np.where(m, target, 0.0)).sum(axis=1) / np.maximum(cnt, 1), np.nan)
    abs_res = np.where(valid, (np.where(m, np.abs(pred - target), 0.0)).sum(axis=1) / np.maximum(cnt, 1), np.nan)
    # future ramp: mean of last 6 valid-ish minus first 6 (approximation with masks)
    h = target.shape[1]
    first = np.where(m[:, : h // 4], target[:, : h // 4], np.nan)
    last = np.where(m[:, 3 * h // 4 :], target[:, 3 * h // 4 :], np.nan)
    ramp = np.nanmean(last, axis=1) - np.nanmean(first, axis=1)
    return valid, y_future, abs_res, ramp


def analyze_seed(run_dir: Path, rated_wind: float = 10.5, band: float = 1.0):
    pred, target, mask, regime, gate, anchor = load_seed(run_dir)
    valid, y_future, abs_res, ramp = cell_stats(
        np.asarray(pred), np.asarray(target), np.asarray(mask)
    )
    R = regime
    g = gate[..., :3].argmax(axis=-1)  # anchored classes 0/1/2
    p_pitch = gate[..., 2] / np.maximum(gate[..., :3].sum(axis=-1), 1e-9)
    wspd = anchor[..., 0]

    sel = valid & np.isin(R, [1, 2])
    y = y_future[sel]
    Rv = R[sel]
    gv = g[sel]
    wv = wspd[sel]
    res = abs_res[sel]

    mu_rule = {c: np.nanmean(y[Rv == c]) for c in (1, 2)}
    mu_gate = {c: (np.nanmean(y[gv == c]) if (gv == c).any() else np.nanmean(y)) for c in (1, 2)}
    mu_rule_arr = np.array([mu_rule[1], mu_rule[2]])
    mu_gate_arr = np.array([mu_gate[1], mu_gate[2]])

    err_rule = np.abs(y - mu_rule_arr[Rv - 1])
    err_gate = np.abs(y - mu_gate_arr[gv - 1])

    disagree = gv != Rv
    n = int(sel.sum())
    nd = int(disagree.sum())
    out = {
        "n_cells": n,
        "n_disagree": nd,
        "disagree_rate": nd / max(n, 1),
        "mu_rule_mppt": float(mu_rule[1]),
        "mu_rule_pitch": float(mu_rule[2]),
    }
    if nd > 0:
        d = err_gate[disagree] - err_rule[disagree]
        out.update(
            disagree_mean_err_delta=float(np.nanmean(d)),  # <0 => gate fits better
            disagree_frac_gate_better=float(np.nanmean(d < 0)),
            disagree_resid_mean=float(np.nanmean(res[disagree])),
            agree_resid_mean=float(np.nanmean(res[~disagree])),
        )
    # disagreement rate vs distance to rated wind
    dist = np.abs(wv - rated_wind)
    bins = [(0, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 3.0), (3.0, 99.0)]
    curve = []
    for lo, hi in bins:
        s = (dist >= lo) & (dist < hi)
        if s.sum() > 50:
            curve.append(
                {"bin": f"[{lo},{hi})", "rate": float(disagree[s].mean()), "n": int(s.sum())}
            )
    out["disagree_by_dist"] = curve

    # soft-signal: on rule-MPPT cells inside the boundary band, does gate P(pitch)
    # predict the residual relative to the rule-conditional mean?
    band_sel = sel & (R == 1) & (np.abs(wspd - rated_wind) <= band)
    if band_sel.sum() > 200:
        resid_mppt = y_future[band_sel] - mu_rule[1]
        pp = p_pitch[band_sel]
        ok = np.isfinite(resid_mppt) & np.isfinite(pp)
        if ok.sum() > 200:
            from scipy.stats import spearmanr  # may be unavailable; fallback below

            rho, p = spearmanr(pp[ok], resid_mppt[ok])
            out["soft_signal_spearman_rho"] = float(rho)
            out["soft_signal_spearman_p"] = float(p)
            out["soft_signal_n"] = int(ok.sum())
    # gate margin vs residual (all selected cells)
    margin = np.abs(p_pitch - 0.5)[sel]
    ok = np.isfinite(margin) & np.isfinite(res)
    if ok.sum() > 200:
        try:
            from scipy.stats import spearmanr

            rho2, p2 = spearmanr(-margin[ok], res[ok])  # low margin ~ uncertain
            out["uncertainty_resid_rho"] = float(rho2)
            out["uncertainty_resid_p"] = float(p2)
        except Exception:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite-root", required=True)
    ap.add_argument("--run-pattern", default="wtb_bal_align_force_seed{seed}")
    ap.add_argument("--seeds", default="201,202,203,204,205")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--rated-wind", type=float, default=10.5)
    ap.add_argument("--band", type=float, default=1.0)
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for seed in [int(s) for s in args.seeds.split(",")]:
        run_dir = Path(args.suite_root) / args.run_pattern.format(seed=seed)
        r = analyze_seed(run_dir, rated_wind=args.rated_wind, band=args.band)
        r["seed"] = seed
        rows.append(r)
        print(f"seed {seed}: disagree_rate={r['disagree_rate']:.4f} "
              f"err_delta={r.get('disagree_mean_err_delta', float('nan')):.3f} "
              f"frac_gate_better={r.get('disagree_frac_gate_better', float('nan')):.4f}")

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "e1_disagreement_by_seed.csv", index=False)

    # seed-level paired summary with bootstrap CI over seeds
    rng = np.random.default_rng(42)
    summary = {}
    for col in ["disagree_rate", "disagree_mean_err_delta", "disagree_frac_gate_better",
                "disagree_resid_mean", "agree_resid_mean", "soft_signal_spearman_rho",
                "uncertainty_resid_rho"]:
        v = df[col].dropna().to_numpy()
        if v.size == 0:
            continue
        boots = rng.choice(v, size=(20000, v.size), replace=True).mean(axis=1)
        summary[col] = {
            "mean": float(v.mean()),
            "ci_low": float(np.percentile(boots, 2.5)),
            "ci_high": float(np.percentile(boots, 97.5)),
            "n_seeds": int(v.size),
        }
    # disagreement-vs-distance curve averaged over seeds
    curves = {}
    for r in rows:
        for item in r.get("disagree_by_dist", []):
            curves.setdefault(item["bin"], []).append(item["rate"])
    summary["disagree_by_dist_mean"] = {k: float(np.mean(v)) for k, v in curves.items()}

    with open(out_dir / "e1_disagreement_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
