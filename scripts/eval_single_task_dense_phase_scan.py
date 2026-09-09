"""Boundary Phase Scan and Decisive Ablation: Single-Task Dense vs. Multi-Task MoE.

Evaluates 5 seeds (201-205) across the full 30-condition degradation grid:
- tau in [0, 10, 20, 30, 60] min (lags [0, 1, 2, 3, 6])
- h in [1, 3, 6] (leads [0, 2, 5])
- Channel modes: 'all' vs 'no_pitch'

Directly compares:
1. Deterministic Continuous Physical Quantile (Clean unadapted)
2. Recalibrated Physical Quantile (Condition-matching validation calibration)
3. Multi-Task MoE Frozen Backbone + Residual Quantile Head
4. Multi-Task MoE Joint Routed Head
5. Single-Task Capacity-Matched Dense Backbone + Residual Quantile Head

Also evaluates Table 4 Selective Decision Abstention under Delay-6 (tau=60m, h=1)
with Random and Uniform Margin Inflation controls.

Produces:
- artifacts/single_task_dense_vs_multitask_moe_ablation.csv (Table 3 mirror + dense ablation)
- artifacts/single_task_dense_vs_multitask_moe_risk_coverage.csv (Table 4 mirror + dense ablation)
"""
from __future__ import annotations

import os
import sys

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["PYTHONUNBUFFERED"] = "1"

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from windfarm_moe.arrival_feed import (
    DegradationSpec,
    UnifiedArrivalDataset,
)
from windfarm_moe.data import CacheBundle, load_cache_bundle
from windfarm_moe.mechanism_intervention import _load_model_from_checkpoint
from scripts.decisive_fair_risk_benchmark import (
    CRITICAL_FRACTILE,
    TARGET_VIOLATION,
    N_BINS,
    DT,
    RHO,
    QuantileResidualHead,
    fit_5bin_quantiles,
    apply_5bin_policy,
    find_iso_reliability_multiplier,
    compute_decisive_metrics,
)
from scripts.run_boundary_phase_scan import evaluate_frozen_threshold_abstention


def train_frozen_quantile_head_dynamic(
    model: nn.Module,
    train_loader: DataLoader,
    device: torch.device,
    lead_step: int = 0,
    max_cache_batches: int = 150,
    epochs: int = 5,
    lr: float = 1e-3,
) -> QuantileResidualHead:
    """Trains residual quantile head adapting dynamically to any backbone hidden_dim."""
    for p in model.parameters():
        p.requires_grad = False
    model.eval()

    cached_ctx, cached_anc, cached_shortfall = [], [], []
    with torch.no_grad():
        count = 0
        for batch in train_loader:
            x_hist = batch["x_hist"].to(device)
            edge_index = batch["edge_index_hist"].to(device)
            edge_weight = batch["edge_weight_hist"].to(device)
            feature_mask = batch["feature_mask_hist"].to(device)
            anchor_phys = batch["anchor_physics"].to(device)
            target = batch["target"].to(device)

            pred, _, aux = model(x_hist, edge_index, edge_weight, feature_mask, anchor_phys)
            context = aux["context"]
            y_pred = pred[:, lead_step, :]
            y_true = target[:, lead_step, :]
            shortfall = torch.clamp(y_pred - y_true, min=0.0)

            cached_ctx.append(context.detach())
            cached_anc.append(anchor_phys.detach())
            cached_shortfall.append(shortfall.detach())

            count += 1
            if count >= max_cache_batches:
                break

    all_ctx = torch.cat(cached_ctx, dim=0)
    all_anc = torch.cat(cached_anc, dim=0)
    all_s = torch.cat(cached_shortfall, dim=0)

    context_dim = int(all_ctx.shape[-1])
    phys_dim = int(all_anc.shape[-1])
    head = QuantileResidualHead(context_dim=context_dim, phys_dim=phys_dim, hidden_dim=64).to(device)
    optimizer = torch.optim.Adam(head.parameters(), lr=lr)

    N_samples = all_ctx.size(0)
    batch_sz = 64
    head.train()
    for _ in range(epochs):
        perm = torch.randperm(N_samples)
        for i in range(0, N_samples, batch_sz):
            idx = perm[i : i + batch_sz]
            b_ctx = all_ctx[idx]
            b_anc = all_anc[idx]
            b_s = all_s[idx]

            pred_r = head(b_ctx, b_anc)
            u = b_s - pred_r
            loss = torch.maximum(CRITICAL_FRACTILE * u, (CRITICAL_FRACTILE - 1.0) * u).mean()

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

    head.eval()
    return head


def run_joint_multilead_pass(
    model: nn.Module,
    frozen_heads: Dict[int, nn.Module],
    loader: DataLoader,
    device: torch.device,
    lead_steps: List[int] = [0, 2, 5],
) -> Dict[str, Any]:
    """Runs a single forward pass over loader, extracting predictions and frozen heads for all leads."""
    model.eval()
    for h in frozen_heads.values():
        h.eval()

    all_pred = {l: [] for l in lead_steps}
    all_target = {l: [] for l in lead_steps}
    all_mask = {l: [] for l in lead_steps}
    all_frozen_raw = {l: [] for l in lead_steps}
    all_anchor, all_prob, all_regime = [], [], []

    with torch.no_grad():
        for batch in loader:
            x_hist = batch["x_hist"].to(device)
            edge_index = batch["edge_index_hist"].to(device)
            edge_weight = batch["edge_weight_hist"].to(device)
            feature_mask = batch["feature_mask_hist"].to(device)
            anchor_phys = batch["anchor_physics"].to(device)
            target = batch["target"].to(device)

            pred, gate_prob, aux = model(x_hist, edge_index, edge_weight, feature_mask, anchor_phys)
            context = aux["context"]
            prob = (
                gate_prob[..., 2].cpu().numpy()
                if gate_prob is not None and gate_prob.shape[-1] >= 3
                else np.zeros((pred.shape[0], pred.shape[2]))
            )

            all_anchor.append(anchor_phys.cpu().numpy())
            all_prob.append(prob)
            all_regime.append(batch["regime_primary"].cpu().numpy())

            for lead in lead_steps:
                all_pred[lead].append(pred[:, lead, :].cpu().numpy())
                all_target[lead].append(target[:, lead, :].cpu().numpy())
                all_mask[lead].append(batch["target_mask"][:, lead, :].cpu().numpy())
                rf = frozen_heads[lead](context, anchor_phys).cpu().numpy()
                all_frozen_raw[lead].append(rf)

    return {
        "anchor": np.concatenate(all_anchor, axis=0),
        "prob": np.concatenate(all_prob, axis=0),
        "regime": np.concatenate(all_regime, axis=0),
        "pred": {l: np.concatenate(all_pred[l], axis=0) for l in lead_steps},
        "target": {l: np.concatenate(all_target[l], axis=0) for l in lead_steps},
        "mask": {l: np.concatenate(all_mask[l], axis=0) for l in lead_steps},
        "frozen_raw": {l: np.concatenate(all_frozen_raw[l], axis=0).reshape(-1) for l in lead_steps},
    }


def run_dense_phase_scan_for_seed(
    farm: str,
    seed: int,
    bundle: CacheBundle,
    routed_ckpt_pattern: str,
    dense_ckpt_pattern: str,
    device: torch.device,
    lags: List[int] = [0, 1, 2, 3, 6],
    channel_modes: List[str] = ["all", "no_pitch"],
    lead_steps: List[int] = [0, 2, 5],
    abstention_coverages: Tuple[float, ...] = (0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 1.00),
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Runs 30-condition phase scan comparing Single-Task Dense vs Multi-Task MoE for one seed."""
    print(f"\n=======================================================", flush=True)
    print(f"Starting Dense vs MoE Phase Scan for Seed {seed} on {farm.upper()}", flush=True)
    print(f"=======================================================", flush=True)

    # 1. Load Pretrained Models
    routed_path = Path(routed_ckpt_pattern.format(seed=seed))
    dense_path = Path(dense_ckpt_pattern.format(seed=seed))

    print(f"Loading Multi-Task MoE from: {routed_path}", flush=True)
    routed_model = _load_model_from_checkpoint(routed_path, bundle, device)
    routed_model.eval()

    print(f"Loading Single-Task Dense from: {dense_path}", flush=True)
    dense_model = _load_model_from_checkpoint(dense_path, bundle, device)
    dense_model.eval()

    rated_wind = 10.5
    band = 1.0
    feat_names = list(bundle.metadata.get("feature_names", []))
    w_mean = float(bundle.metadata["physics_model_stats"]["0"]["mean"])
    w_std = float(bundle.metadata["physics_model_stats"]["0"]["std"])
    p_mean = float(bundle.metadata["physics_model_stats"]["1"]["mean"])
    p_std = float(bundle.metadata["physics_model_stats"]["1"]["std"])
    pitch_withheld_tuple = tuple(ch for ch in ("Pab_mean", "Pab_std") if ch in feat_names)

    # 2. Train Separate Frozen Quantile Heads for Each Model on Clean Data
    print("Training horizon-specific Frozen Backbone Quantile Heads on clean train split...", flush=True)
    train_clean_ds = UnifiedArrivalDataset(bundle, "train", hist_len=36, pred_len=24, degradation=DegradationSpec(delay_steps=0))
    train_clean_loader = DataLoader(train_clean_ds, batch_size=64, shuffle=True)

    frozen_heads_moe: Dict[int, nn.Module] = {}
    frozen_heads_dense: Dict[int, nn.Module] = {}
    for lead in lead_steps:
        lead_m = (lead + 1) * 10
        print(f"  Training MoE Frozen Quantile Head for lead_step={lead} (h={lead_m}m)...", flush=True)
        frozen_heads_moe[lead] = train_frozen_quantile_head_dynamic(routed_model, train_clean_loader, device=device, lead_step=lead)

        print(f"  Training Dense Frozen Quantile Head for lead_step={lead} (h={lead_m}m)...", flush=True)
        frozen_heads_dense[lead] = train_frozen_quantile_head_dynamic(dense_model, train_clean_loader, device=device, lead_step=lead)

    # 3. Precompute Condition-Matching Validation Calibrations across all (lag, channel_mode)
    print("Precomputing condition-matching validation calibrations...", flush=True)
    val_calibrations: Dict[Tuple[int, int, str], Dict[str, Any]] = {}
    clean_phys_calib: Dict[int, Dict[str, Any]] = {}

    for lag in lags:
        for ch_mode in channel_modes:
            withheld = pitch_withheld_tuple if ch_mode == "no_pitch" else ()
            v_spec = DegradationSpec(
                delay_steps=lag,
                corrupted_channels=("all",),
                withheld_channels=withheld,
                history_policy="stalled" if lag > 0 else "shifted",
            )
            val_ds = UnifiedArrivalDataset(bundle, "val", hist_len=36, pred_len=24, degradation=v_spec)
            val_loader = DataLoader(val_ds, batch_size=64, shuffle=False)

            v_out_moe = run_joint_multilead_pass(routed_model, frozen_heads_moe, val_loader, device, lead_steps)
            v_out_dense = run_joint_multilead_pass(dense_model, frozen_heads_dense, val_loader, device, lead_steps)

            v_wspd = (v_out_moe["anchor"][..., 0] * w_std + w_mean).reshape(-1)
            v_pab = (v_out_moe["anchor"][..., 1] * p_std + p_mean).reshape(-1)
            v_prob_moe = v_out_moe["prob"].reshape(-1)

            for lead in lead_steps:
                # Target shortfall from MoE prediction
                v_s_moe = np.maximum(v_out_moe["pred"][lead] - v_out_moe["target"][lead], 0.0).reshape(-1)
                v_s_dense = np.maximum(v_out_dense["pred"][lead] - v_out_dense["target"][lead], 0.0).reshape(-1)

                v_act_moe = ((np.abs(v_wspd - rated_wind) <= band) & (v_out_moe["mask"][lead].reshape(-1) > 0.5) & np.isfinite(v_s_moe))
                v_act_dense = ((np.abs(v_wspd - rated_wind) <= band) & (v_out_dense["mask"][lead].reshape(-1) > 0.5) & np.isfinite(v_s_dense))

                # Physical Rule calibration
                phys_feat = v_pab if ch_mode == "all" else v_wspd
                p_res, p_edg, glob_res = fit_5bin_quantiles(phys_feat, v_s_moe, v_act_moe)
                v_phys_raw = apply_5bin_policy(phys_feat, p_res, p_edg)
                g_phys, d_phys, _ = find_iso_reliability_multiplier(v_s_moe, v_phys_raw, v_act_moe, target_violation=TARGET_VIOLATION)

                if lag == 0 and ch_mode == "all":
                    clean_phys_calib[lead] = {
                        "reserves": p_res,
                        "edges": p_edg,
                        "gamma": g_phys,
                        "delta": d_phys,
                        "global_reserve": glob_res,
                    }

                # Multi-Task MoE Frozen Backbone Head
                v_froz_moe_raw = v_out_moe["frozen_raw"][lead]
                froz_moe_res, froz_moe_edg, _ = fit_5bin_quantiles(v_froz_moe_raw, v_s_moe, v_act_moe)
                v_froz_moe_bin = apply_5bin_policy(v_froz_moe_raw, froz_moe_res, froz_moe_edg)
                g_froz_moe, d_froz_moe, _ = find_iso_reliability_multiplier(v_s_moe, v_froz_moe_bin, v_act_moe, target_violation=TARGET_VIOLATION)

                # Multi-Task MoE Joint Routed Head
                rout_res, rout_edg, _ = fit_5bin_quantiles(v_prob_moe, v_s_moe, v_act_moe)
                v_rout_bin = apply_5bin_policy(v_prob_moe, rout_res, rout_edg)
                g_rout, d_rout, _ = find_iso_reliability_multiplier(v_s_moe, v_rout_bin, v_act_moe, target_violation=TARGET_VIOLATION)

                # Single-Task Dense Frozen Backbone Head
                v_froz_dense_raw = v_out_dense["frozen_raw"][lead]
                froz_dense_res, froz_dense_edg, _ = fit_5bin_quantiles(v_froz_dense_raw, v_s_dense, v_act_dense)
                v_froz_dense_bin = apply_5bin_policy(v_froz_dense_raw, froz_dense_res, froz_dense_edg)
                g_froz_dense, d_froz_dense, _ = find_iso_reliability_multiplier(v_s_dense, v_froz_dense_bin, v_act_dense, target_violation=TARGET_VIOLATION)

                # Validation uncertainty and thresholds for abstention
                eps = 1e-7
                p_clamp = np.clip(v_prob_moe, eps, 1.0 - eps)
                v_ent = -(p_clamp * np.log2(p_clamp) + (1.0 - p_clamp) * np.log2(1.0 - p_clamp))
                v_spr_moe = np.abs(v_phys_raw - v_froz_moe_bin)
                v_hyb_moe = v_spr_moe + 50.0 * v_ent

                v_spr_dense = np.abs(v_phys_raw - v_froz_dense_bin)

                v_ent_act = v_ent[v_act_moe]
                v_spr_moe_act = v_spr_moe[v_act_moe]
                v_hyb_moe_act = v_hyb_moe[v_act_moe]
                v_spr_dense_act = v_spr_dense[v_act_dense]

                thresh_ent = {c: float(np.quantile(v_ent_act, c)) if c < 1.0 else np.inf for c in abstention_coverages}
                thresh_spr_moe = {c: float(np.quantile(v_spr_moe_act, c)) if c < 1.0 else np.inf for c in abstention_coverages}
                thresh_hyb_moe = {c: float(np.quantile(v_hyb_moe_act, c)) if c < 1.0 else np.inf for c in abstention_coverages}
                thresh_spr_dense = {c: float(np.quantile(v_spr_dense_act, c)) if c < 1.0 else np.inf for c in abstention_coverages}

                # Validation reserve baselines for ex-ante alpha computation
                P_rated = 1500.0
                v_pred_moe = v_out_moe["pred"][lead].reshape(-1)
                v_pred_dense = v_out_dense["pred"][lead].reshape(-1)
                v_aero_fb_moe = np.maximum(0.0, np.minimum(P_rated - v_pred_moe, P_rated))
                v_aero_fb_dense = np.maximum(0.0, np.minimum(P_rated - v_pred_dense, P_rated))

                v_r_phys = np.maximum(g_phys * v_phys_raw + d_phys, 0.0)
                v_r_fb_moe = np.maximum(v_r_phys, v_aero_fb_moe)
                v_r_fb_dense = np.maximum(v_r_phys, v_aero_fb_dense)

                v_r_froz_moe = np.maximum(g_froz_moe * v_froz_moe_bin + d_froz_moe, 0.0)
                v_r_rout = np.maximum(g_rout * v_rout_bin + d_rout, 0.0)
                v_r_froz_dense = np.maximum(g_froz_dense * v_froz_dense_bin + d_froz_dense, 0.0)

                def compute_val_alpha_dict(v_r_cand, v_fb, v_u, th_dict, act_mask):
                    a_dict = {}
                    v_r_sub = v_r_cand[act_mask]
                    v_fb_sub = v_fb[act_mask]
                    v_u_sub = v_u[act_mask]
                    base_mwh = float(np.sum(v_r_sub))
                    for c in abstention_coverages:
                        th = th_dict.get(c, np.inf)
                        mask = (v_u_sub <= th) if (c < 1.0 and not np.isinf(th)) else np.ones(len(v_u_sub), dtype=bool)
                        blended = np.where(mask, v_r_sub, v_fb_sub)
                        target_mwh = float(np.sum(blended))
                        a_dict[c] = float(target_mwh / max(base_mwh, 1e-6))
                    return a_dict

                alpha_val_moe_froz = compute_val_alpha_dict(v_r_froz_moe, v_r_fb_moe, v_hyb_moe, thresh_hyb_moe, v_act_moe)
                alpha_val_moe_rout = compute_val_alpha_dict(v_r_rout, v_r_fb_moe, v_hyb_moe, thresh_hyb_moe, v_act_moe)
                alpha_val_dense_froz = compute_val_alpha_dict(v_r_froz_dense, v_r_fb_dense, v_spr_dense, thresh_spr_dense, v_act_dense)

                val_calibrations[(lead, lag, ch_mode)] = {
                    "phys_res": p_res, "phys_edg": p_edg, "g_phys": g_phys, "d_phys": d_phys, "glob_res": glob_res,
                    "froz_moe_res": froz_moe_res, "froz_moe_edg": froz_moe_edg, "g_froz_moe": g_froz_moe, "d_froz_moe": d_froz_moe,
                    "rout_res": rout_res, "rout_edg": rout_edg, "g_rout": g_rout, "d_rout": d_rout,
                    "froz_dense_res": froz_dense_res, "froz_dense_edg": froz_dense_edg, "g_froz_dense": g_froz_dense, "d_froz_dense": d_froz_dense,
                    "thresh_ent": thresh_ent, "thresh_spr_moe": thresh_spr_moe, "thresh_hyb_moe": thresh_hyb_moe, "thresh_spr_dense": thresh_spr_dense,
                    "alpha_val_moe_froz": alpha_val_moe_froz,
                    "alpha_val_moe_rout": alpha_val_moe_rout,
                    "alpha_val_dense_froz": alpha_val_dense_froz,
                }

    # 4. Multi-Dimensional Grid Scan on Test Split
    print("Executing multidimensional grid scan on test set...", flush=True)
    scan_results = []
    abstention_results = []

    for lag in lags:
        for ch_mode in channel_modes:
            withheld = pitch_withheld_tuple if ch_mode == "no_pitch" else ()
            spec = DegradationSpec(
                delay_steps=lag,
                corrupted_channels=("all",),
                withheld_channels=withheld,
                history_policy="stalled" if lag > 0 else "shifted",
            )
            test_ds = UnifiedArrivalDataset(bundle, "test", hist_len=36, pred_len=24, degradation=spec)
            test_loader = DataLoader(test_ds, batch_size=64, shuffle=False)

            t_out_moe = run_joint_multilead_pass(routed_model, frozen_heads_moe, test_loader, device, lead_steps)
            t_out_dense = run_joint_multilead_pass(dense_model, frozen_heads_dense, test_loader, device, lead_steps)

            test_wspd = (t_out_moe["anchor"][..., 0] * w_std + w_mean).reshape(-1)
            test_pab = (t_out_moe["anchor"][..., 1] * p_std + p_mean).reshape(-1)
            test_prob_moe = t_out_moe["prob"].reshape(-1)
            test_regime = t_out_moe["regime"].reshape(-1)

            for lead in lead_steps:
                cond_id = f"lag{lag}_{ch_mode}_lead{lead}"
                print(f"  Evaluating condition: {cond_id} (Seed {seed})", flush=True)
                calib = val_calibrations[(lead, lag, ch_mode)]
                clean_cal = clean_phys_calib[lead]

                test_s_moe = np.maximum(t_out_moe["pred"][lead] - t_out_moe["target"][lead], 0.0).reshape(-1)
                test_s_dense = np.maximum(t_out_dense["pred"][lead] - t_out_dense["target"][lead], 0.0).reshape(-1)

                test_act_moe = ((np.abs(test_wspd - rated_wind) <= band) & (t_out_moe["mask"][lead].reshape(-1) > 0.5) & np.isfinite(test_s_moe))
                test_act_dense = ((np.abs(test_wspd - rated_wind) <= band) & (t_out_dense["mask"][lead].reshape(-1) > 0.5) & np.isfinite(test_s_dense))

                test_pred_moe = t_out_moe["pred"][lead].reshape(-1)
                test_pred_dense = t_out_dense["pred"][lead].reshape(-1)

                # Arm 1: Clean Physical (Deterministic Unadapted)
                clean_feat = test_pab if ch_mode == "all" else test_wspd
                r_phys_clean_raw = apply_5bin_policy(clean_feat, clean_cal["reserves"], clean_cal["edges"])
                r_phys_clean = np.maximum(clean_cal["gamma"] * r_phys_clean_raw + clean_cal["delta"], 0.0)
                m_phys_clean = compute_decisive_metrics(test_s_moe, r_phys_clean, test_act_moe, test_prob_moe, test_regime)

                # Arm 2: Recalibrated Physical (Condition-Matched)
                recal_feat = test_pab if ch_mode == "all" else test_wspd
                r_phys_recal_raw = apply_5bin_policy(recal_feat, calib["phys_res"], calib["phys_edg"])
                r_phys_recal = np.maximum(calib["g_phys"] * r_phys_recal_raw + calib["d_phys"], 0.0)
                m_phys_recal = compute_decisive_metrics(test_s_moe, r_phys_recal, test_act_moe, test_prob_moe, test_regime)

                # Arm 3: Multi-Task MoE Frozen Backbone + Residual Quantile
                t_froz_moe_raw = t_out_moe["frozen_raw"][lead]
                r_froz_moe_binned = apply_5bin_policy(t_froz_moe_raw, calib["froz_moe_res"], calib["froz_moe_edg"])
                r_froz_moe = np.maximum(calib["g_froz_moe"] * r_froz_moe_binned + calib["d_froz_moe"], 0.0)
                m_froz_moe = compute_decisive_metrics(test_s_moe, r_froz_moe, test_act_moe, test_prob_moe, test_regime)

                # Arm 4: Multi-Task MoE Joint Routed Head
                r_rout_binned = apply_5bin_policy(test_prob_moe, calib["rout_res"], calib["rout_edg"])
                r_routed = np.maximum(calib["g_rout"] * r_rout_binned + calib["d_rout"], 0.0)
                m_routed = compute_decisive_metrics(test_s_moe, r_routed, test_act_moe, test_prob_moe, test_regime)

                # Arm 5: Single-Task Capacity-Matched Dense Backbone + Residual Quantile
                t_froz_dense_raw = t_out_dense["frozen_raw"][lead]
                r_froz_dense_binned = apply_5bin_policy(t_froz_dense_raw, calib["froz_dense_res"], calib["froz_dense_edg"])
                r_froz_dense = np.maximum(calib["g_froz_dense"] * r_froz_dense_binned + calib["d_froz_dense"], 0.0)
                m_froz_dense = compute_decisive_metrics(test_s_dense, r_froz_dense, test_act_dense, np.zeros_like(test_prob_moe), test_regime)

                # Record full scan row
                scan_results.append({
                    "seed": seed,
                    "lead_step": lead,
                    "lead_minutes": (lead + 1) * 10,
                    "lag_steps": lag,
                    "lag_minutes": lag * 10,
                    "channel_mode": ch_mode,
                    # Physical Clean
                    "phys_clean_cost": m_phys_clean["total_cost"],
                    "phys_clean_shortage": m_phys_clean["shortage_mwh"],
                    "phys_clean_viol": m_phys_clean["violation_rate"],
                    # Physical Recalibrated
                    "phys_recal_cost": m_phys_recal["total_cost"],
                    "phys_recal_shortage": m_phys_recal["shortage_mwh"],
                    "phys_recal_viol": m_phys_recal["violation_rate"],
                    # Multi-Task MoE Frozen Backbone Head
                    "moe_frozen_cost": m_froz_moe["total_cost"],
                    "moe_frozen_shortage": m_froz_moe["shortage_mwh"],
                    "moe_frozen_viol": m_froz_moe["violation_rate"],
                    # Multi-Task MoE Joint Routed
                    "moe_routed_cost": m_routed["total_cost"],
                    "moe_routed_shortage": m_routed["shortage_mwh"],
                    "moe_routed_viol": m_routed["violation_rate"],
                    # Single-Task Dense Frozen Backbone Head
                    "dense_frozen_cost": m_froz_dense["total_cost"],
                    "dense_frozen_shortage": m_froz_dense["shortage_mwh"],
                    "dense_frozen_viol": m_froz_dense["violation_rate"],
                    # Relative Comparison Flags
                    "dense_vs_moe_frozen_cost_ratio": m_froz_dense["total_cost"] / max(m_froz_moe["total_cost"], 1.0),
                    "dense_vs_moe_routed_cost_ratio": m_froz_dense["total_cost"] / max(m_routed["total_cost"], 1.0),
                })

                # Selective Decision Abstention under Delay-6 (tau=60m, lead=0, h=1)
                if lag == 6 and lead == 0:
                    P_rated = 1500.0
                    t_aero_fb_moe = np.maximum(0.0, np.minimum(P_rated - test_pred_moe, P_rated))
                    r_fb_moe = np.maximum(r_phys_recal, t_aero_fb_moe)

                    t_aero_fb_dense = np.maximum(0.0, np.minimum(P_rated - test_pred_dense, P_rated))
                    r_fb_dense = np.maximum(r_phys_recal, t_aero_fb_dense)

                    eps = 1e-7
                    t_clamp = np.clip(test_prob_moe, eps, 1.0 - eps)
                    t_ent = -(t_clamp * np.log2(t_clamp) + (1.0 - t_clamp) * np.log2(1.0 - t_clamp))
                    t_spr_moe = np.abs(r_phys_recal_raw - r_froz_moe_binned)
                    t_hyb_moe = t_spr_moe + 50.0 * t_ent

                    t_spr_dense = np.abs(r_phys_recal_raw - r_froz_dense_binned)

                    for m_label, r_cand, u_cand, th_dict, a_val_dict, t_s_sub, t_act_sub, r_fb_sub in [
                        ("Joint Routed", r_routed, t_hyb_moe, calib["thresh_hyb_moe"], calib["alpha_val_moe_rout"], test_s_moe, test_act_moe, r_fb_moe),
                        ("Frozen Backbone (MoE)", r_froz_moe, t_hyb_moe, calib["thresh_hyb_moe"], calib["alpha_val_moe_froz"], test_s_moe, test_act_moe, r_fb_moe),
                        ("Single-Task Dense Backbone", r_froz_dense, t_spr_dense, calib["thresh_spr_dense"], calib["alpha_val_dense_froz"], test_s_dense, test_act_dense, r_fb_dense),
                    ]:
                        abs_evals = evaluate_frozen_threshold_abstention(
                            t_s=t_s_sub,
                            t_act=t_act_sub,
                            t_r=r_cand,
                            t_fb=r_fb_sub,
                            t_u=u_cand,
                            frozen_thresh=th_dict,
                            coverages=abstention_coverages,
                            seed=seed,
                            frozen_alpha_val=a_val_dict,
                        )
                        for res in abs_evals:
                            res.update({
                                "seed": seed,
                                "model": m_label,
                                "lead_step": lead,
                                "lag_steps": lag,
                                "channel_mode": ch_mode,
                            })
                        abstention_results.extend(abs_evals)

    return scan_results, abstention_results


def main():
    parser = argparse.ArgumentParser(description="Evaluate Single-Task Dense vs Multi-Task MoE on WTB Phase Scan")
    parser.add_argument("--farm", type=str, default="wtb")
    parser.add_argument("--seeds", type=str, default="201,202,203,204,205")
    parser.add_argument("--cache-dir", type=str, default="artifacts/cache_strictmask_trainweights/wtb_245d")
    parser.add_argument("--routed-pat", type=str, default="artifacts/trainweight_full_rerun_20260830/wtb_full_seed{seed}")
    parser.add_argument("--dense-pat", type=str, default="artifacts/capacity_matched_dense_wtb/wtb_dense_seed{seed}")
    parser.add_argument("--output-dir", type=str, default="artifacts/single_task_dense_vs_multitask_moe_scan")
    parser.add_argument("--device", type=str, default="cuda:0")
    args = parser.parse_args()

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    bundle = load_cache_bundle(args.cache_dir, mmap_mode="r")
    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]

    all_scan, all_abs = [], []
    for seed in seeds:
        s_scan, s_abs = run_dense_phase_scan_for_seed(
            farm=args.farm,
            seed=seed,
            bundle=bundle,
            routed_ckpt_pattern=args.routed_pat,
            dense_ckpt_pattern=args.dense_pat,
            device=device,
        )
        all_scan.extend(s_scan)
        all_abs.extend(s_abs)

    df_scan = pd.DataFrame(all_scan)
    df_scan.to_csv(out_dir / "phase_scan_results_by_seed.csv", index=False)

    df_abs = pd.DataFrame(all_abs)
    df_abs.to_csv(out_dir / "phase_scan_risk_coverage_by_seed.csv", index=False)

    print(f"\nSaved per-seed scan to {out_dir / 'phase_scan_results_by_seed.csv'}", flush=True)
    print(f"Saved per-seed risk coverage to {out_dir / 'phase_scan_risk_coverage_by_seed.csv'}", flush=True)


if __name__ == "__main__":
    main()
