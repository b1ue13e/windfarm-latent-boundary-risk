"""Causal calibration controls for frozen actions, with delayed target feedback.

The learning target event rate is a hyperparameter, not a qualification limit.
No method here provides a distribution-free guarantee for dependent SCADA data.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
from typing import Mapping

import numpy as np


RELEASE_LAG_STEPS = 7


@dataclass(frozen=True)
class DelayedCalibrationConfig:
    """Numerical scales for actions are in the input action units (normally kW)."""

    method: str = "global_shift"
    fixed_shift: float = 0.0
    initial_shift: float = 0.0
    step_size: float = 1.0
    target_event_rate: float = 0.10
    window_steps: int = 432
    quantile: float = 0.90
    gamma: float = 0.01
    initial_alpha: float | None = None


@dataclass(frozen=True)
class DelayedCalibrationResult:
    actions: np.ndarray
    trace: Mapping[str, np.ndarray] | None
    config: DelayedCalibrationConfig
    method: str
    processed_feedback_issues: int
    observed_feedback_issues: int
    observed_feedback_cells: int


def _method(config: DelayedCalibrationConfig) -> str:
    aliases = {
        "fixed": "global_shift", "global_shift": "global_shift",
        "tracker": "quantile_tracker", "quantile_tracker": "quantile_tracker",
        "robbins_monro": "quantile_tracker",
        "rolling": "rolling_quantile", "rolling_quantile": "rolling_quantile",
        "aci": "aci",
    }
    if config.method not in aliases:
        raise ValueError("Unknown delayed-calibration method")
    return aliases[config.method]


def _validate_config(config: DelayedCalibrationConfig) -> str:
    method = _method(config)
    values = (config.fixed_shift, config.initial_shift, config.step_size,
              config.target_event_rate, config.quantile, config.gamma)
    if any(not math.isfinite(float(v)) for v in values):
        raise ValueError("Nonfinite calibration configuration")
    if config.step_size < 0 or config.gamma < 0:
        raise ValueError("Learning steps must be nonnegative")
    if not 0 < config.target_event_rate < 1 or not 0 <= config.quantile <= 1:
        raise ValueError("Invalid learning event rate or quantile")
    if (isinstance(config.window_steps, (bool, np.bool_)) or
            not isinstance(config.window_steps, (int, np.integer)) or config.window_steps < 1):
        raise ValueError("window_steps must be a positive integer issue-clock length")
    if config.initial_alpha is not None and (
            not math.isfinite(float(config.initial_alpha)) or not .001 <= config.initial_alpha <= .999):
        raise ValueError("initial_alpha must lie in the numerical interval [.001,.999]")
    return method


def _anchors(values, expected: int) -> np.ndarray:
    raw = np.asarray(values)
    if raw.shape != (expected,) or raw.dtype.kind not in "iu":
        raise ValueError("Anchors must be a one-dimensional integer issue clock")
    try:
        result = np.asarray([int(a) for a in raw], dtype=np.int64)
    except (OverflowError, ValueError) as exc:
        raise ValueError("Issue anchor outside supported integer range") from exc
    if np.any(result < 0) or any(int(b) <= int(a) for a, b in zip(result[:-1], result[1:])):
        raise ValueError("Issue anchors must be nonnegative, unique and strictly increasing")
    return result


def run_delayed_calibration(
    reference_actions,
    shortfall,
    mask,
    anchors,
    config: DelayedCalibrationConfig,
    *,
    save_trace: bool = True,
    initial_residuals=None,
    initial_residual_anchors=None,
) -> DelayedCalibrationResult:
    """Return all-grid actions using only feedback with ``a + 7 < t``.

    Arrays have shape (issues, nodes). ``mask`` is used only once a past label
    matures, never to choose which current actions to produce. An update uses
    the past policy's actual strict event rate across observed target cells.
    A zero-observation issue is processed but causes no parameter update.

    Rolling windows contain residuals whose original issue anchors satisfy
    ``t-window_steps <= a`` and ``a+7 < t``. Missing targets do not compress the
    issue clock. Residuals are always S-reference, not S-adjusted_action.

    Optional initial residuals require matching issue anchors, all strictly
    mature before the first action; their age determines window expiry. They
    do not update the tracker/ACI event feedback because no prior actions are
    supplied. Without them, an empty rolling window uses shift zero.
    """
    if not isinstance(config, DelayedCalibrationConfig):
        raise TypeError("config must be DelayedCalibrationConfig")
    method = _validate_config(config)
    ref = np.asarray(reference_actions, dtype=np.float64)
    target = np.asarray(shortfall, dtype=np.float64)
    observed = np.asarray(mask)
    if (ref.ndim != 2 or ref.shape[1] < 1 or target.shape != ref.shape or
            observed.shape != ref.shape or observed.dtype != np.bool_):
        raise ValueError("Expected paired (issue,node) arrays and a Boolean target mask")
    issue = _anchors(anchors, len(ref))
    if not np.isfinite(ref).all() or np.any(ref < 0):
        raise ValueError("Reference actions must be finite and nonnegative on the complete grid")
    if not np.isfinite(target[observed]).all() or np.any(target[observed] < 0):
        raise ValueError("Observed shortfalls must be finite and nonnegative")
    if (initial_residuals is None) != (initial_residual_anchors is None):
        raise ValueError("Initial residual values and their issue anchors must be supplied together")

    residuals: deque[tuple[int, np.ndarray]] = deque()
    if initial_residuals is not None:
        y = np.asarray(initial_residuals, dtype=np.float64)
        raw_a = np.asarray(initial_residual_anchors)
        if (y.ndim != 1 or raw_a.shape != y.shape or raw_a.dtype.kind not in "iu" or
                not np.isfinite(y).all() or not len(issue)):
            raise ValueError("Invalid initial residual history")
        a = [int(v) for v in raw_a]
        if any(v < 0 or v + RELEASE_LAG_STEPS >= int(issue[0]) for v in a):
            raise ValueError("Initial residual labels have not strictly matured before the first issue")
        order = np.argsort(raw_a, kind="stable")
        for v in sorted(set(a)):
            residuals.append((v, np.array(y[order][raw_a[order] == v], copy=True)))

    output = np.empty_like(ref)
    fields = {
        "issue": np.array(issue, copy=True),
        "shift": np.zeros(len(issue), dtype=float),
        "alpha": np.full(len(issue), np.nan),
        "quantile": np.full(len(issue), np.nan),
        "released_issues": np.zeros(len(issue), dtype=np.int64),
        "updated_issues": np.zeros(len(issue), dtype=np.int64),
        "updated_cells": np.zeros(len(issue), dtype=np.int64),
        "window_cells": np.zeros(len(issue), dtype=np.int64),
        "last_released_issue": np.full(len(issue), -1, dtype=np.int64),
        "last_feedback_event_rate": np.full(len(issue), np.nan),
    } if save_trace else None
    tracker = float(config.initial_shift)
    alpha = float(config.target_event_rate if config.initial_alpha is None else config.initial_alpha)
    alpha = float(np.clip(alpha, .001, .999))
    pending = 0
    n_updated = 0
    n_cells = 0
    last_rate = math.nan
    for i, t_value in enumerate(issue):
        t = int(t_value)
        # Labels at the same tick are excluded by the strict arrival convention.
        while pending < i and int(issue[pending]) + RELEASE_LAG_STEPS < t:
            valid = observed[pending]
            count = int(np.count_nonzero(valid))
            if count:
                last_rate = float(np.count_nonzero(target[pending, valid] > output[pending, valid]) / count)
                if method == "quantile_tracker":
                    tracker += config.step_size * (last_rate - config.target_event_rate)
                    if not math.isfinite(tracker):
                        raise FloatingPointError("Nonfinite quantile tracker state")
                elif method == "aci":
                    alpha = float(np.clip(alpha + config.gamma * (config.target_event_rate - last_rate), .001, .999))
                if method in ("rolling_quantile", "aci"):
                    residuals.append((int(issue[pending]), target[pending, valid] - ref[pending, valid]))
                n_updated += 1
                n_cells += count
            pending += 1
        cutoff = t - int(config.window_steps)
        while residuals and residuals[0][0] < cutoff:
            residuals.popleft()
        window_count = sum(len(values) for _, values in residuals)
        q = math.nan
        if method == "global_shift":
            shift = float(config.fixed_shift)
        elif method == "quantile_tracker":
            shift = tracker
        else:
            q = float(config.quantile if method == "rolling_quantile" else 1.0 - alpha)
            shift = (float(np.quantile(np.concatenate([v for _, v in residuals]), q, method="higher"))
                     if window_count else 0.0)
        with np.errstate(over="ignore", invalid="ignore"):
            output[i] = np.maximum(ref[i] + shift, 0.0)
        if not np.isfinite(output[i]).all():
            raise FloatingPointError("Nonfinite adjusted action")
        if fields is not None:
            fields["shift"][i] = shift
            fields["alpha"][i] = alpha if method == "aci" else math.nan
            fields["quantile"][i] = q
            fields["released_issues"][i] = pending
            fields["updated_issues"][i] = n_updated
            fields["updated_cells"][i] = n_cells
            fields["window_cells"][i] = window_count
            fields["last_released_issue"][i] = int(issue[pending - 1]) if pending else -1
            fields["last_feedback_event_rate"][i] = last_rate
    output.setflags(write=False)
    if fields is not None:
        for value in fields.values():
            value.setflags(write=False)
    return DelayedCalibrationResult(output, fields, config, method, pending, n_updated, n_cells)
