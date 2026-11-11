"""Stable arithmetic for the same frozen-family weather-block development estimand.

Input daily sums describe the already realized action/update trajectory. This
module neither retrains online policies within a draw nor corrects their search
selection. Fixed fits are never resampled as independent weather observations.
"""
from __future__ import annotations

import hashlib
import json
import numbers
from typing import Any, Sequence

import numpy as np


SEED_IDS = (201, 202, 203, 204, 205)
METRICS = ('C', 'R', 'U', 'V')
ALPHA = .05
RHO = 10.
CSTAR = 42.058880543674675
THRESHOLDS = dict(important_cost_gain=.01, cost_noninferiority=.01,
                  signed_H=.001, absolute_risk=.10, alpha=ALPHA)


def _hash_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def _and(values: Sequence[bool | None]) -> bool | None:
    if any(value is False for value in values):
        return False
    return None if any(value is None for value in values) else True


def _decision(row: dict, threshold: float, *, strict: bool = False) -> bool | None:
    """Three-valued decision; undefined uncertainty never becomes a failure."""
    if row['status'] not in ('ESTIMABLE_APPROX', 'EXACT_ALGEBRAIC_ZERO'):
        return None
    lo, hi = row['lower'], row['upper']
    if hi is not None and (hi < threshold if strict else hi <= threshold):
        return True
    if lo is not None and (lo >= threshold if strict else lo > threshold):
        return False
    return None


def _index(value: str | int, names: list[str]) -> int:
    if isinstance(value, str):
        if value not in names:
            raise ValueError(f'Unknown policy in frozen definition: {value}')
        return names.index(value)
    if isinstance(value, numbers.Integral) and not isinstance(value, (bool, np.bool_)) and 0 <= value < len(names):
        return int(value)
    raise ValueError('A policy reference must be a frozen name or index')


def _draws(n_days: int, n_boot: int, span: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    starts = np.random.default_rng(seed).integers(0, n_days, size=(n_boot, (n_days + span - 1) // span))
    indices = ((starts[..., None] + np.arange(span)) % n_days).reshape(n_boot, -1)[:, :n_days]
    flat = (np.arange(n_boot)[:, None] * n_days + indices).ravel()
    weights = np.bincount(flat, minlength=n_boot * n_days).reshape(n_boot, n_days)
    return indices, weights


def infer_stable_campaign(ledger: np.ndarray, counts: np.ndarray, policy_names: Sequence[str],
                   comparisons: Sequence[tuple[str | int, str | int]], *, span: int,
                   seed: int = 20261022, n_boot: int = 20000, cstar: float = CSTAR,
                   available: Sequence[bool] | None = None,
                   aliases: Sequence[tuple[str | int, str | int]] = ()) -> dict[str, Any]:
    """Infer every nominal endpoint without screening policies by qualification.

    ``ledger`` is [five fixed fits, frozen policies, 35 natural days, C/R/U/V].
    Counts are shared valid-turbine-interval counts. C/R/U are daily sums in kWh
    equivalents and V is a daily strict-event count. The right arm is the cost
    denominator for D. Explicit aliases require exact equality of the complete
    five-fit daily ledger, not merely equality of one aggregate endpoint.

    Returned ``None`` bounds are infinite/unavailable bounds, not numeric zeros.
    Small ``n_boot`` is supported only for synthetic implementation tests; a
    production result records whether the fixed 20,000-draw specification ran.
    Cstar is used solely to report signed H, never to construct an action.
    """
    data = np.asarray(ledger, dtype=np.float64)
    count = np.asarray(counts, dtype=np.float64)
    names = list(policy_names)
    if data.ndim != 4 or data.shape[0] != 5 or data.shape[2:] != (35, 4):
        raise ValueError('Expected daily ledger [5, policies, 35, 4]')
    if not names or len(names) != data.shape[1] or any(not isinstance(x, str) or not x for x in names) or len(set(names)) != len(names):
        raise ValueError('Frozen policy names must be unique, nonempty, and complete')
    if names[0] != 'REF':
        raise ValueError('Fixed REF must occupy index zero')
    if count.shape != (35,) or not np.isfinite(count).all() or np.any(count < 0) or np.any(count != np.floor(count)):
        raise ValueError('Shared daily counts must be finite nonnegative integers')
    if isinstance(span, (bool, np.bool_)) or span not in (1, 3, 7) or isinstance(n_boot, (bool, np.bool_)) or not isinstance(n_boot, numbers.Integral) or n_boot < 2:
        raise ValueError('Use frozen spans 1/3/7 and at least two draws')
    span = int(span)
    if not isinstance(seed, numbers.Integral) or isinstance(seed, (bool, np.bool_)) or seed < 0:
        raise ValueError('Invalid bootstrap seed')
    if isinstance(cstar, (bool, np.bool_)) or not np.isfinite(cstar) or cstar != CSTAR:
        raise ValueError('Cstar is the frozen report-only denominator and must not change')
    availability = [True] * len(names) if available is None else list(available)
    if len(availability) != len(names) or any(not isinstance(x, (bool, np.bool_)) for x in availability):
        raise ValueError('Explicit availability must contain one boolean per frozen policy')
    availability = [bool(x) for x in availability]
    pairs = [(_index(left, names), _index(right, names)) for left, right in comparisons]
    if len(pairs) != len(set(pairs)):
        raise ValueError('Duplicate comparisons in frozen family')
    alias_pairs = [(_index(left, names), _index(right, names)) for left, right in aliases]
    parent = list(range(len(names)))
    alias_verification = []

    def find(i: int) -> int:
        while parent[i] != i:
            i = parent[i]
        return i

    for left, right in alias_pairs:
        if not availability[left] or not availability[right]:
            alias_verification.append(dict(left=names[left], right=names[right], verified=False,
                                           reason='SOURCE_UNAVAILABLE'))
            continue
        if not np.array_equal(data[:, left], data[:, right]):
            raise ValueError('A frozen algebraic alias requires available, identical complete ledgers')
        parent[find(left)] = find(right)
        alias_verification.append(dict(left=names[left], right=names[right], verified=True,
                                       reason='COMPLETE_LEDGER_EXACT_EQUALITY'))

    definitions = []

    def define(cid: str, left: int, right: int | None, metric: str, fit: int | None = None) -> None:
        definitions.append(dict(id=cid, left=left, right=right, metric=metric, fit=fit))

    for policy in range(len(names)):
        define(f'Q:{policy}:D', policy, 0, 'D')
        for fit, fit_id in enumerate(SEED_IDS):
            define(f'Q:{policy}:H:{fit_id}', policy, 0, 'H', fit)
        for fit, fit_id in enumerate(SEED_IDS):
            define(f'Q:{policy}:V:{fit_id}', policy, None, 'V', fit)
    for j, (left, right) in enumerate(pairs):
        for metric in ('D', 'C', 'R', 'U', 'V'):
            define(f'E:{j}:{metric}', left, right, metric)
        for fit, fit_id in enumerate(SEED_IDS):
            define(f'E:{j}:H:{fit_id}', left, right, 'H', fit)

    family = dict(policy_names=names, comparisons=[list(x) for x in pairs],
                  frozen_aliases=[list(x) for x in alias_pairs], definitions=definitions,
                  thresholds=THRESHOLDS.copy(), fixed_fit_ids=list(SEED_IDS), reference_index=0,
                  metric_order=list(METRICS), cstar=float(cstar))
    indices, weights = _draws(35, int(n_boot), span, int(seed))
    n_point = float(count.sum())
    n_draw = weights @ count
    # Weather is the only resampled axis; all five instances receive each draw.
    totals = data.sum(axis=2)
    draw_totals = (weights @ data.transpose(2, 0, 1, 3).reshape(35, -1)).reshape(n_boot, 5, len(names), 4)
    valid_metric = np.isfinite(data).all(axis=2) & (data >= 0).all(axis=2)
    valid_metric[..., 3] &= (data[..., 3] <= count).all(axis=2)
    valid_metric[..., 3] &= (data[..., 3] == np.floor(data[..., 3])).all(axis=2)
    valid_metric &= ((data == 0) | (count[None, None, :, None] > 0)).all(axis=2)
    rows: list[dict] = []
    sample_columns: list[np.ndarray | None] = []
    for definition in definitions:
        left, right, metric, fit = (definition[k] for k in ('left', 'right', 'metric', 'fit'))
        col = 0 if metric == 'D' else 2 if metric == 'H' else METRICS.index(metric)
        fits = list(range(5)) if fit is None else [fit]
        domain = [0., 1.] if metric == 'V' and right is None else [-1., 1.] if metric == 'V' else [None, None]
        row = dict(id=definition['id'], definition=definition.copy(), point=None, lower=domain[0], upper=domain[1],
                   domain=domain, standard_error=None, exact=False, status='SOURCE_UNAVAILABLE',
                   n_invalid_draws=0,
                   unit='fraction' if metric in ('D', 'H', 'V') else 'kWh-equivalent per valid turbine interval')
        rows.append(row)
        sample_columns.append(None)
        if not availability[left] or (right is not None and not availability[right]):
            continue
        if not valid_metric[fits, left, col].all() or (right is not None and not valid_metric[fits, right, col].all()):
            row['status'] = 'SOURCE_INVALID'
            continue
        if n_point == 0:
            row['status'] = 'ZERO_OBSERVED_DENOMINATOR'
            continue
        # Form each paired daily contrast before summing large nearly equal totals.
        # The estimator, full family, variance guard and all scientific thresholds
        # are unchanged; only the floating-point evaluation order differs.
        daily_contrast = data[fits, left, :, col]
        if right is not None:
            daily_contrast = daily_contrast - data[fits, right, :, col]
        daily_contrast = daily_contrast.mean(axis=0)
        point_num = float(daily_contrast.sum())
        draw_num = weights @ daily_contrast
        point_den = n_point
        draw_den = n_draw
        scale = RHO / cstar if metric == 'H' else 1.
        if metric == 'D':
            point_den = float(np.mean(totals[:, right, 0]))
            draw_den = np.mean(draw_totals[:, :, right, 0], axis=1)
            if point_den == 0:
                row['status'] = 'ZERO_OBSERVED_COST_DENOMINATOR'
                continue
        row['point'] = float(scale * point_num / point_den)
        invalid_n = n_draw == 0
        invalid_cost = draw_den == 0 if metric == 'D' else np.zeros(n_boot, dtype=bool)
        row['n_invalid_draws'] = int(np.count_nonzero(invalid_n | invalid_cost))
        if invalid_n.any():
            row['status'] = 'ZERO_DRAW_DENOMINATOR'
            continue
        if invalid_cost.any():
            row['status'] = 'ZERO_DRAW_COST_DENOMINATOR'
            continue
        exact = right is not None and find(left) == find(right)
        if exact:
            # The explicit full-ledger alias, or self-difference, is structural.
            row.update(point=0., lower=0., upper=0., standard_error=0., exact=True, status='EXACT_ALGEBRAIC_ZERO')
            continue
        with np.errstate(over='ignore', divide='ignore', invalid='ignore'):
            sample = scale * draw_num / draw_den
            sd = float(np.std(sample, ddof=1))
        if not np.isfinite(row['point']) or not np.isfinite(sample).all() or not np.isfinite(sd):
            row.update(status='NUMERIC_UNRESOLVED', point=None if not np.isfinite(row['point']) else row['point'])
            continue
        row['standard_error'] = sd
        if sd <= 1e-14:
            row['status'] = 'ZERO_EMPIRICAL_VARIANCE'
            continue
        row['status'] = 'ESTIMABLE_APPROX'
        sample_columns[-1] = sample

    usable = [i for i, row in enumerate(rows) if row['status'] == 'ESTIMABLE_APPROX']
    critical = None
    if usable:
        maxima = np.zeros(n_boot)
        for i in usable:
            maxima = np.maximum(maxima, np.abs(sample_columns[i] - rows[i]['point']) / rows[i]['standard_error'])
        critical = float(np.quantile(maxima, 1 - ALPHA, method='higher'))
        for i in usable:
            row = rows[i]
            width = critical * row['standard_error']
            row['lower'] = max(-np.inf if row['domain'][0] is None else row['domain'][0], row['point'] - width)
            row['upper'] = min(np.inf if row['domain'][1] is None else row['domain'][1], row['point'] + width)
    lookup = {row['id']: row for row in rows}
    qualification = {}
    for j, name in enumerate(names):
        cost = _decision(lookup[f'Q:{j}:D'], THRESHOLDS['cost_noninferiority'])
        h = _and([_decision(lookup[f'Q:{j}:H:{fit_id}'], THRESHOLDS['signed_H']) for fit_id in SEED_IDS])
        risk = _and([_decision(lookup[f'Q:{j}:V:{fit_id}'], THRESHOLDS['absolute_risk']) for fit_id in SEED_IDS])
        qualification[name] = dict(qualified=_and([cost, h, risk]), cost_noninferior=cost,
                                   five_instance_H_noninferior=h, absolute_risk_qualified=risk,
                                   important_cost_gain_vs_ref=_decision(lookup[f'Q:{j}:D'], -.01, strict=True))
    comparison_labels = []
    for j, (left, right) in enumerate(pairs):
        gain = _decision(lookup[f'E:{j}:D'], -.01, strict=True)
        ni = _decision(lookup[f'E:{j}:D'], .01)
        u = _decision(lookup[f'E:{j}:U'], 0, strict=True)
        v = _decision(lookup[f'E:{j}:V'], 0, strict=True)
        h = _and([_decision(lookup[f'E:{j}:H:{fit_id}'], .001) for fit_id in SEED_IDS])
        lq, rq = (qualification[names[p]]['absolute_risk_qualified'] for p in (left, right))
        conditional = _and([ni, u, v, h])
        comparison_labels.append(dict(left=names[left], right=names[right], important_cost_gain=gain,
                                      cost_noninferiority=ni, U_benefit=u, V_benefit=v,
                                      five_instance_H_noninferiority=h, left_absolute_risk_qualified=lq,
                                      right_absolute_risk_qualified=rq, joint_gain=_and([gain, h, lq]),
                                      legacy_pair_joint_gain=_and([gain, h, lq, rq]),
                                      descriptive_conditional_protection=conditional,
                                      qualified_joint_protection=_and([conditional, lq, rq])))

    source = hashlib.sha256()
    source.update(np.ascontiguousarray(data, dtype='<f8').tobytes())
    source.update(np.ascontiguousarray(count, dtype='<f8').tobytes())
    source.update(json.dumps(dict(names=names, availability=availability), sort_keys=True).encode())
    return dict(schema='stable-contrast-inference-v1', arithmetic='paired daily differences before fit averaging and weather aggregation', scientific_thresholds_changed=False, metric_order=list(METRICS), policy_names=names,
                available=availability, coordinates=rows, nominal_coordinate_ids=[x['id'] for x in rows],
                family_size=len(rows), family_sha256=_hash_json(family), source_sha256=source.hexdigest(),
                family_definition=family, qualification=qualification, comparisons=comparison_labels,
                alias_verification=alias_verification,
                span=span, primary=span == 3, n_boot=int(n_boot), resampling_seed=int(seed),
                production_draw_specification=n_boot == 20000 and seed == 20261022,
                bootstrap_indices_sha256=hashlib.sha256(indices.astype('<i8').tobytes()).hexdigest(),
                bootstrap_weights_sha256=hashlib.sha256(weights.astype('<i8').tobytes()).hexdigest(),
                n_days=35, n_fixed_fits=5, fixed_fit_ids=list(SEED_IDS), n_observed_cells=n_point,
                resampling_unit='shared natural weather day', critical_value=critical,
                family_status='EXPLORATORY_INTERVALS_SUPPLIED' if usable else 'NO_ESTIMABLE_INTERVALS',
                estimable_coordinate_count=len(usable), thresholds=THRESHOLDS.copy(),
                cstar_report_only=float(cstar), selection_adjusted=False, independent_confirmation=False,
                coverage_certified=False, deployment_certified=False,
                inference_target='Five fixed fits, shared weather-day approximation, conditional on the realized update trajectory',
                method='shared circular natural-day maximum standardized deviation; higher quantile',
                missing_draw_policy='No epsilon, deletion, redraw, or replacement; affected coordinate is uninformative')
