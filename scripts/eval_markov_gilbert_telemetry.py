"""Markov-Gilbert Bursty Telemetry Degradation Honest Evaluation Script.

Simulates industrial substation network packet bursts (IEC 61400-25 telemetry loss)
and provides an honest, symmetric evaluation of boundary-risk detection resilience:
- Clean Physical Threshold Rule
- Stale Physical Threshold Rule (honest: both Wspd and Pab lagged by burst duration)
- Stale Physical Threshold Rule (legacy: Pab lagged only)
- Corrupted Jointly-Learned Routed Posterior (genuine forward pass with degraded feature tensors)
- Clean Jointly-Learned Routed Posterior (reference)

Protocol: 5 seeds on WTB operational test split (639k cells), 20,000 bootstrap resamples.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"

import numpy as np
import pandas as pd
import torch

torch.set_num_threads(2)
from torch.utils.data import DataLoader


def simulate_markov_gilbert(
    n_steps: int,
    p_gb: float = 0.08,
    p_bb: float = 0.75,
    max_lag: int = 6,
    rng: np.random.Generator = None
) -> Tuple[np.ndarray, np.ndarray]:
    """Simulate two-state Markov-Gilbert packet loss channel: 0=Good, 1=Bad (burst)."""
    if rng is None:
        rng = np.random.default_rng(2026)
    states = np.zeros(n_steps, dtype=np.int8)
    lags = np.zeros(n_steps, dtype=np.int16)
    curr = 0
    curr_lag = 0
    for t in range(n_steps):
        if curr == 0:
            if rng.random() < p_gb:
                curr = 1
                curr_lag = 1
        else:
            if rng.random() < p_bb:
                curr_lag = min(curr_lag + 1, max_lag)
            else:
                curr = 0
                curr_lag = 0
        states[t] = curr
        lags[t] = curr_lag
    return states, lags


def calc_detection_metrics(y_pred: np.ndarray, y_true: np.ndarray, mask: np.ndarray) -> Dict[str, float]:
    """Calculate recall, precision, and F1 score on masked cells."""
    p = y_pred[mask]
    t = y_true[mask]
    tp = float(np.sum(p & t))
    fp = float(np.sum(p & ~t))
    fn = float(np.sum(~p & t))
    rec = tp / max(tp + fn, 1.0)
    prec = tp / max(tp + fp, 1.0)
    f1 = 2.0 * prec * rec / max(prec + rec, 1e-9)
    return {
        "recall": rec,
        "precision": prec,
        "f1": f1,
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "evaluated_cells": int(np.sum(mask)),
        "true_positives_in_mask": int(np.sum(t)),
    }


def resolve_seeds(suite_dir: Path, requested_seeds: List[int]) -> List[int]:
    """Resolve available seed directories."""
    available = []
    for s in requested_seeds:
        if (suite_dir / f"wtb_full_seed{s}").exists():
            available.append(s)
    if available:
        return available

    # Fallback to discovering seeds
    discovered = []
    for p in sorted(suite_dir.glob("wtb_full_seed*")):
        try:
            num = int(p.name.replace("wtb_full_seed", ""))
            discovered.append(num)
        except ValueError:
            pass
    if discovered:
        print(f"Warning: requested seeds {requested_seeds} not found in {suite_dir}. Using discovered: {discovered}")
        return discovered
    raise FileNotFoundError(f"No wtb_full_seed* directories found in {suite_dir}")


def main():
    parser = argparse.ArgumentParser(description="Honest Markov-Gilbert burst telemetry evaluation.")
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--suite-dir", default="artifacts/trainweight_full_rerun_20260830", help="Suite directory.")
    parser.add_argument("--cache-dir", default="artifacts/cache_strictmask_trainweights/wtb_245d", help="Cache bundle directory.")
    parser.add_argument("--seeds", default="201,202,203,204,205", help="Seeds to evaluate.")
    parser.add_argument("--output-dir", default="artifacts/markov_gilbert_eval_honest", help="Output directory.")
    parser.add_argument("--device", default="cuda:0", help="Torch device.")
    parser.add_argument("--p-gb", type=float, default=0.08, help="P(Good -> Bad)")
    parser.add_argument("--p-bb", type=float, default=0.75, help="P(Bad -> Bad)")
    parser.add_argument("--max-lag", type=int, default=6, help="Maximum burst lag steps.")
    parser.add_argument("--n-bootstraps", type=int, default=20000, help="Number of bootstrap resamples.")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    # Add repo root to sys.path for windfarm_moe imports
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    suite_dir = (repo_root / args.suite_dir).resolve()
    cache_dir = (repo_root / args.cache_dir).resolve()
    out_dir = (repo_root / args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    requested_seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    seeds = resolve_seeds(suite_dir, requested_seeds)

    print(f"=== Honest Markov-Gilbert Bursty Telemetry Evaluation ===")
    print(f"Suite: {suite_dir}")
    print(f"Cache: {cache_dir}")
    print(f"Output: {out_dir}")
    print(f"Seeds: {seeds}")
    print(f"Channel params: p_gb={args.p_gb}, p_bb={args.p_bb}, max_lag={args.max_lag}")

    # Import windfarm_moe modules
    try:
        from windfarm_moe.data import load_cache_bundle, RegimeWindowDataset
        from windfarm_moe.mechanism_intervention import _load_model_from_checkpoint
        has_moe = True
    except ImportError as e:
        print(f"Warning: windfarm_moe import failed: {e}. Model forward inference may be unavailable.")
        has_moe = False

    device = torch.device(args.device if (torch.cuda.is_available() and "cuda" in args.device) else "cpu")
    print(f"Inference device: {device}")

    bundle = load_cache_bundle(cache_dir, mmap_mode="r")
    dataset = RegimeWindowDataset(bundle, "test", int(bundle.metadata["hist_len"]), int(bundle.metadata["pred_len"]))
    loader = DataLoader(dataset, batch_size=64, shuffle=False, num_workers=0)

    std_physics = np.asarray(bundle.physics_model, dtype=np.float64)
    raw_physics = np.asarray(bundle.physics, dtype=np.float64)
    anchor_indices = dataset.anchor_indices
    N = len(anchor_indices)

    regime = np.asarray(bundle.regime_primary, dtype=np.int16)[anchor_indices]
    valid = np.asarray(bundle.regime_primary_valid, dtype=bool)[anchor_indices]
    y_true_pitch = (regime == 2) & valid

    physics_names = list(bundle.metadata.get("physics_names", []))
    wspd_phy = physics_names.index("Wspd") if "Wspd" in physics_names else 0
    pab_phy = physics_names.index("Pab_mean") if "Pab_mean" in physics_names else 1

    feature_names = list(bundle.metadata.get("feature_names", []))
    wspd_feat = feature_names.index("Wspd") if "Wspd" in feature_names else -1
    pab_feat = feature_names.index("Pab_mean") if "Pab_mean" in feature_names else -1
    patv_feat = -1
    for cand in ("Patv_hist", "Patv"):
        if cand in feature_names:
            patv_feat = feature_names.index(cand)
            break
    degrade_feat_indices = [idx for idx in (wspd_feat, pab_feat, patv_feat) if idx >= 0]

    # Simulate Markov-Gilbert channel
    rng = np.random.default_rng(2026)
    burst_states, burst_lags = simulate_markov_gilbert(N, p_gb=args.p_gb, p_bb=args.p_bb, max_lag=args.max_lag, rng=rng)
    in_burst = burst_states == 1
    burst_mask = in_burst[:, None] & valid

    print(f"Simulated test steps: {N}")
    print(f"Burst steps: {np.sum(in_burst)} ({np.mean(in_burst):.2%})")
    print(f"Total burst turbine cells: {np.sum(burst_mask):,}")
    print(f"True pitch cells in burst: {np.sum(y_true_pitch[burst_mask]):,}")

    # Compute rule baseline predictions
    # 1. Clean Rule
    wspd_clean = raw_physics[anchor_indices, :, wspd_phy]
    pab_clean = raw_physics[anchor_indices, :, pab_phy]
    pred_clean_rule = (wspd_clean >= 10.5) & (pab_clean > 1.0) & valid

    # 2. Honest Stale Rule: both Wspd and Pab are lagged by burst_lags
    lagged_indices = np.clip(anchor_indices - burst_lags, 0, raw_physics.shape[0] - 1)
    wspd_stale = raw_physics[lagged_indices, :, wspd_phy]
    pab_stale = raw_physics[lagged_indices, :, pab_phy]
    pred_stale_rule_honest = (wspd_stale >= 10.5) & (pab_stale > 1.0) & valid

    # 3. Legacy Stale Rule: only Pab is lagged
    pab_stale_only = np.copy(pab_clean)
    for t in range(N):
        if in_burst[t] and burst_lags[t] > 0:
            t_src = max(0, anchor_indices[t] - burst_lags[t])
            pab_stale_only[t] = raw_physics[t_src, :, pab_phy]
    pred_stale_rule_legacy = (wspd_clean >= 10.5) & (pab_stale_only > 1.0) & valid

    all_rows = []

    for seed in seeds:
        run_dir = suite_dir / f"wtb_full_seed{seed}"
        print(f"\n--- Evaluating Seed {seed} ---")

        # Load clean precomputed gate probabilities
        clean_gate = np.load(run_dir / "test_metrics" / "gate_prob.npy")
        p3_clean = clean_gate[..., :3]
        p_pitch_clean = p3_clean[..., 2] / np.maximum(p3_clean.sum(axis=-1), 1e-9)
        pred_clean_model = p_pitch_clean >= 0.5

        # Forward model with honest burst-corrupted feature inputs
        print("Running genuine model forward pass with Markov-Gilbert corrupted features...")
        model = _load_model_from_checkpoint(run_dir, bundle, device)
        model.eval()

        gate_corrupted = []
        with torch.no_grad():
            for batch in loader:
                b_anchors = batch["anchor_index"].numpy().astype(np.int64)
                x_hist = batch["x_hist"].clone()
                edge_index = batch["edge_index_hist"].to(device)
                edge_weight = batch["edge_weight_hist"].to(device)
                feature_mask = batch["feature_mask_hist"].to(device)

                # Clone anchor physics and inject burst lags
                anc_corrupted = batch["anchor_physics"].clone()
                for b_i, global_idx in enumerate(b_anchors):
                    # Map to test sample index
                    t_match = np.where(anchor_indices == global_idx)[0]
                    if len(t_match) > 0:
                        t = t_match[0]
                        lag = int(burst_lags[t])
                        if lag > 0:
                            lag_idx = max(0, global_idx - lag)
                            anc_corrupted[b_i, :, wspd_phy] = torch.from_numpy(std_physics[lag_idx, :, wspd_phy]).float()
                            anc_corrupted[b_i, :, pab_phy] = torch.from_numpy(std_physics[lag_idx, :, pab_phy]).float()
                            for feat_idx in degrade_feat_indices:
                                vals = x_hist[b_i, :, :, feat_idx]
                                head = vals[:1, :].repeat(lag, 1)
                                shifted = torch.cat([head, vals[:-lag, :]], dim=0)
                                x_hist[b_i, :, :, feat_idx] = shifted

                x_hist = x_hist.to(device)
                anc_corrupted = anc_corrupted.to(device)
                _, g_cor, _ = model(x_hist, edge_index, edge_weight, feature_mask, anc_corrupted)
                gate_corrupted.append(g_cor.cpu().numpy())

        gcor = np.concatenate(gate_corrupted, axis=0)
        p3_cor = gcor[..., :3]
        p_pitch_cor = p3_cor[..., 2] / np.maximum(p3_cor.sum(axis=-1), 1e-9)
        pred_corrupted_model = p_pitch_cor >= 0.5

        methods = {
            "clean_rule": pred_clean_rule,
            "stale_threshold_rule_honest": pred_stale_rule_honest,
            "stale_threshold_rule_legacy": pred_stale_rule_legacy,
            "corrupted_routed_posterior": pred_corrupted_model,
            "clean_routed_posterior": pred_clean_model,
        }

        for m_name, m_pred in methods.items():
            metrics = calc_detection_metrics(m_pred, y_true_pitch, burst_mask)
            print(f"  {m_name:30s}: Recall={metrics['recall']:.4f}, Prec={metrics['precision']:.4f}, F1={metrics['f1']:.4f}")
            all_rows.append({
                "seed": seed,
                "method": m_name,
                **metrics,
            })

    df_raw = pd.DataFrame(all_rows)
    df_raw.to_csv(out_dir / "markov_gilbert_by_seed.csv", index=False)
    print(f"\nSaved per-seed raw metrics to {out_dir / 'markov_gilbert_by_seed.csv'}")

    # Summary table
    summary = (
        df_raw.groupby("method")
        .agg(
            recall_mean=("recall", "mean"),
            recall_std=("recall", "std"),
            precision_mean=("precision", "mean"),
            precision_std=("precision", "std"),
            f1_mean=("f1", "mean"),
            f1_std=("f1", "std"),
            evaluated_cells=("evaluated_cells", "mean"),
        )
        .reset_index()
    )
    summary_path = out_dir / "markov_gilbert_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\n=== Honest Markov-Gilbert Summary Table ===")
    print(summary.to_string(index=False))

    # Compute paired bootstrap between honest model and honest stale rule
    wide_f1 = df_raw.pivot(index="seed", columns="method", values="f1")
    paired_f1 = (wide_f1["corrupted_routed_posterior"] - wide_f1["stale_threshold_rule_honest"]).dropna().to_numpy()

    rng_boot = np.random.default_rng(42)
    boot_samples = rng_boot.choice(paired_f1, size=(args.n_bootstraps, len(paired_f1)), replace=True).mean(axis=1)
    f1_delta_mean = float(np.mean(paired_f1))
    f1_ci_low = float(np.percentile(boot_samples, 2.5))
    f1_ci_high = float(np.percentile(boot_samples, 97.5))

    guard = {
        "status": "honest_markov_gilbert_evaluation_completed",
        "seeds": seeds,
        "burst_packet_channel": {
            "p_gb": args.p_gb,
            "p_bb": args.p_bb,
            "max_lag": args.max_lag,
            "evaluated_burst_cells_per_seed": int(summary["evaluated_cells"].iloc[0]),
        },
        "methods_summary": {
            row["method"]: {
                "recall_mean": float(row["recall_mean"]),
                "recall_std": float(row["recall_std"]),
                "precision_mean": float(row["precision_mean"]),
                "precision_std": float(row["precision_std"]),
                "f1_mean": float(row["f1_mean"]),
                "f1_std": float(row["f1_std"]),
            }
            for _, row in summary.iterrows()
        },
        "honest_comparison": {
            "model_corrupted_f1_mean": float(summary[summary["method"] == "corrupted_routed_posterior"]["f1_mean"].iloc[0]),
            "rule_stale_honest_f1_mean": float(summary[summary["method"] == "stale_threshold_rule_honest"]["f1_mean"].iloc[0]),
            "rule_stale_legacy_f1_mean": float(summary[summary["method"] == "stale_threshold_rule_legacy"]["f1_mean"].iloc[0]),
            "f1_delta_mean (model - rule_honest)": f1_delta_mean,
            "f1_delta_95_ci": [f1_ci_low, f1_ci_high],
            "f1_excludes_zero": bool(f1_ci_low > 0.0 or f1_ci_high < 0.0),
        }
    }

    guard_path = out_dir / "markov_gilbert_guard.json"
    with open(guard_path, "w", encoding="utf-8") as f:
        json.dump(guard, f, indent=2)
    print(f"\nGuard metadata written to {guard_path}")


if __name__ == "__main__":
    main()
