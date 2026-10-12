"""EXP-01: External-Farm Matched Direct-Quantile & No-Graph Control Benchmark

Scientific Question:
    On external wind farms (Penmanshiel 14-turb, Kelmarsh 6-turb), is a local
    wind-speed binned quantile baseline without spatio-temporal graph interaction
    already sufficient for reserve screening? Does cross-farm transferred representation
    still lack decision gain relative to this local conditional baseline?

Matched Information Set:
    Strictly restricted to arrival-time local SCADA features (local wind speed, active power,
    ambient temperature). Blade pitch is completely withheld at test time.

Baselines:
    1. Site-Local Wspd-Bins (10-bin local wind-speed conditional quantile; Primary Baseline)
    2. No-Graph Architectural Control (single-turbine MLP with spatial graph completely severed)

Challengers:
    3. Transferred STGQ-Modular (from WTB; Primary Challenger at h=6)
    4. Fine-tuned STGQ-Modular (locally fine-tuned on external farm)

Estimands & Multiple Comparisons Protocol:
    Primary Endpoint:
        Paired difference Delta PSREI(h=6) = C_transferred - C_local_wspd on each farm separately.
    Secondary / Exploratory Endpoints:
        Delta PSREI at h=1; Fine-tuned and No-Graph controls; Delta V(h=1, h=6).
        No family-wise error rate pooling across sites or horizons.

Uncertainty:
    Site-level daily cluster Block Bootstrap (B=2000).

Target Artifact:
    artifacts/external_matched_control_benchmark.csv
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
from torch.utils.data import DataLoader, TensorDataset

# Execution constants
RHO = 10.0
TAU = 1.0 - 1.0 / RHO  # 0.90
DT = 1.0 / 6.0         # 10 minutes = 1/6 hour
N_WSPD_BINS = 10
N_GATE_BINS = 5
N_BOOTSTRAP = 2000
BLOCK_SIZE = 144       # 144 steps = 1 day

# Seed list
SEEDS = [201, 202, 203, 204, 205]
HORIZONS = [(0, "h=1"), (5, "h=6")]

# No-Graph Architectural Control
class NoGraphQuantileMLP(nn.Module):
    """Single-turbine architectural control predicting residual quantile directly.
    
    Severed from spatial graph interactions: each turbine is processed independently.
    Input features: [Wspd, Patv, Etmp, Itmp, Prtv] (pitch Pab completely withheld).
    """
    def __init__(self, in_features: int = 5, hidden_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_features, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.05),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 1),
            nn.ReLU(),  # Reserves are strictly non-negative
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def pinball_loss_tensor(pred_r: torch.Tensor, target_s: torch.Tensor, tau: float = 0.90) -> torch.Tensor:
    u = target_s - pred_r
    return torch.maximum(tau * u, (tau - 1.0) * u).mean()


def load_split_data(cache_dir: Path, run_dir: Path, split: str) -> Dict[str, np.ndarray]:
    """Loads a model prediction bundle and local arrival-time covariates."""
    d = run_dir / f"{split}_metrics"
    pred = np.load(d / "pred.npy")          # (T, 24, N)
    target = np.load(d / "target.npy")      # (T, 24, N)
    mask = np.load(d / "mask.npy") > 0.5    # (T, 24, N)
    anc = np.load(d / "anchor_physics.npy") # (T, N, 4): [Wspd, Pab, Etmp/Itmp, Patv]
    gate = np.load(d / "gate_prob.npy") if (d / "gate_prob.npy").exists() else None
    t_idx = np.load(d / "anchor_index.npy") if (d / "anchor_index.npy").exists() else np.arange(pred.shape[0])

    # Strictly withhold pitch at test time.
    anc_withheld = anc.copy()
    anc_withheld[..., 1] = 0.0

    return {
        "pred": pred,
        "target": target,
        "mask": mask,
        "anchor": anc_withheld,
        "gate": gate,
        "time": t_idx,
    }


def load_frozen_site_forecast(cache_dir: Path, run_dir: Path, split: str) -> Dict[str, np.ndarray]:
    """Load independent site forecast and reconstruct target from canonical cache.

    The point forecast comes from an external-wind ``external_wind_full_seed*``
    run, never the transferred challenger directory. Realized targets and
    validity masks are reconstructed from the canonical site cache using the
    run's anchor indices, avoiding incompatible run-directory target files.
    """
    d = run_dir / f"{split}_metrics"
    pred = np.load(d / "pred.npy")
    anchors = np.load(d / "anchor_index.npy") if (d / "anchor_index.npy").exists() else None
    if anchors is None:
        start, end = json.loads((cache_dir / "metadata.json").read_text(encoding="utf-8"))["split_bounds"][split]
        hist_len, pred_len = 36, pred.shape[1]
        anchors = np.arange(start + hist_len - 1, end - pred_len - 1, dtype=np.int64)
    cache_target = np.load(cache_dir / "target.npy", mmap_mode="r")
    cache_mask = np.load(cache_dir / "target_mask.npy", mmap_mode="r") > 0.5
    target = np.stack([np.asarray(cache_target[a + 1:a + 1 + pred.shape[1]]) for a in anchors], axis=0)
    mask = np.stack([np.asarray(cache_mask[a + 1:a + 1 + pred.shape[1]]) for a in anchors], axis=0)
    if target.shape != pred.shape:
        raise ValueError(f"Frozen forecast/cache target shape mismatch: {pred.shape} vs {target.shape}")
    return {"pred": pred, "target": target, "mask": mask, "time": anchors}


def fit_wspd_bins(wspd_val: np.ndarray, s_val: np.ndarray, mask_val: np.ndarray, n_bins: int = 10, tau: float = 0.90) -> Tuple[np.ndarray, np.ndarray]:
    """Fits 10-bin local wind-speed conditional quantile."""
    valid = mask_val & np.isfinite(wspd_val) & np.isfinite(s_val)
    w_valid = wspd_val[valid]
    s_valid = s_val[valid]

    # Compute quantile bin edges
    quantiles = np.linspace(0.0, 1.0, n_bins + 1)[1:-1]
    edges = np.quantile(w_valid, quantiles)
    edges = np.unique(edges)  # prevent duplicate edges in low variance
    if len(edges) < 2:
        edges = np.linspace(w_valid.min(), w_valid.max(), n_bins + 1)[1:-1]

    bin_assignments = np.digitize(w_valid, edges)
    unique_bins = np.arange(len(edges) + 1)
    reserves_per_bin = np.zeros(len(unique_bins), dtype=np.float64)
    global_reserve = float(np.quantile(s_valid, tau)) if len(s_valid) > 0 else 50.0

    for b in unique_bins:
        sb = s_valid[bin_assignments == b]
        if len(sb) >= 30:
            reserves_per_bin[b] = float(np.quantile(sb, tau))
        else:
            reserves_per_bin[b] = global_reserve

    return edges, reserves_per_bin


def apply_wspd_bins(wspd_test: np.ndarray, edges: np.ndarray, reserves_per_bin: np.ndarray) -> np.ndarray:
    """Applies fitted wind-speed bins to test set."""
    bin_assignments = np.digitize(wspd_test, edges)
    bin_assignments = np.clip(bin_assignments, 0, len(reserves_per_bin) - 1)
    return reserves_per_bin[bin_assignments]


def fit_and_apply_gate_bins(
    gate_val: np.ndarray,
    s_val: np.ndarray,
    mask_val: np.ndarray,
    gate_test: np.ndarray,
    n_bins: int = 5,
    tau: float = 0.90,
) -> np.ndarray:
    """Fits STGQ modular state-conditional quantile on validation and applies to test."""
    p_pitch_val = gate_val[..., 2] if gate_val.ndim == 3 else gate_val
    p_pitch_test = gate_test[..., 2] if gate_test.ndim == 3 else gate_test

    valid = mask_val & np.isfinite(p_pitch_val) & np.isfinite(s_val)
    pv_valid = p_pitch_val[valid]
    sv_valid = s_val[valid]

    quantiles = np.linspace(0.0, 1.0, n_bins + 1)[1:-1]
    edges = np.quantile(pv_valid, quantiles) if len(pv_valid) > 0 else np.linspace(0, 1, n_bins + 1)[1:-1]
    edges = np.unique(edges)
    if len(edges) < 2:
        edges = np.linspace(0.0, 1.0, n_bins + 1)[1:-1]

    bin_v = np.digitize(pv_valid, edges)
    reserves = np.zeros(len(edges) + 1, dtype=np.float64)
    global_r = float(np.quantile(sv_valid, tau)) if len(sv_valid) > 0 else 50.0

    for b in range(len(edges) + 1):
        sb = sv_valid[bin_v == b]
        reserves[b] = float(np.quantile(sb, tau)) if len(sb) >= 30 else global_r

    bin_t = np.digitize(p_pitch_test, edges)
    bin_t = np.clip(bin_t, 0, len(reserves) - 1)
    return reserves[bin_t]


def train_no_graph_mlp(
    anc_val: np.ndarray,
    s_val: np.ndarray,
    mask_val: np.ndarray,
    anc_test: np.ndarray,
    device: torch.device,
    seed: int = 201,
    epochs: int = 10,
    lr: float = 1e-3,
    batch_size: int = 256,
) -> np.ndarray:
    """Trains the No-Graph Architectural Control on local turbine features."""
    torch.manual_seed(seed)
    np.random.seed(seed)

    # Input features: [Wspd, Temp, Patv, Wspd^2, Patv_norm] (pitch completely withheld)
    def extract_features(anc: np.ndarray) -> np.ndarray:
        wspd = np.nan_to_num(anc[..., 0:1], nan=0.0)
        temp = np.nan_to_num(anc[..., 2:3], nan=0.0)
        patv = np.nan_to_num(anc[..., 3:4], nan=0.0)
        w_sq = wspd ** 2
        p_ratio = np.clip(patv / 2000.0, 0.0, 1.5)
        return np.concatenate([wspd, temp, patv, w_sq, p_ratio], axis=-1)

    feats_val = extract_features(anc_val)   # (T_val, N, 5)
    feats_test = extract_features(anc_test) # (T_test, N, 5)

    T_val = feats_val.shape[0]
    split_idx = int(T_val * 0.70)

    # 70/30 chronological split on validation set
    valid_mask = mask_val & np.isfinite(s_val) & np.all(np.isfinite(feats_val), axis=-1)
    
    x_tr_all = feats_val[:split_idx]
    y_tr_all = s_val[:split_idx]
    m_tr_all = valid_mask[:split_idx]

    x_va_all = feats_val[split_idx:]
    y_va_all = s_val[split_idx:]
    m_va_all = valid_mask[split_idx:]

    X_train_flat = x_tr_all[m_tr_all]
    y_train_flat = y_tr_all[m_tr_all]
    X_val_flat = x_va_all[m_va_all]
    y_val_flat = y_va_all[m_va_all]

    if len(X_train_flat) == 0:
        # Fallback to simple global quantile if no training samples
        q90 = float(np.quantile(s_val[valid_mask], TAU)) if np.any(valid_mask) else 50.0
        return np.full(anc_test.shape[:2], q90, dtype=np.float64)

    # Feature normalization
    mean = np.mean(X_train_flat, axis=0, keepdims=True)
    std = np.std(X_train_flat, axis=0, keepdims=True) + 1e-6

    X_tr_norm = (X_train_flat - mean) / std
    X_va_norm = (X_val_flat - mean) / std if len(X_val_flat) > 0 else X_tr_norm

    ds_tr = TensorDataset(torch.tensor(X_tr_norm, dtype=torch.float32), torch.tensor(y_train_flat, dtype=torch.float32))
    loader_tr = DataLoader(ds_tr, batch_size=batch_size, shuffle=True)

    # CPU or GPU model
    model = NoGraphQuantileMLP(in_features=5, hidden_dim=64).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)

    best_loss = float("inf")
    best_weights = None

    for epoch in range(epochs):
        model.train()
        for batch_x, batch_y in loader_tr:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)
            pred_r = model(batch_x)
            loss = pinball_loss_tensor(pred_r, batch_y, tau=TAU)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        # Validation loss
        if len(X_val_flat) > 0:
            model.eval()
            with torch.no_grad():
                vx = torch.tensor(X_va_norm, dtype=torch.float32).to(device)
                vy = torch.tensor(y_val_flat, dtype=torch.float32).to(device)
                v_loss = pinball_loss_tensor(model(vx), vy, tau=TAU).item()
                if v_loss < best_loss:
                    best_loss = v_loss
                    best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}

    # Load best weights if available
    if best_weights is not None:
        model.load_state_dict(best_weights)
    model.eval()

    # Predict test
    orig_shape = feats_test.shape[:2]
    X_te_flat = feats_test.reshape(-1, 5)
    X_te_norm = (X_te_flat - mean) / std

    with torch.no_grad():
        te_x_t = torch.tensor(X_te_norm, dtype=torch.float32).to(device)
        pred_reserves = model(te_x_t).cpu().numpy().reshape(orig_shape)

    return pred_reserves


def compute_decision_metrics(s: np.ndarray, r: np.ndarray, mask: np.ndarray) -> Dict[str, float]:
    """Computes reserve procurement, shortage exposure, PSREI, and violation rate."""
    valid = mask & np.isfinite(s) & np.isfinite(r)
    s_v = s[valid]
    r_v = r[valid]

    procurement = float(np.sum(r_v) * DT)
    shortage = float(np.sum(np.maximum(s_v - r_v, 0.0)) * DT)
    total_cost = float((np.sum(r_v) + RHO * np.sum(np.maximum(s_v - r_v, 0.0))) * DT)
    violation_rate = float(np.mean(s_v > r_v) * 100.0) if len(s_v) > 0 else 0.0
    n_cells = int(np.sum(valid))

    return {
        "psrei_kwh": total_cost,
        "reserve_kwh": procurement,
        "shortage_kwh": shortage,
        "violation_rate_pct": violation_rate,
        "n_cells": n_cells,
    }


def block_bootstrap_paired(
    s: np.ndarray,
    reserves_map: Dict[str, np.ndarray],
    mask: np.ndarray,
    time_indices: np.ndarray,
    ref_baseline: str = "Site-Local Wspd-Bins",
    n_boot: int = 2000,
    block_size: int = 144,
    seed: int = 42,
) -> Dict[str, Dict[str, Any]]:
    """Performs site-level daily cluster Block Bootstrap for paired differences."""
    rng = np.random.default_rng(seed)
    unique_times = np.unique(time_indices)
    n_times = len(unique_times)
    n_blocks = max(1, int(np.ceil(n_times / block_size)))

    time_to_block = {t: idx // block_size for idx, t in enumerate(unique_times)}
    sample_block_ids = np.array([time_to_block[t] for t in time_indices], dtype=np.int64)

    valid = mask & np.isfinite(s)
    models = list(reserves_map.keys())

    # Pre-aggregate cost and violations per block
    block_costs = {}
    block_viols = {}
    block_counts = np.bincount(sample_block_ids, weights=valid.sum(axis=-1), minlength=n_blocks)[:n_blocks]

    for m in models:
        r = reserves_map[m]
        sh = np.maximum(s - r, 0.0)
        c = (r + RHO * sh) * DT
        c_valid = np.where(valid, c, 0.0).sum(axis=-1)
        v_valid = np.where(valid, (s > r).astype(float), 0.0).sum(axis=-1)

        block_costs[m] = np.bincount(sample_block_ids, weights=c_valid, minlength=n_blocks)[:n_blocks]
        block_viols[m] = np.bincount(sample_block_ids, weights=v_valid, minlength=n_blocks)[:n_blocks]

    # Block bootstrap resampling
    chosen_blocks = rng.integers(0, n_blocks, size=(n_boot, n_blocks))
    boot_counts = block_counts[chosen_blocks].sum(axis=1)

    boot_costs = {}
    boot_viols = {}
    for m in models:
        boot_costs[m] = block_costs[m][chosen_blocks].sum(axis=1)
        boot_viols[m] = (block_viols[m][chosen_blocks].sum(axis=1) / np.maximum(boot_counts, 1.0)) * 100.0

    ref_cost = boot_costs[ref_baseline]
    ref_viol = boot_viols[ref_baseline]

    results = {}
    for m in models:
        c_mean = float(np.mean(boot_costs[m]))
        c_ci = [float(np.quantile(boot_costs[m], 0.025)), float(np.quantile(boot_costs[m], 0.975))]

        delta_c = boot_costs[m] - ref_cost
        delta_c_mean = float(np.mean(delta_c))
        delta_c_ci = [float(np.quantile(delta_c, 0.025)), float(np.quantile(delta_c, 0.975))]
        p_val_cost = float(np.mean(delta_c <= 0.0)) if m != ref_baseline else 1.0

        delta_v = boot_viols[m] - ref_viol
        delta_v_mean = float(np.mean(delta_v))
        delta_v_ci = [float(np.quantile(delta_v, 0.025)), float(np.quantile(delta_v, 0.975))]

        results[m] = {
            "mean_psrei": c_mean,
            "psrei_ci_95": c_ci,
            "delta_psrei_mean": delta_c_mean,
            "delta_psrei_ci_95": delta_c_ci,
            "p_val_delta_psrei": p_val_cost,
            "delta_viol_mean": delta_v_mean,
            "delta_viol_ci_95": delta_v_ci,
        }

    return results


def run_farm_evaluation(
    farm_name: str,
    farm_id: str,
    cache_dir: Path,
    transferred_pattern: str,
    finetuned_pattern: str,
    frozen_pattern: str,
    device: torch.device,
    seeds: List[int] = SEEDS,
    horizons: List[Tuple[int, str]] = HORIZONS,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Evaluates all 4 models across seeds and horizons for a single farm."""
    print(f"\n=======================================================", flush=True)
    print(f"  Starting Evaluation for {farm_name} ({farm_id})", flush=True)
    print(f"=======================================================", flush=True)

    # 1. Hard stopping check on wind speed missing rate
    feat_mask = np.load(cache_dir / "feature_mask.npy")
    wspd_missing = 1.0 - float(np.mean(feat_mask[..., 0] > 0))
    print(f"Local wind speed missingness: {wspd_missing*100:.2f}%", flush=True)
    if wspd_missing > 0.20:
        raise RuntimeError(f"HARD STOP TRIGGERED: Missing rate {wspd_missing*100:.2f}% exceeds 20% limit for {farm_name}!")
    print(f"Hard stop check PASSED (<= 20%).", flush=True)

    # Cache metadata and dimensions
    meta = json.loads((cache_dir / "metadata.json").read_text(encoding="utf-8"))
    n_turbines = feat_mask.shape[1]
    print(f"Number of turbines: {n_turbines}", flush=True)

    # Load canonical cache metadata; the control's fitted quantile model uses the validation split below.
    split_bounds = meta.get("split_bounds", {"train": [0, 25920], "val": [25920, 30240], "test": [30240, 35280]})
    tr_lo, tr_hi = split_bounds["train"]
    va_lo, va_hi = split_bounds["val"]
    te_lo, te_hi = split_bounds["test"]

    features_all = np.load(cache_dir / "features.npy")
    physics_all = np.load(cache_dir / "physics.npy") if (cache_dir / "physics.npy").exists() else None
    target_all = np.load(cache_dir / "target.npy")
    t_mask_all = np.load(cache_dir / "target_mask.npy") > 0.5

    # Prepare training split anchor physics [Wspd, Pab, Temp, Patv]
    # Pitch is strictly withheld: Pab channel zeroed out
    anc_tr = physics_all[tr_lo:tr_hi].copy() if physics_all is not None else np.zeros((tr_hi - tr_lo, n_turbines, 4), dtype=np.float32)
    anc_tr[..., 1] = 0.0 # Withhold pitch
    target_tr = target_all[tr_lo:tr_hi]
    mask_tr = t_mask_all[tr_lo:tr_hi]

    # Approximate canonical point forecast for train split to form shortfall target
    # Train target mean / persistence shortfall
    s_tr = np.maximum(target_tr.mean(axis=0, keepdims=True) - target_tr, 0.0)

    detailed_records = []
    summary_stats = {}

    for lead_step, h_label in horizons:
        print(f"\n-------------------- Horizon {h_label} (step {lead_step}) --------------------", flush=True)
        
        for seed in seeds:
            t0 = time.time()
            trans_dir = Path(transferred_pattern.format(seed=seed))
            fine_dir = Path(finetuned_pattern.format(seed=seed))
            frozen_run_dir = Path(frozen_pattern.format(seed=seed))

            if not trans_dir.exists() or not fine_dir.exists() or not frozen_run_dir.exists():
                print(f"Warning: Directory missing for seed {seed}, skipping: {trans_dir}, {fine_dir}, or frozen {frozen_run_dir}")
                continue

            # Load validation and test bundles for transferred and fine-tuned models
            trans_val = load_split_data(cache_dir, trans_dir, "val")
            trans_test = load_split_data(cache_dir, trans_dir, "test")
            fine_val = load_split_data(cache_dir, fine_dir, "val")
            fine_test = load_split_data(cache_dir, fine_dir, "test")

            # Shared frozen site-specific point forecast and shortfall target.
            # This MUST come from the independent external_wind_full run, never
            # from the transferred challenger prediction.
            frozen_val = load_frozen_site_forecast(cache_dir, frozen_run_dir, "val")
            frozen_test = load_frozen_site_forecast(cache_dir, frozen_run_dir, "test")
            if frozen_val["pred"].shape != trans_val["pred"].shape:
                raise ValueError(f"Frozen/Transferred val shape mismatch: {frozen_val['pred'].shape} vs {trans_val['pred'].shape}")
            if frozen_test["pred"].shape != trans_test["pred"].shape:
                raise ValueError(f"Frozen/Transferred test shape mismatch: {frozen_test['pred'].shape} vs {trans_test['pred'].shape}")
            if not np.array_equal(frozen_val["time"], trans_val["time"]):
                raise ValueError("Frozen and transferred validation anchor indices differ")
            if not np.array_equal(frozen_test["time"], trans_test["time"]):
                raise ValueError("Frozen and transferred test anchor indices differ")

            frozen_pred_val_h = frozen_val["pred"][:, lead_step, :]
            frozen_pred_test_h = frozen_test["pred"][:, lead_step, :]
            target_val_h = frozen_val["target"][:, lead_step, :]
            target_test_h = frozen_test["target"][:, lead_step, :]
            mask_val_h = frozen_val["mask"][:, lead_step, :]
            mask_test_h = frozen_test["mask"][:, lead_step, :]
            s_val_h = np.maximum(frozen_pred_val_h - target_val_h, 0.0)
            s_test_h = np.maximum(frozen_pred_test_h - target_test_h, 0.0)

            # Local wind speed (Wspd) in anchor physics [channel 0]
            wspd_val = trans_val["anchor"][..., 0]
            wspd_test = trans_test["anchor"][..., 0]

            # -------------------------------------------------------------
            # Baseline 1: Site-Local Wspd-Bins (Primary Baseline)
            # -------------------------------------------------------------
            w_edges, w_reserves = fit_wspd_bins(wspd_val, s_val_h, mask_val_h, n_bins=N_WSPD_BINS, tau=TAU)
            r_wspd_bins = apply_wspd_bins(wspd_test, w_edges, w_reserves)

            # -------------------------------------------------------------
            # Baseline 2: No-Graph Architectural Control (Secondary Baseline)
            # -------------------------------------------------------------
            r_nograph_mlp = train_no_graph_mlp(
                anc_val=trans_val["anchor"],
                s_val=s_val_h,
                mask_val=mask_val_h,
                anc_test=trans_test["anchor"],
                device=device,
                seed=seed,
                epochs=10,
                lr=1e-3,
                batch_size=256,
            )

            # -------------------------------------------------------------
            # Challenger 1: Transferred STGQ-Modular (from WTB)
            # -------------------------------------------------------------
            r_trans_stgq = fit_and_apply_gate_bins(
                gate_val=trans_val["gate"],
                s_val=s_val_h,
                mask_val=mask_val_h,
                gate_test=trans_test["gate"],
                n_bins=N_GATE_BINS,
                tau=TAU,
            )

            # -------------------------------------------------------------
            # Challenger 2: Fine-tuned STGQ-Modular (locally trained)
            # -------------------------------------------------------------
            r_fine_stgq = fit_and_apply_gate_bins(
                gate_val=fine_val["gate"],
                s_val=s_val_h,
                mask_val=mask_val_h,
                gate_test=fine_test["gate"],
                n_bins=N_GATE_BINS,
                tau=TAU,
            )

            reserves_map = {
                "Site-Local Wspd-Bins": r_wspd_bins,
                "No-Graph Architectural Control": r_nograph_mlp,
                "Transferred STGQ-Modular": r_trans_stgq,
                "Fine-tuned STGQ-Modular": r_fine_stgq,
            }

            # Decision metrics
            metrics = {}
            for m_name, r_arr in reserves_map.items():
                m_dict = compute_decision_metrics(s_test_h, r_arr, mask_test_h)
                metrics[m_name] = m_dict

            # Block bootstrap for paired difference (vs Site-Local Wspd-Bins)
            boot_res = block_bootstrap_paired(
                s=s_test_h,
                reserves_map=reserves_map,
                mask=mask_test_h,
                time_indices=trans_test["time"],
                ref_baseline="Site-Local Wspd-Bins",
                n_boot=N_BOOTSTRAP,
                block_size=BLOCK_SIZE,
                seed=seed,
            )

            elapsed = time.time() - t0
            print(
                f"Seed {seed} ({h_label}) [{elapsed:.1f}s]: "
                f"Wspd-Bins PSREI={metrics['Site-Local Wspd-Bins']['psrei_kwh']:,.0f} kWh | "
                f"Transferred Delta={boot_res['Transferred STGQ-Modular']['delta_psrei_mean']:+,.0f} kWh (p={boot_res['Transferred STGQ-Modular']['p_val_delta_psrei']:.3f}) | "
                f"No-Graph Delta={boot_res['No-Graph Architectural Control']['delta_psrei_mean']:+,.0f} kWh",
                flush=True,
            )

            # Assemble row records
            for m_name in reserves_map.keys():
                m_eval = metrics[m_name]
                b_eval = boot_res[m_name]

                # Endpoint hierarchy: Primary endpoint is strictly h=6 Transferred vs Wspd-Bins
                if m_name == "Site-Local Wspd-Bins":
                    ep_type = "reference_baseline"
                elif h_label == "h=6" and m_name == "Transferred STGQ-Modular":
                    ep_type = "primary_endpoint"
                else:
                    ep_type = "secondary_endpoint"

                record = {
                    "farm": farm_name,
                    "farm_id": farm_id,
                    "num_turbines": n_turbines,
                    "seed": seed,
                    "horizon": h_label,
                    "lead_step": lead_step,
                    "model": m_name,
                    "endpoint_type": ep_type,
                    "model_category": "primary_baseline" if m_name == "Site-Local Wspd-Bins" else ("secondary_baseline" if "No-Graph" in m_name else "tested_challenger"),
                    "target_source": "external_site_frozen_point_forecast_external_wind_full", 
                    "target_source_seed": seed,
                    "psrei_kwh": m_eval["psrei_kwh"],
                    "psrei_ci_lower": b_eval["psrei_ci_95"][0],
                    "psrei_ci_upper": b_eval["psrei_ci_95"][1],
                    "reserve_kwh": m_eval["reserve_kwh"],
                    "shortage_kwh": m_eval["shortage_kwh"],
                    "violation_rate_pct": m_eval["violation_rate_pct"],
                    "delta_psrei_mean_kwh": b_eval["delta_psrei_mean"],
                    "delta_psrei_ci_lower": b_eval["delta_psrei_ci_95"][0],
                    "delta_psrei_ci_upper": b_eval["delta_psrei_ci_95"][1],
                    "p_val_delta_psrei": b_eval["p_val_delta_psrei"],
                    "delta_viol_pct": b_eval["delta_viol_mean"],
                    "delta_viol_ci_lower": b_eval["delta_viol_ci_95"][0],
                    "delta_viol_ci_upper": b_eval["delta_viol_ci_95"][1],
                    "n_evaluated_cells": m_eval["n_cells"],
                }
                detailed_records.append(record)

    return detailed_records, summary_stats


def main():
    parser = argparse.ArgumentParser(description="Run EXP-01 Matched Direct-Quantile Benchmark")
    parser.add_argument("--output-csv", default="artifacts/external_matched_control_benchmark.csv")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    device = torch.device(args.device)
    print(f"Executing EXP-01 on device: {device}", flush=True)

    farms_config = [
        {
            "farm_name": "Penmanshiel",
            "farm_id": "penmanshiel",
            "cache_dir": Path("artifacts/cache_signature_penmanshiel/external_wind_penmanshiel_obs_window_canonical"),
            "transferred_pattern": "artifacts/signature_gate_farms_runs_20260903/penmanshiel/canonical/wtb_bal_align_force_seed{seed}",
            "finetuned_pattern": "artifacts/external_wind_runs/penmanshiel/chronological/external_wind_bal_align_force_seed{seed}",
            "frozen_pattern": "artifacts/external_wind_runs/penmanshiel/chronological/external_wind_full_seed{seed}",
        },
        {
            "farm_name": "Kelmarsh",
            "farm_id": "kelmarsh",
            "cache_dir": Path("artifacts/cache_signature_kelmarsh/external_wind_kelmarsh_obs_window_canonical"),
            "transferred_pattern": "artifacts/signature_gate_farms_runs_20260903/kelmarsh/canonical/wtb_bal_align_force_seed{seed}",
            "finetuned_pattern": "artifacts/external_wind_runs/kelmarsh/chronological/external_wind_bal_align_force_seed{seed}",
            "frozen_pattern": "artifacts/external_wind_runs/kelmarsh/chronological/external_wind_full_seed{seed}",
        },
    ]

    all_records = []
    for fcfg in farms_config:
        records, _ = run_farm_evaluation(
            farm_name=fcfg["farm_name"],
            farm_id=fcfg["farm_id"],
            cache_dir=fcfg["cache_dir"],
            transferred_pattern=fcfg["transferred_pattern"],
            finetuned_pattern=fcfg["finetuned_pattern"],
            frozen_pattern=fcfg["frozen_pattern"],
            device=device,
            seeds=SEEDS,
            horizons=HORIZONS,
        )
        all_records.extend(records)

    df = pd.DataFrame(all_records)
    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"\n=======================================================", flush=True)
    print(f"Benchmark results successfully written to: {out_path}", flush=True)
    print(f"Total rows: {len(df)}", flush=True)

    # Print Synthesis Table per Farm and Horizon with Seed Disaggregation and Robust Statistics
    print("\n==================== SYNTHESIS BENCHMARK TABLE ====================", flush=True)
    print("NOTE: Per-seed bootstrap probabilities and CIs are NOT arithmetically averaged.")
    print("Reporting mean, robust median, seed-level dispersion, and individual seed outcomes.")

    for farm in ["Penmanshiel", "Kelmarsh"]:
        print(f"\n--- Wind Farm: {farm} ---")
        f_df = df[df["farm"] == farm]
        print(f"{'Horizon':<8} {'Model':<28} {'Mean PSREI':<15} {'Mean Viol':<10} {'Mean Delta':<18} {'Median Delta':<18} {'Seed Deltas (kWh)'}")
        print("-" * 120)
        for (h_label, m_name), grp in f_df.groupby(["horizon", "model"]):
            mean_psrei = grp["psrei_kwh"].mean()
            mean_viol = grp["violation_rate_pct"].mean()
            mean_delta = grp["delta_psrei_mean_kwh"].mean()
            median_delta = grp["delta_psrei_mean_kwh"].median()
            seed_deltas = [f"{round(x/1e3):+d}k" for x in grp["delta_psrei_mean_kwh"].tolist()]
            d_str = f"{mean_delta:+,.0f}" if m_name != "Site-Local Wspd-Bins" else "0 (ref)"
            med_str = f"{median_delta:+,.0f}" if m_name != "Site-Local Wspd-Bins" else "0 (ref)"
            seed_str = ", ".join(seed_deltas) if m_name != "Site-Local Wspd-Bins" else "all 0"
            print(
                f"{h_label:<8} {m_name:<28} {mean_psrei:<15,.0f} "
                f"{mean_viol:<10.2f}% {d_str:<18} {med_str:<18} [{seed_str}]"
            )

    # Formal Scientific Interpretation Check
    print("\n==================== SCIENTIFIC INTERPRETATION ====================", flush=True)
    for farm in ["Penmanshiel", "Kelmarsh"]:
        pm_trans = agg[(agg["farm"] == farm) & (agg["model"] == "Transferred STGQ-Modular")]
        pm_wspd = agg[(agg["farm"] == farm) & (agg["model"] == "Site-Local Wspd-Bins")]
        pm_nograph = agg[(agg["farm"] == farm) & (agg["model"] == "No-Graph Architectural Control")]

        mean_delta_h1 = pm_trans[pm_trans["horizon"] == "h=1"]["delta_psrei_mean_kwh"].values[0]
        mean_delta_h6 = pm_trans[pm_trans["horizon"] == "h=6"]["delta_psrei_mean_kwh"].values[0]

        print(f"\n[{farm}] Transferred vs Site-Local Wspd-Bins:")
        print(f"  Primary Endpoint (h=6) Delta PSREI: {mean_delta_h6:+,.0f} kWh")
        print(f"  Secondary Endpoint (h=1) Delta PSREI: {mean_delta_h1:+,.0f} kWh")

        if mean_delta_h1 >= 0 and mean_delta_h6 >= 0:
            print(f"  --> VERDICT: REVERSE RESULT CONFIRMED.")
            print(f"      Transferred STGQ does not yield significant decision gain over Site-Local Wspd-Bins on {farm}.")
            print(f"      Site-Local Wspd-Bins achieves lower or comparable surrogate cost across both evaluated horizons.")
            print(f"      BOUNDED SCIENTIFIC SCOPE: Confirms simple local baseline sufficiency on the two evaluated sites.")
            print(f"      (Does NOT claim universal absence of spatial value across all arbitrary wind farms).")
        else:
            print(f"  --> VERDICT: Positive decision gain observed on {farm}.")


if __name__ == "__main__":
    main()
    import os
    os._exit(0)

