"""Independent block-level audit; no model imports, resampling, or source writes."""
from pathlib import Path
from itertools import combinations
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import platform
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = ROOT / 'analyses/independent_confirmation_execution_20261019'
REC = BASE / 'recovered'
RESULTS = REC / 'results'
INPUTS = {}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(p):
    INPUTS[str(p.relative_to(ROOT))] = sha(p)
    return json.loads(p.read_text(encoding='utf-8'))

def select(g, epsilon):
    lo, hi = np.array(g['risk_lower']), np.array(g['risk_upper'])
    rr = np.array(g['relative_ratio_upper'], float)
    possible = np.where(np.all(lo <= .1, axis=0))[0]
    qualified = np.where(np.all(hi <= .1, axis=0))[0]
    eligible = [int(i) for i in qualified if np.max(rr[i, possible]) <= epsilon]
    resources = [tuple(x) for x in g['resources']]
    minimum = min((resources[i] for i in eligible), default=None)
    chosen = [i for i in eligible if resources[i] == minimum]
    smaller = [i for i, r in enumerate(resources) if chosen and r < minimum]
    lower = np.array(g['relative_ratio_lower'], float)
    excluded, unresolved = [], []
    for i in smaller:
        risks = np.where(lo[:, i] > .1)[0].tolist()
        witness = [int(j) for j in qualified if lower[i, j] > epsilon]
        if risks:
            excluded.append((i, 'RISK_LOWER_ABOVE_CAP', risks))
        elif witness:
            j = max(witness, key=lambda j: lower[i, j])
            excluded.append((i, 'COST_LOWER_EXCEEDS_MARGIN_VS_FEASIBLE', j))
        else:
            unresolved.append(i)
    status = ('NO_CERTIFIED_SUFFICIENT_POLICY' if not chosen else
              'MINIMUM_UNRESOLVED' if unresolved else 'FINITE_FAMILY_MINIMUM_IDENTIFIED')
    return chosen, smaller, excluded, unresolved, status

def main():
    manifest = read(REC / 'export_manifest.json')
    for name, item in manifest.items():
        p = REC / name
        assert p.stat().st_size == item['bytes'] and sha(p) == item['sha256'], name
    cfg = read(ROOT / 'experiments/independent_confirmation_execution_20261019/protocol.json')
    primary = read(RESULTS / 'aggregate/primary.json')
    secondary = {s: read(RESULTS / f'aggregate/secondary_span{s}.json')['results'] for s in (3, 1, 7)}
    history = read(RESULTS / 'chosen/choices.json')['groups']
    subset = {'Common': ((), 0)}
    for size in (1, 2, 3):
        for channels in combinations(range(3), size):
            for length in (1, 6, 36):
                subset[''.join('WPQ'[c] for c in channels) + str(length)] = (channels, length)
    tasks = []
    for condition in cfg['conditions']:
        for seed in cfg['seeds']:
            for name in (list(subset) if condition == 'pitch_withheld' else cfg['pressure_subsets']):
                for estimator in ('HGB', 'MLP'):
                    tasks.append(dict(condition=condition, seed=seed, subset=name, estimator=estimator))
            tasks.append(dict(condition=condition, seed=seed, subset='P1', estimator='Persistence'))
    costs, risks, paired_counts, identities = {}, {}, None, set()
    for i, task in enumerate(tasks):
        p = RESULTS / 'evaluate' / str(i)
        meta = read(p / 'metadata.json')
        receipt = read(p / 'receipt.json')
        assert meta['task'] == task == receipt['task'] and receipt['status'] == 'COMPLETE'
        assert not meta['refit']
        identities.add(json.dumps(meta['identity'], sort_keys=True))
        blocks = p / 'blocks.npz'
        INPUTS[str(blocks.relative_to(ROOT))] = sha(blocks)
        with np.load(blocks) as b:
            for qi, q in enumerate(cfg['offset_quantiles']):
                n = b[f'{qi}__count']; days = b[f'{qi}__block_ids']
                if paired_counts is None:
                    paired_counts = (n.copy(), days.copy())
                assert np.array_equal(n, paired_counts[0]) and np.array_equal(days, paired_counts[1])
                loss = b[f'{qi}__loss_sum']; reserve = b[f'{qi}__reserve_sum']; shortage = b[f'{qi}__shortage_sum']
                assert np.max(np.abs(loss - reserve - 10 * shortage)) < 1e-7
                label = f"{task['subset']}/{task['estimator']}/q{q}"
                key = (task['condition'], label, task['seed'])
                costs[key] = float(loss.sum() / n.sum())
                risks[key] = float(b[f'{qi}__violation_sum'].sum() / n.sum())
    assert len(identities) == 1
    max_cost_error = max_risk_error = 0
    for g in secondary[3]:
        for i, label in enumerate(g['labels']):
            c = [costs[g['condition'], label, s] for s in cfg['seeds']]
            v = [risks[g['condition'], label, s] for s in cfg['seeds']]
            max_cost_error = max(max_cost_error, abs(np.mean(c) - g['mean_cost'][i]))
            max_risk_error = max(max_risk_error, np.max(np.abs(np.array(v) - np.array(g['risk_point'])[:, i])))
    assert max_cost_error < 1e-10 and max_risk_error < 1e-15
    cases, fixed, witness_details = [], [], []
    for span, groups in secondary.items():
        for gi, g in enumerate(groups):
            hc = history[gi]
            for registered in g['secondary_retrospective_full_q']:
                eps = registered['epsilon']
                chosen, smaller, excluded, unresolved, status = select(g, eps)
                assert chosen == registered['sufficient_set']['minimum_resource_indices']
                assert smaller == registered['minimum_audit']['smaller']
                assert unresolved == registered['minimum_audit']['unresolved']
                assert status == registered['minimum_audit']['status']
                assert [(x[0], x[1]) for x in excluded] == [(x['index'], x['reason']) for x in registered['minimum_audit']['excluded']]
                cases.append(status)
                choice = hc['sets'][str(eps)]['original_indices']; ref = hc['reference_index']
                refpass = hc['reference_historically_qualified'] and np.all(np.array(g['risk_upper'])[:, ref] <= .1)
                passed = [refpass and np.all(np.array(g['risk_upper'])[:, i] <= .1) and g['relative_ratio_upper'][i][ref] <= eps for i in choice]
                fs = 'NO_HISTORICAL_SELECTION' if not choice else 'ALL_FROZEN_CANDIDATES_CONFIRMED' if all(passed) else 'CONFIRMATION_NOT_ESTABLISHED'
                assert fs == g['historical_frozen_assessment'][str(eps)]['status']
                fixed.append(fs)
                if span == 3 and g['condition'] == 'pitch_withheld' and eps == .02:
                    witness_details = [dict(label=g['labels'][i], reason=reason,
                        witness=(g['labels'][w] if isinstance(w, int) else w)) for i, reason, w in excluded]
    per_seed = [dict(seed=s, candidate_cost=costs['pitch_withheld', primary['labels'][0], s],
        reference_cost=costs['pitch_withheld', primary['labels'][1], s],
        ratio=costs['pitch_withheld', primary['labels'][0], s] / costs['pitch_withheld', primary['labels'][1], s] - 1)
        for s in cfg['seeds']]
    e04 = read(ROOT / 'experiments/E04/results/e04_v2/e04_v2_selection.json')
    summary = dict(status='PASS_BLOCK_ARITHMETIC_AND_STORED_BOUND_LOGIC_ONLY',
        export_members_hashed=len(manifest), evaluation_workers=len(tasks),
        target_count=int(paired_counts[0].sum()), n_day_blocks=len(paired_counts[0]),
        block_ids_first_last=[int(paired_counts[1][0]), int(paired_counts[1][-1])],
        maximum_point_cost_error=max_cost_error, maximum_point_risk_error=float(max_risk_error),
        secondary_case_counts=dict(Counter(cases)), fixed_case_counts=dict(Counter(fixed)),
        primary_per_seed=per_seed, smaller_exclusion_witnesses=witness_details,
        e04=dict(status=e04['selection']['status'], risk_upper={k:v['absolute_violation_ucb95'] for k,v in e04['policies'].items()}),
        raw_actions_present=bool(list((RESULTS/'evaluate').rglob('raw_actions.npz'))),
        scope='No fitting, inference, calibration, raw ZIP reads, bootstrap, or remote access. Confidence interval coverage not certified.')
    for name, digest in INPUTS.items():
        assert sha(ROOT / name) == digest, name
    (OUT / 'recompute_results.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    (OUT / 'recompute_receipt.json').write_text(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),
        command='python research_audit/working/rigor/recompute.py', source_sha256=sha(Path(__file__)),
        python=sys.version, numpy=np.__version__, host=platform.node(), inputs_sha256=INPUTS,
        no_source_or_result_mutations=True, no_fit=True, no_inference=True, no_resampling=True), indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
