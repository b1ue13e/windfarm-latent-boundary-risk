"""Two disclosed post-result protection-floor programs within the original cap."""
import argparse,json,os,sys,time,traceback,platform
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from datetime import datetime,timezone
from repo_paths import Path, repository_root
ROOT=Path(repository_root());sys.path.insert(0,str(ROOT))
import numpy as np
from threadpoolctl import threadpool_limits
from windfarm_moe.protected_residual import residual_experts,guarded_action
from windfarm_moe.actual_mixture_update import MixtureConfig,run_mixture
from windfarm_moe.static_convex_bundle import fit_bundle
from windfarm_moe.delayed_calibration_baselines import DelayedCalibrationConfig,run_delayed_calibration
from windfarm_moe.autonomous_campaign_inference import infer_campaign
from scripts.run_mixture_closed_loop import sha,save,deadline_check,score_actions,verify_cache,PHASES


def profile_task(task):
    cfg,out,seed,evaluation=task;out=Path(out);h=Path(cfg['historical_cache'])
    ha=np.load(h/'anchors.npy');hy=np.load(h/'shortfall.npy');hm=np.load(h/'mask.npy')
    hx=np.load(h/f'P_seed{seed}.npy',mmap_mode='r')[:,:,0]
    if evaluation:
        e=Path(cfg['evaluation_cache']);ea=np.load(e/'anchors.npy');ey=np.load(e/'shortfall.npy');em=np.load(e/'mask.npy')
        ex=np.load(e/f'P_seed{seed}.npy',mmap_mode='r')[:,:,0]
        a=np.r_[ha,ea];y=np.r_[hy,ey];m=np.r_[hm,em];x=np.r_[hx,ex]
    else:a,y,m,x=ha,hy,hm,hx
    result=run_delayed_calibration(x,y,m,a,DelayedCalibrationConfig(**cfg['anchor_config']),save_trace=False).actions
    if evaluation:
        result=result[len(ha):]
        expected=json.loads((Path(cfg['parent_results'])/f'instances/evaluate/P_seed{seed}/receipt.json').read_text())['action_sha256'][str(cfg['anchor_id'])]
        import hashlib
        actual=hashlib.sha256(np.ascontiguousarray(result,dtype='<f8').tobytes()).hexdigest()
        if actual!=expected:raise ValueError('Protection anchor identity changed')
    path=out/'profiles'/f'{"evaluate" if evaluation else "historical"}_seed{seed}.npy'
    path.parent.mkdir(parents=True,exist_ok=True);np.save(path,result,allow_pickle=False)
    return dict(seed=seed,evaluation=evaluation,sha256=sha(path))


def fit_task(task):
    cfg,out,phase,seed,arm,deadline=task;out=Path(out);deadline_check(deadline)
    h=Path(cfg['historical_cache']);a=np.load(h/'anchors.npy');y=np.load(h/'shortfall.npy');m=np.load(h/'mask.npy')
    b=np.load(out/f'profiles/historical_seed{seed}.npy');x=np.load(h/f'{arm}_seed{seed}.npy',mmap_mode='r')
    begin,end,cut=PHASES[phase];use=a<cut
    assert int(a[use].max())+7<begin
    delta=residual_experts(np.asarray(x[use]),b[use])[m[use]]
    target=np.maximum(y[use]-b[use],0)[m[use]]
    with threadpool_limits(limits=1):result=fit_bundle(delta,target,time_limit=12.,max_iter=1200)
    # Projection can reactivate zero weights; unlike EW, this comparison needs
    # no artificial full-support smoothing. Keep the strongest numerical LP
    # initial weights exactly identical for fixed and online programs.
    record=asdict(result);canonical=np.asarray(result.weights).copy()
    record.update(phase=phase,seed=seed,arm=arm,fit_window=[27648,cut],episode_start=begin,
        last_label_release=int(a[use].max())+7,valid_fit_cells=len(target),canonical_initial=canonical.tolist(),
        baseline_mean_energy=float(b[use][m[use]].mean()/6),internal_objective='residual C; add baseline energy to recover original C')
    save(out/f'initializers/{phase}/{arm}_seed{seed}.json',record)
    return dict(phase=phase,seed=seed,arm=arm,optimal=result.optimal)


def eval_task(task):
    cfg,out,phase,seed,arm,deadline=task;out=Path(out);deadline_check(deadline)
    folder=Path(cfg['evaluation_cache'] if phase=='evaluate' else cfg['historical_cache'])
    a=np.load(folder/'anchors.npy');y=np.load(folder/'shortfall.npy');m=np.load(folder/'mask.npy');x=np.load(folder/f'{arm}_seed{seed}.npy',mmap_mode='r')
    b=np.load(out/f'profiles/{"evaluate" if phase=="evaluate" else "historical"}_seed{seed}.npy')
    begin,end,_=PHASES[phase];use=(a>=begin)&(a<end);a=a[use];y=y[use];m=m[use];b=b[use];x=np.asarray(x[use])
    delta=residual_experts(x,b);init=json.loads((out/f'initializers/{phase}/{arm}_seed{seed}.json').read_text())
    w=np.asarray(init['canonical_initial']);static=guarded_action(b,delta,w)
    config=MixtureConfig(**cfg['online_config'][arm])
    # Internal reparameterization only. Original y is retained for every score.
    residual_target=np.maximum(y-b,0)
    result=run_mixture(delta,residual_target,m,a,[config],w,score=False,return_actions=True)
    online=b+result['actions'][0]
    if not np.array_equal(static[:8],online[:8]):raise ValueError('Warm-start actions differ')
    rows=[];hashes=[]
    import hashlib
    for action in [static,online]:
        if np.any(action<b):raise ValueError('Pointwise protection floor broken')
        if np.any(np.maximum(y-action,0)[m]>np.maximum(y-b,0)[m]) or np.any((y>action)[m]>(y>b)[m]):
            raise ValueError('Original-target protection dominance broken')
        ledger,counts,days=score_actions(action,y,m,a);rows.append(ledger)
        hashes.append(hashlib.sha256(np.ascontiguousarray(action,dtype='<f8').tobytes()).hexdigest())
    path=out/f'instances/{phase}/{arm}_seed{seed}';path.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(path/'daily.npz',ledger=np.stack(rows),counts=counts,days=days)
    save(path/'receipt.json',dict(seed=seed,arm=arm,phase=phase,completed=2,expected=2,action_sha256=hashes,
        initializer_optimal=init['optimal'],science_target_unchanged=True,
        pointwise_U_V_dominance_verified=True,qualification_filter=False))
    return dict(phase=phase,seed=seed,arm=arm,completed=2,expected=2)


def load_bound_parent_protocol(parent_results,source_input):
    parent=Path(parent_results);src=Path(source_input)
    if not src.is_absolute():src=ROOT/src
    parent_freeze=json.loads((parent/'FINAL_FREEZE.json').read_text(encoding='utf-8'))
    if sha(src)!=parent_freeze['protocol_sha256']:raise ValueError('Parent protocol identity changed')
    src_cfg=json.loads(src.read_text(encoding='utf-8'))
    res_cfg=json.loads((parent/'protocol.json').read_text(encoding='utf-8'))
    if src_cfg!=res_cfg:raise ValueError('Parent protocol copy diverged')
    return res_cfg


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--protocol',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();cfg=json.loads(args.protocol.read_text());out=args.output;out.mkdir(parents=True,exist_ok=False)
    if not os.environ.get('PBS_JOBID'):raise RuntimeError('Bounded Metis allocation required')
    if cfg['total_stage_candidates']!=200 or cfg['maximum_accounted_cpu_seconds']>14400:raise ValueError('Original stage budget exceeded')
    parent=Path(cfg['parent_results']);assert sha(parent/'FINAL_FREEZE.json')==cfg['parent_freeze_sha256']
    parent_cfg=load_bound_parent_protocol(parent,cfg['parent_input_protocol'])
    if any(cfg[key]!=parent_cfg[key] for key in ['historical_cache','evaluation_cache']):raise ValueError('Parent input path changed')
    verify_cache(cfg['historical_cache'],parent_cfg['historical_manifest_sha256'])
    start=time.time();deadline=start+cfg['job_wall_seconds']-30
    save(out/'protocol.json',cfg);versions={p:sha(ROOT/p) for p in cfg['source_files']};save(out/'source_versions.json',versions)
    state=dict(job_id=os.environ['PBS_JOBID'],source_commit=os.environ.get('CAMPAIGN_RELEASE'),
        host=platform.node(),python=sys.version,numpy=np.__version__,scipy=__import__('scipy').__version__,
        started_utc=datetime.now(timezone.utc).isoformat(),status='PREPARING',receipts=[],new_candidates=2)
    def checkpoint(status):
        state.update(status=status,elapsed_seconds=time.time()-start);save(out/'state.json',state);print(json.dumps(state),flush=True)
    try:
        with ProcessPoolExecutor(max_workers=2) as pool:
            checkpoint('HISTORICAL_PROFILES')
            list(pool.map(profile_task,[(cfg,str(out),seed,False) for seed in range(201,206)]))
            fits=list(pool.map(fit_task,[(cfg,str(out),phase,seed,arm,deadline) for phase in PHASES for seed in range(201,206) for arm in ['P','Z']]))
            save(out/'fit_receipts.json',fits)
            for phase in ['inner','outer']:
                state['receipts']+=list(pool.map(eval_task,[(cfg,str(out),phase,seed,arm,deadline) for seed in range(201,206) for arm in ['P','Z']]))
            save(out/'FINAL_FREEZE.json',dict(time_utc=datetime.now(timezone.utc).isoformat(),
                post_result_exploratory_addendum=True,anchor_id=cfg['anchor_id'],online_config=cfg['online_config'],
                initializers={str(f.relative_to(out)):sha(f) for f in (out/'initializers').rglob('*.json')},
                source_versions=versions,protocol_sha256=sha(args.protocol)))
            with (out/'EVALUATION_OPEN.json').open('x') as f:json.dump(dict(time_utc=datetime.now(timezone.utc).isoformat(),freeze_sha256=sha(out/'FINAL_FREEZE.json')),f)
            checkpoint('EVALUATING_BOTH_COMPLETE_PROGRAMS')
            verify_cache(cfg['evaluation_cache'],parent_cfg['evaluation_manifest_sha256'])
            list(pool.map(profile_task,[(cfg,str(out),seed,True) for seed in range(201,206)]))
            state['receipts']+=list(pool.map(eval_task,[(cfg,str(out),'evaluate',seed,arm,deadline) for seed in range(201,206) for arm in ['P','Z']]))
        z=np.load(parent/'all_daily_ledger.npz');family=json.loads((parent/'all_policy_names.json').read_text())
        names=family['names']+['GUARDED_FIXED_P','GUARDED_FIXED_Z','GUARDED_ONLINE_P','GUARDED_ONLINE_Z']
        extra=np.empty((5,4,35,4))
        for si,seed in enumerate(range(201,206)):
            for ai,arm in enumerate(['P','Z']):
                d=np.load(out/f'instances/evaluate/{arm}_seed{seed}/daily.npz')
                if not np.array_equal(d['counts'],z['counts']):raise ValueError('Original score population differs')
                extra[si,ai]=d['ledger'][0];extra[si,2+ai]=d['ledger'][1]
        data=np.concatenate([z['ledger'],extra],axis=1);pairs=[tuple(p) for p in family['comparisons']]
        pairs += [('GUARDED_FIXED_Z','GUARDED_FIXED_P'),('GUARDED_ONLINE_Z','GUARDED_ONLINE_P')]
        for arm in ['P','Z']:
            pairs += [(f'GUARDED_FIXED_{arm}',f'R{cfg["anchor_id"]:04d}_{arm}'),
                (f'GUARDED_ONLINE_{arm}',f'R{cfg["anchor_id"]:04d}_{arm}'),(f'GUARDED_ONLINE_{arm}',f'GUARDED_FIXED_{arm}')]
        assert len(names)*11+len(pairs)*10==12646
        np.savez_compressed(out/'all_daily_ledger.npz',ledger=data,counts=z['counts'],day_ids=z['day_ids'])
        checkpoint('INFERENCE')
        for span in [3,1,7]:
            deadline_check(deadline);result=infer_campaign(data,z['counts'],names,pairs,span=span,
                available=family['available']+[True]*4,aliases=family['aliases'])
            save(out/f'inference_span{span}.json',result)
        if any(sha(ROOT/p)!=h for p,h in versions.items()):raise ValueError('Source changed')
        verify_cache(cfg['historical_cache'],parent_cfg['historical_manifest_sha256'])
        verify_cache(cfg['evaluation_cache'],parent_cfg['evaluation_manifest_sha256'])
        save(out/'completion.json',dict(status='COMPLETED',new_candidates=2,total_stage_candidates=200,
            complete_per_phase={phase:sum(r['completed'] for r in state['receipts'] if r['phase']==phase) for phase in PHASES},
            target_unchanged=True,thresholds_changed=False,post_result_exploratory=True,independent_confirmation=False))
        checkpoint('COMPLETED')
    except BaseException as exc:
        save(out/'failure.json',dict(error=repr(exc),traceback=traceback.format_exc()));checkpoint('FAILED_PRESERVED');raise


if __name__=='__main__':main()
