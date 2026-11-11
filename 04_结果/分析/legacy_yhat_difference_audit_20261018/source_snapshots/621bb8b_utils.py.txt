from __future__ import annotations

import json
import math
import os
import random
from pathlib import Path
from typing import Iterable

import numpy as np


def ensure_dir(path: Path | str) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_json(path: Path | str, payload: dict) -> None:
    path = Path(path)
    ensure_dir(path.parent)

    def _default(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, Path):
            return str(obj)
        raise TypeError(f"Object of type {type(obj)!r} is not JSON serializable")

    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True, default=_default)
        handle.write("\n")
    os.replace(tmp_path, path)


def load_json(path: Path | str) -> dict:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def seed_everything(seed: int) -> None:
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def build_slot_map(slots_per_day: int = 144) -> dict[str, int]:
    slot_map: dict[str, int] = {}
    for idx in range(slots_per_day):
        minutes = idx * 10
        hour = minutes // 60
        minute = minutes % 60
        slot_map[f"{hour:02d}:{minute:02d}"] = idx
    return slot_map


def wrap_degrees(values: np.ndarray) -> np.ndarray:
    wrapped = np.array(values, copy=True, dtype=np.float32)
    finite = np.isfinite(wrapped)
    wrapped[finite] = ((wrapped[finite] + 180.0) % 360.0) - 180.0
    return wrapped


def forward_fill_2d(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32)
    result = values.copy()
    missing = np.isnan(result)
    if not missing.any():
        return result
    row_indices = np.where(~missing, np.arange(result.shape[0], dtype=np.int32)[:, None], 0)
    np.maximum.accumulate(row_indices, axis=0, out=row_indices)
    col_indices = np.arange(result.shape[1], dtype=np.int32)[None, :]
    result = result[row_indices, col_indices]
    return result


def fill_with_train_mean(values: np.ndarray, train_stop: int) -> tuple[np.ndarray, float]:
    filled = forward_fill_2d(values)
    train_values = filled[:train_stop]
    finite_train = train_values[np.isfinite(train_values)]
    if finite_train.size == 0:
        train_mean = 0.0
    else:
        train_mean = float(finite_train.mean())
    filled = np.where(np.isfinite(filled), filled, train_mean)
    return filled.astype(np.float32), train_mean


def standardize(values: np.ndarray, train_stop: int) -> tuple[np.ndarray, float, float]:
    train_mean = float(values[:train_stop].mean())
    train_std = float(values[:train_stop].std())
    train_std = train_std if train_std > 1e-6 else 1.0
    normalized = ((values - train_mean) / train_std).astype(np.float32)
    return normalized, train_mean, train_std


def inverse_frequency_weights(counts: Iterable[int]) -> list[float]:
    counts_arr = np.asarray(list(counts), dtype=np.float64)
    safe = np.where(counts_arr > 0, counts_arr, 1.0)
    inv = safe.sum() / (len(safe) * safe)
    inv = inv / inv.mean()
    return inv.astype(np.float32).tolist()


def to_device(batch: dict, device: torch.device) -> dict:
    import torch

    moved = {}
    for key, value in batch.items():
        if isinstance(value, torch.Tensor):
            moved[key] = value.to(device)
        else:
            moved[key] = value
    return moved
