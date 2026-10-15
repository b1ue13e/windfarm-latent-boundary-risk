"""Check frozen scientific inputs/baseline and retain every old/new difference."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get('PBS_JOBID'):
        raise RuntimeError('Comparison only inside PBS allocation')
    import numpy as np
    import pandas as pd
    root = args.workspace.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    base = root / 'artifacts/raw_replay_external_models_20261015'
    old, new = base / 'matched_transfer', base / 'deterministic_matched_transfer_v1'
    for name in ('matched_transfer', 'deterministic_matched_transfer_v1'):
        record = json.loads((base / f'execution/{name}/record.json').read_text())
        if record.get('status') != 'EXECUTED' or record.get('exit_code') != 0 or not record.get('outputs'):
            raise ValueError('Production execution incomplete')
        for item in record['outputs']:
            if sha(item['path']) != item['sha256']:
                raise ValueError('Original/new output hash differs')
    key = ['farm_id', 'seed', 'horizon']
    frames = [pd.read_csv(path / 'exp01_pitchmasked_v3_seed_results.csv',
        float_precision='round_trip').set_index(key).sort_index() for path in (old, new)]
    if len(frames[0]) != 20 or not frames[0].index.equals(frames[1].index) or not frames[0].index.is_unique:
        raise ValueError('Twenty matched seed/site/horizon keys required')
    for field in ('checkpoint_sha256', 'training_summary_sha256', 'pitch_withheld_before_inference',
                  'n_evaluated_cells', 'baseline_psrei_kwh', 'baseline_violation_rate_pct'):
        if not np.array_equal(frames[0][field].to_numpy(), frames[1][field].to_numpy()):
            raise ValueError('Unchanged-scientific-specification comparison failed: ' + field)
    differences = frames[0].reset_index()[key].copy()
    for field in ('psrei_kwh', 'delta_psrei_kwh', 'violation_rate_pct',
                  'baseline_psrei_kwh', 'baseline_violation_rate_pct', 'n_evaluated_cells'):
        differences[field + '_old'] = frames[0][field].to_numpy()
        differences[field + '_new'] = frames[1][field].to_numpy()
        differences[field + '_new_minus_old'] = frames[1][field].to_numpy() - frames[0][field].to_numpy()
    differences.to_csv(output / 'all_seed_differences.csv', index=False)
    gate_differences = []
    for farm in ('kelmarsh', 'penmanshiel'):
        for seed in range(201, 206):
            for split in ('val', 'test'):
                name = f'{farm}_seed{seed}_{split}_gate_pitchmasked.npy'
                a, b = np.load(old / name), np.load(new / name)
                if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
                    raise ValueError('Invalid old/new gate shape/values')
                gate_differences.append({'farm': farm, 'seed': seed, 'split': split,
                    'old_sha256': sha(old / name), 'new_sha256': sha(new / name),
                    'changed_values': int(np.count_nonzero(a != b)),
                    'max_absolute_difference': float(np.abs(a.astype(np.float64) - b.astype(np.float64)).max()),
                    'changed_argmax_cells': int(np.count_nonzero(a.argmax(-1) != b.argmax(-1)))})
    statistics = [pd.read_csv(path / 'exp01_pitchmasked_v3_joint_statistics.csv',
        float_precision='round_trip').set_index(['farm_id', 'horizon']).sort_index() for path in (old, new)]
    if len(statistics[0]) != 4 or not statistics[0].index.equals(statistics[1].index):
        raise ValueError('Four matched joint-statistic rows required')
    for label, frame in zip(('old', 'new'), statistics):
        frame.to_csv(output / f'{label}_joint_statistics.csv')
    report = {'status': 'EXACT_INPUT_COHORT_AND_WIND_BASELINE_INVARIANCE_VERIFIED',
        'pbs_job_id': os.environ['PBS_JOBID'], 'rows': 20, 'source_sha256': sha(__file__),
        'gate_differences': gate_differences, 'scientific_completion': False,
        'scope': 'input/baseline integrity and all-version differences; old exact audit stays FAILED, no harmlessness/superiority certificate'}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    manifest = [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)}
                for p in output.iterdir() if p.is_file()]
    (output / 'output_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'rows': 20, 'scientific_completion': False}))


if __name__ == '__main__':
    main()
