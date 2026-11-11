"""Independent point arithmetic and three-valued label checks on sealed sums."""
import hashlib,json
from repo_paths import Path, repository_root
import numpy as np


def conjunction(values):
    if False in values:return False
    return None if None in values else True


def decision(row,cap,strict=False):
    if row['status'] not in ['ESTIMABLE_APPROX','EXACT_ALGEBRAIC_ZERO']:return None
    if row['upper'] is not None and (row['upper']<cap if strict else row['upper']<=cap):return True
    if row['lower'] is not None and (row['lower']>=cap if strict else row['lower']>cap):return False
    return None


def main():
    root=Path('experiments/mixture_closed_loop_20261024');p=root/'recovered/results/campaign'
    z=np.load(p/'all_daily_ledger.npz');data=z['ledger'];counts=z['counts']
    assert data.shape==(5,412,35,4) and counts.sum()==672939
    assert np.isfinite(data).all()
    assert np.allclose(data[...,0],data[...,1]+10*data[...,2],rtol=1e-12,atol=1e-8)
    assert np.all(data[...,3]==np.floor(data[...,3])) and np.all(data[...,3]<=counts)
    complete=json.loads((p/'completion.json').read_text())
    assert complete['complete_per_phase']==dict(inner=1980,outer=1980,evaluate=1980)
    for phase in ['inner','outer','evaluate']:
        for seed in range(201,206):
            for arm in ['P','Z']:
                d=json.loads((p/f'instances/{phase}/{arm}_seed{seed}/receipt.json').read_text())
                assert set(d['status'])==set(map(str,range(198)))
                assert all(v=='COMPLETED' for v in d['status'].values())
    fits=list((p/'initializers').rglob('*.json'));assert len(fits)==60
    for f in fits:
        d=json.loads(f.read_text());assert d['last_label_release']<d['episode_start']
        w=np.asarray(d['weights']);assert (w>=0).all() and abs(w.sum()-1)<1e-12
        assert d['optimal'] and d['gap']<=d['numerical_tolerance']
    point_error=0.;label_checks=0
    totals=data.sum(axis=2)
    for span in [3,1,7]:
        info=json.loads((p/f'inference_span{span}.json').read_text());names=info['policy_names'];lookup={r['id']:r for r in info['coordinates']}
        assert info['family_size']==12522 and len(lookup)==12522
        assert info['n_boot']==20000 and info['resampling_seed']==20261022
        for row in info['coordinates']:
            d=row['definition'];left,right,fit,metric=(d[k] for k in ['left','right','fit','metric'])
            col=0 if metric=='D' else 2 if metric=='H' else ['C','R','U','V'].index(metric)
            fits_ix=list(range(5)) if fit is None else [fit]
            numerator=np.mean(totals[fits_ix,left,col]-(0 if right is None else totals[fits_ix,right,col]))
            denominator=np.mean(totals[:,right,0]) if metric=='D' else counts.sum()
            scale=10/42.058880543674675 if metric=='H' else 1
            observed=float(numerator*scale/denominator)
            if row['point'] is not None:point_error=max(point_error,abs(observed-row['point']))
        qualifications={}
        for j,name in enumerate(names):
            cost=decision(lookup[f'Q:{j}:D'],.01)
            h=conjunction([decision(lookup[f'Q:{j}:H:{seed}'],.001) for seed in range(201,206)])
            risk=conjunction([decision(lookup[f'Q:{j}:V:{seed}'],.1) for seed in range(201,206)])
            expected=dict(qualified=conjunction([cost,h,risk]),cost_noninferior=cost,
                five_instance_H_noninferior=h,absolute_risk_qualified=risk,
                important_cost_gain_vs_ref=decision(lookup[f'Q:{j}:D'],-.01,True))
            assert expected==info['qualification'][name];qualifications[name]=expected;label_checks+=1
        for i,pair in enumerate(info['comparisons']):
            gain=decision(lookup[f'E:{i}:D'],-.01,True);ni=decision(lookup[f'E:{i}:D'],.01)
            u=decision(lookup[f'E:{i}:U'],0,True);v=decision(lookup[f'E:{i}:V'],0,True)
            h=conjunction([decision(lookup[f'E:{i}:H:{seed}'],.001) for seed in range(201,206)])
            lq=qualifications[pair['left']]['absolute_risk_qualified'];rq=qualifications[pair['right']]['absolute_risk_qualified']
            expected=dict(important_cost_gain=gain,cost_noninferiority=ni,U_benefit=u,V_benefit=v,
                five_instance_H_noninferiority=h,left_absolute_risk_qualified=lq,right_absolute_risk_qualified=rq,
                joint_gain=conjunction([gain,h,lq]),legacy_pair_joint_gain=conjunction([gain,h,lq,rq]),
                descriptive_conditional_protection=conjunction([ni,u,v,h]),
                qualified_joint_protection=conjunction([ni,u,v,h,lq,rq]))
            assert all(pair[k]==value for k,value in expected.items());label_checks+=1
    assert point_error<1e-10
    freeze=json.loads((p/'FINAL_FREEZE.json').read_text());opened=json.loads((p/'EVALUATION_OPEN.json').read_text())
    assert freeze['time_utc']<opened['time_utc']
    assert hashlib.sha256((p/'FINAL_FREEZE.json').read_bytes()).hexdigest()==opened['freeze_sha256']
    result=dict(status='VERIFIED_POINT_ARITHMETIC_LABELS_AND_INSTANCE_COMPLETENESS',
        scored_instances=5940,point_error=point_error,label_groups_checked=label_checks,
        original_thresholds_changed=False,independent_statistics_implementation_imported=False,
        bootstrap_critical_value_independently_recomputed=False,coverage_certified=False)
    (root/'NUMERICAL_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(result)


if __name__=='__main__':main()
