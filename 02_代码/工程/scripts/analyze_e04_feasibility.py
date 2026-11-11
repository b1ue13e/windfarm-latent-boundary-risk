"""Read-only, post-hoc decomposition of the frozen E04 feasibility result.

The registered selector is imported unchanged. Additional shared-day resampling
is exploratory sensitivity analysis, never a replacement selection rule.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from repo_paths import Path, repository_root

import numpy as np

ROOT = Path(repository_root())
POLICIES = ('B', 'C', 'D', 'D10')
SEEDS = (201, 202, 203, 204, 205)
ALPHA = 0.05
V_MAX = 0.10
PRIMARY_SEED = 20261017
STABILITY_SEED = 20261018
SENSITIVITY_SEED = 20261019
N_PRIMARY = 20_000
N_STABILITY = 10_000


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_arrays(counts, violations):
    if counts.shape != violations.shape or counts.ndim != 2:
        raise ValueError('counts and violations must have matching seed/day shapes')
    if not np.isfinite(counts).all() or (counts <= 0).any():
        raise ValueError('daily valid counts must be finite and positive')
    if not np.isfinite(violations).all() or (violations < 0).any() or (violations > counts).any():
        raise ValueError('invalid violation counts')


def decompose_gap(observed, draws, cap):
    lower, upper = np.quantile(draws, [ALPHA, 1 - ALPHA])
    excess = observed - cap
    margin = float(upper) - observed
    total = float(upper) - cap
    return {
        'observed_rate': float(observed),
        'bootstrap_mean': float(np.mean(draws)),
        'bootstrap_sd': float(np.std(draws, ddof=1)),
        'lcb95': float(lower),
        'ucb95': float(upper),
        'percentile_ci95': np.quantile(draws, [0.025, 0.975]).tolist(),
        'observed_excess_pp': float(100 * excess),
        'uncertainty_margin_pp': float(100 * margin),
        'ucb_excess_pp': float(100 * total),
        'uncertainty_fraction_of_ucb_excess': float(margin / total) if total > 0 else None,
        'draw_fraction_at_or_below_cap': float(np.mean(draws <= cap)),
        'lower_bound_above_cap': bool(lower > cap),
    }


def constraint_failures(cost_delta, violation_delta, absolute_violation):
    return [name for name, fails in (
        ('cost_delta', cost_delta > 0.0),
        ('violation_delta', violation_delta > 0.0),
        ('absolute_violation', absolute_violation > V_MAX),
    ) if fails]


def day_summary(counts, violations):
    validate_arrays(counts, violations)
    n = counts.sum(axis=0)
    v = violations.sum(axis=0)
    rates = v / n
    total_n, total_v = n.sum(), v.sum()
    leave_out = (total_v - v) / (total_n - n)
    seed_rates = violations.sum(axis=1) / counts.sum(axis=1)
    correlations = np.corrcoef(violations / counts)
    cross = correlations[np.triu_indices(len(counts), 1)]
    top = np.argsort(rates)[::-1][:5]
    return {
        'observed_rate': float(total_v / total_n),
        'n_seed_cells': int(total_n),
        'n_cells_per_seed': counts.sum(axis=1).astype(int).tolist(),
        'n_unique_day_positions': len(n),
        'seed_rates': seed_rates.tolist(),
        'seeds_above_cap': int(np.sum(seed_rates > V_MAX)),
        'pooled_days_above_cap': int(np.sum(rates > V_MAX)),
        'daily_rate_min': float(rates.min()),
        'daily_rate_max': float(rates.max()),
        'daily_rate_sd': float(rates.std(ddof=1)),
        'cross_seed_daily_correlation_min': float(cross.min()),
        'cross_seed_daily_correlation_max': float(cross.max()),
        'lag1_daily_rate_correlation': float(np.corrcoef(rates[:-1], rates[1:])[0, 1]) if len(n) > 2 else None,
        'leave_one_day_out_min': float(leave_out.min()),
        'leave_one_day_out_max': float(leave_out.max()),
        'leave_one_day_out_above_cap_count': int(np.sum(leave_out > V_MAX)),
        'top5_daily_rate_block_positions_1based': (top + 1).tolist(),
        'top5_daily_rates': rates[top].tolist(),
        'top5_rate_days_fraction_of_all_violations': float(v[top].sum() / total_v),
        'daily_rates': rates.tolist(),
        'daily_n_across_seeds': n.astype(int).tolist(),
        'daily_violations_across_seeds': v.astype(int).tolist(),
    }


def sensitivity_draws(counts, violations, n_boot, seed, mode, length):
    """Keep day positions common across selected seeds; preserve local pairing."""
    validate_arrays(counts, violations)
    rng = np.random.default_rng(seed)
    ns, nd = counts.shape
    draws = np.empty(n_boot)
    for i in range(n_boot):
        seeds = rng.integers(0, ns, ns) if mode != 'days_only' else np.arange(ns)
        if mode == 'seed_only':
            days = np.arange(nd)
        else:
            starts = rng.integers(0, nd, (nd + length - 1) // length)
            days = ((starts[:, None] + np.arange(length)) % nd).ravel()[:nd]
        draws[i] = violations[np.ix_(seeds, days)].sum() / counts[np.ix_(seeds, days)].sum()
    return draws


def load_selector():
    code = ROOT / 'experiments/E04/code'
    sys.path.insert(0, str(code))
    spec = importlib.util.spec_from_file_location('frozen_e04_selector', code / 'select_e04_v2.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(input_root, output_dir):
    if output_dir.exists():
        raise FileExistsError('Use a new output directory; prior analysis is never overwritten')
    if output_dir.resolve().is_relative_to(input_root.resolve()):
        raise ValueError('Diagnostic output must be outside the frozen result directory')
    selection_path = input_root / 'e04_v2_selection.json'
    manifest_path = input_root / 'e04_v2_output_manifest.json'
    receipt_path = input_root / 'e04_v2_execution_receipt.json'
    plan_path = input_root / 'e04_v2_execution_plan.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    for key, path in [('output_manifest', manifest_path), ('execution_plan', plan_path)]:
        if sha256(path) != receipt[key]['sha256'].lower():
            raise ValueError(f'Receipt {key} hash mismatch')
    if receipt['status'] != 'EXECUTED' or receipt['exit_code'] != 0:
        raise ValueError('Input receipt does not record successful execution')
    expected = {entry['path']: entry['sha256'].lower() for entry in manifest['files']}
    receipt_outputs = {entry['path']: entry['sha256'].lower() for entry in receipt['outputs']}
    if expected != receipt_outputs:
        raise ValueError('Receipt and manifest output sets differ')
    array_paths = [input_root / f'seed{s}_full_policy_day_blocks.npz' for s in SEEDS]
    for path in array_paths:
        if sha256(path) != expected[path.name]:
            raise ValueError(f'Input array hash mismatch: {path.name}')
    selector = load_selector()
    frozen_paths = [*array_paths, selection_path, manifest_path, receipt_path, plan_path,
                    ROOT / 'experiments/E04/code/select_e04_v2.py',
                    ROOT / 'experiments/E05/results/selector_stability.json']
    before = {str(p.relative_to(ROOT)): sha256(p) for p in frozen_paths}
    stored = json.loads(selection_path.read_text(encoding='utf-8'))
    rows = selector.load_rows(input_root)
    counts = np.stack([r['n'] for r in rows])
    if counts.shape != (5, 35) or not all(np.array_equal(counts[0], row) for row in counts):
        raise ValueError('Expected five seeds with aligned, identical 35-day valid counts')
    started = datetime.now(timezone(timedelta(hours=8))).isoformat()
    primary = selector.primary_ucb(rows, np.random.default_rng(PRIMARY_SEED))
    policies = {}
    for p in POLICIES:
        violations = np.stack([r[f'{p}_viol'] for r in rows])
        daily = day_summary(counts, violations)
        gap = decompose_gap(daily['observed_rate'], primary[p]['v'], V_MAX)
        actual_cost = float(sum(r[f'{p}_cost'].sum() - r['B_cost'].sum() for r in rows))
        actual_dv = gap['observed_rate'] - float(sum(r['B_viol'].sum() for r in rows) / counts.sum())
        # Cost totals intentionally follow the frozen selector's sum over seeds.
        ucb_values = {
            'cost_delta_ucb95_kwh': float(np.quantile(primary[p]['cost'], 0.95)),
            'violation_delta_ucb95': float(np.quantile(primary[p]['dv'], 0.95)),
            'absolute_violation_ucb95': gap['ucb95'],
        }
        for key, value in ucb_values.items():
            if not np.isclose(value, stored['policies'][p][key], rtol=1e-12, atol=1e-12):
                raise ValueError(f'Registered replay mismatch: {p}/{key}')
        point_failures = constraint_failures(actual_cost, actual_dv, gap['observed_rate'])
        ucb_failures = constraint_failures(ucb_values['cost_delta_ucb95_kwh'],
                                          ucb_values['violation_delta_ucb95'], gap['ucb95'])
        sensitivities = {}
        for name, mode, length in [('shared_days_1', 'shared_days', 1),
                                   ('shared_days_circular_3', 'shared_days', 3),
                                   ('shared_days_circular_7', 'shared_days', 7),
                                   ('days_only_1', 'days_only', 1),
                                   ('seed_only', 'seed_only', 1)]:
            draws = sensitivity_draws(counts, violations, N_PRIMARY, SENSITIVITY_SEED, mode, length)
            sensitivities[name] = decompose_gap(gap['observed_rate'], draws, V_MAX)
        policies[p] = {
            'registered_gap': gap, 'daily': daily,
            'point_constraints': {'cost_delta_sum_over_seeds_kwh': actual_cost,
                                  'violation_delta': actual_dv,
                                  'failed': point_failures},
            'registered_ucb_constraints': {**ucb_values, 'failed': ucb_failures},
            'exploratory_sensitivity': sensitivities,
        }
    rng = np.random.default_rng(STABILITY_SEED)
    no_feasible = no_absolute_pass = 0
    per_policy = {p: {'absolute_pass': 0, 'all_pass': 0, 'first_selected': 0} for p in POLICIES}
    for _ in range(N_STABILITY):
        draw = selector.draw_aggregate(rows, rng)
        first = None
        absolute_pass = False
        for p in POLICIES:
            m = draw[p]
            passes_absolute = m['absolute_violation'] <= V_MAX
            absolute_pass |= passes_absolute
            per_policy[p]['absolute_pass'] += int(passes_absolute)
            feasible = not constraint_failures(m['cost_delta'], m['violation_delta'], m['absolute_violation'])
            per_policy[p]['all_pass'] += int(feasible)
            if feasible and first is None:
                first = p
        if first is None:
            no_feasible += 1
        else:
            per_policy[first]['first_selected'] += 1
        no_absolute_pass += int(not absolute_pass)
    if no_feasible / N_STABILITY != stored['selection']['no_feasible_frequency']:
        raise ValueError('E05 diagnostic frequency failed exact reproduction')
    for p in POLICIES:
        if per_policy[p]['first_selected'] / N_STABILITY != stored['selection']['selection_frequency'][p]:
            raise ValueError(f'E05 first-selection frequency mismatch: {p}')
    after = {str(p.relative_to(ROOT)): sha256(p) for p in frozen_paths}
    if before != after:
        raise ValueError('A frozen input changed during analysis')
    result = {
        'status': 'POST_HOC_DIAGNOSTIC_NOT_DEPLOYMENT_CERTIFICATION',
        'started_at_Asia_Shanghai': started,
        'finished_at_Asia_Shanghai': datetime.now(timezone(timedelta(hours=8))).isoformat(),
        'command_argv': [sys.executable, *sys.argv],
        'environment': {'platform': platform.platform(), 'python': platform.python_version(),
                        'numpy': np.__version__, 'cpu': os.environ.get('PROCESSOR_IDENTIFIER', platform.processor()),
                        'execution_device': 'CPU; NumPy only; no CUDA execution',
                        'torch_installed_version': package_version('torch'),
                        'cuda_runtime': 'not used'},
        'config': {'alpha': ALPHA, 'q_star': 0.90, 'rho': 10, 'v_max': V_MAX,
                   'epsilon_C_kwh': 0, 'epsilon_V': 0, 'primary_boot': N_PRIMARY,
                   'stability_boot': N_STABILITY, 'primary_seed': PRIMARY_SEED,
                   'stability_seed': STABILITY_SEED, 'sensitivity_seed': SENSITIVITY_SEED,
                   'sensitivity_boot': N_PRIMARY, 'circular_lengths': [1, 3, 7],
                   'candidate_order': list(POLICIES), 'training_seeds': list(SEEDS),
                   'population': 'WTB Full, original 35 native daily block positions'},
        'input_hashes_before': before, 'input_hashes_after': after,
        'inputs_unchanged': before == after,
        'script_sha256': sha256(Path(__file__)),
        'registered_ucbs_reproduced': True,
        'primary_selection_preserved': stored['selection']['status'],
        'policies': policies,
        'stability_diagnostic': {
            'no_feasible_count': no_feasible, 'no_feasible_frequency': no_feasible / N_STABILITY,
            'no_policy_passes_absolute_count': no_absolute_pass,
            'absolute_failure_fraction_of_no_feasible': no_absolute_pass / no_feasible,
            'some_absolute_pass_but_all_joint_fail_count': no_feasible - no_absolute_pass,
            'policy_counts': per_policy,
            'meaning': 'Constraints on resampled aggregate metrics; not nested UCB selection or a future failure probability',
        },
        'limitations': [
            'Observed exceedance is not an identified true population calibration bias.',
            'Uncertainty shares decompose UCB distance arithmetically; they are not causal probabilities.',
            'Bounds are percentile diagnostics conditional on 35 observed blocks and the resampling assumptions; not simultaneous confidence guarantees.',
            'Registered bootstrap samples days independently within each selected training seed; same underlying test days recur across seeds.',
            'Shared-day sensitivity assumes same block position denotes the same test period across seeds, as the replay constructs it; arrays contain no calendar timestamps.',
            'Circular 3/7-day sensitivity wraps the observed series, has few effective blocks, and is exploratory, not preregistered.',
            'Leave-one-day-out is a diagnostic only; no day is removed from selection.',
            'No wind-speed, ramp, actual dispatch actions or time-step shortfall values are in these arrays; regime causes and a recalibrated policy cannot be identified.',
            'Independent scientific review remains pending; no external-site generalization claim is made.',
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / 'diagnostic.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    with (output_dir / 'gap_decomposition.csv').open('w', newline='', encoding='utf-8') as handle:
        fields = ['policy', *policies['B']['registered_gap'].keys()]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for p in POLICIES:
            writer.writerow({'policy': p, **policies[p]['registered_gap']})
    with (output_dir / 'daily_rates.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['block_position_1based', 'n_across_seeds', *[p + '_viol' for p in POLICIES], *[p + '_rate' for p in POLICIES]])
        for d in range(35):
            writer.writerow([d + 1, policies['B']['daily']['daily_n_across_seeds'][d],
                             *[policies[p]['daily']['daily_violations_across_seeds'][d] for p in POLICIES],
                             *[policies[p]['daily']['daily_rates'][d] for p in POLICIES]])
    print(json.dumps({'output': str(output_dir), 'inputs_unchanged': True,
                      'registered_ucbs_reproduced': True, 'selection': result['primary_selection_preserved'],
                      'gaps': {p: policies[p]['registered_gap'] for p in POLICIES},
                      'stability': result['stability_diagnostic']}, indent=2))
    return result


def package_version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return 'not installed'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-root', type=Path, default=ROOT / 'experiments/E04/results/e04_v2')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    run(args.input_root.resolve(), args.output_dir.resolve())


if __name__ == '__main__':
    main()
