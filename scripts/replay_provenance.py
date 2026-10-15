"""Small, explicit provenance helpers; a manifest is not a retraining certificate."""
from __future__ import annotations
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def file_record(path):
    p = Path(path).resolve()
    return {'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha256(p)}


def write_json(path, value):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')


def provenance(output_dir, inputs=(), config=None):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cp = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True)
    record = {'recorded_utc': datetime.now(timezone.utc).isoformat(),
              'argv': sys.argv, 'python': sys.version, 'platform': platform.platform(),
              'git_commit': cp.stdout.strip() if cp.returncode == 0 else None,
              'inputs': [file_record(p) for p in inputs], 'config': config or {},
              'scope': 'archived execution products; no universal reproducibility certification'}
    if Path(sys.argv[0]).is_file():
        record['executed_script'] = file_record(sys.argv[0])
    write_json(out / 'provenance.json', record)
    return record


def finalize(output_dir):
    out = Path(output_dir)
    records = [file_record(p) for p in sorted(out.rglob('*'))
               if p.is_file() and p.name != 'output_manifest.json']
    write_json(out / 'output_manifest.json', records)
