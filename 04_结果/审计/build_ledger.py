"""Normalize actual run points and retained branch records without inventing fields."""
from pathlib import Path
import csv
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research_audit'
FIELDS=['Experiment ID','Research Question','Dataset / Instance','Method','Baseline','Configuration','Seed','Budget',
    'Metric','Raw Result','Comparison','Effect Size','Variability','Artifact Path','Reproducibility','Audit Status','Notes']

def read_csv(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def j(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))

def base():return {k:'UNKNOWN_NOT_RECORDED_OR_NOT_RECONSTRUCTED' for k in FIELDS}

def main():
    rows=[];inputs={}
    source=OUT/'working/rigor/all_worker_quantile_points.csv'
    inputs[str(source.relative_to(ROOT))]=hashlib.sha256(source.read_bytes()).hexdigest()
    points=read_csv(source)
    choices=json.loads((ROOT/'analyses/independent_confirmation_execution_20261019/recovered/results/chosen/choices.json').read_text())
    references={g['condition']:g['labels'][g['reference_index']] for g in choices['groups']}
    lookup={(r['stage'],r['condition'],r['seed'],r['label']):r for r in points}
    for p in points:
        r=base();ref=references[p['condition']];other=lookup.get((p['stage'],p['condition'],p['seed'],ref))
        r.update({'Experiment ID':f"HOT-{p['stage']}-{p['worker']}-q{p['q']}",
            'Research Question':'Fixed-reference noninferiority and separately finite-family capability',
            'Dataset / Instance':f"Hill of Towie; {'2024 selection' if p['stage']=='historical' else '2025 confirmation'}; {p['condition']}",
            'Method':p['label'],'Baseline':ref,'Configuration':j(dict(protocol='experiments/independent_confirmation_execution_20261019/protocol.json',
                resource=p['resource'],q=p['q'],stage=p['stage'],common_forecast='W/P36 at issue-6; clock/ID; conditional incremental input')),
            'Seed':p['seed'],'Budget':'360000 policy-fit rows; HGB100 iterations or MLP80 epochs; Persistence no fit; q variants share model',
            'Metric':'cost_kWh_equivalent_per_valid_turbine_interval; strict violation rate; reserve; shortage',
            'Raw Result':j({k:p[k] for k in ('mean_cost_kwh_equivalent','violation_rate','n_valid','n_day_blocks','cost_total_kwh_equivalent','violations','reserve_total_kwh','shortage_total_kwh')}),
            'Variability':'Single frozen instance point; joint dependent-day approximate bounds live in aggregate JSON, not inferable from this row',
            'Artifact Path':p['artifact'],'Reproducibility':'VERIFIED archived block -> point; no raw data/model/action end-to-end replay',
            'Audit Status':'VERIFIED_BLOCK_ARITHMETIC',
            'Notes':'Worker×q point; five q offsets share fitted model; seeds share weather. All-grid rows are not all confirmatory selections. Descriptive effects need risk matching.'})
        if other:
            a=float(p['mean_cost_kwh_equivalent']);b=float(other['mean_cost_kwh_equivalent'])
            r['Comparison']=j(dict(mean_cost=other['mean_cost_kwh_equivalent'],risk=other['violation_rate'],artifact=other['artifact']))
            r['Effect Size']=j(dict(cost_difference=a-b,relative_cost=a/b-1))
        rows.append(r)
    families=read_csv(OUT/'working/discovery/family_ledger.csv')
    for f in families:
        path=Path(f['artifact_path'])
        inputs[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else 'MISSING'
        records=read_csv(path) if path.is_file() and path.suffix.lower()=='.csv' else [None]
        for i,p in enumerate(records,2 if records!=[None] else 1):
            r=base()
            r.update({'Experiment ID':f"{f['family_id']}-record-{i}",'Research Question':f['experiment_family'],
                'Dataset / Instance':'See original record; heterogeneous historical/development/confirmation scope',
                'Method':(p.get('model') or p.get('method') or p.get('variant') or p.get('policy') or 'NOT_UNIQUELY_INFERRED') if p else f['experiment_family'],
                'Configuration':j(p) if p else 'See artifact protocol/JSON; not silently inferred from name',
                'Seed':(p.get('seed') or p.get('Seed') or p.get('random_seed') or 'MISSING_OR_AGGREGATE') if p else 'MISSING_OR_AGGREGATE',
                'Metric':'Original row with units/metric names preserved; cross-family metrics not pooled',
                'Raw Result':j(p) if p else f['result_summary'],
                'Artifact Path':str(path.relative_to(ROOT)).replace('\\','/')+f'#record={i}',
                'Reproducibility':'Content read / bounded reaggregation; see family status and working/discovery/EVIDENCE_REVIEW.md',
                'Audit Status':f['status'],'Notes':f['interpretation_limit']+'; '+('Original CSV row retained, including unfavorable/invalid branch; not an independent replication.' if p else 'Family-level JSON/document state, not a run.')})
            rows.append(r)
    with (OUT/'02_experiment_ledger.csv').open('w',encoding='utf-8-sig',newline='') as file:
        w=csv.DictWriter(file,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    receipt=dict(rows=len(rows),latest_worker_quantile_points=len(points),family_branches=len(families),
        other_original_or_family_records=len(rows)-len(points),fields=FIELDS,inputs_sha256=inputs,
        missing_policy='All missing fields explicit UNKNOWN/MISSING; no invented CI or budget',
        unit_warning='Rows mix worker×q, original CSV row and family-state records; do not sum as independent runs.')
    (OUT/'ledger_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(j({k:receipt[k] for k in ('rows','latest_worker_quantile_points','family_branches','other_original_or_family_records')}))

if __name__=='__main__':main()
