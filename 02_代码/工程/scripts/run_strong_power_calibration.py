"""Historical selection of finite strong direct and conditional-calibration controls."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import importlib.metadata
import json,os,platform,shutil,sys,time
from repo_paths import Path, repository_root
import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

ROOT=Path(repository_root())
sys.path.insert(0,str(ROOT))
from scripts.run_dynamic_addback import sha,save,finish,verify_old,verify_new,predict
from scripts.run_decision_information_development import load_stage,learner,subsample
from windfarm_moe.conditional_power_calibration import feature_sets,GroupOffset,choose_cost,choose_pitch
from windfarm_moe.dynamic_addback import daily
from windfarm_moe.risk_frontier import shared_block_draws,simultaneous_envelope


def begin(args,inputs):
    args.output.mkdir(parents=True,exist_ok=False)
    sources=[Path(__file__),args.protocol,*[ROOT/p for p in [
        'scripts/run_dynamic_addback.py','scripts/run_decision_information_development.py',
        'windfarm_moe/conditional_power_calibration.py','windfarm_moe/dynamic_addback.py',
        'windfarm_moe/decision_information.py','windfarm_moe/risk_frontier.py']]]
    hashes={}
    for p in sources:
        name=p.resolve().relative_to(ROOT).as_posix();dest=args.output/'source'/name
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);hashes[name]=sha(p)
    rec=dict(status='RUNNING',stage=args.stage,seed=args.seed,argv=sys.argv,
        started_utc=datetime.now(timezone.utc).isoformat(),host=platform.node(),platform=platform.platform(),
        python=sys.version,packages={k:importlib.metadata.version(k) for k in ['numpy','pandas','scikit-learn','joblib']},
        protocol_sha256=sha(args.protocol),source_sha256=hashes,input_sha256={str(p):sha(p) for p in inputs},
        pbs_job_id=os.environ.get('PBS_JOBID'),threads=2,backend='CPU HGB; CUDA unused',
        scope='Exposed WTB development; no independent confirmation, equal-budget or field-value claim')
    rec['cpu']=next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),'unknown') if Path('/proc/cpuinfo').exists() else platform.processor()
    save(args.output/'receipt.json',rec);return rec


def candidate_keys(cfg):
    return [f'{rep}__{model}__{cal}' for rep in cfg['representations'] for model in cfg['models'] for cal in cfg['calibration_methods']]


def get_stage(prepared,data,name,lo,hi):
    source=load_stage(prepared,data,name,dict(delay_steps=0,pitch_available=False),36,6)
    use=(source['anchors']>=lo)&(source['anchors']<hi)
    row_use=np.repeat(use,data.shape[1])
    result={key:value[row_use if key in ('A','B') else use] for key,value in source.items()}
    if not np.array_equal(result['anchors'],np.arange(lo,hi)):raise ValueError('Calendar mismatch')
    return result


def add_blocks(result,key,phase,stats):
    for field,value in stats.items():result[key+'__'+phase+'__'+field]=value


def run(args,cfg):
    seed=args.seed
    if seed not in cfg['seeds']:raise ValueError('Unregistered seed')
    prepared=Path(cfg['parent_prepared']);prior=Path(cfg['addback_runs'])/f'seed{seed}'
    parent=verify_old(prepared);old=verify_new(prior,cfg['addback_protocol_sha256'])
    if parent['protocol_sha256']!=cfg['parent_protocol_sha256']:raise ValueError('Wrong prepared source')
    for package in ['numpy','pandas','scikit-learn','joblib']:
        if old['packages'][package]!=importlib.metadata.version(package):raise ValueError('Environment mismatch '+package)
    inputs=[prepared/'physical_channels.npy',prepared/'output_manifest.json',prior/'manifest.json',
            prior/'probe_pitch.joblib',prior/'policy_indices.npy',prior/'actions.npz',
            *[prepared/f'{p}_forecast.npz' for p in ['policy_fit','calibration','development_evaluation']]]
    rec=begin(args,inputs);timer=time.monotonic()
    data=np.load(prepared/'physical_channels.npy',mmap_mode='r')
    probe=joblib.load(prior/'probe_pitch.joblib')
    stages={};features={};contexts={};extra={}
    for name,(lo,hi) in cfg['stages'].items():
        source='policy_fit' if name=='fit' else 'development_evaluation' if name=='evaluate' else 'calibration'
        stage=get_stage(prepared,data,source,lo,hi)
        score=predict(probe,stage['B']).astype(np.float32)
        features[name],contexts[name],extra[name]=feature_sets(data,stage['anchors'],stage['A'],stage['B'],score)
        stages[name]=stage
    ix=subsample(stages['fit']['mask'].reshape(-1),cfg['fit_rows'],seed)
    if not np.array_equal(ix,np.load(prior/'policy_indices.npy')):raise ValueError('Training row mismatch')
    np.save(args.output/'policy_indices.npy',ix)
    calmask=stages['calfit']['mask'].reshape(-1)
    cix=subsample(calmask,120000,seed)
    np.save(args.output/'calibration_indices.npy',cix)
    np.savez_compressed(args.output/'coordinates.npz',**{
        name+'__'+key:stage[key] for name,stage in stages.items() if name in ['select','evaluate'] for key in ['anchors','shortfall','mask']})
    actions={};blocks={};rows=[];models={};bridges={}
    for rep in cfg['representations']:
        for modelname,settings in cfg['models'].items():
            start=time.monotonic();model=learner(settings,seed,True)
            model.fit(features['fit'][rep][ix],stages['fit']['shortfall'].reshape(-1)[ix])
            joblib.dump(model,args.output/f'policy_{rep}_{modelname}.joblib')
            raw={phase:np.maximum(predict(model,features[phase][rep]),0) for phase in ['calfit','select','evaluate']}
            residual=stages['calfit']['shortfall'].reshape(-1)-raw['calfit']
            global_q=float(np.quantile(residual[calmask],.9,method='higher'))
            cc=extra['calfit']
            grouper=GroupOffset().fit(cc['level'][calmask,0],cc['wind'].reshape(-1)[calmask],cc['trend'][calmask,1],residual[calmask])
            conditional=learner(dict(max_iter=100,max_leaf_nodes=15,min_samples_leaf=100,learning_rate=.05,l2_regularization=1.0),seed,True)
            xc=np.column_stack((contexts['calfit'][rep],raw['calfit']))
            conditional.fit(xc[cix],residual[cix]);joblib.dump(conditional,args.output/f'calibrator_{rep}_{modelname}.joblib')
            save(args.output/f'calibration_{rep}_{modelname}.json',dict(global_q=global_q,
                p_edges=grouper.p_edges_.tolist(),w_edges=grouper.w_edges_.tolist(),
                offsets=grouper.offsets_,global_fallback=grouper.global_))
            for phase in ['select','evaluate']:
                s=stages[phase];e=extra[phase]
                corrections={'GLOBAL':global_q,
                    'GROUP':grouper.predict(e['level'][:,0],e['wind'].reshape(-1),e['trend'][:,1]),
                    'CONDITIONAL':predict(conditional,np.column_stack((contexts[phase][rep],raw[phase])))}
                for cal in cfg['calibration_methods']:
                    key=f'{rep}__{modelname}__{cal}'
                    r=np.maximum(raw[phase]+corrections[cal],0).reshape(s['mask'].shape)
                    actions[key+'__'+phase]=r
                    stats=daily(s['shortfall'],r,s['mask'],s['anchors'],e['group'])
                    add_blocks(blocks,key,phase,stats)
                    n=stats['all__N'].sum()
                    rows.append(dict(seed=seed,key=key,phase=phase,N=int(n),
                        **{k:float(stats['all__'+k].sum()/n) for k in ['C','R','U','V']}))
                if rep in ['COMPACT','FULL','COMPACT_G'] and modelname=='BASE' and phase=='evaluate':
                    oldname={'COMPACT':'PQ_TV','FULL':'FULL','COMPACT_G':'G_PQ_TV'}[rep]
                    with np.load(prior/'actions.npz') as z:
                        delta=float(np.max(np.abs(raw[phase].reshape(s['mask'].shape)-z[oldname+'__raw'])))
                    bridges[rep]=delta
                    if delta>1e-9:raise ValueError('Raw reference changed '+rep)
            models[rep+'__'+modelname]=dict(seconds=time.monotonic()-start,n_features=int(model.n_features_in_))
            print('FIT+CAL',seed,rep,modelname,models[rep+'__'+modelname],flush=True)
            del model,conditional,xc,raw
    np.savez_compressed(args.output/'actions.npz',**actions)
    np.savez_compressed(args.output/'daily.npz',**blocks)
    pd.DataFrame(rows).to_csv(args.output/'metrics.csv',index=False)
    save(args.output/'models.json',models);save(args.output/'parent_bridge.json',bridges)
    rec['seconds']=time.monotonic()-timer;finish(args,rec)
    print('COMPLETED',seed,rec['seconds'],flush=True)


def pairs(cfg,choices):
    result=[]
    for left,right in [('COMPACT_G','COMPACT'),('COMPACT_Z','COMPACT'),('FULL_Z','FULL')]:
        for model in cfg['models']:
            for cal in cfg['calibration_methods']:result.append((f'{left}__{model}__{cal}',f'{right}__{model}__{cal}','matched'))
    for rep in cfg['representations']:
        for model in cfg['models']:
            for cal in ['GROUP','CONDITIONAL']:result.append((f'{rep}__{model}__{cal}',f'{rep}__{model}__GLOBAL','calibration'))
    for rep in cfg['representations']:
        for cal in cfg['calibration_methods']:result.append((f'{rep}__LARGE__{cal}',f'{rep}__BASE__{cal}','capacity'))
    result.extend([(choices['SCORE'],choices['POWER'],'selected_score'),(choices['PITCH'],choices['POWER'],'selected_pitch')])
    assert len(result)==55
    return result


def infer(archives,keys,phase,comparisons,span,cfg):
    first=archives[0];n=first[keys[0]+'__'+phase+'__all__N']
    weights,drawhash=shared_block_draws(len(n),cfg['inference']['n_boot'],span,cfg['inference']['seed'])
    denom=weights@n
    if np.any(denom<=0):raise ValueError('Zero full-population denominator')
    points=[];draws=[];exact=[];labels=[]
    for left,right,kind in comparisons:
        for metric in ['C','R','U','V']:
            diff=np.mean([a[left+'__'+phase+'__all__'+metric]-a[right+'__'+phase+'__all__'+metric] for a in archives],axis=0)
            points.append(diff.sum()/n.sum());draws.append((weights@diff)/denom)
            exact.append(left==right)
            labels.append(dict(left=left,right=right,kind=kind,metric=metric,seed=None))
    for key in keys:
        for seed,a in zip(cfg['seeds'],archives):
            numer=a[key+'__'+phase+'__all__V'];points.append(numer.sum()/n.sum());draws.append((weights@numer)/denom);exact.append(False)
            labels.append(dict(left=key,right='',kind='absolute_risk',metric='V',seed=seed))
    matrix=np.asarray(draws).T;bounds=simultaneous_envelope(np.asarray(points),matrix,.05,np.asarray(exact))
    result=[]
    for j,label in enumerate(labels):
        lo,hi=bounds['lower'][j],bounds['upper'][j]
        if label['kind']=='absolute_risk':lo,hi=max(0,lo),min(1,hi)
        result.append(dict(**label,point=float(points[j]),lower=float(lo) if np.isfinite(lo) else None,
            upper=float(hi) if np.isfinite(hi) else None,unknown=bool(bounds['unknown'][j]),span=span))
    return result,dict(critical=bounds['critical'],draw_sha256=drawhash,n_coordinates=len(labels),n_days=len(n))


def summarize(args,cfg):
    roots=[args.runs/f'seed{s}' for s in cfg['seeds']]
    for root in roots:verify_new(root,sha(args.protocol))
    rec=begin(args,[p/name for p in roots for name in ['metrics.csv','daily.npz']])
    allrows=pd.concat([pd.read_csv(p/'metrics.csv') for p in roots],ignore_index=True)
    allrows.to_csv(args.output/'per_fit.csv',index=False)
    means=allrows.groupby(['key','phase'],sort=False)[['C','R','U','V','N']].mean().reset_index()
    means.to_csv(args.output/'means.csv',index=False)
    keys=candidate_keys(cfg);cost={row.key:row.C for row in means[means.phase=='select'].itertuples()}
    power=[k for k in keys if k.split('__')[0] in ['COMPACT','FULL']]
    score=[k for k in keys if k.startswith('COMPACT_G__')]
    pitch=[k for k in keys if k.split('__')[0] in ['COMPACT_Z','FULL_Z']]
    choices=dict(POWER=choose_cost(cost,power),SCORE=choose_cost(cost,score))
    choices['PITCH']=choose_pitch(cost,pitch,choices['POWER'])
    choices['PITCH_IGNORES_Z']=choices['PITCH']==choices['POWER']
    # Selection reads historical means only. Evaluation values do not enter this function.
    save(args.output/'choices.json',dict(choices=choices,historical_costs=cost,uses_evaluation_selection=False))
    archives=[]
    for root in roots:
        with np.load(root/'daily.npz') as z:archives.append({k:z[k] for k in z.files})
    for phase in ['select','evaluate']:
        n=archives[0][keys[0]+'__'+phase+'__all__N']
        for a in archives:
            for key in keys:
                if not np.array_equal(a[key+'__'+phase+'__all__N'],n):raise ValueError('Population mismatch')
    historical,hinfo=infer(archives,keys,'select',[],3,cfg)
    save(args.output/'historical_risk.json',historical)
    choices_risk={}
    for name in ['POWER','SCORE','PITCH']:
        risk=[r for r in historical if r['left']==choices[name]]
        choices_risk[name]=dict(max_upper=max(r['upper'] for r in risk),qualified=all(r['upper']<=.1 and not r['unknown'] for r in risk))
    save(args.output/'historical_labels.json',choices_risk)
    comparisons=pairs(cfg,choices);out=[];info={}
    for span in [3,1,7]:
        rows,meta=infer(archives,keys,'evaluate',comparisons,span,cfg)
        if meta['n_coordinates']!=370:raise ValueError('Frozen family changed')
        out.extend(rows);info[str(span)]=meta
    pd.DataFrame(out).to_csv(args.output/'intervals.csv',index=False)
    save(args.output/'intervals.json',out);save(args.output/'inference.json',info)
    finish(args,rec);print('COMPLETED SUMMARY',choices,flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['run','summarize'],required=True)
    p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int);p.add_argument('--runs',type=Path)
    args=p.parse_args();cfg=json.loads(args.protocol.read_text())
    if not os.environ.get('PBS_JOBID'):raise ValueError('Use an allocated PBS node')
    if 'FILL' in cfg['addback_protocol_sha256']:raise ValueError('Unbound protocol')
    if cfg['task']['rho']!=10 or cfg['task']['horizon']!=6:raise ValueError('Task changed')
    with threadpool_limits(limits=2):
        if args.stage=='run':run(args,cfg)
        else:summarize(args,cfg)


if __name__=='__main__':main()
