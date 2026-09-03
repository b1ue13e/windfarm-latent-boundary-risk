"""Degraded-gate reserve pricing: does the soft-gate-bin cost survive when the
gate is recomputed on degraded inputs?

Completes the soft-rule contrast: soft-pab-bin wins on clean anchors but
collapses toward the gate under degradation. Here the gate is actually
re-forwarded on degraded anchor inputs (delay/noise, same protocol as the
fair-degradation audit), and its soft binning is evaluated with clean
validation-frozen calibration.

Pre-registered reading: if the recomputed soft-gate-bin cost stays near its
clean value (16.065M) under delay6 and strong noise while soft-pab-bin has
collapsed to the same level, the routed posterior is the only soft pricing
signal that survives degradation.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from windfarm_moe.data import RegimeWindowDataset, load_cache_bundle
from windfarm_moe.mechanism_intervention import _load_model_from_checkpoint

DT = 1.0 / 6.0
QUANTILE_GRID = [0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 0.975, 0.99]
N_BINS = 5


def load_split(run_dir: Path, split: str):
    d = run_dir / f"{split}_metrics"
    pred = np.load(d / "pred.npy")
    target = np.load(d / "target.npy")
    mask = np.load(d / "mask.npy") > 0.5
    regime = np.load(d / "regime_primary.npy")
    gate = np.load(d / "gate_prob.npy")
    anchor = np.load(d / "anchor_physics.npy")
    return pred, target, mask, regime, gate, anchor


def shortfall_cells(pred, target, mask):
    return np.where(mask, np.maximum(pred - target, 0.0), np.nan)


def ppitch_from_gate(gate):
    p3 = gate[..., :3]
    return p3[..., 2] / np.maximum(p3.sum(axis=-1), 1e-9)


def broadcast(bin_anchor, H):
    return np.repeat(bin_anchor[:, None, :], H, axis=1)


def fit_policy(s_val, cell_sel_val, bin_val, rho):
    sel = cell_sel_val & np.isfinite(s_val)
    out = {}
    for b in np.unique(bin_val[cell_sel_val]):
        sb = s_val[sel & (bin_val == b)]
        if sb.size < 50:
            sb = s_val[sel]
        best = None
        for q in QUANTILE_GRID:
            r = np.quantile(sb, q)
            cost = (r * sb.size + rho * np.maximum(sb - r, 0).sum()) * DT
            if best is None or cost < best[0]:
                best = (cost, q, r)
        out[int(b)] = (best[1], best[2])
    return out


def eval_policy(s_test, cell_sel_test, bin_test, reserves, rho):
    sel = cell_sel_test & np.isfinite(s_test)
    s = s_test[sel]
    b = bin_test[sel]
    r = np.array([reserves[int(x)][1] for x in b])
    return {
        "total_cost": float((r.sum() + rho * np.maximum(s - r, 0).sum()) * DT),
        "violation_rate": float(np.mean(s > r)),
        "reserve": float(r.sum() * DT),
        "shortage": float(np.maximum(s - r, 0).sum() * DT),
    }


def forward_gate(model, loader, bundle, device, degrade, seed):
    wspd_phy = 0
    pab_phy = 1
    delay = int(degrade.get("delay", 0))
    noise = degrade.get("noise")
    rng = np.random.default_rng(1729 + seed * 1009 + delay * 7 + (0 if noise is None else int(noise[0] * 100 + noise[1] * 10)))
    std_physics = np.asarray(bundle.physics_model, dtype=np.float64)
    outs = []
    with torch.no_grad():
        for batch in loader:
            anchor_idx = batch["anchor_index"].numpy().astype(np.int64)
            x_hist = batch["x_hist"].clone()
            anchor_physics = batch["anchor_physics"].clone()
            lag_idx = np.clip(anchor_idx - delay, 0, std_physics.shape[0] - 1)
            anchor_physics[:, :, wspd_phy] = torch.from_numpy(std_physics[lag_idx, :, wspd_phy]).float()
            anchor_physics[:, :, pab_phy] = torch.from_numpy(std_physics[lag_idx, :, pab_phy]).float()
            if noise is not None:
                bsz, nodes = anchor_idx.shape[0], anchor_physics.shape[1]
                anchor_physics[..., wspd_phy] += torch.from_numpy(rng.normal(0.0, float(noise[0]), size=(bsz, nodes))).float()
                anchor_physics[..., pab_phy] += torch.from_numpy(rng.normal(0.0, float(noise[1]), size=(bsz, nodes))).float()
            _, gate_prob, _ = model(
                x_hist.to(device),
                batch["edge_index_hist"].to(device),
                batch["edge_weight_hist"].to(device),
                batch["feature_mask_hist"].to(device),
                anchor_physics.to(device),
            )
            outs.append(gate_prob.cpu().numpy())
    return np.concatenate(outs, axis=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default="artifacts/cache_strictmask_trainweights/wtb_245d")
    ap.add_argument("--suite-root", required=True)
    ap.add_argument("--run-pattern", default="wtb_bal_align_force_seed{seed}")
    ap.add_argument("--seeds", default="201,202,203,204,205")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--rated-wind", type=float, default=10.5)
    ap.add_argument("--band", type=float, default=1.0)
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    bundle = load_cache_bundle(args.cache_dir, mmap_mode="r")
    dataset = RegimeWindowDataset(bundle, "test", int(bundle.metadata["hist_len"]), int(bundle.metadata["pred_len"]))
    loader = DataLoader(dataset, batch_size=64, shuffle=False, num_workers=0)
    H = int(bundle.metadata["pred_len"])

    rows = []
    for seed in [int(s) for s in args.seeds.split(",")]:
        run_dir = Path(args.suite_root) / args.run_pattern.format(seed=seed)
        pv, tv, mv, rv_, gv, av = load_split(run_dir, "val")
        pt, tt, mt, rt_, gt, at = load_split(run_dir, "test")
        s_val = shortfall_cells(pv, tv, mv)
        s_test = shortfall_cells(pt, tt, mt)

        wspd = at[..., 0]
        pab = at[..., 1]
        in_band = np.abs(wspd - args.rated_wind) <= args.band
        va_t = np.isin(rt_, [1, 2]) & in_band
        wspd_v = av[..., 0]
        in_band_v = np.abs(wspd_v - args.rated_wind) <= args.band
        va_v = np.isin(rv_, [1, 2]) & in_band_v
        cell_v = broadcast(va_v, H)
        cell_t = broadcast(va_t, H)

        pp_v = ppitch_from_gate(gv)
        pp_t = ppitch_from_gate(gt)
        edges = np.quantile(pp_v[va_v], np.linspace(0, 1, N_BINS + 1)[1:-1])
        bin_v = np.clip(np.searchsorted(edges, pp_v), 0, N_BINS - 1)
        bin_v_c = broadcast(bin_v, H)
        reserves = fit_policy(s_val, cell_v, bin_v_c, 10.0)
        bin_t_clean = np.clip(np.searchsorted(edges, pp_t), 0, N_BINS - 1)
        m = eval_policy(s_test, cell_t, broadcast(bin_t_clean, H), reserves, 10.0)
        rows.append({"seed": seed, "condition": "clean", **m})

        model = _load_model_from_checkpoint(run_dir, bundle, device)
        for delay, noise, label in [(1, None, "delay1"), (3, None, "delay3"), (6, None, "delay6"), (0, (1.0, 2.0), "noise_strong")]:
            gate_d = forward_gate(model, loader, bundle, device, {"delay": delay, "noise": noise}, seed)
            pp_d = ppitch_from_gate(gate_d)
            bin_t_d = np.clip(np.searchsorted(edges, pp_d), 0, N_BINS - 1)
            m = eval_policy(s_test, cell_t, broadcast(bin_t_d, H), reserves, 10.0)
            rows.append({"seed": seed, "condition": label, **m})
            print(f"seed {seed} {label}: cost={m['total_cost']:.4e}", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "degraded_gate_reserve_by_seed.csv", index=False)
    print()
    print("=== recomputed soft-gate-bin cost by degradation (rho=10) ===")
    print(df.groupby("condition")[["total_cost", "violation_rate", "reserve", "shortage"]].mean().to_string())
    print("DEGRADED_GATE_RESERVE_DONE")


if __name__ == "__main__":
    main()
