"""Consequence-Signal Mechanism and Identifiability Ablation (Phase 7).

Evaluates the identifiability and decision value of secondary SCADA consequence channels
when blade pitch telemetry is completely withheld:

Conditions:
- C1: Full Consequence Suite (Patv, Prtv, Etmp, Itmp, Wdir, Ndir, wake)
- C2: Active Power Only (Patv_hist)
- C3: Electrical/Reactive Only (Prtv)
- C4: Thermal Only (Etmp, Itmp)
- C5: Direction/Yaw Only (Wdir, Ndir)
- C6: Wake Context Only (wake_score)
- C7: Active Power + Thermal (Patv_hist + Etmp + Itmp)
- C8: Active Power + Direction (Patv_hist + Wdir + Ndir)
- C9: Active Power + Wake Context (Patv_hist + wake_score)
- C10: Noise-Corrupted Consequence Suite (Gaussian noise sigma=1.0 / 2.0)

Metrics:
- Operating-State Brier Score
- Normalized Mutual Information (NMI)
- Adjusted Rand Index (ARI)
- Transition Window Recovery Recall (within +-3 steps of regime entry/exit)
- Total Reserve Cost (kWh) & Delta PSREI vs Direct Baseline (at h=1 and h=6)
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
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from windfarm_moe.data import CacheBundle, RegimeWindowDataset, load_cache_bundle

DT = 1.0 / 6.0
RHO = 10.0
Q_STAR = 1.0 - 1.0 / RHO  # 0.90
N_BINS = 5

ALL_CHANNELS = {
    "C1_Full_Suite": ["Patv_hist", "Prtv", "Etmp", "Itmp", "Wdir_sin", "Wdir_cos", "Ndir_sin", "Ndir_cos", "wake_score"],
    "C2_Active_Power_Only": ["Patv_hist"],
    "C3_Electrical_Reactive_Only": ["Prtv"],
    "C4_Thermal_Only": ["Etmp", "Itmp"],
    "C5_Direction_Yaw_Only": ["Wdir_sin", "Wdir_cos", "Ndir_sin", "Ndir_cos"],
    "C6_Wake_Context_Only": ["wake_score"],
    "C7_Active_Power_Thermal": ["Patv_hist", "Etmp", "Itmp"],
    "C8_Active_Power_Direction": ["Patv_hist", "Wdir_sin", "Wdir_cos", "Ndir_sin", "Ndir_cos"],
    "C9_Active_Power_Wake": ["Patv_hist", "wake_score"],
    "C10_Noise_Corrupted_Full": ["Patv_hist", "Prtv", "Etmp", "Itmp", "Wdir_sin", "Wdir_cos", "Ndir_sin", "Ndir_cos", "wake_score"],
}


class ConsequenceMLP(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int = 64, dropout: float = 0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 2),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def extract_channel_features(bundle: CacheBundle, split: str, channels: List[str], noise_sigma: float = 0.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Extract summary features (mean, std, max, latest) for specified consequence channels."""
    ds = RegimeWindowDataset(bundle, split, int(bundle.metadata["hist_len"]), int(bundle.metadata["pred_len"]))
    anchors = ds.anchor_indices
    feat_names = list(bundle.metadata.get("feature_names", []))
    features = np.asarray(bundle.features, dtype=np.float32)
    physics = np.asarray(bundle.physics_model, dtype=np.float32)
    regime = np.asarray(bundle.regime_primary, dtype=np.int64)
    valid = np.asarray(bundle.regime_primary_valid, dtype=bool)

    H = int(bundle.metadata["hist_len"])
    W = len(anchors)
    N = features.shape[1]

    # Gather feature windows
    idx = anchors[:, None] - np.arange(H)[None, ::-1]  # (W, H)
    wins_feat = features[idx]                          # (W, H, N, F_feat)
    wins_phy = physics[idx]                            # (W, H, N, F_phy)

    cols = []
    for ch in channels:
        if ch == "wake_score":
            # wake_score is index 2 in physics
            ch_data = wins_phy[..., 2:3]
        elif ch in feat_names:
            ch_idx = feat_names.index(ch)
            ch_data = wins_feat[..., ch_idx : ch_idx + 1]
        else:
            continue

        if noise_sigma > 0.0:
            rng = np.random.default_rng(42)
            ch_data = ch_data + rng.normal(0.0, noise_sigma, size=ch_data.shape).astype(np.float32)

        # Compute summary stats: latest, mean, std, max
        latest = ch_data[:, -1, :, :]
        c_mean = np.mean(ch_data, axis=1)
        c_std = np.std(ch_data, axis=1)
        c_max = np.max(ch_data, axis=1)
        cols.extend([latest, c_mean, c_std, c_max])

    X = np.concatenate(cols, axis=-1)  # (W, N, D)
    y = (regime[anchors] == 2).astype(np.int64)  # (W, N)
    m = valid[anchors]
    return X, y, m


def compute_transition_recall(y_true: np.ndarray, y_pred_binary: np.ndarray, window_radius: int = 3) -> float:
    """Compute recovery recall within +-3 time steps of operating boundary transitions."""
    W, N = y_true.shape
    # Detect transitions along time axis
    diff = np.diff(y_true, axis=0, prepend=y_true[:1, :]) != 0  # (W, N)
    
    # Expand transition windows +- window_radius (bounded non-circular dilation)
    in_window = diff.copy()
    for offset in range(1, window_radius + 1):
        in_window[offset:, :] |= diff[:-offset, :]
        in_window[:-offset, :] |= diff[offset:, :]

    # Target points: true pitch points inside transition windows
    target_mask = in_window & (y_true == 1)
    if np.sum(target_mask) == 0:
        return 0.0
    return float(np.mean(y_pred_binary[target_mask]))


def main():
    parser = argparse.ArgumentParser(description="Consequence-Signal Mechanism Ablation (Phase 7)")
    parser.add_argument("--cache-dir", default="artifacts/cache_strictmask_trainweights/wtb_245d")
    parser.add_argument("--residuals-file", default="artifacts/fixed_forecast_residuals.npz")
    parser.add_argument("--output-csv", default="artifacts/channel_consequence_ablations.csv")
    parser.add_argument("--device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--seeds", default="201,202,203,204,205")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=1024)
    args = parser.parse_args()

    device = torch.device(args.device)
    print(f"[Consequence Ablation] Loading cache from {args.cache_dir}", flush=True)
    bundle = load_cache_bundle(Path(args.cache_dir), mmap_mode="r")

    print(f"[Consequence Ablation] Loading fixed residuals from {args.residuals_file}", flush=True)
    res_data = np.load(args.residuals_file)
    seeds = [int(s.strip()) for s in args.seeds.split(",")]

    out_csv = Path(args.output_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    results = []

    # Direct baseline reference cost from Phase 4/5 (Pitch Withheld)
    direct_ref_h1 = 8009040.0   # 8.01M kWh at h=1
    direct_ref_h6 = 16469328.0  # 16.47M kWh at h=6

    for c_id, channels in ALL_CHANNELS.items():
        print(f"\n==================== CHANNEL GROUP: {c_id} ====================", flush=True)
        noise_sigma = 2.0 if c_id == "C10_Noise_Corrupted_Full" else 0.0

        # Extract features
        X_tr, y_tr, m_tr = extract_channel_features(bundle, "train", channels, noise_sigma=noise_sigma)
        X_va, y_va, m_va = extract_channel_features(bundle, "val", channels, noise_sigma=noise_sigma)
        X_te, y_te, m_te = extract_channel_features(bundle, "test", channels, noise_sigma=noise_sigma)

        in_dim = X_tr.shape[-1]
        print(f"Features: {channels} -> Feature Dimension: {in_dim}", flush=True)

        # Standardize features
        scaler = StandardScaler()
        X_tr_s = scaler.fit_transform(X_tr.reshape(-1, in_dim)).reshape(X_tr.shape)
        X_va_s = scaler.transform(X_va.reshape(-1, in_dim)).reshape(X_va.shape)
        X_te_s = scaler.transform(X_te.reshape(-1, in_dim)).reshape(X_te.shape)

        # Prepare PyTorch datasets
        tr_mask_flat = m_tr.reshape(-1)
        va_mask_flat = m_va.reshape(-1)
        te_mask_flat = m_te.reshape(-1)

        tx_tr = torch.from_numpy(X_tr_s.reshape(-1, in_dim)[tr_mask_flat]).float()
        ty_tr = torch.from_numpy(y_tr.reshape(-1)[tr_mask_flat]).long()

        tx_va = torch.from_numpy(X_va_s.reshape(-1, in_dim)).float()
        tx_te = torch.from_numpy(X_te_s.reshape(-1, in_dim)).float()

        # Metrics accumulators
        brier_list, nmi_list, ari_list, trans_recall_list = [], [], [], []
        cost_h1_list, cost_h6_list, viol_h1_list, viol_h6_list = [], [], [], []

        for seed in seeds:
            torch.manual_seed(seed)
            np.random.seed(seed)

            mlp = ConsequenceMLP(in_dim=in_dim, hidden_dim=64, dropout=0.1).to(device)
            optimizer = optim.AdamW(mlp.parameters(), lr=1e-3, weight_decay=1e-4)
            criterion = nn.CrossEntropyLoss()

            train_ds = TensorDataset(tx_tr, ty_tr)
            loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)

            mlp.train()
            for _ in range(args.epochs):
                for bx, by in loader:
                    bx, by = bx.to(device), by.to(device)
                    out = mlp(bx)
                    loss = criterion(out, by)
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()

            # Predict probabilities
            mlp.eval()
            with torch.no_grad():
                p_va = []
                for i in range(0, len(tx_va), 4096):
                    out = mlp(tx_va[i : i + 4096].to(device))
                    p_va.append(torch.softmax(out, dim=-1)[:, 1].cpu().numpy())
                p_va = np.concatenate(p_va, axis=0).reshape(y_va.shape)

                p_te = []
                for i in range(0, len(tx_te), 4096):
                    out = mlp(tx_te[i : i + 4096].to(device))
                    p_te.append(torch.softmax(out, dim=-1)[:, 1].cpu().numpy())
                p_te = np.concatenate(p_te, axis=0).reshape(y_te.shape)

            # 1. State Identifiability Metrics
            p_te_flat = p_te.reshape(-1)
            y_te_flat = y_te.reshape(-1)
            pred_binary = (p_te >= 0.50).astype(np.int64)

            brier = float(np.mean((p_te_flat[te_mask_flat] - y_te_flat[te_mask_flat]) ** 2))
            nmi = float(normalized_mutual_info_score(y_te_flat[te_mask_flat], (p_te_flat[te_mask_flat] >= 0.5).astype(int)))
            ari = float(adjusted_rand_score(y_te_flat[te_mask_flat], (p_te_flat[te_mask_flat] >= 0.5).astype(int)))
            t_recall = compute_transition_recall(y_te, pred_binary)

            brier_list.append(brier)
            nmi_list.append(nmi)
            ari_list.append(ari)
            trans_recall_list.append(t_recall)

            # 2. Decision Value Metrics (at h=1 and h=6)
            for h_idx, (h_step, cost_acc, viol_acc) in enumerate([(0, cost_h1_list, viol_h1_list), (5, cost_h6_list, viol_h6_list)]):
                m_val = res_data["mask_val"][:, h_idx, :].reshape(-1) > 0.5
                m_test = res_data["mask_test"][:, h_idx, :].reshape(-1) > 0.5
                s_v = res_data[f"shortfall_val_seed{seed}"][:, h_idx, :].reshape(-1)
                s_t = res_data[f"shortfall_test_seed{seed}"][:, h_idx, :].reshape(-1)

                p_v_flat = p_va.reshape(-1)
                p_t_flat = p_te.reshape(-1)

                # 5-bin calibration
                pi_bins = np.quantile(p_v_flat[m_val], np.linspace(0, 1, N_BINS + 1))
                pi_bins[0] = -np.inf
                pi_bins[-1] = np.inf
                q_glob = float(np.quantile(s_v[m_val], Q_STAR))
                c_bin_q = []
                for b_i in range(N_BINS):
                    in_b = m_val & (p_v_flat >= pi_bins[b_i]) & (p_v_flat < pi_bins[b_i + 1])
                    if np.sum(in_b) > 20:
                        c_bin_q.append(float(np.quantile(s_v[in_b], Q_STAR)))
                    else:
                        c_bin_q.append(q_glob)
                r_c = np.zeros_like(s_t)
                for b_i in range(N_BINS):
                    in_t = (p_t_flat >= pi_bins[b_i]) & (p_t_flat < pi_bins[b_i + 1])
                    r_c[in_t] = c_bin_q[b_i]

                # Compute reserve cost
                r = r_c[m_test]
                s = s_t[m_test]
                shortage = np.maximum(s - r, 0.0)
                cost = float(np.sum(r + RHO * shortage) * DT)
                viol = float(np.mean(s > r) * 100.0)

                cost_acc.append(cost)
                viol_acc.append(viol)

        # Cross-seed averages
        mean_brier = float(np.mean(brier_list))
        mean_nmi = float(np.mean(nmi_list))
        mean_ari = float(np.mean(ari_list))
        mean_trecall = float(np.mean(trans_recall_list))
        mean_cost_h1 = float(np.mean(cost_h1_list))
        mean_cost_h6 = float(np.mean(cost_h6_list))
        delta_h1 = float(direct_ref_h1 - mean_cost_h1)
        delta_h6 = float(direct_ref_h6 - mean_cost_h6)

        row = {
            "channel_group": c_id,
            "feature_dim": in_dim,
            "channels": ";".join(channels),
            "brier_score_mean": mean_brier,
            "brier_score_std": float(np.std(brier_list)),
            "nmi_mean": mean_nmi,
            "nmi_std": float(np.std(nmi_list)),
            "ari_mean": mean_ari,
            "ari_std": float(np.std(ari_list)),
            "transition_recall_mean": mean_trecall,
            "transition_recall_std": float(np.std(trans_recall_list)),
            "cost_h1_kwh_mean": mean_cost_h1,
            "cost_h1_kwh_std": float(np.std(cost_h1_list)),
            "viol_h1_pct_mean": float(np.mean(viol_h1_list)),
            "delta_vs_direct_h1_kwh": delta_h1,
            "cost_h6_kwh_mean": mean_cost_h6,
            "cost_h6_kwh_std": float(np.std(cost_h6_list)),
            "viol_h6_pct_mean": float(np.mean(viol_h6_list)),
            "delta_vs_direct_h6_kwh": delta_h6,
        }
        results.append(row)
        print(f"[{c_id:<28}] Brier: {mean_brier:.4f} | NMI: {mean_nmi:.3f} | Trans Recall: {mean_trecall*100:.1f}% | Δh1: {delta_h1:+,.0f} kWh | Δh6: {delta_h6:+,.0f} kWh", flush=True)

        pd.DataFrame(results).to_csv(out_csv, index=False)

    print(f"\n[Saved] Channel consequence ablations summary to {out_csv} ({len(results)} rows)", flush=True)


if __name__ == "__main__":
    main()
