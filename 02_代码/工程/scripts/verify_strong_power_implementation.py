"""Manual-row replay and one identical refit; no new scientific candidates."""
from __future__ import annotations
import argparse,json,os,sys,platform,time
from repo_paths import Path, repository_root
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits

ROOT=Path(repository_root());sys.path.insert(0,str(ROOT))
from scripts.run_dynamic_addback import sha,verify_new,predict
from scripts.run_strong_power_calibration import get_stage
from windfarm_moe.conditional_power_calibration import feature_sets


def six_path(values):
    """Scalar definition, independent of the vectorized production routine."""
    v=np.asarray(values,dtype=np.float64)
    if not np.isfinite(v).all():return [np.nan]*4
    x=np.arange(6,dtype=float)-2.5
    slope=float(np.sum((v-v.mean())*x)/17.5)
    residual=float(np.sqrt(np.mean((v-v.mean()-slope*x)**2)))
    drawdown=max(float(v[i]-v[j]) for j in range(6) for i in range(j+1))
    run=0
    for j in range(5,0,-1):
        if v[j]<v[j-1]:run+=1
        else:break
    return [slope,residual,drawdown,run]


def manual_rows(data,anchors,forecast,indices):
    n_nodes=data.shape[1];base=[];full=[];levels=[];dyn=[];pitch=[];context=[]
    for index in indices:
        j,node=divmod(int(index),n_nodes);t=int(anchors[j])
        f=float(forecast[j,node]);phase=2*np.pi*(t%144)/144
        common=np.asarray([f,np.sin(phase),np.cos(phase),node/max(n_nodes-1,1)],dtype=np.float32)
        wind=np.asarray(data[t-35:t+1,node,0],dtype=np.float32)
        p=np.asarray(data[t-35:t+1,node,1],dtype=np.float32)
        q=np.asarray(data[t-35:t+1,node,2],dtype=np.float32)
        z=np.asarray(data[t-6:t+1,node,3],dtype=np.float64)
        a=np.concatenate((common,wind));b=np.concatenate((a,p,q))
        ps=six_path(p[-6:]);zs=six_path(z[-6:])
        dd=[float(p[-1])-float(p[-2]),float(p[-1])-float(p[-7]),*ps]
        zz=[z[-1],z[-1]-z[-2],z[-1]-z[-7],*zs]
        level=[p[-1],q[-1]]
        base.append(a);full.append(b);levels.append(level);dyn.append(dd);pitch.append(zz)
        context.append([*common,wind[-1],*level,*dd])
    return dict(A=np.asarray(base,dtype=np.float32),FULL=np.asarray(full,dtype=np.float32),
                level=np.asarray(levels,dtype=np.float32),dynamic=np.asarray(dyn,dtype=np.float32),
                pitch=np.asarray(pitch,dtype=np.float32),context=np.asarray(context,dtype=np.float32))


def materialize(rows,g):
    compact=np.column_stack((rows['A'],rows['level'],rows['dynamic']))
    score=np.column_stack((rows['A'],g,rows['level'],rows['dynamic']))
    feature={'COMPACT':compact,'FULL':rows['FULL'],'COMPACT_G':score,
             'COMPACT_Z':np.column_stack((compact,rows['pitch'])),
             'FULL_Z':np.column_stack((rows['FULL'],rows['pitch']))}
    ctx={k:rows['context'] for k in ['COMPACT','FULL']}
    ctx.update(COMPACT_G=np.column_stack((rows['context'],g)),
        COMPACT_Z=np.column_stack((rows['context'],rows['pitch'])),
        FULL_Z=np.column_stack((rows['context'],rows['pitch'])))
    return feature,ctx


def grouped_correction(record,rows,residual=None):
    """Independently rebuild grouping and offsets from calibration observations."""
    p,w,c=rows['level'][:,0],rows['context'][:,4],rows['dynamic'][:,1]
    if residual is None:
        pe=np.asarray(record['p_edges']);we=np.asarray(record['w_edges'])
        offsets={int(k):v for k,v in record['offsets'].items()};fallback=record['global_fallback']
    else:
        pe=np.unique(np.quantile(p[np.isfinite(p)],[.25,.5,.75]))
        we=np.unique(np.quantile(w[np.isfinite(w)],[.25,.5,.75]))
        sorted_y=np.sort(residual);fallback=float(sorted_y[int(np.ceil(.9*(len(sorted_y)-1)))])
        offsets={}
    groups=[]
    for pi,wi,ci in zip(p,w,c):
        if not np.isfinite(pi) or not np.isfinite(wi):groups.append(-1);continue
        category=3 if not np.isfinite(ci) else 0 if ci<-150 else 2 if ci>150 else 1
        groups.append((int(np.searchsorted(pe,pi,side='right'))*(len(we)+1)+int(np.searchsorted(we,wi,side='right')))*4+category)
    groups=np.asarray(groups)
    if residual is not None:
        for k in np.unique(groups):
            use=groups==k;n=int(use.sum())
            if k<0 or n<50:continue
            sorted_y=np.sort(residual[use]);q=float(sorted_y[int(np.ceil(.9*(n-1)))])
            offsets[int(k)]=(n*q+200*fallback)/(n+200)
        np.testing.assert_allclose(pe,record['p_edges'],rtol=0,atol=0)
        np.testing.assert_allclose(we,record['w_edges'],rtol=0,atol=0)
        np.testing.assert_allclose(fallback,record['global_q'],rtol=0,atol=1e-10)
        assert set(offsets)==set(map(int,record['offsets']))
        for k,v in offsets.items():np.testing.assert_allclose(v,record['offsets'][str(k)],rtol=1e-12,atol=1e-9)
    return np.asarray([offsets.get(int(k),fallback) for k in groups])


def run(args):
    if not os.environ.get('PBS_JOBID'):raise ValueError('Allocated node required')
    args.output.mkdir(parents=True,exist_ok=False)
    cfg=json.loads(args.protocol.read_text());prepared=Path(cfg['parent_prepared']);data=np.load(prepared/'physical_channels.npy',mmap_mode='r')
    records=[];start=time.monotonic()
    for seed in cfg['seeds']:
        root=args.runs/f'seed{seed}';receipt=verify_new(root,sha(args.protocol))
        frozen=Path(cfg['addback_runs'])/f'seed{seed}'
        probe=joblib.load(frozen/'probe_pitch.joblib')
        clock=json.loads((frozen/'probe_clock.json').read_text());assert len(clock['removed_issues'])==6
        sample=np.load(root/'policy_indices.npy');cal_sample=np.load(root/'calibration_indices.npy')
        manual={};production={};contexts={};sample_rows={};stages={}
        for phase,(lo,hi) in cfg['stages'].items():
            name='policy_fit' if phase=='fit' else 'development_evaluation' if phase=='evaluate' else 'calibration'
            with np.load(prepared/(name+'_forecast.npz')) as z:
                use=(z['anchors']>=lo)&(z['anchors']<hi);anchors=z['anchors'][use];f=z['forecast'][use]
                np.testing.assert_equal(z['publication_indices'][use],anchors-6)
                np.testing.assert_equal(z['target_indices'][use],anchors+6)
            stage=get_stage(prepared,data,name,lo,hi);stages[phase]=stage
            truth=np.asarray(data[anchors+6,:,1],dtype=np.float64);mask=np.isfinite(truth)
            np.testing.assert_equal(mask,stage['mask'])
            np.testing.assert_allclose(np.maximum(f.astype(float)-truth,0),stage['shortfall'],rtol=0,atol=0,equal_nan=True)
            rng=np.random.default_rng(20261024+seed)
            ix=np.sort(rng.choice(len(anchors)*data.shape[1],1000,replace=False));sample_rows[phase]=ix
            rr=manual_rows(data,anchors,f,ix);g=probe.predict(rr['FULL']).astype(np.float32)
            manual[phase]=materialize(rr,g)
            prod_g=predict(probe,stage['B']).astype(np.float32)
            xx,cc,extra=feature_sets(data,anchors,stage['A'],stage['B'],prod_g)
            production[phase]=xx;contexts[phase]=cc
            for rep in cfg['representations']:
                np.testing.assert_allclose(xx[rep][ix],manual[phase][0][rep],rtol=1e-6,atol=1e-5,equal_nan=True)
                np.testing.assert_allclose(cc[rep][ix],manual[phase][1][rep],rtol=1e-6,atol=1e-5,equal_nan=True)
            if phase in ['fit','calfit']:
                available=np.flatnonzero(mask.reshape(-1));maximum=120000
                expected=np.sort(np.random.default_rng(seed).choice(available,maximum,replace=False)) if len(available)>maximum else available
                np.testing.assert_equal(expected,sample if phase=='fit' else cal_sample)
            manual[phase]+=(rr,)
        release=cfg['task']['label_release'];h=cfg['task']['horizon']
        order=list(cfg['stages'])
        for previous,nxt in zip(order,order[1:]):assert cfg['stages'][previous][1]-1+h+release<cfg['stages'][nxt][0]
        with np.load(root/'actions.npz') as archived:
            for rep in cfg['representations']:
                for name,settings in cfg['models'].items():
                    model=joblib.load(root/f'policy_{rep}_{name}.joblib')
                    reg=model.named_steps['regressor']
                    assert reg.quantile==.9 and reg.loss=='quantile' and not reg.early_stopping
                    for k,v in settings.items():assert reg.get_params()[k]==v
                    conditional=joblib.load(root/f'calibrator_{rep}_{name}.joblib')
                    rreg=conditional.named_steps['regressor'];assert rreg.quantile==.9 and not rreg.early_stopping
                    record=json.loads((root/f'calibration_{rep}_{name}.json').read_text())
                    raw_cal=np.maximum(predict(model,production['calfit'][rep]),0)
                    cm=stages['calfit']['mask'].reshape(-1)
                    residual=stages['calfit']['shortfall'].reshape(-1)[cm]-raw_cal[cm]
                    cal_rows={'level':production['calfit']['COMPACT'][:,-8:-6][cm],
                              'context':contexts['calfit']['COMPACT'][cm],
                              'dynamic':production['calfit']['COMPACT'][:,-6:][cm]}
                    grouped_correction(record,cal_rows,residual)
                    for phase in ['select','evaluate']:
                        x,c,rr=manual[phase];ix=sample_rows[phase]
                        raw=np.maximum(model.predict(x[rep]),0)
                        corr={'GLOBAL':record['global_q'],'GROUP':grouped_correction(record,rr),
                              'CONDITIONAL':conditional.predict(np.column_stack((c[rep],raw)))}
                        for calibration,delta in corr.items():
                            key=f'{rep}__{name}__{calibration}__{phase}'
                            expected=np.maximum(raw+delta,0);actual=archived[key].reshape(-1)[ix]
                            error=float(np.max(np.abs(expected-actual)))
                            np.testing.assert_allclose(expected,actual,rtol=1e-10,atol=1e-8)
                            records.append(dict(seed=seed,key=key,rows=len(ix),max_action_error=error))
                    if seed==201 and rep=='COMPACT' and name=='LARGE':
                        refit=Pipeline([('missing',SimpleImputer(strategy='constant',fill_value=0.,add_indicator=True,keep_empty_features=True)),
                            ('regressor',HistGradientBoostingRegressor(loss='quantile',quantile=.9,early_stopping=False,random_state=seed,**settings))])
                        refit.fit(production['fit'][rep][sample],stages['fit']['shortfall'].reshape(-1)[sample])
                        a=model.predict(manual['evaluate'][0][rep]);b=refit.predict(manual['evaluate'][0][rep])
                        np.testing.assert_allclose(a,b,rtol=0,atol=1e-10)
                        joblib.dump(refit,args.output/'identical_refit_seed201.joblib')
                        records.append(dict(seed=seed,key='IDENTICAL_REFIT_COMPACT_LARGE',rows=len(a),max_action_error=float(np.max(np.abs(a-b)))))
        del stages,production,contexts,manual
        print('REPLAYED',seed,flush=True)
    out=dict(status='MANUAL_FEATURE_ACTION_REPLAY_AND_IDENTICAL_REFIT_MATCHED',records=records,
        seconds=time.monotonic()-start,pbs_job_id=os.environ.get('PBS_JOBID'),host=platform.node(),
        source_sha256=sha(__file__),protocol_sha256=sha(args.protocol),
        scope='Sampled manual feature and action reconstruction; full calibration residual/group recomputation; one identical policy refit; no new candidate or threshold')
    (args.output/'replay.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(out['status'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);p.add_argument('--runs',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    with threadpool_limits(limits=2):run(p.parse_args())
