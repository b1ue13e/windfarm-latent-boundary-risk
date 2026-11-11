"""One bounded Metis campaign: capacity -> historical search -> one frozen replay.

All new outputs live in a fresh directory. Original actions/models are read only.
Evaluation values are not loaded until an immutable final freeze is saved.
"""
from __future__ import annotations
import argparse,csv,json,os,platform,sys,time,traceback,shutil
from dataclasses import asdict
from datetime import datetime,timezone,timedelta
from concurrent.futures import ProcessPoolExecutor
from repo_paths import Path, repository_root
ROOT=Path(repository_root());sys.path.insert(0,str(ROOT))
import numpy as np
from threadpoolctl import threadpool_limits
from windfarm_moe.autonomous_campaign import *
from windfarm_moe.delayed_risk_aggregation import AggregationConfig
from windfarm_moe.delayed_risk_batch import aggregate_batch
from windfarm_moe.delayed_calibration_baselines import DelayedCalibrationConfig,run_delayed_calibration
from windfarm_moe.autonomous_campaign_inference import infer_campaign
from scripts.autonomous_capacity_candidates import prepare_feature_cache,run_capacity_candidate,predict_final
from scripts.run_dynamic_addback import sha,predict


def now():return datetime.now(timezone.utc)
def write(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,allow_nan=False,default=str)+'\n',encoding='utf-8')
def check_deadline(deadline):
    if now()>=datetime.fromisoformat(deadline):raise TimeoutError('Shared campaign work deadline reached')
def metrics(y,r,m,a,span):
    use=(a>=span[0])&(a<span[1]);valid=m[use]
    s=y[use][valid];action=r[use][valid]
    if not len(s):raise ValueError('Undefined scoring population')
    u=np.maximum(s-action,0)/6;reserve=action/6
    return [float(np.mean(reserve+10*u)),float(np.mean(reserve)),float(np.mean(u)),float(np.mean(s>action))]


def capacity_task(args):
    config,cache,out,deadline=args
    try:
        with threadpool_limits(limits=1):value=run_capacity_candidate(config,cache,out,list(SEEDS),deadline)
        return dict(status='COMPLETED',config=config,output=out,summary=value)
    except BaseException as exc:
        return dict(status='FAILED',config=config,output=out,error=repr(exc),traceback=traceback.format_exc())


def check_member(path,record):
    if Path(path).stat().st_size!=record['bytes'] or sha(path)!=record['sha256']:
        raise ValueError('Immutable source mismatch '+str(path))


def verify_expert_cache(cache):
    cache=Path(cache);manifest=json.loads((cache/'manifest.json').read_text())
    for name,record in manifest['files'].items():check_member(cache/name,record)
    return manifest


def assert_coordinates(path,anchors,shortfall,mask,*,prefix=''):
    for key,expected in [('anchors',anchors),('shortfall',shortfall),('mask',mask)]:
        actual=np.load(Path(path)/(prefix+key+'.npy'),mmap_mode='r',allow_pickle=False)
        if actual.shape!=expected.shape or not np.array_equal(actual,expected,equal_nan=True):
            raise ValueError('Frozen coordinate/target bridge failed: '+key)


def prepare_experts(cfg,out,phase,capacity_ids=()):
    """Only the caller's post-freeze path may request phase=evaluate."""
    if phase=='evaluate' and not (Path(out)/'FINAL_FREEZE.json').is_file():raise ValueError('No final freeze; evaluation is locked')
    destination=Path(out)/'expert_cache'/phase;destination.mkdir(parents=True,exist_ok=False)
    phase_key='select' if phase=='select' else 'evaluate'
    coordinate=None;records={};keys=[f'{model}__{cal}' for model in ['BASE','LARGE'] for cal in ['GLOBAL','GROUP','CONDITIONAL']]
    for seed in SEEDS:
        sources=cfg['sources'][str(seed)];fair=Path(sources['fair_directory']);parent=Path(sources['reference_directory'])
        for directory,label in [(fair,'fair'),(parent,'reference')]:
            for name in ['actions.npz','coordinates.npz']:check_member(directory/name,sources[label][name])
        with np.load(fair/'coordinates.npz',allow_pickle=False) as archive:
            anchors=archive[phase_key+'__anchors'];y=archive[phase_key+'__shortfall'];m=archive[phase_key+'__mask']
        expected=range(*( (27648,30233) if phase=='select' else EVALUATE))
        if not np.array_equal(anchors,np.asarray(expected)):raise ValueError('Source anchor mismatch')
        if m.dtype!=bool or y.shape!=m.shape or y.shape!=(len(anchors),134) or not np.isfinite(y[m]).all() or np.any(y[m]<0):raise ValueError('Source population mismatch')
        signature=fingerprint(dict(anchors=sha(fair/'coordinates.npz'),shape=y.shape))
        if coordinate is None:
            coordinate=signature
            for name,array in [('anchors',anchors),('shortfall',y),('mask',m)]:np.save(destination/(name+'.npy'),array,allow_pickle=False)
        elif coordinate!=signature:raise ValueError('Five-fit coordinate byte identity mismatch')
        with np.load(parent/'coordinates.npz',allow_pickle=False) as archive:
            if not np.array_equal(archive[phase_key+'__mask'],m) or not np.array_equal(archive[phase_key+'__shortfall'],y,equal_nan=True):raise ValueError('Reference population mismatch')
        with np.load(parent/'actions.npz',allow_pickle=False) as old:
            reference=old['FULL__BASE__GLOBAL__'+phase_key]
        with np.load(fair/'actions.npz',allow_pickle=False) as archive:
            for arm,representation in [('P','FULL_DYN'),('Z','FULL_DYN_Z')]:
                experts=[reference,*[archive[representation+'__'+key+'__'+phase_key] for key in keys]]
                for capacity in capacity_ids:
                    if phase=='select':array=np.load(Path(out)/'capacity'/f'candidate{capacity:04d}'/f'seed{seed}'/(arm+'_select.npy'),allow_pickle=False)
                    else:
                        folder=Path(out)/'final_capacity'/f'candidate{capacity:04d}'/f'seed{seed}'/arm
                        array=np.load(folder/'actions.npy',allow_pickle=False)
                        assert_coordinates(folder,anchors,y,m)
                    if array.shape!=m.shape:raise ValueError('Capacity action grid differs')
                    experts.append(array)
                values=np.stack(experts,axis=-1)
                if not np.isfinite(values).all() or np.any(values<0):raise ValueError('Invalid current expert actions')
                path=destination/f'{arm}_seed{seed}.npy';np.save(path,values,allow_pickle=False)
                records[path.name]=dict(sha256=sha(path),bytes=path.stat().st_size)
    for name in ['anchors','shortfall','mask']:
        path=destination/(name+'.npy');records[path.name]=dict(sha256=sha(path),bytes=path.stat().st_size)
    write(destination/'manifest.json',dict(status='COMPLETED',phase=phase,files=records,capacity_ids=capacity_ids,
        seeds=SEEDS,coordinate_sha256=coordinate,expert_names=['REF',*keys,*['CAPACITY_'+str(c) for c in capacity_ids]]))
    return destination


def extend_experts(out,oldcache,capacity_ids):
    verify_expert_cache(oldcache)
    aa=np.load(Path(oldcache)/'anchors.npy');yy=np.load(Path(oldcache)/'shortfall.npy');mm=np.load(Path(oldcache)/'mask.npy')
    assert_coordinates(Path(out)/'feature_cache',aa,yy,mm,prefix='select_')
    for cid in capacity_ids:
        record=json.loads((Path(out)/'capacity'/f'candidate{cid:04d}'/'summary.json').read_text())
        if record['cache_manifest_sha256']!=sha(Path(out)/'feature_cache'/'cache_manifest.json'):raise ValueError('Capacity training-cache identity differs')
    destination=Path(out)/'expert_cache'/'historical_extended';destination.mkdir(parents=True,exist_ok=False)
    for name in ['anchors','shortfall','mask']:shutil.copyfile(Path(oldcache)/(name+'.npy'),destination/(name+'.npy'))
    files={}
    for seed in SEEDS:
        for arm in ARMS:
            a=np.load(Path(oldcache)/f'{arm}_seed{seed}.npy',mmap_mode='r')
            additions=[np.load(Path(out)/'capacity'/f'candidate{cid:04d}'/f'seed{seed}'/(arm+'_select.npy'),mmap_mode='r') for cid in capacity_ids]
            if any(x.shape!=mm.shape for x in additions):raise ValueError('New head historical action grid differs')
            parts=[a,*[x[...,None] for x in additions]]
            target=destination/f'{arm}_seed{seed}.npy';np.save(target,np.concatenate(parts,axis=-1),allow_pickle=False)
            files[target.name]=dict(sha256=sha(target),bytes=target.stat().st_size)
    for name in ['anchors','shortfall','mask']:
        path=destination/(name+'.npy');files[path.name]=dict(sha256=sha(path),bytes=path.stat().st_size)
    write(destination/'manifest.json',dict(status='COMPLETED',files=files,capacity_ids=capacity_ids,seeds=SEEDS,
        feature_cache_manifest_sha256=sha(Path(out)/'feature_cache'/'cache_manifest.json')))
    return destination


def batch_task(args):
    recipes,cache,score_span,deadline=args
    start=time.monotonic();count=len(recipes);values=np.full((count,5,2,4),np.nan)
    try:
        check_deadline(deadline);cache=Path(cache)
        a=np.load(cache/'anchors.npy',mmap_mode='r');y=np.load(cache/'shortfall.npy',mmap_mode='r');m=np.load(cache/'mask.npy',mmap_mode='r')
        # Inner search never loads/consumes outer target rows in an action kernel.
        end=int(np.searchsorted(a,score_span[1]));lo=int(np.searchsorted(a,score_span[0]));a=a[:end];y=y[:end];m=m[:end]
        aggregate_ids=[i for i,r in enumerate(recipes) if r['kind']=='aggregation']
        for si,seed in enumerate(SEEDS):
            for ai,arm in enumerate(ARMS):
                check_deadline(deadline);x=np.load(cache/f'{arm}_seed{seed}.npy',mmap_mode='r')[:end]
                with threadpool_limits(limits=1):
                    if aggregate_ids:
                        configs=[AggregationConfig(**recipes[i]['config']) for i in aggregate_ids]
                        priors=np.stack([prior(recipes[i],x.shape[-1]) for i in aggregate_ids])
                        result=aggregate_batch(x,y,m,a,configs,priors,score_slice=(lo,end),return_actions=False)
                        values[aggregate_ids,si,ai]=result.metrics
                    for i,r in enumerate(recipes):
                        if r['kind']=='calibration':
                            action=run_delayed_calibration(x[:,:,r['base_index']],y,m,a,DelayedCalibrationConfig(**r['config']),save_trace=False).actions
                            values[i,si,ai]=metrics(y,action,m,a,score_span)
        if not np.isfinite(values).all():raise ValueError('Incomplete five-fit endpoints')
        return [dict(status='COMPLETED',recipe=r,metrics=values[i].tolist(),batch_seconds=time.monotonic()-start,
                     scored_span=list(score_span),seeds=SEEDS,arms=ARMS) for i,r in enumerate(recipes)]
    except BaseException as exc:
        return [dict(status='FAILED',recipe=r,error=repr(exc),traceback=traceback.format_exc(),
                     batch_seconds=time.monotonic()-start,scored_span=list(score_span)) for r in recipes]


def choose_capacity(results):
    complete=[r for r in results if r['status']=='COMPLETED']
    def cost(r,arm):return np.mean([r['summary']['per_seed'][str(s)]['metrics']['inner'][arm]['C'] for s in SEEDS])
    if not complete:return []
    ranked_p=sorted(complete,key=lambda r:(cost(r,'P'),r['config']['candidate_id']))
    ranked_z=sorted(complete,key=lambda r:(cost(r,'Z'),r['config']['candidate_id']))
    result=[]
    for row in [ranked_p[0],ranked_z[0],*ranked_p]:
        i=row['config']['candidate_id']
        if i not in result:result.append(i)
        if len(result)==2:break
    return result


def final_roles(records,cstar):
    ref=next((r for r in records if r['recipe'].get('prior')=='expert_0' and r['recipe']['family']=='static' and r['status']=='COMPLETED'),None)
    if ref is None:raise ValueError('NO_COMPLETE_REFERENCE: preserve failed/budget rows; no scientific final comparison')
    roles={'REF':dict(row=ref,arm='P')}
    for role,key in [('STATIC','static'),('SIMPLE','simple'),('EW','ew'),('DUAL','dual'),('BEST','best'),('PROTECTED','protected')]:
        for arm_index,arm in enumerate(ARMS):
            if role in ('SIMPLE','EW','DUAL') and arm=='Z':continue
            row=pick_recipes(records,key,arm_index,ref['metrics'],cstar)
            roles[role+'_'+arm]=None if row is None else dict(row=row,arm=arm)
    # Extra measurements may be ignored, selected using outer history only.
    for stem in ['STATIC','BEST','PROTECTED']:
        p,z=roles.get(stem+'_P'),roles.get(stem+'_Z')
        if p is not None and (z is None or mean_metrics(p['row']['metrics'],0)[0]<=mean_metrics(z['row']['metrics'],1)[0]):
            roles[stem+'_Z']=dict(row=p['row'],arm='P',alias=stem+'_P')
    return roles


def final_capacity_task(args):
    model,cfg,out,arm,digest,deadline=args
    check_deadline(deadline)
    with threadpool_limits(limits=1):predict_final(model,cfg,out,arm=arm,expected_model_sha256=digest)
    check_deadline(deadline)
    return out


def score_final(cfg,out,historical_cache,capacity_ids,roles,pool,deadline):
    out=Path(out);freeze=out/'FINAL_FREEZE.json'
    if not freeze.is_file():raise RuntimeError('Evaluation is locked')
    check_deadline(deadline);verify_expert_cache(historical_cache)
    source_versions=json.loads((out/'source_versions.json').read_text())
    if any(sha(ROOT/path)!=digest for path,digest in source_versions.items()):raise ValueError('Source changed since historical search')
    freeze_hash=sha(freeze)
    with (out/'evaluation_open.json').open('x') as stream:json.dump(dict(time_utc=now().isoformat(),freeze_sha256=freeze_hash),stream)
    tasks=[]
    for cid in capacity_ids:
        summary=json.loads((out/'capacity'/f'candidate{cid:04d}'/'summary.json').read_text())
        for seed in SEEDS:
            for arm in ARMS:
                info=summary['per_seed'][str(seed)]['models'][arm]
                target=out/'final_capacity'/f'candidate{cid:04d}'/f'seed{seed}'/arm
                tasks.append((info['model_path'],cfg['prepared'],str(target),arm,info['model_sha256'],deadline))
    list(pool.map(final_capacity_task,tasks))
    final_cache=prepare_experts(cfg,out,'evaluate',capacity_ids)
    hist=Path(historical_cache);a_hist=np.load(hist/'anchors.npy');a_eval=np.load(final_cache/'anchors.npy')
    a=np.r_[a_hist,a_eval];s=np.concatenate([np.load(hist/'shortfall.npy'),np.load(final_cache/'shortfall.npy')]);m=np.concatenate([np.load(hist/'mask.npy'),np.load(final_cache/'mask.npy')])
    final_m=m[len(a_hist):];final_s=s[len(a_hist):];day_ids=np.unique(a_eval//144)
    if len(day_ids)!=35 or int(final_m.sum())!=672939:raise ValueError('Original final population changed')
    counts=np.array([final_m[a_eval//144==d].sum() for d in day_ids],dtype=float)
    names=list(roles);available=[roles[name] is not None for name in names]
    ledger=np.full((5,len(names),35,4),np.nan);means=[];aliases=[]
    actions_out=out/'final_actions';actions_out.mkdir()
    for si,seed in enumerate(SEEDS):
        generated={}
        for pi,name in enumerate(names):
            check_deadline(deadline)
            item=roles[name]
            if item is None:continue
            if item.get('alias'):
                action=generated[item['alias']];aliases.append((name,item['alias']))
            else:
                recipe=item['row']['recipe'];arm=item['arm'];key=(recipe['recipe_sha256'],arm)
                if key in generated:action=generated[key]
                else:
                    x=np.concatenate([np.load(hist/f'{arm}_seed{seed}.npy'),np.load(final_cache/f'{arm}_seed{seed}.npy')])
                    if recipe['kind']=='aggregation':
                        result=aggregate_batch(x,s,m,a,[AggregationConfig(**recipe['config'])],prior(recipe,x.shape[-1])[None,:],score_slice=(len(a_hist),len(a)),return_actions=True)
                        action=result.actions[0,len(a_hist):]
                        write(actions_out/f'{name}_seed{seed}_feedback.json',dict(algorithm=result.metadata,freeze_sha256=freeze_hash))
                    else:
                        result=run_delayed_calibration(x[:,:,recipe['base_index']],s,m,a,DelayedCalibrationConfig(**recipe['config']),save_trace=True)
                        action=result.actions[len(a_hist):]
                        np.savez_compressed(actions_out/f'{name}_seed{seed}_feedback.npz',**dict(result.trace))
                    generated[key]=action
            generated[name]=action
            np.save(actions_out/f'{name}_seed{seed}.npy',action,allow_pickle=False)
            if not np.isfinite(action).all() or np.any(action<0):raise ValueError('Invalid final action')
            for di,day in enumerate(day_ids):
                use=a_eval//144==day;valid=final_m[use];target=final_s[use][valid];r=action[use][valid]
                u=np.maximum(target-r,0)/6;reserve=r/6
                ledger[si,pi,di]=[np.sum(reserve+10*u),np.sum(reserve),np.sum(u),np.sum(target>r)]
            average=ledger[si,pi].sum(axis=0)/counts.sum()
            means.append(dict(policy=name,seed=seed,**dict(zip(METRICS,map(float,average)))))
        del generated
    aliases=list(dict.fromkeys(aliases))
    np.savez_compressed(out/'final_daily_ledger.npz',ledger=ledger,counts=counts,day_ids=day_ids)
    with (out/'final_metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['policy','seed',*METRICS]);w.writeheader();w.writerows(means)
    comparisons=[('STATIC_Z','STATIC_P'),('SIMPLE_P','STATIC_P'),('EW_P','SIMPLE_P'),('DUAL_P','EW_P'),('BEST_P','STATIC_P'),('BEST_P','SIMPLE_P'),('BEST_Z','BEST_P'),('PROTECTED_P','STATIC_P'),('PROTECTED_Z','PROTECTED_P')]
    for span in [3,1,7]:
        check_deadline(deadline)
        result=infer_campaign(ledger,counts,names,comparisons,span=span,n_boot=20000,seed=20261022,cstar=cfg['cstar_reporting_only'],available=available,aliases=aliases)
        write(out/f'final_inference_span{span}.json',result)
    if sha(freeze)!=freeze_hash:raise ValueError('Frozen choice changed during evaluation')
    write(out/'final_programs.json',dict(policy_names=names,available=available,aliases=aliases,comparisons=comparisons,freeze_sha256=freeze_hash))
    return means


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--protocol',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();cfg=json.loads(args.protocol.read_text())
    if not os.environ.get('PBS_JOBID'):raise RuntimeError('Research execution requires a PBS allocation')
    if cfg['max_candidates']!=2000 or cfg['allocated_cpus']!=4 or cfg['cstar_reporting_only']!=42.058880543674675:raise ValueError('Campaign authority differs')
    if cfg['max_job_seconds']*cfg['allocated_cpus']+cfg['preflight_cpu_reserve_seconds']>24*3600:
        raise ValueError('Parallel allocations may not multiply the shared compute budget')
    if tuple(cfg['seeds'])!=SEEDS or cfg['capacity_candidate_limit']+cfg['online_candidate_limit']>2000:
        raise ValueError('Fixed seeds or shared candidate budget changed')
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    start=now();hard=start+timedelta(seconds=cfg['max_job_seconds']);work=hard-timedelta(seconds=cfg['final_reserve_seconds'])
    state=dict(status='PREPARING',started_utc=start.isoformat(),hard_deadline_utc=hard.isoformat(),work_deadline_utc=work.isoformat(),pbs_job_id=os.environ['PBS_JOBID'],protocol_sha256=sha(args.protocol),host=platform.node(),python=sys.version,allocated_cpus=4,attempted=0,completed=0,failed=0,evaluation_opened=False)
    def checkpoint(status):
        state.update(status=status,updated_utc=now().isoformat(),elapsed_seconds=(now()-start).total_seconds(),allocated_cpu_hours=4*(now()-start).total_seconds()/3600)
        write(out/'campaign_state.json',state);print(json.dumps(state),flush=True)
    source_files=[p for folder in ['windfarm_moe','scripts'] for p in (ROOT/folder).glob('*.py')]
    write(out/'source_versions.json',{p.relative_to(ROOT).as_posix():sha(p) for p in source_files})
    shutil.copyfile(args.protocol,out/'protocol.json');checkpoint('PREPARING')
    try:
        oldcache=prepare_experts(cfg,out,'select')
        feature_cache=out/'feature_cache';prepare_feature_cache(cfg['prepared'],feature_cache)
        capacity=[]
        with ProcessPoolExecutor(max_workers=4) as pool:
            checkpoint('CAPACITY_SEARCH')
            cap_grid=capacity_grid(32);write(out/'capacity_candidates.json',cap_grid)
            capacity_deadline=min(work,start+timedelta(seconds=.45*cfg['max_job_seconds']))
            tasks=[(c,str(feature_cache),str(out/'capacity'/f'candidate{c["candidate_id"]:04d}'),capacity_deadline.isoformat()) for c in cap_grid]
            state['attempted']+=len(tasks)
            for value in pool.map(capacity_task,tasks):
                capacity.append(value);write(out/'capacity_receipts'/f'{value["config"]["candidate_id"]:04d}.json',value)
                state['completed' if value['status']=='COMPLETED' else 'failed']+=1;checkpoint('CAPACITY_SEARCH')
            capacity_ids=choose_capacity(capacity);write(out/'capacity_selection.json',dict(ids=capacity_ids,rule='inner-best-P and inner-best-Z shared by both arms; P runner-up fills duplicate'))
            cache=extend_experts(out,oldcache,capacity_ids);k=7+len(capacity_ids)
            recipes=online_grid(k,sha(cache/'manifest.json'),1968);write(out/'online_candidates.json',recipes)
            records=[];best=np.full(4,np.inf);stale=0
            checkpoint('INNER_SEARCH')
            for begin in range(0,len(recipes),256):
                if now()>=work:break
                block=recipes[begin:begin+256];batches=[block[i:i+16] for i in range(0,len(block),16)]
                state['attempted']+=len(block)
                for batch in pool.map(batch_task,[(b,str(cache),INNER,work.isoformat()) for b in batches]):
                    for row in batch:
                        records.append(row);write(out/'inner_results'/f'{row["recipe"]["recipe_id"]:04d}.json',row)
                        state['completed' if row['status']=='COMPLETED' else 'failed']+=1
                complete=[r for r in records if r['status']=='COMPLETED']
                ref=next((r for r in complete if r['recipe'].get('prior')=='expert_0'),None)
                current=[]
                for ai in (0,1):
                    current.append(min((mean_metrics(r['metrics'],ai)[0] for r in complete),default=np.inf))
                for ai in (0,1):
                    guarded=[]
                    if ref is not None:
                        for r in complete:
                            mm=np.asarray(r['metrics'])[:,ai];rr=np.asarray(ref['metrics'])[:,ai]
                            if protected_objective(r['metrics'],ai,ref['metrics']):guarded.append(mean_metrics(r['metrics'],ai)[0])
                    current.append(min(guarded,default=np.inf))
                current=np.asarray(current)
                improvement=np.any(current<best*(1-1e-4));best=np.minimum(best,current)
                stale=0 if improvement else stale+1
                write(out/'inner_incumbent.json',dict(best_cost_unrestricted_and_guarded_PZ=[None if not np.isfinite(x) else float(x) for x in best],recipes_completed=len(complete),stale_blocks=stale,block_end=begin+len(block)))
                checkpoint('INNER_SEARCH')
                families={r['recipe']['family'] for r in complete}
                if len(records)>=768 and stale>=2 and {'static','simple','ew','dual'}<=families:
                    state['early_stop_reason']='Historical-only two-block convergence across unrestricted and guarded P/Z objectives; all families represented';break
            check_deadline(hard.isoformat())
            static=[r for r in records if r.get('status')=='COMPLETED' and r['recipe']['family']=='static']
            chosen=shortlist(records,16);selected={r['recipe']['recipe_id']:r['recipe'] for r in [*static,*chosen]}
            write(out/'HISTORICAL_SHORTLIST_FREEZE.json',dict(time_utc=now().isoformat(),recipe_ids=list(selected),inner_only=True,selection_role='outer is final historical selection, not independent validation'))
            checkpoint('OUTER_SELECTION')
            outer=[];selected=list(selected.values());batches=[selected[i:i+16] for i in range(0,len(selected),16)]
            outer_deadline=hard-timedelta(seconds=cfg['minimum_final_replay_seconds'])
            for batch in pool.map(batch_task,[(b,str(cache),OUTER,outer_deadline.isoformat()) for b in batches]):outer.extend(batch)
            write(out/'outer_results.json',outer)
            roles=final_roles(outer,cfg['cstar_reporting_only'])
            # The legacy full-select normalizer is checked only after all historical
            # labels have matured; it was never an online update/inner-search input.
            aa=np.load(cache/'anchors.npy');yy=np.load(cache/'shortfall.npy');mm=np.load(cache/'mask.npy')
            c0=np.mean([metrics(yy,np.load(cache/f'P_seed{s}.npy')[:,:,0],mm,aa,(27648,30233))[0] for s in SEEDS])
            if not np.isclose(c0,cfg['cstar_reporting_only'],rtol=0,atol=1e-9):raise ValueError('Legacy task/Cstar bridge does not close')
            freeze=dict(time_utc=now().isoformat(),capacity_ids=capacity_ids,roles=roles,protocol_sha256=sha(args.protocol),
                source_versions_sha256=sha(out/'source_versions.json'),selection_scope='Historical only; evaluation is exposed development, not new independent confirmation')
            write(out/'FINAL_FREEZE.json',freeze);state['evaluation_opened']=True;checkpoint('FROZEN_FINAL_REPLAY')
            score_final(cfg,out,cache,capacity_ids,roles,pool,hard.isoformat())
            checkpoint('COMPLETED_DEVELOPMENT_NOT_TOP_JOURNAL_CERTIFICATION')
    except BaseException as exc:
        state['error']=repr(exc);write(out/'failure.json',dict(error=repr(exc),traceback=traceback.format_exc()))
        checkpoint('STOPPED_BUDGET' if isinstance(exc,TimeoutError) else 'FAILED_PRESERVED')
        raise


if __name__=='__main__':main()
