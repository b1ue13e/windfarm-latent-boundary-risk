"""Endpoint-local inference for the V3 retrospective supplement.

This adapter consumes already defined points and the complete predeclared draw
matrix.  It does not generate draws, select models, or consume qualification
labels.  Unsupported endpoints remain in the family ledger with their physical
domain; an empirical constant is never treated as an algebraic identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from .risk_frontier import simultaneous_envelope


ZERO_SD_CUTOFF = 1e-14  # Existing envelope numerical cutoff; not an effect margin.
DOMAINS = {
    "SIGNED_REAL": {"code": "SIGNED_REAL", "lower": None, "upper": None},
    "RISK_0_1": {"code": "RISK_0_1", "lower": 0.0, "upper": 1.0},
    "NONNEGATIVE": {"code": "NONNEGATIVE", "lower": 0.0, "upper": None},
}


@dataclass(frozen=True)
class EndpointCoordinate:
    """One planned coordinate and all of its denominator dependencies.

    Population denominators may be vectors, for example the two stratum counts
    of an interaction.  Their draw counterparts then have shape (B, K).  A zero
    in any dependency makes only this endpoint undefined/uninformative.  Use
    ``computation_failure`` for unavailable fits/sources, never for risk failure.
    ``reference_denominator`` covers formula denominators such as reference cost;
    it defaults to the exact constant one for absolute endpoints.
    """

    coordinate_id: str
    point: float | None
    draws: Sequence[float] | np.ndarray
    population_denominator: float | Sequence[float] | np.ndarray
    draw_population_denominators: Sequence[float] | np.ndarray
    domain: str = "SIGNED_REAL"
    reference_denominator: float | Sequence[float] | np.ndarray = 1.0
    draw_reference_denominators: Sequence[float] | np.ndarray | None = None
    computation_failure: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PooledEstimate:
    """Totals/count pooling, retaining zero-count days and every draw row."""

    point: float | None
    draws: np.ndarray
    population_denominator: float
    draw_population_denominators: np.ndarray


def pooled_mean(total_by_day: Sequence[float] | np.ndarray,
                count_by_day: Sequence[float] | np.ndarray,
                weights: np.ndarray | None = None) -> PooledEstimate:
    """Pool original daily totals, never an unweighted average of day means.

    ``weights`` is supplied by the caller's already fixed common draw schedule.
    No resampling occurs here.  Zero-count days must have a zero total, not a
    fabricated observation.  An unsupported draw is NaN and remains in position.
    """
    totals = np.asarray(total_by_day, dtype=np.float64)
    counts = np.asarray(count_by_day, dtype=np.float64)
    if totals.ndim != 1 or totals.shape != counts.shape or not len(totals):
        raise ValueError("Daily totals/counts must be aligned nonempty vectors")
    if (not np.isfinite(totals).all() or not np.isfinite(counts).all()
            or np.any(counts < 0) or np.any((counts == 0) & (totals != 0))):
        raise ValueError("Invalid daily totals/counts, including nonzero empty-day total")
    if weights is None:
        w = np.eye(len(totals), dtype=np.float64)
    else:
        w = np.asarray(weights, dtype=np.float64)
    if (w.ndim != 2 or w.shape[1] != len(totals)
            or not np.isfinite(w).all() or np.any(w < 0)):
        raise ValueError("Draw weights must retain aligned finite nonnegative calendar columns")
    n = float(counts.sum())
    dn = w @ counts
    draws = np.full(len(w), np.nan, dtype=np.float64)
    np.divide(w @ totals, dn, out=draws, where=dn > 0)
    return PooledEstimate(float(totals.sum() / n) if n > 0 else None, draws, n, dn)


def observed_deficit_annotations(u_a: Sequence[float] | np.ndarray,
                                 u_b: Sequence[float] | np.ndarray,
                                 population_denominator: float) -> list[str]:
    """Return an observation annotation only, with no inference side effect."""
    if not np.isfinite(population_denominator) or population_denominator < 0:
        raise ValueError("Observed population denominator must be finite and nonnegative")
    a, b = np.asarray(u_a, dtype=np.float64), np.asarray(u_b, dtype=np.float64)
    if a.shape != b.shape or a.ndim != 1:
        raise ValueError("Deficit observations must be aligned vectors")
    if population_denominator == 0:
        return []
    if not len(a) or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("A positive population requires finite deficit observations")
    if np.any(a < 0) or np.any(b < 0):
        raise ValueError("Deficits must be nonnegative")
    return ["OBSERVED_BOTH_U_ZERO"] if np.all(a == 0) and np.all(b == 0) else []


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_json_value(v) for v in value]
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if value is None or isinstance(value, str):
        return value
    raise TypeError(f"Unsupported metadata type: {type(value).__name__}")


def _point_denominator(value: Any) -> np.ndarray:
    arr = np.atleast_1d(np.asarray(value, dtype=np.float64))
    if arr.ndim != 1 or not len(arr) or np.any(arr < 0):
        raise ValueError("Observed denominators must be nonnegative scalars/vectors")
    return arr


def _draw_denominators(value: Any, n_draws: int, width: int) -> np.ndarray:
    arr = np.asarray(value, dtype=np.float64)
    if arr.ndim == 1 and width == 1:
        arr = arr[:, None]
    if arr.shape != (n_draws, width) or np.any(arr < 0):
        raise ValueError("Draw denominator dependencies must align with every draw")
    return arr


def adapt_endpoint_family(coordinates: Sequence[EndpointCoordinate], *,
                          family_id: str, span: int, alpha: float = .05,
                          draw_ids: Sequence[str | int] | None = None) -> dict[str, Any]:
    """Apply endpoint-local support rules and the unchanged legacy envelope.

    All IDs and all B rows are exported, including unsupported draw values as
    JSON null.  Only finite, positive-denominator, empirically varying columns
    enter the legacy envelope.  ``alpha`` is passed through unchanged; callers
    must bind the V3 value and fixed span.  This function does not accept exact
    flags: V3 has no predeclared exact inferential coordinate.
    """
    if not isinstance(family_id, str) or not family_id or span not in (1, 3, 7):
        raise ValueError("A named family and declared 1/3/7-day span are required")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be inside (0,1)")
    coords = list(coordinates)
    ids = [c.coordinate_id for c in coords]
    if any(not isinstance(cid, str) or not cid for cid in ids) or len(set(ids)) != len(ids):
        raise ValueError("Planned coordinate IDs must be nonempty and unique")
    if coords:
        arrays = [np.asarray(c.draws, dtype=np.float64) for c in coords]
        n_draws = len(arrays[0]) if arrays[0].ndim == 1 else 0
        if n_draws < 2 or any(a.shape != (n_draws,) for a in arrays):
            raise ValueError("All coordinates must retain the same >=2 draw rows")
    else:
        arrays = []
        n_draws = len(draw_ids) if draw_ids is not None else 0
    row_ids = list(range(n_draws)) if draw_ids is None else list(draw_ids)
    if len(row_ids) != n_draws or len({str(x) for x in row_ids}) != n_draws:
        raise ValueError("Draw IDs must be unique and match the complete row count")
    row_ids = _json_value(row_ids)
    results: list[dict[str, Any]] = []
    finite_indices: list[int] = []
    for idx, (coord, draws) in enumerate(zip(coords, arrays)):
        if coord.domain not in DOMAINS:
            raise ValueError(f"Unknown domain code: {coord.domain}")
        pop = _point_denominator(coord.population_denominator)
        ref = _point_denominator(coord.reference_denominator)
        dpop = _draw_denominators(coord.draw_population_denominators, n_draws, len(pop))
        dref = (np.broadcast_to(ref, (n_draws, len(ref))) if
                coord.draw_reference_denominators is None else
                _draw_denominators(coord.draw_reference_denominators, n_draws, len(ref)))
        pop_valid = np.isfinite(pop).all() and np.all(pop > 0)
        ref_valid = np.isfinite(ref).all() and np.all(ref > 0)
        draw_valid = (np.isfinite(dpop).all(axis=1) & (dpop > 0).all(axis=1)
                      & np.isfinite(dref).all(axis=1) & (dref > 0).all(axis=1))
        domain = dict(DOMAINS[coord.domain])
        result = {
            **_json_value(coord.metadata),
            "coordinate_id": coord.coordinate_id, "family_id": family_id, "span": span,
            "point": None, "point_status": "UNAVAILABLE_COMPUTATION",
            "interval_status": "UNINFORMATIVE_DOMAIN", "domain": domain,
            "lower": domain["lower"], "upper": domain["upper"],
            "reason": None, "exact": False, "standard_error": None,
            "critical": None, "critical_source": None,
            "population_denominator": _json_value(pop),
            "reference_denominator": _json_value(ref),
            "draw_population_denominators": _json_value(dpop),
            "draw_reference_denominators": _json_value(dref),
            "draw_denominator_valid": draw_valid.tolist(),
            "all_draw_denominators_valid": bool(draw_valid.all()),
            "draw_values": _json_value(draws), "draw_count": n_draws,
        }
        # This order is part of the frozen specification.  A source failure is
        # not misreported as an empty population or an empirical zero.
        if coord.computation_failure:
            result.update(interval_status="NOT_AVAILABLE_COMPUTATION",
                          reason=f"COMPUTATION_FAILURE:{coord.computation_failure}")
        elif not np.isfinite(pop).all():
            result.update(interval_status="NOT_AVAILABLE_COMPUTATION",
                          reason="NONFINITE_OBSERVED_POPULATION_DENOMINATOR")
        elif not pop_valid:
            result.update(point_status="UNDEFINED_POPULATION", reason="OBSERVED_POPULATION_ZERO")
        elif not np.isfinite(ref).all():
            result.update(interval_status="NOT_AVAILABLE_COMPUTATION",
                          reason="NONFINITE_OBSERVED_REFERENCE_DENOMINATOR")
        elif not ref_valid:
            result.update(point_status="UNDEFINED_REFERENCE_DENOMINATOR",
                          reason="OBSERVED_REFERENCE_DENOMINATOR_ZERO")
        elif coord.point is None or not np.isfinite(coord.point):
            result.update(interval_status="NOT_AVAILABLE_COMPUTATION", reason="NONFINITE_POINT")
        else:
            result.update(point=float(coord.point), point_status="DEFINED")
            if not draw_valid.all():
                result["reason"] = "DRAW_DENOMINATOR_UNSUPPORTED"
            elif not np.isfinite(draws).all():
                result["reason"] = "NONFINITE_DRAW_VALUE"
            else:
                sd = float(draws.std(ddof=1))
                result["standard_error"] = sd
                if sd <= ZERO_SD_CUTOFF:
                    result["reason"] = "EMPIRICAL_ZERO_VARIANCE"
                else:
                    finite_indices.append(idx)
        results.append(result)
    critical = None
    if finite_indices:
        p = np.array([results[i]["point"] for i in finite_indices], dtype=np.float64)
        d = np.column_stack([arrays[i] for i in finite_indices])
        envelope = simultaneous_envelope(p, d, alpha,
                                         exact=np.zeros(len(finite_indices), dtype=bool))
        critical = float(envelope["critical"])
        for j, idx in enumerate(finite_indices):
            results[idx].update(
                lower=float(envelope["lower"][j]), upper=float(envelope["upper"][j]),
                interval_status="ESTIMATED_APPROX", reason="FINITE_VARIABLE_COORDINATE",
                standard_error=float(envelope["standard_error"][j]), critical=critical,
                critical_source={"family_id": family_id, "span": span,
                                 "finite_coordinate_ids": [ids[i] for i in finite_indices]},
            )
    status = ("NO_ESTIMABLE_INTERVALS" if not finite_indices else
              "ESTIMATED_APPROX" if len(finite_indices) == len(coords) else "PARTIAL_ESTIMATED_APPROX")
    return {
        "family_id": family_id, "span": span, "alpha": float(alpha), "status": status,
        "critical": critical, "critical_source": None if critical is None else "legacy_simultaneous_envelope",
        "planned_coordinate_ids": ids, "finite_coordinate_ids": [ids[i] for i in finite_indices],
        "draw_ids": row_ids, "draw_count": n_draws, "draw_rows_deleted": 0,
        "all_inferential_exact_flags_false": True,
        "method": "shared-block maximum standardized deviation; approximate fixed-fit supplement",
        "coordinates": results,
    }
