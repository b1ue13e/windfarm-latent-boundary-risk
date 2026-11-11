"""Check archived confirmation claims, without changing any scientific gate.

This additional consistency gate accepts faithfully reported negative outcomes.
It does not certify bootstrap coverage or field safety.
"""
import argparse
from datetime import datetime
import hashlib
import json
import subprocess
from repo_paths import Path, repository_root
import tarfile

import numpy as np


def digest(value):
    return hashlib.sha256(value).hexdigest()


def check_primary(primary, choices, cfg):
    selected=next(g for g in choices['groups'] if g['condition']=='pitch_withheld')
    indices=sorted(set(selected['sets']['0.02']['original_indices']+[selected['reference_index']]))
    assert primary['labels']==[selected['labels'][i] for i in indices], 'Primary is not the historical family'
    assert not primary['uses_test_selection'] and not choices['uses_confirmation'], 'Test-side selection'
    ref=indices.index(selected['reference_index'])
    env=primary['bounds']['groups'][0]
    risk=np.asarray(env['risk_upper'],float);cost=np.asarray(env['mean_cost'],float)
    point=np.asarray(env['relative_ratio_point'],float)
    assert risk.shape==(5,len(indices)) and np.isfinite(risk).all()
    assert np.allclose(point,cost[:,None]/cost[None,:]-1,rtol=0,atol=1e-12)
    reference_ok=bool(selected['reference_historically_qualified'] and np.all(risk[:,ref]<=cfg['v_max']))
    candidate_indices=selected['sets']['0.02']['original_indices']
    actual=[]
    for i in candidate_indices:
        p=indices.index(i)
        actual.append(bool(np.all(risk[:,p]<=cfg['v_max']) and reference_ok and
                           env['relative_ratio_upper'][p][ref]<=cfg['primary_epsilon']))
    expected='NO_HISTORICAL_SELECTION' if not actual else (
        'ALL_FROZEN_CANDIDATES_CONFIRMED' if all(actual) else 'CONFIRMATION_NOT_ESTABLISHED')
    assert primary['verdict']['status']==expected, 'Reported confirmation contradicts frozen bounds'
    assert len(actual)==len(primary['verdict']['candidates'])
    assert actual==[r['confirmed'] for r in primary['verdict']['candidates']]
    return expected


def check_secondary(group,cfg):
    lo,hi=np.asarray(group['risk_lower'],float),np.asarray(group['risk_upper'],float)
    lower=np.asarray(group['relative_ratio_lower'],float)
    upper=np.asarray(group['relative_ratio_upper'],float)
    lower=np.where(np.isnan(lower),-np.inf,lower)
    upper=np.where(np.isnan(upper),np.inf,upper)
    order=[tuple(r) for r in group['resources']]
    possible=np.flatnonzero(np.all(lo<=cfg['v_max'],axis=0)).tolist()
    qualified=np.flatnonzero(np.all(hi<=cfg['v_max'],axis=0)).tolist()
    statuses=[]
    for row in group['secondary_retrospective_full_q']:
        eps=row['epsilon'];selection=row['sufficient_set'];audit=row['minimum_audit']
        eligible=[j for j in qualified if all(upper[j,k]<=eps for k in possible)]
        minimum=min((order[j] for j in eligible),default=None)
        chosen=[j for j in eligible if order[j]==minimum]
        assert selection['minimum_resource_indices']==chosen, 'Secondary sufficient set mismatch'
        assert selection['eligible_indices']==eligible
        assert selection['risk_qualified_indices']==qualified
        assert selection['possible_feasible_indices']==possible
        smaller=[j for j in range(len(order)) if chosen and order[j]<minimum]
        excluded=[j for j in smaller if np.any(lo[:,j]>cfg['v_max']) or
                  any(lower[j,k]>eps for k in qualified)]
        unresolved=[j for j in smaller if j not in excluded]
        expected='NO_CERTIFIED_SUFFICIENT_POLICY' if not chosen else (
            'MINIMUM_UNRESOLVED' if unresolved else 'FINITE_FAMILY_MINIMUM_IDENTIFIED')
        assert audit['status']==expected, 'Secondary minimality overclaim'
        assert audit['chosen']==chosen and audit['smaller']==smaller and audit['unresolved']==unresolved
        assert [x['index'] for x in audit['excluded']]==excluded
        statuses.append(expected)
    return statuses


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,default=Path('analyses/independent_confirmation_execution_20261019'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();base=args.evidence
    packet=base/'result_evidence.tar.gz';bound=json.loads((base/'download_manifest.json').read_text())
    assert packet.stat().st_size==bound['bytes'] and digest(packet.read_bytes())==bound['sha256']
    required={'export_manifest.json','results/aggregate/primary.json','results/chosen/freeze.json',
              'results/chosen/choices.json','results/UNLOCK_EVENT.json','results/unlocked/receipt.json',
              'results/aggregate/receipt.json','preflight_receipt.json','deployment_manifest.json',
              'experiments/independent_confirmation_execution_20261019/protocol.json'}
    required.update({f'results/aggregate/secondary_span{s}.json' for s in (3,1,7)})
    with tarfile.open(packet, 'r|gz') as t:
        payload={};event_count=0
        for member in t:
            event_count += member.name=='results/UNLOCK_EVENT.json'
            if member.name in required or (member.name.startswith('results/historical/') and member.name.endswith('/manifest.json')):
                payload[member.name]=t.extractfile(member).read()
        manifest=json.loads(payload['export_manifest.json'])
        def read(name):
            raw=payload[name];record=manifest[name]
            assert len(raw)==record['bytes'] and digest(raw)==record['sha256'], name
            return raw
        def load(name):
            return json.loads(read(name))
        primary=load('results/aggregate/primary.json');choices=load('results/chosen/choices.json')
        freeze=load('results/chosen/freeze.json');event=load('results/UNLOCK_EVENT.json')
        cfg=load('experiments/independent_confirmation_execution_20261019/protocol.json')
        preflight=load('preflight_receipt.json');deployment=load('deployment_manifest.json')
        unlocked=load('results/unlocked/receipt.json');aggregate=load('results/aggregate/receipt.json')
        assert event_count==1
        assert digest(read('results/chosen/freeze.json'))==event['freeze_sha256']
        assert digest(read('results/chosen/choices.json'))==freeze['choices_sha256']==primary['choices_sha256']
        protocol_sha=digest(read('experiments/independent_confirmation_execution_20261019/protocol.json'))
        assert protocol_sha==freeze['protocol_sha256']==event['protocol_sha256']==preflight['protocol_sha256']==deployment['protocol_sha256']
        assert preflight['exit_code']==0 and preflight['sources']==freeze['sources']==deployment['sources']
        assert preflight['git_commit']==deployment['git_commit']
        assert datetime.fromisoformat(freeze['created_utc'])<datetime.fromisoformat(event['utc'])<datetime.fromisoformat(unlocked['finished_utc'])<=datetime.fromisoformat(aggregate['started_utc'])
        assert unlocked['refit'] is False and unlocked['qualification']=='CONFIRMATION_COORDINATES_QUALIFIED'
        assert event['archive_sha256']==cfg['annual_sha256']['2025']
        assert unlocked['event_sha256']==digest(read('results/UNLOCK_EVENT.json'))
        assert len(freeze['historical_manifests'])==550
        for path,expected in freeze['historical_manifests'].items():
            suffix='results/'+path.split('/results/',1)[1]
            assert digest(read(suffix))==expected
        expected=check_primary(primary,choices,cfg)
        secondary_statuses=[]
        for span in (3,1,7):
            for group in load(f'results/aggregate/secondary_span{span}.json')['results']:
                secondary_statuses.extend(check_secondary(group,cfg))
        assert len(secondary_statuses)==90
    source_packet=base/'deployment_packet.tar.gz'
    transport=json.loads((base/'transport.json').read_text())
    assert digest(source_packet.read_bytes())==transport['sha256']
    with tarfile.open(source_packet) as source:
        for name,expected_sha in freeze['sources'].items():
            assert digest(source.extractfile(name).read())==expected_sha, name
        review=json.load(source.extractfile('REVIEW_RELEASE.json'))
        assert review['status']=='PASS_FOR_PRE_UNLOCK_IMPLEMENTATION' and not review['blocking_findings']
        for name,expected_sha in review['sources'].items():
            assert digest(source.extractfile(name).read())==expected_sha, name
    actual=json.loads((base/'confirmation_actual_review_receipt.json').read_text())
    assert actual['errors']==[] and actual['evaluation_workers_verified']==550
    assert actual['primary_sha256']==manifest['results/aggregate/primary.json']['sha256']
    assert actual['secondary_case_count']==90
    original_gate_check=subprocess.run(['git','diff','--exit-code',deployment['git_commit'],'--',
        'scripts/verify_scientific_claim_gate.py','scripts/verify_tste_number_consistency.py'],capture_output=True)
    assert original_gate_check.returncode==0, 'Original scientific/number gate changed since frozen deployment'
    output=dict(status='PASS',primary_status=expected,historical_workers_bound=550,actual_review_workers=550,
                one_unlock_event=True,code_and_protocol_frozen_before_unlock=True,
                original_gates_unchanged=True,secondary_cases_checked=len(secondary_statuses),
                scope='Archive/provenance/claim consistency; no model refit, bootstrap, coverage or deployment certification')
    with args.output.open('x',encoding='utf-8') as f:
        json.dump(output,f,indent=2)
    print(json.dumps(output))


if __name__=='__main__':
    main()
