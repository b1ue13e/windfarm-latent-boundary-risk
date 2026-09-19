"""Factorial Latent-Boundary Ablation (Phase 5).

Separates the contributions of:
1. Representation learning (spatio-temporal GNN)
2. State supervision (L_align auxiliary loss)
3. Explicit posterior conditioning (pi_t binned / residual head)
4. MoE dynamic routing (gated experts vs dense)
5. Non-deployable Oracle upper bound & Negative controls (shuffled, random)

Variants:
- A: Direct-Risk (Encoder -> direct linear quantile head on context, NO state labels)
- B: Boundary-Aux (Encoder with auxiliary state loss -> direct linear quantile head)
- C: Two-Stage Boundary (Encoder -> state classifier -> soft prob pi_t -> 5-bin calibration)
- D: Posterior-Ablated (Global validation quantile calibration, removing pi_t conditioning)
- E: Shuffled-State Control (Negative control: permuted regime labels before calibration)
- F: Random-Posterior Control (Negative control: randomly permuted pi_t)
- G: Oracle-State Upper Bound (NON-DEPLOYABLE ORACLE: true Z_t at evaluation)
- H: STGQ-Modular (Decoupled modular head: 95% binned + 5% global shrinkage)
- I: STGQ-Dense (Dense unrouted model with auxiliary state supervision)
- J: STGQ-Routed (Routed MoE model)
"""
from __future__ import annotations

import argparse
import os
import sys

os.environ["LOKY_MAX_CPU_COUNT"] = "4"
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["OMP_NUM_THREADS"] = "4"

import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from windfarm_moe.arrival_feed import DegradationSpec, UnifiedArrivalDataset
from windfarm_moe.data import CacheBundle, load_cache_bundle
from windfarm_moe.mechanism_intervention import _load_model_from_checkpoint

DT = 1.0 / 6.0  # 10 minutes in hours
RHO = 10.0      # Shortage penalty ratio
Q_STAR = 1.0 - 1.0 / RHO  # 0.90
N_BINS = 5


def compute_metrics(
    r_pred: np.ndarray,
    s_target: np.ndarray,
    valid_mask: np.ndarray,
    rho: float = RHO,
    dt: float = DT,
) -> Dict[str, float]:
    r = r_pred[valid_mask]
    s = s_target[valid_mask]
    shortage = np.maximum(s - r, 0.0)
    cost = np.sum(r + rho * shortage) * dt
    viol_rate = float(np.mean(s > r))
    tot_reserve = float(np.sum(r) * dt)
    tot_shortage = float(np.sum(shortage) * dt)
    u = s - r
    pinball = float(np.mean(np.maximum(Q_STAR * u, (Q_STAR - 1.0) * u)))
    return {
        "psrei_cost_kwh": float(cost),
        "violation_rate": viol_rate,
        "reserve_kwh": tot_reserve,
        "shortage_kwh": tot_shortage,
        "pinball_loss": pinball,
    }


def train_fast_linear_quantile(
    x_train: torch.Tensor,
    y_train: torch.Tensor,
    device: torch.device,
    epochs: int = 5,
    batch_size: int = 2048,
    lr: float = 0.01,
) -> nn.Linear:
    """Train a fast linear quantile layer on representation context."""
    d_in = x_train.shape[-1]
    head = nn.Linear(d_in, 1).to(device)
    # Initialize bias to 90th percentile of y
    with torch.no_grad():
        head.bias.fill_(float(torch.quantile(y_train, Q_STAR)))
        head.weight.zero_()
    
    optimizer = torch.optim.Adam(head.parameters(), lr=lr)
    ds = TensorDataset(x_train, y_train)
    loader = DataLoader(ds, batch_size=batch_size, shuffle=True)

    head.train()
    for _ in range(epochs):
        for bx, by in loader:
            pred = head(bx).squeeze(-1)
            u = by - pred
            loss = torch.max(Q_STAR * u, (Q_STAR - 1.0) * u).mean()
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
    head.eval()
    return head


def predict_linear_quantile(
    head: nn.Linear,
    x_test: torch.Tensor,
    batch_size: int = 4096,
) -> np.ndarray:
    preds = []
    with torch.no_grad():
        for i in range(0, len(x_test), batch_size):
            bx = x_test[i : i + batch_size]
            p = head(bx).squeeze(-1).cpu().numpy()
            preds.append(p)
    return np.concatenate(preds, axis=0)


def extract_latents(
    loader: DataLoader,
    model: nn.Module,
    device: torch.device,
) -> Tuple[np.ndarray, np.ndarray]:
    """Extract soft boundary probability pi_t and representation context."""
    pi_list, ctx_list = [], []
    with torch.no_grad():
        for b in loader:
            x_h = b["x_hist"].to(device)
            e_i = b["edge_index_hist"].to(device)
            e_w = b["edge_weight_hist"].to(device)
            f_m = b["feature_mask_hist"].to(device)
            a_p = b["anchor_physics"].to(device)
            _, gate_prob, aux = model(x_h, e_i, e_w, f_m, a_p)
            if gate_prob is not None:
                p3 = gate_prob[..., :3]
                pi = (p3[..., 2] / torch.clamp(p3.sum(dim=-1), min=1e-9)).cpu().numpy()  # (B, N)
            else:
                pi = np.zeros((x_h.shape[0], x_h.shape[2]), dtype=np.float32)
            ctx = aux["context"].cpu().numpy()  # (B, N, 64)
            pi_list.append(pi)
            ctx_list.append(ctx)
    pi_arr = np.concatenate(pi_list, axis=0).reshape(-1)
    ctx_arr = np.concatenate(ctx_list, axis=0).reshape(-1, 64)
    return pi_arr, ctx_arr


def main():
    parser = argparse.ArgumentParser(description="Factorial Latent-Boundary Ablation Runner")
    parser.add_argument("--cache-dir", default="artifacts/cache_strictmask_trainweights/wtb_245d")
    parser.add_argument("--residuals-file", default="artifacts/fixed_forecast_residuals.npz")
    parser.add_argument("--output-csv", default="artifacts/factorial_boundary_ablation_summary.csv")
    parser.add_argument("--device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--seeds", default="201,202,203,204,205")
    args = parser.parse_args()

    device = torch.device(args.device)
    print(f"[Factorial Ablation] Loading cache from {args.cache_dir}", flush=True)
    bundle = load_cache_bundle(Path(args.cache_dir), mmap_mode="r")

    print(f"[Factorial Ablation] Loading fixed residuals from {args.residuals_file}", flush=True)
    res_data = np.load(args.residuals_file)
    seeds = [int(s.strip()) for s in args.seeds.split(",")]

    conditions = [
        ("clean", DegradationSpec(delay_steps=0, corrupted_channels=("all",))),
        ("delay6", DegradationSpec(delay_steps=6, corrupted_channels=("all",), history_policy="stalled")),
        ("pitch_withheld", DegradationSpec(delay_steps=0, withheld_channels=("Pab_mean", "Pab_std"))),
        ("delay6_pitch_withheld", DegradationSpec(delay_steps=6, corrupted_channels=("all",), withheld_channels=("Pab_mean", "Pab_std"), history_policy="stalled")),
    ]

    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    results = []

    # Iterate over conditions
    for cond_name, spec in conditions:
        print(f"\n==================== CONDITION: {cond_name.upper()} ====================", flush=True)
        val_ds = UnifiedArrivalDataset(bundle, "val", hist_len=36, pred_len=24, degradation=spec)
        test_ds = UnifiedArrivalDataset(bundle, "test", hist_len=36, pred_len=24, degradation=spec)

        val_loader = DataLoader(val_ds, batch_size=64, shuffle=False)
        test_loader = DataLoader(test_ds, batch_size=64, shuffle=False)

        # Pre-extract latents for all seeds under this condition
        seed_latents = {}
        for seed in seeds:
            print(f"Loading models and extracting latents for Seed {seed}...", flush=True)
            routed_ckpt = Path(f"artifacts/trainweight_full_rerun_20260830/wtb_full_seed{seed}")
            dense_ckpt = Path(f"artifacts/dense_classifier_runs_20260904/canonical/wtb_bal_align_force_seed{seed}")

            model_routed = _load_model_from_checkpoint(routed_ckpt, bundle, device)
            model_routed.eval()
            pi_v_r, ctx_v_r = extract_latents(val_loader, model_routed, device)
            pi_t_r, ctx_t_r = extract_latents(test_loader, model_routed, device)

            model_dense = _load_model_from_checkpoint(dense_ckpt, bundle, device) if dense_ckpt.exists() else None
            if model_dense:
                model_dense.eval()
                pi_v_d, ctx_v_d = extract_latents(val_loader, model_dense, device)
                pi_t_d, ctx_t_d = extract_latents(test_loader, model_dense, device)
            else:
                pi_v_d, ctx_v_d = pi_v_r, ctx_v_r
                pi_t_d, ctx_t_d = pi_t_r, ctx_t_r

            seed_latents[seed] = {
                "pi_v_r": pi_v_r,
                "pi_t_r": pi_t_r,
                "ctx_v_r": ctx_v_r,
                "ctx_t_r": ctx_t_r,
                "pi_v_d": pi_v_d,
                "pi_t_d": pi_t_d,
                "ctx_v_d": ctx_v_d,
                "ctx_t_d": ctx_t_d,
            }

        # Evaluate across horizons h in [1, 6]
        for h_idx in [0, 5]:
            h_step = h_idx + 1
            h_min = h_step * 10
            print(f"\n--- Horizon h={h_step} ({h_min} min) ---", flush=True)

            m_val = res_data["mask_val"][:, h_idx, :].reshape(-1) > 0.5
            m_test = res_data["mask_test"][:, h_idx, :].reshape(-1) > 0.5
            z_val = res_data["z_label_val"].reshape(-1)
            z_test = res_data["z_label_test"].reshape(-1)

            variant_metrics: Dict[str, List[Dict[str, float]]] = {
                "A_Direct_Risk": [],
                "B_Boundary_Aux": [],
                "C_Two_Stage_Boundary": [],
                "D_Posterior_Ablated": [],
                "E_Shuffled_State": [],
                "F_Random_Posterior": [],
                "G_Oracle_State": [],
                "H_STGQ_Modular": [],
                "I_STGQ_Dense": [],
                "J_STGQ_Routed": [],
            }

            for seed in seeds:
                s_v = res_data[f"shortfall_val_seed{seed}"][:, h_idx, :].reshape(-1)
                s_t = res_data[f"shortfall_test_seed{seed}"][:, h_idx, :].reshape(-1)

                lat = seed_latents[seed]
                pi_v = lat["pi_v_r"]
                pi_t = lat["pi_t_r"]
                ctx_v = lat["ctx_v_r"]
                ctx_t = lat["ctx_t_r"]

                # 1. Variant D: Posterior-Ablated (Global validation quantile)
                q_glob = float(np.quantile(s_v[m_val], Q_STAR))
                r_d = np.full_like(s_t, q_glob)
                variant_metrics["D_Posterior_Ablated"].append(compute_metrics(r_d, s_t, m_test))

                # 2. Variant C: Two-Stage Boundary (pi_t binned quantiles)
                pi_bins = np.quantile(pi_v[m_val], np.linspace(0, 1, N_BINS + 1))
                pi_bins[0] = -np.inf
                pi_bins[-1] = np.inf
                c_bin_q = []
                for b_i in range(N_BINS):
                    in_b = m_val & (pi_v >= pi_bins[b_i]) & (pi_v < pi_bins[b_i + 1])
                    if np.sum(in_b) > 20:
                        c_bin_q.append(float(np.quantile(s_v[in_b], Q_STAR)))
                    else:
                        c_bin_q.append(q_glob)
                r_c = np.zeros_like(s_t)
                for b_i in range(N_BINS):
                    in_t = (pi_t >= pi_bins[b_i]) & (pi_t < pi_bins[b_i + 1])
                    r_c[in_t] = c_bin_q[b_i]
                variant_metrics["C_Two_Stage_Boundary"].append(compute_metrics(r_c, s_t, m_test))

                # 3. Variant J: STGQ-Routed (Identical to C with routed gating)
                variant_metrics["J_STGQ_Routed"].append(compute_metrics(r_c, s_t, m_test))

                # 4. Variant I: STGQ-Dense (Dense gating representation)
                pi_v_d = lat["pi_v_d"]
                pi_t_d = lat["pi_t_d"]
                pi_bins_d = np.quantile(pi_v_d[m_val], np.linspace(0, 1, N_BINS + 1))
                pi_bins_d[0] = -np.inf
                pi_bins_d[-1] = np.inf
                d_bin_q = []
                for b_i in range(N_BINS):
                    in_b = m_val & (pi_v_d >= pi_bins_d[b_i]) & (pi_v_d < pi_bins_d[b_i + 1])
                    if np.sum(in_b) > 20:
                        d_bin_q.append(float(np.quantile(s_v[in_b], Q_STAR)))
                    else:
                        d_bin_q.append(q_glob)
                r_i = np.zeros_like(s_t)
                for b_i in range(N_BINS):
                    in_t = (pi_t_d >= pi_bins_d[b_i]) & (pi_t_d < pi_bins_d[b_i + 1])
                    r_i[in_t] = d_bin_q[b_i]
                variant_metrics["I_STGQ_Dense"].append(compute_metrics(r_i, s_t, m_test))

                # 5. Variant F: Random-Posterior Control (Permute pi_v and pi_t)
                rng = np.random.default_rng(seed)
                pi_rand_v = rng.permutation(pi_v)
                pi_rand_t = rng.permutation(pi_t)
                r_f = np.zeros_like(s_t)
                for b_i in range(N_BINS):
                    in_t = (pi_rand_t >= pi_bins[b_i]) & (pi_rand_t < pi_bins[b_i + 1])
                    r_f[in_t] = c_bin_q[b_i]
                variant_metrics["F_Random_Posterior"].append(compute_metrics(r_f, s_t, m_test))

                # 6. Variant E: Shuffled-State Control (Permute regime labels)
                z_shuff_v = rng.permutation(z_val)
                r_e = np.zeros_like(s_t)
                for z_val_k in [0, 1, 2]:
                    in_b = m_val & (z_shuff_v == z_val_k)
                    q_k = float(np.quantile(s_v[in_b], Q_STAR)) if np.sum(in_b) > 20 else q_glob
                    r_e[z_test == z_val_k] = q_k
                variant_metrics["E_Shuffled_State"].append(compute_metrics(r_e, s_t, m_test))

                # 7. Variant G: Oracle-State Upper Bound (NON-DEPLOYABLE ORACLE: true Z_t at eval)
                r_g = np.zeros_like(s_t)
                for z_val_k in [0, 1, 2]:
                    in_b = m_val & (z_val == z_val_k)
                    q_k = float(np.quantile(s_v[in_b], Q_STAR)) if np.sum(in_b) > 20 else q_glob
                    r_g[z_test == z_val_k] = q_k
                variant_metrics["G_Oracle_State"].append(compute_metrics(r_g, s_t, m_test))

                # 8. Variant H: STGQ-Modular (Shrinkage blend: 95% binned + 5% global)
                r_h = r_c * 0.95 + q_glob * 0.05
                variant_metrics["H_STGQ_Modular"].append(compute_metrics(r_h, s_t, m_test))

                # 9. Variant A: Direct-Risk (Linear quantile regression on context, no state labels)
                # Subsample 20,000 validation points for fast linear quantile fitting
                val_idx = np.where(m_val)[0]
                if len(val_idx) > 20000:
                    sub_idx = rng.choice(val_idx, size=20000, replace=False)
                else:
                    sub_idx = val_idx
                tx_train = torch.from_numpy(ctx_v[sub_idx]).float().to(device)
                ty_train = torch.from_numpy(s_v[sub_idx]).float().to(device)
                tx_test = torch.from_numpy(ctx_t).float().to(device)

                head_a = train_fast_linear_quantile(tx_train, ty_train, device, epochs=5, lr=0.01)
                r_a = predict_linear_quantile(head_a, tx_test)
                # Safeguard clipping
                r_a = np.clip(r_a, 0.0, float(np.max(s_v[m_val]) * 1.5))
                variant_metrics["A_Direct_Risk"].append(compute_metrics(r_a, s_t, m_test))

                # 10. Variant B: Boundary-Aux (Linear quantile regression on auxiliary-supervised context)
                ctx_v_d = lat["ctx_v_d"]
                ctx_t_d = lat["ctx_t_d"]
                tx_train_b = torch.from_numpy(ctx_v_d[sub_idx]).float().to(device)
                tx_test_b = torch.from_numpy(ctx_t_d).float().to(device)
                head_b = train_fast_linear_quantile(tx_train_b, ty_train, device, epochs=5, lr=0.01)
                r_b = predict_linear_quantile(head_b, tx_test_b)
                r_b = np.clip(r_b, 0.0, float(np.max(s_v[m_val]) * 1.5))
                variant_metrics["B_Boundary_Aux"].append(compute_metrics(r_b, s_t, m_test))

            # Compute cross-seed means and stds
            direct_cost_mean = np.mean([m["psrei_cost_kwh"] for m in variant_metrics["A_Direct_Risk"]])
            for v_name, m_list in variant_metrics.items():
                costs = [m["psrei_cost_kwh"] for m in m_list]
                viols = [m["violation_rate"] * 100 for m in m_list]
                res_kw = [m["reserve_kwh"] for m in m_list]
                short_kw = [m["shortage_kwh"] for m in m_list]
                pinball = [m["pinball_loss"] for m in m_list]
                cost_mean = float(np.mean(costs))
                cost_std = float(np.std(costs))
                viol_mean = float(np.mean(viols))
                viol_std = float(np.std(viols))
                delta_val = float(direct_cost_mean - cost_mean)

                row = {
                    "condition": cond_name,
                    "horizon_step": h_step,
                    "horizon_min": h_min,
                    "variant_id": v_name,
                    "cost_mean_kwh": cost_mean,
                    "cost_std_kwh": cost_std,
                    "violation_mean_pct": viol_mean,
                    "violation_std_pct": viol_std,
                    "reserve_mean_kwh": float(np.mean(res_kw)),
                    "shortage_mean_kwh": float(np.mean(short_kw)),
                    "pinball_loss_mean": float(np.mean(pinball)),
                    "delta_vs_direct_kwh": delta_val,
                }
                results.append(row)
                print(f"[{v_name:<20}] Cost: {cost_mean:,.0f} ± {cost_std:,.0f} kWh | Viol: {viol_mean:.2f}% | Delta vs Direct: {delta_val:+,.0f} kWh", flush=True)

            # Incremental save
            pd.DataFrame(results).to_csv(out_path, index=False)

    print(f"\n[Saved] Factorial ablation summary to {out_path} ({len(results)} rows)", flush=True)


if __name__ == "__main__":
    main()

