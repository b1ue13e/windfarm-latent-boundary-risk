"""Finite-policy risk/near-optimality tools; no distribution-free certificate."""
from __future__ import annotations

import hashlib
from typing import Any, Sequence

import numpy as np


def offset_grid(shortfall: np.ndarray, raw: np.ndarray, mask: np.ndarray,
                quantiles: Sequence[float]) -> np.ndarray:
    """Fit signed offsets using only an explicitly supplied historical slice."""
    s, r, valid = np.asarray(shortfall), np.asarray(raw), np.asarray(mask)
    q = np.asarray(quantiles, dtype=float)
    if s.shape != r.shape or s.shape != valid.shape or valid.dtype != bool or not valid.any():
        raise ValueError("Invalid historical arrays or mask")
    if q.ndim != 1 or not len(q) or not np.isfinite(q).all() or np.any((q < 0) | (q > 1)) or np.any(np.diff(q) < 0):
        raise ValueError("Quantile grid must be finite and ordered inside [0,1]")
    sv, rv = s[valid].astype(np.float64), r[valid].astype(np.float64)
    if not np.isfinite(sv).all() or not np.isfinite(rv).all() or np.any(sv < 0):
        raise ValueError("Invalid observed shortfall/reserve")
    return np.quantile(sv - np.maximum(rv, 0), q, method="higher")


def shared_block_draws(n_blocks: int, n_boot: int, span: int, seed: int) -> tuple[np.ndarray, str]:
    """Shared circular-block multiplicities for all models, seeds and conditions."""
    if n_blocks < 2 or n_boot < 2 or not 1 <= span <= n_blocks:
        raise ValueError("Invalid shared bootstrap configuration")
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n_blocks, size=(n_boot, (n_blocks + span - 1) // span))
    indices = ((starts[..., None] + np.arange(span)) % n_blocks).reshape(n_boot, -1)[:, :n_blocks]
    linear = (np.arange(n_boot)[:, None] * n_blocks + indices).reshape(-1)
    weights = np.bincount(linear, minlength=n_boot * n_blocks).reshape(n_boot, n_blocks).astype(float)
    identity = hashlib.sha256(indices.astype("<i8").tobytes()).hexdigest()
    return weights, identity


def simultaneous_envelope(point: np.ndarray, draws: np.ndarray, alpha: float,
                          exact: np.ndarray | None = None) -> dict[str, Any]:
    """Bootstrap maximum standardized deviation, an approximate joint envelope.

    Empirically constant coordinates stay unbounded unless algebraically exact.
    This avoids declaring zero risk uncertainty merely because no event occurred.
    """
    p, d = np.asarray(point, float), np.asarray(draws, float)
    known = np.zeros(p.shape, dtype=bool) if exact is None else np.asarray(exact, bool)
    if p.ndim != 1 or d.ndim != 2 or d.shape[1] != len(p) or len(d) < 2 or known.shape != p.shape:
        raise ValueError("Invalid envelope dimensions")
    if not np.isfinite(p).all() or not np.isfinite(d).all() or not 0 < alpha < 1:
        raise ValueError("Invalid envelope observations/alpha")
    sd = d.std(axis=0, ddof=1)
    varying = (sd > 1e-14) & ~known
    standardized = np.abs((d[:, varying] - p[varying]) / sd[varying])
    maxima = standardized.max(axis=1) if varying.any() else np.zeros(len(d))
    critical = float(np.quantile(maxima, 1 - alpha, method="higher"))
    lower, upper = p - critical * sd, p + critical * sd
    unknown = ~(varying | known)
    lower[unknown], upper[unknown] = -np.inf, np.inf
    lower[known], upper[known] = p[known], p[known]
    return {"lower": lower, "upper": upper, "standard_error": sd,
            "critical": critical, "unknown": unknown,
            "method": "shared-block maximum standardized deviation; approximate development only"}


def near_optimal_set(risk_lower: np.ndarray, risk_upper: np.ndarray,
                     regret_upper: np.ndarray, historical_pass: Sequence[bool],
                     resources: Sequence[Sequence[int]], epsilon: float,
                     cap: float = .10) -> dict[str, Any]:
    """Identify minimum-resource eligible candidates against possible competitors.

    Risk applies to every archived instance. Cost regret uses the declared mean
    cost, conditional on those instances. Ties remain a set, not a unique model.
    """
    lo, hi, regret = np.asarray(risk_lower, float), np.asarray(risk_upper, float), np.asarray(regret_upper, float)
    historical = np.asarray(historical_pass, bool)
    if lo.ndim != 2 or lo.shape != hi.shape or lo.shape[1] != len(historical):
        raise ValueError("Risk must have instance/candidate dimensions")
    k = lo.shape[1]
    if regret.shape != (k, k) or len(resources) != k or epsilon < 0 or not 0 < cap < 1:
        raise ValueError("Invalid selection objects")
    if np.isnan(lo).any() or np.isnan(hi).any() or np.isnan(regret).any() or np.any(lo > hi):
        raise ValueError("Invalid confidence bounds")
    order = [tuple(int(x) for x in row) for row in resources]
    if any(not row or min(row) < 0 for row in order) or len({len(row) for row in order}) != 1:
        raise ValueError("Resource tuples must be nonnegative and comparable")
    possible = np.flatnonzero(np.all(lo <= cap, axis=0))
    qualified = np.flatnonzero(np.all(hi <= cap, axis=0) & historical)
    required = np.max(regret[:, possible], axis=1) if len(possible) else np.full(k, np.inf)
    eligible = [int(m) for m in qualified if required[m] <= epsilon]
    minimum = min((order[m] for m in eligible), default=None)
    chosen = [m for m in eligible if order[m] == minimum]
    return {"possible_feasible_indices": possible.tolist(), "risk_qualified_indices": qualified.tolist(),
            "eligible_indices": eligible, "minimum_resource_indices": chosen,
            "required_relative_tolerance": required.tolist(), "epsilon": float(epsilon),
            "status": "IDENTIFIED_DEVELOPMENT_SET" if chosen else "NO_IDENTIFIED_POLICY",
            "certified_for_deployment": False}
