"""IEC 61400-12-1 Density-Standardized Multi-Year Rolling Evaluation Pipeline.

Evaluates trained RegimeAwareForecaster models across multi-year chronological SCADA datasets:
1. Kelmarsh (9 full years, 2016-2024, 473k steps, 6 turbines)
2. La Haute Borne (4 turbines, 54k steps)

Key methodologies:
- IEC 61400-12-1 air density normalization: v_norm = v_meas * (rho / rho_0)^(1/3)
  where rho is computed from barometric site altitude and local SCADA Etmp temperature.
- Rolling walk-forward folds and pooled multi-year windows.
- Multi-GPU parallel execution across 4x RTX 4090 GPUs.
- Reserve consequence evaluation under Newsvendor model (rho=10, 5, 20).
"""
from __future__ import annotations

import argparse
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

DT = 1.0 / 6.0
QUANTILE_GRID = [0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 0.975, 0.99]
N_BINS = 5


class WindowedDataset(Dataset):
    """Memory-efficient PyTorch Dataset over pre-loaded CacheBundle."""

    def __init__(
        self,
        bundle: CacheBundle,
        start_step: int,
        end_step: int,
        hist_len: int = 36,
        pred_len: int = 24,
    ) -> None:
        self.bundle = bundle
        self.hist_len = hist_len
        self.pred_len = pred_len
        anchor_start = max(start_step + hist_len - 1, hist_len - 1)
        anchor_end = min(end_step - pred_len - 1, bundle.features.shape[0] - pred_len - 1)
        if anchor_end < anchor_start:
            self.anchor_indices = np.empty((0,), dtype=np.int64)
        else:
            self.anchor_indices = np.arange(anchor_start, anchor_end + 1, dtype=np.int64)

    def __len__(self) -> int:
        return int(self.anchor_indices.shape[0])

    def __getitem__(self, index: int) -> dict[str, Any]:
        anchor = int(self.anchor_indices[index])
        hist_slice = slice(anchor - self.hist_len + 1, anchor + 1)
        future_slice = slice(anchor + 1, anchor + 1 + self.pred_len)
        return {
            "x_hist": torch.from_numpy(np.array(self.bundle.features[hist_slice], dtype=np.float32, copy=True)),
            "feature_mask_hist": torch.from_numpy(
                np.array(self.bundle.feature_mask[hist_slice], dtype=np.float32, copy=True)
            ),
            "edge_index_hist": torch.from_numpy(
                np.array(self.bundle.edge_index[hist_slice], dtype=np.int64, copy=True)
            ),
            "edge_weight_hist": torch.from_numpy(
                np.array(self.bundle.edge_weight[hist_slice], dtype=np.float32, copy=True)
            ),
            "target": torch.from_numpy(np.array(self.bundle.target[future_slice], dtype=np.float32, copy=True)),
            "target_mask": torch.from_numpy(
                np.array(self.bundle.target_mask[future_slice], dtype=np.float32, copy=True)
            ),
            "anchor_physics": torch.from_numpy(
                np.array(self.bundle.physics_model[anchor], dtype=np.float32, copy=True)
            ),
            "anchor_index": torch.tensor(anchor, dtype=torch.int64),
        }


def compute_iec_density(
    etmp_norm: np.ndarray,
    etmp_mean: float,
    etmp_std: float,
    elevation: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Calculate air density and wind speed correction ratio per IEC 61400-12-1."""
    etmp_degC = etmp_norm * etmp_std + etmp_mean
    T_K = np.clip(etmp_degC + 273.15, 233.15, 323.15)  # [-40C, +50C]
    p0 = 101325.0
    p = p0 * (1.0 - 0.0065 * elevation / 288.15) ** 5.25588
    rho = p / (287.058 * T_K)
    corr_ratio = (rho / 1.225) ** (1.0 / 3.0)
    return corr_ratio, rho


def policy_bins(name: str, p_pitch: np.ndarray, pab: np.ndarray, val_mask: np.ndarray, pab_obs: np.ndarray, edges=None):
    if name == "global":
        return np.zeros_like(p_pitch, dtype=int), None
    if name == "soft-gate-bin":
        values = p_pitch
        if edges is None:
            if np.sum(val_mask) < 10:
                edges = np.linspace(0, 1, N_BINS + 1)[1:-1]
            else:
                edges = np.quantile(values[val_mask], np.linspace(0, 1, N_BINS + 1)[1:-1])
        return np.clip(np.searchsorted(edges, values), 0, N_BINS - 1), edges
    if name == "soft-pab-bin":
        values = pab
        sel = val_mask & pab_obs
        if edges is None:
            if np.sum(sel) < 10:
                edges = np.linspace(0, 30, N_BINS + 1)[1:-1]
            else:
                edges = np.quantile(values[sel], np.linspace(0, 1, N_BINS + 1)[1:-1])
        bins = np.clip(np.searchsorted(edges, values), 0, N_BINS - 1)
        bins[~pab_obs] = 0
        return bins, edges
    raise ValueError(name)


def fit_policy(s_val: np.ndarray, cell_val: np.ndarray, bin_val: np.ndarray, rho: float) -> dict[int, tuple[float, float]]:
    sel = cell_val & np.isfinite(s_val)
    out = {}
    unique_bins = np.unique(bin_val[cell_val]) if np.any(cell_val) else np.arange(N_BINS)
    for b in unique_bins:
        sb = s_val[sel & (bin_val == b)]
        if sb.size < 50:
            sb = s_val[sel]
        if sb.size == 0:
            out[int(b)] = (0.90, 100.0)
            continue
        best = None
        for q in QUANTILE_GRID:
            r = np.quantile(sb, q)
            cost = (r * sb.size + rho * np.maximum(sb - r, 0).sum()) * DT
            if best is None or cost < best[0]:
                best = (cost, q, r)
        out[int(b)] = (best[1], best[2])
    return out


def eval_policy(s_test: np.ndarray, cell_test: np.ndarray, bin_test: np.ndarray, reserves: dict[int, tuple[float, float]], rho: float) -> dict[str, Any]:
    sel = cell_test & np.isfinite(s_test)
    s = s_test[sel]
    b = bin_test[sel]
    if s.size == 0:
        return {"total_cost": 0.0, "violation_rate": 0.0, "reserve": 0.0, "shortage": 0.0, "n_cells": 0}
    r = np.array([reserves.get(int(x), (0.90, 100.0))[1] for x in b])
    return {
        "total_cost": float((r.sum() + rho * np.maximum(s - r, 0).sum()) * DT),
        "violation_rate": float(np.mean(s > r)),
        "reserve": float(r.sum() * DT),
        "shortage": float(np.maximum(s - r, 0).sum() * DT),
        "n_cells": int(s.size),
    }


def run_inference_on_slice(
    model: torch.nn.Module,
    bundle: CacheBundle,
    start_step: int,
    end_step: int,
    device: torch.device,
    batch_size: int = 256,
) -> dict[str, np.ndarray]:
    """Execute forward inference on a continuous slice of the dataset."""
    ds = WindowedDataset(bundle, start_step, end_step)
    loader = DataLoader(ds, batch_size=batch_size, shuffle=False, num_workers=2, pin_memory=True)

    preds, targets, masks, gates, anchors = [], [], [], [], []
    model.eval()
    with torch.no_grad():
        for batch in loader:
            batch = to_device(batch, device)
            with torch.amp.autocast("cuda"):
                p, g, _ = model(
                    batch["x_hist"],
                    batch["edge_index_hist"],
                    batch["edge_weight_hist"],
                    batch["feature_mask_hist"],
                    batch["anchor_physics"],
                )
            preds.append(p.float().cpu().numpy())
            targets.append(batch["target"].float().cpu().numpy())
            masks.append(batch["target_mask"].float().cpu().numpy())
            if g is not None:
                gates.append(g.float().cpu().numpy())
            anchors.append(batch["anchor_index"].cpu().numpy())

    return {
        "pred": np.concatenate(preds, axis=0) if preds else np.empty((0,)),
        "target": np.concatenate(targets, axis=0) if targets else np.empty((0,)),
        "mask": np.concatenate(masks, axis=0) if masks else np.empty((0,)),
        "gate": np.concatenate(gates, axis=0) if gates else np.empty((0,)),
        "anchor_idx": np.concatenate(anchors, axis=0) if anchors else np.empty((0,), dtype=np.int64),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default="/root/paper3_audit_rerun_20260830")
    parser.add_argument("--farm", default="kelmarsh", choices=["kelmarsh", "penmanshiel", "la_haute_borne"])
    parser.add_argument("--gpu-id", type=int, default=0)
    parser.add_argument("--seeds", default="201")
    parser.add_argument("--rated-wind", type=float, default=None)
    parser.add_argument("--band", type=float, default=1.0)
    parser.add_argument("--rhos", default="10.0,5.0,20.0")
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--output-dir", default="/root/paper3_audit_rerun_20260830/artifacts/iec_density_rolling_eval")
    args = parser.parse_args()

    repo = Path(args.repo_root)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(f"cuda:{args.gpu_id}" if torch.cuda.is_available() else "cpu")

    # Site configuration
    if args.farm == "kelmarsh":
        elevation = 137.0
        rated_wind = 11.0 if args.rated_wind is None else args.rated_wind
        cache_dir = repo / "artifacts/cache_external_wind/external_wind_kelmarsh_chronological"
        model_root = repo / "artifacts/signature_gate_farms_runs_20260903/kelmarsh/canonical"
        steps_per_year = 52560
    elif args.farm == "penmanshiel":
        elevation = 230.0
        rated_wind = 11.5 if args.rated_wind is None else args.rated_wind
        cache_dir = repo / "artifacts/cache_external_wind/external_wind_penmanshiel_chronological"
        model_root = repo / "artifacts/signature_gate_farms_runs_20260903/penmanshiel/canonical"
        steps_per_year = 52560
    else:  # la_haute_borne
        elevation = 380.0
        rated_wind = 11.5 if args.rated_wind is None else args.rated_wind
        cache_dir = repo / "artifacts/cache_external_wind/external_wind_la_haute_borne_chronological"
        model_root = repo / "artifacts/signature_gate_lhb_runs_20260902/canonical"
        steps_per_year = 13500  # quarterly slices

    print(f"[GPU {args.gpu_id}] Loading cache bundle for {args.farm}...")
    bundle = load_cache_bundle(cache_dir)
    num_steps = bundle.features.shape[0]
    num_turbines = bundle.features.shape[1]
    print(f"[GPU {args.gpu_id}] Dataset: {num_steps} steps, {num_turbines} turbines.")

    # Compute IEC 61400-12-1 density calibration across the entire dataset
    meta = bundle.metadata
    etmp_stat = meta["feature_stats"]["Etmp"]
    etmp_norm = bundle.features[..., 5]
    corr_ratio, rho_arr = compute_iec_density(etmp_norm, etmp_stat["mean"], etmp_stat["std"], elevation)

    raw_wspd = bundle.physics[..., 0]
    cal_wspd = raw_wspd * corr_ratio
    raw_pab = bundle.physics[..., 1]
    raw_patv = bundle.physics[..., 3] if bundle.physics.shape[-1] > 3 else np.ones_like(raw_wspd)

    print(f"[GPU {args.gpu_id}] IEC 61400-12-1 calibrated wind speed computed (mean={np.nanmean(cal_wspd):.2f} m/s).")

    seeds = [int(s) for s in args.seeds.split(",")]
    rhos = [float(r) for r in args.rhos.split(",")]
    policies = ["global", "soft-gate-bin", "soft-pab-bin"]

    all_rows = []

    for seed in seeds:
        ckpt_path = model_root / f"wtb_bal_align_force_seed{seed}" / "best_model.pt"
        if not ckpt_path.exists():
            print(f"[GPU {args.gpu_id}] WARNING: checkpoint {ckpt_path} not found, skipping!")
            continue

        print(f"[GPU {args.gpu_id}] Loading model seed {seed} from {ckpt_path}...")
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
        if args.farm in ["kelmarsh", "penmanshiel"]:
            # Walk-Forward Rolling Folds (2 years train/cal, 1 year test)
            n_years = num_steps // steps_per_year
            for f_idx in range(n_years - 2):
                v_start = f_idx * steps_per_year
                v_end = v_start + 2 * steps_per_year
                t_start = v_end
                t_end = min(t_start + steps_per_year, num_steps)
                windows.append((f"rolling_fold_{f_idx+1}", v_start, v_end, t_start, t_end))
            # Individual Annual Windows (calibrated on prior year or baseline window)
            cal_base_start, cal_base_end = 0, steps_per_year
            for y_idx in range(n_years):
                t_start = y_idx * steps_per_year
                t_end = min(t_start + steps_per_year, num_steps)
                windows.append((f"year_{y_idx+1}", cal_base_start, cal_base_end, t_start, t_end))
            # Full Pooled Multi-Year Window (Calibrate on initial 180 days, test on all remaining multi-year data)
            windows.append(("pooled_multiyear_full", 0, 180 * 144, 180 * 144, num_steps))
        else:
            # LHB Quarterly Folds
            for q_idx in range(3):
                v_start = q_idx * steps_per_year
                v_end = v_start + steps_per_year
                t_start = v_end
                t_end = min(t_start + steps_per_year, num_steps)
                windows.append((f"rolling_quarter_{q_idx+1}", v_start, v_end, t_start, t_end))
            # Full LHB Pooled Window (Calibrate first 180 days, test remainder)
            windows.append(("pooled_annual_full", 0, 180 * 144, 180 * 144, num_steps))

        print(f"[GPU {args.gpu_id}] Running {len(windows)} rolling evaluation windows for seed {seed}...")

        # Cache inference predictions by time step to avoid redundant computation
        # Compute forward pass across the required ranges
        all_eval_indices = set()
        for _, vs, ve, ts, te in windows:
            all_eval_indices.update(range(vs, ve))
            all_eval_indices.update(range(ts, te))

        min_step = min(all_eval_indices)
        max_step = max(all_eval_indices)
        print(f"[GPU {args.gpu_id}] Running continuous forward inference from step {min_step} to {max_step}...")
        t0 = time.perf_counter()
        inf_result = run_inference_on_slice(model, bundle, min_step, max_step, device, batch_size=args.batch_size)
        torch.cuda.synchronize()
        dt = time.perf_counter() - t0
        print(f"[GPU {args.gpu_id}] Inference complete: {inf_result['anchor_idx'].size} windows in {dt:.1f}s ({inf_result['anchor_idx'].size / max(dt, 0.001):.1f} w/s)")

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

            # Extract calibrated boundary fields
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

            val_boundary = (np.abs(wspd_cal_v - rated_wind) <= args.band) & normal_op_v
            test_boundary = (np.abs(wspd_cal_t - rated_wind) <= args.band) & normal_op_t

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
                    m = eval_policy(st, cell_test, bin_t_c, reserves, rho)
                    m.update({
                        "farm": args.farm,
                        "seed": seed,
                        "window": win_name,
                        "policy": pol,
                        "rho": rho,
                        "rated_wind": rated_wind,
                        "band": args.band,
                        "elevation": elevation,
                    })
                    all_rows.append(m)

        print(f"[GPU {args.gpu_id}] Finished evaluation for seed {seed}!")

    df = pd.DataFrame(all_rows)
    save_file = out_dir / f"{args.farm}_gpu{args.gpu_id}_results.csv"
    df.to_csv(save_file, index=False)
    print(f"[GPU {args.gpu_id}] Saved {len(df)} rows to {save_file}")


if __name__ == "__main__":
    main()
