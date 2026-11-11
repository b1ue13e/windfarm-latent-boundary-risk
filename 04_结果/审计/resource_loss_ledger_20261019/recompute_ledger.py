"""Read-only resource/loss accounting from existing code, blocks and receipts."""
from pathlib import Path
import ast
import collections
import csv
import datetime as dt
import hashlib
import json
import platform
import re
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
BASE=ROOT/'analyses/independent_confirmation_execution_20261019/recovered/results'
READS={}

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def track(path):
    READS[path.relative_to(ROOT).as_posix()]=sha(path)
    return path

def read(path):return json.loads(track(path).read_text(encoding='utf-8-sig'))

def save_csv(name,rows):
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)

def duration(r):
    return (dt.datetime.fromisoformat(r['finished_utc'])-dt.datetime.fromisoformat(r['started_utc'])).total_seconds()

def search_materials():
    roots=['src','windfarm_moe','scripts','docs','manuscript','experiments',
           '00_Planning','01_Literature','02_Theory','03_Implementation','04_Experiments','05_Manuscript','06_Review']
    # Exclude archived worker outputs and giant binary/cache files from the demand search.
    patterns={
      'business_need':r'客户合同|接口合同|服务等级|访谈纪要|用户验收|带宽预算|计费|收费|signed contract|service.level agreement|\bSLA\b|billing|customer requirement',
      'service_implementation':r'\bFastAPI\b|\bFlask\b|\bMQTT\b|\bKafka\b|\bgRPC\b|production endpoint|service endpoint|IEC.?104|104.{0,8}规约|OPC.?UA',
      'bounded_scope':r'no real arrival|no observed field|synthetic.*clock|not.*settlement|not settlement|not.*cashflow'}
    found=[];files=set();errors=[]
    for folder in roots:
        for p in sorted((ROOT/folder).rglob('*')):
            if not p.is_file() or p.suffix.lower() not in {'.md','.py','.toml','.yaml','.yml','.ini'}:continue
            if p.stat().st_size>2*1024*1024 or any(x in p.parts for x in ('__pycache__','remote_j02','checkpoints')):continue
            if p.is_symlink():continue
            files.add(p.relative_to(ROOT).as_posix())
            try:text=track(p).read_text(encoding='utf-8-sig')
            except UnicodeError as e:
                errors.append(dict(path=p.relative_to(ROOT).as_posix(),error=str(e)));continue
            for number,line in enumerate(text.splitlines(),1):
                for category,pattern in patterns.items():
                    if re.search(pattern,line,re.IGNORECASE):
                        found.append(dict(path=p.relative_to(ROOT).as_posix(),line=number,category=category,text=line[:1600],
                            review_status='CANDIDATE_NOT_AUTOMATIC_PRODUCTION_EVIDENCE'))
    save_csv('demand_search_hits.csv',found or [dict(path='NONE',line=0,category='NONE',text='No hit',review_status='NOT_FOUND')])
    summary=dict(files_scanned=len(files),roots=roots,patterns=patterns,hits=len(found),errors=errors,
        exclusion='Text/code <=2MiB; no env/Git/raw measurements; archived duplicates not exhaustive; no cloud/private business systems or contact outreach',
        inference='Missing documentary evidence in this bounded search is not proof that no interface need exists anywhere.')
    (OUT/'demand_search_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    return summary

def main():
    started=time.monotonic()
    scope=read(OUT/'scope_and_inputs.json')
    for name,value in scope['inputs_sha256'].items():assert sha(ROOT/name)==value,name
    cfg=read(ROOT/'experiments/independent_confirmation_execution_20261019/protocol.json')
    primary=read(BASE/'aggregate/primary.json')
    prepared_manifest=read(BASE/'prepared/manifest.json')
    assert primary['labels']==['P1/HGB/q0.95','WPQ36/HGB/q0.95']
    choices=read(BASE/'chosen/choices.json')
    group=next(g for g in choices['groups'] if g['condition']=='pitch_withheld')
    original=group['sets']['0.02']['original_indices']
    assert [group['labels'][i] for i in original]==['P1/HGB/q0.95']
    with np.load(track(BASE/'unlocked/confirmation.npz'),allow_pickle=False) as arrays:
        forecast_shape=list(arrays['forecast'].shape)
    rows=[]
    for p in sorted((BASE/'evaluate').iterdir(),key=lambda p:int(p.name)):
        if not p.is_dir():continue
        # The task table is frozen; inspect metadata to identify the two fixed policies.
        meta_path=p/'metadata.json'
        meta=json.loads(meta_path.read_text(encoding='utf-8'))
        t=meta['task']
        if t['condition']!='pitch_withheld' or t['estimator']!='HGB' or t['subset'] not in ('P1','WPQ36'):continue
        track(meta_path)
        hist=p.parent.parent/'historical'/p.name
        hm=read(hist/'metadata.json');hr=read(hist/'receipt.json');er=read(p/'receipt.json');manifest=read(hist/'manifest.json')
        arrays_path=track(p/'blocks.npz');qi=cfg['offset_quantiles'].index(.95)
        with np.load(arrays_path,allow_pickle=False) as a:
            totals={k:float(a[f'{qi}__{k}'].sum()) for k in ('count','loss_sum','reserve_sum','shortage_sum','violation_sum')}
        n=totals['count'];assert n==1059248
        assert abs(totals['loss_sum']-totals['reserve_sum']-10*totals['shortage_sum'])<1e-6
        rows.append(dict(seed=t['seed'],policy=t['subset'],q=.95,worker=int(p.name),count=n,
            cost_total=totals['loss_sum'],cost_mean=totals['loss_sum']/n,reserve_mean=totals['reserve_sum']/n,
            shortage_mean=totals['shortage_sum']/n,violation_rate=totals['violation_sum']/n,
            fit_seconds=hm['fit_seconds'],historical_stage_seconds=duration(hr),evaluation_stage_seconds=duration(er),
            recorded_model_bytes=manifest['model.joblib']['bytes'],model_locally_present=(hist/'model.joblib').exists(),
            host=hr['host'],source=arrays_path.relative_to(ROOT).as_posix()))
    assert len(rows)==10
    save_csv('policy_seed_ledger.csv',rows)
    summary={}
    for policy in ('P1','WPQ36'):
        rr=[r for r in rows if r['policy']==policy]
        assert {r['seed'] for r in rr}==set(cfg['seeds'])
        summary[policy]={k:float(np.mean([r[k] for r in rr])) for k in ('cost_total','cost_mean','reserve_mean','shortage_mean',
            'violation_rate','fit_seconds','historical_stage_seconds','evaluation_stage_seconds','recorded_model_bytes')}
        summary[policy]['manifest_model_bytes_minmax']=[min(r['recorded_model_bytes'] for r in rr),max(r['recorded_model_bytes'] for r in rr)]
    p,f=summary['P1'],summary['WPQ36']
    delta={k:p[k]-f[k] for k in p if isinstance(p[k],float)}
    delta['relative_cost']=p['cost_mean']/f['cost_mean']-1
    assert abs(p['cost_mean']-primary['bounds']['groups'][0]['mean_cost'][0])<1e-12
    assert abs(delta['relative_cost']-primary['bounds']['groups'][0]['relative_ratio_point'][0][1])<1e-12
    assert abs(delta['cost_mean']-delta['reserve_mean']-10*delta['shortage_mean'])<1e-12
    resources=dict(common_point_feature_values=72,p1_raw_columns=5,full_raw_columns=112,
        common_materialized_columns=148,forecast_shape=forecast_shape,
        full_X_bytes=int(np.prod(forecast_shape)*148*4),
        initial_training_index_copy_bytes=cfg['reserve_rows']*148*4,
        learner_training_slice_bytes=dict(P1=cfg['reserve_rows']*5*4,WPQ36=cfg['reserve_rows']*112*4),
        learner_evaluation_slice_bytes=dict(P1=int(np.prod(forecast_shape)*5*4),WPQ36=int(np.prod(forecast_shape)*112*4)),
        theoretical_raw_value_bytes_per_row=dict(P1=20,WPQ36=448),
        underlying_time_history='P1 only chooses latest reserve P; upstream W/P36 retained; no physical sensor removal shown',
        serialized_model_size_scope='bytes recorded in archived manifest; model.joblib absent locally, no independent model read or RSS measurement')
    shared_bytes=prepared_manifest['point_forecaster.joblib']['bytes']
    resources['shared_point_model_manifest_bytes']=shared_bytes
    resources['recorded_point_plus_policy_model_bytes']={name:shared_bytes+summary[name]['recorded_model_bytes'] for name in ('P1','WPQ36')}
    resources['hypothetical_cached_stream_scalar_counts']={'P1':1,'WPQ36':3,
        'scope':'Illustrative steady-state local-lag-cache interface, not an implemented or measured network; 36 lags need not be retransmitted every issue.'}
    search=search_materials()
    before=dict(READS)
    for name,value in before.items():assert sha(ROOT/name)==value,name
    result=dict(policies=summary,deltas_p1_minus_reference=delta,resources=resources,
        seeds=cfg['seeds'],q=.95,primary_interval=primary['bounds']['groups'][0]['relative_ratio_lower'][0][1:2]+
            primary['bounds']['groups'][0]['relative_ratio_upper'][0][1:2],
        no_monetary_conversion=True,demand_search_files=search['files_scanned'])
    (OUT/'derived.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    receipt=dict(utc=dt.datetime.now(dt.timezone.utc).isoformat(),argv=sys.argv,python=sys.version,numpy=np.__version__,
        platform=platform.platform(),host=platform.node(),script_sha256=sha(Path(__file__)),seconds=time.monotonic()-started,
        sources_sha256_before=before,sources_sha256_after={name:sha(ROOT/name) for name in before},all_inputs_unchanged=True,
        no_training=True,no_inference=True,no_calibration=True,no_resampling=True,no_remote=True,random_seed='NA: deterministic archived-artifact accounting only',
        scientific_instances=cfg['seeds'],scope='Archived point accounting, shape arithmetic and recorded wall times; not a controlled benchmark or deployment measurement')
    (OUT/'recompute_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
