"""Candidate-axis batching of the frozen delayed convex-aggregation oracle.

Only matured expert losses are computed for updates. Offline metric scoring is
separate and never changes policy state. No model fitting or data I/O occurs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence
import numpy as np

from .delayed_risk_aggregation import (
    AggregationConfig, DT_HOURS, FEEDBACK_RELEASE_OFFSET, MIN_FEEDBACK_LAG,
    RHO, RISK_CAP, _config, _initial_weights,
)


@dataclass(frozen=True)
class BatchAggregationResult:
    metrics: np.ndarray
    actions: np.ndarray | None
    metadata: dict[str, Any]


def _priors(configs: Sequence[AggregationConfig], k: int,
            priors: np.ndarray | None) -> np.ndarray:
    if priors is not None:
        supplied = np.asarray(priors, dtype=np.float64)
        if supplied.shape != (len(configs), k):
            raise ValueError('Prior matrix must have shape [candidate,expert]')
    else:
        supplied = None
    result = []
    for i, conf in enumerate(configs):
        _config(conf, k)
        row = None if supplied is None else supplied[i]
        if conf.method == 'equal' and row is not None:
            if not np.isfinite(row).all() or not (row > 0).all() or not (row == row[0]).all():
                raise ValueError('Equal method accepts only a uniform prior row')
            row = None
        result.append(_initial_weights(k, row, conf.method))
    return np.asarray(result, dtype=np.float64).reshape(len(configs), k)


def _softmax_groups(prior, ledger, eta, temperature, groups, out):
    # Grouping identical support sets preserves scalar summation order when
    # historical priors contain exact zeros. It never selects using outcomes.
    for candidates, active in groups:
        ll = ledger[np.ix_(candidates, active)]
        shifted = ll - ll.min(axis=1, keepdims=True)
        with np.errstate(over='ignore', under='ignore', invalid='ignore'):
            penalty = np.minimum(shifted * eta[candidates, None]
                                 / temperature[candidates, None], 700.)
        penalty[shifted == 0] = 0.
        if not np.isfinite(penalty).all():
            raise FloatingPointError('Nonfinite exponential penalty')
        logits = np.log(prior[np.ix_(candidates, active)]) - penalty
        exp = np.exp(np.maximum(logits - logits.max(axis=1, keepdims=True), -700.))
        out[np.ix_(candidates, active)] = exp / exp.sum(axis=1, keepdims=True)


def aggregate_batch(experts: np.ndarray, y: np.ndarray, mask: np.ndarray,
                    anchors: np.ndarray, configs: Sequence[AggregationConfig],
                    priors: np.ndarray | None = None, *,
                    score_slice: tuple[int, int] | None = None,
                    return_actions: bool = False) -> BatchAggregationResult:
    """Batch finite policies; return mean (C,R,U,V) and optional [C,T,N] actions.

    ``score_slice`` is a half-open pair of row indices, not event timestamps.
    Metrics use the unchanged valid-cell denominator in that slice. An empty
    scoring population produces four NaNs per candidate, never scientific 0.

    Priors have shape [C,K]. An equal method's supplied row must be uniform;
    fixed methods require a supplied row. Adaptive methods retain exact zero
    prior weights as in the scalar oracle. Reference identity is fixed by each
    configuration, never selected from current or future outcomes.

    Cumulative/discounted expert scores are shared across candidates only after
    their legal release. Dual updates use each past mixture's actual U/V. At
    most eight old action rows are cached; no tail feedback is flushed. Full
    actions are stored solely when explicitly requested. A current target mask
    may be read for offline scoring but never gates the decision or update.
    """
    x = np.asarray(experts, dtype=np.float64)
    target = np.asarray(y, dtype=np.float64)
    m = np.asarray(mask)
    a = np.asarray(anchors)
    if (x.ndim != 3 or x.shape[2] == 0 or target.shape != x.shape[:2]
            or m.shape != target.shape or m.dtype != np.bool_
            or a.shape != (x.shape[0],) or a.dtype.kind not in 'iu'):
        raise ValueError('Invalid expert/target/mask/anchor shapes or dtypes')
    if (np.any(a < 0) or np.any(a[1:] <= a[:-1])
            or not np.isfinite(x).all() or np.any(x < 0)):
        raise ValueError('Invalid expert actions or issue order')
    t_count, n, k = x.shape
    configs = list(configs)
    c = len(configs)
    if score_slice is None:
        lo, hi = 0, t_count
    else:
        if (not isinstance(score_slice, (tuple, list)) or len(score_slice) != 2
                or any(not isinstance(v, (int, np.integer)) or isinstance(v, (bool, np.bool_))
                       for v in score_slice)):
            raise ValueError('Score slice must be integer half-open row indices')
        lo, hi = map(int, score_slice)
        if not 0 <= lo <= hi <= t_count:
            raise ValueError('Score slice outside the issue grid')
    prior = _priors(configs, k, priors)
    weights = prior.copy()
    ledger = np.zeros((c, k))
    lv, lu = np.zeros(c), np.zeros(c)
    eta = np.array([v.eta for v in configs])
    temperature = np.array([v.temperature for v in configs])
    scale = np.array([v.cost_scale for v in configs])
    discount = np.array([v.discount for v in configs])
    dv = np.array([v.dual_eta_v for v in configs])
    du = np.array([v.dual_eta_u for v in configs])
    reference = np.array([v.reference_index for v in configs], dtype=np.int64)
    adaptive = np.array([v.method not in ('equal', 'fixed') for v in configs])
    dual = np.array([v.method in ('dual', 'discounted_dual') for v in configs])
    discounted = np.array([v.method in ('discounted', 'discounted_dual') for v in configs])
    ai, di = np.flatnonzero(adaptive), np.flatnonzero(dual)
    support_groups = {}
    for j in ai:
        support_groups.setdefault(tuple(np.flatnonzero(prior[j] > 0)), []).append(j)
    groups = [(np.asarray(indices), np.asarray(support))
              for support, indices in support_groups.items()]
    saved = np.empty((c, t_count, n)) if return_actions else None
    pending = {}
    totals = np.zeros((c, 4))
    score_n = 0
    cursor = used_rows = total_cells = 0
    max_pending = 0
    last_release = -1
    release_trace = np.full(t_count, -1, dtype=np.int64)
    for i in range(t_count):
        now = int(a[i])
        if i and discounted.any():
            decay = np.where(discounted, discount ** (now - int(a[i-1])), 1.)
            ledger *= decay[:, None]
            lv *= decay; lu *= decay
        while cursor < i and int(a[cursor]) <= now - MIN_FEEDBACK_LAG:
            release = int(a[cursor]) + FEEDBACK_RELEASE_OFFSET
            valid = m[cursor]
            count = int(np.count_nonzero(valid))
            used_rows += 1; total_cells += count; last_release = release
            old_action = pending.pop(cursor, None)
            if count:
                yy = target[cursor, valid]
                if not np.isfinite(yy).all() or np.any(yy < 0):
                    raise ValueError('Invalid matured shortfall; row was not dropped')
                xx = x[cursor, valid]
                cell_weight = count / n
                age = np.where(discounted, discount ** (now-release), 1.)
                if len(ai):
                    with np.errstate(over='ignore', invalid='ignore'):
                        u = np.sum((np.maximum(yy[:, None]-xx, 0)*DT_HOURS)/count,
                                   axis=0, dtype=np.float64)
                        cost = np.sum((xx*DT_HOURS)/count, axis=0, dtype=np.float64) + RHO*u
                        score = cost[None, :]/scale[ai, None]
                        if len(di):
                            v = np.sum((yy[:, None]>xx).astype(float)/count,
                                       axis=0, dtype=np.float64)
                            severity = RHO*(u[None, :]-u[reference[ai], None])/scale[ai, None]
                            score = (score + lv[ai, None]*(v[None, :]-RISK_CAP)
                                     + lu[ai, None]*severity)
                        ledger[ai] += (age[ai]*cell_weight)[:, None]*score
                    if not np.isfinite(ledger[ai]).all():
                        raise FloatingPointError('Nonfinite expert score ledger')
                if len(di):
                    if old_action is None:
                        raise RuntimeError('Missing pending mixture action')
                    actual = old_action[:, valid]
                    actual_u = np.sum((np.maximum(yy[None, :]-actual, 0)*DT_HOURS)/count,
                                      axis=1, dtype=np.float64)
                    actual_v = np.mean(yy[None, :]>actual, axis=1)
                    lv[di] = np.maximum(0., lv[di]+age[di]*cell_weight*dv[di]*(actual_v-RISK_CAP))
                    lu[di] = np.maximum(0., lu[di]+age[di]*cell_weight*du[di]
                                        *RHO*(actual_u-u[reference[di]])/scale[di])
                    if not np.isfinite(lv[di]).all() or not np.isfinite(lu[di]).all():
                        raise FloatingPointError('Nonfinite risk multiplier')
            cursor += 1
        _softmax_groups(prior, ledger, eta, temperature, groups, weights)
        # Identical product/reduction order to the scalar oracle, including
        # zero-weight experts: BLAS rounding must not flip strict V membership.
        with np.errstate(over='ignore', invalid='ignore'):
            current = np.sum(x[i][None, :, :]*weights[:, None, :], axis=-1)
        if not np.isfinite(current).all():
            raise FloatingPointError('Nonfinite aggregate action')
        if saved is not None:
            saved[:, i] = current
        if len(di):
            pending[i] = current[di].copy()
            max_pending = max(max_pending, len(pending))
        release_trace[i] = last_release
        if lo <= i < hi:
            valid = m[i]
            count = int(np.count_nonzero(valid))
            score_n += count
            if count:
                yy = target[i, valid]
                if not np.isfinite(yy).all() or np.any(yy < 0):
                    raise ValueError('Invalid offline scored shortfall; row was not dropped')
                rr = current[:, valid]*DT_HOURS
                uu = np.maximum(yy[None, :]-current[:, valid], 0)*DT_HOURS
                totals[:, 0] += np.sum(rr+RHO*uu, axis=1)
                totals[:, 1] += np.sum(rr, axis=1)
                totals[:, 2] += np.sum(uu, axis=1)
                totals[:, 3] += np.sum(yy[None, :]>current[:, valid], axis=1)
    metrics = totals/score_n if score_n else np.full((c, 4), np.nan)
    if score_n and not np.isfinite(metrics).all():
        raise FloatingPointError('Nonfinite offline aggregate metrics')
    return BatchAggregationResult(metrics, saved, {
        'metric_order': ['C', 'R', 'U', 'V'], 'score_slice': [lo, hi],
        'score_N': score_n, 'score_status': 'DEFINED' if score_n else 'UNDEFINED_POPULATION',
        'feedback_rule': 'source_anchor + 7 < decision_anchor',
        'feedback_release_offset': FEEDBACK_RELEASE_OFFSET,
        'minimum_consecutive_grid_lag': MIN_FEEDBACK_LAG,
        'last_feedback_release_by_decision': release_trace.tolist(),
        'feedback_rows_used': used_rows, 'feedback_cells_used': total_cells,
        'pending_feedback_rows': t_count-cursor,
        'max_pending_feedback_rows': max_pending,
        'final_weights': weights.tolist(), 'final_lambda_v': lv.tolist(),
        'final_lambda_u': lu.tolist(), 'candidate_count': c,
        'feedback_weighting': 'valid-cell sums divided by fixed node count',
        'risk_guarantee': False, 'independent_confirmation': False,
        'uses_historical_Cstar': False,
        'action_arithmetic': 'same product and last-axis sum as scalar oracle',
    })
