"""Bounded matched-initialization and actual-mixture development campaign."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib,json,os,platform,sys,time,traceback
from repo_paths import Path, repository_root
ROOT=Path(repository_root());sys.path.insert(0,str(ROOT))
import numpy as np
import scipy
from threadpoolctl import threadpool_limits
from windfarm_moe.actual_mixture_update import MixtureConfig,run_mixture,run_matched_ew
from windfarm_moe.static_convex_bundle import fit_bundle
from windfarm_moe.delayed_risk_aggregation import AggregationConfig,_initial_weights
from windfarm_moe.delayed_risk_batch import aggregate_batch
from windfarm_moe.delayed_calibration_baselines import DelayedCalibrationConfig,run_delayed_calibration
from windfarm_moe.autonomous_campaign_inference import infer_campaign

SEEDS=tuple(range(201,206));ARMS=('P','Z')
PHASES={'inner':(28087,28937,28080),'outer':(28944,30233,28937),'evaluate':(30240,35273,30233)}


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()


def save(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,allow_nan=False,
        default=lambda x:x.tolist() if isinstance(x,np.ndarray) else str(x))+'\n')


def deadline_check(deadline):
    if time.time()>=deadline:raise TimeoutError('This stage must remain within its fixed allocation')


def verify_cache(cache,expected):
    cache=Path(cache)
    if sha(cache/'manifest.json')!=expected:raise ValueError('Frozen expert manifest differs')
    d=json.loads((cache/'manifest.json').read_text())
    for name,item in d['files'].items():
        p=cache/name
        if p.stat().st_size!=item['bytes'] or sha(p)!=item['sha256']:
            raise ValueError('Source identity differs: '+str(p))
    return d


def score_actions(actions,y,mask,anchors):
    """Single-policy daily C/R/U/V sums, with the original strict endpoint."""
    if actions.shape!=y.shape or not np.isfinite(actions).all() or np.any(actions<0):
        raise ValueError('Invalid complete-grid actions')
    result=[];counts=[];days=np.unique(anchors//144)
    for day in days:
        use=anchors//144==day;valid=mask[use];r=actions[use][valid];s=y[use][valid]
        if not np.isfinite(s).all() or np.any(s<0):raise ValueError('Invalid scored target')
        u=np.maximum(s-r,0)/6
        result.append([np.sum(r/6+10*u),np.sum(r/6),np.sum(u),np.sum(s>r)])
        counts.append(int(valid.sum()))
    return np.asarray(result),np.asarray(counts),days


def control_initial(weight):
    """Canonicalize once for old EW; fixed and gradient controls reuse it."""
    raw=.99*np.asarray(weight)+.01/len(weight)
    return raw,_initial_weights(len(weight),raw,'exponential')


def fit_task(task):
    cfg,out,phase,seed,arm,deadline=task;out=Path(out);start=time.monotonic()
    deadline_check(deadline)
    cache=Path(cfg['historical_cache']);a=np.load(cache/'anchors.npy');y=np.load(cache/'shortfall.npy');m=np.load(cache/'mask.npy')
    begin,end,cut=PHASES[phase];use=(a>=27648)&(a<cut)
    if len(a[use])!=cut-27648 or int(a[use].max())+7>=begin:
        raise ValueError('Warm-start labels are not strictly mature')
    x=np.load(cache/f'{arm}_seed{seed}.npy',mmap_mode='r')[use][m[use]];target=y[use][m[use]]
    cap=float(np.maximum(target-x[:,0],0).mean());records={}
    for goal,limit in [('COST',None),('CAP',cap)]:
        deadline_check(deadline)
        try:
            with threadpool_limits(limits=1):result=fit_bundle(x,target,uncovered_cap=limit,time_limit=15.,max_iter=1200)
            record=asdict(result)
        except Exception as exc:
            w=np.zeros(x.shape[1]);w[0]=1
            r=x[:,0];u=np.maximum(target-r,0)
            record=dict(weights=w,status='INITIALIZER_ERROR_DECLARED_REF_FALLBACK',optimal=False,
                objective=float(np.mean(r+10*u)/6),error=repr(exc),traceback=traceback.format_exc())
        w=np.asarray(record['weights']);raw,canonical=control_initial(w)
        record.update(phase=phase,seed=seed,arm=arm,goal=goal,
            fit_window=[27648,cut],episode_start=begin,last_label_release=int(a[use].max())+7,
            valid_fit_cells=len(target),n_experts=x.shape[1],historical_U_cap_power=limit,
            raw_smoothed_prior=raw.tolist(),canonical_initial=canonical.tolist(),
            source_manifest_sha256=cfg['historical_manifest_sha256'],elapsed_seconds=time.monotonic()-start)
        p=out/'initializers'/phase/f'{goal}_{arm}_seed{seed}.json';save(p,record);records[goal]=str(p)
    return dict(phase=phase,seed=seed,arm=arm,files=records)


def load_phase(cfg,phase,seed,arm):
    cache=Path(cfg['evaluation_cache'] if phase=='evaluate' else cfg['historical_cache'])
    a=np.load(cache/'anchors.npy');y=np.load(cache/'shortfall.npy');m=np.load(cache/'mask.npy')
    x=np.load(cache/f'{arm}_seed{seed}.npy',mmap_mode='r')
    return cache,a,y,m,x


def execute_task(task):
    cfg,out,phase,seed,arm,recipes,deadline=task;out=Path(out);deadline_check(deadline)
    cache,a,y,m,x=load_phase(cfg,phase,seed,arm)
    begin,end,_=PHASES[phase];use=(a>=begin)&(a<end)
    aa=a[use];yy=y[use];mm=m[use];xx=np.asarray(x[use])
    if phase=='evaluate' and (len(aa)!=5033 or int(mm.sum())!=672939):raise ValueError('Evaluation population differs')
    goal_records={g:json.loads((out/'initializers'/phase/f'{g}_{arm}_seed{seed}.json').read_text()) for g in ['COST','CAP']}
    destination=out/'instances'/phase/f'{arm}_seed{seed}';destination.mkdir(parents=True,exist_ok=False)
    status={};point={};ledgers={};hashes={};metadata={};errors={}
    def record(recipe,actions=None,ledger=None,info=None):
        rid=recipe['id']
        if ledger is None:ledger,counts,days=score_actions(actions,yy,mm,aa)
        else:
            days=np.unique(aa//144);counts=np.asarray([mm[aa//144==d].sum() for d in days])
        if ledger.shape!=(len(days),4) or not np.isfinite(ledger).all():raise ValueError('Invalid candidate ledger')
        ledgers[rid]=ledger;point[rid]=(ledger.sum(axis=0)/counts.sum()).tolist();status[rid]='COMPLETED'
        metadata[rid]=info or {}
        if actions is not None:hashes[rid]=hashlib.sha256(np.ascontiguousarray(actions,dtype='<f8').tobytes()).hexdigest()
    def failed(recipe,exc):
        rid=recipe['id'];status[rid]='FAILED_PRESERVED';errors[rid]=dict(error=repr(exc),traceback=traceback.format_exc())
    # First finish the matched fixed/online controls for every fixed instance.
    for recipe in [r for r in recipes if r['kind'].startswith('control')]:
        deadline_check(deadline)
        try:
            rec=goal_records[recipe['goal']]
            if recipe['kind']=='control_exact':w=np.asarray(rec['weights']);action=np.sum(xx*w,axis=-1)
            elif recipe['kind']=='control_fixed':w=np.asarray(rec['canonical_initial']);action=np.sum(xx*w,axis=-1)
            else:
                action=run_matched_ew(xx,yy,mm,aa,np.asarray(rec['canonical_initial']))
                fixed=np.sum(xx*np.asarray(rec['canonical_initial']),axis=-1)
                if not np.array_equal(action[:8],fixed[:8]):raise ValueError('Matched initial action is not bitwise equal')
            record(recipe,actions=action,info=dict(initializer_status=rec['status'],initializer_optimal=rec['optimal']))
        except Exception as exc:failed(recipe,exc)
    for goal in ['COST','CAP']:
        group=[r for r in recipes if r['kind']=='actual' and r['goal']==goal]
        if not group:continue
        configs=[MixtureConfig(**r['config']) for r in group];initial=np.asarray(goal_records[goal]['canonical_initial'])
        try:
            deadline_check(deadline);result=run_mixture(xx,yy,mm,aa,configs,initial,return_actions=True)
            fixed=np.sum(xx*initial,axis=-1)
            if not np.array_equal(result['actions'][:,:8],np.broadcast_to(fixed[:8],(len(group),8,xx.shape[1]))):
                raise ValueError('Actual-loss update does not share the exact initial actions')
            for i,recipe in enumerate(group):
                record(recipe,actions=result['actions'][i],ledger=result['ledger'][i],info=dict(
                    final_weights=result['metadata']['final_weights'][i],
                    final_lambda_u=result['metadata']['final_lambda_u'][i],
                    maximum_lambda_u=result['metadata']['maximum_lambda_u'][i],
                    initializer_status=goal_records[goal]['status'],
                    feedback_rule='source_anchor+7<decision_anchor'))
        except Exception as batch_error:
            save(destination/f'{goal}_batch_failure.json',dict(error=repr(batch_error),traceback=traceback.format_exc()))
            for recipe in group:
                try:
                    deadline_check(deadline)
                    z=run_mixture(xx,yy,mm,aa,[MixtureConfig(**recipe['config'])],initial,return_actions=True)
                    record(recipe,actions=z['actions'][0],ledger=z['ledger'][0],info=z['metadata'])
                except Exception as exc:failed(recipe,exc)
    legacy=[r for r in recipes if r['kind']=='legacy']
    # These pre-existing recipes retain their original causal history. They are
    # coverage probes, not the matched-initialization update comparison.
    if legacy:
        hist=Path(cfg['historical_cache']);ha=np.load(hist/'anchors.npy');hy=np.load(hist/'shortfall.npy');hm=np.load(hist/'mask.npy')
        hx=np.load(hist/f'{arm}_seed{seed}.npy',mmap_mode='r')
        if phase=='evaluate':
            ax=np.r_[ha,aa];tx=np.concatenate([hy,yy]);mx=np.concatenate([hm,mm]);ex=np.concatenate([hx,xx]);offset=len(ha)
        else:
            stop=int(np.searchsorted(ha,end));ax=ha[:stop];tx=hy[:stop];mx=hm[:stop];ex=np.asarray(hx[:stop]);offset=int(np.searchsorted(ax,begin))
        for i in range(0,len(legacy),16):
            batch=legacy[i:i+16];aggs=[r for r in batch if r['legacy']['kind']=='aggregation']
            def old_one(recipe):
                old=recipe['legacy']
                if old['kind']=='aggregation':
                    result=aggregate_batch(ex,tx,mx,ax,[AggregationConfig(**old['config'])],
                        old_prior(old,ex.shape[-1])[None,:],return_actions=True)
                    return result.actions[0,offset:]
                result=run_delayed_calibration(ex[:,:,old['base_index']],tx,mx,ax,
                    DelayedCalibrationConfig(**old['config']),save_trace=False)
                return result.actions[offset:]
            if aggs:
                try:
                    deadline_check(deadline)
                    z=aggregate_batch(ex,tx,mx,ax,[AggregationConfig(**r['legacy']['config']) for r in aggs],
                        np.stack([old_prior(r['legacy'],ex.shape[-1]) for r in aggs]),return_actions=True)
                    for j,recipe in enumerate(aggs):record(recipe,actions=z.actions[j,offset:])
                except Exception as exc:
                    save(destination/f'legacy_batch_{i}_failure.json',dict(error=repr(exc)))
                    for recipe in aggs:
                        try:deadline_check(deadline);record(recipe,actions=old_one(recipe))
                        except Exception as error:failed(recipe,error)
            for recipe in [r for r in batch if r not in aggs]:
                try:deadline_check(deadline);record(recipe,actions=old_one(recipe))
                except Exception as exc:failed(recipe,exc)
    # REF and every planned recipe receive a slot; failures are never censored.
    ref,counts,days=score_actions(xx[:,:,0],yy,mm,aa)
    ids=[r['id'] for r in recipes];array=np.full((len(ids),len(days),4),np.nan)
    for i,rid in enumerate(ids):
        if rid in ledgers:array[i]=ledgers[rid]
        if rid not in status:status[rid]='NOT_EVALUATED_PRESERVED'
    np.savez_compressed(destination/'daily.npz',ledger=array,reference=ref,counts=counts,days=days)
    save(destination/'receipt.json',dict(phase=phase,seed=seed,arm=arm,ids=ids,status=status,
        metrics=point,action_sha256=hashes,metadata=metadata,errors=errors,
        source_manifest_sha256=cfg['evaluation_manifest_sha256'] if phase=='evaluate' else cfg['historical_manifest_sha256'],
        complete_expected=len(recipes),completed=sum(v=='COMPLETED' for v in status.values()),
        scientific_qualification_used_to_filter=False))
    return dict(phase=phase,seed=seed,arm=arm,completed=sum(v=='COMPLETED' for v in status.values()),expected=len(recipes))


def old_prior(recipe,k):
    p=recipe.get('prior','uniform')
    if p=='uniform':return np.full(k,1/k)
    if p=='reference_half':
        w=np.full(k,.5/(k-1));w[0]=.5;return w
    if p.startswith('expert_'):
        w=np.zeros(k);w[int(p.split('_')[1])]=1;return w
    if p.startswith('blend_'):
        _,idx,alpha=p.split('_');w=np.zeros(k);w[0]=1-float(alpha);w[int(idx)]+=float(alpha);return w
    raise ValueError('Unknown frozen prior')


def collect(out,phase,recipes):
    out=Path(out);points=np.full((len(recipes),5,2,4),np.nan);ledgers={}
    for si,seed in enumerate(SEEDS):
        for ai,arm in enumerate(ARMS):
            folder=out/'instances'/phase/f'{arm}_seed{seed}';d=np.load(folder/'daily.npz');receipt=json.loads((folder/'receipt.json').read_text())
            for j,recipe in enumerate(recipes):
                if str(recipe['id']) in receipt['metrics']:points[j,si,ai]=receipt['metrics'][str(recipe['id'])]
            ledgers[seed,arm]=d['ledger']
    return points,ledgers


def history_summary(points,recipes):
    complete=np.isfinite(points).all(axis=(1,2,3));roles={}
    for ai,arm in enumerate(ARMS):
        for family in ['actual_cost','actual_u','coverage','protection','controls']:
            pool=[j for j,r in enumerate(recipes) if r['family']==family and complete[j]]
            if pool:
                best=min(pool,key=lambda j:(points[j,:,ai,0].mean(),recipes[j]['id']))
                # Independent protection representative; no risk qualification filter.
                protect=min(pool,key=lambda j:(points[j,:,ai,3].max(),points[j,:,ai,2].max(),points[j,:,ai,0].mean()))
                roles[family+'_'+arm]=dict(minimum_C_id=recipes[best]['id'],minimum_maxV_id=recipes[protect]['id'])
    return dict(roles=roles,complete_recipe_count=int(complete.sum()),all_recipes_retained=True,
        qualification_did_not_filter_instances=True,selection_scope='Historical only; all recipes still scored in evaluation')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--protocol',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();cfg=json.loads(args.protocol.read_text())
    if not os.environ.get('PBS_JOBID'):raise RuntimeError('Bounded Metis PBS allocation required')
    if cfg['max_candidates']!=200 or cfg['max_cpu_seconds']!=14400 or len(cfg['recipes'])>198:
        raise ValueError('Authorized small-loop budget differs')
    if not os.environ.get('CAMPAIGN_RELEASE'):raise RuntimeError('Missing exact source release identity')
    reservation=cfg['budget_reservation']
    if (reservation['slots']!=200 or reservation['cpu_seconds']!=14400
        or reservation['global_total_slots']>2000 or reservation['global_total_cpu_seconds']>86400):
        raise ValueError('Cumulative budget reservation is invalid')
    if 2*cfg['job_wall_seconds']+cfg['preflight_cpu_reserve_seconds']>14400:
        raise ValueError('Parallel allocation exceeds four CPU hours')
    out=args.output;out.mkdir(parents=True,exist_ok=False);start=time.time();deadline=start+cfg['job_wall_seconds']-60
    recipes=cfg['recipes'];source_files=[ROOT/p for p in cfg['source_files']]
    source_versions={str(p.relative_to(ROOT)):sha(p) for p in source_files}
    save(out/'source_versions.json',source_versions);save(out/'protocol.json',cfg)
    state=dict(status='PREFLIGHT',job_id=os.environ['PBS_JOBID'],host=platform.node(),python=sys.version,
        numpy=np.__version__,scipy=scipy.__version__,started_utc=datetime.now(timezone.utc).isoformat(),
        recipes=len(recipes),planned_instances_per_phase=len(recipes)*10,phase_receipts=[],
        source_commit=os.environ.get('CAMPAIGN_RELEASE','UNSET'),clock='source_issue+7<decision_issue',independent_confirmation=False)
    def checkpoint(status):
        state.update(status=status,elapsed_seconds=time.time()-start,allocated_cpu_seconds=2*(time.time()-start));save(out/'state.json',state)
        print(json.dumps(state),flush=True)
    try:
        verify_cache(cfg['historical_cache'],cfg['historical_manifest_sha256'])
        a=np.load(Path(cfg['historical_cache'])/'anchors.npy')
        if not np.array_equal(a,np.arange(27648,30233)):raise ValueError('Historical grid changed')
        with ProcessPoolExecutor(max_workers=2) as pool:
            checkpoint('ALIGNED_HISTORY_INITIALIZATION')
            tasks=[(cfg,str(out),phase,seed,arm,deadline) for phase in PHASES for seed in SEEDS for arm in ARMS]
            fits=list(pool.map(fit_task,tasks));save(out/'initializer_receipts.json',fits)
            for phase in ['inner','outer']:
                checkpoint('HISTORICAL_'+phase.upper())
                tasks=[(cfg,str(out),phase,seed,arm,recipes,deadline) for seed in SEEDS for arm in ARMS]
                state['phase_receipts']+=list(pool.map(execute_task,tasks))
                points,_=collect(out,phase,recipes)
                np.save(out/(phase+'_points.npy'),points,allow_pickle=False)
                save(out/(phase+'_selection.json'),history_summary(points,recipes))
            save(out/'FINAL_FREEZE.json',dict(time_utc=datetime.now(timezone.utc).isoformat(),
                recipes=recipes,historical_roles=json.loads((out/'outer_selection.json').read_text()),
                all_initializers={str(f.relative_to(out)):sha(f) for f in (out/'initializers').rglob('*.json')},
                source_versions=source_versions,protocol_sha256=sha(args.protocol),
                selection_scope='Already exposed development; every planned recipe/fixed instance is evaluated'))
            if any(sha(ROOT/p)!=h for p,h in source_versions.items()):raise ValueError('Source changed before evaluation')
            with (out/'EVALUATION_OPEN.json').open('x') as f:json.dump(dict(time_utc=datetime.now(timezone.utc).isoformat(),freeze_sha256=sha(out/'FINAL_FREEZE.json')),f)
            verify_cache(cfg['evaluation_cache'],cfg['evaluation_manifest_sha256'])
            checkpoint('ALL_INSTANCE_EVALUATION')
            tasks=[(cfg,str(out),'evaluate',seed,arm,recipes,deadline) for seed in SEEDS for arm in ARMS]
            state['phase_receipts']+=list(pool.map(execute_task,tasks))
        points,ledgers=collect(out,'evaluate',recipes);np.save(out/'evaluation_points.npy',points,allow_pickle=False)
        parent=Path(cfg['parent_ledger']);descriptor=cfg['parent_family']
        if sha(parent)!=cfg['parent_ledger_sha256']:raise ValueError('Parent evidence changed')
        old=np.load(parent);names=list(descriptor['policy_names']);all_ledger=old['ledger'].copy()
        for si,seed in enumerate(SEEDS):
            for arm in ARMS:
                d=np.load(out/'instances/evaluate'/f'{arm}_seed{seed}'/'daily.npz')
                if (not np.array_equal(d['counts'],old['counts']) or not np.array_equal(d['days'],old['day_ids'])
                    or not np.allclose(d['reference'],old['ledger'][si,0],rtol=0,atol=1e-8)):
                    raise ValueError('Reference/target population bridge changed')
        available=list(descriptor['available']);aliases=[tuple(p) for p in cfg['full_aliases']]
        for j,recipe in enumerate(recipes):
            for ai,arm in enumerate(ARMS):
                names.append(f'R{recipe["id"]:04d}_{arm}')
                panel=np.stack([ledgers[seed,arm][j] for seed in SEEDS])
                all_ledger=np.concatenate([all_ledger,panel[:,None]],axis=1)
                available.append(bool(np.isfinite(panel).all()))
        comparisons=[tuple(pair) for pair in cfg['comparisons']]
        if len(names)*11+len(comparisons)*10!=cfg['nominal_family_size']:raise ValueError('Comparison family changed')
        np.savez_compressed(out/'all_daily_ledger.npz',ledger=all_ledger,counts=old['counts'],day_ids=old['day_ids'])
        save(out/'all_policy_names.json',dict(names=names,available=available,aliases=aliases,comparisons=comparisons))
        checkpoint('FROZEN_FAMILY_INFERENCE')
        for span in [3,1,7]:
            deadline_check(deadline)
            result=infer_campaign(all_ledger,old['counts'],names,comparisons,span=span,available=available,aliases=aliases)
            save(out/f'inference_span{span}.json',result)
        if sha(out/'FINAL_FREEZE.json')!=json.loads((out/'EVALUATION_OPEN.json').read_text())['freeze_sha256']:
            raise ValueError('Final freeze changed')
        if any(sha(ROOT/p)!=h for p,h in source_versions.items()):raise ValueError('Source changed during replay')
        verify_cache(cfg['historical_cache'],cfg['historical_manifest_sha256'])
        verify_cache(cfg['evaluation_cache'],cfg['evaluation_manifest_sha256'])
        totals={p:sum(r['completed'] for r in state['phase_receipts'] if r['phase']==p) for p in PHASES}
        all_complete=all(n==len(recipes)*10 for n in totals.values())
        save(out/'completion.json',dict(status='COMPLETED_ALL_PREDEFINED_INSTANCES' if all_complete else 'COMPLETED_WITH_PRESERVED_FAILURES',
            planned_recipes=len(recipes),planned_instances_per_phase=len(recipes)*10,
            complete_per_phase=totals,all_predefined_instances_scored=all_complete,
            elapsed_seconds=time.time()-start,old_results_written=False,thresholds_changed=False,
            independent_confirmation=False,all_planned_instances_retained=True))
        checkpoint('COMPLETED_EXPLORATORY_DEVELOPMENT')
    except BaseException as exc:
        save(out/'failure.json',dict(error=repr(exc),traceback=traceback.format_exc()))
        checkpoint('FAILED_OR_BUDGET_PRESERVED');raise


if __name__=='__main__':main()
