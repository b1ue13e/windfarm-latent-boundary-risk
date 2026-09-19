"""Direct Simple-Baseline Challenge (Phase 4).

Evaluates 5 conceptually simple direct conditional quantile baselines under the
EXACT same deployable information set I_t^(d) and the EXACT same frozen residual
target s_t = max(yhat_fixed_t - y_t, 0) across horizons h in [1, 6] (and full sweep)
and degradation conditions:
1. Clean (tau=0)
2. Delay-6 (tau=60m)
3. Pitch-Withheld (tau=0, no pitch)
4. Delay-6 + Pitch-Withheld (tau=60m, no pitch)

Baselines:
- B0: Global empirical quantile Q_0.90(s)
- B1: Empirical conditional wind-speed binned quantile
- B2: Linear quantile regression (exact pinball loss on GPU)
- B3: Quantile GBDT (HistGradientBoosting / LightGBM)
- B4: Small direct MLP (capacity-matched, pinball loss, NO state supervision)
"""
from __future__ import annotations

import argparse
import os
import sys

os.environ["LOKY_MAX_CPU_COUNT"] = "4"
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["OMP_NUM_THREADS"] = "4"

import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from windfarm_moe.arrival_feed import DegradationSpec, UnifiedArrivalDataset
from windfarm_moe.data import CacheBundle, load_cache_bundle

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


def pinball_loss_torch(pred: torch.Tensor, target: torch.Tensor, q: float = Q_STAR) -> torch.Tensor:
    u = target - pred
    return torch.maximum(q * u, (q - 1.0) * u).mean()


class LinearQuantileRegressorGPU(nn.Module):
    """Exact convex linear quantile regression via PyTorch on GPU."""
    def __init__(self, in_dim: int):
        super().__init__()
        self.linear = nn.Linear(in_dim, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear(x).squeeze(-1)


class DirectMLP(nn.Module):
    """Small capacity-matched 2-layer MLP trained directly on residual quantile objective."""
    def __init__(self, in_dim: int, hidden_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 1),
            nn.ReLU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def main():
    parser = argparse.ArgumentParser(description="Direct Simple-Baseline Challenge")
    parser.add_argument("--cache-dir", default="artifacts/cache_strictmask_trainweights/wtb_245d")
    parser.add_argument("--residuals-file", default="artifacts/fixed_forecast_residuals.npz")
    parser.add_argument("--output-csv", default="artifacts/direct_quantile_baselines_summary.csv")
    parser.add_argument("--device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--seed", type=int, default=201)
    args = parser.parse_args()

    device = torch.device(args.device)
    print(f"[Direct Baselines] Loading bundle from {args.cache_dir}", flush=True)
    bundle = load_cache_bundle(Path(args.cache_dir), mmap_mode="r")

    print(f"[Direct Baselines] Loading fixed residuals from {args.residuals_file}", flush=True)
    res_data = np.load(args.residuals_file)
    s_val = res_data[f"shortfall_val_seed{args.seed}"]    # (T_val, 6, 134)
    s_test = res_data[f"shortfall_test_seed{args.seed}"]  # (T_test, 6, 134)
    m_val = res_data["mask_val"]                          # (T_val, 6, 134)
    m_test = res_data["mask_test"]                        # (T_test, 6, 134)

    conditions = [
        ("clean", DegradationSpec(delay_steps=0, corrupted_channels=("all",))),
        ("delay6", DegradationSpec(delay_steps=6, corrupted_channels=("all",), history_policy="stalled")),
        ("pitch_withheld", DegradationSpec(delay_steps=0, withheld_channels=("Pab_mean", "Pab_std"))),
        ("delay6_pitch_withheld", DegradationSpec(delay_steps=6, corrupted_channels=("all",), withheld_channels=("Pab_mean", "Pab_std"), history_policy="stalled")),
    ]

    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    all_rows = []

    for cond_name, spec in conditions:
        print(f"\n==================== CONDITION: {cond_name.upper()} ====================", flush=True)
        t_c0 = time.time()
        val_ds = UnifiedArrivalDataset(bundle, "val", hist_len=36, pred_len=24, degradation=spec)
        test_ds = UnifiedArrivalDataset(bundle, "test", hist_len=36, pred_len=24, degradation=spec)

        val_loader = DataLoader(val_ds, batch_size=128, shuffle=False)
        test_loader = DataLoader(test_ds, batch_size=128, shuffle=False)

        def extract_features(loader):
            feats_list, wspd_list = [], []
            for b in loader:
                x = b["x_hist"]  # (B, H, N, C)
                B, H, N, C = x.shape
                x_mean = x.mean(dim=1)  # (B, N, C)
                x_std = x.std(dim=1)    # (B, N, C)
                x_last = x[:, -1, :, :] # (B, N, C)
                anc = b["anchor_physics"] # (B, N, 4)
                fused = torch.cat([x_mean, x_std, x_last, anc], dim=-1) # (B, N, 3*C + 4)
                feats_list.append(fused.numpy())
                wspd_list.append(anc[..., 0].numpy())
            return np.concatenate(feats_list, axis=0), np.concatenate(wspd_list, axis=0)

        X_val, Wspd_val = extract_features(val_loader)   # (T_val, 134, F)
        X_test, Wspd_test = extract_features(test_loader) # (T_test, 134, F)
        T_v, N_turb, F_dim = X_val.shape
        T_t, _, _ = X_test.shape

        X_val_flat = X_val.reshape(T_v * N_turb, F_dim)
        X_test_flat = X_test.reshape(T_t * N_turb, F_dim)
        scaler = StandardScaler()
        X_val_norm = scaler.fit_transform(X_val_flat).astype(np.float32)
        X_test_norm = scaler.transform(X_test_flat).astype(np.float32)

        eval_horizons = [0, 5]  # Index 0 is h=1 (10m), index 5 is h=6 (60m)

        for h_idx in eval_horizons:
            h_step = h_idx + 1
            h_min = h_step * 10
            print(f"\n--- Evaluating Horizon h={h_step} ({h_min} min) ---", flush=True)

            s_v_flat = s_val[:, h_idx, :].reshape(T_v * N_turb)
            s_t_flat = s_test[:, h_idx, :].reshape(T_t * N_turb)
            m_v_flat = m_val[:, h_idx, :].reshape(T_v * N_turb) > 0.5
            m_t_flat = m_test[:, h_idx, :].reshape(T_t * N_turb) > 0.5

            # B0: Global Empirical Quantile Q_0.90(s)
            q_global = float(np.quantile(s_v_flat[m_v_flat], Q_STAR))
            r_b0 = np.full_like(s_t_flat, q_global)
            res_b0 = compute_metrics(r_b0, s_t_flat, m_t_flat)
            print(f"B0 Global: Cost={res_b0['psrei_cost_kwh']:.0f} kWh, Viol={res_b0['violation_rate']*100:.2f}%, Res={res_b0['reserve_kwh']:.0f} kWh, Short={res_b0['shortage_kwh']:.0f} kWh", flush=True)
            row_b0 = {
                "condition": cond_name, "horizon_step": h_step, "horizon_min": h_min,
                "model_id": "B0_Global_Quantile", "model_name": "Global Empirical Quantile",
                **res_b0
            }
            all_rows.append(row_b0)

            # B1: State-Free Empirical Conditional Wind-Speed Binned Quantile
            w_v_flat = Wspd_val.reshape(T_v * N_turb)
            w_t_flat = Wspd_test.reshape(T_t * N_turb)
            bins = np.quantile(w_v_flat[m_v_flat], np.linspace(0, 1, N_BINS + 1))
            bins[0] = -np.inf
            bins[-1] = np.inf
            bin_q = []
            for b_i in range(N_BINS):
                in_b = m_v_flat & (w_v_flat >= bins[b_i]) & (w_v_flat < bins[b_i + 1])
                if np.sum(in_b) > 10:
                    bin_q.append(float(np.quantile(s_v_flat[in_b], Q_STAR)))
                else:
                    bin_q.append(q_global)
            r_b1 = np.zeros_like(s_t_flat)
            for b_i in range(N_BINS):
                in_t_b = (w_t_flat >= bins[b_i]) & (w_t_flat < bins[b_i + 1])
                r_b1[in_t_b] = bin_q[b_i]
            res_b1 = compute_metrics(r_b1, s_t_flat, m_t_flat)
            print(f"B1 Wspd-Bin: Cost={res_b1['psrei_cost_kwh']:.0f} kWh, Viol={res_b1['violation_rate']*100:.2f}%, Res={res_b1['reserve_kwh']:.0f} kWh, Short={res_b1['shortage_kwh']:.0f} kWh", flush=True)
            row_b1 = {
                "condition": cond_name, "horizon_step": h_step, "horizon_min": h_min,
                "model_id": "B1_Conditional_Wspd_Bins", "model_name": "Wind-Speed Binned Empirical Quantile",
                **res_b1
            }
            all_rows.append(row_b1)

            # B2: Linear Quantile Regression on GPU
            lin_model = LinearQuantileRegressorGPU(in_dim=F_dim).to(device)
            lin_opt = optim.Adam(lin_model.parameters(), lr=1e-2, weight_decay=1e-4)
            train_X_t = torch.from_numpy(X_val_norm[m_v_flat]).to(device)
            train_s_t = torch.from_numpy(s_v_flat[m_v_flat]).float().to(device)
            lin_loader = DataLoader(TensorDataset(train_X_t, train_s_t), batch_size=1024, shuffle=True)

            lin_model.train()
            for ep in range(5):
                for bx, by in lin_loader:
                    lin_opt.zero_grad()
                    pred = lin_model(bx)
                    loss = pinball_loss_torch(pred, by, Q_STAR)
                    loss.backward()
                    lin_opt.step()

            lin_model.eval()
            with torch.no_grad():
                test_X_t = torch.from_numpy(X_test_norm).to(device)
                r_b2 = np.maximum(lin_model(test_X_t).cpu().numpy(), 0.0)
            res_b2 = compute_metrics(r_b2, s_t_flat, m_t_flat)
            print(f"B2 Linear Pinball: Cost={res_b2['psrei_cost_kwh']:.0f} kWh, Viol={res_b2['violation_rate']*100:.2f}%, Res={res_b2['reserve_kwh']:.0f} kWh, Short={res_b2['shortage_kwh']:.0f} kWh", flush=True)
            row_b2 = {
                "condition": cond_name, "horizon_step": h_step, "horizon_min": h_min,
                "model_id": "B2_Linear_Quantile_Reg", "model_name": "Linear Quantile Regression",
                **res_b2
            }
            all_rows.append(row_b2)

            # B3: Quantile GBDT (HistGradientBoostingRegressor)
            sub_gbdt = np.random.choice(np.where(m_v_flat)[0], size=min(40000, np.sum(m_v_flat)), replace=False)
            gbdt = HistGradientBoostingRegressor(
                loss="quantile",
                quantile=Q_STAR,
                max_iter=100,
                max_depth=6,
                min_samples_leaf=30,
                random_state=args.seed,
            )
            gbdt.fit(X_val_flat[sub_gbdt], s_v_flat[sub_gbdt])
            r_b3 = np.maximum(gbdt.predict(X_test_flat), 0.0)
            res_b3 = compute_metrics(r_b3, s_t_flat, m_t_flat)
            print(f"B3 Quantile GBDT: Cost={res_b3['psrei_cost_kwh']:.0f} kWh, Viol={res_b3['violation_rate']*100:.2f}%, Res={res_b3['reserve_kwh']:.0f} kWh, Short={res_b3['shortage_kwh']:.0f} kWh", flush=True)
            row_b3 = {
                "condition": cond_name, "horizon_step": h_step, "horizon_min": h_min,
                "model_id": "B3_Quantile_GBDT", "model_name": "Quantile GBDT (HistGradientBoosting)",
                **res_b3
            }
            all_rows.append(row_b3)

            # B4: Small Capacity-Matched Direct MLP (Pinball Loss, NO state supervision)
            mlp = DirectMLP(in_dim=F_dim, hidden_dim=64).to(device)
            mlp_opt = optim.AdamW(mlp.parameters(), lr=1e-3, weight_decay=1e-4)
            mlp_loader = DataLoader(TensorDataset(train_X_t, train_s_t), batch_size=512, shuffle=True)

            mlp.train()
            for ep in range(5):
                for bx, by in mlp_loader:
                    mlp_opt.zero_grad()
                    p = mlp(bx)
                    loss = pinball_loss_torch(p, by, Q_STAR)
                    loss.backward()
                    mlp_opt.step()

            mlp.eval()
            with torch.no_grad():
                r_b4 = np.maximum(mlp(test_X_t).cpu().numpy(), 0.0)
            res_b4 = compute_metrics(r_b4, s_t_flat, m_t_flat)
            print(f"B4 Direct MLP: Cost={res_b4['psrei_cost_kwh']:.0f} kWh, Viol={res_b4['violation_rate']*100:.2f}%, Res={res_b4['reserve_kwh']:.0f} kWh, Short={res_b4['shortage_kwh']:.0f} kWh", flush=True)
            row_b4 = {
                "condition": cond_name, "horizon_step": h_step, "horizon_min": h_min,
                "model_id": "B4_Direct_MLP", "model_name": "Capacity-Matched Direct MLP",
                **res_b4
            }
            all_rows.append(row_b4)

            # Incremental save
            pd.DataFrame(all_rows).to_csv(out_path, index=False)

    print(f"\n[Completed] All direct baselines recorded to {out_path} ({len(all_rows)} total rows)", flush=True)


if __name__ == "__main__":
    main()
