from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import Dataset

from .config import DataConfig
from .preprocess import preprocess_dataset
from .utils import load_json


@dataclass
class CacheBundle:
    cache_dir: Path
    metadata: dict[str, Any]
    features: np.ndarray
    feature_mask: np.ndarray
    target: np.ndarray
    target_mask: np.ndarray
    regime_primary: np.ndarray
    regime_primary_valid: np.ndarray
    regime_aux: np.ndarray | None
    regime_aux_valid: np.ndarray | None
    physics: np.ndarray
    physics_model: np.ndarray
    edge_index: np.ndarray
    edge_weight: np.ndarray
    coords: np.ndarray
    time_index: np.ndarray
    node_ids: np.ndarray


def ensure_cache_ready(config: DataConfig) -> Path:
    return preprocess_dataset(config)


def _optional_load(path: Path, mmap_mode: str | None, default: np.ndarray | None = None) -> np.ndarray | None:
    if path.exists():
        return np.load(path, mmap_mode=mmap_mode)
    return default


def load_cache_bundle(cache_dir: Path | str, mmap_mode: str | None = "r") -> CacheBundle:
    cache_dir = Path(cache_dir)
    metadata = load_json(cache_dir / "metadata.json")
    features = np.load(cache_dir / "features.npy", mmap_mode=mmap_mode)
    primary = np.load(cache_dir / "regime_primary.npy", mmap_mode=mmap_mode)
    primary_valid = np.load(cache_dir / "regime_primary_valid.npy", mmap_mode=mmap_mode)
    aux = _optional_load(cache_dir / "regime_aux.npy", mmap_mode)
    aux_valid = _optional_load(cache_dir / "regime_aux_valid.npy", mmap_mode)
    physics = np.load(cache_dir / "physics.npy", mmap_mode=mmap_mode)
    physics_model = _optional_load(cache_dir / "physics_model.npy", mmap_mode, default=physics)
    node_ids = _optional_load(
        cache_dir / "node_ids.npy",
        mmap_mode,
        default=np.arange(features.shape[1], dtype=np.int32),
    )
    return CacheBundle(
        cache_dir=cache_dir,
        metadata=metadata,
        features=features,
        feature_mask=np.load(cache_dir / "feature_mask.npy", mmap_mode=mmap_mode),
        target=np.load(cache_dir / "target.npy", mmap_mode=mmap_mode),
        target_mask=np.load(cache_dir / "target_mask.npy", mmap_mode=mmap_mode),
        regime_primary=primary,
        regime_primary_valid=primary_valid,
        regime_aux=aux,
        regime_aux_valid=aux_valid,
        physics=physics,
        physics_model=np.asarray(physics_model),
        edge_index=np.load(cache_dir / "edge_index.npy", mmap_mode=mmap_mode),
        edge_weight=np.load(cache_dir / "edge_weight.npy", mmap_mode=mmap_mode),
        coords=np.load(cache_dir / "coords.npy", mmap_mode=mmap_mode),
        time_index=np.load(cache_dir / "time_index.npy", mmap_mode=mmap_mode),
        node_ids=np.asarray(node_ids),
    )


class RegimeWindowDataset(Dataset):
    def __init__(self, bundle: CacheBundle, split: str, hist_len: int, pred_len: int) -> None:
        if split not in bundle.metadata.get("split_bounds", {}):
            raise ValueError(f"Unsupported split: {split}")
        self.bundle = bundle
        self.split = split
        self.hist_len = hist_len
        self.pred_len = pred_len
        start, end = bundle.metadata["split_bounds"][split]
        anchor_start = start + hist_len - 1
        anchor_end = end - pred_len - 1
        if anchor_end < anchor_start:
            self.anchor_indices = np.empty((0,), dtype=np.int64)
        else:
            self.anchor_indices = np.arange(anchor_start, anchor_end + 1, dtype=np.int64)

    def __len__(self) -> int:
        return int(self.anchor_indices.shape[0])

    def __getitem__(self, index: int) -> dict[str, Any]:
        anchor = int(self.anchor_indices[index])
        hist_slice = slice(anchor - self.hist_len + 1, anchor + 1)
        future_slice = slice(anchor + 1, anchor + 1 + self.pred_len)
        aux = self.bundle.regime_aux
        aux_valid = self.bundle.regime_aux_valid
        if aux is None:
            aux_anchor = np.full((self.bundle.features.shape[1],), -1, dtype=np.int64)
        else:
            aux_anchor = np.array(aux[anchor], dtype=np.int64, copy=True)
        if aux_valid is None:
            aux_anchor_valid = np.zeros((self.bundle.features.shape[1],), dtype=np.float32)
        else:
            aux_anchor_valid = np.array(aux_valid[anchor], dtype=np.float32, copy=True)
        return {
            "x_hist": torch.from_numpy(np.array(self.bundle.features[hist_slice], dtype=np.float32, copy=True)),
            "feature_mask_hist": torch.from_numpy(
                np.array(self.bundle.feature_mask[hist_slice], dtype=np.float32, copy=True)
            ),
            "edge_index_hist": torch.from_numpy(
                np.array(self.bundle.edge_index[hist_slice], dtype=np.int64, copy=True)
            ),
            "edge_weight_hist": torch.from_numpy(
                np.array(self.bundle.edge_weight[hist_slice], dtype=np.float32, copy=True)
            ),
            "target": torch.from_numpy(np.array(self.bundle.target[future_slice], dtype=np.float32, copy=True)),
            "target_mask": torch.from_numpy(
                np.array(self.bundle.target_mask[future_slice], dtype=np.float32, copy=True)
            ),
            "regime_primary": torch.from_numpy(
                np.array(self.bundle.regime_primary[anchor], dtype=np.int64, copy=True)
            ),
            "regime_primary_valid": torch.from_numpy(
                np.array(self.bundle.regime_primary_valid[anchor], dtype=np.float32, copy=True)
            ),
            "regime_aux": torch.from_numpy(aux_anchor),
            "regime_aux_valid": torch.from_numpy(aux_anchor_valid),
            "anchor_physics": torch.from_numpy(
                np.array(self.bundle.physics_model[anchor], dtype=np.float32, copy=True)
            ),
            "anchor_index": torch.tensor(anchor, dtype=torch.int64),
        }
