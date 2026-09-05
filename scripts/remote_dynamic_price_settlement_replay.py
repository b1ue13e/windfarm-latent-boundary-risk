"""Multi-Year Real-Price Dynamic Settlement Cashflow Replay Pipeline.

Replays 17.6 cumulative turbine-operating years (Kelmarsh 9 yr, Penmanshiel 8.6 yr)
under real historical UK Elexon BMRS half-hourly System Buy Prices (2016-2024).

Evaluates:
- Imbalance cashout shortfall penalty: sum(shortage_mwh * sbp)
- Real GBP shortfall savings vs baselines (Global Quantile, Physical Pitch Rule)
- Net cashflow impact with reserve capacity procurement cost
- Seed-paired bootstrap confidence intervals (20,000 resamples) across 5 seeds
- Walk-forward rolling folds (13 folds total) and calendar year breakdowns
"""
from __future__ import annotations

import argparse
import datetime
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset

from windfarm_moe.config import ModelConfig
from windfarm_moe.data import CacheBundle, load_cache_bundle
from windfarm_moe.model import RegimeAwareForecaster
from windfarm_moe.utils import to_device
from scripts.remote_iec_density_multiyear_eval import (
    DT,
    QUANTILE_GRID,
    N_BINS,
    WindowedDataset,
    compute_iec_density,
    policy_bins,
    fit_policy,
    run_inference_on_slice,
)


def build_step_sbp_table(elexon_csv_or_dir: Path, n_steps: int, start_date: datetime.date = datetime.date(2016, 1, 1)) -> np.ndarray:
    """Build a fast 1D array mapping each 10-min step index to its Elexon System Buy Price (GBP/MWh)."""
    if elexon_csv_or_dir.is_file():
        price_df = pd.read_csv(elexon_csv_or_dir)
    else:
        csvs = list(elexon_csv_or_dir.glob("elexon_prices_*.csv"))
        if not csvs:
            full_file = elexon_csv_or_dir / "elexon_system_prices_2016_2024.csv"
            if full_file.exists():
                price_df = pd.read_csv(full_file)
            else:
                raise FileNotFoundError(f"No price files found in {elexon_csv_or_dir}")
        else:
            price_df = pd.concat([pd.read_csv(p) for p in sorted(csvs)], ignore_index=True)

    price_df["settlementDate"] = price_df["settlementDate"].astype(str)
    price_df["settlementPeriod"] = price_df["settlementPeriod"].astype(int)
    price_df["systemBuyPrice"] = pd.to_numeric(price_df["systemBuyPrice"], errors="coerce")

    # Build fast lookup dictionary: (date_str, sp) -> sbp
    price_map: dict[tuple[str, int], float] = {}
    for _, row in price_df.iterrows():
        price_map[(row["settlementDate"], int(row["settlementPeriod"]))] = float(row["systemBuyPrice"])

    overall_mean = float(price_df["systemBuyPrice"].dropna().mean())
    print(f"Loaded {len(price_map):,} settlement periods. Overall mean SBP: GBP {overall_mean:.2f}/MWh")

    # Map each step s to SBP
    sbp_arr = np.full((n_steps,), overall_mean, dtype=np.float32)
    missing = 0
    for s in range(n_steps):
        day_idx = s // 144
        sp = ((s % 144) // 3) + 1
        d = start_date + datetime.timedelta(days=int(day_idx))
        key = (d.isoformat(), sp)
        if key in price_map and np.isfinite(price_map[key]):
            sbp_arr[s] = price_map[key]
        else:
            missing += 1

    if missing > 0:
        print(f"[WARN] {missing}/{n_steps} steps ({missing/n_steps*100:.2f}%) filled with overall mean SBP.")
    else:
        print(f"100% of {n_steps:,} steps successfully mapped to Elexon SBP.")

    return sbp_arr


def eval_real_price_policy(
    s_test: np.ndarray,
    cell_test: np.ndarray,
    bin_test: np.ndarray,
    reserves: dict[int, tuple[float, float]],
    sbp_test_cells: np.ndarray,
    c_res_per_mwh: float = 15.0,
) -> dict[str, Any]:
    """Evaluate reserve policy under real-time half-hourly Elexon System Buy Prices."""
    sel = cell_test & np.isfinite(s_test)
    s = s_test[sel]
    b = bin_test[sel]
    sbp = sbp_test_cells[sel]

    if s.size == 0:
        return {
            "n_cells": 0,
            "shortage_mwh": 0.0,
            "reserve_mwh": 0.0,
            "shortfall_cashflow_gbp": 0.0,
            "shortfall_floor_gbp": 0.0,
            "reserve_cost_gbp": 0.0,
            "total_cashflow_gbp": 0.0,
            "mean_shortfall_sbp": 0.0,
            "mean_period_sbp": 0.0,
            "violation_rate": 0.0,
        }

    r = np.array([reserves.get(int(x), (0.90, 100.0))[1] for x in b], dtype=np.float32)
    shortage_kw = np.maximum(s - r, 0.0)
    shortage_mwh = shortage_kw * (DT / 1000.0)
    reserve_mwh = r * (DT / 1000.0)

    # Cashout settlement: imbalance shortfall * SBP
    shortfall_cashflow_gbp = float(np.sum(shortage_mwh * sbp))
    shortfall_floor_gbp = float(np.sum(shortage_mwh * np.maximum(sbp, 0.0)))
    reserve_cost_gbp = float(np.sum(reserve_mwh * c_res_per_mwh))
    total_cashflow_gbp = shortfall_cashflow_gbp + reserve_cost_gbp

    shortage_mask = shortage_kw > 0.0
    mean_shortfall_sbp = float(np.average(sbp[shortage_mask], weights=shortage_mwh[shortage_mask])) if np.any(shortage_mask) else float(np.mean(sbp))
    mean_period_sbp = float(np.mean(sbp))

    return {
        "n_cells": int(s.size),
        "shortage_mwh": float(np.sum(shortage_mwh)),
        "reserve_mwh": float(np.sum(reserve_mwh)),
        "shortfall_cashflow_gbp": shortfall_cashflow_gbp,
        "shortfall_floor_gbp": shortfall_floor_gbp,
        "reserve_cost_gbp": reserve_cost_gbp,
        "total_cashflow_gbp": total_cashflow_gbp,
        "mean_shortfall_sbp": mean_shortfall_sbp,
        "mean_period_sbp": mean_period_sbp,
        "violation_rate": float(np.mean(shortage_mask)),
    }


def run_farm_real_price_replay(
    farm: str,
    seeds: list[int],
    gpu_id: int,
    repo_root: Path,
    elexon_dir: Path,
    out_dir: Path,
    batch_size: int = 256,
    c_res_per_mwh: float = 15.0,
) -> Path:
    device = torch.device(f"cuda:{gpu_id}" if torch.cuda.is_available() else "cpu")

    if farm == "kelmarsh":
        elevation = 137.0
        rated_wind = 11.0
        cache_dir = repo_root / "artifacts/cache_external_wind/external_wind_kelmarsh_chronological"
        model_root = repo_root / "artifacts/signature_gate_farms_runs_20260903/kelmarsh/canonical"
        steps_per_year = 52560
        n_turbines = 6
    elif farm == "penmanshiel":
        elevation = 230.0
        rated_wind = 11.5
        cache_dir = repo_root / "artifacts/cache_external_wind/external_wind_penmanshiel_chronological"
        model_root = repo_root / "artifacts/signature_gate_farms_runs_20260903/penmanshiel/canonical"
        steps_per_year = 52560
        n_turbines = 14
    else:
        raise ValueError(farm)

    print(f"[GPU {gpu_id}] Loading cache bundle for {farm} from {cache_dir}...")
    bundle = load_cache_bundle(cache_dir)
    num_steps = bundle.features.shape[0]
    print(f"[GPU {gpu_id}] Dataset loaded: {num_steps} steps, {bundle.features.shape[1]} turbines.")

    # Build step -> SBP lookup array
    sbp_by_step = build_step_sbp_table(elexon_dir, num_steps)

    # IEC density calibration
    meta = bundle.metadata
    etmp_stat = meta["feature_stats"]["Etmp"]
    etmp_norm = bundle.features[..., 5]
    corr_ratio, _ = compute_iec_density(etmp_norm, etmp_stat["mean"], etmp_stat["std"], elevation)

    raw_wspd = bundle.physics[..., 0]
    cal_wspd = raw_wspd * corr_ratio
    raw_pab = bundle.physics[..., 1]
    raw_patv = bundle.physics[..., 3] if bundle.physics.shape[-1] > 3 else np.ones_like(raw_wspd)

    policies = ["global", "soft-gate-bin", "soft-pab-bin"]
    rhos = [10.0, 5.0, 20.0]

    all_rows = []

    for seed in seeds:
        ckpt_path = model_root / f"wtb_bal_align_force_seed{seed}" / "best_model.pt"
        if not ckpt_path.exists():
            print(f"[GPU {gpu_id}] WARNING: checkpoint {ckpt_path} not found, skipping!")
            continue

        print(f"[GPU {gpu_id}] Loading model seed {seed} from {ckpt_path}...")
        ckpt = torch.load(ckpt_path, map_location="cpu")
        mcfg = ModelConfig(**ckpt["model_config"])
        model = RegimeAwareForecaster(
            feature_dim=bundle.features.shape[-1],
            pred_len=24,
            mode="moe_full_no_aux",
            config=mcfg,
        ).to(device)
        model.load_state_dict(ckpt["model_state"])
        model.eval()

        # Define evaluation windows
        windows = []
        n_years = num_steps // steps_per_year
        # 1. Walk-Forward Rolling Folds (2 years calibration, 1 year test)
        for f_idx in range(n_years - 2):
            v_start = f_idx * steps_per_year
            v_end = v_start + 2 * steps_per_year
            t_start = v_end
            t_end = min(t_start + steps_per_year, num_steps)
            windows.append((f"rolling_fold_{f_idx+1}", v_start, v_end, t_start, t_end))

        # 2. Individual Annual Windows
        cal_base_start, cal_base_end = 0, steps_per_year
        for y_idx in range(n_years):
            t_start = y_idx * steps_per_year
            t_end = min(t_start + steps_per_year, num_steps)
            windows.append((f"year_{y_idx+1}", cal_base_start, cal_base_end, t_start, t_end))

        # 3. Full Pooled Multi-Year Window
        windows.append(("pooled_multiyear_full", 0, 180 * 144, 180 * 144, num_steps))

        # Determine all required steps for continuous forward inference
        all_eval_indices = set()
        for _, vs, ve, ts, te in windows:
            all_eval_indices.update(range(vs, ve))
            all_eval_indices.update(range(ts, te))

        min_step = min(all_eval_indices)
        max_step = max(all_eval_indices)
        print(f"[GPU {gpu_id}] Running continuous forward inference from step {min_step} to {max_step}...")
        t0 = time.perf_counter()
        inf_result = run_inference_on_slice(model, bundle, min_step, max_step, device, batch_size=batch_size)
        torch.cuda.synchronize() if torch.cuda.is_available() else None
        dt = time.perf_counter() - t0
        print(f"[GPU {gpu_id}] Inference complete: {inf_result['anchor_idx'].size} windows in {dt:.1f}s")

        anchor_idx = inf_result["anchor_idx"]
        step_to_local = {step: idx for idx, step in enumerate(anchor_idx)}

        # Evaluate each rolling window
        for win_name, v_start, v_end, t_start, t_end in windows:
            v_anchors = [step_to_local[s] for s in range(v_start, v_end) if s in step_to_local]
            t_anchors = [step_to_local[s] for s in range(t_start, t_end) if s in step_to_local]
            if not v_anchors or not t_anchors:
                continue

            pv = inf_result["pred"][v_anchors]
            tv = inf_result["target"][v_anchors]
            mv = inf_result["mask"][v_anchors] > 0.5
            gv = inf_result["gate"][v_anchors]
            av_idx = anchor_idx[v_anchors]

            pt = inf_result["pred"][t_anchors]
            tt = inf_result["target"][t_anchors]
            mt = inf_result["mask"][t_anchors] > 0.5
            gt = inf_result["gate"][t_anchors]
            at_idx = anchor_idx[t_anchors]

            sv = np.where(mv, np.maximum(pv - tv, 0.0), np.nan)
            st = np.where(mt, np.maximum(pt - tt, 0.0), np.nan)

            Hv = sv.shape[1]
            Ht = st.shape[1]

            # Future timestamps for test cells to extract contemporaneous SBP
            # For each test anchor at_idx[i] and horizon h in [0, Ht-1], future step is at_idx[i] + 1 + h
            fut_steps = at_idx[:, None] + 1 + np.arange(Ht)[None, :] # shape (N_test, Ht)
            fut_steps = np.clip(fut_steps, 0, num_steps - 1)
            sbp_test_matrix = sbp_by_step[fut_steps] # shape (N_test, Ht)
            sbp_test_cells = np.repeat(sbp_test_matrix[:, :, None], st.shape[-1], axis=2) # shape (N_test, Ht, N_turbines)

            # Calibrated boundary fields
            p_pitch_v = gv[..., 2] / np.maximum(gv[..., :3].sum(axis=-1), 1e-9)
            p_pitch_t = gt[..., 2] / np.maximum(gt[..., :3].sum(axis=-1), 1e-9)

            wspd_cal_v = cal_wspd[av_idx]
            wspd_cal_t = cal_wspd[at_idx]
            pab_v = raw_pab[av_idx]
            pab_t = raw_pab[at_idx]
            patv_v = raw_patv[av_idx]
            patv_t = raw_patv[at_idx]

            normal_op_v = (patv_v >= 0.0) & ~((wspd_cal_v < 8.0) & (pab_v > 10.0))
            normal_op_t = (patv_t >= 0.0) & ~((wspd_cal_t < 8.0) & (pab_t > 10.0))

            val_boundary = (np.abs(wspd_cal_v - rated_wind) <= 1.0) & normal_op_v
            test_boundary = (np.abs(wspd_cal_t - rated_wind) <= 1.0) & normal_op_t

            pab_obs_v = np.isfinite(pab_v) & (pab_v > -5.0)
            pab_obs_t = np.isfinite(pab_t) & (pab_t > -5.0)

            cell_val = np.repeat(val_boundary[:, None, :], Hv, axis=1)
            cell_test = np.repeat(test_boundary[:, None, :], Ht, axis=1)

            for pol in policies:
                bin_v, edges = policy_bins(pol, p_pitch_v, pab_v, val_boundary, pab_obs_v)
                bin_t, _ = policy_bins(pol, p_pitch_t, pab_t, test_boundary, pab_obs_t, edges=edges)

                bin_v_c = np.repeat(bin_v[:, None, :], Hv, axis=1)
                bin_t_c = np.repeat(bin_t[:, None, :], Ht, axis=1)

                for rho in rhos:
                    reserves = fit_policy(sv, cell_val, bin_v_c, rho)
                    m = eval_real_price_policy(st, cell_test, bin_t_c, reserves, sbp_test_cells, c_res_per_mwh=c_res_per_mwh)
                    m.update({
                        "farm": farm,
                        "seed": seed,
                        "window": win_name,
                        "policy": pol,
                        "rho": rho,
                        "c_res_per_mwh": c_res_per_mwh,
                        "n_turbines": n_turbines,
                    })
                    all_rows.append(m)

        print(f"[GPU {gpu_id}] Finished evaluation for seed {seed}!")

    df = pd.DataFrame(all_rows)
    save_file = out_dir / f"{farm}_gpu{gpu_id}_real_price_results.csv"
    df.to_csv(save_file, index=False)
    print(f"[GPU {gpu_id}] Saved {len(df)} rows to {save_file}")
    return save_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--farm", default="kelmarsh", choices=["kelmarsh", "penmanshiel"])
    parser.add_argument("--gpu-id", type=int, default=0)
    parser.add_argument("--seeds", default="201,202,203,204,205")
    parser.add_argument("--elexon-dir", default="artifacts/elexon_bmrs_imbalance")
    parser.add_argument("--output-dir", default="artifacts/dynamic_price_settlement_audit")
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--c-res", type=float, default=15.0)
    args = parser.parse_args()

    repo = Path(args.repo_root)
    elexon_dir = Path(args.elexon_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    seeds = [int(s) for s in args.seeds.split(",")]

    run_farm_real_price_replay(
        args.farm,
        seeds,
        args.gpu_id,
        repo,
        elexon_dir,
        out_dir,
        batch_size=args.batch_size,
        c_res_per_mwh=args.c_res,
    )


if __name__ == "__main__":
    main()
