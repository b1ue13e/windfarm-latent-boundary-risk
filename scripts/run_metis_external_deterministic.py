"""Guarded out-of-tree production and audit for deterministic external replay."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--mode', choices=['preflight', 'produce'], required=True)
    args = parser.parse_args()
    if not os.environ.get('PBS_JOBID'):
        raise RuntimeError('Only inside PBS allocation')
    root = args.workspace.resolve()
    tool = args.manifest.resolve().parent
    manifest = json.loads(args.manifest.read_text())
    for row in manifest['files']:
        if sha(tool / row['name']) != row['sha256']:
            raise ValueError('Package source differs: ' + row['name'])
    frozen = root / 'metis_input_manifest.json'
    if sha(frozen) != manifest['frozen_input_manifest_sha256']:
        raise ValueError('Frozen input manifest identity differs')
    for row in json.loads(frozen.read_text()):
        if sha(root / row['relative_path']) != row['sha256']:
            raise ValueError('Frozen source/input differs')
    original = (root / 'scripts/repair_exp01_pitch_withheld_v3.py').read_text()
    for token in ('import json\n', 'ROOT = Path(__file__).resolve().parents[1]',
                  '    out.mkdir(parents=True, exist_ok=True)',
                  'retrospective reanalysis; no preregistration created or backfilled',
                  '\nif __name__=="__main__":'):
        if original.count(token) != 1:
            raise ValueError('Unexpected producer source adapter target')
    modified = original.replace('import json\n', 'import json\nimport os\nfrom metis_numeric_profile import configure\nNUMERIC_PROFILE = configure()\n', 1)
    modified = modified.replace('ROOT = Path(__file__).resolve().parents[1]',
                                'ROOT = Path(os.environ["WINDFARM_REPO_ROOT"]).resolve()', 1)
    modified = modified.replace('    out.mkdir(parents=True, exist_ok=True)',
        '    out.mkdir(parents=True, exist_ok=False)\n'
        '    from replay_provenance import provenance, finalize\n'
        '    provenance(out, [Path(__file__), Path(__file__).parent / "metis_numeric_profile.py", Path(__file__).parent / "manifest.json"], vars(args))\n'
        '    (out / "numeric_execution_profile.json").write_text(json.dumps(NUMERIC_PROFILE, indent=2), encoding="utf-8")', 1)
    modified = modified.replace('retrospective reanalysis; no preregistration created or backfilled',
        'registered deterministic execution repair; original non-exact results retained', 1)
    modified = modified.replace('\nif __name__=="__main__":', '\n    finalize(out)\n\nif __name__=="__main__":', 1)
    if modified != (tool / 'produce_external_transfer.py').read_text():
        raise ValueError('Producer differs beyond declared profile/workspace/provenance adapters')
    for filename in ('produce_external_transfer.py', 'audit_metis_external_transfer.py'):
        compile((tool / filename).read_text(), filename, 'exec')
    sys.path[:0] = [str(root / 'scripts'), str(root)]
    from raw_replay import verify_run_receipt, run_command
    from replay_provenance import write_json, file_record
    base = root / 'artifacts/raw_replay_external_models_20261015'
    name = 'deterministic_matched_transfer_v1'
    output = base / name
    if output.exists() or (base / 'execution' / name).exists():
        raise FileExistsError('Preserve existing production attempt')
    required = [root / f'artifacts/raw_replay_20261015_v2/execution/train_aligned_force_{s}/record.json' for s in range(201, 206)]
    required += [base / f'execution/{farm}_{s}/record.json' for farm in ('kelmarsh', 'penmanshiel') for s in range(201, 206)]
    for path in required:
        record = json.loads(path.read_text())
        if (record.get('status') != 'EXECUTED' or record.get('exit_code') != 0 or
            not record.get('inputs') or not record.get('outputs') or record.get('missing_outputs')):
            raise ValueError('Incomplete upstream success receipt')
        verify_run_receipt(path)
    if args.mode == 'preflight':
        path = tool / 'preflight_report.json'
        if path.exists():
            raise FileExistsError(path)
        write_json(path, {'status': 'SOURCE_AND_INPUTS_VERIFIED', 'pbs_job_id': os.environ['PBS_JOBID'],
            'manifest': file_record(args.manifest), 'receipts': [file_record(p) for p in required],
            'scientific_completion': False})
        print('DECLARED_ADAPTERS_AND_SUCCESSFUL_INPUTS_PASS', flush=True)
        return
    preflight = json.loads((tool / 'preflight_report.json').read_text())
    if preflight['status'] != 'SOURCE_AND_INPUTS_VERIFIED' or preflight['manifest']['sha256'] != sha(args.manifest):
        raise ValueError('Matching successful preflight required')
    import subprocess
    command = ['/opt/pbs/bin/qstat', '-x', '-f', '-F', 'json', preflight['pbs_job_id']]
    check = subprocess.run(command, capture_output=True)
    for suffix, data in [('stdout', check.stdout), ('stderr', check.stderr)]:
        with (tool / f'production_preflight.{suffix}').open('xb') as stream:
            stream.write(data)
    job = json.loads(check.stdout).get('Jobs', {}).get(preflight['pbs_job_id'], {}) if check.returncode == 0 else {}
    if (job.get('job_state') != 'F' or job.get('Exit_status') != 0 or
        job.get('Job_Name') != 'p3_det_check' or not job.get('Job_Owner', '').startswith('junyu@')):
        raise ValueError('Actual PBS preflight exit0 required')
    os.environ['WINDFARM_REPO_ROOT'] = str(root)
    source = root / 'artifacts/raw_replay_20261015_v2/models/aligned_force'
    inputs = [args.manifest, Path(__file__), tool / 'produce_external_transfer.py',
        tool / 'metis_numeric_profile.py', frozen, base / 'cache_map.json', *required]
    inputs += [source / f'seed{s}/best_model.pt' for s in range(201, 206)]
    inputs += [base / f'{farm}/seed{s}/output_manifest.json' for farm in ('kelmarsh', 'penmanshiel') for s in range(201, 206)]
    run_command(base, name, [sys.executable, '-u', str(tool / 'produce_external_transfer.py'),
        '--source-pattern', str(source / 'seed{seed}'), '--forecast-pattern', str(base / '{farm}/seed{seed}'),
        '--cache-map', str(base / 'cache_map.json'), '--output-dir', str(output),
        '--seeds', '201,202,203,204,205', '--bootstrap', '5000', '--random-seed', '20261014'],
        inputs, [output / x for x in ['exp01_pitchmasked_v3_seed_results.csv',
            'exp01_pitchmasked_v3_joint_statistics.csv', 'exp01_native_day_blocks_v4.npz',
            'numeric_execution_profile.json', 'output_manifest.json']],
        {'WINDFARM_REPO_ROOT': str(root), 'CUBLAS_WORKSPACE_CONFIG': ':4096:8'})


if __name__ == '__main__':
    main()
