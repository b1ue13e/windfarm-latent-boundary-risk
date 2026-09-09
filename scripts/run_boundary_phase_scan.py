"""Phase Boundary Scan and Selective Decision Abstention Benchmark.

Systematically scans the multidimensional degradation matrix:
1. Information Age / Telemetry Lag: tau in [0, 1, 2, 3, 6] steps (0, 10, 20, 30, 60 minutes)
2. Channel Observability: 'all' (all telemetry channels present) vs 'no_pitch' (pitch telemetry completely unobservable/masked)
3. Forecast Lead Step: lead_step in [0, 2, 5] (corresponding to h = 1, 3, 6)
4. Condition-Matching Validation Calibration:
   For every (lead, lag, channel_mode), all models (Physical, Frozen Backbone, Joint Routed)
   undergo symmetric 5-bin quantile mapping and iso-reliability multiplier calibration
   on validation data evaluated under that exact matching degradation condition.
5. Rigorous Selective Decision Abstention:
   - Thresholds frozen on validation set for target coverages c in [0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 1.00].
   - Evaluates realized coverage, accepted violation rate, fleet violation rate, and fleet cost.
   - Evaluated against two mandatory controls:
     * Random Abstention (rejecting same fraction randomly)
     * Uniform Margin Inflation (scaling reserve uniformly to match same total MWh)

Directly establishes the Three-Way Operational Boundaries:
- Regime I: Simple Recalibration Sufficient (violation <= 10.0%, cost gap vs learned < 5%)
- Regime II: Learned Representation Advantage (representation cuts cost/shortage > 10%)
- Regime III: Refusal / Safety Ceiling Boundary (evaluates whether abstention confers true Pareto gains over uniform conservatism)
"""
from __future__ import annotations

import os
import sys

os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"
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
    extract_symmetric_rule_input,
)
from windfarm_moe.data import CacheBundle, load_cache_bundle
from windfarm_moe.mechanism_intervention import _load_model_from_checkpoint
from scripts.decisive_fair_risk_benchmark import (
    CRITICAL_FRACTILE,
    TARGET_VIOLATION,
    N_BINS,
    DT,
    RHO,
    fit_5bin_quantiles,
    apply_5bin_policy,
    find_iso_reliability_multiplier,
    compute_decisive_metrics,
    train_frozen_quantile_head_fast,
    run_forward_pass,
)


def compute_uncertainty_score(
    p_pitch: np.ndarray,
    r_physics: np.ndarray,
    r_learned: np.ndarray,
    entropy_weight: float = 50.0,
) -> np.ndarray:
    """Computes sample-level uncertainty score combining posterior entropy and rule-representation spread."""
    eps = 1e-7
    p_clamped = np.clip(p_pitch, eps, 1.0 - eps)
    binary_entropy = -(p_clamped * np.log2(p_clamped) + (1.0 - p_clamped) * np.log2(1.0 - p_clamped))
    spread = np.abs(r_physics - r_learned)
    score = spread + entropy_weight * binary_entropy
    return score


def evaluate_frozen_threshold_abstention(
    t_s: np.ndarray,
    t_act: np.ndarray,
    t_r: np.ndarray,
    t_fb: np.ndarray,
    t_u: np.ndarray,
    frozen_thresh: Dict[float, float],
    coverages: Tuple[float, ...] = (0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 1.00),
    seed: int = 42,
    dt: float = DT,
    rho: float = RHO,
    frozen_alpha_val: Optional[Dict[float, float]] = None,
) -> List[Dict[str, Any]]:
    """Evaluates selective abstention using thresholds frozen on the validation set, with mandatory controls."""
    valid = t_act & np.isfinite(t_s) & np.isfinite(t_r) & np.isfinite(t_fb) & np.isfinite(t_u)
    s_val = t_s[valid]
    r_val = t_r[valid]
    fb_val = t_fb[valid]
    u_val = t_u[valid]
    n_total = len(s_val)

    if n_total == 0:
        return []

    results = []
    for cov in coverages:
        thresh = frozen_thresh.get(cov, np.inf)
        if cov >= 1.0 or np.isinf(thresh):
            accepted_mask = np.ones(n_total, dtype=bool)
        else:
            accepted_mask = (u_val <= thresh)

        realized_cov = float(np.mean(accepted_mask))

        # Model selective blended reserve
        blended_reserve = np.where(accepted_mask, r_val, fb_val)
        fleet_shortage = np.maximum(s_val - blended_reserve, 0.0)
        fleet_cost = (blended_reserve + rho * fleet_shortage) * dt

        # Accepted subset (purely evaluating the confident decisions)
        acc_s = s_val[accepted_mask]
        acc_r = r_val[accepted_mask]
        acc_viol = float(np.mean(acc_s > acc_r)) if len(acc_s) > 0 else 0.0

        # Fleet-level outcomes under safety fallback
        fleet_viol = float(np.mean(s_val > blended_reserve))
        fleet_res_mwh = float(np.sum(blended_reserve) * dt / 1000.0)
        fleet_short_mwh = float(np.sum(fleet_shortage) * dt / 1000.0)
        fleet_total_cost = float(np.sum(fleet_cost))

        # Control Benchmark 1: Random Abstention (same acceptance rate)
        rng = np.random.default_rng(seed + int(cov * 1000))
        rand_mask = rng.uniform(0.0, 1.0, size=n_total) <= realized_cov
        rand_res = np.where(rand_mask, r_val, fb_val)
        rand_shortage = np.maximum(s_val - rand_res, 0.0)
        rand_viol = float(np.mean(s_val > rand_res))
        rand_cost = float(np.sum((rand_res + rho * rand_shortage) * dt))
        rand_acc_viol = float(np.mean(s_val[rand_mask] > r_val[rand_mask])) if rand_mask.sum() > 0 else 0.0

        # Control Benchmark 2a: Uniform Margin Inflation (Ex-Post Test Budget-Matching Control)
        sum_base = float(np.sum(r_val))
        sum_target = float(np.sum(blended_reserve))
        alpha = sum_target / max(sum_base, 1e-6)
        unif_res = r_val * alpha
        unif_shortage = np.maximum(s_val - unif_res, 0.0)
        unif_viol = float(np.mean(s_val > unif_res))
        unif_cost = float(np.sum((unif_res + rho * unif_shortage) * dt))

        # Control Benchmark 2b: Uniform Margin Inflation (Ex-Ante Validation-Frozen Deployable Policy)
        alpha_val = frozen_alpha_val.get(cov, alpha) if frozen_alpha_val is not None else alpha
        unif_val_res = r_val * alpha_val
        unif_val_shortage = np.maximum(s_val - unif_val_res, 0.0)
        unif_val_viol = float(np.mean(s_val > unif_val_res))
        unif_val_cost = float(np.sum((unif_val_res + rho * unif_val_shortage) * dt))

        results.append({
            "coverage": float(cov),
            "target_coverage": float(cov),
            "realized_coverage": realized_cov,
            # Model Selective Abstention
            "accepted_violation_rate": acc_viol,
            "fleet_violation_rate": fleet_viol,
            "fleet_reserve_mwh": fleet_res_mwh,
            "fleet_shortage_mwh": fleet_short_mwh,
            "fleet_total_cost": fleet_total_cost,
            "n_accepted": int(np.sum(accepted_mask)),
            "n_total": n_total,
            # Random Abstention Benchmark
            "random_fleet_viol": rand_viol,
            "random_fleet_cost": rand_cost,
            "random_acc_viol": rand_acc_viol,
            # Uniform Margin Inflation: Ex-Post Test Budget-Matching Diagnostic Control
            "uniform_alpha": alpha,
            "uniform_fleet_viol": unif_viol,
            "uniform_fleet_cost": unif_cost,
            # Uniform Margin Inflation: Ex-Ante Validation-Frozen Deployable Policy
            "uniform_val_alpha": alpha_val,
            "uniform_val_fleet_viol": unif_val_viol,
            "uniform_val_fleet_cost": unif_val_cost,
        })
    return results


def run_joint_multilead_pass(
    routed_model: nn.Module,
    frozen_heads: Dict[int, nn.Module],
    loader: DataLoader,
    device: torch.device,
    lead_steps: List[int] = [0, 2, 5],
) -> Dict[str, Any]:
    """Runs a single forward pass over loader, extracting predictions and frozen heads for all leads."""
    routed_model.eval()
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

            pred, gate_prob, aux = routed_model(x_hist, edge_index, edge_weight, feature_mask, anchor_phys)
            context = aux["context"]
            prob = gate_prob[..., 2].cpu().numpy() if gate_prob is not None and gate_prob.shape[-1] >= 3 else np.zeros((pred.shape[0], pred.shape[2]))

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


def run_phase_scan_for_seed(
    farm: str,
    seed: int,
    bundle: CacheBundle,
    routed_ckpt_pattern: str,
    dense_ckpt_pattern: Optional[str],
    device: torch.device,
    lags: List[int] = [0, 1, 2, 3, 6],
    channel_modes: List[str] = ["all", "no_pitch"],
    lead_steps: List[int] = [0, 2, 5],
    abstention_coverages: Tuple[float, ...] = (0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 1.00),
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Runs the full multidimensional phase scan for one random seed under condition-matching validation calibration."""
    print(f"\n=======================================================", flush=True)
    print(f"Starting Boundary Phase Scan for Seed {seed} on {farm.upper()}", flush=True)
    print(f"=======================================================", flush=True)

    # 1. Load Pretrained Models
    routed_path = Path(routed_ckpt_pattern.format(seed=seed))
    print(f"Loading Routed Model from: {routed_path}", flush=True)
    routed_model = _load_model_from_checkpoint(routed_path, bundle, device)
    routed_model.eval()

    rated_wind = 10.5
    band = 1.0
    feat_names = list(bundle.metadata.get("feature_names", []))
    w_mean = float(bundle.metadata["physics_model_stats"]["0"]["mean"])
    w_std = float(bundle.metadata["physics_model_stats"]["0"]["std"])
    p_mean = float(bundle.metadata["physics_model_stats"]["1"]["mean"])
    p_std = float(bundle.metadata["physics_model_stats"]["1"]["std"])

    # Pitch withholding definition: completely remove Pab_mean and Pab_std
    pitch_withheld_tuple = tuple(ch for ch in ("Pab_mean", "Pab_std") if ch in feat_names)

    # 2. Train Separate Frozen Quantile Heads for Each Horizon on Clean Data
    print("Training horizon-specific Frozen Backbone Quantile Heads on clean train split...", flush=True)
    train_clean_ds = UnifiedArrivalDataset(bundle, "train", hist_len=36, pred_len=24, degradation=DegradationSpec(delay_steps=0))
    train_clean_loader = DataLoader(train_clean_ds, batch_size=64, shuffle=True)

    frozen_heads: Dict[int, nn.Module] = {}
    for lead in lead_steps:
        print(f"  Training Frozen Backbone Quantile Head for lead_step={lead} (h={(lead+1)*10}m)...", flush=True)
        f_head = train_frozen_quantile_head_fast(routed_model, train_clean_loader, device=device, lead_step=lead)
        f_head.eval()
        frozen_heads[lead] = f_head

    # 3. Precompute Condition-Matching Validation Calibrations (One Pass Per Condition)
    print("Precomputing condition-matching validation calibrations across all (lag, channel_mode)...", flush=True)
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

            # Single unified forward pass extracting all leads and frozen heads
            v_out = run_joint_multilead_pass(routed_model, frozen_heads, val_loader, device, lead_steps)
            v_wspd = (v_out["anchor"][..., 0] * w_std + w_mean).reshape(-1)
            v_pab = (v_out["anchor"][..., 1] * p_std + p_mean).reshape(-1)
            v_prob = v_out["prob"].reshape(-1)

            for lead in lead_steps:
                v_s = np.maximum(v_out["pred"][lead] - v_out["target"][lead], 0.0).reshape(-1)
                v_act = ((np.abs(v_wspd - rated_wind) <= band) & (v_out["mask"][lead].reshape(-1) > 0.5) & np.isfinite(v_s))

                # Physical Rule
                # If pitch is observable, bin on pitch angle; if pitch is withheld, bin on wind speed
                phys_feat = v_pab if ch_mode == "all" else v_wspd
                p_res, p_edg, glob_res = fit_5bin_quantiles(phys_feat, v_s, v_act)
                v_phys_raw = apply_5bin_policy(phys_feat, p_res, p_edg)
                g_phys, d_phys, _ = find_iso_reliability_multiplier(v_s, v_phys_raw, v_act, target_violation=TARGET_VIOLATION)

                if lag == 0 and ch_mode == "all":
                    clean_phys_calib[lead] = {
                        "reserves": p_res,
                        "edges": p_edg,
                        "gamma": g_phys,
                        "delta": d_phys,
                        "global_reserve": glob_res,
                    }

                # Frozen Backbone Head (evaluated under matching condition and calibrated)
                v_froz_raw = v_out["frozen_raw"][lead]
                froz_res, froz_edg, _ = fit_5bin_quantiles(v_froz_raw, v_s, v_act)
                v_froz_bin = apply_5bin_policy(v_froz_raw, froz_res, froz_edg)
                g_froz, d_froz, _ = find_iso_reliability_multiplier(v_s, v_froz_bin, v_act, target_violation=TARGET_VIOLATION)

                # Joint Routed Head
                rout_res, rout_edg, _ = fit_5bin_quantiles(v_prob, v_s, v_act)
                v_rout_bin = apply_5bin_policy(v_prob, rout_res, rout_edg)
                g_rout, d_rout, _ = find_iso_reliability_multiplier(v_s, v_rout_bin, v_act, target_violation=TARGET_VIOLATION)

                # Precompute validation uncertainty thresholds for selective abstention
                eps = 1e-7
                p_clamp = np.clip(v_prob, eps, 1.0 - eps)
                v_ent = -(p_clamp * np.log2(p_clamp) + (1.0 - p_clamp) * np.log2(1.0 - p_clamp))
                v_spr = np.abs(v_phys_raw - v_froz_bin)
                v_hyb = v_spr + 50.0 * v_ent

                v_ent_act = v_ent[v_act]
                v_spr_act = v_spr[v_act]
                v_hyb_act = v_hyb[v_act]

                thresh_ent = {c: float(np.quantile(v_ent_act, c)) if c < 1.0 else np.inf for c in abstention_coverages}
                thresh_spr = {c: float(np.quantile(v_spr_act, c)) if c < 1.0 else np.inf for c in abstention_coverages}
                thresh_hyb = {c: float(np.quantile(v_hyb_act, c)) if c < 1.0 else np.inf for c in abstention_coverages}

                # Validation candidate models and fallback for ex-ante alpha computation
                P_rated = 1500.0
                v_pred = v_out["pred"][lead].reshape(-1)
                v_aero_fb = np.maximum(0.0, np.minimum(P_rated - v_pred, P_rated))
                v_r_phys = np.maximum(g_phys * v_phys_raw + d_phys, 0.0)
                v_r_fb = np.maximum(v_r_phys, v_aero_fb)
                v_r_froz = np.maximum(g_froz * v_froz_bin + d_froz, 0.0)
                v_r_rout = np.maximum(g_rout * v_rout_bin + d_rout, 0.0)

                def compute_val_alpha_dict(v_r_cand, v_u, th_dict):
                    a_dict = {}
                    v_r_sub = v_r_cand[v_act]
                    v_fb_sub = v_r_fb[v_act]
                    v_u_sub = v_u[v_act]
                    base_mwh = float(np.sum(v_r_sub))
                    for c in abstention_coverages:
                        th = th_dict.get(c, np.inf)
                        mask = (v_u_sub <= th) if (c < 1.0 and not np.isinf(th)) else np.ones(len(v_u_sub), dtype=bool)
                        blended = np.where(mask, v_r_sub, v_fb_sub)
                        target_mwh = float(np.sum(blended))
                        a_dict[c] = float(target_mwh / max(base_mwh, 1e-6))
                    return a_dict

                alpha_val_frozen_hyb = compute_val_alpha_dict(v_r_froz, v_hyb, thresh_hyb)
                alpha_val_frozen_ent = compute_val_alpha_dict(v_r_froz, v_ent, thresh_ent)
                alpha_val_frozen_spr = compute_val_alpha_dict(v_r_froz, v_spr, thresh_spr)
                alpha_val_routed_hyb = compute_val_alpha_dict(v_r_rout, v_hyb, thresh_hyb)
                alpha_val_routed_ent = compute_val_alpha_dict(v_r_rout, v_ent, thresh_ent)

                val_calibrations[(lead, lag, ch_mode)] = {
                    "phys_res": p_res, "phys_edg": p_edg, "g_phys": g_phys, "d_phys": d_phys, "glob_res": glob_res,
                    "froz_res": froz_res, "froz_edg": froz_edg, "g_froz": g_froz, "d_froz": d_froz,
                    "rout_res": rout_res, "rout_edg": rout_edg, "g_rout": g_rout, "d_rout": d_rout,
                    "thresh_ent": thresh_ent, "thresh_spr": thresh_spr, "thresh_hyb": thresh_hyb,
                    "alpha_val_frozen_hyb": alpha_val_frozen_hyb,
                    "alpha_val_frozen_ent": alpha_val_frozen_ent,
                    "alpha_val_frozen_spr": alpha_val_frozen_spr,
                    "alpha_val_routed_hyb": alpha_val_routed_hyb,
                    "alpha_val_routed_ent": alpha_val_routed_ent,
                }

    # 4. Multi-Dimensional Grid Scan on Test Split (One Pass Per Condition)
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

            # Single unified forward pass extracting all leads and frozen heads
            t_out = run_joint_multilead_pass(routed_model, frozen_heads, test_loader, device, lead_steps)
            test_wspd = (t_out["anchor"][..., 0] * w_std + w_mean).reshape(-1)
            test_pab = (t_out["anchor"][..., 1] * p_std + p_mean).reshape(-1)
            test_prob = t_out["prob"].reshape(-1)
            test_regime = t_out["regime"].reshape(-1)

            for lead in lead_steps:
                cond_id = f"lag{lag}_{ch_mode}_lead{lead}"
                print(f"  Evaluating condition: {cond_id} (Seed {seed})", flush=True)
                calib = val_calibrations[(lead, lag, ch_mode)]
                clean_cal = clean_phys_calib[lead]

                test_s = np.maximum(t_out["pred"][lead] - t_out["target"][lead], 0.0).reshape(-1)
                test_act = ((np.abs(test_wspd - rated_wind) <= band) & (t_out["mask"][lead].reshape(-1) > 0.5) & np.isfinite(test_s))
                test_pred = t_out["pred"][lead].reshape(-1)

                # Arm 1: Clean Physical (Deterministic Unadapted)
                clean_feat = test_pab if ch_mode == "all" else test_wspd
                r_phys_clean_raw = apply_5bin_policy(clean_feat, clean_cal["reserves"], clean_cal["edges"])
                r_phys_clean = np.maximum(clean_cal["gamma"] * r_phys_clean_raw + clean_cal["delta"], 0.0)
                m_phys_clean = compute_decisive_metrics(test_s, r_phys_clean, test_act, test_prob, test_regime)

                # Arm 2: Recalibrated Physical (Condition-Matched)
                recal_feat = test_pab if ch_mode == "all" else test_wspd
                r_phys_recal_raw = apply_5bin_policy(recal_feat, calib["phys_res"], calib["phys_edg"])
                r_phys_recal = np.maximum(calib["g_phys"] * r_phys_recal_raw + calib["d_phys"], 0.0)
                m_phys_recal = compute_decisive_metrics(test_s, r_phys_recal, test_act, test_prob, test_regime)

                # Arm 3: Frozen Backbone + Residual Quantile (Calibrated!)
                t_froz_raw = t_out["frozen_raw"][lead]
                r_froz_binned = apply_5bin_policy(t_froz_raw, calib["froz_res"], calib["froz_edg"])
                r_frozen = np.maximum(calib["g_froz"] * r_froz_binned + calib["d_froz"], 0.0)
                m_frozen = compute_decisive_metrics(test_s, r_frozen, test_act, test_prob, test_regime)

                # Arm 4: Joint Routed (MoE) (Calibrated!)
                r_rout_binned = apply_5bin_policy(test_prob, calib["rout_res"], calib["rout_edg"])
                r_routed = np.maximum(calib["g_rout"] * r_rout_binned + calib["d_rout"], 0.0)
                m_routed = compute_decisive_metrics(test_s, r_routed, test_act, test_prob, test_regime)

                # Record scan row
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
                    # Frozen Backbone Head
                    "frozen_cost": m_frozen["total_cost"],
                    "frozen_shortage": m_frozen["shortage_mwh"],
                    "frozen_viol": m_frozen["violation_rate"],
                    # Joint Routed (MoE)
                    "routed_cost": m_routed["total_cost"],
                    "routed_shortage": m_routed["shortage_mwh"],
                    "routed_viol": m_routed["violation_rate"],
                    # Relative Comparison Flags
                    "recalibration_sufficient": (m_phys_recal["violation_rate"] <= 0.10) and (m_phys_recal["total_cost"] <= 1.05 * m_frozen["total_cost"]),
                    "representation_advantage": (m_frozen["violation_rate"] <= 0.10) and (m_frozen["total_cost"] < 0.90 * m_phys_recal["total_cost"]),
                    "refusal_required": (m_phys_recal["violation_rate"] > 0.10) and (m_frozen["violation_rate"] > 0.10),
                })

                # Selective Decision Abstention Evaluation
                eps = 1e-7
                t_clamp = np.clip(test_prob, eps, 1.0 - eps)
                t_ent = -(t_clamp * np.log2(t_clamp) + (1.0 - t_clamp) * np.log2(1.0 - t_clamp))
                t_spr = np.abs(r_phys_recal_raw - r_froz_binned)
                t_hyb = t_spr + 50.0 * t_ent

                # Conservative Fallback Ceiling (Aerodynamic capacity reserve ceiling clamped to rated)
                P_rated = 1500.0  # Goldwind 1.5MW nominal
                t_aero_fallback = np.maximum(0.0, np.minimum(P_rated - test_pred, P_rated))
                r_fallback = np.maximum(r_phys_recal, t_aero_fallback)

                for m_label, r_cand, u_cand, th_dict, a_val_dict in [
                    ("Frozen Backbone + Residual Quantile", r_frozen, t_hyb, calib["thresh_hyb"], calib["alpha_val_frozen_hyb"]),
                    ("Frozen Backbone (Entropy)", r_frozen, t_ent, calib["thresh_ent"], calib["alpha_val_frozen_ent"]),
                    ("Frozen Backbone (Spread)", r_frozen, t_spr, calib["thresh_spr"], calib["alpha_val_frozen_spr"]),
                    ("Joint Routed", r_routed, t_hyb, calib["thresh_hyb"], calib["alpha_val_routed_hyb"]),
                    ("Joint Routed (Entropy)", r_routed, t_ent, calib["thresh_ent"], calib["alpha_val_routed_ent"]),
                ]:
                    abs_evals = evaluate_frozen_threshold_abstention(
                        t_s=test_s,
                        t_act=test_act,
                        t_r=r_cand,
                        t_fb=r_fallback,
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
                        abstention_results.append(res)

    return scan_results, abstention_results


def main():
    parser = argparse.ArgumentParser(description="Boundary Phase Scan & Selective Abstention Runner")
    parser.add_argument("--farm", default="wtb", choices=["wtb", "kelmarsh", "penmanshiel"])
    parser.add_argument("--seeds", default="201,202,203,204,205")
    parser.add_argument("--device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--output-dir", default="artifacts/boundary_phase_scan")
    args = parser.parse_args()

    out_dir = Path(args.output_dir) / args.farm
    out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)

    # Locate Cache
    cache_cands = [
        "artifacts/cache_strictmask_trainweights/wtb_245d",
        "artifacts/cache_strictmask/wtb_245d",
    ]
    cache_path = None
    for c in cache_cands:
        if Path(c).exists():
            cache_path = Path(c)
            break
    if cache_path is None:
        raise FileNotFoundError(f"No cache bundle found for {args.farm}")

    print(f"Loading Cache Bundle: {cache_path}", flush=True)
    bundle = load_cache_bundle(cache_path, mmap_mode="r")

    routed_pat = "artifacts/trainweight_full_rerun_20260830/wtb_full_seed{seed}"
    dense_pat = "artifacts/dense_classifier_runs_20260904/canonical/wtb_bal_align_force_seed{seed}"

    seeds = [int(s) for s in args.seeds.split(",")]
    all_scan, all_abstention = [], []

    for seed in seeds:
        s_scan, s_abs = run_phase_scan_for_seed(
            farm=args.farm,
            seed=seed,
            bundle=bundle,
            routed_ckpt_pattern=routed_pat,
            dense_ckpt_pattern=dense_pat,
            device=device,
        )
        all_scan.extend(s_scan)
        all_abstention.extend(s_abs)

    # Save Results
    df_scan = pd.DataFrame(all_scan)
    df_scan.to_csv(out_dir / "phase_scan_results_by_seed.csv", index=False)

    df_abs = pd.DataFrame(all_abstention)
    df_abs.to_csv(out_dir / "phase_scan_risk_coverage_by_seed.csv", index=False)

    # Cross-seed Aggregation
    agg_scan = df_scan.groupby(["lead_step", "lead_minutes", "lag_steps", "lag_minutes", "channel_mode"]).agg({
        "phys_clean_cost": ["mean", "std"],
        "phys_clean_shortage": ["mean", "std"],
        "phys_clean_viol": ["mean", "std"],
        "phys_recal_cost": ["mean", "std"],
        "phys_recal_shortage": ["mean", "std"],
        "phys_recal_viol": ["mean", "std"],
        "frozen_cost": ["mean", "std"],
        "frozen_shortage": ["mean", "std"],
        "frozen_viol": ["mean", "std"],
        "routed_cost": ["mean", "std"],
        "routed_shortage": ["mean", "std"],
        "routed_viol": ["mean", "std"],
        "recalibration_sufficient": ["mean"],
        "representation_advantage": ["mean"],
        "refusal_required": ["mean"],
    }).reset_index()
    agg_scan.to_csv(out_dir / "phase_scan_cross_seed_aggregate.csv", index=False)

    agg_abs = df_abs.groupby(["model", "lead_step", "lag_steps", "channel_mode", "coverage"]).agg({
        "realized_coverage": ["mean", "std"],
        "accepted_violation_rate": ["mean", "std"],
        "fleet_violation_rate": ["mean", "std"],
        "fleet_total_cost": ["mean", "std"],
        "fleet_shortage_mwh": ["mean", "std"],
        "fleet_reserve_mwh": ["mean", "std"],
        "random_fleet_viol": ["mean", "std"],
        "random_fleet_cost": ["mean", "std"],
        "random_acc_viol": ["mean", "std"],
        "uniform_alpha": ["mean", "std"],
        "uniform_fleet_viol": ["mean", "std"],
        "uniform_fleet_cost": ["mean", "std"],
    }).reset_index()
    agg_abs.to_csv(out_dir / "phase_scan_risk_coverage_aggregate.csv", index=False)

    print(f"\n[PHASE SCAN COMPLETE] All outputs saved to {out_dir}", flush=True)


if __name__ == "__main__":
    main()

