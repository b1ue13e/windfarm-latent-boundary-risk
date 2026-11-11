"""Causal convex aggregation of frozen experts with strictly earlier feedback release.

This module implements developmental policies, not risk certificates. Every
decision uses current expert actions and only targets whose release anchor is
strictly before the current issue. Future target masks never gate current decisions.
Strict event risk is non-convex; expert-event penalties give no mixture bound.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np


HORIZON_STEPS = 6
LABEL_RELEASE_STEPS = 1
FEEDBACK_RELEASE_OFFSET = HORIZON_STEPS + LABEL_RELEASE_STEPS
MIN_FEEDBACK_LAG = FEEDBACK_RELEASE_OFFSET + 1
RHO = 10.
DT_HOURS = 1. / 6.
RISK_CAP = .10
METHODS = ('equal', 'fixed', 'exponential', 'discounted', 'dual', 'discounted_dual')


@dataclass(frozen=True)
class AggregationConfig:
    """Finite configuration; cost_scale is fixed before any feedback is read.

    The dual severity learning target is rho*(U_mix-U_reference)<=0. It is
    separate from, and never changes, any downstream frozen qualification
    margin or historical Cstar. Discount is per event slot, not per row.
    """
    cost_scale: float = 100.
    method: str = 'exponential'
    eta: float = 1.
    discount: float = 1.
    temperature: float = 1.
    dual_eta_v: float = .1
    dual_eta_u: float = .1
    reference_index: int = 0


@dataclass(frozen=True)
class AggregationResult:
    action: np.ndarray
    weights: np.ndarray | None
    final_weights: np.ndarray
    trace: dict[str, np.ndarray]
    metadata: dict[str, Any]


def _config(config: AggregationConfig, k: int) -> None:
    if config.method not in METHODS:
        raise ValueError('Unknown aggregation method')
    if not (isinstance(config.reference_index, (int, np.integer))
            and not isinstance(config.reference_index, (bool, np.bool_))
            and 0 <= config.reference_index < k):
        raise ValueError('Invalid reference expert index')
    for field in ('cost_scale', 'temperature'):
        v = getattr(config, field)
        if not np.isscalar(v) or not np.isfinite(v) or v <= 0:
            raise ValueError('Invalid positive configuration value: ' + field)
    for field in ('eta', 'dual_eta_v', 'dual_eta_u'):
        v = getattr(config, field)
        if not np.isscalar(v) or not np.isfinite(v) or v < 0:
            raise ValueError('Invalid nonnegative configuration value: ' + field)
    if not np.isfinite(config.discount) or not 0 < config.discount <= 1:
        raise ValueError('Discount must lie in (0,1]')
    if config.method not in ('discounted', 'discounted_dual') and config.discount != 1:
        raise ValueError('A discount requires an explicit discounted method')


def _initial_weights(k: int, weights: Sequence[float] | None,
                     method: str) -> np.ndarray:
    if method == 'equal':
        if weights is not None:
            raise ValueError('Equal weighting does not accept historical weights')
        return np.full(k, 1. / k)
    if weights is None:
        if method == 'fixed':
            raise ValueError('Fixed mixing requires explicit historical weights')
        return np.full(k, 1. / k)
    w = np.asarray(weights, dtype=np.float64)
    if w.shape != (k,) or not np.isfinite(w).all() or np.any(w < 0) or not np.any(w > 0):
        raise ValueError('Invalid historical weights')
    # Divide before summing to avoid overflow from finite large priors.
    w = w / w.max()
    return w / w.sum()


def _softmax(prior: np.ndarray, ledger: np.ndarray,
             config: AggregationConfig) -> np.ndarray:
    active = prior > 0
    shifted = ledger[active] - ledger[active].min()
    # A finite, nonnegative score gap may overflow its exponential scale.
    # Saturating at exp(-700) is explicit arithmetic protection, not removal.
    with np.errstate(over='ignore', under='ignore', invalid='ignore'):
        penalty = np.minimum((shifted * config.eta) / config.temperature, 700.)
    penalty[shifted == 0] = 0.
    if not np.isfinite(penalty).all():
        raise FloatingPointError('Nonfinite exponential penalty')
    logits = np.log(prior[active]) - penalty
    exponents = np.exp(np.maximum(logits - logits.max(), -700.))
    out = np.zeros_like(prior)
    out[active] = exponents / exponents.sum()
    return out


def _mean(values: np.ndarray) -> np.ndarray:
    """Average along cells with division before summation for finite ranges."""
    return np.sum(values / len(values), axis=0, dtype=np.float64)


def aggregate_delayed(expert_actions: np.ndarray, shortfall: np.ndarray,
                      mask: np.ndarray, anchors: np.ndarray,
                      config: AggregationConfig | None = None, *,
                      historical_weights: Sequence[float] | None = None,
                      store_weights: bool = True,
                      store_ledger: bool = False) -> AggregationResult:
    """Return [T,N] actions, optional [T,K] weights and a causal update trace.

    All N turbines share a pooled K-vector. Experts are fixed before this run;
    their actions may depend on lawful issue-time features. For a decision at
    t, feedback a is usable exactly when a+7<t. On a consecutive grid the
    minimum lag is eight slots; synthetic release remains a+7. Empty mature rows update no
    losses or multipliers. No pending tail is flushed after the last decision.

    Each row contributes its valid-cell sum divided by the fixed node count,
    so partial target availability does not give a sparse issue the same loss
    weight as a fully observed issue. All methods use the original target mask.
    Exponential methods use cumulative C/cost_scale. Discounted methods apply
    discount**elapsed_slots and age each newly received row by its release.
    Dual variants add lambda_v*(V_expert-.10) and
    lambda_u*rho*(U_expert-U_reference)/cost_scale to expert scores, then update
    nonnegative multipliers from the *actual past aggregate action*. These
    learning targets are not downstream scientific acceptance criteria.

    Actions are returned on the entire issue/node grid, even when the current
    future-target mask is false. Masks are consulted only for mature feedback.
    Unmatured targets can be NaN. Current/future expert inputs must be finite
    nonnegative actions, and reference expert index is never reselected.
    """
    config = AggregationConfig() if config is None else config
    x = np.asarray(expert_actions, dtype=np.float64)
    y = np.asarray(shortfall, dtype=np.float64)
    m = np.asarray(mask)
    a = np.asarray(anchors)
    if (x.ndim != 3 or x.shape[2] == 0 or y.shape != x.shape[:2]
            or m.shape != y.shape or m.dtype != np.bool_
            or a.shape != (x.shape[0],) or a.dtype.kind not in 'iu'):
        raise ValueError('Invalid expert/target/mask/anchor shapes or dtypes')
    if (np.any(a < 0) or np.any(a[1:] <= a[:-1])
            or not np.isfinite(x).all() or np.any(x < 0)):
        raise ValueError('Invalid expert actions or issue order')
    t_count, n, k = x.shape
    _config(config, k)
    prior = _initial_weights(k, historical_weights, config.method)
    w = prior.copy()
    action = np.empty((t_count, n), dtype=np.float64)
    weights = np.empty((t_count, k), dtype=np.float64) if store_weights else None
    ledger = np.zeros(k, dtype=np.float64)
    trace = {name: np.zeros(t_count, dtype=np.float64)
             for name in ('lambda_v', 'lambda_u')}
    trace.update({name: np.zeros(t_count, dtype=np.int64)
                  for name in ('feedback_rows', 'feedback_cells')})
    trace.update({name: np.full(t_count, -1, dtype=np.int64)
                  for name in ('last_feedback_anchor', 'last_feedback_release')})
    if store_ledger:
        trace['ledger'] = np.empty((t_count, k), dtype=np.float64)
    dual = config.method in ('dual', 'discounted_dual')
    adaptive = config.method not in ('equal', 'fixed')
    discounted = config.method in ('discounted', 'discounted_dual')
    lv = lu = 0.
    cursor = 0
    total_cells = 0
    used_rows = 0
    last_anchor = last_release = -1
    for i in range(t_count):
        now = int(a[i])
        if discounted and i:
            decay = config.discount ** (now - int(a[i - 1]))
            ledger *= decay
            lv *= decay
            lu *= decay
        while cursor < i and int(a[cursor]) <= now - MIN_FEEDBACK_LAG:
            issue = int(a[cursor]); release = issue + FEEDBACK_RELEASE_OFFSET
            valid = m[cursor]
            count = int(np.count_nonzero(valid))
            last_anchor, last_release = issue, release
            trace['feedback_rows'][i] += 1
            trace['feedback_cells'][i] += count
            used_rows += 1
            total_cells += count
            if count:
                target = y[cursor, valid]
                if not np.isfinite(target).all() or np.any(target < 0):
                    raise ValueError('Invalid matured shortfall; row was not dropped')
                expert = x[cursor, valid]
                age_weight = config.discount ** (now - release) if discounted else 1.
                cell_weight = count / n
                if adaptive:
                    with np.errstate(over='ignore', invalid='ignore'):
                        u = _mean(np.maximum(target[:, None] - expert, 0) * DT_HOURS)
                        cost = _mean(expert * DT_HOURS) + RHO * u
                        score = cost / config.cost_scale
                        if dual:
                            v = _mean((target[:, None] > expert).astype(np.float64))
                            severity = RHO * (u - u[config.reference_index]) / config.cost_scale
                            score = score + lv * (v - RISK_CAP) + lu * severity
                        ledger += age_weight * cell_weight * score
                    if not np.isfinite(ledger).all():
                        raise FloatingPointError('Nonfinite expert score ledger')
                if dual:
                    actual = action[cursor, valid]
                    actual_u = float(_mean(np.maximum(target - actual, 0) * DT_HOURS))
                    reference_u = float(u[config.reference_index])
                    actual_v = float(np.mean(target > actual))
                    lv = max(0., lv + age_weight * cell_weight * config.dual_eta_v * (actual_v - RISK_CAP))
                    lu = max(0., lu + age_weight * cell_weight * config.dual_eta_u
                             * RHO * (actual_u - reference_u) / config.cost_scale)
                    if not np.isfinite([lv, lu]).all():
                        raise FloatingPointError('Nonfinite risk multiplier')
            cursor += 1
        if adaptive:
            w = _softmax(prior, ledger, config)
        with np.errstate(over='ignore', invalid='ignore'):
            action[i] = np.sum(x[i] * w[None, :], axis=-1)
        if not np.isfinite(action[i]).all():
            raise FloatingPointError('Nonfinite aggregate action')
        if weights is not None:
            weights[i] = w
        trace['lambda_v'][i], trace['lambda_u'][i] = lv, lu
        trace['last_feedback_anchor'][i] = last_anchor
        trace['last_feedback_release'][i] = last_release
        if store_ledger:
            trace['ledger'][i] = ledger
    return AggregationResult(action, weights, w.copy(), trace, {
        'method': config.method, 'horizon_steps': HORIZON_STEPS,
        'label_release_steps': LABEL_RELEASE_STEPS,
        'feedback_release_offset': FEEDBACK_RELEASE_OFFSET,
        'minimum_consecutive_grid_lag': MIN_FEEDBACK_LAG,
        'feedback_rule': 'source_anchor + 7 < decision_anchor',
        'feedback_rows_used': used_rows, 'feedback_cells_used': total_cells,
        'pending_feedback_rows': t_count - cursor,
        'cost_scale_fixed_before_run': config.cost_scale,
        'reference_index': config.reference_index,
        'risk_cap_learning_target': RISK_CAP,
        'signed_severity_learning_target': 0.,
        'uses_historical_Cstar': False,
        'risk_guarantee': False, 'independent_confirmation': False,
        'weight_scope': 'one pooled expert vector per issue',
        'feedback_weighting': 'valid-cell sums divided by fixed node count',
        'zero_prior_experts': np.flatnonzero(prior == 0).tolist(),
    })


delayed_risk_aggregation = aggregate_delayed
