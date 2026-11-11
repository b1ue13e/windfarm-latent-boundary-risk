"""Read-only reaggregation of archived evidence; no fitting or resampling."""
from pathlib import Path
import csv
import json
from collections import defaultdict, Counter
from statistics import mean, stdev
import hashlib
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
reads = []

def load_csv(name):
    p = ROOT / name
    with p.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    reads.append({'path':name, 'rows':len(rows), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    return rows

def load_json(name):
    p = ROOT / name
    reads.append({'path':name, 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    return json.loads(p.read_text(encoding='utf-8-sig'))

facts = {}
e02 = load_csv('artifacts/exp02-zero-privileged-supervision/v1/zero_privileged_supervision_benchmark.csv')
groups = defaultdict(list)
for row in e02:
    groups[(row['horizon'], row['model'])].append(row)
facts['e02'] = []
for (horizon, model), rr in groups.items():
    facts['e02'].append({'horizon':horizon,'model':model,'n_seeds':len(rr),
        'psrei_mean':mean(float(r['full_psrei_kwh']) for r in rr),
        'paired_delta_means_average':mean(float(r['full_delta_psrei_mean']) for r in rr),
        'negative_delta_seeds':sum(float(r['full_delta_psrei_mean'])<0 for r in rr),
        'violation_pct':mean(float(r['full_violation_rate_pct']) for r in rr),
        'all_5_seed_interval_directions':[[r['seed'],float(r['full_delta_psrei_ci95_low']),float(r['full_delta_psrei_ci95_high'])] for r in rr]})

external = load_csv('artifacts/exp01_pitchmasked_v4/exp01_pitchmasked_v3_seed_results.csv')
groups=defaultdict(list)
for row in external: groups[(row['farm_id'],row['horizon'])].append(row)
facts['e01']=[{'farm':k[0],'horizon':k[1],'seeds':len(rr),
    'delta_mean':mean(float(r['delta_psrei_kwh']) for r in rr),
    'negative_seeds':sum(float(r['delta_psrei_kwh'])<0 for r in rr)} for k,rr in groups.items()]
facts['e01_archived_intervals']=load_csv('artifacts/exp01_pitchmasked_v4/exp01_pitchmasked_v3_joint_statistics.csv')

rows=load_csv('artifacts/strictmask_ablation_routing_controls_gate/_aggregated_suite_runs/wtb_test_aggregated_runs.csv')
groups=defaultdict(list)
for row in rows: groups[row['variant_key']].append(row)
facts['old_ablation']=[{'variant':k,'n':len(rr),'rmse_mean':mean(float(r['overall_rmse']) for r in rr),
    'nmi_mean':mean(float(r['nmi']) for r in rr if r['nmi']) if any(r['nmi'] for r in rr) else None,
    'ari_mean':mean(float(r['ari']) for r in rr if r['ari']) if any(r['ari'] for r in rr) else None,
    'train_seconds_mean':mean(float(r['total_train_seconds']) for r in rr)} for k,rr in groups.items()]
facts['channels']=load_csv('artifacts/channel_consequence_ablations.csv')
facts['e03_rows']=len(load_csv('artifacts/exp03_async/psrei_vs_delay.csv'))

old=load_csv('artifacts/boundary_phase_scan/phase_scan_results_by_seed.csv')
facts['old_phase_recalibration']=[]
for lag in [0,1,2,3,6]:
    rr=[r for r in old if r['lead_step']=='5' and int(r['lag_steps'])==lag and r['channel_mode']=='all']
    if rr:
        clean=mean(float(r['phys_clean_shortage']) for r in rr)
        recal=mean(float(r['phys_recal_shortage']) for r in rr)
        facts['old_phase_recalibration'].append({'lag_steps':lag,'n':len(rr),'clean_shortage':clean,'recal_shortage':recal,'absorption':1-recal/clean})

newbase='analyses/decision_information_execution_20261018/evidence/results'
metrics=load_csv(newbase+'/aggregate/all_metrics.csv')
summary=load_csv(newbase+'/aggregate/summary.csv')
facts['new_development_summary']=summary
facts['calibration_discontinuity']=[]
lookup={(r['seed'],r['condition'],r['variant'],r['version']):r for r in metrics}
for (seed,condition,variant,version),r in lookup.items():
    if version!='raw': continue
    c=lookup[(seed,condition,variant,'calibrated')]
    facts['calibration_discontinuity'].append({'seed':seed,'condition':condition,'variant':variant,
        'raw_cost':float(r['mean_loss_kwh_per_cell']),'cal_cost':float(c['mean_loss_kwh_per_cell']),
        'raw_viol':float(r['violation_rate']),'cal_viol':float(c['violation_rate']),
        'delta_violation_pp':100*(float(c['violation_rate'])-float(r['violation_rate']))})
facts['paired_intervals']=load_json(newbase+'/aggregate/paired_intervals.json')

dev=load_csv('analyses/claim_revision_recovery_20261019/derived/all_decision_cases.csv')
facts['wtb_selection_case_counts']=dict(Counter(r['status'] for r in dev))
facts['wtb_case_counts']=load_json('analyses/claim_revision_recovery_20261019/derived/summary.json')['necessity_counts']
facts['wtb_pq1']=load_csv('analyses/claim_revision_recovery_20261019/derived/pq1_candidate_table.csv')
curves=load_csv('analyses/claim_revision_recovery_20261019/derived/withheld_selected_curves.csv')
facts['curve_rows']=len(curves)

indbase='analyses/independent_confirmation_execution_20261019/recovered/results'
primary=load_json(indbase+'/aggregate/primary.json')
facts['independent_primary']=primary
secondary=load_json(indbase+'/aggregate/secondary_span3.json')
facts['secondary_schema']={'top':list(secondary),'result_keys':list(secondary['results'][0])}
facts['independent_case_counts']=dict(Counter(r['minimum_status'] for r in load_csv('analyses/independent_confirmation_execution_20261019/derived/secondary_cases.csv')))
facts['independent_primary_span_rows']=load_csv('analyses/independent_confirmation_execution_20261019/derived/primary_span_secondary.csv')

# Re-sum stored policy actions' daily sufficient statistics, without model access.
all_eval=[]
for p in sorted((ROOT/indbase/'evaluate').glob('*/metadata.json'),key=lambda x:int(x.parent.name)):
    meta=json.loads(p.read_text(encoding='utf-8'))
    for pp in [p, p.parent/'blocks.npz']:
        reads.append({'path':pp.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(pp.read_bytes()).hexdigest()})
    z=np.load(p.parent/'blocks.npz',allow_pickle=False)
    all_eval.append({'directory':p.parent.name,'task':meta['task'],'keys':z.files,
                     'arrays':{k:float(z[k].sum(dtype=np.float64)) for k in z.files if ('loss' in k or 'count' in k or 'violation' in k)}})
facts['independent_stored_block_coverage']=len(all_eval)
facts['independent_stored_block_sums']=all_eval
primary_means={}
for subset in ['P1','WPQ36']:
    rr=[r for r in all_eval if r['task']['condition']=='pitch_withheld' and r['task']['subset']==subset and r['task']['estimator']=='HGB']
    primary_means[subset]=mean(r['arrays']['2__loss_sum']/r['arrays']['2__count'] for r in rr)
facts['primary_mean_reconstruction']=primary_means
facts['primary_ratio_reconstruction']=primary_means['P1']/primary_means['WPQ36']-1
cost_diff=[]
risk_diff=[]
point_rows=[]
qlevels=[.9,.925,.95,.975,.99]
for group in secondary['results']:
    for i,label in enumerate(group['labels']):
        subset,est,q=label.split('/')
        qi=qlevels.index(float(q[1:]))
        rr=sorted([r for r in all_eval if r['task']['condition']==group['condition'] and r['task']['subset']==subset and r['task']['estimator']==est],key=lambda r:r['task']['seed'])
        assert len(rr)==5
        costs=[r['arrays'][f'{qi}__loss_sum']/r['arrays'][f'{qi}__count'] for r in rr]
        risks=[r['arrays'][f'{qi}__violation_sum']/r['arrays'][f'{qi}__count'] for r in rr]
        cost_diff.append(mean(costs)-group['mean_cost'][i])
        risk_diff.extend(risks[s]-group['risk_point'][s][i] for s in range(5))
        point_rows.append({'condition':group['condition'],'policy':label,'mean_cost':mean(costs),'max_instance_risk':max(risks),
                           'archived_risk_upper':max(s[i] for s in group['risk_upper'])})
facts['secondary_point_reconstruction']={'policies':len(cost_diff),'instance_risks':len(risk_diff),
    'cost_max_abs_diff':max(map(abs,cost_diff)),'risk_max_abs_diff':max(map(abs,risk_diff)),'no_model_access':True,'no_resampling':True}
with (OUT/'independent_policy_points.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(point_rows[0]));w.writeheader();w.writerows(point_rows)
facts['corrected_e02']=[]
rr=load_csv('artifacts/raw_replay_20261015_v2/exp02/results.csv')
groups=defaultdict(list)
for row in rr:groups[(row['horizon'],row['model'])].append(row)
for (horizon,model),rr in groups.items():
    facts['corrected_e02'].append({'horizon':horizon,'model':model,'n':len(rr),
        'cost_mean':mean(float(r['full_psrei_kwh']) for r in rr),
        'raw_paired_cost_diff_mean':mean(float(r['full_psrei_kwh'])-float(next(b['full_psrei_kwh'] for b in groups[(horizon,'Site-Local Wspd-Bins')] if b['seed']==r['seed'])) for r in rr),
        'stored_bootstrap_delta_mean':mean(float(r['full_delta_psrei_mean']) for r in rr),
        'negative_seeds':sum(float(r['full_delta_psrei_mean'])<0 for r in rr),
        'viol_pct':mean(float(r['full_violation_rate_pct']) for r in rr),
        'seed_CI':[[r['seed'],float(r['full_delta_psrei_ci95_low']),float(r['full_delta_psrei_ci95_high'])] for r in rr]})
facts['corrected_channels']=load_csv('artifacts/raw_replay_20261015_v2/channels/summary.csv')
rr=load_csv('artifacts/raw_replay_20261015_v2/downstream_recovery_v1_attempt1/phase_aggregate/phase_scan_results_by_seed.csv')
facts['corrected_phase_recalibration']=[]
for lead in ['0','2','5']:
    for lag in [0,1,2,3,6]:
        rows=[r for r in rr if r['lead_step']==lead and int(r['lag_steps'])==lag and r['channel_mode']=='all']
        if rows:
            clean=mean(float(r['phys_clean_shortage']) for r in rows)
            recal=mean(float(r['phys_recal_shortage']) for r in rows)
            facts['corrected_phase_recalibration'].append({'lead':lead,'lag':lag,'n':len(rows),'clean':clean,'recal':recal,'absorption':1-recal/clean})
external=load_json('artifacts/metis_external_deterministic_20261015_attempt1/audit_report.json')
groups=defaultdict(list)
for r in external['results']:groups[(r['farm'],r['horizon'])].append(r)
facts['current_external']=[{'farm':k[0],'horizon':k[1],'n':len(rr),'mean_delta':mean(r['metrics']['delta_psrei_kwh'] for r in rr),
    'mean_violation':mean(r['metrics']['violation_rate_pct'] for r in rr),'mean_baseline_violation':mean(r['metrics']['baseline_violation_rate_pct'] for r in rr)} for k,rr in groups.items()]
facts['external_audit_stat_keys']=list(external)
facts['corrected_e03_rows']=len(load_csv('artifacts/raw_replay_20261015_v2/exp03/psrei_vs_delay.csv'))
facts['active_power_intervention']=load_csv('artifacts/raw_replay_20261015_v2/downstream_recovery_v1_attempt1/active_power/results.csv')
facts['supervision_intervention']=load_csv('artifacts/raw_replay_20261015_v2/downstream_recovery_v1_attempt1/supervision/results.csv')
receipt_checks=[]
for stage in ['exp02','exp03','channels']:
    receipt=load_json(f'artifacts/raw_replay_20261015_v2/execution/{stage}/record.json')
    for item in receipt['outputs']:
        suffix=item['path'].split('/artifacts/raw_replay_20261015_v2/',1)[1]
        pp=ROOT/'artifacts/raw_replay_20261015_v2'/suffix
        receipt_checks.append({'stage':stage,'status':receipt['status'],'exit_code':receipt['exit_code'],'path':pp.relative_to(ROOT).as_posix(),
            'hash_match':hashlib.sha256(pp.read_bytes()).hexdigest()==item['sha256'],'size_match':pp.stat().st_size==item['bytes']})
facts['replay_receipt_binding']=receipt_checks
(OUT/'recomputed_facts.json').write_text(json.dumps(facts,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'read_manifest.json').write_text(json.dumps(reads,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in facts.items() if k in ['corrected_e02','corrected_phase_recalibration','current_external','primary_mean_reconstruction','primary_ratio_reconstruction']},ensure_ascii=False,indent=2))
