"""Fair-degradation replay for the MPPT-to-pitch early-window detection claim.

Experiment A: degrade the *gate's own* anchor inputs (delay / sensor noise)
and compare gate recall against the threshold-rule recall computed from the
same degraded readings. This closes the semantic gap of the previous
label-degradation audit, where only the rule/classifier stream was degraded
while the gate stayed clean.

Delay semantics: the confirming issue-time anchor stream (Wspd, Pab_mean)
arrives d steps late, so both the gate anchor and the rule use the t-d
readings; history windows retain the archived stream. Noise semantics:
zero-mean Gaussian noise is added to Wspd/Pab in physical units and mapped
into the standardized model space via train-split statistics.

Ground truth: clean-regime MPPT->pitch transitions define the early
pitch-window target cells (identical to the existing label-degradation audit).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"

repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import numpy as np
import pandas as pd
import torch

torch.set_num_threads(2)
from torch.utils.data import DataLoader

from windfarm_moe.anchor_stress import (
    _detection_metrics,
    _early_pitch_window,
    _mppt_to_pitch_transitions,
)
from windfarm_moe.data import RegimeWindowDataset, load_cache_bundle
from windfarm_moe.mechanism_intervention import _load_model_from_checkpoint
from windfarm_moe.regimes import compute_wtb_operation_regime
from windfarm_moe.utils import ensure_dir, load_json

DELAYS = [1, 3, 6]
NOISE_LEVELS = [(0.5, 1.0), (1.0, 2.0)]


def _standardized_noise_scale(metadata: dict[str, Any], name: str, phys_sigma: float) -> float:
    stats = metadata.get("physics_model_stats", {})
    names = list(metadata.get("physics_names", []))
    idx = names.index(name) if name in names else -1
    std = 1.0
    if idx >= 0:
        entry = stats.get(str(idx))
        if isinstance(entry, dict):
            std = float(entry.get("std") or 1.0)
    return float(phys_sigma) / max(std, 1e-6)


def _forward_collect(model, loader, bundle, device, degrade: dict[str, Any] | None, seed: int):
    gate_batches = []
    anchor_batches = []
    feature_names = list(bundle.metadata.get("feature_names", []))
    physics_names = list(bundle.metadata.get("physics_names", []))
    wspd_feat = feature_names.index("Wspd") if "Wspd" in feature_names else -1
    pab_feat = feature_names.index("Pab_mean") if "Pab_mean" in feature_names else -1
    patv_feat = -1
    for cand in ("Patv_hist", "Patv"):
        if cand in feature_names:
            patv_feat = feature_names.index(cand)
            break
    degrade_feat_indices = [idx for idx in (wspd_feat, pab_feat, patv_feat) if idx >= 0]
    wspd_phy = physics_names.index("Wspd") if "Wspd" in physics_names else 0
    pab_phy = physics_names.index("Pab_mean") if "Pab_mean" in physics_names else 1
    patv_phy = physics_names.index("Patv") if "Patv" in physics_names else -1
    channel_policy = str(degrade.get("channel_policy", "primary")) if degrade else "primary"
    delay = int(degrade.get("delay", 0)) if degrade else 0
    history_delay = bool(degrade.get("history_delay", True)) if degrade else True
    noise = degrade.get("noise") if degrade else None

    raw_physics = np.asarray(bundle.physics, dtype=np.float64)
    std_physics = np.asarray(bundle.physics_model, dtype=np.float64)
    steps_per_day = int(bundle.metadata.get("steps_per_hour", 6)) * 24
    deltas = {}
    if noise is not None:
        w_sigma_std = _standardized_noise_scale(bundle.metadata, "Wspd", float(noise[0]))
        p_sigma_std = _standardized_noise_scale(bundle.metadata, "Pab_mean", float(noise[1]))
        deltas = {"feat_wspd": w_sigma_std, "feat_pab": p_sigma_std, "phy_wspd": w_sigma_std, "phy_pab": p_sigma_std}
    rng = np.random.default_rng(1729 + seed * 1009 + delay * 7 + (0 if noise is None else int(noise[0] * 100 + noise[1] * 10)))

    with torch.no_grad():
        for batch in loader:
            anchor_idx = batch["anchor_index"].numpy().astype(np.int64)
            x_hist = batch["x_hist"].clone()
            anchor_physics = batch["anchor_physics"].clone()
            lag_idx = np.clip(anchor_idx - delay, 0, raw_physics.shape[0] - 1)
            if channel_policy == "all":
                anchor_physics = torch.from_numpy(std_physics[lag_idx]).float()
                if history_delay and delay > 0:
                    head = x_hist[:, :1, :, :].repeat(1, delay, 1, 1)
                    x_hist = torch.cat([head, x_hist[:, :-delay, :, :]], dim=1)
            else:
                anchor_physics[:, :, wspd_phy] = torch.from_numpy(std_physics[lag_idx, :, wspd_phy]).float()
                anchor_physics[:, :, pab_phy] = torch.from_numpy(std_physics[lag_idx, :, pab_phy]).float()
                if patv_phy >= 0:
                    anchor_physics[:, :, patv_phy] = torch.from_numpy(std_physics[lag_idx, :, patv_phy]).float()
                if history_delay and delay > 0:
                    for idx in degrade_feat_indices:
                        vals = x_hist[..., idx]  # (B, H, N)
                        head = vals[:, :1, :].repeat(1, delay, 1)
                        shifted = torch.cat([head, vals[:, :-delay, :]], dim=1)
                        x_hist[..., idx] = shifted
            if noise is not None:
                bsz = anchor_idx.shape[0]
                nodes = x_hist.shape[2]
                if wspd_feat >= 0:
                    x_hist[..., wspd_feat] += torch.from_numpy(
                        rng.normal(0.0, deltas["feat_wspd"], size=(bsz, x_hist.shape[1], nodes))
                    ).float()
                if pab_feat >= 0:
                    x_hist[..., pab_feat] += torch.from_numpy(
                        rng.normal(0.0, deltas["feat_pab"], size=(bsz, x_hist.shape[1], nodes))
                    ).float()
                anchor_physics[..., wspd_phy] += torch.from_numpy(
                    rng.normal(0.0, deltas["phy_wspd"], size=(bsz, nodes))
                ).float()
                anchor_physics[..., pab_phy] += torch.from_numpy(
                    rng.normal(0.0, deltas["phy_pab"], size=(bsz, nodes))
                ).float()
            x_hist = x_hist.to(device)
            edge_index = batch["edge_index_hist"].to(device)
            edge_weight = batch["edge_weight_hist"].to(device)
            feature_mask = batch["feature_mask_hist"].to(device)
            anchor_physics = anchor_physics.to(device)
            _, gate_prob, _ = model(x_hist, edge_index, edge_weight, feature_mask, anchor_physics)
            gate_batches.append(gate_prob.cpu().numpy())
            anchor_batches.append(anchor_idx)
    return np.concatenate(gate_batches, axis=0), np.concatenate(anchor_batches, axis=0)


def _rule_pitch_from_degraded(raw_physics, anchors, delay, noise, seed, cut_in, rated, pth):
    lag_idx = np.clip(anchors - delay, 0, raw_physics.shape[0] - 1)
    wspd = raw_physics[lag_idx, :, 0].copy()
    pab = raw_physics[lag_idx, :, 1].copy()
    rng = np.random.default_rng(1729 + seed * 1009 + delay * 7 + (0 if noise is None else int(noise[0] * 100 + noise[1] * 10)))
    if noise is not None:
        wspd += rng.normal(0.0, float(noise[0]), size=wspd.shape)
        pab += rng.normal(0.0, float(noise[1]), size=pab.shape)
    regime, valid_float = compute_wtb_operation_regime(wspd, pab, cut_in_wind=cut_in, rated_wind=rated, pitch_threshold=pth)
    return (regime == 2) & valid_float.astype(bool)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default="artifacts/cache_strictmask_trainweights/wtb_245d")
    ap.add_argument("--suite-root", default="artifacts/trainweight_class_weight_rerun_20260702")
    ap.add_argument("--output-dir", default="artifacts/fair_degradation_replay_20260903")
    ap.add_argument("--seeds", default="201,202,203,204,205")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--degrade-history", dest="degrade_history", action="store_true", default=True,
                    help="Shift the Wspd/Pab history channels by the delay (Unified Arrival Layer, default: True)")
    ap.add_argument("--no-degrade-history", dest="degrade_history", action="store_false",
                    help="Disable shifting Wspd/Pab history channels")
    ap.add_argument("--cut-in", type=float, default=3.0)
    ap.add_argument("--rated", type=float, default=10.5)
    ap.add_argument("--pitch-th", type=float, default=2.0)
    ap.add_argument("--channel-policy", default="primary", choices=["all", "primary"],
                    help="Channels degraded: 'primary' (Wspd, Pab, Patv) or 'all' (all 11 telemetry channels)")
    args = ap.parse_args()

    out_dir = ensure_dir(args.output_dir)
    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    bundle = load_cache_bundle(args.cache_dir, mmap_mode="r")
    dataset = RegimeWindowDataset(bundle, "test", int(bundle.metadata["hist_len"]), int(bundle.metadata["pred_len"]))
    loader = DataLoader(dataset, batch_size=64, shuffle=False, num_workers=0)

    regime = np.asarray(bundle.regime_primary, dtype=np.int16)[dataset.anchor_indices]
    valid = np.asarray(bundle.regime_primary_valid, dtype=bool)[dataset.anchor_indices]
    raw_physics = np.asarray(bundle.physics, dtype=np.float64)

    transitions = _mppt_to_pitch_transitions(regime, valid)
    early_pitch, transition_support = _early_pitch_window(regime, valid, transitions, early_window_steps=6)

    rows = []
    for seed in [int(s) for s in args.seeds.split(",")]:
        run_dir = Path(args.suite_root) / f"wtb_bal_align_force_seed{seed}"
        model = _load_model_from_checkpoint(run_dir, bundle, device)
        print(f"seed {seed} loaded", flush=True)

        gate_clean, anchors = _forward_collect(model, loader, bundle, device, None, seed)
        gate_classes = min(int(bundle.metadata.get("primary_num_classes", 3)), gate_clean.shape[-1])
        gate_label_clean = gate_clean[..., :gate_classes].argmax(axis=-1)
        conditions = [("clean", None, None)]
        for d in DELAYS:
            conditions.append((f"delay{d}", d, None))
        for (w, p) in NOISE_LEVELS:
            conditions.append((f"noise_{w}_{p}", 0, (w, p)))

        for name, delay, noise in conditions:
            if delay is None:
                gate_label = gate_label_clean
                rule_pitch = (regime == 2) & valid
            else:
                gate_prob, _ = _forward_collect(
                    model, loader, bundle, device,
                    {"delay": delay, "noise": noise, "history_delay": args.degrade_history, "channel_policy": args.channel_policy},
                    seed,
                )
                gate_label = gate_prob[..., :gate_classes].argmax(axis=-1)
                rule_pitch = _rule_pitch_from_degraded(
                    raw_physics, anchors, delay, noise, seed, args.cut_in, args.rated, args.pitch_th
                )
            gate_pitch = gate_label == 2
            m = _detection_metrics(gate_pitch, rule_pitch, early_pitch, transition_support)
            rows.append(
                {
                    "seed": seed,
                    "condition": name if args.degrade_history else (name + ("_no_histdelay" if delay not in (None, 0) else "")),
                    "delay_steps": 0 if delay is None else int(delay),
                    "wspd_noise": 0.0 if noise is None else float(noise[0]),
                    "pab_noise": 0.0 if noise is None else float(noise[1]),
                    **m,
                }
            )
            print(f"  {name}: gate_recall={m['gate_recall']:.4f} rule_recall={m['threshold_recall']:.4f} gain={m['recall_gain']:.4f}", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "fair_degradation_raw.csv", index=False)
    summary = (
        df.groupby("condition")
        .agg(
            gate_recall_mean=("gate_recall", "mean"),
            gate_recall_std=("gate_recall", "std"),
            rule_recall_mean=("threshold_recall", "mean"),
            rule_recall_std=("threshold_recall", "std"),
            gain_mean=("recall_gain", "mean"),
            gain_std=("recall_gain", "std"),
        )
        .reset_index()
    )
    summary.to_csv(out_dir / "fair_degradation_summary.csv", index=False)
    print(summary.to_string(index=False))
    save_json_path = out_dir / "fair_degradation_config.json"
    with open(save_json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "cache_dir": args.cache_dir,
                "suite_root": args.suite_root,
                "seeds": args.seeds,
                "delays": DELAYS,
                "noise_levels": NOISE_LEVELS,
                "policy": (
                    "Fair degradation (Unified Arrival Layer): gate and rule see the same degraded Wspd/Pab readings "
                    "across both anchor and history channels. Early-window targets are defined by clean-regime transitions."
                ),
            },
            f,
            indent=2,
        )
    print("FAIR_DEGRADATION_DONE")


if __name__ == "__main__":
    main()
