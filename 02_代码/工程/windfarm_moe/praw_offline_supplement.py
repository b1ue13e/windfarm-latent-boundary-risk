"""Fixed raw-power ablation, isolated from historical qualification selectors.

This module defines computation only. Qualification labels are produced later
from sealed outputs and cannot be supplied to the evaluation API.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np

from .state_measurement import account, information_matrix


def praw_information_matrix(data: np.ndarray, anchors: np.ndarray,
                            forecast: np.ndarray) -> np.ndarray:
    """Reuse O6 verbatim and append exactly one current active-power value."""
    background = information_matrix(data, anchors, forecast, "O6")
    fresh = np.asarray(data)[np.asarray(anchors, dtype=np.int64), :, 1].reshape(-1, 1)
    result = np.column_stack((background, fresh)).astype(np.float32)
    if result.shape[1] != 119:
        raise ValueError("Praw must contain O6's 118 columns and one current P")
    return result


def freeze_registry(rules: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return the ten declared identities without accepting eligibility labels."""
    expected = [(e, s) for e in ("HGB", "MLP") for s in range(201, 206)]
    heads = rules.get("new_fit_budget", {}).get("heads")
    if heads is not None:
        actual = [(h["estimator"], h["seed"]) for h in heads]
        if actual != expected:
            raise ValueError("Registry must preserve both estimators and all five seeds")
    if "seeds" in rules and list(rules["seeds"]) != list(range(201, 206)):
        raise ValueError("Unregistered seed list")
    return [dict(identity_id=f"Praw_{e}_{s}", estimator=e, seed=s, arm="Praw")
            for e, s in expected]


def fit_signed_offset(raw_history: np.ndarray, shortfall_history: np.ndarray,
                      mask: np.ndarray, q: float = .925) -> float:
    """Fit a signed offset from the supplied historical offset population only."""
    if q != .925:
        raise ValueError("The supplementary offset level is fixed at .925")
    raw, shortfall, valid = np.asarray(raw_history, float), np.asarray(shortfall_history, float), np.asarray(mask)
    if raw.shape != shortfall.shape or valid.shape != raw.shape or valid.dtype != bool or not valid.any():
        raise ValueError("CALIBRATION_UNDEFINED: invalid or empty historical population")
    if not np.isfinite(raw).all() or not np.isfinite(shortfall[valid]).all() or np.any(shortfall[valid] < 0):
        raise ValueError("CALIBRATION_UNDEFINED: nonfinite raw or target")
    return float(np.quantile((shortfall - np.maximum(raw, 0))[valid], .925, method="higher"))


def evaluate_all(registry: Sequence[Mapping[str, Any]], models: Mapping[str, Any],
                 offsets: Mapping[str, float], inputs: Mapping[str, np.ndarray],
                 predict_fn: Callable[[Any, np.ndarray], np.ndarray] | None = None) -> list[dict[str, Any]]:
    """Compute all listed heads once, retaining failures and high finite losses.

    No qualification argument, file access or historical selection is present.
    The caller seals the resulting actions before generating labels.
    """
    records: list[dict[str, Any]] = []
    features = inputs["features"]
    shortfall, mask, anchors = inputs["shortfall"], inputs["mask"], inputs["anchors"]
    for identity in registry:
        row = dict(identity)
        key = row["identity_id"]
        try:
            if key not in models or models[key] is None:
                raise ValueError("FIT_FAILED: model unavailable")
            if key not in offsets or not np.isfinite(offsets[key]):
                raise ValueError("CALIBRATION_UNDEFINED: own offset unavailable")
            prediction = models[key].predict(features) if predict_fn is None else predict_fn(models[key], features)
            raw = np.maximum(np.asarray(prediction, dtype=np.float64), 0).reshape(np.shape(shortfall))
            actions = np.maximum(raw + float(offsets[key]), 0)
            if not np.isfinite(raw).all() or not np.isfinite(actions).all():
                raise ValueError("PREDICTION_INVALID: nonfinite action")
            blocks = account(shortfall, actions, mask, anchors)
            row.update(compute_status="EVALUATION_COMPLETED", failure_reason=None,
                       raw=raw, actions=actions, blocks=blocks)
        except (ValueError, RuntimeError, KeyError, TypeError, MemoryError) as exc:
            row.update(compute_status="COMPUTATION_FAILED", failure_reason=f"{type(exc).__name__}: {exc}",
                       raw=None, actions=None, blocks=None)
        records.append(row)
    return records


def pool_daily_totals(blocks: Mapping[str, np.ndarray]) -> dict[str, float | None]:
    """Pool totals over valid cells, never average unequal-size daily means."""
    n = float(np.asarray(blocks["N"], dtype=np.float64).sum())
    return {k: None if n <= 0 else float(np.asarray(blocks[k], dtype=np.float64).sum() / n)
            for k in ("C", "R", "U", "V")} | {"N": n}


def pooled_five_fit_metrics(records: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Require the complete five declared fits for estimator-level summaries."""
    result: dict[str, dict[str, Any]] = {}
    for estimator in ("HGB", "MLP"):
        rows = [r for r in records if r["estimator"] == estimator]
        complete = [r for r in rows if r["compute_status"] == "EVALUATION_COMPLETED"]
        seeds = [r["seed"] for r in complete]
        if sorted(seeds) != list(range(201, 206)) or len(rows) != 5:
            result[estimator] = dict(status="UNAVAILABLE_INCOMPLETE_FITS", fit_count=len(complete),
                                     **{k: None for k in ("C", "R", "U", "V")})
            continue
        counts = [np.asarray(r["blocks"]["N"]) for r in complete]
        if any(not np.array_equal(counts[0], n) for n in counts[1:]):
            raise ValueError("Five-fit summaries require the identical scoring population")
        metrics = [pool_daily_totals(r["blocks"]) for r in complete]
        result[estimator] = dict(status="COMPLETE_FIVE_FIT", fit_count=5,
            **{k: None if any(m[k] is None for m in metrics) else float(np.mean([m[k] for m in metrics]))
               for k in ("C", "R", "U", "V")})
    return result


def bind_common_reference(mapping: Mapping[str, Mapping[str, Any]], estimator: str,
                          cell: str, seed: int, q: float = .925) -> Mapping[str, Any]:
    """Reject original individually selected-q records as Common references."""
    if q != .925 or cell not in ("O6", "OP6", "OZ6", "OPZ6", "F", "FZ"):
        raise ValueError("Reference must use a registered cell and Common q=.925")
    item = mapping[f"Common|{estimator}|{cell}|{seed}|{q:g}"]
    if item.get("recipe") != "Common" or item.get("q") != .925:
        raise ValueError("Reference recipe mismatch; Original selected-q is inadmissible")
    return item
