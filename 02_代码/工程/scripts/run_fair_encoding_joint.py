"""Reuse tested training and add matched power encoding with joint qualification."""
from __future__ import annotations
import argparse,json,os,sys,shutil
from repo_paths import Path, repository_root
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

ROOT=Path(repository_root());sys.path.insert(0,str(ROOT))
import scripts.run_strong_power_calibration as engine
from scripts.run_dynamic_addback import sha,save,verify_new,finish
from windfarm_moe.fair_joint import fair_features,historical_eligible,select_joint,assess_increment
from windfarm_moe.risk_frontier import shared_block_draws,simultaneous_envelope

ORIGINAL_BEGIN=engine.begin


def begin(args,inputs):
    cfg=json.loads(args.protocol.read_text())
    inputs=list(inputs)+[Path(cfg['parent_runs'])/f'seed{s}'/'manifest.json' for s in cfg['seeds']]
    rec=ORIGINAL_BEGIN(args,inputs)
    for p in [Path(__file__),ROOT/'windfarm_moe/fair_joint.py']:
        relative=p.relative_to(ROOT).as_posix();target=args.output/'source'/relative
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
        rec['source_sha256'][relative]=sha(p)
    rec['scope']='Exposed-data fair encoding and joint cost/severity/risk development; no confirmation'
    save(args.output/'receipt.json',rec);return rec


def run(args,cfg):
    prior=ROOT/'experiments/strong_power_calibration_20261022/protocol.json'
    if sha(prior)!=cfg['parent_protocol_sha256']:raise ValueError('Changed prior protocol')
    parent=json.loads(prior.read_text())
    for seed in cfg['seeds']:verify_new(Path(cfg['parent_runs'])/f'seed{seed}',cfg['parent_protocol_sha256'])
    adapted=dict(parent)
    adapted.update(representations=cfg['new_representations'],models=cfg['models'],seeds=cfg['seeds'],stages=cfg['stages'])
    # Dependency injection in this new process only; original source/results stay read-only.
    engine.feature_sets=fair_features;engine.begin=begin
    engine.run(args,adapted)


def keys_for(cfg):
    old=['COMPACT','FULL','COMPACT_G','COMPACT_Z','FULL_Z']
    return [f'{r}__{m}__{c}' for r in old+cfg['new_representations'] for m in cfg['models'] for c in cfg['calibrators']]


def mean_draws(archives,keys,phase,cfg,span):
    first=archives[0];n=first[keys[0]+'__'+phase+'__all__N']
    w,h=shared_block_draws(len(n),cfg['inference']['n_boot'],span,cfg['inference']['seed'])
    denominator=w@n
    if np.any(denominator<=0):raise ValueError('Empty full-population weather draw')
    points={};draws={}
    for metric in ['C','R','U','V']:
        value=np.asarray([[a[k+'__'+phase+'__all__'+metric] for k in keys] for a in archives])
        # B,S,K shape; five fits are not independent weather draws.
        points[metric]=value.sum(axis=2)/n.sum()
        draws[metric]=np.einsum('bd,skd->bsk',w,value,optimize=True)/denominator[:,None,None]
    return points,draws,dict(draw_sha256=h,n_days=len(n),N=int(n.sum()))


def envelope(labels,points,draws,exact,span):
    p=np.asarray(points);d=np.asarray(draws).T;exact=np.asarray(exact)
    finite=np.isfinite(p)&np.isfinite(d).all(axis=0)
    bounds=simultaneous_envelope(p[finite],d[:,finite],.05,exact[finite])
    lower=np.full(len(p),np.nan);upper=lower.copy();unknown=np.ones(len(p),bool)
    lower[finite]=bounds['lower'];upper[finite]=bounds['upper'];unknown[finite]=bounds['unknown']
    out=[]
    for i,label in enumerate(labels):
        lo,hi=lower[i],upper[i]
        if label.get('kind')=='absolute_risk' and finite[i]:lo,hi=max(lo,0),min(hi,1)
        out.append(dict(**label,point=float(p[i]) if np.isfinite(p[i]) else None,
            lower=float(lo) if np.isfinite(lo) else None,upper=float(hi) if np.isfinite(hi) else None,
            unknown=bool(unknown[i]),span=span))
    return out,dict(critical=bounds['critical'],slots=len(labels),finite_slots=int(finite.sum()))


def historical(archives,keys,cfg):
    p,d,meta=mean_draws(archives,keys,'select',cfg,3)
    ref=keys.index(cfg['reference']['key']);cstar=cfg['reference']['Cstar']
    np.testing.assert_allclose(p['C'][:,ref].mean(),cstar,rtol=0,atol=1e-10)
    labels=[];points=[];draws=[];exact=[]
    for j,key in enumerate(keys):
        cp=p['C'][:,j].mean();cr=p['C'][:,ref].mean()
        dc=d['C'][:,:,j].mean(axis=1);dr=d['C'][:,:,ref].mean(axis=1)
        labels.append(dict(left=key,right=keys[ref],metric='D',seed=None,kind='historical_joint'))
        points.append((cp-cr)/cr)
        draws.append(np.where(dr>0,(dc-dr)/dr,np.nan));exact.append(j==ref)
        for s,seed in enumerate(cfg['seeds']):
            labels.append(dict(left=key,right=keys[ref],metric='H',seed=seed,kind='historical_joint'))
            points.append(10*(p['U'][s,j]-p['U'][s,ref])/cstar)
            draws.append(10*(d['U'][:,s,j]-d['U'][:,s,ref])/cstar);exact.append(j==ref)
        for s,seed in enumerate(cfg['seeds']):
            labels.append(dict(left=key,right='',metric='V',seed=seed,kind='absolute_risk'))
            points.append(p['V'][s,j]);draws.append(d['V'][:,s,j]);exact.append(False)
    result,info=envelope(labels,points,draws,exact,3)
    assert len(result)==528
    return result,info|meta


def comparisons(cfg,choices):
    rows=[]
    for a,b in [('COMPACT_G','COMPACT'),('FULL_DYN_G','FULL_DYN'),('COMPACT_Z','COMPACT'),('FULL_DYN_Z','FULL_DYN')]:
        for model in cfg['models']:
            for cal in cfg['calibrators']:rows.append((f'{a}__{model}__{cal}',f'{b}__{model}__{cal}','matched'))
    for a,b in [('FULL_DYN','FULL'),('FULL_DYN_Z','FULL_Z')]:
        for model in cfg['models']:
            for cal in cfg['calibrators']:rows.append((f'{a}__{model}__{cal}',f'{b}__{model}__{cal}','encoding'))
    rows += [(choices['SCORE'],choices['POWER'],'selected_score'),(choices['PITCH'],choices['POWER'],'selected_pitch')]
    assert len(rows)==38
    return rows


def evaluation(archives,keys,cfg,choices,span):
    p,d,meta=mean_draws(archives,keys,'evaluate',cfg,span)
    labels=[];points=[];draws=[];exact=[];cstar=cfg['reference']['Cstar'];nb=cfg['inference']['n_boot']
    for left,right,kind in comparisons(cfg,choices):
        unavailable=left is None or right is None
        a,b=(keys.index(left),keys.index(right)) if not unavailable else (0,0)
        for metric in ['D','C','R','U','V']:
            labels.append(dict(left=left,right=right,kind=kind,metric=metric,seed=None))
            if unavailable:points.append(np.nan);draws.append(np.full(nb,np.nan));exact.append(False);continue
            if metric=='D':
                pc=p['C'][:,a].mean();pr=p['C'][:,b].mean();dc=d['C'][:,:,a].mean(axis=1);dr=d['C'][:,:,b].mean(axis=1)
                points.append((pc-pr)/pr);draws.append(np.where(dr>0,(dc-dr)/dr,np.nan))
            else:
                points.append((p[metric][:,a]-p[metric][:,b]).mean())
                draws.append((d[metric][:,:,a]-d[metric][:,:,b]).mean(axis=1))
            exact.append(a==b)
        for s,seed in enumerate(cfg['seeds']):
            labels.append(dict(left=left,right=right,kind=kind,metric='H',seed=seed))
            points.append(10*(p['U'][s,a]-p['U'][s,b])/cstar if not unavailable else np.nan)
            draws.append(10*(d['U'][:,s,a]-d['U'][:,s,b])/cstar if not unavailable else np.full(nb,np.nan))
            exact.append(a==b and not unavailable)
    for j,key in enumerate(keys):
        for s,seed in enumerate(cfg['seeds']):
            labels.append(dict(left=key,right='',metric='V',seed=seed,kind='absolute_risk'))
            points.append(p['V'][s,j]);draws.append(d['V'][:,s,j]);exact.append(False)
    result,info=envelope(labels,points,draws,exact,span)
    assert len(result)==620
    return result,info|meta


def summarize(args,cfg):
    inputs=[];archives=[];tables=[]
    for seed in cfg['seeds']:
        old=Path(cfg['parent_runs'])/f'seed{seed}';new=args.runs/f'seed{seed}'
        verify_new(old,cfg['parent_protocol_sha256']);verify_new(new,sha(args.protocol))
        merged={}
        for root in [old,new]:
            inputs += [root/'daily.npz',root/'metrics.csv']
            with np.load(root/'daily.npz') as z:
                for k in z.files:
                    if k in merged:raise ValueError('Duplicated program')
                    merged[k]=z[k]
            tables.append(pd.read_csv(root/'metrics.csv'))
        archives.append(merged)
    rec=begin(args,inputs);keys=keys_for(cfg);assert len(keys)==48
    for phase in ['select','evaluate']:
        n=archives[0][keys[0]+'__'+phase+'__all__N']
        for archive in archives:
            for key in keys:np.testing.assert_array_equal(archive[key+'__'+phase+'__all__N'],n)
    frame=pd.concat(tables,ignore_index=True);frame.to_csv(args.output/'per_fit.csv',index=False)
    means=frame.groupby(['key','phase'],sort=False)[['C','R','U','V','N']].mean().reset_index()
    means.to_csv(args.output/'means.csv',index=False)
    hist,hinfo=historical(archives,keys,cfg);save(args.output/'historical_endpoints.json',hist)
    eligible={k:historical_eligible(hist,k,cfg['thresholds']) for k in keys}
    cost={r.key:r.C for r in means[means.phase=='select'].itertuples()}
    ref=cfg['reference']['key'];choices=dict(POWER=None,SCORE=None,PITCH=None)
    if eligible[ref]:
        power=[k for k in keys if k.split('__')[0] in ['COMPACT','FULL_DYN']]+[ref]
        choices['POWER']=select_joint(cost,power,eligible)
        for role,reps in [('SCORE',['COMPACT_G','FULL_DYN_G']),('PITCH',['COMPACT_Z','FULL_DYN_Z'])]:
            candidates=([choices['POWER']] if choices['POWER'] is not None else [])+[k for k in keys if k.split('__')[0] in reps]
            choices[role]=select_joint(cost,candidates,eligible)
    save(args.output/'choices.json',dict(choices=choices,eligible=eligible,uses_evaluation_selection=False,
        reference_qualified=eligible[ref],thresholds=cfg['thresholds'],Cstar=cfg['reference']['Cstar']))
    results=[];metadata=dict(historical=hinfo);verdicts={}
    for span in [3,1,7]:
        out,info=evaluation(archives,keys,cfg,choices,span);results.extend(out);metadata[str(span)]=info
        for role,kind in [('SCORE','selected_score'),('PITCH','selected_pitch')]:
            power=choices['POWER'];candidate=choices[role]
            pair=[r for r in out if r['kind']==kind]
            rp=[r for r in out if r['kind']=='absolute_risk' and r['left']==power]
            rz=[r for r in out if r['kind']=='absolute_risk' and r['left']==candidate]
            verdicts[role+f'_span{span}']=assess_increment(pair,rp,rz,
                candidate is not None and candidate==power,cfg['thresholds'])
    save(args.output/'intervals.json',results);pd.DataFrame(results).to_csv(args.output/'intervals.csv',index=False)
    save(args.output/'inference.json',metadata);save(args.output/'verdicts.json',verdicts)
    finish(args,rec);print('COMPLETED JOINT',choices,verdicts,flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['run','summarize'],required=True)
    p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int);p.add_argument('--runs',type=Path)
    args=p.parse_args();cfg=json.loads(args.protocol.read_text())
    if not os.environ.get('PBS_JOBID'):raise ValueError('Use allocated CPU node')
    if cfg['thresholds']!=dict(important_gain=.01,cost_noninferiority=.01,risk_cap=.1,signed_U_cap=.001,rho=10,alpha=.05):
        raise ValueError('Original thresholds changed')
    with threadpool_limits(limits=2):
        if args.stage=='run':run(args,cfg)
        else:summarize(args,cfg)


if __name__=='__main__':main()
