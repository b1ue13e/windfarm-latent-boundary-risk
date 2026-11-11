"""Fixed-vintage endpoint and release-rule development campaign."""
from repo_paths import Path, repository_root
import sys,os,json,time,hashlib,argparse,traceback,platform
ROOT=Path(repository_root());sys.path.insert(0,str(ROOT))
import numpy as np
import sklearn,scipy,joblib
from threadpoolctl import threadpool_limits
from scripts.run_mixture_closed_loop import save,sha,score_actions,PHASES,SEEDS,deadline_check
from scripts.run_residual_meta import shard_assignment
from scripts.run_prospective_release import _save_protocol_copies,_window_cell_metrics,verify_prefix
from windfarm_moe.matched_endpoint_bank import build_matched_bank,VINTAGES
from windfarm_moe.release_bank import save_release_bank,load_release_bank,verify_parent_campaign_freeze
from windfarm_moe.release_gate import save_release_gate_model,load_release_gate_model,build_recipes
from windfarm_moe.matched_release_design import (
    SNAPSHOTS,VALIDATION_WINDOWS,fit_snapshot_models,scheduled_actions,policy_name,build_family)
from windfarm_moe.stable_contrast_inference import infer_stable_campaign

def env():
    return dict(host=platform.node(),python=sys.version,numpy=np.__version__,scipy=scipy.__version__,
        sklearn=sklearn.__version__,joblib=joblib.__version__,job_id=os.environ.get('PBS_JOBID'),release=os.environ.get('CAMPAIGN_RELEASE'))
def sources(cfg):
    for rel,digest in cfg['source_hashes'].items():
        if sha(ROOT/rel)!=digest:raise ValueError('Release source mismatch: '+rel)
def config_check(cfg):
    assert cfg['recipes']==build_recipes() and cfg['max_candidates']==48 and cfg['max_cpu_seconds']==7200
    assert cfg['snapshots']=={v:{k:list(x) for k,x in ss.items()} for v,ss in SNAPSHOTS.items()}
    assert cfg['stage_limits']==dict(s0=120,history=240,evaluate=120,freeze=60,aggregate=600,audit=300,reserve=480)
    assert 3*120+15*240+15*120+60+600+300+480==7200
    assert cfg['thresholds']==dict(important_cost_gain=.01,cost_noninferiority=.01,signed_H=.001,absolute_risk=.10,alpha=.05)
def history_path(out,shard):return out/'shards/history'/f'{shard:02d}.json'
def bankpath(out,v,arm,seed):return out/'banks/history'/v/f'{arm}_seed{seed}'/'release_bank.npz'
def phase_path(out,v,phase,arm,seed):return out/v/'instances'/phase/f'{arm}_seed{seed}'
def modelpath(out,v,key,arm,seed,rid):return out/'models'/v/key/f'{arm}_seed{seed}'/f'EM{rid:03d}.joblib'
def model_receipt_path(p):return p.with_name(p.stem+'_receipt.json')
def _assert_new(path):
    if path.exists():raise FileExistsError('Refusing to replace existing result: '+str(path))
def _saved_bank_manifest(path):
    meta=path.with_name('release_bank_metadata.json')
    return dict(npz_sha256=sha(path),metadata_sha256=sha(meta))
def _read_bank(path,manifest=None):
    return load_release_bank(path,**({} if manifest is None else dict(expected_sha256=manifest['npz_sha256'],expected_metadata_sha256=manifest['metadata_sha256'])))
def score_phase(cfg,out,v,phase,seed,arm,bank,models,deadline):
    folder=phase_path(out,v,phase,arm,seed);_assert_new(folder)
    lo,hi,_=PHASES[phase];sel=(bank['anchors']>=lo)&(bank['anchors']<hi)
    y,m,a=bank['shortfall'][sel],bank['mask'][sel],bank['anchors'][sel]
    if not len(a):raise ValueError('Empty phase')
    rows=[];records={}
    for rid in range(24):
        deadline_check(deadline)
        actions,diag=scheduled_actions(bank,models,v,rid)
        daily,counts,days=score_actions(actions[sel],y,m,a);rows.append(daily)
        windows={}
        for win,(begin,end) in VALIDATION_WINDOWS[v].items():
            use=(bank['anchors']>=begin)&(bank['anchors']<end)&sel
            if use.any():windows[win]=_window_cell_metrics(actions[use],bank['shortfall'][use],bank['mask'][use])
        records[str(rid)]=dict(status='COMPLETED',action_sha256=hashlib.sha256(np.ascontiguousarray(actions[sel],dtype='<f8').tobytes()).hexdigest(),
            metrics=(daily.sum(0)/counts.sum()).tolist(),diagnostics=diag,validation_windows=windows)
    ref,refn,refdays=score_actions(bank['reference'][sel],y,m,a)
    assert np.array_equal(refn,counts) and np.array_equal(refdays,days)
    folder.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(folder/'daily.npz',ledger=np.stack(rows),reference=ref,counts=counts,days=days)
    rec=dict(vintage=v,phase=phase,seed=seed,arm=arm,policies=records,daily_sha256=sha(folder/'daily.npz'),
        target_sha256=hashlib.sha256(np.ascontiguousarray(y,dtype='<f8').tobytes()).hexdigest(),mask_sha256=hashlib.sha256(m.tobytes()).hexdigest())
    save(folder/'receipt.json',rec)
    return dict(path=str((folder/'receipt.json').relative_to(out)),sha256=sha(folder/'receipt.json'),daily_sha256=rec['daily_sha256'])
def read_phase(out,v,phase,seed,arm,binding=None):
    folder=phase_path(out,v,phase,arm,seed)
    if binding and sha(folder/'receipt.json')!=binding['sha256']:raise ValueError('Phase binding changed')
    rec=json.loads((folder/'receipt.json').read_text())
    if (rec['vintage'],rec['phase'],rec['seed'],rec['arm'])!=(v,phase,seed,arm) or len(rec['policies'])!=24:
        raise ValueError('Phase identity/family differs')
    if sha(folder/'daily.npz')!=rec['daily_sha256']:raise ValueError('Daily ledger changed')
    with np.load(folder/'daily.npz') as z:arr={k:z[k].copy() for k in z.files}
    return rec,arr
def check_bank(bank,v,evaluate=False):
    expected=(2139 if v=='inner' else 1289)+(5033 if evaluate else 0)
    assert len(bank['anchors'])==expected
    assert bank['metadata']['phase_restarts']==0 and bank['metadata']['vintage']==v
    assert bank['metadata']['include_evaluation']==evaluate
    if evaluate:
        select=bank['anchors']>=30240;assert int(bank['mask'][select].sum())==672939
    trace=np.asarray(bank['metadata']['feedback_release_trace'])
    assert np.all(trace<bank['anchors'])

def s0(cfg,out,shard,deadline):
    seed,arm=201,('C','P','Z')[shard]
    dst=out/'s0'/f'{arm}.json';_assert_new(dst);records={}
    for v in VINTAGES:
        deadline_check(deadline);bank=build_matched_bank(cfg,seed,arm,v,False,root=ROOT);check_bank(bank,v)
        path=bankpath(out,v,arm,seed);manifest=save_release_bank(path,bank)
        records[v]=dict(manifest=manifest,first_phase_safe_sha256=bank['metadata']['first_phase_safe_sha256'],
            first_phase_cost_sha256=bank['metadata']['first_phase_cost_sha256'],frozen_models=bank['metadata']['frozen_meta_models'])
    save(dst,dict(status='COMPLETED',seed=seed,arm=arm,records=records,environment=env(),protocol_sha256=sha(out/'protocol_original.json')))

def history(cfg,out,shard,deadline):
    seed,arm=shard_assignment(shard);dst=history_path(out,shard);_assert_new(dst)
    for aa in ('C','P','Z'):
        r=json.loads((out/'s0'/f'{aa}.json').read_text())
        if r['status']!='COMPLETED' or r['protocol_sha256']!=sha(out/'protocol_original.json'):raise ValueError('S0 barrier absent')
    versions={}
    for v in VINTAGES:
        deadline_check(deadline);p=bankpath(out,v,arm,seed)
        if p.exists():bank=_read_bank(p);manifest=_saved_bank_manifest(p)
        else:
            bank=build_matched_bank(cfg,seed,arm,v,False,root=ROOT);manifest=save_release_bank(p,bank)
        check_bank(bank,v)
        models,receipts=fit_snapshot_models(bank,v,seed)
        expected=24*len(SNAPSHOTS[v])
        if len(models)!=expected or len(receipts)!=expected:raise ValueError('Incomplete fitted model family')
        records=[]
        for (key,rid),model in models.items():
            deadline_check(deadline);p=modelpath(out,v,key,arm,seed,rid);rp=model_receipt_path(p);_assert_new(p);_assert_new(rp)
            save_release_gate_model(p,model);save(rp,receipts[key,rid])
            records.append(dict(snapshot=key,recipe_id=rid,path=str(p.relative_to(out)),sha256=sha(p),
                receipt_path=str(rp.relative_to(out)),receipt_sha256=sha(rp),status=model['status'],
                tree_fit=model.get('tree') is not None,global_fit=model['kind']=='GLOBAL_FIT' and model['status']=='FITTED_OK'))
        phases={ph:score_phase(cfg,out,v,ph,seed,arm,bank,models,deadline) for ph in (('inner','outer') if v=='inner' else ('outer',))}
        versions[v]=dict(bank_manifest=manifest,models=records,phases=phases)
    save(dst,dict(status='COMPLETED',shard=shard,seed=seed,arm=arm,versions=versions,
        evaluation_touched=False,environment=env(),protocol_sha256=sha(out/'protocol_original.json')))

def _load_models(out,records,v):
    ans={}
    for r in records:
        if sha(out/r['path'])!=r['sha256'] or sha(out/r['receipt_path'])!=r['receipt_sha256']:raise ValueError('Model identity changed')
        ans[r['snapshot'],r['recipe_id']]=load_release_gate_model(out/r['path'])
    if set(ans)!={(key,j) for key in SNAPSHOTS[v] for j in range(24)}:raise ValueError('Incomplete model keys')
    return ans
def freeze(cfg,out,deadline):
    dst=out/'FINAL_FREEZE.json';_assert_new(dst);_assert_new(out/'EVALUATION_OPEN.json')
    records=[];selections={};treefits=globalfits=0
    for shard in range(15):
        deadline_check(deadline);p=history_path(out,shard);h=json.loads(p.read_text());seed,arm=shard_assignment(shard)
        if h['status']!='COMPLETED' or (h['seed'],h['arm'])!=(seed,arm) or h['evaluation_touched'] or h['protocol_sha256']!=sha(out/'protocol_original.json'):
            raise ValueError('Historical shard incomplete/changed')
        for v,record in h['versions'].items():
            bp=bankpath(out,v,arm,seed);manifest=record['bank_manifest']
            if sha(bp)!=manifest['npz_sha256'] or sha(bp.with_name('release_bank_metadata.json'))!=manifest['metadata_sha256']:raise ValueError('Historical bank changed')
            if len(record['models'])!=24*len(SNAPSHOTS[v]):raise ValueError('Incomplete model records')
            for item in record['models']:
                if sha(out/item['path'])!=item['sha256'] or sha(out/item['receipt_path'])!=item['receipt_sha256']:raise ValueError('Model changed before freeze')
                treefits+=int(item['tree_fit']);globalfits+=int(item['global_fit'])
            for ph,binding in record['phases'].items():read_phase(out,v,ph,seed,arm,binding)
        records.append(dict(path=str(p.relative_to(out)),sha256=sha(p),versions=h['versions']))
    for v in VINTAGES:
        selections[v]={}
        for arm in ('C','P','Z'):
            point=np.asarray([[read_phase(out,v,'outer',seed,arm)[0]['policies'][str(j)]['metrics'] for j in range(24)] for seed in SEEDS])
            selections[v][arm]=dict(minimum_C_id=int(np.argmin(point.mean(0)[:,0])),minimum_maxV_id=int(np.argmin(point[:,:,3].max(0))),
                outer_mean_points=point.mean(0).tolist(),selection_filters_evaluation=False)
    save(out/'HISTORY_SELECTION.json',selections)
    if (treefits,globalfits)!=(1680,105):raise ValueError('Actual fit count differs')
    r=dict(status='FROZEN',histories=records,source_hashes=cfg['source_hashes'],protocol_sha256=sha(out/'protocol_original.json'),
        selection_sha256=sha(out/'HISTORY_SELECTION.json'),model_records=2520,actual_tree_fits=treefits,actual_global_fits=globalfits,
        evaluation_touched=False,independent_confirmation=False,environment=env())
    with dst.open('x') as f:json.dump(r,f,indent=2)
    save(out/'EVALUATION_OPEN.json',dict(freeze_sha256=sha(dst),protocol_sha256=r['protocol_sha256']))
def verified_freeze(cfg,out):
    opened=json.loads((out/'EVALUATION_OPEN.json').read_text());f=json.loads((out/'FINAL_FREEZE.json').read_text())
    if sha(out/'FINAL_FREEZE.json')!=opened['freeze_sha256'] or f['protocol_sha256']!=sha(out/'protocol_original.json') or f['source_hashes']!=cfg['source_hashes']:
        raise ValueError('Freeze barrier changed')
    if sha(out/'HISTORY_SELECTION.json')!=f['selection_sha256']:raise ValueError('Historical roles changed')
    return f,opened['freeze_sha256']
def evaluate(cfg,out,shard,deadline):
    seed,arm=shard_assignment(shard);dst=out/'shards/evaluate'/f'{shard:02d}.json';_assert_new(dst)
    f,fsha=verified_freeze(cfg,out);h=f['histories'][shard]
    if sha(out/h['path'])!=h['sha256']:raise ValueError('History receipt changed after freeze')
    records={}
    for v,record in h['versions'].items():
        deadline_check(deadline)
        hist=_read_bank(bankpath(out,v,arm,seed),record['bank_manifest'])
        models=_load_models(out,record['models'],v)
        full=build_matched_bank(cfg,seed,arm,v,True,root=ROOT);check_bank(full,v,True);verify_prefix(hist,full)
        meta=out/'full_bank_metadata'/v/f'{arm}_seed{seed}.json';save(meta,full['metadata'])
        binding=score_phase(cfg,out,v,'evaluate',seed,arm,full,models,deadline)
        records[v]=dict(phase=binding,metadata_path=str(meta.relative_to(out)),metadata_sha256=sha(meta))
    save(dst,dict(status='COMPLETED',shard=shard,seed=seed,arm=arm,versions=records,freeze_sha256=fsha,
        evaluated_all_24_per_vintage=True,qualification_filter=False,environment=env()))
def aggregate(cfg,out,deadline):
    _assert_new(out/'completion.json');f,fsha=verified_freeze(cfg,out)
    parent=Path(cfg['parent_results'])
    verify_parent_campaign_freeze(parent,cfg['parent_freeze_sha256'],label='GR parent')
    if sha(parent/'all_daily_ledger.npz')!=cfg['parent_ledger_sha256'] or sha(parent/'inference_span3.json')!=cfg['parent_span3_sha256']:
        raise ValueError('Immutable parent ledger differs')
    parent_inf=json.loads((parent/'inference_span3.json').read_text());names,available,pairs,aliases=build_family(parent_inf)
    with np.load(parent/'all_daily_ledger.npz') as z:old=z['ledger'].copy();counts=z['counts'].copy();days=z['day_ids'].copy()
    if old.shape!=(5,1256,35,4):raise ValueError('Parent dimensions differ')
    data=np.empty((5,len(names),35,4));data[:,:1256]=old
    evalbindings=[]
    for shard in range(15):
        deadline_check(deadline);seed,arm=shard_assignment(shard)
        p=out/'shards/evaluate'/f'{shard:02d}.json';r=json.loads(p.read_text())
        if r['status']!='COMPLETED' or r['freeze_sha256']!=fsha or r['qualification_filter'] or not r['evaluated_all_24_per_vintage']:
            raise ValueError('Mandatory evaluation incomplete')
        for v in VINTAGES:
            binding=r['versions'][v]
            if sha(out/binding['metadata_path'])!=binding['metadata_sha256']:raise ValueError('Full bank metadata changed')
            rec,z=read_phase(out,v,'evaluate',seed,arm,binding['phase'])
            si=seed-201
            if not np.array_equal(z['counts'],counts) or not np.array_equal(z['days'],days) or not np.allclose(z['reference'],old[si,0],rtol=0,atol=1e-8):
                raise ValueError('Reference or population bridge changed')
            if z['ledger'].shape!=(24,35,4) or not np.isfinite(z['ledger']).all():raise ValueError('Unscored candidate')
            for rid in range(24):data[si,names.index(policy_name(v,rid,arm))]=z['ledger'][rid]
        evalbindings.append(dict(path=str(p.relative_to(out)),sha256=sha(p)))
    # Design returns all policies' availability, including new complete policies.
    if len(available)==1256:available=available+[True]*144
    if len(names)!=1400 or len(pairs)!=7257 or len(aliases)!=152 or len(available)!=1400:raise ValueError('Expanded family differs')
    for left,right in aliases:
        if not np.array_equal(data[:,names.index(left)],data[:,names.index(right)],equal_nan=True):raise ValueError('Explicit alias ledger differs')
    if not np.array_equal(data[:,:1256],old,equal_nan=True):raise ValueError('Parent ledger prefix changed')
    np.savez_compressed(out/'all_daily_ledger.npz',ledger=data,counts=counts,day_ids=days)
    save(out/'all_policy_names.json',dict(names=names,available=available,comparisons=pairs,aliases=aliases,nominal_family_size=87970))
    for span in (1,3,7):
        deadline_check(deadline)
        inf=infer_stable_campaign(data,counts,names,pairs,span=span,n_boot=20000,seed=20261022,available=available,aliases=aliases)
        save(out/f'inference_span{span}.json',inf)
    save(out/'completion.json',dict(status='COMPLETED',source_hashes=cfg['source_hashes'],freeze_sha256=fsha,environment=env(),
        model_records=2520,actual_tree_fits=1680,actual_global_alpha_fits=105,new_upstream_fits=0,
        scored_instances=1800,evaluated_all=True,qualification_used_to_filter=False,independent_confirmation=False,
        parent_prefix_exact=True,ledger_sha256=sha(out/'all_daily_ledger.npz'),evaluation_bindings=evalbindings))

def main():
    p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--stage',choices=('s0','history','freeze','evaluate','aggregate'),required=True);p.add_argument('--shard',type=int,default=0)
    a=p.parse_args()
    if not os.environ.get('PBS_JOBID') or not os.environ.get('CAMPAIGN_RELEASE'):raise ValueError('Bounded PBS allocation and source identity required')
    cfg=json.loads(a.protocol.read_text());out=a.output;out.mkdir(parents=True,exist_ok=True)
    config_check(cfg);sources(cfg);_save_protocol_copies(cfg,out,a.protocol)
    deadline=time.time()+cfg['stage_limits'][a.stage]
    try:
        with threadpool_limits(limits=1):
            args=[cfg,out]+([a.shard] if a.stage in ('s0','history','evaluate') else [])+[deadline]
            globals()[a.stage](*args)
    except BaseException as exc:
        save(out/'failures'/f'{a.stage}_{a.shard}.json',dict(error=repr(exc),traceback=traceback.format_exc(),environment=env()))
        raise
if __name__=='__main__':main()
