"""Verify ledger identities and run only the existing document-consistency gates."""
from pathlib import Path
import ast
import csv
import datetime as dt
import hashlib
import json
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    (OUT/'verification').mkdir(exist_ok=False)
    scope=json.loads((OUT/'scope_and_inputs.json').read_text(encoding='utf-8'))
    recompute=json.loads((OUT/'recompute_receipt.json').read_text(encoding='utf-8'))
    a=json.loads((OUT/'derived.json').read_text(encoding='utf-8'))
    decision=json.loads((OUT/'decision.json').read_text(encoding='utf-8'))
    for source,expected in scope['inputs_sha256'].items():assert sha(ROOT/source)==expected,source
    for source,expected in recompute['sources_sha256_before'].items():assert sha(ROOT/source)==expected,source
    assert recompute['sources_sha256_before']==recompute['sources_sha256_after'] and recompute['all_inputs_unchanged']
    assert all(recompute[k] for k in ('no_training','no_inference','no_calibration','no_resampling','no_remote'))
    assert decision['decision']=='STOP_ADDITIONAL_INVESTMENT' and decision['no_currency_conversion']
    assert 0<a['deltas_p1_minus_reference']['relative_cost']<.02
    assert abs(a['deltas_p1_minus_reference']['relative_cost']-.005641474815991643)<1e-12
    assert a['resources']['full_X_bytes']==653338896
    assert a['resources']['learner_training_slice_bytes']=={'P1':7200000,'WPQ36':161280000}
    with (OUT/'policy_seed_ledger.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==10 and {int(r['seed']) for r in rows}=={201,202,203,204,205}
    for seed in range(201,206):
        p=next(r for r in rows if int(r['seed'])==seed and r['policy']=='P1')
        q=next(r for r in rows if int(r['seed'])==seed and r['policy']=='WPQ36')
        assert float(p['cost_mean'])>float(q['cost_mean']) and float(p['shortage_mean'])>float(q['shortage_mean'])
    for p in OUT.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
    commands=[('scientific_claim_gate',[sys.executable,'scripts/verify_scientific_claim_gate.py']),
        ('number_gate',[sys.executable,'scripts/verify_tste_number_consistency.py','--output-dir',str(OUT/'verification/numbers')])]
    results=[]
    for name,cmd in commands:
        r=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (OUT/'verification'/f'{name}.txt').write_bytes(r.stdout)
        results.append(dict(name=name,argv=cmd,exit_code=r.returncode))
        assert r.returncode==0,r.stdout.decode('utf-8','replace')[-1800:]
    numbers=json.loads((OUT/'verification/numbers/tste_number_consistency_audit.json').read_text(encoding='utf-8'))
    assert numbers['n_checks']==77 and numbers['n_failed']==0
    for source,expected in recompute['sources_sha256_before'].items():assert sha(ROOT/source)==expected,source
    receipt=dict(utc=dt.datetime.now(dt.timezone.utc).isoformat(),argv=sys.argv,python=sys.version,platform=platform.platform(),
        status='PASS_BOUNDED_RESOURCE_LOSS_REVIEW',protected_sources_rechecked=len(recompute['sources_sha256_before']),
        frozen_scope_inputs=len(scope['inputs_sha256']),source_changes=[],commands=results,number_checks='77/77',
        decision=decision['decision'],no_currency_conversion=True,no_training=True,no_inference=True,no_resampling=True,no_new_direction=True,
        scope='Deterministic resource/loss accounting and consistency, not real customer demand, monetary net-benefit, benchmark or field-safety certification')
    paths=[ROOT/'research_audit/14_resource_loss_break_even_review.md']+[p for p in OUT.rglob('*') if p.is_file() and p.name!='validation_receipt.json' and '__pycache__' not in p.parts and p.parent.name!='local_retrieval_cache']
    receipt['output_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)}
    (OUT/'validation_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k!='output_sha256'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
