"""Bounded information add-back pilot on an allocated Metis CPU node."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from repo_paths import Path, repository_root
import platform
import shutil
import sys
import time

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

ROOT=Path(repository_root())
sys.path.insert(0,str(ROOT))
from scripts.run_decision_information_development import load_stage,learner,subsample
from windfarm_moe.dynamic_addback import past_dynamics,matrices,clock_qualified,daily


def sha(path):
    d=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda:stream.read(1024*1024),b''):d.update(part)
    return d.hexdigest()


def save(path,value):
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')


def verify_old(path):
    path=Path(path)
    manifest=json.loads((path/'output_manifest.json').read_text())
    for name,record in manifest.items():
        member=(path/name).resolve()
        if not member.is_relative_to(path.resolve()) or not member.is_file():raise ValueError('Unsafe old member')
        if member.stat().st_size!=record['bytes'] or sha(member)!=record['sha256']:raise ValueError('Old source mismatch: '+str(member))
    rec=json.loads((path/'execution_receipt.json').read_text())
    if rec['status']!='COMPLETED_DEVELOPMENT_NOT_CERTIFIED':raise ValueError('Parent not complete')
    return rec


def begin(args,inputs):
    args.output.mkdir(parents=True,exist_ok=False)
    paths=[Path(__file__),ROOT/'windfarm_moe/dynamic_addback.py',
           ROOT/'scripts/run_decision_information_development.py',ROOT/'windfarm_moe/decision_information.py',args.protocol]
    sources={}
    for p in paths:
        relative=p.resolve().relative_to(ROOT).as_posix()
        target=args.output/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,target);sources[relative]=sha(p)
    rec=dict(status='RUNNING',stage=args.stage,seed=args.seed,argv=sys.argv,
             started_utc=datetime.now(timezone.utc).isoformat(),host=platform.node(),platform=platform.platform(),
             python=sys.version,packages={k:importlib.metadata.version(k) for k in ['numpy','pandas','scikit-learn','joblib']},
             pbs_job_id=os.environ.get('PBS_JOBID'),cpu=platform.processor(),threads=2,
             backend='CPU HGB; no CUDA used',protocol_sha256=sha(args.protocol),source_sha256=sources,
             input_sha256={str(p):sha(p) for p in inputs},
             claim_scope='Exposed-data development; no independent confirmation or physical causality')
    if Path('/proc/cpuinfo').exists():
        rec['cpu']=next((l.split(':',1)[1].strip() for l in Path('/proc/cpuinfo').read_text().splitlines() if l.startswith('model name')),rec['cpu'])
    save(args.output/'receipt.json',rec)
    return rec


def finish(args,rec):
    for p,digest in rec['input_sha256'].items():
        if sha(p)!=digest:raise ValueError('Read-only input changed: '+p)
    rec.update(status='COMPLETED_DEVELOPMENT',finished_utc=datetime.now(timezone.utc).isoformat())
    save(args.output/'receipt.json',rec)
    save(args.output/'manifest.json',{p.relative_to(args.output).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p))
         for p in sorted(args.output.rglob('*')) if p.is_file() and p.name!='manifest.json'})


def verify_new(path,protocol_hash):
    path=Path(path)
    for name,record in json.loads((path/'manifest.json').read_text()).items():
        p=(path/name).resolve()
        if not p.is_relative_to(path.resolve()) or p.stat().st_size!=record['bytes'] or sha(p)!=record['sha256']:
            raise ValueError('New bundle mismatch')
    rec=json.loads((path/'receipt.json').read_text())
    if rec['status']!='COMPLETED_DEVELOPMENT' or rec['protocol_sha256']!=protocol_hash:raise ValueError('Unfinished/new protocol mismatch')
    return rec


def predict(model,x):
    return np.concatenate([model.predict(x[i:i+30000]) for i in range(0,len(x),30000)])


def run(args,cfg):
    if not os.environ.get('PBS_JOBID'):raise ValueError('Research only on allocated PBS node')
    if args.seed not in cfg['seeds']:raise ValueError('Unregistered seed')
    prepared=Path(cfg['parent_prepared']);parent=Path(cfg['parent_runs'])/f'seed{args.seed}'/'pitch_withheld'
    producer=verify_old(prepared);old=verify_old(parent)
    if producer['protocol_sha256']!=cfg['parent_protocol_sha256'] or old['protocol_sha256']!=cfg['parent_protocol_sha256']:
        raise ValueError('Parent protocol identity mismatch')
    for package in ['numpy','pandas','sklearn']:
        current=importlib.metadata.version('scikit-learn' if package=='sklearn' else package)
        if producer[package]!=current:raise ValueError('Original environment mismatch '+package)
    input_files=[prepared/'physical_channels.npy',prepared/'data_manifest.json',prepared/'output_manifest.json',
        parent/'output_manifest.json',parent/'policy_fit_sample_indices.npy',parent/'evaluation_actions.npz',
        *[prepared/f'{s}_forecast.npz' for s in ['state_fit','policy_fit','calibration','development_evaluation']]]
    rec=begin(args,input_files)
    start=time.monotonic();settings=cfg['learner']
    data=np.load(prepared/'physical_channels.npy',mmap_mode='r')
    meta=json.loads((prepared/'data_manifest.json').read_text())
    condition=dict(delay_steps=0,pitch_available=False)
    state=load_stage(prepared,data,'state_fit',condition,36,6)
    qualified=clock_qualified(state['anchors'],meta['stages']['point_fit'][1])
    fitmask=np.repeat(qualified,data.shape[1]) & state['mask'].reshape(-1)
    pitch=data[state['anchors'],:,3].reshape(-1).astype(np.float64)
    fitmask &= np.isfinite(pitch)
    ix=subsample(fitmask,cfg['max_probe_rows'],args.seed)
    np.save(args.output/'probe_indices.npy',ix)
    probes={}
    for name,target,quantile in [('pitch',pitch,False),('risk',state['shortfall'].reshape(-1),True)]:
        model=learner(settings,args.seed,quantile)
        model.fit(state['B'][ix],target[ix]);probes[name]=model
        joblib.dump(model,args.output/f'probe_{name}.joblib')
    save(args.output/'probe_clock.json',dict(removed_issues=state['anchors'][~qualified].tolist(),
        n_qualified_issues=int(qualified.sum()),n_sample_rows=len(ix),sample_sha256=sha(args.output/'probe_indices.npy'),
        point_fit_end=meta['stages']['point_fit'][1],publication_rule='issue-6 strictly later than point final label release'))
    del state,pitch,fitmask
    stages={};features={};extras={}
    for phase in ['policy_fit','calibration','development_evaluation']:
        s=load_stage(prepared,data,phase,condition,36,6)
        extra=past_dynamics(data,s['anchors'])
        g=predict(probes['pitch'],s['B']).astype(np.float32)
        risk=predict(probes['risk'],s['B']).astype(np.float32)
        features[phase]=matrices(s['A'],s['B'],g,risk,extra)
        stages[phase]=s;extras[phase]=extra
    fit,cal,ev=[stages[k] for k in ['policy_fit','calibration','development_evaluation']]
    fit_ix=subsample(fit['mask'].reshape(-1),cfg['max_policy_rows'],args.seed)
    if not np.array_equal(fit_ix,np.load(parent/'policy_fit_sample_indices.npy')):
        raise ValueError('Policy training sample not exactly paired with old source')
    np.save(args.output/'policy_indices.npy',fit_ix)
    np.savez_compressed(args.output/'evaluation_coordinates.npz',anchors=ev['anchors'],forecast=ev['forecast'],
        shortfall=ev['shortfall'],mask=ev['mask'],groups=extras['development_evaluation']['group'],
        level=extras['development_evaluation']['level'],trend=extras['development_evaluation']['trend'],
        path=extras['development_evaluation']['path'],wind=extras['development_evaluation']['wind'],
        pitch=extras['development_evaluation']['pitch'])
    actions={};blocks={};rows=[];models={};offsets={}
    for arm in cfg['arms']:
        timer=time.monotonic();model=learner(settings,args.seed,True)
        model.fit(features['policy_fit'][arm][fit_ix],fit['shortfall'].reshape(-1)[fit_ix])
        joblib.dump(model,args.output/f'policy_{arm}.joblib')
        calraw=np.maximum(predict(model,features['calibration'][arm]),0)
        raw=np.maximum(predict(model,features['development_evaluation'][arm]),0).reshape(ev['mask'].shape)
        valid_cal=cal['mask'].reshape(-1)
        offset=float(np.quantile(cal['shortfall'].reshape(-1)[valid_cal]-calraw[valid_cal],.9,method='higher'))
        offsets[arm]=offset;calibrated=np.maximum(raw+offset,0)
        models[arm]=dict(seconds=time.monotonic()-timer,n_features=int(model.n_features_in_))
        for version,r in [('raw',raw),('global',calibrated)]:
            actions[arm+'__'+version]=r
            out=daily(ev['shortfall'],r,ev['mask'],ev['anchors'],extras['development_evaluation']['group'])
            for key,value in out.items():blocks[arm+'__'+version+'__'+key]=value
            count=out['all__N'].sum()
            rows.append(dict(seed=args.seed,arm=arm,version=version,N=int(count),
                **{k:float(out['all__'+k].sum()/count) for k in ['C','R','U','V']}))
        print('FIT',args.seed,arm,models[arm],flush=True)
        del model,calraw
    # These two arms do not consume probes and should reproduce parent actions.
    with np.load(parent/'evaluation_actions.npz') as z:
        bridge={}
        for arm,oldarm in [('A','A_Wind'),('FULL','B_Consequences')]:
            for newversion,oldversion in [('raw',oldarm+'_raw'),('global',oldarm)]:
                diff=float(np.max(np.abs(actions[arm+'__'+newversion]-z[oldversion])))
                bridge[arm+'__'+newversion]=diff
                if diff>1e-9:raise ValueError('Reproduced reference action mismatch: '+arm+' '+str(diff))
    np.savez_compressed(args.output/'actions.npz',**actions)
    np.savez_compressed(args.output/'daily.npz',**blocks)
    pd.DataFrame(rows).to_csv(args.output/'metrics.csv',index=False)
    save(args.output/'offsets.json',offsets)
    save(args.output/'models.json',models)
    save(args.output/'parent_bridge.json',bridge)
    rec['seconds']=time.monotonic()-start
    finish(args,rec)
    print('COMPLETED RUN',args.seed,rec['seconds'],flush=True)


def interval(point,draws,family_size,alpha=.05):
    if not np.isfinite(point) or not np.isfinite(draws).all():
        return dict(point=float(point) if np.isfinite(point) else None,lower=None,upper=None,status='UNRESOLVED_ZERO_DENOMINATOR_NO_REDRAW')
    if np.all(draws==draws[0]):
        return dict(point=float(point),lower=None,upper=None,status='UNRESOLVED_EMPIRICAL_ZERO_VARIANCE')
    bounds=np.quantile(draws,[alpha/(2*family_size),1-alpha/(2*family_size)])
    return dict(point=float(point),lower=float(bounds[0]),upper=float(bounds[1]),status='APPROXIMATE_DEVELOPMENT_INTERVAL')


def summarize(args,cfg):
    if not os.environ.get('PBS_JOBID'):raise ValueError('Research only on allocated PBS node')
    paths=[args.runs/f'seed{s}' for s in cfg['seeds']]
    for p in paths:verify_new(p,sha(args.protocol))
    rec=begin(args,[p/'daily.npz' for p in paths]+[p/'metrics.csv' for p in paths])
    archives=[]
    for p in paths:
        with np.load(p/'daily.npz') as z:archives.append({k:z[k] for k in z.files})
    rows=pd.concat([pd.read_csv(p/'metrics.csv') for p in paths],ignore_index=True)
    rows.to_csv(args.output/'per_fit.csv',index=False)
    summary=rows.groupby(['arm','version'],sort=False)[['C','R','U','V','N']].mean().reset_index()
    summary.to_csv(args.output/'summary.csv',index=False)
    first=archives[0]
    count=first['A__global__all__N']
    days=first['A__global__days']
    for a in archives:
        for arm in cfg['arms']:
            if not np.array_equal(a[arm+'__global__all__N'],count):raise ValueError('Unpaired population')
            if not np.array_equal(a[arm+'__global__days'],days):raise ValueError('Unpaired weather calendar')
    family_size=len(cfg['contrasts'])*4+len(cfg['conditional_contrasts'])
    records=[]
    for span in [3,1,7]:
        rng=np.random.default_rng(cfg['inference']['seed'])
        n=len(days);starts=rng.integers(0,n,size=(cfg['inference']['n_boot'],(n+span-1)//span))
        indices=((starts[...,None]+np.arange(span))%n).reshape(len(starts),-1)[:,:n]
        denominator=count[indices].sum(axis=1)
        if np.any(denominator<=0):raise ValueError('Empty main population resample')
        for left,right in cfg['contrasts']:
            for metric in ['C','R','U','V']:
                diff=np.mean([a[left+'__global__all__'+metric]-a[right+'__global__all__'+metric] for a in archives],axis=0)
                result=interval(diff.sum()/count.sum(),diff[indices].sum(axis=1)/denominator,family_size)
                records.append(dict(left=left,right=right,metric=metric,span=span,group='all',**result))
        for left,right in cfg['conditional_contrasts']:
            effects=[];points=[]
            for group in ['down','other']:
                nc=first['A__global__'+group+'__N']
                diff=np.mean([a[left+'__global__'+group+'__C']-a[right+'__global__'+group+'__C'] for a in archives],axis=0)
                for a in archives:
                    if not np.array_equal(a[left+'__global__'+group+'__N'],nc):raise ValueError('Group population mismatch')
                dd=nc[indices].sum(axis=1)
                with np.errstate(divide='ignore',invalid='ignore'):
                    effects.append(diff[indices].sum(axis=1)/dd)
                    points.append(diff.sum()/nc.sum())
            result=interval(points[0]-points[1],effects[0]-effects[1],family_size)
            records.append(dict(left=left,right=right,metric='C_interaction',span=span,group='down-minus-other',**result))
        np.savez_compressed(args.output/f'draw_indices_span{span}.npz',indices=indices,days=days)
    pd.DataFrame(records).to_csv(args.output/'paired_intervals.csv',index=False)
    save(args.output/'paired_intervals.json',records)
    save(args.output/'inference.json',dict(family_size=family_size,n_days=len(days),count=int(count.sum()),
        interpretation='conditional on fixed five fits; dependent-day approximation; not confirmation',
        groups={g:dict(N=int(first['A__global__'+g+'__N'].sum()),days=int(np.sum(first['A__global__'+g+'__N']>0))) for g in ['down','other','unknown']}))
    finish(args,rec);print('COMPLETED SUMMARY',flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['run','summarize'],required=True)
    p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--runs',type=Path);p.add_argument('--seed',type=int)
    args=p.parse_args();cfg=json.loads(args.protocol.read_text())
    if cfg['rho']!=10 or cfg['horizon_steps']!=6 or cfg['inference']['primary_span']!=3:raise ValueError('Frozen task changed')
    with threadpool_limits(limits=2):
        if args.stage=='run':run(args,cfg)
        else:summarize(args,cfg)


if __name__=='__main__':main()
