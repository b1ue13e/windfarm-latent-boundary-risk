"""Read-only arithmetic audit: no estimator loading, prediction, fitting or resampling."""
from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import json
import platform
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RESULTS = ROOT / 'analyses/independent_confirmation_execution_20261019/recovered/results'
started = time.perf_counter()
before = {}

def protected(p):
    p = Path(p)
    before[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return p

def read(p):
    return json.loads(protected(p).read_text(encoding='utf-8-sig'))

def dump(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

for name in ['AGENTS.md', 'PROJECT.md', 'docs/SCIENTIFIC_CONTRACT.md',
             '.agents/skills/research-skill/SKILL.md', 'paper_tste_ieee.md',
             'research_audit/08_claim_inventory.md',
             'research_audit/novelty_impact_20261019/claim_freeze.json',
             'windfarm_moe/independent_confirmation.py', 'windfarm_moe/information_subset.py',
             'windfarm_moe/decision_information.py', 'scripts/run_independent_confirmation.py',
             'scripts/run_decision_information_development.py',
             'experiments/independent_confirmation_execution_20261019/historical.pbs',
             'experiments/independent_confirmation_execution_20261019/evaluate.pbs']:
    protected(ROOT / name)
cfg = read(ROOT / 'experiments/independent_confirmation_execution_20261019/protocol.json')
freeze = read(ROOT / 'research_audit/novelty_impact_20261019/claim_freeze.json')
freeze_matches = {name: hashlib.sha256(protected(ROOT/name).read_bytes()).hexdigest() == expected
                  for name, expected in freeze['sources_sha256'].items()}
assert all(freeze_matches.values()), 'Frozen claim source changed'
primary = read(RESULTS / 'aggregate/primary.json')
secondary = read(RESULTS / 'aggregate/secondary_span3.json')['results'][0]
job_status = read(ROOT / 'analyses/independent_confirmation_execution_20261019/final_job_status.json')

def seconds(receipt):
    return (datetime.fromisoformat(receipt['finished_utc']) -
            datetime.fromisoformat(receipt['started_utc'])).total_seconds()

workers, metric_rows, primary_daily, timing = {}, [], {}, []
wanted = {'Common', 'P1', 'WPQ36'}
for folder in sorted((RESULTS / 'historical').iterdir(), key=lambda p: int(p.name)):
    # Metadata first: only the pitch-withheld practical comparator family is inspected.
    meta = read(folder / 'metadata.json')
    task = meta['task']
    if task['condition'] != 'pitch_withheld' or task['subset'] not in wanted:
        continue
    index = folder.name
    historical_receipt = read(folder / 'receipt.json')
    evaluation_receipt = read(RESULTS / 'evaluate' / index / 'receipt.json')
    evaluation_meta = read(RESULTS / 'evaluate' / index / 'metadata.json')
    assert evaluation_meta['task'] == task
    timing.append(dict(task_index=int(index), **task, resource=meta['resource'],
                       fit_seconds=meta['fit_seconds'],
                       historical_stage_seconds=seconds(historical_receipt),
                       evaluation_stage_seconds=seconds(evaluation_receipt),
                       predict_seconds=None, host=evaluation_receipt['host'],
                       backend=evaluation_receipt['backend']))
    if task['estimator'] == 'MLP':
        continue
    with np.load(protected(RESULTS / 'evaluate' / index / 'blocks.npz')) as b:
        for qi, q in enumerate(cfg['offset_quantiles']):
            fields = {k: np.asarray(b[f'{qi}__{k}']) for k in
                      ['count', 'loss_sum', 'reserve_sum', 'shortage_sum', 'violation_sum', 'block_ids']}
            count = int(fields['count'].sum())
            row = dict(task_index=int(index), **task, q=q, count=count,
                       mean_cost=float(fields['loss_sum'].sum()/count),
                       total_loss=float(fields['loss_sum'].sum()),
                       mean_reserve=float(fields['reserve_sum'].sum()/count),
                       mean_shortage=float(fields['shortage_sum'].sum()/count),
                       risk=float(fields['violation_sum'].sum()/count))
            assert np.isclose(row['mean_cost'], row['mean_reserve']+10*row['mean_shortage'])
            metric_rows.append(row)
            if task['subset'] in {'P1', 'WPQ36'} and task['estimator'] == 'HGB' and q == .95:
                primary_daily[(task['subset'], task['seed'])] = fields

def csv_out(name, rows):
    with (OUT/name).open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

csv_out('worker_metrics.csv', metric_rows)
csv_out('worker_timing.csv', timing)
seed_pairs, daily = [], []
for seed in cfg['seeds']:
    a, b = (primary_daily[(subset, seed)] for subset in ['P1', 'WPQ36'])
    assert np.array_equal(a['count'], b['count']) and np.array_equal(a['block_ids'], b['block_ids'])
    ca, cb = float(a['loss_sum'].sum()), float(b['loss_sum'].sum())
    n = int(a['count'].sum())
    seed_pairs.append(dict(seed=seed, count=n, p1_mean_cost=ca/n, reference_mean_cost=cb/n,
                           absolute_mean_premium=(ca-cb)/n, relative_premium=(ca-cb)/cb,
                           total_premium=ca-cb))
    for i, day_id in enumerate(a['block_ids']):
        date = str(np.datetime64('2023-01-01') + np.timedelta64(int(day_id), 'D'))
        daily.append(dict(seed=seed, day_id=int(day_id), date=date, count=int(a['count'][i]),
                          p1_cost=float(a['loss_sum'][i]), reference_cost=float(b['loss_sum'][i]),
                          premium=float(a['loss_sum'][i]-b['loss_sum'][i]),
                          p1_risk=float(a['violation_sum'][i]/a['count'][i]) if a['count'][i] else None,
                          reference_risk=float(b['violation_sum'][i]/b['count'][i]) if b['count'][i] else None))
csv_out('primary_seed_pairs.csv', seed_pairs)
csv_out('primary_days.csv', daily)
for label, j in [(label, j) for j, label in enumerate(secondary['labels'])
                 if label.startswith(('Common/', 'P1/Persistence/', 'P1/HGB/', 'WPQ36/HGB/'))]:
    workers[label] = dict(mean_cost=secondary['mean_cost'][j],
                          max_risk_point=float(np.max(np.asarray(secondary['risk_point'])[:,j])),
                          max_risk_upper=float(np.max(np.asarray(secondary['risk_upper'])[:,j])),
                          resource=secondary['resources'][j])
csv_out('baseline_envelope.csv', [dict(label=k, **v) for k,v in workers.items()])
timing_summary = {}
for subset in wanted:
    for estimator in ['HGB','MLP','Persistence']:
        rows = [r for r in timing if r['subset']==subset and r['estimator']==estimator]
        if rows:
            timing_summary[f'{subset}/{estimator}'] = {name: dict(mean=float(np.mean([r[name] for r in rows])),
                       min=min(r[name] for r in rows),max=max(r[name] for r in rows))
                       for name in ['fit_seconds','historical_stage_seconds','evaluation_stage_seconds']}
            timing_summary[f'{subset}/{estimator}']['hosts'] = sorted(set(r['host'] for r in rows))
with np.load(protected(RESULTS/'unlocked/confirmation.npz')) as forecast:
    shape = forecast['forecast'].shape
    forecast_cells = int(forecast['forecast'].size)
summary = dict(primary=primary, timing_summary=timing_summary,
    primary_seed_pairs=seed_pairs, mean_annual_proxy_premium=float(np.mean([r['total_premium'] for r in seed_pairs])),
    daily_worst_premium=max(daily,key=lambda r:r['premium']),
    daily_worst_risk=max((r for r in daily if r['count']),key=lambda r:r['p1_risk']),
    number_seed_days=len(daily), valid_seed_days=sum(r['count']>0 for r in daily),
    zero_target_seed_days=sum(r['count']==0 for r in daily),
    fraction_valid_seed_days_positive_premium=float(np.mean([r['premium']>0 for r in daily if r['count']])),
    forecast_shape=shape, raw_feature_materialization_columns=148,
    raw_feature_materialization_bytes=forecast_cells*148*4,
    fit_first_index_copy_bytes=cfg['reserve_rows']*148*4,
    p1_raw_width=5, full_raw_width=112, p1_mlp_width=10, full_mlp_width=224,
    raw_width_reduction=1-5/112, standalone_float32_row_bytes={'P1':20,'WPQ36':448},
    actual_hgb_width='UNKNOWN: original model/scaler not exported; missing indicators depend on fit data',
    scheduler=job_status, baselines=workers,
    all_seed_noninferiority_mean_reconstructed=bool(np.allclose(
        [np.mean([r['p1_mean_cost'] for r in seed_pairs]),np.mean([r['reference_mean_cost'] for r in seed_pairs])],
        primary['bounds']['groups'][0]['mean_cost'],rtol=0,atol=1e-12)))
assert summary['all_seed_noninferiority_mean_reconstructed']
dump('practical_derived.json', summary)
after = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in before}
assert before == after, 'Protected inputs changed'
dump('practical_receipt.json', dict(utc=datetime.now(timezone.utc).isoformat(),
    argv=sys.argv, cwd=str(ROOT), python=sys.version, platform=platform.platform(), numpy=np.__version__,
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    frozen_claim_source_matches=freeze_matches,
    no_training=True, no_inference=True, no_resampling=True, no_remote=True,
    seconds=time.perf_counter()-started, sources_sha256_before=before,
    sources_sha256_after=after, all_inputs_unchanged=before==after,
    caveat='Receipt timestamps measure whole historical/evaluation stages, not pure inference; no deployment runtime measurement.'))
print(json.dumps({k:v for k,v in summary.items() if k not in {'primary','scheduler','baselines'}},indent=2))
