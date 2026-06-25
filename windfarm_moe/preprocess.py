from __future__ import annotations

import os
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import WTB_FEATURE_NAMES, DataConfig
from .external_wind import ExternalWindConfig, preprocess_external_wind
from .graph import build_dynamic_graph, build_static_candidates
from .regimes import (
    WTB_AUX_NAMES,
    WTB_PRIMARY_NAMES,
    compute_wtb_operation_regime,
    compute_wtb_wake_flag,
    inverse_frequency_weights_from_labels,
)
from .utils import (
    build_slot_map,
    ensure_dir,
    fill_with_train_mean,
    save_json,
    standardize,
    wrap_degrees,
)


RAW_COLUMNS = ["Wspd", "Wdir", "Etmp", "Itmp", "Ndir", "Pab1", "Pab2", "Pab3", "Prtv", "Patv"]


def preprocess_dataset(config: DataConfig) -> Path:
    if config.dataset == "wtb":
        return _preprocess_wtb(config)
    if config.dataset == "era5":
        return _preprocess_era5(config)
    if config.dataset == "external_wind":
        return preprocess_external_wind(ExternalWindConfig.from_data_config(config))
    raise ValueError(f"Unsupported dataset: {config.dataset}")


def _preprocess_era5(config: DataConfig) -> Path:
    cache_dir = ensure_dir(config.cache_dir())
    required = ["metadata.json", "features.npy", "physics.npy", "physics_model.npy", "regime_primary.npy"]
    if all((cache_dir / name).exists() for name in required):
        return cache_dir

    helper_python = config.discover_era5_python()
    if helper_python is None:
        raise RuntimeError("Could not find a Python interpreter capable of reading ERA5 NetCDF files.")

    root_dir = Path(config.root_dir).resolve()
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(root_dir) if not existing_pythonpath else f"{root_dir}{os.pathsep}{existing_pythonpath}"
    command = [
        str(helper_python),
        str(root_dir / "windfarm_moe" / "era5_worker.py"),
        "--root-dir",
        str(root_dir),
        "--output-dir",
        str(cache_dir.resolve()),
        "--zip-pattern",
        config.era5_zip_pattern,
        "--patch-size",
        str(config.era5_patch_size),
        "--hist-len",
        str(config.hist_len),
        "--pred-len",
        str(config.pred_len),
        "--candidate-k",
        str(config.era5_candidate_k),
    ]
    if config.era5_max_archives is not None:
        command.extend(["--max-archives", str(config.era5_max_archives)])
    subprocess.run(command, cwd=str(root_dir), check=True, env=env)
    return cache_dir


def _stream_raw_arrays(config: DataConfig) -> dict[str, np.ndarray]:
    total_steps = config.total_steps()
    slot_map = build_slot_map(config.slots_per_day)
    buffers = {
        column: np.full((total_steps, config.num_turbines), np.nan, dtype=np.float32) for column in RAW_COLUMNS
    }
    file_path = Path(config.root_dir) / config.dynamic_file
    usecols = ["TurbID", "Day", "Tmstamp", *RAW_COLUMNS]
    for chunk in pd.read_csv(file_path, usecols=usecols, chunksize=config.preprocess_chunk_size):
        chunk = chunk[chunk["Day"] <= config.total_days()]
        if chunk.empty:
            continue
        time_index = (
            (chunk["Day"].to_numpy(dtype=np.int32) - 1) * config.slots_per_day
            + chunk["Tmstamp"].map(slot_map).to_numpy(dtype=np.int32)
        )
        turb_index = chunk["TurbID"].to_numpy(dtype=np.int32) - 1
        for column in RAW_COLUMNS:
            values = pd.to_numeric(chunk[column], errors="coerce").to_numpy(dtype=np.float32)
            buffers[column][time_index, turb_index] = values
    return buffers


def _prepare_wtb_channels(
    raw_channels: dict[str, np.ndarray],
    train_stop: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any], dict[str, np.ndarray]]:
    feature_arrays: list[np.ndarray] = []
    feature_masks: list[np.ndarray] = []
    stats: dict[str, Any] = {}
    filled_channels: dict[str, np.ndarray] = {}

    for feature_name in WTB_FEATURE_NAMES:
        raw_values = raw_channels[feature_name]
        mask = np.isfinite(raw_values).astype(np.float32)
        filled, fill_mean = fill_with_train_mean(raw_values, train_stop)
        standardized, mean, std = standardize(filled, train_stop)
        feature_arrays.append(standardized)
        feature_masks.append(mask)
        filled_channels[feature_name] = filled.astype(np.float32)
        stats[feature_name] = {
            "fill_mean": fill_mean,
            "mean": mean,
            "std": std,
        }

    features = np.stack(feature_arrays, axis=-1).astype(np.float32)
    feature_mask = np.stack(feature_masks, axis=-1).astype(np.float32)
    return features, feature_mask, stats, filled_channels


def _save_common_arrays(cache_dir: Path, arrays: dict[str, np.ndarray]) -> None:
    for name, values in arrays.items():
        np.save(cache_dir / f"{name}.npy", values)


def _standardize_physics_stack(physics: np.ndarray, train_stop: int) -> tuple[np.ndarray, dict[str, dict[str, float]]]:
    standardized = np.zeros_like(physics, dtype=np.float32)
    stats: dict[str, dict[str, float]] = {}
    for idx in range(physics.shape[-1]):
        filled, _ = fill_with_train_mean(physics[..., idx], train_stop)
        normalized, mean, std = standardize(filled, train_stop)
        standardized[..., idx] = normalized
        stats[str(idx)] = {"mean": mean, "std": std}
    return standardized.astype(np.float32), stats


def _preprocess_wtb(config: DataConfig) -> Path:
    cache_dir = ensure_dir(config.cache_dir())
    required = ["metadata.json", "features.npy", "physics.npy", "physics_model.npy", "regime_primary.npy"]
    if all((cache_dir / name).exists() for name in required):
        return cache_dir

    raw = _stream_raw_arrays(config)
    locations = pd.read_csv(Path(config.root_dir) / config.location_file).sort_values("TurbID")
    coords = locations[["x", "y"]].to_numpy(dtype=np.float32)
    node_ids = locations["TurbID"].to_numpy(dtype=np.int32)
    candidates = build_static_candidates(coords, config.candidate_k, config.max_distance)

    target = raw["Patv"].astype(np.float32)
    target_mask = (np.isfinite(target) & (target > 0.0)).astype(np.float32)
    train_stop = config.train_steps()

    wdir_wrapped = wrap_degrees(raw["Wdir"])
    ndir_wrapped = wrap_degrees(raw["Ndir"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        pab_stack = np.stack([raw["Pab1"], raw["Pab2"], raw["Pab3"]], axis=0)
        pab_mean_raw = np.nanmean(pab_stack, axis=0).astype(np.float32)
        pab_std_raw = np.nanstd(pab_stack, axis=0).astype(np.float32)

    raw_feature_channels = {
        "Wspd": raw["Wspd"],
        "Wdir_sin": np.where(np.isfinite(wdir_wrapped), np.sin(np.deg2rad(wdir_wrapped)), np.nan).astype(np.float32),
        "Wdir_cos": np.where(np.isfinite(wdir_wrapped), np.cos(np.deg2rad(wdir_wrapped)), np.nan).astype(np.float32),
        "Ndir_sin": np.where(np.isfinite(ndir_wrapped), np.sin(np.deg2rad(ndir_wrapped)), np.nan).astype(np.float32),
        "Ndir_cos": np.where(np.isfinite(ndir_wrapped), np.cos(np.deg2rad(ndir_wrapped)), np.nan).astype(np.float32),
        "Etmp": raw["Etmp"],
        "Itmp": raw["Itmp"],
        "Pab_mean": pab_mean_raw,
        "Pab_std": pab_std_raw,
        "Prtv": raw["Prtv"],
        "Patv_hist": np.where(target_mask > 0.0, raw["Patv"], np.nan).astype(np.float32),
    }
    features, feature_mask, feature_stats, filled = _prepare_wtb_channels(raw_feature_channels, train_stop)

    edge_index, edge_weight, wake_score = build_dynamic_graph(
        wdir_wrapped,
        candidates,
        max_in_edges=config.max_in_edges,
        cone_half_angle_deg=config.cone_half_angle_deg,
        parallel_scale=config.parallel_scale,
        cross_scale=config.cross_scale,
        direction_is_from=config.direction_is_from,
        chunk_size=config.graph_chunk_size,
    )

    op_regime, op_valid = compute_wtb_operation_regime(raw["Wspd"], pab_mean_raw)
    anchor_observed = np.isfinite(raw["Wspd"]) & np.isfinite(pab_mean_raw)
    op_regime = np.where(anchor_observed, op_regime, 3).astype(np.int16)
    op_valid = (op_valid.astype(bool) & anchor_observed).astype(np.float32)
    wake_flag, wake_valid, wake_threshold = compute_wtb_wake_flag(wake_score, op_regime, train_stop)
    primary_class_weights = inverse_frequency_weights_from_labels(op_regime, op_valid, 3)
    pitch_binary_labels = np.zeros_like(op_regime, dtype=np.int16)
    pitch_valid = ((op_regime == 1) | (op_regime == 2)).astype(np.float32)
    pitch_binary_labels[op_regime == 2] = 1
    pitch_force_weights = inverse_frequency_weights_from_labels(pitch_binary_labels, pitch_valid, 2)

    wake_valid_mask = wake_valid.astype(bool)
    if wake_valid_mask.any():
        wake_train = wake_flag[:train_stop][wake_valid_mask[:train_stop]]
        pos_count = float((wake_train == 1).sum())
        neg_count = float((wake_train == 0).sum())
        wake_pos_weight = neg_count / max(pos_count, 1.0)
    else:
        wake_pos_weight = 1.0

    physics = np.stack(
        [
            filled["Wspd"],
            filled["Pab_mean"],
            wake_score.astype(np.float32),
            np.nan_to_num(target, nan=0.0).astype(np.float32),
        ],
        axis=-1,
    ).astype(np.float32)
    physics_model, physics_model_stats = _standardize_physics_stack(physics, train_stop)

    day_index = np.repeat(np.arange(1, config.total_days() + 1, dtype=np.int16), config.slots_per_day)
    slot_index = np.tile(np.arange(config.slots_per_day, dtype=np.int16), config.total_days())
    time_index = np.stack([day_index, slot_index], axis=-1)
    effective_train_days, effective_val_days, effective_test_days, effective_holdout_days = config.effective_day_split()

    _save_common_arrays(
        cache_dir,
        {
            "features": features,
            "feature_mask": feature_mask,
            "target": target.astype(np.float32),
            "target_mask": target_mask.astype(np.float32),
            "regime_primary": op_regime.astype(np.int16),
            "regime_primary_valid": op_valid.astype(np.float32),
            "regime_aux": wake_flag.astype(np.int16),
            "regime_aux_valid": wake_valid.astype(np.float32),
            "physics": physics,
            "physics_model": physics_model,
            "edge_index": edge_index.astype(np.int16),
            "edge_weight": edge_weight.astype(np.float32),
            "coords": coords.astype(np.float32),
            "time_index": time_index,
            "node_ids": node_ids.astype(np.int32),
        },
    )

    metadata = {
        "dataset": "wtb",
        "num_steps": int(config.total_steps()),
        "num_nodes": int(config.num_turbines),
        "feature_names": list(WTB_FEATURE_NAMES),
        "physics_names": ["Wspd", "Pab_mean", "wake_score", "Patv"],
        "primary_regime_names": list(WTB_PRIMARY_NAMES),
        "aux_regime_names": list(WTB_AUX_NAMES),
        "primary_num_classes": 3,
        "wake_expert_index": 3,
        "steps_per_hour": 6,
        "split_bounds": {k: list(v) for k, v in config.split_bounds().items()},
        "train_days": effective_train_days,
        "val_days": effective_val_days,
        "test_days": effective_test_days,
        "holdout_days": effective_holdout_days,
        "hist_len": config.hist_len,
        "pred_len": config.pred_len,
        "feature_stats": feature_stats,
        "physics_model_stats": physics_model_stats,
        "primary_class_weights": primary_class_weights,
        "pitch_force_weights": pitch_force_weights,
        "wake_pos_weight": wake_pos_weight,
        "wake_threshold": wake_threshold,
        "graph_config": {
            "candidate_k": config.candidate_k,
            "max_distance": config.max_distance,
            "max_in_edges": config.max_in_edges,
            "cone_half_angle_deg": config.cone_half_angle_deg,
            "parallel_scale": config.parallel_scale,
            "cross_scale": config.cross_scale,
            "direction_is_from": config.direction_is_from,
        },
    }
    save_json(cache_dir / "metadata.json", metadata)
    return cache_dir
