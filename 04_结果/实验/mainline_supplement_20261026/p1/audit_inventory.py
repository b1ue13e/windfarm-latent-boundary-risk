"""Read-only identity inventory of the original frozen 2023--2024 policies."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--legacy-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    root = args.legacy_root
    freeze_path = root / 'results/chosen/freeze.json'
    freeze = json.loads(freeze_path.read_text())
    assert sha(freeze_path) == 'c04710efaa9e57b250906a9626c31e5a83559b4cfd30b6a18df2a489a39c7595'
    for rel, expected in freeze['sources'].items():
        assert sha(root / rel) == expected, rel
    assert sha(root / 'results/prepared/manifest.json') == freeze['prepared_manifest_sha256']
    assert sha(root / 'results/chosen/choices.json') == freeze['choices_sha256']
    prepared = json.loads((root / 'results/prepared/manifest.json').read_text())
    verified = {}
    for name, info in prepared.items():
        path = root / 'results/prepared' / name
        assert path.stat().st_size == info['bytes'] and sha(path) == info['sha256'], str(path)
        verified[str(path)] = info
    tasks = []
    for directory in sorted((root / 'results/historical').iterdir(), key=lambda x: int(x.name)):
        meta = json.loads((directory / 'metadata.json').read_text())
        task = meta['task']
        if task['condition'] != 'pitch_withheld' or task['estimator'] != 'HGB' or task['subset'] not in ('P1', 'WPQ36'):
            continue
        assert sha(directory / 'manifest.json') == freeze['historical_manifests'][str(directory / 'manifest.json')]
        manifest = json.loads((directory / 'manifest.json').read_text())
        for name, info in manifest.items():
            path = directory / name
            assert path.stat().st_size == info['bytes'] and sha(path) == info['sha256'], str(path)
            verified[str(path)] = info
        tasks.append(dict(task_index=int(directory.name), task=task, manifest_sha256=sha(directory / 'manifest.json'),
                          files=manifest, resource=meta['resource']))
    assert len(tasks) == 10
    assert sorted((t['task']['subset'], t['task']['seed']) for t in tasks) == sorted((s, seed) for s in ('P1','WPQ36') for seed in range(201,206))
    # Read only the manifest of the old 2025 context, never any 2026 data.
    unlocked_manifest = root / 'results/unlocked/manifest.json'
    unlocked = json.loads(unlocked_manifest.read_text())
    context = root / 'results/unlocked/physical_channels.npy'
    assert sha(context) == unlocked['physical_channels.npy']['sha256']
    verified[str(context)] = unlocked['physical_channels.npy']
    record = dict(status='VERIFIED_ORIGINAL_WEIGHTS_AVAILABLE', utc=datetime.now(timezone.utc).isoformat(),
                  legacy_root=str(root), legacy_freeze_sha256=sha(freeze_path), legacy_protocol_sha256=freeze['protocol_sha256'],
                  source_sha256=freeze['sources'], selected_tasks=tasks, verified_inputs=verified,
                  context_manifest_sha256=sha(unlocked_manifest), context_file=unlocked['physical_channels.npy'],
                  schema=json.loads((root / 'results/prepared/consumed_schema.json').read_text()),
                  new_2026_data_accessed=False, new_fits=0, argv=sys.argv, python=sys.version, host=platform.node())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(record, f, indent=2)
    print(json.dumps(dict(status=record['status'], selected_tasks=[(t['task_index'],t['task']) for t in tasks],
                          source_count=len(freeze['sources']), verified_files=len(verified), output=str(args.output))))


if __name__ == '__main__':
    main()
