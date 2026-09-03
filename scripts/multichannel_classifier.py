"""K2 (Breakthrough B): can a multi-channel classifier reproduce the gate's
signature recovery and fair-degradation robustness?

Decision question: are the two surviving contributions (boundary recoverability
without defining channels; degradation robustness) properties of the MoE
architecture, or of simply *using more channels* than the two-channel rule?

Classifiers compared on the same WTB cache and the same early-window
detection protocol as the fair-degradation audit:

  - logistic-all:   logistic regression on all 11 issue-time channels
  - logistic-cons:  logistic regression on consequence channels only
                    (no Wspd/Pab_mean; Patv/Prtv/Pab_std/temperatures/directions)
  - gbdt-cons:      gradient-boosted trees on the same consequence channels
  - gate-cons:      the MoE gate trained on consequence channels only
                    (signature_full protocol reference)

Degradation: identical delay/noise applied to the Wspd/Pab readings of the
inputs where they exist (for consequence-only classifiers the Wspd/Pab
channels are absent, so degradation can only hit the anchor channels that
exist; we therefore additionally degrade the shared consequence channels'
history for all models in a second pass).

Pre-registered criterion: if a consequence-channel classifier reaches similar
boundary NMI and similar degraded recall as the MoE gate, the MoE architecture
has no mechanism-level increment; the claim must then rest on uncertainty
pricing and joint forecasting alone.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import normalized_mutual_info_score
from sklearn.preprocessing import StandardScaler

from windfarm_moe.anchor_stress import _detection_metrics, _early_pitch_window, _mppt_to_pitch_transitions
from windfarm_moe.data import RegimeWindowDataset, load_cache_bundle

CONS_FEATURES = ["Wdir_sin", "Wdir_cos", "Ndir_sin", "Ndir_cos", "Etmp", "Itmp", "Pab_std", "Prtv", "Patv_hist"]


def build_matrices(bundle, split, cons_only, window_stats):
    ds = RegimeWindowDataset(bundle, split, int(bundle.metadata["hist_len"]), int(bundle.metadata["pred_len"]))
    anchors = ds.anchor_indices
    names = list(bundle.metadata.get("feature_names", []))
    features = np.asarray(bundle.features, dtype=np.float64)
    regime = np.asarray(bundle.regime_primary, dtype=np.int64)
    valid = np.asarray(bundle.regime_primary_valid, dtype=bool)
    sel = np.isin(regime[anchors], [1, 2]) & valid[anchors]
    H = int(bundle.metadata["hist_len"])
    idx = anchors[:, None] - np.arange(H)[None, ::-1]
    wins = features[idx]  # (W, H, N, F)
    wspd_idx = names.index("Wspd")
    pab_idx = names.index("Pab_mean")
    if cons_only:
        keep = [names.index(n) for n in CONS_FEATURES]
        wins = wins[..., keep]
        wspd_idx_kept = -1
    else:
        wspd_idx_kept = wspd_idx
    if window_stats:
        X = np.concatenate(
            [wins[:, 0, :, :],
             wins.mean(axis=1),
             wins.std(axis=1),
             np.nan_to_num(np.nanmax(wins, axis=1))],
            axis=2,
        )
    else:
        X = wins[:, 0, :, :]
    W, N, D = X.shape
    X = X.reshape(W * N, D)
    y = (regime[anchors] == 2).reshape(-1)
    sel = sel.reshape(-1)
    return X, y, sel, anchors, wins, wspd_idx_kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default="artifacts/cache_strictmask_trainweights/wtb_245d")
    ap.add_argument("--output-dir", default="artifacts/multichannel_classifier_20260904")
    ap.add_argument("--rated-wind", type=float, default=10.5)
    ap.add_argument("--band", type=float, default=1.0)
    ap.add_argument("--window-stats", action="store_true")
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = load_cache_bundle(args.cache_dir, mmap_mode="r")

    X_tr, y_tr, sel_tr, anchors_tr, wins_tr, _ = build_matrices(bundle, "train", cons_only=False, window_stats=args.window_stats)
    X_va, y_va, sel_va, anchors_va, wins_va, _ = build_matrices(bundle, "val", cons_only=False, window_stats=args.window_stats)
    X_te, y_te, sel_te, anchors_te, wins_te, _ = build_matrices(bundle, "test", cons_only=False, window_stats=args.window_stats)
    Xc_tr, _, _, _, wins_te_cons, _ = build_matrices(bundle, "test", cons_only=True, window_stats=args.window_stats)
    Xc_tr, _, _, _, _, _ = build_matrices(bundle, "train", cons_only=True, window_stats=args.window_stats)
    Xc_va, _, _, _, _, _ = build_matrices(bundle, "val", cons_only=True, window_stats=args.window_stats)
    Xc_te, _, _, _, wins_te_cons, _ = build_matrices(bundle, "test", cons_only=True, window_stats=args.window_stats)

    regime = np.asarray(bundle.regime_primary, dtype=np.int64)[anchors_te]
    valid = np.asarray(bundle.regime_primary_valid, dtype=bool)[anchors_te]
    transitions = _mppt_to_pitch_transitions(regime, valid)
    early_pitch, support = _early_pitch_window(regime, valid, transitions, early_window_steps=6)

    def flatten_w(w):
        if args.window_stats:
            return np.concatenate(
                [w[:, 0, :, :], w.mean(axis=1), w.std(axis=1), np.nan_to_num(np.nanmax(w, axis=1))],
                axis=2,
            ).reshape(w.shape[0] * w.shape[2], -1)
        return w[:, 0, :, :].reshape(w.shape[0] * w.shape[2], -1)

    results = []
    configs = [
        ("logistic-all", LogisticRegression(max_iter=2000, C=1.0), X_tr, X_va, X_te, wins_te, True),
        ("logistic-cons", LogisticRegression(max_iter=2000, C=1.0), Xc_tr, Xc_va, Xc_te, wins_te_cons, False),
        ("gbdt-cons", HistGradientBoostingClassifier(max_iter=300, random_state=0), Xc_tr, Xc_va, Xc_te, wins_te_cons, False),
    ]
    W_te = wins_te.shape[0]
    N_te = wins_te.shape[2]
    for name, clf, tr, va, te, w_te, has_wspd in configs:
        scaler = StandardScaler().fit(tr)
        Xs_tr = scaler.transform(tr)
        Xs_va = scaler.transform(va)
        Xs_te = scaler.transform(te)
        clf.fit(Xs_tr[sel_tr], y_tr[sel_tr])
        proba_te = clf.predict_proba(Xs_te)[:, 1]
        pred_te = (proba_te >= 0.5).reshape(W_te, N_te)
        nmi = normalized_mutual_info_score(y_te[sel_te], (proba_te[sel_te] >= 0.5).astype(int))
        m = _detection_metrics(pred_te & valid, np.zeros_like(valid, dtype=bool), early_pitch, support)
        results.append({
            "model": name, "condition": "clean", "nmi": float(nmi),
            "gate_recall": m["gate_recall"], "gate_precision": m["gate_precision"],
        })
        print(f"{name}: NMI={nmi:.4f} recall={m['gate_recall']:.4f}", flush=True)

        names_full = list(bundle.metadata.get("feature_names", []))
        wspd_idx = names_full.index("Wspd")
        pab_idx = names_full.index("Pab_mean")
        if has_wspd:
            for delay, noise, label in [(6, None, "delay6"), (0, (1.0, 2.0), "noise_strong")]:
                rng = np.random.default_rng(1729 + delay * 7 + (0 if noise is None else 100))
                w = w_te.copy()
                wspd_col = w[:, 0, :, wspd_idx]
                pab_col = w[:, 0, :, pab_idx]
                if delay > 0:
                    wspd_col = np.concatenate([wspd_col[:delay], wspd_col[:-delay]], axis=0)
                    pab_col = np.concatenate([pab_col[:delay], pab_col[:-delay]], axis=0)
                if noise is not None:
                    wspd_col = wspd_col + rng.normal(0.0, float(noise[0]), size=wspd_col.shape)
                    pab_col = pab_col + rng.normal(0.0, float(noise[1]), size=pab_col.shape)
                w[:, 0, :, wspd_idx] = wspd_col
                w[:, 0, :, pab_idx] = pab_col
                Xd = flatten_w(w)
                proba_d = clf.predict_proba(scaler.transform(Xd))[:, 1]
                pred_d = (proba_d >= 0.5).reshape(W_te, N_te)
                m = _detection_metrics(pred_d & valid, np.zeros_like(valid, dtype=bool), early_pitch, support)
                results.append({"model": name, "condition": label, "nmi": float("nan"),
                                "gate_recall": m["gate_recall"], "gate_precision": m["gate_precision"]})
                print(f"  {label}: recall={m['gate_recall']:.4f}", flush=True)
        else:
            for delay, noise, label in [(6, None, "delay6"), (0, (0.5, 1.0), "noise_shared")]:
                rng = np.random.default_rng(1729 + delay * 7 + (0 if noise is None else 200))
                w = w_te.copy()
                last = w[:, 0, :, :]
                if delay > 0:
                    last = np.concatenate([last[:delay], last[:-delay]], axis=0)
                if noise is not None:
                    last = last + rng.normal(0.0, float(noise[0]), size=last.shape)
                w[:, 0, :, :] = last
                Xd = flatten_w(w)
                proba_d = clf.predict_proba(scaler.transform(Xd))[:, 1]
                pred_d = (proba_d >= 0.5).reshape(W_te, N_te)
                m = _detection_metrics(pred_d & valid, np.zeros_like(valid, dtype=bool), early_pitch, support)
                results.append({"model": name, "condition": label, "nmi": float("nan"),
                                "gate_recall": m["gate_recall"], "gate_precision": m["gate_precision"]})
                print(f"  {label}: recall={m['gate_recall']:.4f}", flush=True)

    df = pd.DataFrame(results)
    df.to_csv(out_dir / "multichannel_classifier_results.csv", index=False)
    print()
    print(df.to_string(index=False))
    print("MULTICHANNEL_CLASSIFIER_DONE")


if __name__ == "__main__":
    main()
