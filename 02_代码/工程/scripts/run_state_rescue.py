"""Execute the frozen historical state-rescue pilot on allocated CPU nodes."""
from __future__ import annotations
import argparse,hashlib,importlib.util,importlib.metadata,json,os,platform,shutil,sys,time
from repo_paths import Path, repository_root
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits

ROOT=Path(repository_root())
sys.path.insert(0,str(ROOT))
from windfarm_moe.state_rescue import matrices,group_masks,day_accounting,circular_weights,endpoint,joint_bounds,matched_score_indices,STATES,TRENDS


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def write(path,value):
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')


def ahash(value):return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def source_paths(args):
    return [Path(__file__),ROOT/'windfarm_moe/state_rescue.py',ROOT/'windfarm_moe/decision_information.py',args.protocol]


def start(args):
    if 'PBS_JOBID' not in os.environ:raise RuntimeError('Research computation requires an allocated PBS node')
    args.output.mkdir(parents=True,exist_ok=False)
    source=args.output/'source';source.mkdir()
    for path in source_paths(args):shutil.copyfile(path,source/path.name)
    record={'status':'RUNNING','stage':args.stage,'seed':args.seed,'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
            'argv':sys.argv,'python':sys.version,'numpy':np.__version__,'sklearn':sklearn.__version__,
            'pandas':pd.__version__,'torch_installed':importlib.metadata.version('torch'),
            'backend':'CPU sklearn; CUDA not used','host':platform.node(),'platform':platform.platform(),
            'pbs_job_id':os.environ['PBS_JOBID'],'threads':args.threads,
            'sources':{str(p):sha(p) for p in source_paths(args)},'inputs':{},
            'confirmation':False,'manuscript_changed':False}
    write(args.output/'receipt.json',record)
    return record


def finish(args,record):
    for path,digest in record['inputs'].items():
        if sha(path)!=digest:raise ValueError('Consumed parent changed: '+path)
    for path,digest in record['sources'].items():
        if sha(path)!=digest:raise ValueError('Executing source changed: '+path)
    record.update(status='COMPLETED_DEVELOPMENT',finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    write(args.output/'receipt.json',record)
    write(args.output/'manifest.json',{str(p.relative_to(args.output)):{'bytes':p.stat().st_size,'sha256':sha(p)}
          for p in sorted(args.output.rglob('*')) if p.is_file() and p.name!='manifest.json'})


def consume_bundle(root,names,record,protocol):
    root=Path(root)
    producer=json.loads((root/'execution_receipt.json').read_text())
    if producer['protocol_sha256']!=protocol['parent_protocol_sha256'] or producer['status']!='COMPLETED_DEVELOPMENT_NOT_CERTIFIED':
        raise ValueError('Wrong parent protocol or incomplete producer')
    manifest=json.loads((root/'output_manifest.json').read_text())
    for name in list(names)+['execution_receipt.json']:
        path=root/name
        if name not in manifest or path.stat().st_size!=manifest[name]['bytes'] or sha(path)!=manifest[name]['sha256']:
            raise ValueError('Parent member mismatch: '+str(path))
        record['inputs'][str(path)]=manifest[name]['sha256']
    record['inputs'][str(root/'output_manifest.json')]=sha(root/'output_manifest.json')
    return producer


def legacy_module(protocol,record):
    parent=Path(protocol['parent_root'])
    runner=parent/'scripts/run_decision_information_development.py'
    core=parent/'windfarm_moe/decision_information.py'
    if sha(runner)!=protocol['parent_runner_sha256'] or sha(core)!=protocol['parent_core_sha256']:
        raise ValueError('Legacy implementation identity changed')
    for p in [runner,core]:record['inputs'][str(p)]=sha(p)
    spec=importlib.util.spec_from_file_location('legacy_state_rescue_parent',runner)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def context_learner(settings,seed):
    return Pipeline([('missing',SimpleImputer(strategy='constant',fill_value=0,add_indicator=True,keep_empty_features=True)),
        ('regressor',HistGradientBoostingRegressor(loss='quantile',quantile=.9,random_state=seed,**settings))])


def run(args,protocol):
    record=start(args);legacy=legacy_module(protocol,record)
    parent=Path(protocol['parent_root']);prepared=parent/'results/prepared'
    oldrun=parent/f'results/runs/seed{args.seed}/pitch_withheld'
    parent_protocol=parent/'experiments/decision_information_development_20261018/protocol.json'
    if sha(parent_protocol)!=protocol['parent_protocol_sha256']:raise ValueError('Parent protocol bytes differ')
    record['inputs'][str(parent_protocol)]=sha(parent_protocol)
    original=json.loads(parent_protocol.read_text());settings=original['learner']
    consume_bundle(prepared,['physical_channels.npy','data_manifest.json','policy_fit_forecast.npz',
        'calibration_forecast.npz','development_evaluation_forecast.npz','state_fit_forecast.npz'],record,protocol)
    consumed=['state_pitch.joblib','policy_fit_sample_indices.npy','state_fit_sample_indices.npy',
              'evaluation_coordinates.npz','evaluation_actions.npz','calibration_offsets.json','metrics.csv']
    consumed += ['policy_'+name+'.joblib' for name in protocol['old_variants'].values()]
    producer=consume_bundle(oldrun,consumed,record,protocol)
    if sklearn.__version__!=producer['sklearn'] or np.__version__!=producer['numpy']:
        raise ValueError('Parent model runtime versions differ')
    data=np.load(prepared/'physical_channels.npy',mmap_mode='r')
    condition={'delay_steps':0,'pitch_available':False}
    stages={name:legacy.load_stage(prepared,data,name,condition,36,6)
            for name in ['state_fit','policy_fit','calibration','development_evaluation']}
    evaluation=stages['development_evaluation'];calibration=stages['calibration'];fit=stages['policy_fit']
    with np.load(oldrun/'evaluation_coordinates.npz') as archive:
        for key in ['anchors','forecast','shortfall','mask']:
            if not np.array_equal(evaluation[key],archive[key],equal_nan=True):raise ValueError('Parent coordinate differs: '+key)
    record['coordinate_hashes']={k:ahash(evaluation[k]) for k in ['anchors','forecast','shortfall','mask']}
    indices=np.load(oldrun/'policy_fit_sample_indices.npy')
    np.testing.assert_array_equal(indices,legacy.subsample(fit['mask'].ravel(),settings['max_fit_rows'],args.seed))
    np.save(args.output/'policy_fit_indices.npy',indices)
    oldprobe=joblib.load(oldrun/'state_pitch.joblib')
    oldoffsets=json.loads((oldrun/'calibration_offsets.json').read_text())
    predictions={};old_replay=[]
    with np.load(oldrun/'evaluation_actions.npz') as archive:
        for alias,variant in protocol['old_variants'].items():
            model=joblib.load(oldrun/('policy_'+variant+'.joblib'))
            output={}
            for stage_name in ['calibration','development_evaluation']:
                stage=stages[stage_name]
                if alias=='Hfull':x=stage['B']
                elif alias=='Tfull':x=np.column_stack((stage['B'],data[stage['anchors'],:,3].ravel()))
                else:
                    g=oldprobe.predict(stage['B']).astype(np.float32)
                    x=np.column_stack((stage['A' if alias=='Eold' else 'B'],g))
                output[stage_name]=np.maximum(model.predict(x),0)
            raw=output['development_evaluation'].reshape(evaluation['mask'].shape)
            global_action=np.maximum(raw+oldoffsets[variant],0)
            if not np.array_equal(raw,archive[variant+'_raw']) or not np.array_equal(global_action,archive[variant]):
                raise ValueError('Old action replay differs: '+variant)
            correction=float(np.quantile(calibration['shortfall'].ravel()[calibration['mask'].ravel()]-output['calibration'][calibration['mask'].ravel()],.9,method='higher'))
            if correction!=oldoffsets[variant]:raise ValueError('Old calibration offset differs')
            predictions[alias]=output;old_replay.append({'variant':variant,'raw_equal':True,'global_equal':True})
    write(args.output/'parent_replay.json',old_replay)
    if args.stage=='preflight':
        write(args.output/'preflight.json',{'rows':int(evaluation['mask'].sum()),'days':len(np.unique(evaluation['anchors']//144)),
            'policy_rows':len(indices),'parent_runtime_exact':True,'old_references_exact':len(old_replay)})
        finish(args,record);return
    # New paired scores use the exact same eligible historical rows.
    state=stages.pop('state_fit')
    old_state_indices=np.load(oldrun/'state_fit_sample_indices.npy')
    target_pitch=np.asarray(data[state['anchors'],:,3],dtype=np.float64).ravel()
    target_s=state['shortfall'].ravel()
    manifest=json.loads((prepared/'data_manifest.json').read_text())
    point_release=manifest['stages']['point_fit'][1]-1+12+1
    issue_rows=np.repeat(state['anchors'],data.shape[1])
    score_indices=matched_score_indices(old_state_indices,state['anchors'],data.shape[1],target_pitch,target_s,point_release,fit['anchors'][0])
    if len(score_indices)==0:raise ValueError('No common mature score-fit rows')
    np.save(args.output/'score_fit_indices.npy',score_indices)
    score_models={}
    for score,target,quantile in [('pitch',target_pitch,False),('shortfall',target_s,True)]:
        model=legacy.learner(settings,args.seed,quantile)
        model.fit(state['B'][score_indices],target[score_indices]);score_models[score]=model
        joblib.dump(model,args.output/('score_'+score+'.joblib'))
    record['score_rows']={'parent':len(old_state_indices),'matched':len(score_indices),
                          'first_issue':int(issue_rows[score_indices].min()),'point_final_label_release':int(point_release)}
    del state,target_pitch,target_s,oldprobe
    design={};contexts={}
    for name,stage in stages.items():
        g=score_models['pitch'].predict(stage['B']).astype(np.float32)
        q=score_models['shortfall'].predict(stage['B']).astype(np.float32)
        design[name],contexts[name]=matrices(stage,data,g,q)
    fitted=[]
    for variant in protocol['new_variants']:
        timer=time.monotonic();model=legacy.learner(settings,args.seed,True)
        model.fit(design['policy_fit'][variant][indices],fit['shortfall'].ravel()[indices])
        joblib.dump(model,args.output/('policy_'+variant+'.joblib'))
        predictions[variant]={name:np.maximum(model.predict(design[name][variant]),0)
                              for name in ['calibration','development_evaluation']}
        fitted.append({'variant':variant,'width':int(model.n_features_in_),'seconds':time.monotonic()-timer})
        print('FIT',args.seed,variant,fitted[-1],flush=True)
    del design,score_models
    context_indices=legacy.subsample(calibration['mask'].ravel(),protocol['calibration']['context_fit_max_rows'],args.seed+200000)
    np.save(args.output/'context_fit_indices.npy',context_indices)
    actions={};offsets={}
    for variant,values in predictions.items():
        raw=values['development_evaluation']
        correction=float(np.quantile(calibration['shortfall'].ravel()[calibration['mask'].ravel()]-values['calibration'][calibration['mask'].ravel()],.9,method='higher'))
        offsets[variant]=correction
        actions[variant+':raw']=raw
        actions[variant+':global']=np.maximum(raw+correction,0)
        if variant in protocol['calibration']['context_variants']:
            timer=time.monotonic();model=context_learner(protocol['calibration']['context_settings'],args.seed)
            residual=calibration['shortfall'].ravel()-values['calibration']
            model.fit(contexts['calibration'][context_indices],residual[context_indices])
            joblib.dump(model,args.output/('context_'+variant+'.joblib'))
            actions[variant+':context']=np.maximum(raw+model.predict(contexts['development_evaluation']),0)
            fitted.append({'variant':variant+':context','width':int(model.n_features_in_),'seconds':time.monotonic()-timer})
    groups=group_masks(data,evaluation['anchors'])
    arrays={};metrics=[]
    counts_reference=None
    for key,action in actions.items():
        calendar,counts,totals=day_accounting(evaluation['shortfall'],action,evaluation['mask'],evaluation['anchors'],groups)
        if counts_reference is None:counts_reference=counts
        else:
            for group in counts:np.testing.assert_array_equal(counts[group],counts_reference[group])
        for suffix,array in totals.items():arrays[key+'|'+suffix]=array
        valid=evaluation['mask'].ravel();s=evaluation['shortfall'].ravel()[valid];r=action[valid]
        for metric,reference in [('R',r.sum()/6),('U',np.maximum(s-r,0).sum()/6),
                                 ('C',(r+10*np.maximum(s-r,0)).sum()/6),('V',float((s>r).sum()))]:
            np.testing.assert_allclose(totals['all|'+metric].sum(),reference,rtol=1e-12,atol=1e-7)
        metrics.append({'seed':args.seed,'policy':key,'N':int(valid.sum()),**{m:float(totals['all|'+m].sum()/valid.sum()) for m in ['C','R','U','V']}})
    np.savez_compressed(args.output/'daily_totals.npz',calendar=calendar,**arrays,
                        **{'N|'+g:c for g,c in counts_reference.items()})
    np.savez_compressed(args.output/'actions.npz',**actions)
    pd.DataFrame(metrics).to_csv(args.output/'metrics.csv',index=False)
    write(args.output/'offsets.json',offsets);write(args.output/'fit_records.json',fitted)
    write(args.output/'accounting.json',{'all_actions_finite':True,'common_population':True,
        'independent_total_checks':len(actions)*4,'new_fits':len(fitted)+2,'days':len(calendar),
        'groups':{g:int(c.sum()) for g,c in counts_reference.items()}})
    if len(fitted)+2!=15:raise ValueError('Unexpected new fit count')
    finish(args,record)


def aggregate(args,protocol):
    record=start(args)
    totals={};counts=None;calendar=None;identities=[];frames=[]
    for seed in protocol['seeds']:
        runpath=args.runs/('seed'+str(seed));manifest=json.loads((runpath/'manifest.json').read_text())
        for name in ['receipt.json','daily_totals.npz','metrics.csv','accounting.json']:
            p=runpath/name
            if sha(p)!=manifest[name]['sha256']:raise ValueError('Worker output differs')
            record['inputs'][str(p)]=sha(p)
        receipt=json.loads((runpath/'receipt.json').read_text())
        if receipt['status']!='COMPLETED_DEVELOPMENT' or receipt['seed']!=seed or receipt['sources'][str(args.protocol)]!=sha(args.protocol):
            raise ValueError('Worker protocol/stage identity differs')
        current_sources={p.name:sha(p) for p in source_paths(args)}
        archived_sources={Path(p).name:d for p,d in receipt['sources'].items()}
        if archived_sources!=current_sources:raise ValueError('Worker source differs from aggregator')
        accounting=json.loads((runpath/'accounting.json').read_text())
        if accounting['new_fits']!=15:raise ValueError('Worker fit count differs')
        expected={v+':'+s for v in list(protocol['old_variants'])+protocol['new_variants'] for s in ['raw','global']}
        expected|={v+':context' for v in protocol['calibration']['context_variants']}
        frame=pd.read_csv(runpath/'metrics.csv')
        if set(frame['policy'])!=expected or len(frame)!=len(expected) or set(frame['seed'])!={seed}:
            raise ValueError('Incomplete or duplicated worker policy grid')
        identities.append(receipt['coordinate_hashes']);frames.append(pd.read_csv(runpath/'metrics.csv'))
        with np.load(runpath/'daily_totals.npz') as a:
            now_counts={k[2:]:a[k] for k in a.files if k.startswith('N|')}
            if counts is None:counts=now_counts;calendar=a['calendar']
            else:
                np.testing.assert_array_equal(calendar,a['calendar'])
                for g in counts:np.testing.assert_array_equal(counts[g],now_counts[g])
            for k in a.files:
                if not k.startswith('N|') and k!='calendar':totals.setdefault(k,[]).append(a[k])
    if any(i!=identities[0] for i in identities):raise ValueError('Worker targets/populations differ')
    stacked={k:np.stack(v) for k,v in totals.items()}
    mean={k:v.mean(axis=0) for k,v in stacked.items()}
    allmetrics=pd.concat(frames,ignore_index=True);allmetrics.to_csv(args.output/'all_fit_metrics.csv',index=False)
    allmetrics.groupby('policy',sort=False)[['C','R','U','V']].mean().to_csv(args.output/'means.csv')
    specs=[]
    def pair(left,right,metric,group='all',label=None,other_group=None):
        terms=[(1,mean[left+'|'+group+'|'+metric],counts[group]),(-1,mean[right+'|'+group+'|'+metric],counts[group])]
        if other_group:
            terms += [(-1,mean[left+'|'+other_group+'|'+metric],counts[other_group]),(1,mean[right+'|'+other_group+'|'+metric],counts[other_group])]
        specs.append({'id':label or f'{left}-minus-{right}|{group}|{metric}',
                      'left':left,'right':right,'metric':metric,'group':group,'other_group':other_group,'terms':terms,
                      'domain':(-2,2) if metric=='V' and other_group else ((-1,1) if metric=='V' else (-np.inf,np.inf))})
    for version in ['raw','global']:
        for left,right in protocol['comparisons']:
            for metric in protocol['inference']['metrics']:pair(left+':'+version,right+':'+version,metric)
    for left,right in protocol['context_comparisons']:
        for metric in protocol['inference']['metrics']:pair(left,right,metric)
    for left,right in protocol['group_pairs']:
        for metric in protocol['inference']['metrics']:
            for group in TRENDS:pair(left+':global',right+':global',metric,group)
            pair(left+':global',right+':global',metric,'down',other_group='flat',label=f'{left}-{right}|down-minus-flat|{metric}')
            for state in STATES:
                for group in ['down','flat']:pair(left+':global',right+':global',metric,state+':'+group)
                pair(left+':global',right+':global',metric,state+':down',other_group=state+':flat',label=f'{left}-{right}|{state}:down-minus-flat|{metric}')
    for policy in allmetrics['policy'].drop_duplicates():
        key=policy+'|all|V'
        for i,seed in enumerate(protocol['seeds']):
            specs.append({'id':f'{policy}|seed{seed}|absolute_V','left':policy,'right':None,'metric':'V','group':'all',
                          'other_group':None,'seed':seed,'terms':[(1,stacked[key][i],counts['all'])],'domain':(0,1)})
    if len({s['id'] for s in specs})!=len(specs):raise ValueError('Duplicate inference coordinate')
    summary=[]
    for span in [protocol['inference']['primary_span']]+protocol['inference']['sensitivity_spans']:
        indices,w=circular_weights(len(calendar),protocol['inference']['n_boot'],span,protocol['inference']['seed'])
        results=[endpoint(s['terms'],w,s['domain']) for s in specs]
        critical=joint_bounds(results,protocol['inference']['alpha'])
        np.savez_compressed(args.output/f'draws_span{span}.npz',indices=indices,weights=w,
             **{s['id']:r['draws'] for s,r in zip(specs,results) if r['draws'] is not None})
        out=[]
        def serial(v):return None if isinstance(v,float) and not np.isfinite(v) else v
        for s,r in zip(specs,results):
            row={k:v for k,v in s.items() if k not in ['terms','domain']}
            row.update({k:serial(r[k]) for k in ['point','lower','upper','status']})
            row.update(span=span,lower_unbounded=not np.isfinite(r['lower']),upper_unbounded=not np.isfinite(r['upper']))
            out.append(row);summary.append(row)
        write(args.output/f'family_span{span}.json',{'family_size':len(specs),'critical':critical,'coordinates':out,
            'coverage':'Dependent-day development approximation, not deployment or finite-sample certification',
            'calendar':calendar.tolist(),'weights_sha256':ahash(w)})
    pd.DataFrame(summary).to_csv(args.output/'all_endpoints.csv',index=False)
    write(args.output/'status.json',{'status':'COMPLETED_HISTORICAL_PILOT','seeds':protocol['seeds'],
        'new_fits':75,'policies':allmetrics['policy'].nunique(),'family_size_per_span':len(specs),
        'independent_confirmation':False,'MLP_replication':False,'old_thresholds_changed':False})
    finish(args,record)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['preflight','run','aggregate'])
    p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int,default=201);p.add_argument('--runs',type=Path);p.add_argument('--threads',type=int,default=2)
    args=p.parse_args();args.protocol=args.protocol.resolve()
    protocol=json.loads(args.protocol.read_text());
    if args.seed not in protocol['seeds']:raise ValueError('Unregistered seed')
    with threadpool_limits(limits=args.threads):
        if args.stage=='aggregate':aggregate(args,protocol)
        else:run(args,protocol)

if __name__=='__main__':main()
