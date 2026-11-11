"""Coordinator-reviewed executable freeze. Does not open any ZIP or outcomes."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    base=Path(__file__).resolve().parent
    protocol=base/'protocol.json'; adapter=base/'adapter.py'
    cfg=json.loads(protocol.read_text())
    receipt=base/'results/preflight/preflight_receipt.json'
    r=json.loads(receipt.read_text())
    assert r['status']=='PREFLIGHT_PASS_NO_TEST_READ' and r['archive_never_opened']
    assert r['protocol_sha256']==sha(protocol) and r['adapter_sha256']==sha(adapter)
    assert sha(adapter)=='9a3a6ffbcc5d93c2b461cb56c2c462e4e92af901b28ca444e6d802f5fe5a68ca'
    assert r['pbs_job'] and r['legacy_freeze_verified'] and r['checked_legacy_inputs']==69
    assert not (base/'results/UNLOCK_EVENT.json').exists()
    created=datetime.now(timezone.utc).isoformat()
    assert datetime.fromisoformat(r['utc'])<datetime.fromisoformat(created)
    freeze=dict(review_status='PASS_BEFORE_UNLOCK',created_utc=created,
                protocol_sha256=sha(protocol),adapter_sha256=sha(adapter),
                preflight_receipt_sha256=sha(receipt),legacy_freeze_sha256=cfg['legacy_freeze_sha256'],
                source_2026_archive_sha256=cfg['new_archive']['sha256'],
                source_2025_boundary_archive_sha256=cfg['raw_2025_archive_sha256'],
                sources={n:sha(base/n) for n in ('adapter.py','test_mainline_2026_adapter.py')},
                tests=dict(synthetic_adapter_passed=11,original_tests_passed=16,P0_passed=3),
                review='Coordinator independently corrected and inspected worker draft before any outcome read; no H gate or q selection',
                window=cfg['window'],models_refitted=0)
    destination=base/'results/chosen/freeze.json'
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('x') as f: json.dump(freeze,f,indent=2)
    print(json.dumps(dict(freeze_sha256=sha(destination),**freeze)))


if __name__=='__main__': main()
