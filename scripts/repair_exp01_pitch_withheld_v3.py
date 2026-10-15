from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from windfarm_moe.config import ModelConfig
from windfarm_moe.data import RegimeWindowDataset, load_cache_bundle
from windfarm_moe.model import RegimeAwareForecaster
from scripts.hierarchical_bootstrap import compute_hierarchical_joint_bootstrap
from scripts.run_exp01_matched_control_benchmark import RHO, TAU, DT, BLOCK_SIZE

SOURCE_RUN = "artifacts/strictmask_ablation_rerun_wtb_full/wtb_bal_align_force_seed{seed}"
FARMS = {
    "penmanshiel": ("Penmanshiel", "artifacts/cache_signature_penmanshiel/external_wind_penmanshiel_obs_window_canonical"),
    "kelmarsh": ("Kelmarsh", "artifacts/cache_signature_kelmarsh/external_wind_kelmarsh_obs_window_canonical"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class WithheldDataset(Dataset):
    def __init__(self, base, bundle, pitch_idx):
        self.base, self.bundle, self.pitch_idx = base, bundle, pitch_idx

    def __len__(self):
        return len(self.base)

    def __getitem__(self, idx):
        item = self.base[idx]
        ap = item["anchor_physics"].clone()
        ap[..., self.pitch_idx] = 0.0
        item["anchor_physics"] = ap
        # Feature input includes only standardized SCADA channels. Mask the pitch
        # channel when its identity is documented in metadata; otherwise fail closed.
        names = self.bundle.metadata.get("feature_names", [])
        pitch_features = [
            i for i, n in enumerate(names)
            if str(n).lower() in {"pab", "pitch", "pab_mean", "pab_std"}
        ]
        if not {"Pab_mean", "Pab_std"}.issubset({str(n) for n in names}):
            raise ValueError(f"Pitch history channels are not fully named in metadata: {names}")
        for pitch_feature in pitch_features:
            item["x_hist"][..., pitch_feature] = 0.0
            item["feature_mask_hist"][..., pitch_feature] = 0.0
        return item


def infer_gates(source_run: Path, bundle, split: str, device: torch.device):
    ckpt_path = source_run / "best_model.pt"
    checkpoint = torch.load(ckpt_path, map_location=device, weights_only=False)
    raw_config = dict(checkpoint["model_config"])
    config = ModelConfig(**{k: v for k, v in raw_config.items() if k in ModelConfig.__dataclass_fields__})
    train_config = dict(checkpoint["train_config"])
    model = RegimeAwareForecaster(
        feature_dim=int(bundle.features.shape[-1]),
        pred_len=int(bundle.metadata["pred_len"]),
        mode=str(train_config["mode"]), config=config,
    ).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    physics_names = bundle.metadata.get("physics_names", [])
    if "Pab_mean" not in physics_names:
        raise ValueError("Target cache metadata lacks named Pab_mean pitch feature")
    pitch_idx = physics_names.index("Pab_mean")
    base = RegimeWindowDataset(bundle, split, int(bundle.metadata["hist_len"]), int(bundle.metadata["pred_len"]))
    ds = WithheldDataset(base, bundle, pitch_idx)
    loader = DataLoader(ds, batch_size=int(train_config.get("batch_size", 16)), shuffle=False, num_workers=0)
    gates, anchors = [], []
    with torch.no_grad():
        for batch in loader:
            ap = batch["anchor_physics"].to(device)
            if torch.count_nonzero(ap[..., pitch_idx]).item() != 0:
                raise AssertionError("Nonzero pitch reached model forward")
            _, gate, _ = model(
                batch["x_hist"].to(device), batch["edge_index_hist"].to(device),
                batch["edge_weight_hist"].to(device), batch["feature_mask_hist"].to(device), ap,
            )
            gates.append(gate.detach().cpu().numpy())
            anchors.extend(batch["anchor_index"].cpu().numpy().tolist())
    del model
    return np.concatenate(gates), np.asarray(anchors, dtype=np.int64), checkpoint, pitch_idx


def block_delta(s, rc, rb, mask, anchors):
    ordered = np.unique(anchors)
    indices = np.array([int(np.searchsorted(ordered, a)) // BLOCK_SIZE for a in anchors])
    n = int(indices.max()) + 1
    valid = mask & np.isfinite(s) & np.isfinite(rc) & np.isfinite(rb)
    diff = ((rc + RHO * np.maximum(s - rc, 0)) - (rb + RHO * np.maximum(s - rb, 0))) * DT
    delta = np.bincount(indices, weights=np.where(valid, diff, 0).sum(axis=1), minlength=n)
    count = np.bincount(indices, weights=valid.sum(axis=1), minlength=n)
    return delta, count


def fit_bins(values, s, mask, bins, min_n=30):
    edges = np.unique(np.quantile(values[mask], np.linspace(0, 1, bins + 1)[1:-1]))
    assignment = np.digitize(values, edges)
    global_q = float(np.quantile(s[mask], TAU))
    qs = np.array([float(np.quantile(s[(assignment == b) & mask], TAU)) if np.sum((assignment == b) & mask) >= min_n else global_q for b in range(len(edges) + 1)])
    return edges, qs


def assert_forecast_alignment(metric_dir, bundle, anchors, target, mask):
    """Integer anchors are insufficient: reject different physical windows and nodes."""
    metric_dir = Path(metric_dir)
    saved_target = np.load(metric_dir/'target.npy', mmap_mode='r')
    saved_mask = np.load(metric_dir/'mask.npy', mmap_mode='r').astype(bool)
    if saved_target.shape != target.shape or not np.array_equal(saved_mask, mask):
        raise ValueError('Frozen forecast population mask mismatch (possibly shifted physical window)')
    if not np.array_equal(saved_target[mask], target[mask], equal_nan=True):
        raise ValueError('Frozen forecast targets belong to a different physical window')
    saved_times = np.load(metric_dir/'anchor_time_index.npy')
    if not np.array_equal(saved_times, np.asarray(bundle.time_index[anchors])):
        raise ValueError('Frozen forecast physical time indices differ')
    identity = json.loads((metric_dir/'population_identity.json').read_text(encoding='utf-8'))
    expected_nodes = bundle.metadata.get('node_labels', np.asarray(bundle.node_ids).tolist())
    for key, expected in [('node_labels',expected_nodes), ('window_begin',bundle.metadata.get('window_begin')),
                          ('window_offset_days',bundle.metadata.get('window_offset_days'))]:
        if identity.get(key) != expected:
            raise ValueError(f'Frozen forecast identity mismatch: {key}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="artifacts/exp01_pitchmasked_v3")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--seeds", default="201,202,203,204,205")
    parser.add_argument("--bootstrap", type=int, default=5000)
    parser.add_argument("--random-seed", type=int, default=20261014)
    parser.add_argument('--source-pattern', default=SOURCE_RUN)
    parser.add_argument('--forecast-pattern', default='artifacts/external_wind_runs/{farm}/chronological/external_wind_full_seed{seed}')
    parser.add_argument('--cache-map', type=Path, default=None,
                        help='JSON mapping farm to corrected raw cache path')
    args = parser.parse_args()
    out = ROOT / args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)
    seeds = [int(x) for x in args.seeds.split(",")]
    rows, provenance, block_records, native_blocks_dict = [], [], {}, {}

    cache_map = json.loads(args.cache_map.read_text(encoding='utf-8')) if args.cache_map else {}
    for farm, (display, legacy_cache) in FARMS.items():
        cache_rel = cache_map.get(farm, legacy_cache)
        bundle = load_cache_bundle(ROOT / cache_rel, mmap_mode="r")
        names = bundle.metadata.get("physics_names", [])
        if "Pab_mean" not in names:
            raise ValueError(f"{farm} cache does not identify pitch channel; metadata keys={sorted(bundle.metadata.keys())}")
        pitch_idx = names.index("Pab_mean")
        feat_names = bundle.metadata.get("feature_names", [])
        wspd_idx = names.index("Wspd") if "Wspd" in names else 0
        pred_len = int(bundle.metadata["pred_len"])
        for seed in seeds:
            src = ROOT / args.source_pattern.format(seed=seed)
            src_summary = json.loads((src / "training_summary.json").read_text(encoding="utf-8"))
            checkpoint_meta = torch.load(src / "best_model.pt", map_location="cpu", weights_only=False).get("metadata", {})
            if str(checkpoint_meta.get("dataset", "")).lower() != "wtb" or int(checkpoint_meta.get("num_nodes", 0)) != 134:
                raise RuntimeError(f"Checkpoint is not proven WTB-trained: {checkpoint_meta.get('dataset')} / {checkpoint_meta.get('num_nodes')} nodes")
            src_checkpoint = src / "best_model.pt"
            gates_by_split, anchors_by_split, hashes = {}, {}, {}
            for split in ("val", "test"):
                gate, anchors, checkpoint, pi = infer_gates(src, bundle, split, device)
                if pi != pitch_idx:
                    raise AssertionError("Pitch index changed between inference and cache")
                gates_by_split[split], anchors_by_split[split] = gate, anchors
                path = out / f"{farm}_seed{seed}_{split}_gate_pitchmasked.npy"
                np.save(path, gate)
                hashes[split] = sha256(path)
            val_anchor, test_anchor = anchors_by_split["val"], anchors_by_split["test"]
            run_dir = ROOT / args.forecast_pattern.format(farm=farm,seed=seed)
            if not np.array_equal(test_anchor, np.load(run_dir / 'test_metrics/anchor_index.npy')):
                raise ValueError(f"Frozen forecast anchor mismatch: {farm} seed {seed}")
            if not np.array_equal(val_anchor, np.load(run_dir / 'val_metrics/anchor_index.npy')):
                raise ValueError(f"Frozen validation anchor mismatch: {farm} seed {seed}")
            val_target = np.stack([np.asarray(bundle.target[a+1:a+1+pred_len]) for a in val_anchor])
            test_target = np.stack([np.asarray(bundle.target[a+1:a+1+pred_len]) for a in test_anchor])
            val_mask = np.stack([np.asarray(bundle.target_mask[a+1:a+1+pred_len]) for a in val_anchor]).astype(bool)
            test_mask = np.stack([np.asarray(bundle.target_mask[a+1:a+1+pred_len]) for a in test_anchor]).astype(bool)
            assert_forecast_alignment(run_dir/'val_metrics', bundle, val_anchor, val_target, val_mask)
            assert_forecast_alignment(run_dir/'test_metrics', bundle, test_anchor, test_target, test_mask)
            vp = np.load(run_dir / "val_metrics/pred.npy")
            tp = np.load(run_dir / "test_metrics/pred.npy")
            val_wspd = np.asarray(bundle.physics_model[val_anchor, :, wspd_idx])
            test_wspd = np.asarray(bundle.physics_model[test_anchor, :, wspd_idx])
            for lead, horizon in ((0, "h=1"), (5, "h=6")):
                sv = np.maximum(vp[:, lead, :] - val_target[:, lead, :], 0)
                st = np.maximum(tp[:, lead, :] - test_target[:, lead, :], 0)
                mv, mt = val_mask[:, lead, :], test_mask[:, lead, :]
                w_edges, wq = fit_bins(val_wspd, sv, mv, 10)
                w_reserve = wq[np.clip(np.digitize(test_wspd, w_edges), 0, len(wq)-1)]
                gv, gt = gates_by_split["val"][..., 2], gates_by_split["test"][..., 2]
                g_edges, gq = fit_bins(gv, sv, mv, 5)
                g_reserve = gq[np.clip(np.digitize(gt, g_edges), 0, len(gq)-1)]
                valid = mt & np.isfinite(st)
                cost_b = float(np.sum((w_reserve + RHO*np.maximum(st-w_reserve, 0))[valid]) * DT)
                cost_c = float(np.sum((g_reserve + RHO*np.maximum(st-g_reserve, 0))[valid]) * DT)
                violation_b = float(np.mean(st[valid] > w_reserve[valid]) * 100)
                violation_c = float(np.mean(st[valid] > g_reserve[valid]) * 100)
                delta, counts = block_delta(st, g_reserve, w_reserve, valid, test_anchor)
                block_records.setdefault((farm, horizon), {})[seed] = (delta, counts)
                prefix = f"{farm}_{horizon}_seed{seed}"
                # Keep native daily-block dict
                native_blocks_dict[f"{prefix}_delta"] = delta
                native_blocks_dict[f"{prefix}_count"] = counts
                rows.append({"farm":display,"farm_id":farm,"seed":seed,"horizon":horizon,"model":"WTB-source STGQ-Modular, pitch-masked inference","checkpoint":str(src_checkpoint.relative_to(ROOT)),"training_domain":"WTB (metadata cache_dir verified)","pitch_withheld_before_inference":True,"target_source":"external_site_frozen_point_forecast_external_wind_full","psrei_kwh":cost_c,"baseline_psrei_kwh":cost_b,"delta_psrei_kwh":cost_c-cost_b,"violation_rate_pct":violation_c,"baseline_violation_rate_pct":violation_b,"n_evaluated_cells":int(valid.sum()),"checkpoint_sha256":sha256(src_checkpoint),"training_summary_sha256":sha256(src/"training_summary.json"),"pitch_feature_name":"Pab_mean","pitch_feature_index":pitch_idx})
            provenance.append({"farm":farm,"seed":seed,"source_run":str(src.relative_to(ROOT)),"source_cache_dir":checkpoint.get("metadata", {}).get("cache_dir", "embedded metadata omits cache_dir; dataset=wtb, num_nodes=134"),"checkpoint_sha256":sha256(src_checkpoint),"summary_sha256":sha256(src/"training_summary.json"),"target_cache_metadata_sha256":sha256(ROOT/cache_rel/"metadata.json"),"pitch_feature":"Pab_mean","pitch_index":pitch_idx,"pitch_mask":"anchor_physics[Pab_mean] set to exactly 0 before model forward; both history features Pab_mean and Pab_std and their feature masks are set to zero before model forward","gate_hashes":hashes,"retrospective_reanalysis":True})

    np.savez_compressed(out/"exp01_native_day_blocks_v4.npz", **native_blocks_dict)
    stats=[]
    for (farm,horizon), seeds_map in block_records.items():
        lengths={len(v[0]) for v in seeds_map.values()}
        if len(lengths)!=1:
            raise ValueError(f"Unequal time-block counts for {farm}/{horizon}: {lengths}")
        joint=compute_hierarchical_joint_bootstrap({s:v[0] for s,v in seeds_map.items()},n_boot=args.bootstrap,two_stage_resample=True,random_seed=args.random_seed)
        stats.append({"farm_id":farm,"horizon":horizon,"n_seeds":joint["n_seeds"],"n_time_blocks":joint["n_blocks"],"mean_delta_psrei_kwh":joint["joint_mean"],"median_seed_delta_kwh":joint["joint_median"],"seed_sd_kwh":joint["joint_std"],"joint_ci95_low_kwh":joint["joint_ci_95"][0],"joint_ci95_high_kwh":joint["joint_ci_95"][1],"joint_p_noninferior_P_delta_le_0":joint["joint_p_non_inferior"],"inference":"two-stage resampling of daily blocks and model seeds; empirical P(delta<=0), not a two-sided p-value"})
    pd.DataFrame(rows).to_csv(out/"exp01_pitchmasked_v3_seed_results.csv",index=False)
    pd.DataFrame(stats).to_csv(out/"exp01_pitchmasked_v3_joint_statistics.csv",index=False)
    (out/"exp01_pitchmasked_v3_provenance.json").write_text(json.dumps({"status":"retrospective reanalysis; no preregistration created or backfilled","source_checkpoint_policy":"WTB-only source checkpoint paths, and training_summary cache_dir must identify wtb_245d","results":provenance},indent=2),encoding="utf-8")

if __name__=="__main__":
    main()
