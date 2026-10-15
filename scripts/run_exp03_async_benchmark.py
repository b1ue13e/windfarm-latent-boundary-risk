"""EXP-03 (Integer-Step Asynchronous Packet Arrival Envelope Benchmark)

Scientific Question:
    Under an explicit out-of-order telemetry protocol with integer dispatch steps,
    how does causal packet arrival and missingness alter downstream reserve screening
    PSREI relative to delay, and does the challenger remain comparable or superior
    to Site-Local Wspd-Bins under identical arrival trace and missing mask contamination?

Preregistered Protocol & Hard Gates:
    1. Integer-step packet simulator: Time is discrete dispatch steps (DT=1/6 h, 10 min).
       Each packet explicitly records (event_time, arrival_time, channel_id, sequence_id).
    2. Causal buffer policy: At dispatch step t, models can only read packets with
       arrival_time <= t. Same-arrival packets are deterministically ordered by
       (arrival_time, sequence_id, channel_id).
    3. Late packets beyond finite max_lateness are dropped and marked missing.
       Future backfill is strictly forbidden (allow_future_backfill=False).
    4. Exact information parity: Both Site-Local Wspd-Bins and Challenger observe
       the identical arrival trace, identical causal features, and identical missing mask.
    5. Primary Estimand: Paired PSREI-vs-delay curve Delta PSREI(tau) across delay grid
       tau in {0, 1, 2, 3, 4, 5, 6} integer steps, and critical threshold tau*.
    6. Operating Target Sensitivity: 10% is the preregistered nominal operating target
       (corresponding to q*=1-1/rho=0.90 at rho=10.0), with sensitivity evaluated
       at 5%, 10%, and 15% violation rates.
    7. Synthetic Asynchronous Envelope: Outputs are strictly synthetic boundary probes,
       never extrapolated to industrial telemetry prevalence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.exp03_async_packet_protocol import BufferPolicy, CausalPacketBuffer, Packet
from scripts.hierarchical_bootstrap import compute_hierarchical_joint_bootstrap

# Preregistered Execution Constants
RHO = 10.0
TAU_QUANTILE = 1.0 - 1.0 / RHO  # 0.90
DT = 1.0 / 6.0                  # 10 min = 1/6 h
N_WSPD_BINS = 10
N_BOOTSTRAP = 2000
BLOCK_SIZE = 144                # 144 steps = 1 day
SEEDS = [201, 202, 203, 204, 205]
HORIZONS = [(0, "h=1"), (5, "h=6")]
DELAY_GRID = [0, 1, 2, 3, 4, 5, 6]  # 0 to 60 min delay in 10-min integer steps
V_RATED = 10.5
P_RATED = 1500.0
EPSILON = 50.0                  # kW


def unstandardize_feature(values: np.ndarray, feature_name: str, feature_stats: Dict[str, Any]) -> np.ndarray:
    """Convert a cached standardized feature back to its physical units."""
    if feature_name not in feature_stats:
        raise KeyError(f"Missing feature statistics for physical threshold: {feature_name}")
    stats = feature_stats[feature_name]
    mean = float(stats["mean"])
    std = float(stats["std"])
    if not np.isfinite(std) or std <= 0.0:
        raise ValueError(f"Invalid standard deviation for {feature_name}: {std}")
    return np.asarray(values, dtype=np.float64) * std + mean


def build_proxy_labels(
    wspd_standardized: np.ndarray,
    patv_standardized: np.ndarray,
    feature_stats: Dict[str, Any],
    epsilon: float = EPSILON,
) -> np.ndarray:
    """Build the weak proxy label from physical wind speed and active power."""
    wspd_physical = unstandardize_feature(wspd_standardized, "Wspd", feature_stats)
    patv_physical = unstandardize_feature(patv_standardized, "Patv_hist", feature_stats)
    return ((wspd_physical > V_RATED) & (patv_physical < P_RATED - epsilon)).astype(np.int64)


# ------------------------------------------------------------------------------
# Challenger Neural Network
# ------------------------------------------------------------------------------
class ZeroPrivilegedRepresentationNet(nn.Module):
    def __init__(self, in_features: int = 7, hidden_dim: int = 64):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Linear(in_features, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.05),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
        )
        self.quantile_head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.GELU(),
            nn.Linear(32, 1),
            nn.ReLU(),
        )
        self.proxy_head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.GELU(),
            nn.Linear(32, 2),
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        feat = self.backbone(x)
        r = self.quantile_head(feat).squeeze(-1)
        proxy_logits = self.proxy_head(feat)
        return r, proxy_logits


# ------------------------------------------------------------------------------
# Asynchronous Packet Simulator
# ------------------------------------------------------------------------------
def generate_integer_step_delays(
    n_steps: int,
    mean_delay: int,
    max_lateness: int,
    seed: int,
) -> np.ndarray:
    """Generate discrete integer delays with bounded lateness and out-of-order jitter."""
    if mean_delay == 0:
        return np.zeros(n_steps, dtype=np.int64)
    rng = np.random.default_rng(seed)
    # Poisson-distributed integer arrivals with delay jitter
    base_delays = rng.poisson(lam=mean_delay, size=n_steps)
    # Add random out-of-order burst jitter for ~15% of packets
    burst_mask = rng.random(size=n_steps) < 0.15
    base_delays[burst_mask] += rng.integers(1, 4, size=int(np.sum(burst_mask)))
    return np.asarray(base_delays, dtype=np.int64)


def simulate_asynchronous_scada_stream(
    raw_features: np.ndarray,          # (T, N, F)
    feature_names: Sequence[str],
    mean_delay: int,
    max_lateness: int = 4,
    seed: int = 20261012,
    archive_path: Path | None = None,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any], List[Packet]]:
    """Replay SCADA channel telemetry through causal packet buffer with transparent LOCF.

    Resolves Issue 2, 3, 4:
    - Guarantees strict identical arrival information set across ALL consumed channels
      (including active power 'Patv_hist').
    - Implements transparent causal Last Observation Carried Forward (LOCF) for late/dropped packets
      so that the evaluated test population remains strictly FIXED (100% cells, no collapse).
    - Returns verified channel-level dropout and staleness masks for complete provenance.
    """
    T, N, F = raw_features.shape

    # Consistently resolve all 5 SCADA feature channels consumed by models
    channel_aliases = {
        "Wspd": ("Wspd",),
        "Patv_hist": ("Patv_hist", "Patv"),
        "Etmp": ("Etmp",),
        "Itmp": ("Itmp",),
        "Prtv": ("Prtv",),
    }
    resolved_channels = []
    ch_indices = []
    for canonical, aliases in channel_aliases.items():
        found_alias = False
        for alias in aliases:
            if alias in feature_names:
                resolved_channels.append(alias)
                ch_indices.append(feature_names.index(alias))
                found_alias = True
                break
        if not found_alias:
            raise KeyError(f"Critical channel '{canonical}' not found in feature_names: {feature_names}")

    contaminated_features = raw_features.copy()
    dropped_mask = np.zeros((T, N, len(ch_indices)), dtype=bool)
    stale_mask = np.zeros((T, N, len(ch_indices)), dtype=bool)
    selected_source = np.full((T, N, len(ch_indices)), -1, dtype=np.int32)
    sample_packets: List[Packet] = []

    rng = np.random.default_rng(seed)
    delays = np.zeros((T, N, len(ch_indices)), dtype=np.int64)
    if mean_delay > 0:
        base = rng.poisson(lam=mean_delay, size=(T, N, len(ch_indices)))
        burst = rng.random(size=(T, N, len(ch_indices))) < 0.15
        base[burst] += rng.integers(1, 4, size=int(np.sum(burst)), dtype=np.int64)
        delays = base

    # Comprehensive packet provenance for node 0 and node 1 across channels
    for c_idx, ch in enumerate(ch_indices):
        for t in range(min(T, 144)):
            for node_sample in [0, min(1, N - 1)]:
                d = int(delays[t, node_sample, c_idx])
                sample_packets.append(Packet(
                    event_time=t,
                    arrival_time=t + d,
                    channel_id=feature_names[ch],
                    sequence_id=t,
                    value=float(raw_features[t, node_sample, ch]),
                ))

    # Causal unexpired-packet selection with causal LOCF (Last Observation Carried Forward):
    # At step t, valid candidate events s must satisfy s in [max(0, t - max_lateness), t] and arr[s] <= t.
    # If no new packet arrived or all were dropped due to lateness > max_lateness:
    # We maintain the previous causal observation (LOCF) rather than dropping the evaluated cell!
    for c_idx, ch in enumerate(ch_indices):
        d_ch = delays[:, :, c_idx]
        v_ch = raw_features[:, :, ch]
        arr_ch = np.arange(T)[:, None] + d_ch

        for n in range(N):
            # Predetermined standardized mean until a packet actually arrives.
            last_causal_val = 0.0
            last_source = -1
            for t in range(T):
                s_min = max(0, t - max_lateness)
                found = False
                matched_s = -1
                for s in range(t, s_min - 1, -1):
                    if arr_ch[s, n] <= t:
                        last_causal_val = float(v_ch[s, n])
                        last_source = s
                        found = True
                        matched_s = s
                        break
                contaminated_features[t, n, ch] = last_causal_val
                selected_source[t, n, c_idx] = last_source
                if not found:
                    dropped_mask[t, n, c_idx] = True
                    stale_mask[t, n, c_idx] = True
                else:
                    stale_mask[t, n, c_idx] = (matched_s != t)

    trace_stats = {
        "protocol_version": "async-causal-init-full-trace-v2",
        "simulator_seed": seed,
        "max_lateness": max_lateness,
        "initial_value_standardized": 0.0,
        "mean_delay_steps": mean_delay,
        "mean_delay_minutes": mean_delay * 10,
        "channels_delayed": resolved_channels,
        "overall_drop_fraction": float(np.mean(dropped_mask)),
        "overall_stale_fraction": float(np.mean(stale_mask)),
        "per_channel_drop_fraction": {
            resolved_channels[i]: float(np.mean(dropped_mask[..., i])) for i in range(len(resolved_channels))
        },
    }
    if archive_path is not None:
        archive_path = Path(archive_path)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        if archive_path.exists():
            raise FileExistsError(f'Refusing to overwrite packet archive: {archive_path}')
        np.savez_compressed(archive_path, raw_features=raw_features,
                            channel_indices=np.asarray(ch_indices), delays=delays,
                            selected_source=selected_source, dropped_mask=dropped_mask,
                            stale_mask=stale_mask, contaminated_features=contaminated_features,
                            feature_names=np.asarray(feature_names),
                            metadata_json=np.asarray(json.dumps(trace_stats)))
        trace_stats['archive_sha256'] = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        trace_stats['archive_path'] = str(archive_path)

    return contaminated_features, dropped_mask, trace_stats, sample_packets


# ------------------------------------------------------------------------------
# Wspd-Bins Baseline
# ------------------------------------------------------------------------------
def fit_wspd_bins(wspd_val: np.ndarray, s_val: np.ndarray, mask_val: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    valid = mask_val & np.isfinite(wspd_val) & np.isfinite(s_val)
    w_valid = wspd_val[valid]
    s_valid = s_val[valid]

    quantiles = np.linspace(0.0, 1.0, N_WSPD_BINS + 1)[1:-1]
    edges = np.quantile(w_valid, quantiles)
    edges = np.unique(edges)
    if len(edges) < 2:
        edges = np.linspace(w_valid.min(), w_valid.max(), N_WSPD_BINS + 1)[1:-1]

    bin_assignments = np.digitize(w_valid, edges)
    unique_bins = np.arange(len(edges) + 1)
    reserves_per_bin = np.zeros(len(unique_bins), dtype=np.float64)
    global_reserve = float(np.quantile(s_valid, TAU_QUANTILE)) if len(s_valid) > 0 else 50.0

    for b in unique_bins:
        sb = s_valid[bin_assignments == b]
        if len(sb) >= 30:
            reserves_per_bin[b] = float(np.quantile(sb, TAU_QUANTILE))
        else:
            reserves_per_bin[b] = global_reserve

    return edges, reserves_per_bin


def apply_wspd_bins(wspd_test: np.ndarray, edges: np.ndarray, reserves_per_bin: np.ndarray) -> np.ndarray:
    bin_assignments = np.digitize(wspd_test, edges)
    bin_assignments = np.clip(bin_assignments, 0, len(reserves_per_bin) - 1)
    return reserves_per_bin[bin_assignments]


# ------------------------------------------------------------------------------
# Decision Metrics & Paired Block Bootstrap
# ------------------------------------------------------------------------------
def compute_psrei_metrics(s: np.ndarray, r: np.ndarray, mask: np.ndarray) -> Dict[str, float]:
    valid = mask & np.isfinite(s) & np.isfinite(r)
    s_v = s[valid]
    r_v = r[valid]
    procurement = float(np.sum(r_v) * DT)
    shortage = float(np.sum(np.maximum(s_v - r_v, 0.0)) * DT)
    total_cost = float((np.sum(r_v) + RHO * np.sum(np.maximum(s_v - r_v, 0.0))) * DT)
    viol_rate = float(np.mean(s_v > r_v) * 100.0) if len(s_v) > 0 else 0.0
    n_cells = int(np.sum(valid))
    per_cell_cost = total_cost / max(1, n_cells)
    return {
        "psrei_kwh": total_cost,
        "psrei_per_cell_kwh": per_cell_cost,
        "reserve_kwh": procurement,
        "shortage_kwh": shortage,
        "violation_rate_pct": viol_rate,
        "n_cells": n_cells,
    }


def paired_cluster_bootstrap(
    s: np.ndarray,
    r_challenger: np.ndarray,
    r_baseline: np.ndarray,
    mask: np.ndarray,
    n_boot: int = N_BOOTSTRAP,
    block_size: int = BLOCK_SIZE,
    seed: int = 42,
) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)
    T, N = s.shape
    n_blocks = max(1, int(np.ceil(T / block_size)))
    time_indices = np.arange(T)
    sample_block_ids = time_indices // block_size

    valid = mask & np.isfinite(s)
    sh_c = np.maximum(s - r_challenger, 0.0)
    sh_b = np.maximum(s - r_baseline, 0.0)

    cost_c = (r_challenger + RHO * sh_c) * DT
    cost_b = (r_baseline + RHO * sh_b) * DT

    c_valid_c = np.where(valid, cost_c, 0.0).sum(axis=-1)
    c_valid_b = np.where(valid, cost_b, 0.0).sum(axis=-1)

    block_costs_c = np.bincount(sample_block_ids, weights=c_valid_c, minlength=n_blocks)[:n_blocks]
    block_costs_b = np.bincount(sample_block_ids, weights=c_valid_b, minlength=n_blocks)[:n_blocks]

    chosen_blocks = rng.integers(0, n_blocks, size=(n_boot, n_blocks))
    boot_c = block_costs_c[chosen_blocks].sum(axis=1)
    boot_b = block_costs_b[chosen_blocks].sum(axis=1)

    delta_c = boot_c - boot_b
    delta_mean = float(np.mean(delta_c))
    delta_ci = [float(np.quantile(delta_c, 0.025)), float(np.quantile(delta_c, 0.975))]
    p_val = float(np.mean(delta_c <= 0.0))  # empirical probability challenger non-inferior

    return {
        "delta_psrei_mean": delta_mean,
        "delta_psrei_ci_95": delta_ci,
        "p_val": p_val,
        "challenger_psrei_mean": float(np.mean(boot_c)),
        "baseline_psrei_mean": float(np.mean(boot_b)),
        "block_delta_cost": block_costs_c - block_costs_b,
    }


# ------------------------------------------------------------------------------
# Main Benchmark Runner
# ------------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="EXP-03 Asynchronous Envelope Benchmark")
    parser.add_argument("--cache-dir", type=Path, default=REPO_ROOT / "artifacts/cache_strictmask_trainweights/wtb_245d")
    parser.add_argument("--residuals-file", type=Path, default=REPO_ROOT / "artifacts/fixed_forecast_residuals.npz")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "artifacts/exp03_async_replay_v2")
    parser.add_argument("--output-report", type=Path, default=REPO_ROOT / "artifacts/exp03_async_replay_v2/report.md")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--smoke", action="store_true", help="Quick smoke test mode")
    args = parser.parse_args()

    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)

    print("==================================================================")
    print("EXP-03: INTEGER-STEP ASYNCHRONOUS TELEMETRY BENCHMARK")
    print(f"Device: {device} | Smoke mode: {args.smoke}")
    print("==================================================================")

    # 1. Load WTB metadata & features
    with open(args.cache_dir / "metadata.json", "r", encoding="utf-8") as f:
        meta = json.load(f)
    feature_names = meta["feature_names"]
    wspd_idx = feature_names.index("Wspd")
    patv_idx = feature_names.index("Patv_hist") if "Patv_hist" in feature_names else feature_names.index("Patv")
    etmp_idx = feature_names.index("Etmp")
    itmp_idx = feature_names.index("Itmp")
    prtv_idx = feature_names.index("Prtv")

    raw_features = np.load(args.cache_dir / "features.npy", mmap_mode="r")
    split_bounds = meta["split_bounds"]
    val_slice = slice(split_bounds["val"][0], split_bounds["val"][1])
    test_slice = slice(split_bounds["test"][0], split_bounds["test"][1])

    # 2. Load frozen residuals
    res_data = np.load(args.residuals_file)
    anchors_val = res_data["anchor_indices_val"]
    anchors_test = res_data["anchor_indices_test"]
    mask_test_all = res_data["mask_test"]

    delays_to_eval = [0, 2, 4] if args.smoke else DELAY_GRID
    seeds_to_eval = [201] if args.smoke else SEEDS
    horizons_to_eval = [(5, "h=6")] if args.smoke else HORIZONS

    all_results: List[Dict[str, Any]] = []
    saved_packets: List[Packet] = []

    # 3. Offline Phase: Pre-train & Calibrate Models on Validation Set (Clean History)
    print("\n--- PHASE 1: OFFLINE CALIBRATION ON VALIDATION SPLIT ---")
    rel_anchors_val = anchors_val - split_bounds["val"][0]
    val_feat_block = np.asarray(raw_features[val_slice])
    val_inputs = val_feat_block[rel_anchors_val]
    wspd_val_raw = val_inputs[..., wspd_idx]

    def make_input_tensor(feat_arr: np.ndarray) -> np.ndarray:
        w = feat_arr[..., wspd_idx]
        p = feat_arr[..., patv_idx]
        e = feat_arr[..., etmp_idx]
        i = feat_arr[..., itmp_idx]
        pr = feat_arr[..., prtv_idx]
        w2 = (w ** 2) / 100.0
        pratio = np.clip(p / (P_RATED + 1e-5), 0.0, 1.5)
        return np.stack([w, p, e, i, pr, w2, pratio], axis=-1)

    val_x_7 = make_input_tensor(val_inputs)
    feature_stats = meta.get("feature_stats", {})

    # Physical thresholds must be applied after undoing cache standardization.
    # Keep the proxy target separate from the standardized model input tensor.
    proxy_labels_val = build_proxy_labels(
        val_inputs[..., wspd_idx], val_inputs[..., patv_idx], feature_stats, EPSILON
    )
    proxy_positive_count = int(np.sum(proxy_labels_val))
    proxy_total_count = int(proxy_labels_val.size)
    if proxy_positive_count == 0 or proxy_positive_count == proxy_total_count:
        raise ValueError(
            "EXP-03 proxy labels are degenerate after physical-unit conversion: "
            f"{proxy_positive_count}/{proxy_total_count} positives"
        )
    print(
        f"  Proxy validation positives: {proxy_positive_count}/{proxy_total_count} "
        f"({100.0 * proxy_positive_count / proxy_total_count:.3f}%)"
    )

    # Dictionary to store pre-calibrated models and baselines
    calibrated_models: Dict[Tuple[int, int], Tuple[Tuple[np.ndarray, np.ndarray], ZeroPrivilegedRepresentationNet]] = {}

    for seed in seeds_to_eval:
        s_val = res_data[f"shortfall_val_seed{seed}"]
        m_val = res_data["mask_val"]

        for h_idx, h_name in horizons_to_eval:
            torch.manual_seed(seed)
            np.random.seed(seed)
            s_val_h = s_val[:, h_idx, :]
            mask_val_h = m_val[:, h_idx, :] > 0.5

            # 1. Fit Site-Local Wspd-Bins
            edges, bin_reserves = fit_wspd_bins(wspd_val_raw, s_val_h, mask_val_h)

            # 2. Train Challenger Model
            valid_val = mask_val_h & np.isfinite(s_val_h)
            x_train_flat = torch.from_numpy(val_x_7[valid_val]).float().to(device)
            s_train_flat = torch.from_numpy(s_val_h[valid_val]).float().to(device)

            z_proxy = proxy_labels_val[valid_val]
            z_train_flat = torch.from_numpy(z_proxy).long().to(device)

            challenger_model = ZeroPrivilegedRepresentationNet(in_features=7, hidden_dim=64).to(device)
            optimizer = torch.optim.AdamW(challenger_model.parameters(), lr=1e-3, weight_decay=1e-4)
            criterion_pinball = lambda p, t: torch.maximum(TAU_QUANTILE * (t - p), (TAU_QUANTILE - 1.0) * (t - p)).mean()
            criterion_ce = nn.CrossEntropyLoss()

            challenger_model.train()
            dataset = TensorDataset(x_train_flat, s_train_flat, z_train_flat)
            loader = DataLoader(dataset, batch_size=2048, shuffle=True)
            n_epochs = 3 if args.smoke else 8
            history = []
            for epoch in range(n_epochs):
                loss_sum, count = 0.0, 0
                for bx, bs, bz in loader:
                    optimizer.zero_grad()
                    pred_r, pred_proxy = challenger_model(bx)
                    loss = criterion_pinball(pred_r, bs) + 0.1 * criterion_ce(pred_proxy, bz)
                    loss.backward()
                    optimizer.step()
                    loss_sum += float(loss.item()) * len(bx)
                    count += len(bx)
                history.append({'epoch': epoch+1, 'loss': loss_sum/count})
            challenger_model.eval()
            model_dir = out_dir / 'models' / f'seed{seed}_h{h_idx+1}'
            model_dir.mkdir(parents=True, exist_ok=False)
            torch.save({'model_state': challenger_model.state_dict(), 'seed': seed,
                        'history': history, 'epochs': n_epochs,
                        'baseline_edges': edges, 'baseline_reserves': bin_reserves},
                       model_dir / 'model.pt')
            (model_dir / 'training_history.json').write_text(json.dumps(history, indent=2), encoding='utf-8')

            calibrated_models[(seed, h_idx)] = ((edges, bin_reserves), challenger_model)
            print(f"  [Calibrated] Seed {seed} | Horizon {h_name}")

    print("--- OFFLINE CALIBRATION COMPLETE ---\n")

    # 4. Online Phase: Asynchronous Telemetry Evaluation Across Delay Grid
    print("--- PHASE 2: ONLINE ASYNCHRONOUS DELAY GRID EVALUATION ---")
    rel_anchors_test = anchors_test - split_bounds["test"][0]
    test_feat_block = np.asarray(raw_features[test_slice])

    # Tracking structures for joint uncertainty and transparency
    block_deltas_tracker: Dict[Tuple[str, int], Dict[int, np.ndarray]] = {}
    missing_manifest_records: List[Dict[str, Any]] = []
    global_hasher = hashlib.sha256()

    for delay in delays_to_eval:
        print(f"\n>>> Evaluating Delay Level tau = {delay} ({delay * 10} min)...")
        t0 = time.time()

        async_feat, dropped_mask, trace_stats, packets = simulate_asynchronous_scada_stream(
            test_feat_block,
            feature_names,
            mean_delay=delay,
            max_lateness=4,
            seed=20261012 + delay * 100,
            archive_path=out_dir / 'packet_grid' / f'delay{delay}.npz',
        )
        if len(saved_packets) == 0:
            saved_packets = packets

        # Hash manifest of every full-grid archive; all model seeds share this trace.
        global_hasher.update(f"{delay}:{trace_stats['archive_sha256']}\n".encode('ascii'))

        missing_manifest_records.append({
            "delay_tau": delay,
            "delay_minutes": delay * 10,
            "trace_stats": trace_stats,
            "sample_first_48_steps_wspd_dropped": dropped_mask[:48, 0, 0].tolist(),
        })

        test_inputs = async_feat[rel_anchors_test]
        test_x_7 = make_input_tensor(test_inputs)
        test_x_flat = torch.from_numpy(test_x_7.reshape(-1, 7)).float().to(device)

        for seed in seeds_to_eval:
            s_test = res_data[f"shortfall_test_seed{seed}"]
            m_test = res_data["mask_test"]

            for h_idx, h_name in horizons_to_eval:
                s_test_h = s_test[:, h_idx, :]
                # Fixed population: strictly defined on valid dispatch anchors without sample collapse!
                mask_test_h = (m_test[:, h_idx, :] > 0.5)

                (edges, bin_reserves), challenger_model = calibrated_models[(seed, h_idx)]

                # Baseline inference
                wspd_test_async = test_inputs[..., wspd_idx]
                r_baseline = apply_wspd_bins(wspd_test_async, edges, bin_reserves)

                # Challenger inference
                with torch.no_grad():
                    pred_r_flat, _ = challenger_model(test_x_flat)
                    r_challenger = pred_r_flat.cpu().numpy().reshape(test_inputs.shape[0], test_inputs.shape[1])

                # Metrics & Bootstrap
                base_metrics = compute_psrei_metrics(s_test_h, r_baseline, mask_test_h)
                chal_metrics = compute_psrei_metrics(s_test_h, r_challenger, mask_test_h)
                boot_stat = paired_cluster_bootstrap(s_test_h, r_challenger, r_baseline, mask_test_h, seed=seed)

                # Track block deltas for hierarchical joint bootstrap
                if (h_name, delay) not in block_deltas_tracker:
                    block_deltas_tracker[(h_name, delay)] = {}
                block_deltas_tracker[(h_name, delay)][seed] = boot_stat["block_delta_cost"]
                pred_dir = out_dir / 'predictions'
                pred_dir.mkdir(exist_ok=True)
                np.savez_compressed(pred_dir / f'delay{delay}_seed{seed}_h{h_idx+1}.npz',
                                    reserve_challenger=r_challenger, reserve_baseline=r_baseline,
                                    shortfall=s_test_h, mask=mask_test_h, anchor_indices=anchors_test,
                                    block_delta_cost=boot_stat['block_delta_cost'])

                all_results.append({
                    "delay_tau": delay,
                    "delay_minutes": delay * 10,
                    "seed": seed,
                    "horizon": h_name,
                    "n_evaluated_cells": base_metrics["n_cells"],
                    "drop_fraction": trace_stats["overall_drop_fraction"],
                    "stale_fraction": trace_stats["overall_stale_fraction"],
                    "baseline_psrei": base_metrics["psrei_kwh"],
                    "baseline_psrei_per_cell": base_metrics["psrei_per_cell_kwh"],
                    "baseline_viol_pct": base_metrics["violation_rate_pct"],
                    "baseline_reserve_kwh": base_metrics["reserve_kwh"],
                    "baseline_shortage_kwh": base_metrics["shortage_kwh"],
                    "challenger_psrei": chal_metrics["psrei_kwh"],
                    "challenger_psrei_per_cell": chal_metrics["psrei_per_cell_kwh"],
                    "challenger_viol_pct": chal_metrics["violation_rate_pct"],
                    "challenger_reserve_kwh": chal_metrics["reserve_kwh"],
                    "challenger_shortage_kwh": chal_metrics["shortage_kwh"],
                    "delta_psrei_mean": boot_stat["delta_psrei_mean"],
                    "delta_psrei_ci_lower": boot_stat["delta_psrei_ci_95"][0],
                    "delta_psrei_ci_upper": boot_stat["delta_psrei_ci_95"][1],
                    "p_val": boot_stat["p_val"],
                })

        print(f"Delay tau = {delay} completed in {time.time() - t0:.1f}s.")

    # 4. Save results CSV
    df = pd.DataFrame(all_results)
    csv_path = out_dir / "psrei_vs_delay.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n[OK] Saved benchmark metrics to: {csv_path}")

    # 5. Save arrival trace sample & compute trace hash
    trace_path = out_dir / "arrival_trace.jsonl"
    with trace_path.open("w", encoding="utf-8") as f:
        for p in saved_packets:
            f.write(json.dumps(p.__dict__, sort_keys=True) + "\n")
    
    trace_digest = global_hasher.hexdigest()
    (out_dir / "input_trace_hash.txt").write_text(trace_digest + "\n", encoding="ascii")
    print(f"[OK] Full-grid archive hash manifest digest: {trace_digest}")

    # 6. Save Verified Missing Mask Manifest
    (out_dir / "missing_mask_manifest.json").write_text(
        json.dumps(missing_manifest_records, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "missing_mask.json").write_text(
        json.dumps({"schema": "full-grid-mask-locations-v2", "archives": [r["trace_stats"]["archive_path"] for r in missing_manifest_records]}, indent=2) + "\n", encoding="utf-8"
    )

    # 7. Protocol Summary JSON
    protocol = {
        "experiment": "EXP-03",
        "label": "synthetic asynchronous envelope",
        "population_condition": "fixed dispatch-anchor population (100% cells, no drop collapse)",
        "delays_evaluated_steps": delays_to_eval,
        "delays_evaluated_minutes": [d * 10 for d in delays_to_eval],
        "model_seeds": seeds_to_eval,
        "simulator_seeds_by_delay": {str(d): 20261012 + d * 100 for d in delays_to_eval},
        "trace_replication": "one realized trace per delay, shared by all model seeds",
        "tau_star_definition": "first delay whose joint CI upper bound >= 0 (loss of demonstrated advantage)",
        "horizons": [h[1] for h in horizons_to_eval],
        "operating_target_nominal": 10.0,
        "operating_target_sensitivities": [5.0, 10.0, 15.0],
        "primary_estimand": "paired PSREI-vs-delay curve Delta PSREI(tau) and hierarchical tau*",
        "trace_sha256": trace_digest,
    }
    (out_dir / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")

    # 8. Hierarchical Joint Uncertainty Analysis & tau* computation
    joint_delay_summary = []
    tau_star_hierarchical = {}

    for h_idx, h_name in horizons_to_eval:
        tau_star_h = None
        for delay in delays_to_eval:
            sub = df[(df["horizon"] == h_name) & (df["delay_tau"] == delay)]
            seed_deltas = block_deltas_tracker[(h_name, delay)]
            j_res = compute_hierarchical_joint_bootstrap(seed_deltas, n_boot=2000, two_stage_resample=True)

            mean_delta = float(sub["delta_psrei_mean"].mean())
            med_delta = float(sub["delta_psrei_mean"].median())
            viol_c = float(sub["challenger_viol_pct"].mean())
            viol_b = float(sub["baseline_viol_pct"].mean())
            n_cells_val = int(sub["n_evaluated_cells"].iloc[0])
            drop_f = float(sub["drop_fraction"].iloc[0])
            stale_f = float(sub["stale_fraction"].iloc[0]) if "stale_fraction" in sub else float("nan")

            j_low = j_res["joint_ci_95"][0]
            j_high = j_res["joint_ci_95"][1]
            p_sup = j_res["joint_p_val_superiority"]

            if tau_star_h is None and j_high >= 0.0:
                tau_star_h = delay

            joint_delay_summary.append({
                "horizon": h_name,
                "delay_tau": delay,
                "delay_minutes": delay * 10,
                "n_cells": n_cells_val,
                "drop_fraction": drop_f,
                "stale_fraction": stale_f,
                "mean_delta_kwh": mean_delta,
                "median_delta_kwh": med_delta,
                "joint_ci_95_low": j_low,
                "joint_ci_95_high": j_high,
                "joint_p_superiority": p_sup,
                "challenger_viol_pct": viol_c,
                "baseline_viol_pct": viol_b,
                "baseline_psrei": float(sub["baseline_psrei"].mean()),
                "challenger_psrei": float(sub["challenger_psrei"].mean()),
            })
        tau_star_hierarchical[h_name] = tau_star_h

    df_joint_delay = pd.DataFrame(joint_delay_summary)

    # 9. Generate Comprehensive Markdown Audit Report
    joint_path = out_dir / 'joint_statistics.json'
    joint_path.write_text(json.dumps(joint_delay_summary, indent=2), encoding='utf-8')
    report_md = f"""# EXP03 causal replay v2

Synthetic asynchronous envelope only. Execution device: {device}.
Result CSV: {csv_path}. Joint seed/day statistics: {joint_path}.
Full packet-grid archives: packet_grid/delay*.npz. They contain raw values,
all packet delays (event time is the time-axis index; arrival=event+delay),
node/channel indices, selected source event, missing/stale masks and consumed features.
Manifest digest: {trace_digest}. arrival_trace.jsonl is a sample only.
One simulator realization per delay is shared by all model seeds; uncertainty
is conditional on these traces and is not uncertainty across simulator seeds.
Initial state is standardized zero until a causal packet is available.
Tau loss-of-advantage: {tau_star_hierarchical}; this is the first upper CI bound
reaching zero, NOT the first demonstrated disadvantage. No directional scientific
verdict is hardcoded. Inspect every joint interval and preserve negative/null results.
"""
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(report_md, encoding="utf-8")
    print(f"[OK] Generated hardened audit report: {args.output_report}")
    print("==================================================================")
    print("EXP-03 EXECUTION COMPLETE")
    print("==================================================================")


if __name__ == "__main__":
    main()
