"""Frozen historical selection and causal clocks for external confirmation."""
from __future__ import annotations

import numpy as np

from .decision_information import arrived_history, block_totals
from .information_subset import subset_grid, telemetry_columns
from .risk_frontier import near_optimal_set

STEP_NS = 600 * 10**9
START_NS = int(np.datetime64('2023-01-01', 'ns').astype(np.int64))


def anchor_window(first: str, last: str, horizon: int) -> np.ndarray:
    """Last target and its one-step release must precede the next stage."""
    lo, hi = [(int(np.datetime64(x.replace('Z', ''), 'ns').astype(np.int64)) - START_NS) // STEP_NS
              for x in (first, last)]
    return np.arange(max(lo, 41), hi - horizon - 1, dtype=np.int64)


def features(data: np.ndarray, anchors: np.ndarray, forecast: np.ndarray,
             delay: int) -> np.ndarray:
    phase = 2 * np.pi * (anchors % 144) / 144
    nodes = data.shape[1]
    common = np.column_stack((forecast.reshape(-1), np.repeat(np.sin(phase), nodes),
                              np.repeat(np.cos(phase), nodes),
                              np.tile(np.arange(nodes) / max(nodes - 1, 1), len(anchors))))
    history = arrived_history(data, anchors, 36, delay)
    return np.column_stack((common, history.transpose(0, 1, 3, 2).reshape(len(common), -1))).astype(np.float32)


def point_features(data: np.ndarray, anchors: np.ndarray) -> np.ndarray:
    h = arrived_history(data[..., :2], anchors, 36, 0)
    return h.transpose(0, 1, 3, 2).reshape(len(anchors) * data.shape[1], -1)


def task_table(cfg: dict) -> list[dict]:
    result = []
    for condition in cfg['conditions']:
        grid = list(subset_grid()) if condition == 'pitch_withheld' else cfg['pressure_subsets']
        for seed in cfg['seeds']:
            for subset in grid:
                for estimator in ('HGB', 'MLP'):
                    result.append(dict(condition=condition, seed=seed, subset=subset, estimator=estimator))
            result.append(dict(condition=condition, seed=seed, subset='P1', estimator='Persistence'))
    return result


def resource(task: dict, condition: dict) -> list[int]:
    channels, length = subset_grid()[task['subset']]
    if task['estimator'] == 'Persistence':
        return [1, 0, 2]
    return [len(channels) + int(condition['pitch_available']), 1,
            len(telemetry_columns(channels, length, condition['delay_steps'], condition['pitch_available']))]


def totals_for_offsets(shortfall: np.ndarray, raw: np.ndarray, mask: np.ndarray,
                       anchors: np.ndarray, offsets: np.ndarray) -> dict:
    output = {}
    for qi, offset in enumerate(offsets):
        totals = block_totals(shortfall, np.maximum(raw + offset, 0), mask, anchors)
        for key, value in totals.items():
            output[f'{qi}__{key}'] = value
    return output


def historical_selection(envelope: dict, labels: list[str], resources: list[list[int]],
                         quantiles: list[float], epsilons: list[float], cap: float) -> dict:
    """Freeze q, full-information reference and tied policy sets on history only."""
    upper, lower = envelope['risk_upper'], envelope['risk_lower']
    costs, regret = envelope['mean_cost'], envelope['relative_ratio_upper']
    nq = len(quantiles)
    selected, passed = [], []
    for base in range(len(labels) // nq):
        indices = list(range(base * nq, (base + 1) * nq))
        feasible = [i for i in indices if np.all(upper[:, i] <= cap)]
        chosen = min(feasible, key=lambda i: (costs[i], i)) if feasible else indices[-1]
        selected.append(chosen)
        passed.append(bool(feasible))
    idx = np.asarray(selected)
    sets = {}
    for eps in epsilons:
        result = near_optimal_set(lower[:, idx], upper[:, idx], regret[np.ix_(idx, idx)],
                                  passed, [resources[i] for i in idx], eps, cap)
        result['original_indices'] = [int(idx[i]) for i in result['minimum_resource_indices']]
        sets[str(eps)] = result
    full = [i for i, label in enumerate(labels) if label.startswith('WPQ36/')]
    feasible_full = [i for i in full if i in selected and np.all(upper[:, i] <= cap)]
    fallback = [i for i in full if i % nq == nq - 1]
    if not full or not fallback:
        raise ValueError('Full-information reference absent')
    reference = min(feasible_full or fallback, key=lambda i: (costs[i], labels[i]))
    return dict(q_indices=selected, q_historically_qualified=passed, sets=sets,
                reference_index=int(reference), reference_historically_qualified=bool(feasible_full),
                reference_rule='Lowest historical mean cost among risk-qualified historically chosen WPQ36/HGB or MLP; otherwise fixed q.99 diagnostic, explicitly unqualified',
                uses_confirmation=False)


def confirmation_verdict(envelope: dict, selected_positions: list[int], reference_position: int,
                         epsilon: float, cap: float, history_reference_qualified: bool) -> dict:
    """No test-side selection; all historical ties and failures are returned."""
    results = []
    reference_pass = bool(history_reference_qualified and
                          np.all(envelope['risk_upper'][:, reference_position] <= cap))
    for p in selected_positions:
        safe = bool(np.all(envelope['risk_upper'][:, p] <= cap))
        cost_pass = bool(envelope['relative_ratio_upper'][p, reference_position] <= epsilon)
        results.append(dict(position=p, risk_pass=safe, paired_cost_pass=cost_pass,
                            reference_risk_pass=reference_pass,
                            confirmed=bool(safe and cost_pass and reference_pass)))
    status = 'NO_HISTORICAL_SELECTION' if not results else (
        'ALL_FROZEN_CANDIDATES_CONFIRMED' if all(r['confirmed'] for r in results) else 'CONFIRMATION_NOT_ESTABLISHED')
    return dict(status=status, candidates=results, epsilon=epsilon,
                scope='Fixed historical choices against frozen full-information reference only; not finite-family minimum or deployment safety')
