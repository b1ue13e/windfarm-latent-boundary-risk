from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def rec(p):
    h=hashlib.sha256();
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return {'bytes':p.stat().st_size,'sha256':h.hexdigest()}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--bundle',type=Path,required=True); ap.add_argument('--prereg',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args(); b=a.bundle.resolve()
    receipt=json.loads((b/'e04_v2_execution_receipt.json').read_text()); plan=json.loads((b/'e04_v2_execution_plan.json').read_text()); manifest=json.loads((b/'e04_v2_output_manifest.json').read_text()); sel=json.loads((b/'e04_v2_selection.json').read_text())
    failures=[]
    if receipt.get('status')!='EXECUTED' or receipt.get('exit_code')!=0: failures.append('receipt status/exit')
    manifest_path=b/'e04_v2_output_manifest.json'; plan_path=b/'e04_v2_execution_plan.json'
    if receipt.get('output_manifest',{}).get('sha256') != rec(manifest_path)['sha256']: failures.append('receipt output manifest binding')
    if receipt.get('execution_plan',{}).get('sha256') != rec(plan_path)['sha256']: failures.append('receipt plan binding')
    if receipt.get('inputs',[{}])[0].get('sha256') != rec(a.prereg)['sha256']: failures.append('prereg hash mismatch')
    expected=[f'seed{s}_full_policy_day_blocks.npz' for s in range(201,206)]
    if sorted(x['path'] for x in manifest.get('files',[])) != expected: failures.append('manifest output set')
    for x in manifest.get('files',[]):
        p=b/x['path']
        if not p.is_file() or rec(p)!={'bytes':x['bytes'],'sha256':x['sha256']}: failures.append(f'output hash {x["path"]}')
    result={'status':'PASS_BUNDLE' if not failures else 'FAIL_BUNDLE','failures':failures,'receipt':rec(b/'e04_v2_execution_receipt.json'),'plan':rec(b/'e04_v2_execution_plan.json'),'manifest':rec(b/'e04_v2_output_manifest.json'),'selection':sel['selection']['status'],'stability':sel['selection'].get('selection_frequency'),'scientific_status':'needs-work; independent review pending'}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2)); return 0 if not failures else 1
if __name__=='__main__': raise SystemExit(main())
