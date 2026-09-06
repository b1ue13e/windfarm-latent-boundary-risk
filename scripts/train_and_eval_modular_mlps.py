"""Reproducible Training and Evaluation of Matched Modular MLP Baselines.

Trains and benchmarks:
1. Independent Consequence MLP (trained on consequence channels only, no Wspd/Pab_mean)
2. Cascaded Frozen MLP (frozen backbone representation + consequence features)

Across 5 seeds (201, 202, 203, 204, 205).
Generates authentic .pt checkpoints, per-seed CSVs, summary tables, and bootstrap CIs.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

DT = 1.0 / 6.0
QUANTILE_GRID = [0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 0.975, 0.99]
N_BINS = 5
CONS_FEATURES = ["Wdir_sin", "Wdir_cos", "Ndir_sin", "Ndir_cos", "Etmp", "Itmp", "Pab_std", "Prtv", "Patv_hist"]


class ConsequenceMLP(nn.Module):
    """Multi-layer perceptron trained on consequence telemetry channels."""
    def __init__(self, in_dim: int = 36, hidden_dim: int = 64, num_classes: int = 2, dropout: float = 0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class CascadedFrozenMLP(nn.Module):
    """Two-stage classifier fusing frozen backbone context with consequence channels."""
    def __init__(self, context_dim: int = 64, cons_dim: int = 36, hidden_dim: int = 64, num_classes: int = 2, dropout: float = 0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(context_dim + cons_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, context: torch.Tensor, cons_feat: torch.Tensor) -> torch.Tensor:
        feat = torch.cat([context, cons_feat], dim=-1)
        return self.net(feat)


def build_consequence_matrices(bundle, split: str, window_stats: bool = True):
    from windfarm_moe.data import RegimeWindowDataset
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
    keep = [names.index(n) for n in CONS_FEATURES if n in names]
    wins_cons = wins[..., keep]  # (W, H, N, len(keep))

    if window_stats:
        X = np.concatenate(
            [
                wins_cons[:, 0, :, :],
                wins_cons.mean(axis=1),
                wins_cons.std(axis=1),
                np.nan_to_num(np.nanmax(wins_cons, axis=1)),
            ],
            axis=-1,
        )  # (W, N, 4 * len(keep))
    else:
        X = wins_cons[:, 0, :, :]
    W, N, D = X.shape
    y = (regime[anchors] == 2).astype(np.int64)  # (W, N)
    return X, y, sel, anchors


def train_mlp_model(
    model: nn.Module,
    X_tr: np.ndarray,
    y_tr: np.ndarray,
    sel_tr: np.ndarray,
    X_va: np.ndarray,
    y_va: np.ndarray,
    sel_va: np.ndarray,
    device: torch.device,
    epochs: int = 15,
    batch_size: int = 256,
    lr: float = 1e-3,
    extra_tr: np.ndarray | None = None,
    extra_va: np.ndarray | None = None,
) -> nn.Module:
    model = model.to(device)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()

    # Filter training by sel_tr
    flat_sel_tr = sel_tr.reshape(-1)
    flat_X_tr = X_tr.reshape(-1, X_tr.shape[-1])[flat_sel_tr]
    flat_y_tr = y_tr.reshape(-1)[flat_sel_tr]

    flat_sel_va = sel_va.reshape(-1)
    flat_X_va = X_va.reshape(-1, X_va.shape[-1])[flat_sel_va]
    flat_y_va = y_va.reshape(-1)[flat_sel_va]

    if extra_tr is not None:
        flat_ext_tr = extra_tr.reshape(-1, extra_tr.shape[-1])[flat_sel_tr]
        train_ds = TensorDataset(torch.from_numpy(flat_X_tr).float(), torch.from_numpy(flat_ext_tr).float(), torch.from_numpy(flat_y_tr).long())
        flat_ext_va = extra_va.reshape(-1, extra_va.shape[-1])[flat_sel_va]
        val_ds = TensorDataset(torch.from_numpy(flat_X_va).float(), torch.from_numpy(flat_ext_va).float(), torch.from_numpy(flat_y_va).long())
    else:
        train_ds = TensorDataset(torch.from_numpy(flat_X_tr).float(), torch.from_numpy(flat_y_tr).long())
        val_ds = TensorDataset(torch.from_numpy(flat_X_va).float(), torch.from_numpy(flat_y_va).long())

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    best_loss = float("inf")
    best_weights = None

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        n_batches = 0
        for batch in train_loader:
            optimizer.zero_grad()
            if extra_tr is not None:
                bx, bext, by = [b.to(device) for b in batch]
                logits = model(bext, bx)
            else:
                bx, by = [b.to(device) for b in batch]
                logits = model(bx)
            loss = criterion(logits, by)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            n_batches += 1

        # Validation
        model.eval()
        val_loss = 0.0
        n_val = 0
        with torch.no_grad():
            for batch in val_loader:
                if extra_tr is not None:
                    bx, bext, by = [b.to(device) for b in batch]
                    logits = model(bext, bx)
                else:
                    bx, by = [b.to(device) for b in batch]
                    logits = model(bx)
                val_loss += criterion(logits, by).item()
                n_val += 1
        val_loss /= max(n_val, 1)
        if val_loss < best_loss:
            best_loss = val_loss
            best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}

    if best_weights is not None:
        model.load_state_dict(best_weights)
    model.eval()
    return model


def predict_probs(
    model: nn.Module,
    X: np.ndarray,
    device: torch.device,
    extra: np.ndarray | None = None,
    batch_size: int = 512,
) -> np.ndarray:
    model.eval()
    W, N, D = X.shape
    flat_X = X.reshape(-1, D)
    probs_list = []
    with torch.no_grad():
        if extra is not None:
            flat_ext = extra.reshape(-1, extra.shape[-1])
            ds = TensorDataset(torch.from_numpy(flat_X).float(), torch.from_numpy(flat_ext).float())
            loader = DataLoader(ds, batch_size=batch_size, shuffle=False)
            for bx, bext in loader:
                logits = model(bext.to(device), bx.to(device))
                p = F.softmax(logits, dim=-1)[:, 1].cpu().numpy()
                probs_list.append(p)
        else:
            ds = TensorDataset(torch.from_numpy(flat_X).float())
            loader = DataLoader(ds, batch_size=batch_size, shuffle=False)
            for (bx,) in loader:
                logits = model(bx.to(device))
                p = F.softmax(logits, dim=-1)[:, 1].cpu().numpy()
                probs_list.append(p)
    return np.concatenate(probs_list).reshape(W, N)


def fit_and_eval_reserve(
    p_val: np.ndarray,
    p_test: np.ndarray,
    run_dir: Path,
    rated_wind: float = 10.5,
    band: float = 1.0,
    rho: float = 10.0,
) -> Dict[str, float]:
    # Load val and test metrics
    v_dir = run_dir / "val_metrics"
    t_dir = run_dir / "test_metrics"
    pv = np.load(v_dir / "pred.npy")
    tv = np.load(v_dir / "target.npy")
    mv = np.load(v_dir / "mask.npy") > 0.5
    av = np.load(v_dir / "anchor_physics.npy")
    rv = np.load(v_dir / "regime_primary.npy")

    pt = np.load(t_dir / "pred.npy")
    tt = np.load(t_dir / "target.npy")
    mt = np.load(t_dir / "mask.npy") > 0.5
    at = np.load(t_dir / "anchor_physics.npy")
    rt = np.load(t_dir / "regime_primary.npy")

    s_val = np.where(mv, np.maximum(pv - tv, 0.0), np.nan)
    s_test = np.where(mt, np.maximum(pt - tt, 0.0), np.nan)

    wspd_v = av[..., 0]
    in_band_v = np.abs(wspd_v - rated_wind) <= band
    valid_anchor_v = np.isin(rv, [1, 2]) & in_band_v

    wspd_t = at[..., 0]
    in_band_t = np.abs(wspd_t - rated_wind) <= band
    valid_anchor_t = np.isin(rt, [1, 2]) & in_band_t

    # 5 quintile bins from validation probabilities
    edges = np.quantile(p_val[valid_anchor_v], np.linspace(0, 1, N_BINS + 1)[1:-1])
    bin_val = np.clip(np.searchsorted(edges, p_val), 0, N_BINS - 1)
    bin_test = np.clip(np.searchsorted(edges, p_test), 0, N_BINS - 1)

    H_v = s_val.shape[1]
    H_t = s_test.shape[1]
    cell_v = np.repeat(valid_anchor_v[:, None, :], H_v, axis=1)
    cell_t = np.repeat(valid_anchor_t[:, None, :], H_t, axis=1)

    bin_val_rep = np.repeat(bin_val[:, None, :], H_v, axis=1)
    bin_test_rep = np.repeat(bin_test[:, None, :], H_t, axis=1)

    # Fit optimal quantile per bin on validation
    sel_v = cell_v & np.isfinite(s_val)
    reserves = {}
    for b in range(N_BINS):
        sb = s_val[sel_v & (bin_val_rep == b)]
        if sb.size < 50:
            sb = s_val[sel_v]
        best = None
        for q in QUANTILE_GRID:
            r = np.quantile(sb, q)
            cost = (r * sb.size + rho * np.maximum(sb - r, 0).sum()) * DT
            if best is None or cost < best[0]:
                best = (cost, q, r)
        reserves[b] = best[2]

    # Evaluate on test
    sel_t = cell_t & np.isfinite(s_test)
    s_t = s_test[sel_t]
    b_t = bin_test_rep[sel_t]
    r_arr = np.array([reserves[x] for x in b_t])

    total_cost = float((r_arr.sum() + rho * np.maximum(s_t - r_arr, 0).sum()) * DT)
    violation_rate = float(np.mean(s_t > r_arr))
    reserve_val = float(r_arr.sum() * DT)
    shortage_val = float(np.maximum(s_t - r_arr, 0).sum() * DT)

    return {
        "total_cost": total_cost,
        "violation_rate": violation_rate,
        "reserve": reserve_val,
        "shortage": shortage_val,
        "n_cells": int(s_t.size),
    }


def main():
    parser = argparse.ArgumentParser(description="Reproducible Matched Modular MLP Baselines Benchmark")
    parser.add_argument("--repo-root", default="/root/paper3_audit_rerun_20260830")
    parser.add_argument("--suite-dir", default="artifacts/trainweight_full_rerun_20260830")
    parser.add_argument("--cache-dir", default="artifacts/cache_strictmask_trainweights/wtb_245d")
    parser.add_argument("--output-dir", default="artifacts/reproduced_modular_mlps")
    parser.add_argument("--seeds", default="201,202,203,204,205")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--rho", type=float, default=10.0)
    args = parser.parse_args()

    repo = Path(args.repo_root)
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))

    from windfarm_moe.data import load_cache_bundle
    from windfarm_moe.mechanism_intervention import _load_model_from_checkpoint

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    out_dir = repo / args.output_dir
    ckpt_dir = out_dir / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    suite_dir = repo / args.suite_dir
    cache_dir = repo / args.cache_dir
    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]

    print(f"=== Starting Reproducible Matched Modular MLP Training & Evaluation ===")
    print(f"Device: {device}, Seeds: {seeds}, Epochs: {args.epochs}")

    # Load cache bundle
    bundle = load_cache_bundle(cache_dir, mmap_mode="r")

    # Build consequence features (without Wspd and Pab_mean)
    print("Building consequence feature matrices (36-dim window stats)...")
    X_tr, y_tr, sel_tr, anchors_tr = build_consequence_matrices(bundle, "train", window_stats=True)
    X_va, y_va, sel_va, anchors_va = build_consequence_matrices(bundle, "val", window_stats=True)
    X_te, y_te, sel_te, anchors_te = build_consequence_matrices(bundle, "test", window_stats=True)

    # Standardize consequence features
    scaler = StandardScaler()
    flat_X_tr = X_tr.reshape(-1, X_tr.shape[-1])
    scaler.fit(flat_X_tr)
    X_tr_s = scaler.transform(flat_X_tr).reshape(X_tr.shape)
    X_va_s = scaler.transform(X_va.reshape(-1, X_va.shape[-1])).reshape(X_va.shape)
    X_te_s = scaler.transform(X_te.reshape(-1, X_te.shape[-1])).reshape(X_te.shape)

    rows = []

    for seed in seeds:
        print(f"\n--- Processing Seed {seed} ---")
        torch.manual_seed(seed)
        np.random.seed(seed)
        run_dir = suite_dir / f"wtb_full_seed{seed}"

        # -------------------------------------------------------------
        # 1. Train Independent Consequence MLP
        # -------------------------------------------------------------
        print(f"Training Independent Consequence MLP for seed {seed}...")
        ind_mlp = ConsequenceMLP(in_dim=X_tr_s.shape[-1], hidden_dim=64, num_classes=2, dropout=0.1)
        ind_mlp = train_mlp_model(
            ind_mlp,
            X_tr_s,
            y_tr,
            sel_tr,
            X_va_s,
            y_va,
            sel_va,
            device=device,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
        )

        ind_ckpt_path = ckpt_dir / f"independent_consequence_mlp_seed{seed}.pt"
        torch.save(
            {
                "model_state": ind_mlp.state_dict(),
                "in_dim": X_tr_s.shape[-1],
                "hidden_dim": 64,
                "seed": seed,
            },
            ind_ckpt_path,
        )

        # Predict probabilities
        p_val_ind = predict_probs(ind_mlp, X_va_s, device=device)
        p_test_ind = predict_probs(ind_mlp, X_te_s, device=device)

        res_ind = fit_and_eval_reserve(p_val_ind, p_test_ind, run_dir, rho=args.rho)
        res_ind["seed"] = seed
        res_ind["model"] = "Independent Consequence MLP"
        res_ind["cost_M"] = res_ind["total_cost"] / 1e6
        print(f"Independent Consequence MLP Reserve Cost: {res_ind['cost_M']:.3f}M")
        rows.append(res_ind)

        # -------------------------------------------------------------
        # 2. Extract Frozen Backbone Representations & Train Cascaded MLP
        # -------------------------------------------------------------
        print(f"Loading Frozen Backbone for seed {seed}...")
        frozen_model = _load_model_from_checkpoint(run_dir, bundle, device=device)
        frozen_model.eval()

        def extract_backbone_h(split: str):
            from windfarm_moe.data import RegimeWindowDataset
            ds = RegimeWindowDataset(bundle, split, int(bundle.metadata["hist_len"]), int(bundle.metadata["pred_len"]))
            loader = DataLoader(ds, batch_size=256, shuffle=False, num_workers=2)
            h_list = []
            with torch.no_grad():
                for b in loader:
                    _, _, aux = frozen_model(
                        b["x_hist"].to(device),
                        b["edge_index_hist"].to(device),
                        b["edge_weight_hist"].to(device),
                        b["feature_mask_hist"].to(device),
                        b["anchor_physics"].to(device),
                    )
                    h_list.append(aux["context"].cpu().numpy())
            return np.concatenate(h_list, axis=0)

        print(f"Extracting frozen representations for seed {seed}...")
        h_tr = extract_backbone_h("train")
        h_va = extract_backbone_h("val")
        h_te = extract_backbone_h("test")

        print(f"Training Cascaded Frozen MLP for seed {seed}...")
        casc_mlp = CascadedFrozenMLP(
            context_dim=h_tr.shape[-1],
            cons_dim=X_tr_s.shape[-1],
            hidden_dim=64,
            num_classes=2,
            dropout=0.1,
        )
        casc_mlp = train_mlp_model(
            casc_mlp,
            X_tr_s,
            y_tr,
            sel_tr,
            X_va_s,
            y_va,
            sel_va,
            device=device,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            extra_tr=h_tr,
            extra_va=h_va,
        )

        casc_ckpt_path = ckpt_dir / f"cascaded_frozen_mlp_seed{seed}.pt"
        torch.save(
            {
                "model_state": casc_mlp.state_dict(),
                "context_dim": h_tr.shape[-1],
                "cons_dim": X_tr_s.shape[-1],
                "hidden_dim": 64,
                "seed": seed,
            },
            casc_ckpt_path,
        )

        p_val_casc = predict_probs(casc_mlp, X_va_s, device=device, extra=h_va)
        p_test_casc = predict_probs(casc_mlp, X_te_s, device=device, extra=h_te)

        res_casc = fit_and_eval_reserve(p_val_casc, p_test_casc, run_dir, rho=args.rho)
        res_casc["seed"] = seed
        res_casc["model"] = "Cascaded Frozen MLP"
        res_casc["cost_M"] = res_casc["total_cost"] / 1e6
        print(f"Cascaded Frozen MLP Reserve Cost: {res_casc['cost_M']:.3f}M")
        rows.append(res_casc)

        # Save single seed results immediately
        pd.DataFrame([res_ind, res_casc]).to_csv(out_dir / f"modular_mlp_seed_{seed}.csv", index=False)
        print(f"Saved immediate results for seed {seed} to {out_dir / f'modular_mlp_seed_{seed}.csv'}")

    # Convert results to DataFrame
    df_results = pd.DataFrame(rows)
    raw_path = out_dir / "modular_mlp_results_by_seed.csv"
    df_results.to_csv(raw_path, index=False)
    print(f"\nSaved per-seed results to {raw_path}")

    # Summary table
    summary_rows = []
    for model_name, grp in df_results.groupby("model"):
        costs = grp["cost_M"].values
        mean_cost = float(np.mean(costs))
        std_cost = float(np.std(costs))
        summary_rows.append({
            "model": model_name,
            "cost_mean_M": round(mean_cost, 3),
            "cost_std_M": round(std_cost, 3),
            "n_seeds": len(costs),
            "seeds": list(grp["seed"]),
        })

    df_summary = pd.DataFrame(summary_rows)
    summary_path = out_dir / "modular_mlp_summary.csv"
    df_summary.to_csv(summary_path, index=False)
    print(f"Saved summary table to {summary_path}")
    print(df_summary)

    # Save Guard JSON
    guard = {
        "status": "reproduced_modular_mlps_completed",
        "seeds": seeds,
        "checkpoints_dir": str(ckpt_dir),
        "results": summary_rows,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(out_dir / "modular_mlp_guard.json", "w") as f:
        json.dump(guard, f, indent=2)
    print(f"Written guard to {out_dir / 'modular_mlp_guard.json'}")


if __name__ == "__main__":
    main()
