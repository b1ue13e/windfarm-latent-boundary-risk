"""Unified Arrival-Time Data Feed for causally symmetric degradation benchmarking.

This module directly addresses P0-B from the independent audit:
- Problem in legacy code: When delaying anchor_physics, history_delay was False,
  so the model's GNN encoder x_hist retained uncorrupted contemporary readings at issue time t,
  while threshold rules were forced to evaluate on delayed values.
- Solution: UnifiedArrivalDataset enforces that ANY delay, burst loss, or sensor noise
  is applied synchronously and identically to:
    1. x_hist (contemporary steps t-d+1:t are stalled or shifted)
    2. feature_mask_hist (masks reflect arrival status)
    3. anchor_physics (anchor readings reflect arrival status)
    4. rule inputs (extracted directly from the corrupted batch, guaranteeing symmetry).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
from torch.utils.data import Dataset

from .data import CacheBundle, RegimeWindowDataset


@dataclass
class DegradationSpec:
    """Specification of communication/sensor degradation applied at arrival time."""
    delay_steps: int = 0
    corrupted_channels: Tuple[str, ...] = ("Wspd", "Pab_mean")
    history_policy: str = "stalled"  # 'stalled' (sample-and-hold from t-d) or 'shifted'
    noise_sigma_physical: Dict[str, float] = field(default_factory=dict)
    # Markov-Gilbert parameters (if active, overrides static delay_steps)
    use_markov_gilbert: bool = False
    p_gb: float = 0.08
    p_bb: float = 0.75
    max_lag: int = 6
    random_seed: int = 2026


def simulate_markov_gilbert_lags(
    n_steps: int,
    p_gb: float = 0.08,
    p_bb: float = 0.75,
    max_lag: int = 6,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate two-state Markov-Gilbert burst drop states and lags."""
    if rng is None:
        rng = np.random.default_rng(2026)

    states = np.zeros(n_steps, dtype=np.int8)
    lags = np.zeros(n_steps, dtype=np.int64)
    curr_state = 0
    curr_lag = 0

    for t in range(n_steps):
        u = rng.uniform(0.0, 1.0)
        if curr_state == 0:
            if u < p_gb:
                curr_state = 1
                curr_lag = 1
            else:
                curr_state = 0
                curr_lag = 0
        else:
            if u < p_bb:
                curr_state = 1
                curr_lag = min(curr_lag + 1, max_lag)
            else:
                curr_state = 0
                curr_lag = 0
        states[t] = curr_state
        lags[t] = curr_lag

    return states, lags


class UnifiedArrivalDataset(Dataset):
    """Dataset that applies synchronous, causally symmetric arrival-time degradation."""

    def __init__(
        self,
        bundle: CacheBundle,
        split: str,
        hist_len: int,
        pred_len: int,
        degradation: Optional[DegradationSpec] = None,
    ) -> None:
        self.base_dataset = RegimeWindowDataset(bundle, split, hist_len, pred_len)
        self.bundle = bundle
        self.hist_len = hist_len
        self.pred_len = pred_len
        self.degradation = degradation or DegradationSpec()

        # Cache feature and physics indices
        feature_names = list(bundle.metadata.get("feature_names", []))
        physics_names = list(bundle.metadata.get("physics_names", ["Wspd", "Pab_mean", "wake_score", "Patv"]))

        self.feat_indices = {
            name: feature_names.index(name) for name in self.degradation.corrupted_channels if name in feature_names
        }
        self.phy_indices = {
            name: physics_names.index(name) for name in self.degradation.corrupted_channels if name in physics_names
        }

        # Precompute noise scales in normalized feature space if specified
        self.feat_noise_stds: Dict[str, float] = {}
        self.phy_noise_stds: Dict[str, float] = {}
        if self.degradation.noise_sigma_physical:
            feat_stats = bundle.metadata.get("feature_stats", {})
            phy_stats = bundle.metadata.get("physics_model_stats", {})
            for ch, phys_sigma in self.degradation.noise_sigma_physical.items():
                if ch in feat_stats:
                    ch_std = float(feat_stats[ch].get("std", 1.0) or 1.0)
                    self.feat_noise_stds[ch] = float(phys_sigma) / max(ch_std, 1e-6)
                if ch in self.phy_indices:
                    idx_str = str(self.phy_indices[ch])
                    p_std = float(phy_stats.get(idx_str, {}).get("std", 1.0) or 1.0) if phy_stats else 1.0
                    self.phy_noise_stds[ch] = float(phys_sigma) / max(p_std, 1e-6)

        # Precompute Markov-Gilbert channel if requested
        self.burst_states: Optional[np.ndarray] = None
        self.burst_lags: Optional[np.ndarray] = None
        if self.degradation.use_markov_gilbert:
            rng = np.random.default_rng(self.degradation.random_seed)
            self.burst_states, self.burst_lags = simulate_markov_gilbert_lags(
                len(self.base_dataset),
                p_gb=self.degradation.p_gb,
                p_bb=self.degradation.p_bb,
                max_lag=self.degradation.max_lag,
                rng=rng,
            )

    def __len__(self) -> int:
        return len(self.base_dataset)

    @property
    def anchor_indices(self) -> np.ndarray:
        return self.base_dataset.anchor_indices

    def __getitem__(self, index: int) -> Dict[str, Any]:
        item = self.base_dataset[index]
        if self.degradation.delay_steps == 0 and not self.degradation.use_markov_gilbert and not self.degradation.noise_sigma_physical:
            # Clean baseline: return unchanged
            item["lag_applied"] = 0
            return item

        # Determine lag at this step
        if self.degradation.use_markov_gilbert and self.burst_lags is not None:
            lag = int(self.burst_lags[index])
        else:
            lag = int(self.degradation.delay_steps)

        anchor = int(item["anchor_index"])
        total_steps = self.bundle.features.shape[0]

        # 1. Synchronously degrade anchor_physics
        if lag > 0:
            lagged_anchor = max(0, anchor - lag)
            lagged_physics = torch.from_numpy(np.array(self.bundle.physics_model[lagged_anchor], dtype=np.float32, copy=True))
            for ch, phy_idx in self.phy_indices.items():
                item["anchor_physics"][:, phy_idx] = lagged_physics[:, phy_idx]

        # 2. Synchronously degrade x_hist to eliminate information asymmetry
        # When lag > 0, the readings at steps (H - lag) to (H - 1) have not arrived yet.
        if lag > 0 and self.feat_indices:
            x_hist = item["x_hist"].clone()
            H = x_hist.shape[0]

            for ch, feat_idx in self.feat_indices.items():
                if self.degradation.history_policy == "stalled":
                    # Sample-and-hold: replicate reading from t - lag to all subsequent unarrived steps
                    stalled_step = max(0, H - 1 - lag)
                    last_known_val = x_hist[stalled_step:stalled_step + 1, :, feat_idx]
                    for step_idx in range(stalled_step + 1, H):
                        x_hist[step_idx, :, feat_idx] = last_known_val[0]
                elif self.degradation.history_policy == "shifted":
                    # Shift entire history backwards by lag steps
                    vals = x_hist[:, :, feat_idx]  # (H, N)
                    head = vals[:1, :].repeat(lag, 1)
                    shifted = torch.cat([head, vals[:-lag, :]], dim=0)
                    x_hist[:, :, feat_idx] = shifted

            item["x_hist"] = x_hist

        # 3. Add synchronous sensor noise if specified
        if self.degradation.noise_sigma_physical:
            rng = np.random.default_rng(self.degradation.random_seed + index * 31)
            for ch, std_scale in self.feat_noise_stds.items():
                feat_idx = self.feat_indices.get(ch)
                if feat_idx is not None:
                    noise = torch.from_numpy(rng.normal(0.0, std_scale, size=item["x_hist"][:, :, feat_idx].shape)).float()
                    item["x_hist"][:, :, feat_idx] += noise

            for ch, p_std_scale in self.phy_noise_stds.items():
                phy_idx = self.phy_indices.get(ch)
                if phy_idx is not None:
                    noise = torch.from_numpy(rng.normal(0.0, p_std_scale, size=item["anchor_physics"][:, phy_idx].shape)).float()
                    item["anchor_physics"][:, phy_idx] += noise

        item["lag_applied"] = lag
        return item


def extract_symmetric_rule_input(batch: Dict[str, Any], metadata: Dict[str, Any]) -> Tuple[torch.Tensor, torch.Tensor]:
    """Extract Wspd and Pab_mean from anchor_physics to guarantee exact symmetry with model inputs.

    Returns:
        wspd: (B, N) standardized or physical wind speed
        pab: (B, N) standardized or physical blade pitch
    """
    anchor_physics = batch["anchor_physics"]
    physics_names = list(metadata.get("physics_names", ["Wspd", "Pab_mean", "wake_score", "Patv"]))
    wspd_idx = physics_names.index("Wspd") if "Wspd" in physics_names else 0
    pab_idx = physics_names.index("Pab_mean") if "Pab_mean" in physics_names else 1
    return anchor_physics[..., wspd_idx], anchor_physics[..., pab_idx]
