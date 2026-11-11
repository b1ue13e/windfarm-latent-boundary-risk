"""Read-only audit of P25 fairness, frozen branch removal and retention ratios.

Inspects existing parameters and ledgers only. No inference draws, predictions,
model fitting, action generation or remote access are performed.
"""
from repo_paths import Path, repository_root
import sys,json,hashlib,zipfile,warnings
import numpy as np
import joblib
ROOT=Path(repository_root());sys.path.insert(0,str(ROOT))

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def retention(nv_cost,gate_cost,reference_cost):
    denom=float(reference_cost-gate_cost)
    return None if denom==0 else float((reference_cost-nv_cost)/denom)

def run(out):
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    h=ROOT/'experiments/em1_minimal_followup_20261025';p=ROOT/'experiments/endpoint_match_20261025'
    r=p/'recovered/results/campaign';q=h/'recovered/results/campaign'
    cfg=read(h/'protocol.json');frozen=read(r/'FINAL_FREEZE.json');identities={}
    def bind(path):identities[str(path.relative_to(ROOT))]=dict(sha256=sha(path),bytes=path.stat().st_size)
    for path in [h/'source_payload.zip',h/'protocol.json',r/'FINAL_FREEZE.json',r/'HISTORY_SELECTION.json',
                 q/'step1/all_daily_ledger.npz',q/'step2/all_daily_ledger.npz',q/'step1/all_policy_names.json',q/'step2/all_policy_names.json',
                 h/'KEY_RESULTS_ALL_SPANS.json',h/'REPLAY_AUDIT_SUMMARY.json']:
        bind(path)
    with zipfile.ZipFile(h/'source_payload.zip') as z:
        for rel,digest in cfg['source_hashes'].items():
            assert hashlib.sha256(z.read(rel)).hexdigest()==digest
            assert sha(ROOT/rel)==digest
    info1=read(q/'step1/all_policy_names.json');info2=read(q/'step2/all_policy_names.json')
    assert (len(info1['names']),len(info1['comparisons']),len(info1['aliases']))==(1400,7259,152)
    assert (len(info2['names']),len(info2['comparisons']),len(info2['aliases']))==(1401,7260,152)
    assert info1['names']==info2['names'][:-1] and info1['comparisons']==info2['comparisons'][:-1]
    parent_info=read(r/'all_policy_names.json')
    assert info1['names']==parent_info['names'] and info1['comparisons'][:7257]==parent_info['comparisons']
    assert info1['comparisons'][-2:]==[['EM1_008_Z','EM1_003_P'],['EM1_008_Z','EM1_004_P']]
    with np.load(q/'step1/all_daily_ledger.npz') as z:a=z['ledger'].copy();counts=z['counts'].copy();days=z['day_ids'].copy()
    with np.load(q/'step2/all_daily_ledger.npz') as z:b=z['ledger'].copy();assert np.array_equal(counts,z['counts']) and np.array_equal(days,z['day_ids'])
    assert np.array_equal(a,b[:,:1400],equal_nan=True)
    records=[];loader_warnings=[];fairness=[]
    for seed in range(201,206):
        shard=(seed-201)*3+2;models=frozen['histories'][shard]['versions']['outer']['models']
        replay=read(q/'replay'/f'seed{seed}/receipt.json');bind(q/'replay'/f'seed{seed}/receipt.json')
        assert replay['independent_action_bytes_exact'] and replay['new_fits']==0
        for snap,(cut,start) in {'C':(29376,29384),'E':(29808,29816),'D':(30233,30240)}.items():
            row=next(m for m in models if m['snapshot']==snap and m['recipe_id']==8)
            mp=p/'frozen_weights/results/campaign'/row['path'];rp=r/row['receipt_path'];bind(mp);bind(rp)
            assert sha(mp)==row['sha256'] and sha(rp)==row['receipt_sha256']
            receipt=read(rp)
            with warnings.catch_warnings(record=True) as ws:
                warnings.simplefilter('always');model=joblib.load(mp)
            loader_warnings.extend(str(w.message) for w in ws)
            assert model['cut_anchor']==cut and model['episode_start']==model['enabled_anchor']==start
            assert (cut-1)+7<start
            tree=model['tree'].tree_
            assert tree.node_count==3 and int(tree.feature[0])==3
            assert model['feature_names'][3]=='cost_minus_safe' and tree.threshold[0]>0
            left,right=int(tree.children_left[0]),int(tree.children_right[0]);assert left==1 and right==2
            assert tree.children_left[left]==tree.children_left[right]==-1
            support={int(k):int(v['n_cells']) for k,v in model['leaf_stats'].items()}
            alphas={int(k):float(v) for k,v in model['leaf_alphas'].items()}
            major=min(support,key=lambda k:(-support[k],k))
            selected=replay['kernel']['snapshots'][snap]
            assert major==left and alphas[right]==0 and selected['leaf_id']==major
            assert selected['alpha']==alphas[major] and selected['historical_cells']==support[major]
            assert {str(k):v for k,v in alphas.items()}==receipt['leaf_alphas']
            records.append(dict(seed=seed,snapshot=snap,cut=cut,enabled=start,major_leaf=major,
                major_alpha=alphas[major],other_leaf_alpha=alphas[right],threshold=float(tree.threshold[0]),
                split_feature='cost_minus_safe',historical_major_support=support[major],
                major_leaf_was_derived_from_conditional_training=True,
                old_model_and_selected_alpha_identical=True,inference_branch_only_changed=True,
                monotone_action_relation='No-veto>=Gate; positive-cost-minus-safe veto region'))
        for phase in ['outer','evaluate']:
            gr=r/'outer/instances'/phase/f'Z_seed{seed}/receipt.json'
            pr=r/'outer/instances'/phase/f'P_seed{seed}/receipt.json';bind(gr);bind(pr)
            gate,control=read(gr),read(pr)
            assert gate['target_sha256']==control['target_sha256'] and gate['mask_sha256']==control['mask_sha256']
            old=gate['policies']['8'];new=replay['phases'][phase]
            assert new['gate_action_sha256']==old['action_sha256'] and new['grid_no_veto_ge_gate']
            assert new['scored_no_veto_ge_gate'] and new['scored_cells']>0
            fairness.append(dict(seed=seed,phase=phase,target_sha256=gate['target_sha256'],mask_sha256=gate['mask_sha256'],
                grid_action_monotonic=True,gate_original_action_sha256=old['action_sha256'],
                no_veto_independent_loss_tolerance=replay['independent_daily_tolerance']))
    names=info2['names'];N,G,S,P25,P50=[names.index(k) for k in ['NV_MAJOR_Z','EM1_008_Z','EM1_000_P','EM1_003_P','EM1_004_P']]
    pt=b.sum(2)/counts.sum();mean=pt.mean(0)
    ratios=[]
    for fit in range(5):ratios.append(dict(seed=201+fit,gate_cost_gain=float(pt[fit,S,0]-pt[fit,G,0]),
        no_veto_cost_gain=float(pt[fit,S,0]-pt[fit,N,0]),retention=retention(pt[fit,N,0],pt[fit,G,0],pt[fit,S,0])))
    c=retention(mean[N,0],mean[G,0],mean[S,0])
    assert abs(c-.8694138957567981)<1e-10
    alternative=retention(mean[N,0],mean[G,0],mean[names.index('BR009_P'),0])
    parent_evidence=read(p/'SELECTED_EVIDENCE.json')['coordinates']
    bound=next(x for x in parent_evidence if x['left_name']=='EM1_008_Z' and x['right_name']=='EM1_000_P' and x['definition']['metric']=='D')
    assert bound['lower']<0<bound['upper']
    ratio_info=dict(formula='(C_SAFE-C_NV)/(C_SAFE-C_G)',reference='EM1_000_P',
        aggregate_cost_retention=c,alternative_BR009P_retention=alternative,per_fit=ratios,
        aggregate_ratio_is_not_mean_of_fit_ratios=True,
        denominator_difference_to_SAFE_interval_crosses_zero=True,ratio_interval_not_estimated=True,
        U_improvement_retention=float((mean[S,2]-mean[N,2])/(mean[S,2]-mean[G,2])),
        V_improvement_retention=float((mean[S,3]-mean[N,3])/(mean[S,3]-mean[G,3])),
        no_unconditional_training_mechanism_identified=True,no_causal_fraction_identified=True)
    points={name:dict(zip(['C','R','U','V'],mean[names.index(name)].tolist())) for name in
            ['EM1_008_Z','EM1_000_P','EM1_003_P','EM1_004_P','NV_MAJOR_Z']}
    selected=read(h/'KEY_RESULTS_ALL_SPANS.json');stat=[]
    for stage,v in selected.items():
        for span,r0 in v['spans'].items():
            for pair in r0['comparisons']:
                columns=[]
                for row in pair['coordinates']:
                    d=row['definition'];metric=d['metric'];fit=d['fit'];j=0 if metric=='D' else 2 if metric=='H' else ['C','R','U','V'].index(metric)
                    ii,kk=[names.index(pair[k]) for k in ['left','right']]
                    val=(b[:,ii,:,j]-b[:,kk,:,j]).mean(0).sum()/counts.sum() if fit is None else (b[fit,ii,:,j]-b[fit,kk,:,j]).sum()/counts.sum()
                    if metric=='D':val*=counts.sum()/b[:,kk,:,0].sum(1).mean()
                    if metric=='H':val*=10/42.058880543674675
                    assert abs(val-row['point'])<1e-12
                    columns.append(dict(metric=metric,fit=fit,status=row['status'],point=row['point'],lower=row['lower'],upper=row['upper']))
                stat.append(dict(stage=stage,span=span,left=pair['left'],right=pair['right'],labels=pair['labels'],coordinates=columns))
    save(out/'MODELS_AND_BRANCHES.json',records);save(out/'POPULATION_AND_REPLAY_BINDINGS.json',fairness)
    save(out/'RETENTION_RATIO_REVIEW.json',ratio_info);save(out/'POINTS.json',points);save(out/'FROZEN_STATISTICS.json',stat)
    save(out/'PARAMETER_LOAD_NOTES.json',dict(predictions_executed=False,model_parameter_inspection_only=True,warnings=sorted(set(loader_warnings))))
    save(out/'INPUT_IDENTITIES.json',identities)
    for rel,value in identities.items():assert sha(ROOT/rel)==value['sha256']
    save(out/'EXECUTION.json',dict(status='FROZEN_DIAGNOSTICS_REVIEW_COMPLETE',new_model_fits=0,new_predictions=0,
        new_actions=0,new_resampling=0,remote_access=False,source_sha256=sha(Path(__file__)),input_files=len(identities),
        original_results_thresholds_and_paper_changed=False,matched_branch_ablation_is_valid=True,
        unconditional_mixture_learning_attribution_is_identified=False))
    print(json.dumps(dict(models_verified=len(records),retention=c,alternative_reference=alternative,
        fifth_fit_ratio=ratios[-1]['retention'],new_experiments=0,input_files=len(identities))))
def main():
    p=__import__('argparse').ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.output)
if __name__=='__main__':main()
