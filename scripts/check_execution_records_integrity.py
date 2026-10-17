import json
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]

def digest(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

cov_dir = ROOT / 'artifacts/raw_replay_20261015_v2'
exec_dir = cov_dir / 'execution'

records = sorted(exec_dir.glob('*/record.json'))
print(f"Total execution records in {exec_dir}: {len(records)}")

for r in records:
    name = r.parent.name
    try:
        data = json.loads(r.read_text(encoding='utf-8'))
        inputs = data.get('inputs', [])
        outputs = data.get('outputs', [])
        # Check inputs
        in_ok = True
        for inp in inputs:
            p = Path(inp['path'])
            if not p.is_file() or digest(p) != inp['sha256']:
                in_ok = False
                break
        out_ok = True
        for out in outputs:
            p = Path(out['path'])
            if not p.is_file() or digest(p) != out['sha256']:
                out_ok = False
                break
        print(f"[{name}] status={data.get('status')}, exit_code={data.get('exit_code')}, inputs_ok={in_ok} ({len(inputs)}), outputs_ok={out_ok} ({len(outputs)})")
    except Exception as e:
        print(f"[{name}] ERROR: {e}")
