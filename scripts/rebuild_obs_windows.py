"""Rebuild Penmanshiel/Kelmarsh caches with observability-qualified time windows.

Pre-registered, outcome-blind window rules:
  - penmanshiel: earliest contiguous 245-day window where
      daily pitch-coverage >= 0.70 AND daily regime-valid >= 0.70
      (scanned above: start day 720)
  - kelmarsh: earliest contiguous 245-day window where
      daily regime-valid >= 0.70
      (scanned above: start day 120; pitch coverage is a genuine
      partial-observability property, ~0.6, and is the quantity of interest)

Derived fields (class weights, pitch-force weights, feature/physics stats)
are recomputed from the new train split only, matching the train-only
provenance standard used elsewhere.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np

from windfarm_moe.external_wind import inverse_frequency_weights_from_labels

ROOT = Path(".")
HIST, PRED = 36, 24
WINDOW_DAYS = 245
TRAIN_DAYS, VAL_DAYS, TEST_DAYS = 180, 30, 35
SLOTS = 144
W = WINDOW_DAYS * SLOTS  # 35280

WINDOW_START_DAY = {
    "penmanshiel": 720,
    "kelmarsh": 120,
}

ARRAYS = [
    "features", "feature_mask", "target", "target_mask",
    "regime_primary", "regime_primary_valid",
    "regime_aux", "regime_aux_valid", "regime_valid",
    "physics", "physics_model", "edge_index", "edge_weight",
    "coords", "time_index", "anchor_index",
]


def rebuild(farm: str) -> None:
    src = ROOT / "artifacts/cache_external_wind" / f"external_wind_{farm}_chronological"
    dst = ROOT / "artifacts/cache_external_wind" / f"external_wind_{farm}_obs_window"
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)

    start = WINDOW_START_DAY[farm] * SLOTS
    stop = start + W

    metadata = json.loads((src / "metadata.json").read_text(encoding="utf-8"))

    for name in ARRAYS:
        path = src / f"{name}.npy"
        if not path.exists():
            continue
        arr = np.load(path, mmap_mode="r")
        sliced = np.array(arr[start:stop])
        np.save(dst / f"{name}.npy", sliced)

    # Recompute train-only class weights and pitch-force weights.
    regime = np.load(dst / "regime_primary.npy")
    valid = np.load(dst / "regime_primary_valid.npy")
    train_stop = TRAIN_DAYS * SLOTS
    primary_w = inverse_frequency_weights_from_labels(regime[:train_stop], valid[:train_stop], 3)
    pitch_binary = np.zeros_like(regime, dtype=np.int16)
    pitch_valid = ((regime == 1) | (regime == 2)).astype(np.float32)
    pitch_binary[regime == 2] = 1
    pitch_w = inverse_frequency_weights_from_labels(pitch_binary[:train_stop], pitch_valid[:train_stop], 2)

    # Recompute feature stats and physics_model_stats on the new train split.
    features = np.load(dst / "features.npy")
    feature_mask = np.load(dst / "feature_mask.npy")
    physics = np.load(dst / "physics.npy")
    physics_model = np.load(dst / "physics_model.npy")
    feature_names = [str(n) for n in metadata["feature_names"]]
    physics_names = [str(n) for n in metadata["physics_names"]]
    train_feat = features[:train_stop]
    train_phys = physics[:train_stop]

    feature_stats = {}
    for idx, name in enumerate(feature_names):
        vals = train_feat[..., idx]
        m = feature_mask[:train_stop, ..., idx]
        obs = vals[m > 0]
        feature_stats[name] = {
            "fill_mean": float(np.nanmean(obs)) if obs.size else 0.0,
            "mean": float(np.nanmean(obs)) if obs.size else 0.0,
            "std": float(np.nanstd(obs)) if obs.size else 1.0,
        }
    physics_stats = {}
    for idx, name in enumerate(physics_names):
        vals = train_phys[..., idx]
        obs = vals[np.isfinite(vals) & (vals != 0)] if name != "wake_score" else vals[np.isfinite(vals)]
        physics_stats[str(idx)] = {
            "fill_mean": float(np.nanmean(obs)) if obs.size else 0.0,
            "mean": float(np.nanmean(obs)) if obs.size else 0.0,
            "std": float(np.nanstd(obs)) if obs.size else 1.0,
        }

    metadata["num_steps"] = W
    metadata["split_bounds"] = {
        "train": [0, train_stop],
        "val": [train_stop, train_stop + VAL_DAYS * SLOTS],
        "test": [train_stop + VAL_DAYS * SLOTS, train_stop + (VAL_DAYS + TEST_DAYS) * SLOTS],
    }
    metadata["primary_class_weights"] = [float(x) for x in primary_w]
    metadata["pitch_force_weights"] = [float(x) for x in pitch_w]
    metadata["feature_stats"] = feature_stats
    metadata["physics_model_stats"] = physics_stats
    metadata["window_offset_days"] = WINDOW_START_DAY[farm]
    metadata["window_rule"] = (
        "Earliest contiguous 245-day window with daily pitch-coverage >= 0.70 and daily "
        "regime-valid >= 0.70 (penmanshiel) / daily regime-valid >= 0.70 (kelmarsh). "
        "Selected on input observability masks only, before any model training."
    )
    metadata["window_pitch_coverage"] = float((physics[..., 1] != 0).mean())
    metadata["window_valid_rate"] = float(valid.mean())

    (dst / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"[{farm}] rebuilt: start day {WINDOW_START_DAY[farm]}, "
          f"pitch={metadata['window_pitch_coverage']:.3f}, valid={metadata['window_valid_rate']:.3f}, "
          f"class_weights={primary_w}")


if __name__ == "__main__":
    for farm in ("penmanshiel", "kelmarsh"):
        rebuild(farm)
    print("REBUILD_DONE")
