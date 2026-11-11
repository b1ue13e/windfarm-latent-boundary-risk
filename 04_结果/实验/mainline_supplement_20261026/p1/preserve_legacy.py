"""Preserve the original policy/runtime files without copying any new measurements."""
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    base = Path(__file__).resolve().parent
    identity = json.loads((base / 'identity_packet.json').read_text())
    root = Path(identity['legacy_root'])
    archive = base / 'legacy_policy_runtime.zip'
    names = set(identity['source_sha256'])
    names.update(['results/chosen/freeze.json', 'results/chosen/choices.json',
                  'results/prepared/point_forecaster.joblib', 'results/prepared/consumed_schema.json',
                  'results/prepared/manifest.json', 'results/unlocked/manifest.json'])
    for task in identity['selected_tasks']:
        names.update('results/historical/{}/{}'.format(task['task_index'], n) for n in task['files'])
        names.add('results/historical/{}/manifest.json'.format(task['task_index']))
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for name in sorted(names):
            z.write(root / name, name)
    record = dict(bytes=archive.stat().st_size, sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  members=len(names), new_2026_measurements_included=False)
    (base / 'legacy_policy_runtime_receipt.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record))


if __name__ == '__main__':
    main()
