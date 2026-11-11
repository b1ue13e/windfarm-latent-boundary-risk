"""Read-only audit of sealed EM1_008_Z comparisons; no bootstrap or action run."""
from repo_paths import Path, repository_root
import sys,json,csv,hashlib,argparse
import numpy as np
ROOT=Path(repository_root());sys.path.insert(0,str(ROOT))
from windfarm_moe.stable_contrast_inference import _decision

LEFT='EM1_008_Z';SAFE='EM1_000_P'
CONTROLS=[SAFE,'EM1_007_Z','EM1_022_Z','EM1_008_P','BR009_P','BR009_Z','R0182_P',
    *[f'EM1_{j:03d}_P' for j in [1,2,3,4,5,6,7,20,21,22,23]],'GR002_P']

def valid_interval(row):
    if row['status'] not in ('ESTIMABLE_APPROX','EXACT_ALGEBRAIC_ZERO') or row['lower'] is None or row['upper'] is None:
        return None
    return [float(row['lower']),float(row['upper'])]

def subtract_intervals(left,right):
    if left is None or right is None:return None
    return [left[0]-right[1],left[1]-right[0]]

def ratio_contrast_intervals(left,right):
    """D(G,P)=(1+D(G,S))/(1+D(P,S))-1, bounded by the same joint box."""
    if left is None or right is None or 1+right[0]<=0 or 1+left[0]<0:return None
    return [(1+left[0])/(1+right[1])-1,(1+left[1])/(1+right[0])-1]

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def run(root,out):
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    parent=root/'experiments/endpoint_match_20261025'
    r=parent/'recovered/results/campaign'
    frozen=read(r/'FINAL_FREEZE.json');identities={}
    def bind(p):identities[str(p.relative_to(root))]=dict(bytes=p.stat().st_size,sha256=digest(p))
    for p in [r/'FINAL_FREEZE.json',r/'EVALUATION_OPEN.json',r/'all_daily_ledger.npz',r/'all_policy_names.json',r/'HISTORY_SELECTION.json',parent/'protocol.json']:
        bind(p)
    with np.load(r/'all_daily_ledger.npz') as z:
        data=z['ledger'].copy();counts=z['counts'].copy();days=z['day_ids'].copy()
    info=read(r/'all_policy_names.json');names=info['names'];total=counts.sum()
    points=data.sum(2)/total;means=points.mean(0);li=names.index(LEFT);si=names.index(SAFE)
    metric_names=['C','R','U','V']
    perfit=[]
    for seed in range(201,206):
        shard=(seed-201)*3+2
        version=frozen['histories'][shard]['versions']['outer']
        item=next(m for m in version['models'] if m['snapshot']=='D' and m['recipe_id']==8)
        rp=r/item['receipt_path'];bind(rp)
        if digest(rp)!=item['receipt_sha256']:raise ValueError('Frozen receipt changed')
        meta=read(rp)
        model=parent/'frozen_weights/results/campaign'/item['path'];bind(model)
        if digest(model)!=item['sha256']:raise ValueError('Frozen model changed')
        paths=[r/'outer/instances/evaluate'/f'{arm}_seed{seed}/receipt.json' for arm in ['Z','P']]
        for p in paths:bind(p)
        zrec,prec=[read(p) for p in paths]
        assert zrec['target_sha256']==prec['target_sha256'] and zrec['mask_sha256']==prec['mask_sha256']
        gate=zrec['policies']['8'];safe=prec['policies']['0'];globalrule=zrec['policies']['7']
        diag=gate['diagnostics']['D'];alphas=meta['leaf_alphas']
        zero=all(float(v)==0. for v in alphas.values())
        exact_sha=gate['action_sha256']==safe['action_sha256']
        exact_daily=np.array_equal(data[seed-201,li],data[seed-201,si])
        if zero and not (exact_sha and exact_daily):raise ValueError('Algebraic identity contradicted by actions')
        support=diag['leaf_support'];all_cells=sum(support.values())
        use=sum(int(n) for leaf,n in support.items() if float(alphas[leaf])>0)
        perfit.append(dict(seed=seed,leaf_alphas=alphas,prediction_grid_cells=all_cells,
            scored_cells=int(total),full_grid_release_fraction=use/all_cells,
            full_grid_release_fraction_is_not_scored_population_fraction=True,
            structurally_safe=zero,evaluation_action_sha_equal=exact_sha,complete_daily_ledger_equal=exact_daily,
            action_sha256=gate['action_sha256'],safe_action_sha256=safe['action_sha256'],
            global_action_sha_equal=gate['action_sha256']==globalrule['action_sha256'],
            exact_H_zero_certificate=zero and exact_sha and exact_daily,
            delta_metrics_vs_safe=(points[seed-201,li]-points[seed-201,si]).tolist(),
            source_model_sha256=item['sha256'],source_receipt_sha256=item['receipt_sha256']))
    save(out/'PER_FIT_IDENTITY_CERTIFICATES.json',perfit)
    windows={}
    for arm in ['P','Z']:
        records=[]
        for seed in range(201,206):
            path=r/'outer/instances/outer'/f'{arm}_seed{seed}/receipt.json';bind(path);records.append(read(path))
        windows[arm]={}
        for rid in range(24):
            summary={}
            for win in ['C','E']:
                deltas=[]
                for rec in records:
                    val=rec['policies'][str(rid)]['validation_windows'][win]
                    base=rec['policies']['0']['validation_windows'][win]
                    deltas.append([val[k]-base[k] for k in ['C','U','V']])
                summary[win]=dict(zip(['delta_C','delta_U','delta_V'],np.mean(deltas,0).tolist()))
            windows[arm][str(rid)]=summary
    points_rows=[];concentration={}
    for name in CONTROLS:
        j=names.index(name);ds=(data[:,li]-data[:,j]).mean(0)
        loo=np.asarray([(ds.sum(0)-row)/(total-count) for row,count in zip(ds,counts)])
        row=dict(policy=name,**dict(zip(metric_names,means[j].tolist())))
        row.update({f'gate_minus_control_{k}':float(means[li,kj]-means[j,kj]) for kj,k in enumerate(metric_names)})
        row['gate_cost_change_pct']=float(100*(means[li,0]/means[j,0]-1))
        points_rows.append(row)
        concentration[name]=dict(per_fit_delta=(points[:,li]-points[:,j]).tolist(),
            lower_cost_days=int(np.sum(ds[:,0]<0)),lower_U_days=int(np.sum(ds[:,2]<0)),
            leave_one_day_out_delta_C_range=[float(loo[:,0].min()),float(loo[:,0].max())],
            leave_one_day_out_delta_U_range=[float(loo[:,2].min()),float(loo[:,2].max())],
            descriptive_only=True,no_resampling=True)
    with (out/'CONTROL_POINTS.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(points_rows[0]));w.writeheader();w.writerows(points_rows)
    save(out/'DAILY_AND_FIT_DIAGNOSTICS.json',concentration);save(out/'HISTORY_WINDOWS.json',windows)
    review={}
    for span in (1,3,7):
        path=r/f'inference_span{span}.json';bind(path);inf=read(path)
        assert inf['source_sha256']==read(r/'inference_span3.json')['source_sha256'] if span!=3 else True
        pair_lookup={(p['left'],p['right']):p for p in inf['comparisons']}
        definitions=inf['family_definition']['comparisons'];coords={row['id']:row for row in inf['coordinates']}
        def get_rows(left,right):
            if (left,right) not in pair_lookup:return None
            pindex=definitions.index([names.index(left),names.index(right)])
            return [coords[f'E:{pindex}:{metric}'] for metric in ['D','C','R','U','V']]+[coords[f'E:{pindex}:H:{s}'] for s in range(201,206)]
        stored={};bridges={}
        G=get_rows(LEFT,SAFE)
        for name in CONTROLS:
            stored[name]=dict(registered=(LEFT,name) in pair_lookup,
                original_labels=pair_lookup.get((LEFT,name)),original_coordinates=get_rows(LEFT,name),
                original_qualification=inf['qualification'][name])
            if name in (SAFE,LEFT):continue
            P=get_rows(name,SAFE)
            if P is None:continue
            gi={row['definition']['metric']:row for row in G if row['definition']['fit'] is None}
            pi={row['definition']['metric']:row for row in P if row['definition']['fit'] is None}
            derived={'D':ratio_contrast_intervals(valid_interval(gi['D']),valid_interval(pi['D']))}
            for metric in ['C','R','U','V']:
                derived[metric]=subtract_intervals(valid_interval(gi[metric]),valid_interval(pi[metric]))
            bridges[name]=dict(bounds=derived,
                construction='Deterministic conservative bridge of already simultaneous frozen intervals through matched SAFE',
                no_new_bootstrap_or_original_label_override=True)
        review[str(span)]=dict(critical_value=inf['critical_value'],n_weather_days=inf['n_days'],
            full_family_size=inf['family_size'],gate_qualification=inf['qualification'][LEFT],comparisons=stored,derived_bridges=bridges)
    save(out/'FROZEN_COMPARISON_REVIEW.json',review)
    save(out/'HISTORY_SELECTION_COPY.json',read(r/'HISTORY_SELECTION.json'))
    save(out/'INPUT_IDENTITIES.json',identities)
    for rel,record in identities.items():
        p=root/rel
        if p.stat().st_size!=record['bytes'] or digest(p)!=record['sha256']:raise ValueError('Read-only input changed')
    save(out/'AUDIT_EXECUTION.json',dict(status='SEALED_EVIDENCE_REVIEW_COMPLETE',new_fits=0,new_policies=0,
        new_measurements=0,new_bootstrap_draws=0,remote_jobs=0,original_results_changed=False,
        thresholds_changed=False,source_sha256=digest(Path(__file__)),input_files=len(identities),
        gate_status_not_upgraded=True,identity_certificate_is_separate_from_original_decision=True))
    print(json.dumps(dict(input_files=len(identities),registered_controls=[k for k,v in review['3']['comparisons'].items() if v['registered']],
        exact_safe_fit_ids=[p['seed'] for p in perfit if p['exact_H_zero_certificate']],new_bootstrap_draws=0)))

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(ROOT,a.output)
if __name__=='__main__':main()
