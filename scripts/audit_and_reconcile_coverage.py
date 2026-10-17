import json
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

cov_path = ROOT / 'artifacts/raw_replay_20261015_v2/coverage.json'
rows = json.loads(cov_path.read_text(encoding='utf-8'))
manifest_path = ROOT / 'artifacts/raw_replay_20261015_v2/historical_ARTIFACT_MANIFEST.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))

print(f"Total coverage rows: {len(rows)}")
print(f"Total historical manifest rows: {len(manifest)}")

# Check disposition mapping
disposition_doc = (ROOT / 'docs/REPLAY_CLAIM_DISPOSITION_20261015.md').read_text(encoding='utf-8')
print("Disposition doc length:", len(disposition_doc))

# Check existing records in raw_replay_20261015_v2/execution
exec_dir = ROOT / 'artifacts/raw_replay_20261015_v2/execution'
records = list(exec_dir.glob('*/record.json'))
print(f"Found {len(records)} execution records in raw_replay_20261015_v2/execution:")
for r in records:
    d = json.loads(r.read_text(encoding='utf-8'))
    print(f" - {r.parent.name}: status={d.get('status')}, exit_code={d.get('exit_code')}")
