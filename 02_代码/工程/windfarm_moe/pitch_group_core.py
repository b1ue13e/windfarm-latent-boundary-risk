"""Causal features and accounting for the fixed-membership pitch group study.

No estimator fitting, measurement I/O, model I/O or inference occurs here.
Features use only completed records through each issue.  Target validity is
consumed separately, for retrospective scoring or after a label has matured.
"""
from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Any

import numpy as np


FEATURE_ARMS = ("P", "Z0", "ZD")
DYNAMIC_NAMES = ("delta1", "delta6", "ols_slope6", "detrended_std6",
                 "max_drawdown6", "trailing_negative_count6")
REGIME_LOW, REGIME_HIGH, REGIME_UNKNOWN = 0, 1, 2


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if (isinstance(value, (bool, np.bool_))
            or not isinstance(value, (int, np.integer)) or int(value) < minimum):
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return int(value)


def _anchors(anchors: np.ndarray, *, first: int = 0, last: int | None = None) -> np.ndarray:
    raw = np.asarray(anchors)
    if raw.ndim != 1 or raw.dtype.kind not in "iu" or raw.size == 0:
        raise ValueError("anchors must be a nonempty integer vector")
    a = raw.astype(np.int64, copy=False)
    if (np.any(np.diff(a) <= 0) or a[0] < first
            or (last is not None and a[-1] >= last)):
        raise ValueError("anchors must be strictly increasing and in bounds")
    return a


def _coordinates(data: np.ndarray, anchors: np.ndarray, forecast: np.ndarray,
                 *, history: int = 1, future: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = np.asarray(data)
    if values.ndim != 3 or values.shape[1] < 1 or values.shape[2] != 4:
        raise ValueError("Expected data[time, member, W/P/Q/Z]")
    a = _anchors(anchors, first=history - 1, last=len(values) - future)
    f = np.asarray(forecast, dtype=np.float64)
    if f.shape != (len(a), values.shape[1]):
        raise ValueError("forecast must match issue/member coordinates")
    return values, a, f


def _dynamics(history: np.ndarray) -> np.ndarray:
    """Six summaries, each preserving its own fixed required-value support.

    history is [issue, member, at least seven chronological values].  Delta1
    needs two endpoints, delta6 needs current and t-6; the remaining summaries
    need all six latest values.  No summary searches backwards past a missing
    observation.  The formula matches the existing six-feature add-back design.
    """
    p = np.asarray(history, dtype=np.float64)
    tail = p[..., -6:]
    delta1 = p[..., -1] - p[..., -2]
    delta6 = p[..., -1] - p[..., -7]
    delta1 = np.where(np.isfinite(p[..., -1]) & np.isfinite(p[..., -2]), delta1, np.nan)
    delta6 = np.where(np.isfinite(p[..., -1]) & np.isfinite(p[..., -7]), delta6, np.nan)
    valid = np.isfinite(tail).all(axis=-1)
    work = np.where(np.isfinite(tail), tail, 0.)
    mean = work.mean(axis=-1)
    centred_time = np.arange(6, dtype=np.float64) - 2.5
    slope = ((work - mean[..., None]) * centred_time).sum(axis=-1) / 17.5
    detrended = work - mean[..., None] - slope[..., None] * centred_time
    std = np.sqrt(np.mean(detrended ** 2, axis=-1))
    drawdown = (np.maximum.accumulate(work, axis=-1) - work).max(axis=-1)
    changes = np.diff(work, axis=-1)
    run = np.zeros(work.shape[:-1], dtype=np.float64)
    still_negative = np.ones(work.shape[:-1], dtype=bool)
    for index in range(4, -1, -1):
        still_negative &= changes[..., index] < 0.
        run += still_negative
    return np.stack((delta1, delta6, np.where(valid, slope, np.nan),
                     np.where(valid, std, np.nan), np.where(valid, drawdown, np.nan),
                     np.where(valid, run, np.nan)), axis=-1)


def build_group_features(data: np.ndarray, anchors: np.ndarray, forecast: np.ndarray,
                         arm: str = "P", history: int = 36,
                         node_ids: Sequence[Any] | None = None,
                         expected_node_ids: Sequence[Any] | None = None,
                         ) -> tuple[np.ndarray, list[str]]:
    """Return [issue, feature] float32 covariates and their unique column names.

    P columns are a byte-identical prefix in Z0 and ZD.  Member count is taken
    from data, allowing small independently checkable fixtures; the real input
    source/runner separately requires the frozen 134-member identity.  NaN is
    retained for downstream training-only preprocessing; infinities in consumed
    observations are represented as missing.  Neither targets nor masks are
    accepted by this API, and future observations are never indexed.
    """
    h = _integer(history, "history", 7)
    if arm not in FEATURE_ARMS:
        raise ValueError(f"Unknown feature arm: {arm}")
    values, a, f = _coordinates(data, anchors, forecast, history=h)
    n = values.shape[1]
    ids = [str(i) for i in range(n)] if node_ids is None else [str(i) for i in node_ids]
    if len(ids) != n or len(set(ids)) != n:
        raise ValueError("node_ids must contain one unique identity per member")
    if expected_node_ids is not None and ids != [str(i) for i in expected_node_ids]:
        raise ValueError("Frozen member order/identity differs")
    source = a[:, None] - np.arange(h - 1, -1, -1)[None, :]
    # Advanced indexing reads only at-or-before-issue event-time rows.
    hist = np.asarray(values[source], dtype=np.float64).transpose(0, 2, 3, 1)
    hist = np.where(np.isfinite(hist), hist, np.nan)
    f = np.where(np.isfinite(f), f, np.nan)
    phase = 2. * np.pi * (a % 144) / 144.
    parts = [f, f.sum(axis=1, dtype=np.float64)[:, None],
             np.sin(phase)[:, None], np.cos(phase)[:, None],
             hist[:, :, :3, :].reshape(len(a), -1)]
    columns = [f"forecast:{i}" for i in ids] + ["forecast_sum", "clock_sin", "clock_cos"]
    columns += [f"{channel}:{member}:lag{lag}" for member in ids
                for channel in ("W", "P", "Q") for lag in range(h - 1, -1, -1)]
    for channel, index in (("P", 1), ("Q", 2)):
        parts.append(_dynamics(hist[:, :, index, :]).reshape(len(a), -1))
        columns += [f"{channel}:{member}:{name}" for member in ids for name in DYNAMIC_NAMES]
    if arm in ("Z0", "ZD"):
        parts.append(hist[:, :, 3, -1])
        columns += [f"Z:{member}:current" for member in ids]
    if arm == "ZD":
        parts.append(_dynamics(hist[:, :, 3, :]).reshape(len(a), -1))
        columns += [f"Z:{member}:{name}" for member in ids for name in DYNAMIC_NAMES]
    matrix = np.ascontiguousarray(np.column_stack(parts), dtype=np.float32)
    if matrix.shape != (len(a), len(columns)) or len(columns) != len(set(columns)):
        raise AssertionError("Feature schema lost its fixed member/channel alignment")
    if np.isinf(matrix).any():
        raise ValueError("Consumed finite feature exceeds float32 representable range")
    return matrix, columns


def group_target_masks(data: np.ndarray, anchors: np.ndarray, forecast: np.ndarray,
                       horizon: int = 6, high_wind: float = 10.5) -> dict[str, np.ndarray]:
    """Construct retrospective group S/target-mask/pair-mask and current regime.

    Pair completeness does not select group membership, alter covariates or
    control actions.  The Z channel is assumed already to require three finite
    blade angles at its upstream producer; provenance must establish that fact.
    Missing future power produces a NaN S, never a zero target.  W missingness
    creates an unknown regime and does not remove a primary scoring observation.
    """
    ahead = _integer(horizon, "horizon", 1)
    if not np.isfinite(high_wind):
        raise ValueError("Nonfinite regime boundary")
    values, a, f = _coordinates(data, anchors, forecast, future=ahead)
    y = np.asarray(values[a + ahead, :, 1], dtype=np.float64)
    target = np.isfinite(f).all(axis=1) & np.isfinite(y).all(axis=1)
    signed = (f - y).sum(axis=1, dtype=np.float64)
    shortfall = np.where(target, np.maximum(signed, 0.), np.nan)
    pair = (target & np.isfinite(values[a, :, 1]).all(axis=1)
            & np.isfinite(values[a, :, 3]).all(axis=1))
    wind = np.asarray(values[a, :, 0], dtype=np.float64)
    wind_valid = np.isfinite(wind).all(axis=1)
    wind_mean = np.where(wind_valid, wind.mean(axis=1), np.nan)
    regime = np.full(len(a), REGIME_UNKNOWN, dtype=np.int8)
    regime[wind_valid] = (wind_mean[wind_valid] >= high_wind).astype(np.int8)
    return dict(shortfall=shortfall, target_mask=target, pair_mask=pair,
                signed_group_error=np.where(target, signed, np.nan),
                group_wind=wind_mean, regime=regime)


def rolling_residual_actions(raw_cond: np.ndarray, targets: np.ndarray,
                             anchors: np.ndarray, target_valid: np.ndarray,
                             initial_offset: float, q: float = .925,
                             window: int = 144, lag: int = 7,
                             ) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Causal rolling signed-offset actions and an auditable maturity trace.

    At issue t the residual window contains original issue times s >= t-window
    and s+lag < t.  It is not the last `window` available labels, and gaps are
    never filled.  Validity/target values are read only for matured sources.
    Pass the complete ordered warmup/selection/evaluation stream together to
    carry state across stage boundaries.  No scoring-pair mask is accepted.
    """
    width, release = _integer(window, "window", 1), _integer(lag, "lag", 0)
    a = _anchors(anchors)
    raw = np.asarray(raw_cond, dtype=np.float64)
    y = np.asarray(targets, dtype=np.float64)
    valid = np.asarray(target_valid)
    if (raw.shape != a.shape or y.shape != a.shape or valid.shape != a.shape
            or valid.dtype != bool):
        raise ValueError("Expected aligned 1D scores, targets and boolean target validity")
    if not np.isfinite(initial_offset) or not np.isfinite(q) or not 0. <= q <= 1.:
        raise ValueError("Invalid initial offset or quantile")
    action = np.empty(len(a), dtype=np.float64)
    offsets = np.empty(len(a), dtype=np.float64)
    support = np.zeros(len(a), dtype=np.int64)
    first_source = np.full(len(a), -1, dtype=np.int64)
    last_source = np.full(len(a), -1, dtype=np.int64)
    for index, issue in enumerate(a):
        if not np.isfinite(raw[index]):
            raise ValueError(f"Nonfinite score at issue {int(issue)}")
        left = int(np.searchsorted(a, issue - width, side="left"))
        right = min(index, int(np.searchsorted(a, issue - release, side="left")))
        source = np.arange(left, right, dtype=np.int64)
        # Source validity is inspected only after the strict release barrier.
        source = source[valid[source]]
        correction = float(initial_offset)
        if source.size:
            if (not np.isfinite(y[source]).all() or np.any(y[source] < 0.)
                    or not np.isfinite(raw[source]).all()):
                raise ValueError("Matured valid targets/scores must be finite, targets nonnegative")
            correction = float(np.quantile(y[source] - raw[source], q, method="higher"))
            support[index] = source.size
            first_source[index], last_source[index] = a[source[0]], a[source[-1]]
        offsets[index] = correction
        action[index] = max(float(raw[index]) + correction, 0.)
    return action, dict(offset=offsets, support=support,
                        first_source_anchor=first_source, last_source_anchor=last_source,
                        used_fallback=support == 0)


def account_group(action: np.ndarray, shortfall: np.ndarray, pair_mask: np.ndarray,
                  anchors: np.ndarray) -> dict[str, np.ndarray]:
    """Full-calendar daily C/R/U/V sums and counts for one fixed group policy.

    Output ledger columns are C,R,U,V.  Zero-count days remain placeholders;
    whether an endpoint is estimable is the inference layer's separate duty.
    Every action must exist before the retrospective mask is applied.
    """
    a = _anchors(anchors)
    r, s, mask = np.asarray(action, dtype=np.float64), np.asarray(shortfall, dtype=np.float64), np.asarray(pair_mask)
    if r.shape != a.shape or s.shape != a.shape or mask.shape != a.shape or mask.dtype != bool:
        raise ValueError("Expected aligned 1D group action, target and boolean mask")
    if not np.isfinite(r).all() or np.any(r < 0.):
        raise ValueError("Actions must be finite and nonnegative for every issue")
    if not np.isfinite(s[mask]).all() or np.any(s[mask] < 0.):
        raise ValueError("Scored group shortfall must be finite and nonnegative")
    day_ids = a // 144
    days = np.arange(day_ids[0], day_ids[-1] + 1, dtype=np.int64)
    dense_day = day_ids - days[0]
    observed_s = np.where(mask, s, 0.)
    reserve = np.where(mask, r / 6., 0.)
    uncovered = np.where(mask, np.maximum(observed_s - r, 0.) / 6., 0.)
    event = mask & (observed_s > r)
    values = (reserve + 10. * uncovered, reserve, uncovered, event)
    ledger = np.column_stack([np.bincount(dense_day, weights=value,
                              minlength=len(days)) for value in values]).astype(np.float64)
    counts = np.bincount(dense_day, weights=mask, minlength=len(days)).astype(np.int64)
    return dict(days=days, counts=counts, ledger=ledger, C=ledger[:, 0], R=ledger[:, 1],
                U=ledger[:, 2], V=ledger[:, 3], N=counts)


def array_sha256(value: np.ndarray, dtype: str | None = None) -> str:
    """Byte identity helper; dtype conversion must be explicit at its caller."""
    return hashlib.sha256(np.ascontiguousarray(value, dtype=dtype).tobytes()).hexdigest()
