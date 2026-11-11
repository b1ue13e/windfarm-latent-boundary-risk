"""Summarize all fixed instances without qualification-based filtering."""
import csv,hashlib,json
from repo_paths import Path, repository_root
import numpy as np


def write_csv(path,rows):
    if not rows:return
    with Path(path).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    root=Path('experiments/mixture_closed_loop_20261024');p=root/'recovered/results/campaign'
    complete=json.loads((p/'completion.json').read_text())
    cfg=json.loads((p/'protocol.json').read_text());freeze=json.loads((p/'FINAL_FREEZE.json').read_text())
    opened=json.loads((p/'EVALUATION_OPEN.json').read_text())
    assert hashlib.sha256((p/'FINAL_FREEZE.json').read_bytes()).hexdigest()==opened['freeze_sha256']
    assert freeze['time_utc']<opened['time_utc']
    ledger=np.load(p/'all_daily_ledger.npz');data=ledger['ledger'];counts=ledger['counts']
    info=json.loads((p/'inference_span3.json').read_text());names=info['policy_names']
    assert len(names)==412 and counts.sum()==672939 and info['family_size']==12522
    assert info['thresholds']==dict(important_cost_gain=.01,cost_noninferiority=.01,signed_H=.001,absolute_risk=.1,alpha=.05)
    values=data.sum(axis=2)/counts.sum();means=values.mean(axis=0)
    points=np.load(p/'evaluation_points.npy');recipes=cfg['recipes'];rows=[];instance_rows=[]
    receipts={(seed,arm):json.loads((p/f'instances/evaluate/{arm}_seed{seed}/receipt.json').read_text())
              for seed in range(201,206) for arm in ['P','Z']}
    for j,r in enumerate(recipes):
        for ai,arm in enumerate(['P','Z']):
            name=f'R{r["id"]:04d}_{arm}';index=names.index(name)
            np.testing.assert_allclose(values[:,index],points[j,:,ai],rtol=0,atol=1e-10,equal_nan=True)
            q=info['qualification'][name];m=means[index]
            rows.append(dict(id=r['id'],policy=name,kind=r['kind'],family=r['family'],goal=r.get('goal','legacy'),arm=arm,
                C=m[0],R=m[1],U=m[2],V=m[3],cost_delta_REF_percent=100*(m[0]/means[0,0]-1),
                U_delta_REF_percent=100*(m[2]/means[0,2]-1),V_delta_REF_pp=100*(m[3]-means[0,3]),
                qualified=str(q['qualified']),cost_noninferior=str(q['cost_noninferior']),
                H_noninferior=str(q['five_instance_H_noninferior']),risk_qualified=str(q['absolute_risk_qualified']),
                important_cost_gain_REF=str(q['important_cost_gain_vs_ref'])))
            for si,seed in enumerate(range(201,206)):
                receipt=receipts[seed,arm]
                m0=points[j,si,ai]
                instance_rows.append(dict(id=r['id'],policy=name,seed=seed,arm=arm,status=receipt['status'][str(r['id'])],
                    C=m0[0],R=m0[1],U=m0[2],V=m0[3],action_sha256=receipt['action_sha256'].get(str(r['id']),'')))
    write_csv(root/'all_candidate_metrics.csv',rows);write_csv(root/'all_instance_metrics.csv',instance_rows)
    endpoint_rows=[]
    for span in [3,1,7]:
        z=json.loads((p/f'inference_span{span}.json').read_text())
        for row in z['coordinates']:
            endpoint_rows.append(dict(span=span,family_size=z['family_size'],id=row['id'],point=row['point'],
                lower=row['lower'],upper=row['upper'],unit=row['unit'],status=row['status']))
    write_csv(root/'all_intervals.csv',endpoint_rows)
    comparison_map={(d['left'],d['right']):d for d in info['comparisons']}
    comparison_ids={(names[l],names[r]):i for i,(l,r) in enumerate(info['family_definition']['comparisons'])}
    lookup={d['id']:d for d in info['coordinates']}
    selected={}
    for role,choice in freeze['historical_roles']['roles'].items():
        arm=role.rsplit('_',1)[1]
        for duty in ['minimum_C_id','minimum_maxV_id']:
            rid=choice[duty];name=f'R{rid:04d}_{arm}';index=names.index(name)
            selected[role+'_'+duty]=dict(id=rid,policy=name,recipe=recipes[rid],metrics=means[index].tolist(),
                qualification=info['qualification'][name])
    controls={}
    for goal,base in [('COST',0),('CAP',3)]:
        for arm in ['P','Z']:
            entries={}
            for suffix,idx in [('exact',base),('fixed',base+1),('EW',base+2)]:
                name=f'R{idx:04d}_{arm}';entries[suffix]=dict(policy=name,metrics=means[names.index(name)].tolist(),qualification=info['qualification'][name])
            pair=(entries['EW']['policy'],entries['fixed']['policy']);ci=lookup[f'E:{comparison_ids[pair]}:D']
            entries['update_vs_fixed']=dict(**comparison_map[pair],relative_cost_point=ci['point'],relative_cost_CI=[ci['lower'],ci['upper']])
            controls[goal+'_'+arm]=entries
    primary=[]
    def percent(value):return None if value is None else 100*value
    for family,base in [('actual_cost',0),('actual_u',3)]:
        for arm in ['P','Z']:
            chosen=selected[family+'_'+arm+'_minimum_C_id'];left=chosen['policy']
            for label,rid in [('exact',base),('fixed',base+1),('EW',base+2)]:
                right=f'R{rid:04d}_{arm}';i=comparison_ids[left,right];d=lookup[f'E:{i}:D']
                primary.append(dict(family=family,arm=arm,id=chosen['id'],left=left,right=right,comparator=label,
                    cost_delta_percent=percent(d['point']),cost_lower_percent=percent(d['lower']),cost_upper_percent=percent(d['upper']),
                    **{k:str(v) for k,v in comparison_map[left,right].items() if k not in ['left','right']}))
    write_csv(root/'historically_selected_comparisons.csv',primary)
    finite=[row for row in rows if np.isfinite(row['C'])]
    best=min(finite,key=lambda row:row['C']) if finite else None
    fitted=[json.loads(f.read_text()) for f in (p/'initializers').rglob('*.json')]
    for row in fitted:assert row['last_label_release']<row['episode_start']
    result=dict(status='ANALYZED_ALL_PREDEFINED_INSTANCES',completion=complete,nominal_family_size=info['family_size'],
        metric_order=['C','R','U','V'],controls=controls,historical_roles=selected,
        best_observed_frozen_recipe=best,best_observed_is_not_historical_selection=True,
        evaluated_instance_rows=len(instance_rows),initializer_fits=len(fitted),
        initializer_numerically_optimal=sum(row['optimal'] for row in fitted),
        complete_qualified_recipes=sum(row['qualified']=='True' for row in rows),
        source_files_unchanged=all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in freeze['source_versions'].items()),
        independent_confirmation=False,field_procurement_claim=False,original_thresholds_changed=False)
    (root/'analysis.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(best_observed=result['best_observed_frozen_recipe'],controls=controls,
        historically_selected=primary,qualified_count=result['complete_qualified_recipes'],
        completed=complete,initializer_fits=len(fitted),optimal_initializers=result['initializer_numerically_optimal']),indent=2))


if __name__=='__main__':main()
