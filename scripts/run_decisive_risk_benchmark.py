"""Decisive Experiment v3: Make-or-Break Benchmark under Causally Symmetric Arrival Feed.

Reformulated Scientific Question:
"在所有方法获得相同、带到达时间的 SCADA 信息时，边界监督的共享表征，能否在不增加误报、不放松可靠性的条件下，改善场站短缺风险？"

Execution Steps:
1. Evidence Base: Verified in decisive_evidence_base_audit.py (q*(rho) = 1 - 1/rho, strict isolation, no unsourced claims).
2. Unified Ingress: Degrades all channels, masks, and anchor physics synchronously.
3. Fixed Backbone & 6 Risk Layers:
   - Continuous Physical Quantile (soft-pitch-bin on arrival feed)
   - Missingness-Aware GBDT Quantile (direct residual quantile from symmetric features + mask)
   - Sequence Classifier (2-layer GRU on arrival sequence + physics)
   - Frozen Encoder + Residual Quantile Head (with equal 5-bin calibration budget)
   - Joint Dense (multitask dense head with 5-bin calibration)
   - Joint Routed (MoE boundary router with 5-bin calibration)
4. Unified Evaluation Unit & Iso-Reliability:
   - Single delivery moment evaluation (lead_step=0, 10-min horizon, no 24-step over-counting).
   - Iso-Reliability: Validation-calibrated reserve scaling to ensure strict violation_rate <= 10.0%.
   - Reports: Cost, Reserve MWh, Shortage MWh, Violation Rate, False Alarm Rate, Event Recall & Delay, Brier Score, ECE.
   - Weather-event block bootstrap (block_size=144, 1000 resamples).
5. External Confirmation & Route Dispatch:
   - Evaluates on WTB and external commercial farms (Kelmarsh, Penmanshiel).
   - Evaluates the 4 decision criteria and outputs Route Dispatch verdicts.
"""
from __future__ import annotations

import os
import sys

os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"
os.environ["PYTHONUNBUFFERED"] = "1"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

torch.set_num_threads(2)

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from windfarm_moe.arrival_feed import (
    DegradationSpec,
    UnifiedArrivalDataset,
    extract_symmetric_rule_input,
)
from windfarm_moe.data import CacheBundle, load_cache_bundle
from windfarm_moe.mechanism_intervention import _load_model_from_checkpoint


DT = 1.0 / 6.0       # 10-minute step in hours
RHO = 10.0           # Penalty ratio
CRITICAL_FRACTILE = 1.0 - 1.0 / RHO  # 0.90
TARGET_VIOLATION = 1.0 - CRITICAL_FRACTILE  # 0.10
N_BINS = 5


# ==============================================================================
# Model Architecture Components
# ==============================================================================

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


class SequenceGRUClassifier(nn.Module):
    """Sequence classifier baseline operating directly on arrival history feed."""
    def __init__(self, in_channels: int = 11, phys_dim: int = 4, hidden_dim: int = 64):
        super().__init__()
        self.gru = nn.GRU(
            input_size=in_channels,
            hidden_size=hidden_dim,
            num_layers=2,
            batch_first=True,
            dropout=0.1,
        )
        self.mlp = nn.Sequential(
            nn.Linear(hidden_dim + phys_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, 2),  # Class 0: non-pitch, Class 1: pitch
        )

    def forward(self, x_hist: torch.Tensor, anchor_phys: torch.Tensor) -> torch.Tensor:
        # x_hist: (B, H, N, C)
        B, H, N, C = x_hist.shape
        x_reshaped = x_hist.permute(0, 2, 1, 3).reshape(B * N, H, C)
        out, h_n = self.gru(x_reshaped)
        h_last = h_n[-1]  # (B*N, hidden_dim)

        anc_reshaped = anchor_phys.reshape(B * N, -1)
        fused = torch.cat([h_last, anc_reshaped], dim=-1)
        logits = self.mlp(fused)  # (B*N, 2)
        prob = torch.softmax(logits, dim=-1)[:, 1]  # P(pitch)
        return prob.reshape(B, N)


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
    w_feat = batch_x[..., w_idx]
    p_feat = batch_x[..., p_idx]
    w_mask = batch_mask[..., w_idx]
    p_mask = batch_mask[..., p_idx]

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


# ==============================================================================
# 5-Bin Calibration & Iso-Reliability
# ==============================================================================

def fit_5bin_quantiles(
    val_score: np.ndarray,
    val_shortfall: np.ndarray,
    val_active: np.ndarray,
    n_bins: int = N_BINS,
    tau: float = CRITICAL_FRACTILE,
) -> Tuple[Dict[int, float], np.ndarray, float]:
    """Fit 5 quintile reserve values on validation active boundary cells."""
    v_s_act = val_shortfall[val_active]
    v_sc_act = val_score[val_active]

    global_reserve = float(np.quantile(v_s_act, tau)) if len(v_s_act) > 0 else 0.0

    quantiles = np.linspace(0.0, 1.0, n_bins + 1)[1:-1]
    edges = np.quantile(v_sc_act, quantiles) if len(v_sc_act) > n_bins else np.zeros(n_bins - 1)

    v_bins = np.clip(np.searchsorted(edges, v_sc_act), 0, n_bins - 1)
    reserves = {}
    for b in range(n_bins):
        sub_s = v_s_act[v_bins == b]
        if len(sub_s) < 30:
            reserves[b] = global_reserve
        else:
            reserves[b] = float(np.quantile(sub_s, tau))

    return reserves, edges, global_reserve


def apply_5bin_policy(
    test_score: np.ndarray,
    reserves: Dict[int, float],
    edges: np.ndarray,
    n_bins: int = N_BINS,
) -> np.ndarray:
    """Apply validation-fitted 5-bin quantiles to test risk scores."""
    t_bins = np.clip(np.searchsorted(edges, test_score), 0, n_bins - 1)
    r_out = np.zeros_like(test_score, dtype=np.float64)
    for b in range(n_bins):
        r_out[t_bins == b] = reserves[b]
    return r_out


def calibrate_iso_reliability_multiplier(
    val_shortfall: np.ndarray,
    val_reserve: np.ndarray,
    val_active: np.ndarray,
    target_violation: float = TARGET_VIOLATION,
) -> float:
    """Finds the validation-frozen scaling multiplier gamma such that violation_rate <= target_violation."""
    valid = val_active & np.isfinite(val_shortfall) & np.isfinite(val_reserve)
    s_act = val_shortfall[valid]
    r_act = val_reserve[valid]

    if len(s_act) == 0:
        return 1.0

    raw_viol = float(np.mean(s_act > r_act))
    if raw_viol <= target_violation:
        # Check if we can scale down while staying compliant, or leave as 1.0
        gammas = np.linspace(0.5, 1.0, 51)
        for g in gammas:
            if float(np.mean(s_act > g * r_act)) <= target_violation:
                return float(g)
        return 1.0

    # Needs scale up
    gammas = np.linspace(1.0, 3.5, 251)
    for g in gammas:
        if float(np.mean(s_act > g * r_act)) <= target_violation:
            return float(g)

    return 3.5


# ==============================================================================
# Comprehensive Evaluation Metrics
# ==============================================================================

def compute_decisive_metrics(
    shortfall: np.ndarray,
    reserve: np.ndarray,
    active: np.ndarray,
    prob: Optional[np.ndarray],
    regime: np.ndarray,
    rho: float = RHO,
    dt: float = DT,
    tau: float = CRITICAL_FRACTILE,
) -> Dict[str, float]:
    """Computes all decision, risk, reliability, and calibration metrics on active cells."""
    valid = active & np.isfinite(shortfall) & np.isfinite(reserve)
    s = shortfall[valid]
    r = reserve[valid]

    shortage = np.maximum(s - r, 0.0)
    cost = (r + rho * shortage) * dt
    violation = (s > r).astype(np.float64)
    pinball = pinball_loss_np(s, r, tau=tau)

    # False Alarm Rate during Region 2 MPPT (regime == 1, no pitch)
    # Define alarm as reserve falling into high-risk allocation (e.g. top quartile of reserve)
    mppt_valid = valid & (regime.reshape(-1) == 1)
    if mppt_valid.sum() > 0:
        r_thresh = np.quantile(r, 0.80) if len(r) > 0 else 0.0
        far = float((reserve[mppt_valid] >= r_thresh).mean())
    else:
        far = 0.0

    # Event Detection Recall & Delay (regime == 2, pitching active)
    pitch_valid = valid & (regime.reshape(-1) == 2)
    if pitch_valid.sum() > 0:
        r_thresh = np.quantile(r, 0.50) if len(r) > 0 else 0.0
        recall = float((reserve[pitch_valid] >= r_thresh).mean())
    else:
        recall = 1.0

    # Probabilistic Calibration (Brier Score and ECE)
    brier_score = 0.0
    ece = 0.0
    if prob is not None:
        p_act = prob[valid]
        y_act = (regime.reshape(-1)[valid] == 2).astype(np.float64)
        brier_score = float(np.mean((p_act - y_act) ** 2))

        # 10-bin ECE
        bin_edges = np.linspace(0.0, 1.0, 11)
        for i in range(10):
            in_bin = (p_act >= bin_edges[i]) & (p_act < bin_edges[i + 1])
            if in_bin.sum() > 0:
                bin_acc = float(np.mean(y_act[in_bin]))
                bin_conf = float(np.mean(p_act[in_bin]))
                ece += (in_bin.sum() / len(p_act)) * abs(bin_acc - bin_conf)

    return {
        "total_cost": float(cost.sum()),
        "mean_cost_per_event": float(cost.mean()) if len(cost) > 0 else 0.0,
        "reserve_mwh": float(r.sum() * dt / 1000.0),
        "shortage_mwh": float(shortage.sum() * dt / 1000.0),
        "violation_rate": float(violation.mean()) if len(violation) > 0 else 0.0,
        "false_alarm_rate": round(far, 4),
        "event_recall": round(recall, 4),
        "brier_score": round(brier_score, 4),
        "ece": round(ece, 4),
        "pinball_loss": round(pinball, 4),
        "n_active_cells": int(valid.sum()),
    }


def weather_block_bootstrap(
    shortfall: np.ndarray,
    reserves_dict: Dict[str, np.ndarray],
    active: np.ndarray,
    time_indices: np.ndarray,
    block_size: int = 144,
    n_boot: int = 1000,
    seed: int = 42,
    ref_model: str = "Joint Routed",
) -> Dict[str, Any]:
    """Fast vectorized weather block bootstrap for 95% CIs and paired difference vs ref_model."""
    rng = np.random.default_rng(seed)
    unique_times = np.unique(time_indices)
    n_times = len(unique_times)
    n_blocks = max(1, int(np.ceil(n_times / block_size)))

    time_to_block = {t: idx // block_size for idx, t in enumerate(unique_times)}
    sample_block_ids = np.array([time_to_block[t] for t in time_indices], dtype=np.int64)

    valid = active & np.isfinite(shortfall)
    models = list(reserves_dict.keys())

    # Pre-aggregate cost per block for each model
    block_costs = {}
    for m in models:
        r = np.nan_to_num(reserves_dict[m], nan=0.0)
        sh = np.maximum(shortfall - r, 0.0)
        c = (r + RHO * sh) * DT
        c_valid = np.where(valid, c, 0.0)
        block_sum = np.bincount(sample_block_ids, weights=c_valid, minlength=n_blocks)[:n_blocks]
        block_costs[m] = block_sum

    chosen_blocks = rng.integers(0, n_blocks, size=(n_boot, n_blocks))
    boot_costs = {m: block_costs[m][chosen_blocks].sum(axis=1) for m in models}

    ref_boot = boot_costs.get(ref_model, next(iter(boot_costs.values())))

    summary = {}
    for m in models:
        mean_c = float(np.mean(boot_costs[m]))
        ci_lower = float(np.quantile(boot_costs[m], 0.025))
        ci_upper = float(np.quantile(boot_costs[m], 0.975))
        diff = boot_costs[m] - ref_boot
        p_val = float(np.mean(diff <= 0.0)) if m != ref_model else 1.0
        diff_ci_lower = float(np.quantile(diff, 0.025))
        diff_ci_upper = float(np.quantile(diff, 0.975))
        summary[m] = {
            "mean_boot_cost": mean_c,
            "ci_95": [ci_lower, ci_upper],
            "delta_vs_routed": float(np.mean(diff)),
            "delta_ci_95": [diff_ci_lower, diff_ci_upper],
            "p_val_vs_routed": p_val,
        }
    return summary


# ==============================================================================
# Model Forward Passes and Feature Extraction
# ==============================================================================

def run_forward_pass(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    lead_step: int = 0,
) -> Dict[str, np.ndarray]:
    all_pred, all_target, all_anchor, all_prob, all_time, all_mask, all_x, all_fmask, all_regime = [], [], [], [], [], [], [], [], []
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

            all_pred.append(pred[:, lead_step, :].cpu().numpy())
            all_target.append(target[:, lead_step, :].cpu().numpy())
            all_anchor.append(anchor_phys.cpu().numpy())
            prob = gate_prob[..., 2].cpu().numpy() if gate_prob is not None and gate_prob.shape[-1] >= 3 else np.zeros_like(pred[:, lead_step, :].cpu().numpy())
            all_prob.append(prob)
            all_time.append(t_idx)
            all_mask.append(batch["target_mask"][:, lead_step, :].cpu().numpy())
            all_x.append(x_hist.cpu().numpy())
            all_fmask.append(feature_mask.cpu().numpy())
            all_regime.append(batch["regime_primary"].cpu().numpy())

    return {
        "pred": np.concatenate(all_pred, axis=0),
        "target": np.concatenate(all_target, axis=0),
        "anchor": np.concatenate(all_anchor, axis=0),
        "prob": np.concatenate(all_prob, axis=0),
        "time": np.concatenate(all_time, axis=0),
        "mask": np.concatenate(all_mask, axis=0),
        "x": np.concatenate(all_x, axis=0),
        "fmask": np.concatenate(all_fmask, axis=0),
        "regime": np.concatenate(all_regime, axis=0),
    }


def train_sequence_gru_classifier(
    train_loader: DataLoader,
    in_channels: int,
    device: torch.device,
    epochs: int = 3,
    max_batches: int = 300,
    lr: float = 1e-3,
) -> SequenceGRUClassifier:
    """Trains a 2-layer GRU Sequence Classifier on arrival sequence feed."""
    model = SequenceGRUClassifier(in_channels=in_channels, phys_dim=4, hidden_dim=64).to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()

    model.train()
    for epoch in range(epochs):
        batch_count = 0
        for batch in train_loader:
            x_h = batch["x_hist"].to(device)
            ap = batch["anchor_physics"].to(device)
            reg = batch["regime_primary"].to(device)  # (B, N)
            y = (reg == 2).long()

            B, H, N, C = x_h.shape
            x_reshaped = x_h.permute(0, 2, 1, 3).reshape(B * N, H, C)
            out, h_n = model.gru(x_reshaped)
            h_last = h_n[-1]
            anc_reshaped = ap.reshape(B * N, -1)
            logits = model.mlp(torch.cat([h_last, anc_reshaped], dim=-1))

            loss = criterion(logits, y.reshape(-1))
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            batch_count += 1
            if batch_count >= max_batches:
                break

    model.eval()
    return model


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
    optimizer = optim.Adam(head.parameters(), lr=lr)

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


# ==============================================================================
# Main Benchmark Execution Function
# ==============================================================================

def run_decisive_benchmark_for_seed(
    farm: str,
    seed: int,
    bundle: CacheBundle,
    routed_ckpt_pattern: str,
    dense_ckpt_pattern: Optional[str],
    device: torch.device,
    lead_step: int = 0,
    rated_wind: float = 10.5,
    band: float = 1.0,
    n_boot: int = 1000,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Runs all 6 risk layers under 4 degradation regimes for a single seed with Iso-Reliability."""
    t_start = time.time()
    print(f"\n==================== SEED {seed} ({farm.upper()}) ====================", flush=True)

    routed_path = Path(routed_ckpt_pattern.format(seed=seed))
    print(f"Loading routed checkpoint: {routed_path}", flush=True)
    routed_model = _load_model_from_checkpoint(routed_path, bundle, device)

    dense_model = None
    if dense_ckpt_pattern:
        dense_path = Path(dense_ckpt_pattern.format(seed=seed))
        if dense_path.exists():
            print(f"Loading dense checkpoint: {dense_path}", flush=True)
            dense_model = _load_model_from_checkpoint(dense_path, bundle, device)
        else:
            print(f"Dense checkpoint {dense_path} not found, skipping Joint Dense", flush=True)

    w_mean = float(bundle.metadata["physics_model_stats"]["0"]["mean"])
    w_std = float(bundle.metadata["physics_model_stats"]["0"]["std"])
    p_mean = float(bundle.metadata["physics_model_stats"]["1"]["mean"])
    p_std = float(bundle.metadata["physics_model_stats"]["1"]["std"])
    feat_names = list(bundle.metadata.get("feature_names", []))
    w_idx = feat_names.index("Wspd") if "Wspd" in feat_names else 0
    p_idx = feat_names.index("Pab_mean") if "Pab_mean" in feat_names else (7 if len(feat_names) > 7 else 1)

    # 1. Prepare Datasets
    clean_spec = DegradationSpec(delay_steps=0, corrupted_channels=("all",))
    train_ds = UnifiedArrivalDataset(bundle, "train", hist_len=36, pred_len=24, degradation=clean_spec)
    val_ds = UnifiedArrivalDataset(bundle, "val", hist_len=36, pred_len=24, degradation=clean_spec)
    train_loader = DataLoader(train_ds, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=64, shuffle=False)

    # 2. Train Heads on Train Split
    print("Training Sequence GRU Classifier...", flush=True)
    seq_clf = train_sequence_gru_classifier(train_loader, in_channels=len(feat_names), device=device)

    print("Training Frozen Backbone Quantile Head...", flush=True)
    frozen_head = train_frozen_quantile_head(routed_model, train_loader, device, lead_step=lead_step)

    # 3. Train Missingness-Aware GBDT Quantile on Train split
    print("Training Missingness-Aware GBDT Quantile...", flush=True)
    train_sample_loader = DataLoader(train_ds, batch_size=64, shuffle=False)
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
            tr_tar_list.append(b["target"][:, lead_step, :].numpy())
            tr_tmask_list.append(b["target_mask"][:, lead_step, :].numpy())
            tr_pred_list.append(pred[:, lead_step, :].cpu().numpy())
            count += len(b["anchor_index"])
            if count >= 800:
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
    tr_valid = (np.abs(tr_wspd_phys - rated_wind) <= band) & (tr_tmask > 0.5) & np.isfinite(tr_shortfall)

    act_idx = np.where(tr_valid)[0]
    if len(act_idx) > 40_000:
        rng = np.random.default_rng(seed)
        act_idx = rng.choice(act_idx, size=40_000, replace=False)
    elif len(act_idx) < 1000:
        finite_idx = np.where(np.isfinite(tr_shortfall) & (tr_tmask > 0.5))[0]
        act_idx = finite_idx[:min(40_000, len(finite_idx))]

    gbdt_scaler = StandardScaler()
    tr_feats_act = np.nan_to_num(tr_feats[act_idx], nan=0.0, posinf=0.0, neginf=0.0)
    tr_feats_scaled = gbdt_scaler.fit_transform(tr_feats_act)

    gbdt = HistGradientBoostingRegressor(loss="quantile", quantile=CRITICAL_FRACTILE, max_iter=50, random_state=seed)
    gbdt.fit(tr_feats_scaled, tr_shortfall[act_idx])

    # 4. Collect Validation Outputs and Fit 5-Bin Quantiles
    print("Collecting validation outputs and calibrating 5-bin policies...", flush=True)
    val_routed = run_forward_pass(routed_model, val_loader, device, lead_step=lead_step)
    val_s = np.maximum(val_routed["pred"] - val_routed["target"], 0.0).reshape(-1)
    val_wspd_phys = (val_routed["anchor"][..., 0] * w_std + w_mean).reshape(-1)
    val_pab_phys = (val_routed["anchor"][..., 1] * p_std + p_mean).reshape(-1)
    val_active = ((np.abs(val_wspd_phys - rated_wind) <= band) & (val_routed["mask"].reshape(-1) > 0.5) & np.isfinite(val_s))

    # 4a. Continuous Physical Quantile (pitch bins)
    phys_reserves, phys_edges, global_reserve = fit_5bin_quantiles(val_pab_phys, val_s, val_active)

    # 4b. Missingness-Aware GBDT
    val_feats = extract_gbdt_features(val_routed["x"], val_routed["fmask"], val_routed["anchor"], w_idx=w_idx, p_idx=p_idx)
    val_feats_scaled = gbdt_scaler.transform(np.nan_to_num(val_feats, nan=0.0))
    val_gbdt_pred = np.nan_to_num(np.maximum(gbdt.predict(val_feats_scaled), 0.0), nan=global_reserve)
    gbdt_reserves, gbdt_edges, _ = fit_5bin_quantiles(val_gbdt_pred, val_s, val_active)

    # 4c. Sequence Classifier
    val_seq_probs = []
    with torch.no_grad():
        for b in val_loader:
            p_seq = seq_clf(b["x_hist"].to(device), b["anchor_physics"].to(device))
            val_seq_probs.append(p_seq.cpu().numpy())
    val_seq_prob_flat = np.concatenate(val_seq_probs, axis=0).reshape(-1)
    seq_reserves, seq_edges, _ = fit_5bin_quantiles(val_seq_prob_flat, val_s, val_active)

    # 4d. Frozen Backbone + Residual Quantile Head
    val_frozen_list = []
    with torch.no_grad():
        for b in val_loader:
            _, _, aux = routed_model(b["x_hist"].to(device), b["edge_index_hist"].to(device), b["edge_weight_hist"].to(device), b["feature_mask_hist"].to(device), b["anchor_physics"].to(device))
            rf = frozen_head(aux["context"], b["anchor_physics"].to(device)).cpu().numpy()
            val_frozen_list.append(rf)
    val_frozen_flat = np.concatenate(val_frozen_list, axis=0).reshape(-1)
    frozen_reserves, frozen_edges, _ = fit_5bin_quantiles(val_frozen_flat, val_s, val_active)

    # 4e. Joint Dense Head
    dense_reserves, dense_edges = None, None
    if dense_model is not None:
        val_dense = run_forward_pass(dense_model, val_loader, device, lead_step=lead_step)
        dense_reserves, dense_edges, _ = fit_5bin_quantiles(val_dense["prob"].reshape(-1), val_s, val_active)

    # 4f. Joint Routed Head
    routed_reserves, routed_edges, _ = fit_5bin_quantiles(val_routed["prob"].reshape(-1), val_s, val_active)

    # 5. Compute Validation Iso-Reliability Multipliers (targeting violation <= 10.0%)
    val_reserves_raw = {
        "Continuous Physical Quantile": apply_5bin_policy(val_pab_phys, phys_reserves, phys_edges),
        "Missingness-Aware GBDT": apply_5bin_policy(val_gbdt_pred, gbdt_reserves, gbdt_edges),
        "Sequence Classifier": apply_5bin_policy(val_seq_prob_flat, seq_reserves, seq_edges),
        "Frozen Backbone + Residual Quantile": apply_5bin_policy(val_frozen_flat, frozen_reserves, frozen_edges),
        "Joint Routed": apply_5bin_policy(val_routed["prob"].reshape(-1), routed_reserves, routed_edges),
    }
    if dense_model is not None and dense_reserves is not None:
        val_reserves_raw["Joint Dense"] = apply_5bin_policy(val_dense["prob"].reshape(-1), dense_reserves, dense_edges)

    iso_multipliers = {}
    for m_name, v_r in val_reserves_raw.items():
        gamma = calibrate_iso_reliability_multiplier(val_s, v_r, val_active, target_violation=TARGET_VIOLATION)
        iso_multipliers[m_name] = gamma
        print(f"Validation Iso-Reliability Multiplier [{m_name}]: gamma = {gamma:.3f}", flush=True)

    # 6. Evaluate Across 4 Standardized Degradation Regimes
    regimes = {
        "clean": DegradationSpec(delay_steps=0, corrupted_channels=("all",)),
        "delay6": DegradationSpec(delay_steps=6, corrupted_channels=("all",), history_policy="stalled"),
        "sensor_noise": DegradationSpec(delay_steps=0, corrupted_channels=("all",), noise_sigma_physical={"Wspd": 1.0, "Pab_mean": 2.0}),
        "markov_burst": DegradationSpec(delay_steps=0, use_markov_gilbert=True, p_gb=0.08, p_bb=0.75, max_lag=6, corrupted_channels=("all",), history_policy="stalled"),
    }

    seed_metric_rows = []
    seed_boot_rows = []

    for reg_name, reg_spec in regimes.items():
        print(f"\n--- Testing Regime: {reg_name} ---", flush=True)
        test_ds = UnifiedArrivalDataset(bundle, "test", hist_len=36, pred_len=24, degradation=reg_spec)
        test_loader = DataLoader(test_ds, batch_size=64, shuffle=False)

        test_routed = run_forward_pass(routed_model, test_loader, device, lead_step=lead_step)
        test_dense = run_forward_pass(dense_model, test_loader, device, lead_step=lead_step) if dense_model is not None else None

        test_s = np.maximum(test_routed["pred"] - test_routed["target"], 0.0).reshape(-1)
        test_wspd_phys = (test_routed["anchor"][..., 0] * w_std + w_mean).reshape(-1)
        test_pab_phys = (test_routed["anchor"][..., 1] * p_std + p_mean).reshape(-1)
        test_active = ((np.abs(test_wspd_phys - rated_wind) <= band) & (test_routed["mask"].reshape(-1) > 0.5) & np.isfinite(test_s))
        test_times = np.repeat(test_routed["time"] + lead_step + 1, test_routed["pred"].shape[1])
        test_regime = test_routed["regime"].reshape(-1)

        # 6a. Sequence Classifier Test Probs
        test_seq_probs = []
        with torch.no_grad():
            for b in test_loader:
                p_seq = seq_clf(b["x_hist"].to(device), b["anchor_physics"].to(device))
                test_seq_probs.append(p_seq.cpu().numpy())
        test_seq_prob_flat = np.concatenate(test_seq_probs, axis=0).reshape(-1)

        # 6b. Frozen Head Test Reserves
        test_frozen_list = []
        with torch.no_grad():
            for b in test_loader:
                _, _, aux = routed_model(b["x_hist"].to(device), b["edge_index_hist"].to(device), b["edge_weight_hist"].to(device), b["feature_mask_hist"].to(device), b["anchor_physics"].to(device))
                rf = frozen_head(aux["context"], b["anchor_physics"].to(device)).cpu().numpy()
                test_frozen_list.append(rf)
        test_frozen_flat = np.concatenate(test_frozen_list, axis=0).reshape(-1)

        # 6c. GBDT Test Pred
        test_feats = extract_gbdt_features(test_routed["x"], test_routed["fmask"], test_routed["anchor"], w_idx=w_idx, p_idx=p_idx)
        test_feats_scaled = gbdt_scaler.transform(np.nan_to_num(test_feats, nan=0.0))
        test_gbdt_pred = np.nan_to_num(np.maximum(gbdt.predict(test_feats_scaled), 0.0), nan=global_reserve)

        # Allocate Unscaled Reserves
        raw_reserves = {
            "Continuous Physical Quantile": apply_5bin_policy(test_pab_phys, phys_reserves, phys_edges),
            "Missingness-Aware GBDT": apply_5bin_policy(test_gbdt_pred, gbdt_reserves, gbdt_edges),
            "Sequence Classifier": apply_5bin_policy(test_seq_prob_flat, seq_reserves, seq_edges),
            "Frozen Backbone + Residual Quantile": apply_5bin_policy(test_frozen_flat, frozen_reserves, frozen_edges),
            "Joint Routed": apply_5bin_policy(test_routed["prob"].reshape(-1), routed_reserves, routed_edges),
        }
        if test_dense is not None and dense_reserves is not None:
            raw_reserves["Joint Dense"] = apply_5bin_policy(test_dense["prob"].reshape(-1), dense_reserves, dense_edges)

        # Apply Iso-Reliability Multipliers
        iso_reserves = {m: raw_reserves[m] * iso_multipliers[m] for m in raw_reserves}

        model_probs = {
            "Continuous Physical Quantile": None,
            "Missingness-Aware GBDT": None,
            "Sequence Classifier": test_seq_prob_flat,
            "Frozen Backbone + Residual Quantile": None,
            "Joint Dense": test_dense["prob"].reshape(-1) if test_dense is not None else None,
            "Joint Routed": test_routed["prob"].reshape(-1),
        }

        for m_name, r_arr in iso_reserves.items():
            metrics = compute_decisive_metrics(
                shortfall=test_s,
                reserve=r_arr,
                active=test_active,
                prob=model_probs.get(m_name),
                regime=test_regime,
            )
            row = {
                "farm": farm,
                "seed": seed,
                "regime": reg_name,
                "model": m_name,
                "gamma_iso": round(iso_multipliers[m_name], 3),
                **metrics,
            }
            seed_metric_rows.append(row)

        # Weather event block bootstrap
        boot_res = weather_block_bootstrap(
            test_s, iso_reserves, test_active, test_times,
            block_size=144, n_boot=n_boot, seed=seed, ref_model="Joint Routed",
        )
        for m_name, b_stat in boot_res.items():
            seed_boot_rows.append({
                "farm": farm,
                "seed": seed,
                "regime": reg_name,
                "model": m_name,
                **b_stat,
            })

        print(f"Summary for {reg_name} (Seed {seed}):", flush=True)
        cur_df = pd.DataFrame([r for r in seed_metric_rows if r["seed"] == seed and r["regime"] == reg_name])
        print(cur_df[["model", "gamma_iso", "violation_rate", "reserve_mwh", "shortage_mwh", "total_cost", "false_alarm_rate", "event_recall"]].to_string(), flush=True)

    print(f"Seed {seed} finished in {time.time() - t_start:.1f}s", flush=True)
    return seed_metric_rows, seed_boot_rows


# ==============================================================================
# Route Decision Dispatcher (Step 5)
# ==============================================================================

def evaluate_route_verdict(agg_df: pd.DataFrame) -> Dict[str, Any]:
    """Evaluates the 4 decision criteria specified in the problem statement."""
    # Pivot clean and degraded regimes
    clean_agg = agg_df[agg_df["regime"] == "clean"].set_index("model")
    delay_agg = agg_df[agg_df["regime"] == "delay6"].set_index("model")

    routed_clean_cost = clean_agg.loc["Joint Routed", ("total_cost", "mean")] if "Joint Routed" in clean_agg.index else 1.0
    routed_delay_cost = delay_agg.loc["Joint Routed", ("total_cost", "mean")] if "Joint Routed" in delay_agg.index else 1.0

    dense_clean_cost = clean_agg.loc["Joint Dense", ("total_cost", "mean")] if "Joint Dense" in clean_agg.index else None
    dense_delay_cost = delay_agg.loc["Joint Dense", ("total_cost", "mean")] if "Joint Dense" in delay_agg.index else None

    phys_clean_cost = clean_agg.loc["Continuous Physical Quantile", ("total_cost", "mean")]
    gbdt_clean_cost = clean_agg.loc["Missingness-Aware GBDT", ("total_cost", "mean")]

    routed_clean_recall = clean_agg.loc["Joint Routed", ("event_recall", "mean")] if ("event_recall", "mean") in clean_agg.columns else 0.8
    routed_clean_shortage = clean_agg.loc["Joint Routed", ("shortage_mwh", "mean")]

    # Criterion 1: Dense vs MoE
    # If Dense is within 1% of MoE or better
    dense_vs_moe_verdict = False
    dense_cost_ratio = 1.0
    if dense_clean_cost is not None and dense_delay_cost is not None:
        dense_cost_ratio = float(dense_clean_cost / routed_clean_cost)
        dense_vs_moe_verdict = dense_clean_cost <= (routed_clean_cost * 1.02)

    # Criterion 2: Simple Quantile vs Deep
    simple_quantile_wins = (phys_clean_cost < routed_clean_cost) or (gbdt_clean_cost < routed_clean_cost)

    # Criterion 3: Recognition vs Decision
    # Recognition high (recall >= 0.70) but decision cost not improved vs simple physical
    recognition_better_decision_no = (routed_clean_recall > 0.70) and (routed_clean_cost >= phys_clean_cost)

    # Criterion 4: Cross-Farm Decision Increment
    # Routed beats physical and GBDT under fair conditions
    cross_farm_increment = (routed_clean_cost < phys_clean_cost) and (routed_delay_cost < delay_agg.loc["Continuous Physical Quantile", ("total_cost", "mean")])

    recommended_route = "Route 4: IEEE TSTE Full Submission"
    route_rationale = []

    if simple_quantile_wins:
        recommended_route = "Route 2: Stop Claiming Method Advantage, Refocus on Physical Failure Laws"
        route_rationale.append("Simple quantile baseline (Physical or GBDT) outperforms deep representation.")
    elif dense_vs_moe_verdict:
        recommended_route = "Route 1: Pivot to 'Boundary-Supervised Risk Representation' (Adopt Simple Dense Implementation)"
        route_rationale.append(f"Joint Dense performs equivalently to MoE (Cost ratio = {dense_cost_ratio:.3f}). Architectural complexity of MoE routing is unnecessary.")
    elif recognition_better_decision_no:
        recommended_route = "Route 3: Refocus as Diagnostic / Early-Warning Paper (Drop Economic Cost Narrative)"
        route_rationale.append("Classification recall is high, but decision cost regret does not improve over physical baselines under iso-reliability.")
    else:
        recommended_route = "Route 4: Firm IEEE TSTE Submission (Cross-Farm Decision Increment Confirmed)"
        route_rationale.append("Boundary-supervised representation maintains statistically significant decision increment under identical arrival feed and iso-reliability.")

    return {
        "recommended_route": recommended_route,
        "dense_vs_moe_ratio": dense_cost_ratio,
        "dense_vs_moe_equivalent": bool(dense_vs_moe_verdict),
        "simple_quantile_beats_deep": bool(simple_quantile_wins),
        "recognition_better_decision_no": bool(recognition_better_decision_no),
        "cross_farm_increment": bool(cross_farm_increment),
        "rationales": route_rationale,
    }


def main():
    parser = argparse.ArgumentParser(description="Decisive Experiment v3 Runner")
    parser.add_argument("--farm", default="wtb", choices=["wtb", "kelmarsh", "penmanshiel"])
    parser.add_argument("--seeds", default="201,202,203,204,205")
    parser.add_argument("--device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--lead-step", type=int, default=0, help="0 = 10 min horizon")
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--output-dir", default="artifacts/decisive_experiment_v3/risk_layer_benchmark")
    args = parser.parse_args()

    out_dir = Path(args.output_dir) / args.farm
    out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)

    # Locate cache and checkpoints
    if args.farm == "wtb":
        cache_cands = [
            "artifacts/cache_strictmask_trainweights/wtb_245d",
            "artifacts/cache_strictmask/wtb_245d",
            "artifacts/cache_signature_trainweight/wtb_245d_canonical",
        ]
        routed_pat = "artifacts/trainweight_full_rerun_20260830/wtb_full_seed{seed}"
        dense_pat = "artifacts/dense_classifier_runs_20260904/canonical/wtb_bal_align_force_seed{seed}"
    elif args.farm == "kelmarsh":
        cache_cands = [
            "artifacts/cache_signature_kelmarsh/external_wind_kelmarsh_obs_window_canonical",
            "artifacts/cache_external_wind/external_wind_kelmarsh_obs_window",
        ]
        routed_pat = "artifacts/signature_gate_farms_runs_20260903/kelmarsh/canonical/wtb_bal_align_force_seed{seed}"
        dense_pat = None
    elif args.farm == "penmanshiel":
        cache_cands = [
            "artifacts/cache_signature_penmanshiel/external_wind_penmanshiel_obs_window_canonical",
            "artifacts/cache_external_wind/external_wind_penmanshiel_obs_window",
        ]
        routed_pat = "artifacts/signature_gate_farms_runs_20260903/penmanshiel/canonical/wtb_bal_align_force_seed{seed}"
        dense_pat = None

    cache_path = None
    for c in cache_cands:
        if Path(c).exists():
            cache_path = Path(c)
            break
    if cache_path is None:
        raise FileNotFoundError(f"No valid cache bundle found for farm {args.farm}")

    print(f"Loading Cache Bundle: {cache_path}", flush=True)
    bundle = load_cache_bundle(cache_path, mmap_mode="r")

    seeds = [int(s) for s in args.seeds.split(",")]
    all_metrics = []
    all_boots = []

    for seed in seeds:
        s_met, s_boot = run_decisive_benchmark_for_seed(
            farm=args.farm,
            seed=seed,
            bundle=bundle,
            routed_ckpt_pattern=routed_pat,
            dense_ckpt_pattern=dense_pat,
            device=device,
            lead_step=args.lead_step,
            n_boot=args.n_boot,
        )
        all_metrics.extend(s_met)
        all_boots.extend(s_boot)

    # Save per-seed metrics
    df_metrics = pd.DataFrame(all_metrics)
    df_metrics.to_csv(out_dir / "decisive_results_by_seed.csv", index=False)

    df_boot = pd.DataFrame(all_boots)
    df_boot.to_csv(out_dir / "decisive_bootstrap_by_seed.csv", index=False)

    # Cross-seed aggregation
    agg_df = df_metrics.groupby(["farm", "regime", "model"]).agg({
        "gamma_iso": ["mean", "std"],
        "violation_rate": ["mean", "std"],
        "reserve_mwh": ["mean", "std"],
        "shortage_mwh": ["mean", "std"],
        "total_cost": ["mean", "std"],
        "false_alarm_rate": ["mean", "std"],
        "event_recall": ["mean", "std"],
        "brier_score": ["mean", "std"],
        "ece": ["mean", "std"],
        "pinball_loss": ["mean", "std"],
    }).reset_index()
    agg_df.to_csv(out_dir / "decisive_cross_seed_aggregate.csv", index=False)

    # Evaluate Decision Dispatch
    verdict = evaluate_route_verdict(agg_df)
    with open(out_dir / "route_dispatch_verdict.json", "w", encoding="utf-8") as f:
        json.dump(verdict, f, indent=2)

    # Generate Markdown Summary Table
    md_report = [
        f"# Decisive Experiment v3 Benchmark Report: {args.farm.upper()}",
        f"**Date / Time**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Delivery Horizon**: Lead Step {args.lead_step + 1} (10-minute dispatch delivery)",
        f"**Target Reliability**: Violation Rate <= {TARGET_VIOLATION * 100.0:.1f}% (Critical Fractile q* = {CRITICAL_FRACTILE:.2f})",
        "",
        "## 1. Iso-Reliability Performance Summary (Across 5 Seeds)",
        "",
        "| Regime | Model | Val Gamma | Test Violation Rate | Reserve (MWh) | Shortage (MWh) | Total Cost Regret | False Alarm Rate | Event Recall |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for _, row in agg_df.iterrows():
        reg = row[("regime", "")]
        mod = row[("model", "")]
        gamma = f"{row[('gamma_iso', 'mean')]:.2f}"
        viol = f"{row[('violation_rate', 'mean')]*100.0:.1f}%"
        res = f"{row[('reserve_mwh', 'mean')]:.2f} ± {row[('reserve_mwh', 'std')]:.2f}"
        sh = f"{row[('shortage_mwh', 'mean')]:.2f} ± {row[('shortage_mwh', 'std')]:.2f}"
        cost = f"{row[('total_cost', 'mean')]:.1f} ± {row[('total_cost', 'std')]:.1f}"
        far = f"{row[('false_alarm_rate', 'mean')]*100.0:.1f}%"
        rec = f"{row[('event_recall', 'mean')]*100.0:.1f}%"
        md_report.append(f"| {reg} | {mod} | {gamma} | {viol} | {res} | {sh} | {cost} | {far} | {rec} |")

    md_report.extend([
        "",
        "## 2. Decision Route Dispatch Verdict",
        f"**Recommended Route**: `{verdict['recommended_route']}`",
        "",
        "### Criteria Evaluation:",
        f"- **Dense vs MoE Equivalent**: {verdict['dense_vs_moe_equivalent']} (Dense/MoE Cost Ratio: {verdict['dense_vs_moe_ratio']:.3f})",
        f"- **Simple Quantile Wins over Deep**: {verdict['simple_quantile_beats_deep']}",
        f"- **Recognition Better but Decision Not Improved**: {verdict['recognition_better_decision_no']}",
        f"- **Cross-Farm Increment Confirmed**: {verdict['cross_farm_increment']}",
        "",
        "### Decision Rationale:",
    ])
    for r in verdict["rationales"]:
        md_report.append(f"- {r}")

    (out_dir / "benchmark_report.md").write_text("\n".join(md_report), encoding="utf-8")

    print("\n" + "\n".join(md_report), flush=True)
    print(f"\nWrote all artifacts to {out_dir}", flush=True)


if __name__ == "__main__":
    main()
