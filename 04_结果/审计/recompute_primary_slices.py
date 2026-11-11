"""Descriptive temporal slices from archived blocks; no new intervals/selection."""
from pathlib import Path
import csv
import datetime as dt
import hashlib
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'analyses/independent_confirmation_execution_20261019/recovered/results/evaluate'
OUT=ROOT/'research_audit/derived'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[];identities={};raw=[]
    for worker in sorted(BASE.iterdir(),key=lambda p:int(p.name)):
        meta=json.loads((worker/'metadata.json').read_text())
        task=meta['task']
        if task['condition']!='pitch_withheld' or task['estimator']!='HGB' or task['subset'] not in ('P1','WPQ36'):
            continue
        for p in (worker/'metadata.json',worker/'blocks.npz'):
            identities[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
        with np.load(worker/'blocks.npz',allow_pickle=False) as arrays:
            days=arrays['2__block_ids'].astype(int)
            dates=np.datetime64('2023-01-01')+days.astype('timedelta64[D]')
            months=dates.astype('datetime64[M]').astype(str)
            all_masks={'all_2025':np.ones(len(days),bool)}
            all_masks.update({month:months==month for month in sorted(set(months))})
            for label,mask in all_masks.items():
                n=float(arrays['2__count'][mask].sum())
                row=dict(seed=task['seed'],policy=task['subset']+'/HGB/q0.95',period=label,
                    n=n,cost=float(arrays['2__loss_sum'][mask].sum()/n),
                    violation=float(arrays['2__violation_sum'][mask].sum()/n),
                    reserve=float(arrays['2__reserve_sum'][mask].sum()/n),
                    shortage=float(arrays['2__shortage_sum'][mask].sum()/n),
                    artifact=(worker/'blocks.npz').relative_to(ROOT).as_posix())
                rows.append(row)
    with (OUT/'primary_temporal_by_seed.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    for period in sorted({r['period'] for r in rows}):
        a=[r for r in rows if r['period']==period and r['policy'].startswith('P1/')]
        b=[r for r in rows if r['period']==period and r['policy'].startswith('WPQ36/')]
        assert len(a)==len(b)==5
        ca=float(np.mean([r['cost'] for r in a])); cb=float(np.mean([r['cost'] for r in b]))
        raw.append(dict(period=period,candidate_mean_cost=ca,reference_mean_cost=cb,
            relative_cost=ca/cb-1,candidate_max_seed_violation=max(r['violation'] for r in a),
            reference_max_seed_violation=max(r['violation'] for r in b),
            per_seed_relative_cost=[x['cost']/y['cost']-1 for x,y in zip(a,b)]))
    annual=next(r for r in raw if r['period']=='all_2025')
    expected=json.loads((ROOT/'analyses/independent_confirmation_execution_20261019/derived/summary.json').read_text())
    assert abs(annual['candidate_mean_cost']-expected['mean_cost'][0])<1e-10
    assert abs(annual['reference_mean_cost']-expected['mean_cost'][1])<1e-10
    assert abs(annual['relative_cost']-expected['relative_cost_point'])<1e-12
    for name,value in identities.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value
    receipt=dict(utc=dt.datetime.now(dt.timezone.utc).isoformat(),rows=raw,inputs_sha256=identities,
        scope='Post-hoc monthly descriptions, no new confidence interval, selection, fit or resampling. Does not change annual primary estimand.')
    (OUT/'primary_temporal_summary.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(raw,indent=2))

if __name__=='__main__':main()
