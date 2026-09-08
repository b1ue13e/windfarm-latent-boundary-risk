"""Phase Boundary Scan and Selective Decision Abstention Benchmark.

Systematically scans the multidimensional degradation matrix:
1. Information Age / Telemetry Lag: tau in [0, 1, 2, 3, 6] steps (0, 10, 20, 30, 60 minutes)
2. Channel Observability: 'all' (all channels delayed/noisy) vs 'no_pitch' (pitch telemetry unobservable/masked)
3. Forecast Lead Step: lead_step in [0, 2, 5] (corresponding to h = 1, 3, 6)
4. Selective Decision Abstention: sweeps coverage c in [0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
   based on posterior entropy and prediction interval spread, deferring ambiguous decisions to
   conservative aerodynamic fallback reserve.

Directly establishes the Three-Way Operational Boundaries:
- Regime I: Simple Recalibration Sufficient (violation <= 10.0%, cost gap vs learned < 5%)
- Regime II: Learned Representation Advantage (representation cuts cost/shortage > 10%)
- Regime III: Mandatory Refusal Boundary (all unconstrained models fail; safety strictly requires abstention)
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
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
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
    compute_hybrid_policy_reserve,
    find_iso_reliability_multiplier,
    compute_decisive_metrics,
    train_sequence_gru_classifier_fast,
    train_frozen_quantile_head_fast,
    extract_gbdt_features,
    run_forward_pass,
    pinball_loss_np,
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


def evaluate_abstention_curve(
    shortfall: np.ndarray,
    active: np.ndarray,
    raw_reserve: np.ndarray,
    fallback_reserve: np.ndarray,
    uncertainty_score: np.ndarray,
    coverages: Tuple[float, ...] = (0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 1.00),
    dt: float = DT,
    rho: float = RHO,
) -> List[Dict[str, float]]:
    """Evaluates the Risk-Coverage curve under selective decision abstention."""
    valid = active & np.isfinite(shortfall) & np.isfinite(raw_reserve) & np.isfinite(uncertainty_score)
    s_val = shortfall[valid]
    r_val = raw_reserve[valid]
    fb_val = fallback_reserve[valid]
    u_val = uncertainty_score[valid]
    n_total = len(s_val)

    if n_total == 0:
        return []

    results = []
    for cov in coverages:
        if cov >= 1.0:
            accepted_mask = np.ones(n_total, dtype=bool)
        else:
            thresh = float(np.quantile(u_val, cov))
            accepted_mask = u_val <= thresh

        # Accepted samples use the model reserve; rejected samples defer to conservative fallback
        blended_reserve = np.where(accepted_mask, r_val, fb_val)
        fleet_shortage = np.maximum(s_val - blended_reserve, 0.0)
        fleet_cost = (blended_reserve + rho * fleet_shortage) * dt

        # Accepted-subset metrics (purely evaluate the confident decisions)
        acc_s = s_val[accepted_mask]
        acc_r = r_val[accepted_mask]
        acc_viol = float(np.mean(acc_s > acc_r)) if len(acc_s) > 0 else 0.0

        # Fleet-level metrics (overall system outcome under safety fallback)
        fleet_viol = float(np.mean(s_val > blended_reserve))
        fleet_reserve_mwh = float(np.sum(blended_reserve) * dt / 1000.0)
        fleet_shortage_mwh = float(np.sum(fleet_shortage) * dt / 1000.0)
        fleet_total_cost = float(np.sum(fleet_cost))

        results.append({
            "coverage": float(cov),
            "accepted_violation_rate": acc_viol,
            "fleet_violation_rate": fleet_viol,
            "fleet_reserve_mwh": fleet_reserve_mwh,
            "fleet_shortage_mwh": fleet_shortage_mwh,
            "fleet_total_cost": fleet_total_cost,
            "n_accepted": int(np.sum(accepted_mask)),
            "n_total": n_total,
        })
    return results


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
    abstention_coverages: Tuple[float, ...] = (0.50, 0.60, 0.70, 0.80, 0.90, 1.00),
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Runs the full multidimensional phase scan for one random seed."""
    print(f"\n=======================================================", flush=True)
    print(f"Starting Boundary Phase Scan for Seed {seed} on {farm.upper()}", flush=True)
    print(f"=======================================================", flush=True)

    # 1. Load Pretrained Models
    routed_path = Path(routed_ckpt_pattern.format(seed=seed))
    print(f"Loading Routed Model from: {routed_path}", flush=True)
    routed_model = _load_model_from_checkpoint(routed_path, bundle, device)
    routed_model.eval()

    dense_model = None
    if dense_ckpt_pattern is not None:
        dense_path = Path(dense_ckpt_pattern.format(seed=seed))
        if dense_path.exists():
            print(f"Loading Dense Model from: {dense_path}", flush=True)
            dense_model = _load_model_from_checkpoint(dense_path, bundle, device)
            dense_model.eval()

    rated_wind = 10.5
    band = 1.0
    feat_names = list(bundle.metadata.get("feature_names", []))
    w_idx = feat_names.index("Wspd") if "Wspd" in feat_names else 0
    p_idx = feat_names.index("Pab_mean") if "Pab_mean" in feat_names else (7 if len(feat_names) > 7 else 1)

    w_mean = float(bundle.metadata["physics_model_stats"]["0"]["mean"])
    w_std = float(bundle.metadata["physics_model_stats"]["0"]["std"])
    p_mean = float(bundle.metadata["physics_model_stats"]["1"]["mean"])
    p_std = float(bundle.metadata["physics_model_stats"]["1"]["std"])

    # 2. Train Lightweight Auxiliary Heads on Base Clean Data
    print("Fitting baseline sequence classifier and frozen quantile head...", flush=True)
    train_clean_ds = UnifiedArrivalDataset(bundle, "train", hist_len=36, pred_len=24, degradation=DegradationSpec(delay_steps=0))
    train_clean_loader = DataLoader(train_clean_ds, batch_size=64, shuffle=True)

    val_clean_ds = UnifiedArrivalDataset(bundle, "val", hist_len=36, pred_len=24, degradation=DegradationSpec(delay_steps=0))
    val_clean_loader = DataLoader(val_clean_ds, batch_size=64, shuffle=False)

    val_stale_ds = UnifiedArrivalDataset(bundle, "val", hist_len=36, pred_len=24, degradation=DegradationSpec(delay_steps=6, history_policy="stalled"))
    val_stale_loader = DataLoader(val_stale_ds, batch_size=64, shuffle=False)

    seq_clf = train_sequence_gru_classifier_fast(train_clean_loader, in_channels=len(feat_names), device=device)
    seq_clf.eval()

    frozen_head = train_frozen_quantile_head_fast(routed_model, train_clean_loader, device=device, lead_step=0)
    frozen_head.eval()

    # 3. Fit Tabular GBDT Baseline on Clean Train Features
    tr_x_list, tr_mask_list, tr_anc_list, tr_tar_list, tr_tmask_list, tr_pred_list = [], [], [], [], [], []
    count = 0
    routed_model.eval()
    with torch.no_grad():
        for b in train_clean_loader:
            x_h = b["x_hist"].to(device)
            ei = b["edge_index_hist"].to(device)
            ew = b["edge_weight_hist"].to(device)
            fm = b["feature_mask_hist"].to(device)
            ap = b["anchor_physics"].to(device)
            pred, _, _ = routed_model(x_h, ei, ew, fm, ap)

            tr_x_list.append(b["x_hist"].numpy())
            tr_mask_list.append(b["feature_mask_hist"].numpy())
            tr_anc_list.append(b["anchor_physics"].numpy())
            tr_tar_list.append(b["target"][:, 0, :].numpy())
            tr_tmask_list.append(b["target_mask"][:, 0, :].numpy())
            tr_pred_list.append(pred[:, 0, :].cpu().numpy())
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

    # 4. Fit Validation Calibration Multipliers for each Horizon
    val_calibrations = {}
    for lead in lead_steps:
        h_val_routed_clean = run_forward_pass(routed_model, val_clean_loader, device, lead_step=lead)
        h_val_routed_stale = run_forward_pass(routed_model, val_stale_loader, device, lead_step=lead)

        val_s_clean = np.maximum(h_val_routed_clean["pred"] - h_val_routed_clean["target"], 0.0).reshape(-1)
        val_wspd_clean = (h_val_routed_clean["anchor"][..., 0] * w_std + w_mean).reshape(-1)
        val_pab_clean = (h_val_routed_clean["anchor"][..., 1] * p_std + p_mean).reshape(-1)
        val_active_clean = ((np.abs(val_wspd_clean - rated_wind) <= band) & (h_val_routed_clean["mask"].reshape(-1) > 0.5) & np.isfinite(val_s_clean))

        val_s_stale = np.maximum(h_val_routed_stale["pred"] - h_val_routed_stale["target"], 0.0).reshape(-1)
        val_wspd_stale = (h_val_routed_stale["anchor"][..., 0] * w_std + w_mean).reshape(-1)
        val_pab_stale = (h_val_routed_stale["anchor"][..., 1] * p_std + p_mean).reshape(-1)
        val_active_stale = ((np.abs(val_wspd_stale - rated_wind) <= band) & (h_val_routed_stale["mask"].reshape(-1) > 0.5) & np.isfinite(val_s_stale))

        # Fit quintiles
        phys_res, phys_edg, glob_res = fit_5bin_quantiles(val_pab_clean, val_s_clean, val_active_clean)

        val_p_pitch_clean = h_val_routed_clean["prob"].reshape(-1)
        val_p_pitch_stale = h_val_routed_stale["prob"].reshape(-1)
        routed_res, routed_edg, _ = fit_5bin_quantiles(val_p_pitch_clean, val_s_clean, val_active_clean)

        val_clean_raw = {
            "Continuous Physical Quantile": apply_5bin_policy(val_pab_clean, phys_res, phys_edg),
            "Joint Routed": apply_5bin_policy(val_p_pitch_clean, routed_res, routed_edg),
        }
        val_stale_raw = {
            "Continuous Physical Quantile": apply_5bin_policy(val_pab_stale, phys_res, phys_edg),
            "Joint Routed": apply_5bin_policy(val_p_pitch_stale, routed_res, routed_edg),
        }

        # Multipliers
        g_clean, d_clean = {}, {}
        for m_name, v_r in val_clean_raw.items():
            g, d, _ = find_iso_reliability_multiplier(val_s_clean, v_r, val_active_clean, target_violation=TARGET_VIOLATION)
            g_clean[m_name] = g
            d_clean[m_name] = d

        g_stale, d_stale = {}, {}
        for m_name, v_r in val_stale_raw.items():
            g, d, _ = find_iso_reliability_multiplier(val_s_stale, v_r, val_active_stale, target_violation=TARGET_VIOLATION)
            g_stale[m_name] = g
            d_stale[m_name] = d

        val_calibrations[lead] = {
            "phys_reserves": phys_res,
            "phys_edges": phys_edg,
            "routed_reserves": routed_res,
            "routed_edges": routed_edg,
            "global_reserve": glob_res,
            "gamma_clean": g_clean,
            "delta_clean": d_clean,
            "gamma_stale": g_stale,
            "delta_stale": d_stale,
        }

    # 5. Grid Scan across Lags, Channel Masking, and Lead Steps
    print("Executing multidimensional grid scan on test set...", flush=True)
    scan_results = []
    abstention_results = []

    for lead in lead_steps:
        calib = val_calibrations[lead]
        for lag in lags:
            for ch_mode in channel_modes:
                cond_id = f"lag{lag}_{ch_mode}_lead{lead}"
                print(f"  Scanning condition: {cond_id} (Seed {seed})", flush=True)

                if ch_mode == "no_pitch":
                    corrupted = ("Pab_mean",)
                else:
                    corrupted = ("all",)

                spec = DegradationSpec(
                    delay_steps=lag,
                    corrupted_channels=corrupted,
                    history_policy="stalled" if lag > 0 else "shifted",
                )

                test_ds = UnifiedArrivalDataset(bundle, "test", hist_len=36, pred_len=24, degradation=spec)
                test_loader = DataLoader(test_ds, batch_size=64, shuffle=False)

                test_routed = run_forward_pass(routed_model, test_loader, device, lead_step=lead)

                test_s = np.maximum(test_routed["pred"] - test_routed["target"], 0.0).reshape(-1)
                test_wspd_phys = (test_routed["anchor"][..., 0] * w_std + w_mean).reshape(-1)
                test_pab_phys = (test_routed["anchor"][..., 1] * p_std + p_mean).reshape(-1)
                test_active = ((np.abs(test_wspd_phys - rated_wind) <= band) & (test_routed["mask"].reshape(-1) > 0.5) & np.isfinite(test_s))
                test_regime = test_routed["regime"].reshape(-1)

                # Gate probability & Frozen Backbone Head
                test_p_pitch = test_routed["prob"].reshape(-1)

                test_frozen_list = []
                with torch.no_grad():
                    for b in test_loader:
                        _, _, aux = routed_model(b["x_hist"].to(device), b["edge_index_hist"].to(device), b["edge_weight_hist"].to(device), b["feature_mask_hist"].to(device), b["anchor_physics"].to(device))
                        rf = frozen_head(aux["context"], b["anchor_physics"].to(device)).cpu().numpy()
                        test_frozen_list.append(rf)
                test_frozen_raw = np.concatenate(test_frozen_list, axis=0).reshape(-1)

                # Evaluate Models
                phys_raw = apply_5bin_policy(test_pab_phys, calib["phys_reserves"], calib["phys_edges"])

                # Arm 1: Clean-Calibrated Physical Rule (deterministic unadapted)
                r_phys_clean = np.maximum(calib["gamma_clean"]["Continuous Physical Quantile"] * phys_raw + calib["delta_clean"]["Continuous Physical Quantile"], 0.0)
                m_phys_clean = compute_decisive_metrics(test_s, r_phys_clean, test_active, test_p_pitch, test_regime)

                # Arm 2: State-Conditional Recalibrated Physical Rule (adapted)
                if lag == 0 and ch_mode == "all":
                    r_phys_recal = r_phys_clean
                else:
                    r_phys_recal = np.maximum(calib["gamma_stale"]["Continuous Physical Quantile"] * phys_raw + calib["delta_stale"]["Continuous Physical Quantile"], 0.0)
                m_phys_recal = compute_decisive_metrics(test_s, r_phys_recal, test_active, test_p_pitch, test_regime)

                # Arm 3: Frozen Backbone + Residual Quantile (Strongest Baseline)
                r_frozen = np.maximum(test_frozen_raw, 0.0)
                m_frozen = compute_decisive_metrics(test_s, r_frozen, test_active, test_p_pitch, test_regime)

                # Arm 4: Joint Routed (MoE)
                routed_raw = apply_5bin_policy(test_p_pitch, calib["routed_reserves"], calib["routed_edges"])
                if lag == 0 and ch_mode == "all":
                    r_routed = np.maximum(calib["gamma_clean"]["Joint Routed"] * routed_raw + calib["delta_clean"]["Joint Routed"], 0.0)
                else:
                    r_routed = np.maximum(calib["gamma_stale"]["Joint Routed"] * routed_raw + calib["delta_stale"]["Joint Routed"], 0.0)
                m_routed = compute_decisive_metrics(test_s, r_routed, test_active, test_p_pitch, test_regime)

                # Conservative Fallback Ceiling (used for Abstention)
                r_fallback = np.maximum(r_phys_recal, calib["global_reserve"])

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

                # Selective Decision Abstention Evaluation (on Frozen Backbone & Joint Routed)
                u_frozen = compute_uncertainty_score(test_p_pitch, r_phys_recal, r_frozen)
                ab_frozen = evaluate_abstention_curve(test_s, test_active, r_frozen, r_fallback, u_frozen, coverages=abstention_coverages)
                for res in ab_frozen:
                    res.update({
                        "seed": seed,
                        "model": "Frozen Backbone + Residual Quantile",
                        "lead_step": lead,
                        "lag_steps": lag,
                        "channel_mode": ch_mode,
                    })
                    abstention_results.append(res)

                u_routed = compute_uncertainty_score(test_p_pitch, r_phys_recal, r_routed)
                ab_routed = evaluate_abstention_curve(test_s, test_active, r_routed, r_fallback, u_routed, coverages=abstention_coverages)
                for res in ab_routed:
                    res.update({
                        "seed": seed,
                        "model": "Joint Routed",
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
        "accepted_violation_rate": ["mean", "std"],
        "fleet_violation_rate": ["mean", "std"],
        "fleet_total_cost": ["mean", "std"],
        "fleet_shortage_mwh": ["mean", "std"],
        "fleet_reserve_mwh": ["mean", "std"],
    }).reset_index()
    agg_abs.to_csv(out_dir / "phase_scan_risk_coverage_aggregate.csv", index=False)

    print(f"\n[PHASE SCAN COMPLETE] All outputs saved to {out_dir}", flush=True)


if __name__ == "__main__":
    main()
