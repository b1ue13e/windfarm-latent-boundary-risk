"""Causal features and paired accounting for a separate development study.

These functions do not change the historical E04/E07 targets or selectors.
"""
from __future__ import annotations

import hashlib
from typing import Any

import numpy as np


def arrived_history(
    values: np.ndarray, anchors: np.ndarray, history_steps: int, delay_steps: int
) -> np.ndarray:
    """Mask unavailable observations inside an identical event-time window."""
    data = np.asarray(values)
    issue = np.asarray(anchors)
    if data.ndim != 3 or issue.ndim != 1 or issue.dtype.kind not in "iu":
        raise ValueError("Expected time/node/channel data and integer anchors")
    if history_steps < 1 or delay_steps < 0:
        raise ValueError("Invalid history or delay")
    if np.any(issue < 0) or np.any(issue >= len(data)):
        raise ValueError("Issue anchor outside observations")
    offsets = np.arange(history_steps - 1, -1, -1)
    source = issue[:, None] - offsets[None, :]
    observed = (source >= 0) & (source <= issue[:, None] - delay_steps)
    # Safe indexing is only an implementation detail: invalid slots stay NaN.
    gathered = np.asarray(data[np.maximum(source, 0)], dtype=np.float32)
    gathered[~observed] = np.nan
    return gathered.transpose(0, 2, 1, 3)


def sample_loss(
    shortfall: np.ndarray, reserve: np.ndarray, rho: float = 10.0, dt: float = 1 / 6
) -> np.ndarray:
    """Return procurement plus penalized unmet shortfall in kWh per cell."""
    s, r = np.asarray(shortfall, dtype=np.float64), np.asarray(reserve, dtype=np.float64)
    if s.shape != r.shape or not np.isfinite([rho, dt]).all() or rho <= 1 or dt <= 0:
        raise ValueError("Invalid shapes or loss parameters")
    if not np.isfinite(s).all() or not np.isfinite(r).all():
        raise ValueError("Nonfinite valid shortfall or reserve")
    if np.any(s < 0) or np.any(r < 0):
        raise ValueError("Shortfall and reserve must be nonnegative")
    return (r + rho * np.maximum(s - r, 0.0)) * dt


def block_totals(
    shortfall: np.ndarray,
    reserve: np.ndarray,
    mask: np.ndarray,
    anchor_indices: np.ndarray,
    steps_per_block: int = 144,
) -> dict[str, np.ndarray]:
    """Keep numerators and denominators separate for shared time-block inference."""
    s, r, valid, anchors = map(np.asarray, (shortfall, reserve, mask, anchor_indices))
    if s.ndim != 2 or s.shape != r.shape or valid.shape != s.shape:
        raise ValueError("Expected matching time/node arrays")
    if anchors.shape != (len(s),) or anchors.dtype.kind not in "iu":
        raise ValueError("Invalid anchor coordinates")
    if len(anchors) == 0 or np.any(np.diff(anchors) <= 0) or steps_per_block < 1:
        raise ValueError("Empty, duplicate, or unsorted anchors")
    if not np.isfinite(valid).all() or not np.isin(valid, [0, 1]).all():
        raise ValueError("Mask must be finite boolean or binary")
    valid = valid.astype(bool)
    if not valid.any():
        raise ValueError("No valid target cells")
    loss = sample_loss(s[valid], r[valid])
    s64, r64 = s.astype(np.float64), r.astype(np.float64)
    loss_grid = np.zeros(s.shape, dtype=np.float64)
    loss_grid[valid] = loss
    reserve_grid = np.where(valid, r64 / 6, 0.0)
    shortage_grid = np.where(valid, np.maximum(s64 - r64, 0.0) / 6, 0.0)
    violations = valid & (s64 > r64)
    ids = anchors // steps_per_block
    block_ids = np.unique(ids)
    result = {"block_ids": block_ids}
    for name, grid in (
        ("count", valid), ("loss_sum", loss_grid), ("reserve_sum", reserve_grid),
        ("shortage_sum", shortage_grid), ("violation_sum", violations),
    ):
        result[name] = np.asarray([grid[ids == block].sum(dtype=np.float64) for block in block_ids])
    return result


def paired_interval(
    numerators: np.ndarray,
    counts: np.ndarray,
    left: int,
    right: int,
    n_boot: int = 2000,
    block_span: int = 3,
    seed: int = 20261019,
    alpha: float = 0.05,
    family_size: int = 1,
) -> dict[str, Any]:
    """Circular moving-block interval conditional on the archived model seeds.

    Positive differences mean the left candidate has a higher metric. Counts
    weight each replicate; duplicating a seed does not create new weather.
    """
    data, count = np.asarray(numerators, dtype=np.float64), np.asarray(counts, dtype=np.float64)
    if data.ndim != 3 or count.shape != (data.shape[2],) or data.shape[0] < 1:
        raise ValueError("Expected seed/candidate/block numerators and shared counts")
    if not np.isfinite(data).all() or not np.isfinite(count).all() or np.any(count < 0) or count.sum() <= 0:
        raise ValueError("Invalid numerators or counts")
    if not (0 <= left < data.shape[1] and 0 <= right < data.shape[1]):
        raise ValueError("Candidate index out of bounds")
    if n_boot < 2 or not 1 <= block_span <= len(count) or not 0 < alpha < 1 or family_size < 1:
        raise ValueError("Invalid resampling configuration")
    rng = np.random.default_rng(seed)
    n_segments = (len(count) + block_span - 1) // block_span
    starts = rng.integers(0, len(count), size=(n_boot, n_segments))
    indices = ((starts[..., None] + np.arange(block_span)) % len(count)).reshape(n_boot, -1)[:, :len(count)]
    denominator = count[indices].sum(axis=1)
    if np.any(denominator <= 0):
        raise ValueError("Resampled window has no valid targets; no redraw permitted")
    # Average the frozen instances before temporal resampling. This also makes
    # an exact duplicate of every instance irrelevant to effective sample size.
    differences = (data[:, left] - data[:, right]).mean(axis=0)
    draws = differences[indices].sum(axis=1) / denominator
    point = differences.sum() / count.sum()
    return {
        "point": float(point),
        "ci95": np.quantile(draws, [alpha / 2, 1 - alpha / 2]).tolist(),
        "simultaneous_ci": np.quantile(draws, [alpha / (2 * family_size), 1 - alpha / (2 * family_size)]).tolist(),
        "bootstrap_indices_sha256": hashlib.sha256(indices.astype("<i8").tobytes()).hexdigest(),
        "n_boot": n_boot, "block_span": block_span, "resampling_seed": seed,
        "family_size": family_size, "unit": "kWh per valid turbine-interval for loss",
        "seed_inference": "conditional on archived instances; seeds not resampled",
        "coverage_status": "development approximation; not finite-sample certification",
    }


def validate_temporal_stages(
    stages: dict[str, tuple[int, int]], horizon: int, label_delay: int = 1
) -> None:
    """Require every preceding stage's final label to mature before the next."""
    if horizon < 1 or label_delay < 0 or not stages:
        raise ValueError("Invalid horizon, label delay or stages")
    previous_end = None
    for name, (start, end) in stages.items():
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or start >= end:
            raise ValueError(f"Invalid stage {name}")
        if previous_end is not None and previous_end - 1 + horizon + label_delay >= start:
            raise ValueError(f"Labels from preceding stage not mature before {name}")
        previous_end = end
