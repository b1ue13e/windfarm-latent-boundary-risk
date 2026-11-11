"""Independent arithmetic and original-function replay; never fits or selects policies."""
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import joblib
import numpy as np
from threadpoolctl import threadpool_limits


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def daily(actions, shortfall, mask, anchors):
    days=np.unique(anchors//144)
    x=shortfall[mask]; r=actions[mask]; day=np.repeat(anchors//144,mask.shape[1])[mask.ravel()]
    grids=(np.ones(len(x)),r/6+10*np.maximum(x-r,0)/6,r/6,np.maximum(x-r,0)/6,(x>r).astype(float))
    vals=np.stack([np.bincount(day,weights=g,minlength=int(days[-1])+1)[days] for g in grids],axis=-1)
    return days,vals


def main():
    if not os.environ.get('PBS_JOBID'):raise ValueError('Requires allocated audit node')
    base=Path(__file__).resolve().parent;cfg=json.loads((base/'protocol.json').read_text())
    legacy=Path(cfg['legacy_root'])
    for rel,h in cfg['source_sha256'].items():
        assert sha(legacy/rel)==h
    for name,info in cfg['verified_inputs'].items():
        assert sha(name)==info['sha256']
    for path in (legacy,legacy/'scripts',legacy/'experiments/independent_confirmation_20261019'):
        sys.path.insert(0,str(path))
    old=importlib.import_module('run_independent_confirmation')
    assert Path(old.__file__).resolve().is_relative_to(legacy.resolve())
    result=base/'results'; dest=base/'independent_audit.json'
    if dest.exists():raise FileExistsError('Audit receipt immutable')
    rec=dict(started_utc=datetime.now(timezone.utc).isoformat(),pbs_job=os.environ['PBS_JOBID'],status='RUNNING',
             new_fits=0,new_policy_selection=False,audit_source_sha256=sha(__file__),checked_tasks=[],
             python=sys.version,numpy=np.__version__)
    try:
        inputs={}; maximum=0; population=None; points=[]
        original_freeze=json.loads((result/'chosen/freeze.json').read_text())
        unlock_receipt=json.loads((result/'unlocked/receipt.json').read_text())
        for table in ('tblSCTurbine','tblSCTurGrid'):
            if unlock_receipt['boundary'][table]['seen']!=21:
                raise ValueError('Incomplete original raw boundary; confirmation invalid: '+table)
        for stage in ('unlocked','aggregate'):
            receipt=json.loads((result/stage/'receipt.json').read_text())
            assert receipt['status']=='COMPLETE'
            assert receipt['adapter_sha256']==original_freeze['adapter_sha256']
            assert receipt['protocol_sha256']==original_freeze['protocol_sha256']
        assert sha(base/'adapter.py')==original_freeze['adapter_sha256']
        assert sha(base/'protocol.json')==original_freeze['protocol_sha256']
        merged=np.load(result/'unlocked/physical_channels.npy',mmap_mode='r')
        with np.load(result/'unlocked/confirmation.npz') as a:
            anchors=a['anchors'];forecast=a['forecast']
        expected=old.anchor_window(cfg['window']['start'],cfg['window']['end'],6)
        np.testing.assert_array_equal(expected,anchors)
        assert merged.shape==(1216*144+1,21,4)
        # Fixed sample indexes, independent of values or scientific outcomes.
        sample=np.unique(np.r_[0,np.arange(0,len(anchors),137),len(anchors)-1]).astype(int)
        point_model=joblib.load(legacy/'results/prepared/point_forecaster.joblib')
        original_fc=old.forecast_at(point_model,merged,anchors[sample])
        np.testing.assert_array_equal(forecast[sample],original_fc)
        for item in cfg['selected_tasks']:
            k=item['task_index'];p=result/'evaluate'/str(k)
            manifest=json.loads((p/'manifest.json').read_text())
            inputs[str(p/'manifest.json')]=sha(p/'manifest.json')
            for name,info in manifest.items():
                assert sha(p/name)==info['sha256']
            metadata=json.loads((p/'metadata.json').read_text())
            assert metadata['task']==item['task'] and metadata['refit'] is False
            receipt=json.loads((p/'receipt.json').read_text())
            assert receipt['adapter_sha256']==original_freeze['adapter_sha256']
            with np.load(p/'raw_actions.npz') as a:
                raw,off,s,mask,aa=(a[n] for n in ('raw','offsets','shortfall','mask','anchors'))
            np.testing.assert_array_equal(aa,anchors)
            np.testing.assert_array_equal(off,np.load(legacy/f'results/historical/{k}/offsets.npy'))
            valid=np.isfinite(merged[anchors+6,:,1])
            target=np.where(valid,np.maximum(forecast.astype(float)-merged[anchors+6,:,1],0),np.nan)
            np.testing.assert_array_equal(valid,mask);np.testing.assert_array_equal(target,s)
            identity=tuple(hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest() for x in (s,mask,aa))
            if population is None:population=identity
            assert population==identity
            assert raw.shape==s.shape and np.isfinite(raw).all()
            action=np.maximum(raw+off[2],0)
            days,v=daily(action,s,mask,aa)
            with np.load(p/'blocks.npz') as b:
                np.testing.assert_array_equal(days,b['2__block_ids'])
                for j,name in enumerate(('count','loss_sum','reserve_sum','shortage_sum','violation_sum')):
                    err=float(np.max(np.abs(v[:,j]-b['2__'+name])))
                    maximum=max(maximum,err)
                    if name in ('count','violation_sum'):np.testing.assert_array_equal(v[:,j],b['2__'+name])
                    else:np.testing.assert_allclose(v[:,j],b['2__'+name],rtol=0,atol=1e-7)
            model=joblib.load(legacy/f'results/historical/{k}/model.joblib')
            stage=dict(X=old.features(merged,anchors[sample],forecast[sample],0),
                       forecast=forecast[sample],mask=mask[sample])
            original_raw=old.predict(model,stage,item['task'],dict(delay_steps=0,pitch_available=False))
            np.testing.assert_array_equal(raw[sample],original_raw)
            means=v[:,1:].sum(0)/v[:,0].sum()
            points.append(dict(task_index=k,task=item['task'],C=means[0],R=means[1],U=means[2],V=means[3]))
            rec['checked_tasks'].append(k)
        primary=json.loads((result/'aggregate/primary.json').read_text())
        assert primary['labels']==['P1/HGB/q0.95','WPQ36/HGB/q0.95']
        assert primary['primary_coordinate_family']==14
        means={subset:np.array([[p[m] for m in ('C','R','U','V')] for p in points if p['task']['subset']==subset]).mean(0)
               for subset in ('P1','WPQ36')}
        np.testing.assert_allclose(primary['mean_cost'],[means['P1'][0],means['WPQ36'][0]],atol=1e-10,rtol=0)
        ratio=means['P1'][0]/means['WPQ36'][0]-1
        assert abs(ratio-primary['relative_ratio_point'][0][1])<1e-12
        env=primary['bounds']['groups'][0]
        status=all(np.asarray(env['risk_upper']).ravel()<=.1) and env['relative_ratio_upper'][0][1]<=.02
        assert status==(primary['verdict']['status']=='ALL_FROZEN_CANDIDATES_CONFIRMED')
        # Deterministic original-code replay for the post-evaluate identity gap.
        # Reuses exactly the frozen random stream, not additional draws for inference.
        inference=importlib.import_module('windfarm_moe.subset_inference')
        assert Path(inference.__file__).resolve()==(legacy/'windfarm_moe/subset_inference.py').resolve()
        assert sha(inference.__file__)==cfg['source_sha256']['windfarm_moe/subset_inference.py']
        c=[];v=[]
        for seed in cfg['seeds']:
            cs=[];vs=[]
            for subset in ('P1','WPQ36'):
                item=next(t for t in cfg['selected_tasks'] if t['task']['seed']==seed and t['task']['subset']==subset)
                with np.load(result/'evaluate'/str(item['task_index'])/'blocks.npz') as b:
                    cs.append(b['2__loss_sum']);vs.append(b['2__violation_sum']);cnt=b['2__count']
            c.append(cs);v.append(vs)
        g=dict(costs=np.array(c),violations=np.array(v),counts=cnt,exact_pair=np.eye(2,dtype=bool))
        replay={}
        sensitivity=json.loads((result/'aggregate/sensitivity.json').read_text())
        for span in (3,1,7):
            out=inference.streamed_envelopes([g],cfg['n_boot'],span,cfg['bootstrap_seed'],cfg['alpha'])
            env2=out['groups'][0]
            if span==3:
                assert out['draw_sha256']==primary['bounds']['draw_sha256']
                for name in ('mean_cost','risk_point','risk_upper','risk_lower','relative_ratio_point','relative_ratio_lower','relative_ratio_upper'):
                    np.testing.assert_allclose(env2[name],primary['bounds']['groups'][0][name],atol=1e-12,rtol=0)
            else:
                s0=sensitivity[f'span_{span}']
                for n,actual in (('candidate_max_risk_upper',np.max(env2['risk_upper'][:,0])),
                                 ('reference_max_risk_upper',np.max(env2['risk_upper'][:,1])),
                                 ('relative_cost_ratio_upper',env2['relative_ratio_upper'][0,1])):
                    assert abs(s0[n]-actual)<1e-12
            replay[str(span)]=dict(draw_sha256=out['draw_sha256'],critical=out['critical'],
                                  coordinate_family_size=out['coordinate_family_size'])
        freeze=json.loads((result/'chosen/freeze.json').read_text());event=json.loads((result/'UNLOCK_EVENT.json').read_text())
        assert event['freeze_sha256']==sha(result/'chosen/freeze.json')
        assert datetime.fromisoformat(freeze['created_utc'])<datetime.fromisoformat(event['utc'])
        for name,info in cfg['verified_inputs'].items():assert sha(name)==info['sha256']
        for p,h in inputs.items():assert sha(p)==h
        rec.update(status='PASS_INDEPENDENT_ACTION_AND_SOURCE_REPLAY',points=points,means={k:v.tolist() for k,v in means.items()},
                   relative_cost_point=ratio,maximum_daily_arithmetic_error=maximum,
                   exact_original_predictor_sample_issues=len(sample),original_predictor_sample_node_cells=len(sample)*21,
                   raw_six_field_boundary_seen_both_tables=21,source_runtime_module=str(inference.__file__),
                   original_statistics_replay=replay,
                   full_target_mask_exact=True,all_input_population_identical=True,
                   original_inputs_unchanged=True,inputs_sha256=inputs,primary_label_recomputed=primary['verdict']['status'],
                   scope='Identity, causal coordinates, deterministic original predictor sample, all-node daily arithmetic and decision consistency; not new CI coverage certification')
    except BaseException as e:
        rec.update(status='FAILED_PRESERVED',error=repr(e));raise
    finally:
        rec['finished_utc']=datetime.now(timezone.utc).isoformat()
        with dest.open('x') as f:json.dump(rec,f,indent=2)
        print(json.dumps(rec),flush=True)


if __name__=='__main__':
    with threadpool_limits(limits=2):main()
