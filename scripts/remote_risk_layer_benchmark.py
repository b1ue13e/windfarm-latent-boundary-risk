"""Phase 3: Risk-Layer Showdown Benchmark under Causally Symmetric Arrival Feed.

Strict evaluation of 6 risk layer architectures:
1. Global Quantile Baseline (unconditional 90th percentile)
2. Continuous Physical Quantile (soft-pab-bin on arrival feed)
3. Missingness-Aware GBDT Quantile (direct residual quantile from symmetric features + mask)
4. Frozen Backbone + Residual Quantile Head (two-stage decoupled representation)
5. Joint Non-routed Head (Dense Head multitask representation)
6. Joint Routed Head (Boundary Router MoE representation)

Under 4 controlled degradation regimes:
- Clean
- Delay-6 (symmetric 6-step lag)
- Sensor Noise (sigma_wspd=1.0 m/s, sigma_pab=2.0 deg)
- Markov-Gilbert Burst Drops (p=0.08, p_bb=0.75, max_lag=6)

Evaluated at unique physical delivery moments (1 decision per delivery time, eliminating 24-step over-counting).
"""
from __future__ import annotations

import os
import sys

# Prevent OpenMP thread contention across parallel processes
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"
os.environ["VECLIB_MAXIMUM_THREADS"] = "2"
os.environ["NUMEXPR_NUM_THREADS"] = "2"
os.environ["PYTHONUNBUFFERED"] = "1"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

torch.set_num_threads(2)

from windfarm_moe.arrival_feed import (
    DegradationSpec,
    UnifiedArrivalDataset,
    extract_symmetric_rule_input,
)
from windfarm_moe.data import CacheBundle, load_cache_bundle
from windfarm_moe.mechanism_intervention import _load_model_from_checkpoint


DT = 1.0 / 6.0  # 10-minute step in hours
RHO = 10.0      # Penalty ratio
CRITICAL_FRACTILE = 1.0 - 1.0 / RHO  # 0.90
N_BINS = 5


class QuantileResidualHead(nn.Module):
    """Two-stage decoupled residual quantile predictor on frozen representations."""
    def __init__(self, context_dim: int = 64, phys_dim: int = 4, hidden_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(context_dim + phys_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, 1),
            nn.ReLU(),
        )

    def forward(self, context: torch.Tensor, anchor_physics: torch.Tensor) -> torch.Tensor:
        feat = torch.cat([context, anchor_physics], dim=-1)
        return self.net(feat).squeeze(-1)


def pinball_loss_tensor(pred_r: torch.Tensor, target_s: torch.Tensor, tau: float = 0.90) -> torch.Tensor:
    u = target_s - pred_r
    return torch.maximum(tau * u, (tau - 1.0) * u).mean()


def pinball_loss_np(target: np.ndarray, pred_q: np.ndarray, tau: float = 0.90) -> float:
    u = target - pred_q
    return float(np.mean(np.maximum(tau * u, (tau - 1.0) * u)))


def extract_gbdt_features(
    batch_x: np.ndarray,
    batch_mask: np.ndarray,
    batch_anchor: np.ndarray,
    w_idx: int = 0,
    p_idx: int = 7,
) -> np.ndarray:
    """Extract compact feature vector per turbine from symmetric arrival feed."""
    B, H, N, C = batch_x.shape
    w_feat = batch_x[..., w_idx]  # Wspd
    p_feat = batch_x[..., p_idx]  # Pab_mean
    w_mask = batch_mask[..., w_idx]
    p_mask = batch_mask[..., p_idx]

    # Ensure batch_anchor is (B, N, C_anchor) to match turbine dimension
    if batch_anchor.ndim == 2:
        batch_anchor = np.broadcast_to(batch_anchor[:, None, :], (B, N, batch_anchor.shape[-1]))

    feats = [
        w_feat.mean(axis=1),
        w_feat.std(axis=1),
        w_feat.min(axis=1),
        w_feat.max(axis=1),
        w_feat[:, -1, :],
        p_feat.mean(axis=1),
        p_feat.std(axis=1),
        p_feat.min(axis=1),
        p_feat.max(axis=1),
        p_feat[:, -1, :],
        w_mask.mean(axis=1),
        p_mask.mean(axis=1),
        batch_anchor[..., 0],
        batch_anchor[..., 1],
        batch_anchor[..., 2],
        batch_anchor[..., 3],
    ]
    stacked = np.stack(feats, axis=-1)  # (B, N, 16)
    return stacked.reshape(B * N, -1)


def fit_and_evaluate_binned_policy(
    val_score: np.ndarray,
    val_shortfall: np.ndarray,
    val_active: np.ndarray,
    test_score: np.ndarray,
    n_bins: int = N_BINS,
    tau: float = CRITICAL_FRACTILE,
) -> tuple[np.ndarray, dict[int, float], np.ndarray]:
    """Fits validation-frozen quintile reserves and applies to test set."""
    v_score_act = val_score[val_active]
    v_s_act = val_shortfall[val_active]

    quantiles = np.linspace(0.0, 1.0, n_bins + 1)[1:-1]
    edges = np.quantile(v_score_act, quantiles)

    v_bins = np.digitize(v_score_act, edges)
    reserves = {}
    for b in range(n_bins):
        sub_s = v_s_act[v_bins == b]
        if len(sub_s) < 20:
            reserves[b] = float(np.quantile(v_s_act, tau))
        else:
            reserves[b] = float(np.quantile(sub_s, tau))

    t_bins = np.digitize(test_score, edges)
    test_reserve = np.zeros_like(test_score, dtype=np.float64)
    for b in range(n_bins):
        test_reserve[t_bins == b] = reserves[b]

    return test_reserve, reserves, edges


def compute_metrics(
    s: np.ndarray,
    r: np.ndarray,
    active: np.ndarray,
    rho: float = RHO,
    dt: float = DT,
    tau: float = CRITICAL_FRACTILE,
) -> dict[str, float]:
    """Compute cost, violation, shortage, reserve, and pinball loss on active cells."""
    valid = active & np.isfinite(s) & np.isfinite(r)
    s_act = s[valid]
    r_act = r[valid]
    shortage = np.maximum(s_act - r_act, 0.0)
    cost = (r_act + rho * shortage) * dt
    violation = (s_act > r_act).astype(np.float64)
    pinball = pinball_loss_np(s_act, r_act, tau=tau)

    return {
        "total_cost": float(cost.sum()),
        "mean_cost_per_event": float(cost.mean()) if len(cost) > 0 else 0.0,
        "violation_rate": float(violation.mean()) if len(violation) > 0 else 0.0,
        "total_shortage": float(shortage.sum() * dt),
        "total_reserve": float(r_act.sum() * dt),
        "pinball_loss": pinball,
        "n_events": int(valid.sum()),
    }


def block_bootstrap(
    s: np.ndarray,
    reserves_dict: dict[str, np.ndarray],
    active: np.ndarray,
    time_indices: np.ndarray,
    block_size: int = 144,
    n_boot: int = 1000,
    seed: int = 42,
) -> dict[str, Any]:
    """Fast vectorized weather event block bootstrap for 95% CI and paired difference vs Joint Routed."""
    rng = np.random.default_rng(seed)
    unique_times = np.unique(time_indices)
    n_times = len(unique_times)
    n_blocks = max(1, int(np.ceil(n_times / block_size)))

    time_to_block = {t: idx // block_size for idx, t in enumerate(unique_times)}
    sample_block_ids = np.array([time_to_block[t] for t in time_indices], dtype=np.int64)

    valid = active & np.isfinite(s)
    models = list(reserves_dict.keys())

    # Pre-aggregate cost per block for each model using np.bincount
    block_costs = {}
    for m in models:
        r = np.nan_to_num(reserves_dict[m], nan=0.0)
        sh = np.maximum(s - r, 0.0)
        c = (r + RHO * sh) * DT
        c_valid = np.where(valid, c, 0.0)
        block_sum = np.bincount(sample_block_ids, weights=c_valid, minlength=n_blocks)[:n_blocks]
        block_costs[m] = block_sum

    # Vectorized bootstrap resample
    chosen_blocks = rng.integers(0, n_blocks, size=(n_boot, n_blocks))
    boot_costs = {}
    for m in models:
        boot_costs[m] = block_costs[m][chosen_blocks].sum(axis=1)

    summary = {}
    ref_model = "Joint Routed"
    ref_boot = boot_costs[ref_model]

    for m in models:
        mean_c = float(np.mean(boot_costs[m]))
        ci_lower = float(np.quantile(boot_costs[m], 0.025))
        ci_upper = float(np.quantile(boot_costs[m], 0.975))
        diff = boot_costs[m] - ref_boot
        p_val = float(np.mean(diff <= 0.0)) if m != ref_model else 1.0
        diff_ci_lower = float(np.quantile(diff, 0.025))
        diff_ci_upper = float(np.quantile(diff, 0.975))
        summary[m] = {
            "mean_cost": mean_c,
            "ci_95": [ci_lower, ci_upper],
            "delta_vs_routed": float(np.mean(diff)),
            "delta_ci_95": [diff_ci_lower, diff_ci_upper],
            "p_val_vs_routed": p_val,
        }
    return summary


def train_frozen_quantile_head(
    model: nn.Module,
    train_loader: DataLoader,
    device: torch.device,
    lead_step: int = 0,
    max_batches: int = 300,
    epochs: int = 3,
    lr: float = 1e-3,
) -> QuantileResidualHead:
    """Trains a 2-layer residual quantile head on frozen spatio-temporal representations."""
    head = QuantileResidualHead(context_dim=64, phys_dim=4, hidden_dim=64).to(device)
    optimizer = torch.optim.Adam(head.parameters(), lr=lr)

    for p in model.parameters():
        p.requires_grad = False
    model.eval()

    head.train()
    for epoch in range(epochs):
        batch_count = 0
        for batch in train_loader:
            x_hist = batch["x_hist"].to(device)
            edge_index = batch["edge_index_hist"].to(device)
            edge_weight = batch["edge_weight_hist"].to(device)
            feature_mask = batch["feature_mask_hist"].to(device)
            anchor_phys = batch["anchor_physics"].to(device)
            target = batch["target"].to(device)

            with torch.no_grad():
                pred, _, aux = model(x_hist, edge_index, edge_weight, feature_mask, anchor_phys)
                context = aux["context"]

            pred_r = head(context, anchor_phys)
            y_pred = pred[:, lead_step, :]
            y_true = target[:, lead_step, :]
            shortfall = torch.clamp(y_pred - y_true, min=0.0)

            loss = pinball_loss_tensor(pred_r, shortfall, tau=CRITICAL_FRACTILE)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            batch_count += 1
            if batch_count >= max_batches:
                break

    head.eval()
    return head


def collect_split_predictions(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    lead_step: int = 0,
) -> dict[str, np.ndarray]:
    """Runs forward pass and collects predictions, targets, anchor features, and probabilities."""
    all_pred = []
    all_target = []
    all_anchor = []
    all_prob = []
    all_time = []
    all_mask = []
    all_x = []
    all_fmask = []

    model.eval()
    with torch.no_grad():
        for batch in loader:
            x_hist = batch["x_hist"].to(device)
            edge_index = batch["edge_index_hist"].to(device)
            edge_weight = batch["edge_weight_hist"].to(device)
            feature_mask = batch["feature_mask_hist"].to(device)
            anchor_phys = batch["anchor_physics"].to(device)
            target = batch["target"].to(device)
            t_idx = batch["anchor_index"].cpu().numpy()

            pred, gate_prob, aux = model(x_hist, edge_index, edge_weight, feature_mask, anchor_phys)

            p_lead = pred[:, lead_step, :].cpu().numpy()
            t_lead = target[:, lead_step, :].cpu().numpy()
            anc = anchor_phys.cpu().numpy()
            prob = gate_prob[..., 2].cpu().numpy()

            all_pred.append(p_lead)
            all_target.append(t_lead)
            all_anchor.append(anc)
            all_prob.append(prob)
            all_time.append(t_idx)
            all_mask.append(batch["target_mask"][:, lead_step, :].cpu().numpy())
            all_x.append(x_hist.cpu().numpy())
            all_fmask.append(feature_mask.cpu().numpy())

    return {
        "pred": np.concatenate(all_pred, axis=0),
        "target": np.concatenate(all_target, axis=0),
        "anchor": np.concatenate(all_anchor, axis=0),
        "prob": np.concatenate(all_prob, axis=0),
        "time": np.concatenate(all_time, axis=0),
        "mask": np.concatenate(all_mask, axis=0),
        "x": np.concatenate(all_x, axis=0),
        "fmask": np.concatenate(all_fmask, axis=0),
    }


def main():
    parser = argparse.ArgumentParser(description="Phase 3 Risk Layer Showdown Benchmark")
    parser.add_argument("--farm", default="wtb", help="Wind farm identifier: wtb, kelmarsh, or penmanshiel")
    parser.add_argument("--cache-dir", default="artifacts/cache_signature_trainweight/wtb_245d_canonical")
    parser.add_argument("--routed-checkpoint-pattern", default="artifacts/trainweight_full_rerun_20260830/wtb_full_seed{seed}")
    parser.add_argument("--dense-checkpoint-pattern", default="artifacts/dense_classifier_runs_20260904/canonical/wtb_bal_align_force_seed{seed}")
    parser.add_argument("--seeds", default="201,202,203,204,205")
    parser.add_argument("--output-dir", default="artifacts/clean_evidence_v2/risk_layer_benchmark")
    parser.add_argument("--device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lead-step", type=int, default=0, help="0-indexed lead step (0 = horizon 1, 10 min; 5 = horizon 6, 1 hr)")
    parser.add_argument("--rated-wind", type=float, default=10.5)
    parser.add_argument("--band", type=float, default=1.0)
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--dataloader-workers", type=int, default=0, help="DataLoader num_workers (default 0 to prevent cgroup OOM)")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)
    print(f"Starting Phase 3 Risk Layer Benchmark for [{args.farm.upper()}] on {device} (lead_step={args.lead_step})", flush=True)
    print(f"Cache: {args.cache_dir}", flush=True)
    print(f"Output: {out_dir}", flush=True)

    cache_path = Path(args.cache_dir)
    if not cache_path.exists():
        for alt in ["artifacts/cache_strictmask_trainweights/wtb_245d", "artifacts/cache_strictmask/wtb_245d"]:
            if Path(alt).exists():
                cache_path = Path(alt)
                break
    bundle = load_cache_bundle(cache_path, mmap_mode="r")
    seeds = [int(s) for s in args.seeds.split(",")]

    feat_names = list(bundle.metadata.get("feature_names", []))
    w_idx = feat_names.index("Wspd") if "Wspd" in feat_names else 0
    p_idx = feat_names.index("Pab_mean") if "Pab_mean" in feat_names else (7 if len(feat_names) > 7 else 1)

    w_mean = float(bundle.metadata["physics_model_stats"]["0"]["mean"])
    w_std = float(bundle.metadata["physics_model_stats"]["0"]["std"])
    p_mean = float(bundle.metadata["physics_model_stats"]["1"]["mean"])
    p_std = float(bundle.metadata["physics_model_stats"]["1"]["std"])

    regimes = {
        "clean": DegradationSpec(delay_steps=0),
        "delay6": DegradationSpec(delay_steps=6),
        "sensor_noise": DegradationSpec(delay_steps=0, noise_sigma_physical={"Wspd": 1.0, "Pab_mean": 2.0}),
        "markov_burst": DegradationSpec(delay_steps=0, use_markov_gilbert=True, p_gb=0.08, p_bb=0.75, max_lag=6),
    }

    all_seed_rows = []
    all_boot_rows = []

    for seed in seeds:
        print(f"\n==================== SEED {seed} ====================", flush=True)
        t_seed_start = time.time()
        routed_path = Path(args.routed_checkpoint_pattern.format(seed=seed))
        print(f"Loading routed checkpoint: {routed_path}", flush=True)
        routed_model = _load_model_from_checkpoint(routed_path, bundle, device)

        dense_model = None
        if args.dense_checkpoint_pattern:
            candidate_dense_path = Path(args.dense_checkpoint_pattern.format(seed=seed))
            if candidate_dense_path.exists():
                print(f"Loading dense checkpoint: {candidate_dense_path}", flush=True)
                dense_model = _load_model_from_checkpoint(candidate_dense_path, bundle, device)
            else:
                print(f"Dense checkpoint {candidate_dense_path} not found, skipping Joint Dense Head", flush=True)

        print("Setting up datasets...", flush=True)
        train_ds = UnifiedArrivalDataset(bundle, "train", hist_len=36, pred_len=24, degradation=DegradationSpec(delay_steps=0))
        val_ds = UnifiedArrivalDataset(bundle, "val", hist_len=36, pred_len=24, degradation=DegradationSpec(delay_steps=0))
        train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=args.dataloader_workers)
        val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=args.dataloader_workers)

        # 1. Train Frozen Backbone + Residual Quantile Head
        print("Training Frozen Backbone Residual Quantile Head...", flush=True)
        frozen_head = train_frozen_quantile_head(routed_model, train_loader, device, lead_step=args.lead_step, max_batches=300, epochs=3)

        # 2. Collect validation outputs
        print("Collecting validation outputs...", flush=True)
        val_routed = collect_split_predictions(routed_model, val_loader, device, lead_step=args.lead_step)
        dense_reserves, dense_edges = None, None
        if dense_model is not None:
            val_dense = collect_split_predictions(dense_model, val_loader, device, lead_step=args.lead_step)
            val_dense_prob_flat = val_dense["prob"].reshape(-1)
            _, dense_reserves, dense_edges = fit_and_evaluate_binned_policy(
                val_dense_prob_flat, val_s_flat if 'val_s_flat' in locals() else np.maximum(val_routed["pred"] - val_routed["target"], 0.0).reshape(-1),
                val_act_flat if 'val_act_flat' in locals() else (val_routed["mask"] > 0.5).reshape(-1),
                val_dense_prob_flat, n_bins=N_BINS, tau=CRITICAL_FRACTILE
            )

        val_shortfall = np.maximum(val_routed["pred"] - val_routed["target"], 0.0)
        val_wspd_phys = val_routed["anchor"][..., 0] * w_std + w_mean
        val_pab_phys = val_routed["anchor"][..., 1] * p_std + p_mean
        val_s_flat = val_shortfall.reshape(-1)
        val_active = (
            (np.abs(val_wspd_phys - args.rated_wind) <= args.band)
            & (val_routed["mask"] > 0.5)
            & np.isfinite(val_shortfall)
        )
        val_act_flat = val_active.reshape(-1)
        print(f"Validation active boundary cells: {val_act_flat.sum()} / {val_act_flat.size}", flush=True)

        if dense_model is not None and dense_reserves is None:
            val_dense_prob_flat = val_dense["prob"].reshape(-1)
            _, dense_reserves, dense_edges = fit_and_evaluate_binned_policy(
                val_dense_prob_flat, val_s_flat, val_act_flat, val_dense_prob_flat, n_bins=N_BINS, tau=CRITICAL_FRACTILE
            )

        # Fit Global Quantile
        global_reserve_val = float(np.quantile(val_s_flat[val_act_flat], CRITICAL_FRACTILE))
        print(f"Global Quantile reserve (tau=0.90): {global_reserve_val:.2f} kW", flush=True)

        # Fit Continuous Physical Quantile (soft-pab-bin)
        val_pab_flat = val_pab_phys.reshape(-1)
        _, phys_reserves, pab_edges = fit_and_evaluate_binned_policy(
            val_pab_flat, val_s_flat, val_act_flat, val_pab_flat, n_bins=N_BINS, tau=CRITICAL_FRACTILE
        )

        # Fit Joint Routed Head Quantile (soft-gate-bin)
        val_routed_prob_flat = val_routed["prob"].reshape(-1)
        _, routed_reserves, routed_edges = fit_and_evaluate_binned_policy(
            val_routed_prob_flat, val_s_flat, val_act_flat, val_routed_prob_flat, n_bins=N_BINS, tau=CRITICAL_FRACTILE
        )

        # Train Missingness-Aware GBDT Quantile on Train split
        print("Training Missingness-Aware GBDT Quantile...", flush=True)
        train_sample_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=False, num_workers=args.dataloader_workers)
        tr_x_list, tr_mask_list, tr_anc_list, tr_tar_list, tr_tmask_list, tr_pred_list = [], [], [], [], [], []
        count = 0
        routed_model.eval()
        with torch.no_grad():
            for b in train_sample_loader:
                x_h = b["x_hist"].to(device)
                ei = b["edge_index_hist"].to(device)
                ew = b["edge_weight_hist"].to(device)
                fm = b["feature_mask_hist"].to(device)
                ap = b["anchor_physics"].to(device)
                pred, _, _ = routed_model(x_h, ei, ew, fm, ap)

                tr_x_list.append(b["x_hist"].numpy())
                tr_mask_list.append(b["feature_mask_hist"].numpy())
                tr_anc_list.append(b["anchor_physics"].numpy())
                tr_tar_list.append(b["target"][:, args.lead_step, :].numpy())
                tr_tmask_list.append(b["target_mask"][:, args.lead_step, :].numpy())
                tr_pred_list.append(pred[:, args.lead_step, :].cpu().numpy())
                count += len(b["anchor_index"])
                if count >= 1000:
                    break

        tr_x = np.concatenate(tr_x_list, axis=0)
        tr_mask = np.concatenate(tr_mask_list, axis=0)
        tr_anc = np.concatenate(tr_anc_list, axis=0)
        tr_tar = np.concatenate(tr_tar_list, axis=0)
        tr_tmask = np.concatenate(tr_tmask_list, axis=0).reshape(-1)
        tr_pred = np.concatenate(tr_pred_list, axis=0)

        tr_feats = extract_gbdt_features(tr_x, tr_mask, tr_anc, w_idx=w_idx, p_idx=p_idx)
        tr_shortfall = np.maximum(tr_pred - tr_tar, 0.0).reshape(-1)
        tr_wspd_phys = (tr_anc[..., 0] * w_std + w_mean).reshape(-1)
        tr_valid = (
            (np.abs(tr_wspd_phys - args.rated_wind) <= args.band)
            & (tr_tmask > 0.5)
            & np.isfinite(tr_shortfall)
        )

        act_idx = np.where(tr_valid)[0]
        if len(act_idx) > 50_000:
            rng = np.random.default_rng(seed)
            act_idx = rng.choice(act_idx, size=50_000, replace=False)
        elif len(act_idx) < 1000:
            finite_idx = np.where(np.isfinite(tr_shortfall) & (tr_tmask > 0.5))[0]
            act_idx = finite_idx[:min(50_000, len(finite_idx))]

        gbdt_scaler = StandardScaler()
        tr_feats_act = np.nan_to_num(tr_feats[act_idx], nan=0.0, posinf=0.0, neginf=0.0)
        tr_feats_scaled = gbdt_scaler.fit_transform(tr_feats_act)

        gbdt = HistGradientBoostingRegressor(loss="quantile", quantile=CRITICAL_FRACTILE, max_iter=50, random_state=seed)
        gbdt.fit(tr_feats_scaled, tr_shortfall[act_idx])
        print("GBDT training complete with StandardScaler.", flush=True)

        # 3. Evaluate across 4 Controlled Degradation Regimes
        for reg_name, reg_spec in regimes.items():
            print(f"\n--- Testing Regime: {reg_name} ---", flush=True)
            test_ds = UnifiedArrivalDataset(bundle, "test", hist_len=36, pred_len=24, degradation=reg_spec)
            test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=args.dataloader_workers)

            test_routed = collect_split_predictions(routed_model, test_loader, device, lead_step=args.lead_step)
            test_dense = collect_split_predictions(dense_model, test_loader, device, lead_step=args.lead_step) if dense_model is not None else None

            test_s = np.maximum(test_routed["pred"] - test_routed["target"], 0.0)
            test_wspd_phys = test_routed["anchor"][..., 0] * w_std + w_mean
            test_pab_phys = test_routed["anchor"][..., 1] * p_std + p_mean
            test_active = (
                (np.abs(test_wspd_phys - args.rated_wind) <= args.band)
                & (test_routed["mask"] > 0.5)
                & np.isfinite(test_s)
            )

            test_s_flat = test_s.reshape(-1)
            test_act_flat = test_active.reshape(-1)
            test_times_flat = np.repeat(test_routed["time"] + args.lead_step + 1, test_s.shape[1])

            # Allocate reserves for models
            reserves_map = {}

            # 1. Global Quantile
            reserves_map["Global Quantile"] = np.full_like(test_s_flat, global_reserve_val)

            # 2. Continuous Physical Quantile (soft-pab-bin)
            t_pab_bins = np.digitize(test_pab_phys.reshape(-1), pab_edges)
            r_phys = np.zeros_like(test_s_flat)
            for b in range(N_BINS):
                r_phys[t_pab_bins == b] = phys_reserves[b]
            reserves_map["Continuous Physical Quantile"] = r_phys

            # 3. Missingness-Aware GBDT Quantile (scaled and symmetric)
            test_feats = extract_gbdt_features(test_routed["x"], test_routed["fmask"], test_routed["anchor"], w_idx=w_idx, p_idx=p_idx)
            test_feats_clean = np.nan_to_num(test_feats, nan=0.0, posinf=0.0, neginf=0.0)
            test_feats_scaled = gbdt_scaler.transform(test_feats_clean)
            r_gbdt = np.nan_to_num(np.maximum(gbdt.predict(test_feats_scaled), 0.0), nan=global_reserve_val)
            reserves_map["Missingness-Aware GBDT"] = r_gbdt

            # 4. Frozen Backbone + Residual Quantile Head
            r_frozen_list = []
            with torch.no_grad():
                for batch in test_loader:
                    x_h = batch["x_hist"].to(device)
                    ei = batch["edge_index_hist"].to(device)
                    ew = batch["edge_weight_hist"].to(device)
                    fm = batch["feature_mask_hist"].to(device)
                    ap = batch["anchor_physics"].to(device)
                    _, _, aux = routed_model(x_h, ei, ew, fm, ap)
                    ctx = aux["context"]
                    rf = frozen_head(ctx, ap).cpu().numpy()
                    r_frozen_list.append(rf)
            r_frozen = np.nan_to_num(np.concatenate(r_frozen_list, axis=0).reshape(-1), nan=global_reserve_val)
            reserves_map["Frozen Backbone MLP"] = r_frozen

            # 5. Joint Non-routed Head (Dense Head, if available)
            if dense_model is not None and dense_edges is not None:
                t_dense_bins = np.digitize(test_dense["prob"].reshape(-1), dense_edges)
                r_dense = np.zeros_like(test_s_flat)
                for b in range(N_BINS):
                    r_dense[t_dense_bins == b] = dense_reserves[b]
                reserves_map["Joint Dense Head"] = r_dense

            # 6. Joint Routed Head (MoE Boundary Router)
            t_routed_bins = np.digitize(test_routed["prob"].reshape(-1), routed_edges)
            r_routed = np.zeros_like(test_s_flat)
            for b in range(N_BINS):
                r_routed[t_routed_bins == b] = routed_reserves[b]
            reserves_map["Joint Routed"] = r_routed

            # Compute individual seed metrics
            for m_name, r_arr in reserves_map.items():
                m_res = compute_metrics(test_s_flat, r_arr, test_act_flat)
                row = {
                    "farm": args.farm,
                    "seed": seed,
                    "regime": reg_name,
                    "lead_step": args.lead_step + 1,
                    "model": m_name,
                    **m_res,
                }
                all_seed_rows.append(row)

            # Compute Fast Weather Block Bootstrap
            boot_res = block_bootstrap(
                test_s_flat, reserves_map, test_act_flat, test_times_flat,
                block_size=144, n_boot=args.n_boot, seed=seed
            )
            for m_name, b_stat in boot_res.items():
                all_boot_rows.append({
                    "farm": args.farm,
                    "seed": seed,
                    "regime": reg_name,
                    "lead_step": args.lead_step + 1,
                    "model": m_name,
                    **b_stat,
                })

            print(f"Summary for {reg_name} (Seed {seed}):", flush=True)
            summary_df = pd.DataFrame([r for r in all_seed_rows if r["seed"] == seed and r["regime"] == reg_name])
            print(summary_df[["model", "total_cost", "violation_rate", "total_reserve", "total_shortage"]].to_string(), flush=True)

        print(f"Seed {seed} total elapsed time: {time.time() - t_seed_start:.1f}s", flush=True)

    # Save final artifacts
    seed_df = pd.DataFrame(all_seed_rows)
    seed_df.to_csv(out_dir / "results_by_seed.csv", index=False)

    boot_df = pd.DataFrame(all_boot_rows)
    boot_df.to_csv(out_dir / "bootstrap_summary.csv", index=False)

    # Aggregate cross-seed summary
    agg = seed_df.groupby(["farm", "regime", "lead_step", "model"]).agg({
        "total_cost": ["mean", "std"],
        "violation_rate": ["mean", "std"],
        "total_reserve": ["mean", "std"],
        "total_shortage": ["mean", "std"],
        "pinball_loss": ["mean", "std"],
    }).reset_index()
    agg.to_csv(out_dir / "cross_seed_aggregate.csv", index=False)

    print("\n==================== BENCHMARK COMPLETE ====================", flush=True)
    print(agg.to_string(), flush=True)


if __name__ == "__main__":
    main()
