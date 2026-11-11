"""Bounded validation runner; preserves scientific inputs and captures receipts."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'research_audit'/'validation'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    protected=[ROOT/x for x in ('AGENTS.md','PROJECT.md','docs/SCIENTIFIC_CONTRACT.md','paper_tste_ieee.md','paper_tste_supplementary.md',
        'scripts/verify_scientific_claim_gate.py','scripts/verify_tste_number_consistency.py','scripts/verify_independent_confirmation_gate.py',
        'analyses/independent_confirmation_execution_20261019/result_evidence.tar.gz',
        'experiments/E04/results/e04_v2/e04_v2_selection.json')]
    protected += list((ROOT/'analyses/independent_confirmation_execution_20261019/recovered/results').rglob('*.*'))
    protected=[p for p in protected if p.is_file()]
    before={p.relative_to(ROOT).as_posix():sha(p) for p in protected}
    cmds=[('scientific_claim_gate',[sys.executable,'scripts/verify_scientific_claim_gate.py']),
        ('tste_numbers',[sys.executable,'scripts/verify_tste_number_consistency.py','--output-dir',str(OUT/'numbers')]),
        ('independent_confirmation_gate',[sys.executable,'scripts/verify_independent_confirmation_gate.py','--output',str(OUT/'independent_confirmation_gate.json')]),
        ('targeted_tests',[sys.executable,'-m','pytest','-q','-p','no:cacheprovider',
            'tests/test_independent_confirmation.py','tests/test_independent_confirmation_gate.py',
            'tests/test_subset_minimum_necessity.py','tests/test_information_subset.py',
            'tests/test_decision_information_actions.py','tests/test_risk_frontier.py'])]
    receipts=[]
    for name,cmd in cmds:
        start=dt.datetime.now(dt.timezone.utc).isoformat();t=time.monotonic()
        with (OUT/f'{name}.log').open('w',encoding='utf-8') as log:
            result=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
        r={'name':name,'argv':cmd,'started_utc':start,'seconds':time.monotonic()-t,'exit_code':result.returncode,'log':f'research_audit/validation/{name}.log'}
        receipts.append(r);print(json.dumps(r),flush=True)
    after={p.relative_to(ROOT).as_posix():sha(p) for p in protected}
    changes=[x for x in before if before[x]!=after[x]]
    receipt={'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
        'hostname':platform.node(),'commands':receipts,'protected_files':len(protected),'protected_sha256_before':before,
        'protected_sha256_after':after,'changed_protected_files':changes,'training':False,'inference':False,'resampling':False,
        'scientific_scope':'Software and archive/claim consistency; no dependent-data coverage or field safety certification'}
    (OUT/'validation_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    if changes or any(x['exit_code'] for x in receipts):raise SystemExit(1)

if __name__=='__main__':main()
