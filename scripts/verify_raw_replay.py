"""Result-neutral completion check: cached checks cannot certify raw replay.

No scientific success threshold is changed. A withdrawal is never called reproduced.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from replay_provenance import sha256
from raw_replay import verify_records


def verify(root):
    failures=[]; reproduced=0; withdrawn=0
    coverage_path=root/'coverage.json'
    if not coverage_path.is_file():return ['Missing raw replay coverage manifest'],0,0
    rows=json.loads(coverage_path.read_text(encoding='utf-8'))
    registered=root/'historical_ARTIFACT_MANIFEST.json'
    if not registered.exists():
        failures.append('Missing immutable initial artifact-scope inventory')
    else:
        expected={r['filename'] for r in json.loads(registered.read_text(encoding='utf-8-sig'))}
        present=[r['historical_artifact'] for r in rows]
        missing=expected-set(present)
        if missing:failures.append(f'Registered scope was removed: {sorted(missing)}')
        if len(present)!=len(set(present)):failures.append('Duplicate coverage rows')
    for row in rows:
        name=row['historical_artifact'];status=row.get('execution_status')
        if status=='REPRODUCED':
            try:
                receipts=row['execution_receipts']
                if not receipts:raise ValueError('No actual execution receipts')
                for path in receipts:
                    receipt=json.loads(Path(path).read_text(encoding='utf-8'))
                    if receipt.get('status')!='EXECUTED' or receipt.get('exit_code')!=0:
                        raise ValueError(f'Execution incomplete: {path}')
                    if not receipt.get('inputs') or not receipt.get('outputs'):
                        raise ValueError(f'Incomplete execution lineage: {path}')
                    verify_records(receipt['inputs']);verify_records(receipt['outputs'])
                manifest=json.loads(Path(row['evidence_manifest']).read_text(encoding='utf-8'))
                verify_records(manifest)
                reproduced+=1
            except (KeyError,ValueError,OSError) as exc:failures.append(f'{name}: {exc}')
        elif status in ('FAILED','BLOCKED') and row.get('claim_disposition')=='WITHDRAWN':
            try:
                record=json.loads(Path(row['attempt_record']).read_text(encoding='utf-8'))
                if record.get('status') not in ('FAILED','BLOCKED') or not row.get('reason'):
                    raise ValueError('Withdrawal lacks an explicit attempted-execution/blocker record')
                if not Path(row['withdrawal_notice']).is_file():raise ValueError('Missing withdrawal notice')
                withdrawn+=1
            except (KeyError,ValueError,OSError) as exc:failures.append(f'{name}: {exc}')
        else:failures.append(f'{name}: execution {status}, not completed or explicitly withdrawn after a recorded failure/blocker')
    review_path=root/'final_independent_review.json'
    if not review_path.exists():failures.append('Missing final independent raw-data-to-manuscript review')
    else:
        review=json.loads(review_path.read_text(encoding='utf-8'))
        if review.get('scope')!='raw-data-to-manuscript' or review.get('verdict') not in ('PASS','PASS_WITH_BLOCKERS'):
            failures.append('Final review does not certify the required scope')
        if review.get('coverage_sha256')!=sha256(coverage_path):failures.append('Final review predates current coverage')
    return failures,reproduced,withdrawn


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]/'artifacts/raw_replay_20261015_v2')
    a=p.parse_args(); failures,n,w=verify(a.root)
    print('RAW_REPLAY_GATE: '+('FAIL' if failures else 'PASS_WITH_WITHDRAWALS' if w else 'PASS'))
    print(f'Validated reproduced artifacts: {n}; recorded withdrawals: {w}; unresolved checks: {len(failures)}')
    for f in failures[:8]:print('- '+f)
    if len(failures)>8:print(f'- ... {len(failures)-8} further unresolved checks')
    return 1 if failures else 0


if __name__=='__main__':raise SystemExit(main())
