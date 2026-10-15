"""Versioned recovery outside the frozen Metis runtime; never certifies science."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--mode', choices=['preflight', 'core'], required=True)
    args = parser.parse_args()
    root = args.workspace.resolve()
    tool = args.manifest.resolve().parent
    if not os.environ.get('PBS_JOBID'):
        raise RuntimeError('Recovery checks/computation require a PBS allocation')
    manifest = json.loads(args.manifest.read_text())
    for row in manifest['files']:
        if digest(tool / row['name']) != row['sha256']:
            raise ValueError('Recovery tool hash differs: ' + row['name'])
    frozen_manifest = root / 'metis_input_manifest.json'
    if digest(frozen_manifest) != manifest['frozen_input_manifest_sha256']:
        raise ValueError('Frozen input manifest changed')
    for row in json.loads(frozen_manifest.read_text()):
        if digest(root / row['relative_path']) != row['sha256']:
            raise ValueError('Frozen input/source changed: ' + row['relative_path'])
    original = (root / 'scripts/test_strong_baseline_closure.py').read_text()
    patched = (tool / 'test_strong_baseline_closure.py').read_text()
    if patched.replace('import json\n', '', 1) != original:
        raise ValueError('Correction must be exactly one missing json import')
    os.environ['WINDFARM_REPO_ROOT'] = str(root)
    sys.path[:0] = [str(root / 'scripts'), str(root)]
    spec = importlib.util.spec_from_file_location('recovered_strong_baseline',
                                                 tool / 'test_strong_baseline_closure.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.json.loads(module.json.dumps({'serialization': True})) != {'serialization': True}:
        raise ValueError('Missing-import serialization regression')
    from raw_replay import verify_records, verify_run_receipt, run_command
    from replay_provenance import write_json, file_record
    base = root / 'artifacts/raw_replay_20261015_v2'
    def require_success(path):
        record = json.loads(path.read_text())
        if (record.get('status') != 'EXECUTED' or record.get('exit_code') != 0 or
            not record.get('inputs') or not record.get('outputs') or record.get('missing_outputs')):
            raise ValueError('Incomplete successful execution evidence: ' + str(path))
        verify_run_receipt(path)
    require_success(base / 'execution/fixed_residuals/record.json')
    ready = root / 'metis_execution/fit_audits/factorial_readiness_attempt2/report.json'
    readiness = json.loads(ready.read_text())
    if (digest(ready) != manifest['readiness_report_sha256'] or
        readiness['readiness'] != 'INPUTS_VERIFIED' or readiness['pending'] or
        readiness['failures'] or len(readiness['results']) != 20 or not readiness['canonical']):
        raise ValueError('Dedicated readiness evidence differs')
    # Retain and deeply verify the four real completed runs. They are not rerun.
    import pandas as pd
    import numpy as np
    extension = root / 'metis_execution/extensions/factorial_four_conditions_v2_attempt1'
    if digest(extension / 'extension_manifest.json') != manifest['original_extension_manifest_sha256']:
        raise ValueError('Original factorial manifest identity differs')
    ext_manifest = json.loads((extension / 'extension_manifest.json').read_text())
    for row in ext_manifest['files']:
        if digest(extension / row['name']) != row['sha256']:
            raise ValueError('Original factorial extension changed')
    for row in ext_manifest['frozen_files']:
        if digest(root / row['relative_path']) != row['sha256']:
            raise ValueError('Original factorial frozen dependency changed')
    sys.path.insert(0, str(extension))
    from replay_factorial_four_conditions import VARIANTS
    factorial = base / 'factorial_four_conditions_v2'
    complete = []
    for seed in range(201, 205):
        receipt = factorial / f'execution/clean_{seed}/record.json'
        require_success(receipt)
        output = factorial / f'clean/seed{seed}'
        verify_records(json.loads((output / 'output_manifest.json').read_text()))
        frame = pd.read_csv(output / 'seed_results.csv')
        expected = {(h, pop, variant) for h in (1, 6)
                    for pop in ('Full', 'Boundary') for variant in VARIANTS}
        actual = set(zip(frame.horizon, frame.population, frame.variant))
        if (len(frame) != 44 or actual != expected or set(frame.seed) != {seed} or
            set(frame.condition) != {'clean'} or
            not np.isfinite(frame[['psrei_kwh', 'reserve_kwh', 'shortage_kwh',
                                  'violation_rate']].to_numpy()).all()):
            raise ValueError('Incomplete/nonfinite completed clean cells')
        complete.append(file_record(receipt))
    if args.mode == 'preflight':
        for index in range(4, 20):
            condition = ('clean', 'delay6', 'pitch_withheld', 'delay6_pitch_withheld')[index // 5]
            seed = 201 + index % 5
            if (factorial / f'execution/{condition}_{seed}').exists() or (factorial / condition / f'seed{seed}').exists():
                raise FileExistsError('Do not overwrite a started/completed factorial attempt')
        report = tool / 'preflight_report.json'
        if report.exists():
            raise FileExistsError(report)
        accounting = []
        for label, argv in [('array', ['/opt/pbs/bin/tracejob', '-n', '1', '242602[].cm']),
                            ('child', ['/opt/pbs/bin/tracejob', '-n', '1', '242602[0].cm'])]:
            result = subprocess.run(argv, capture_output=True)
            streams = []
            for suffix, data in [('stdout', result.stdout), ('stderr', result.stderr)]:
                path = tool / f'tracejob_{label}.{suffix}'
                with path.open('xb') as stream:
                    stream.write(data)
                streams.append(file_record(path))
            accounting.append({'argv': argv, 'exit_code': result.returncode,
                               'streams': streams, 'cause': 'UNKNOWN; no inferred termination cause'})
        write_json(report, {'pbs_job_id': os.environ['PBS_JOBID'],
            'status': 'SOFTWARE_AND_REQUEUE_INPUTS_VERIFIED', 'completed_clean': complete,
            'unexecuted_indices': list(range(4, 20)), 'readiness_report': file_record(ready),
            'manifest': file_record(args.manifest), 'scheduler_accounting': accounting,
            'scientific_completion': False})
        print('IMPORT_SERIALIZATION_AND_EXISTING_FOUR_RUNS_PASS', flush=True)
        return
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('Core recovery requires an allocated GPU')
    preflight_path = tool / 'preflight_report.json'
    preflight = json.loads(preflight_path.read_text())
    if (preflight.get('status') != 'SOFTWARE_AND_REQUEUE_INPUTS_VERIFIED' or
        preflight.get('manifest', {}).get('sha256') != digest(args.manifest)):
        raise ValueError('Successful matching recovery preflight report required')
    command = ['/opt/pbs/bin/qstat', '-x', '-f', '-F', 'json', preflight['pbs_job_id']]
    check = subprocess.run(command, capture_output=True)
    for suffix, data in [('stdout', check.stdout), ('stderr', check.stderr)]:
        with (tool / f'core_preflight_pbs.{suffix}').open('xb') as stream:
            stream.write(data)
    job = json.loads(check.stdout).get('Jobs', {}).get(preflight['pbs_job_id'], {}) if check.returncode == 0 else {}
    if (job.get('job_state') != 'F' or job.get('Exit_status') != 0 or
        job.get('Job_Name') != 'p3_rec_check' or not job.get('Job_Owner', '').startswith('junyu@')):
        raise ValueError('Matching real PBS preflight exit0 required')
    for family in ('forecast', 'aligned_force', 'unaligned', 'aligned', 'dense_classifier', 'dense'):
        for seed in range(201, 206):
            require_success(base / f'execution/train_{family}_{seed}/record.json')
    cache = base / 'cache_wtb'
    residual = base / 'fixed_forecast_residuals.npz'
    inputs = [args.manifest, Path(__file__), residual, base / 'cache_manifest.json',
              *sorted(cache.glob('*.npy')), cache / 'metadata.json',
              *[base / f'models/dense_classifier/seed{s}/best_model.pt' for s in range(201, 206)]]
    destination = base / 'strong_baseline_retry_import_v1'
    if destination.exists():
        raise FileExistsError('Preserve existing retry output: ' + str(destination))
    run_command(base, 'strong_baseline_retry_import_v1',
        [sys.executable, str(tool / 'test_strong_baseline_closure.py'), '--cache-dir', str(cache),
         '--residuals-file', str(residual), '--runs-pattern', str(base / 'models/dense_classifier/seed{seed}')],
        [*inputs, tool / 'test_strong_baseline_closure.py'],
        [destination / 'strong_baseline_closure_summary.csv',
         destination / 'strong_baseline_joint_interaction_v2.json', destination / 'evidence/output_manifest.json'],
        {'STRONG_BASELINE_OUTPUT_DIR': str(destination), 'WINDFARM_REPO_ROOT': str(root)})
    for name, script, extra, expected in [
        ('channels', 'run_channel_consequence_ablations.py',
         ['--output-csv', str(base / 'channels/summary.csv')], base / 'channels/summary.csv'),
        ('exp02', 'run_exp02_zero_privileged_supervision.py',
         ['--oracle-pattern', str(base / 'models/aligned/seed{seed}'), '--archive-dir', str(base / 'exp02/runs'),
          '--output-csv', str(base / 'exp02/results.csv'), '--output-report', str(base / 'exp02/report.md'),
          '--output-blocks', str(base / 'exp02/day_blocks.npz')], base / 'exp02/results.csv'),
        ('exp03', 'run_exp03_async_benchmark.py',
         ['--output-dir', str(base / 'exp03'), '--output-report', str(base / 'exp03/report.md')],
         base / 'exp03/psrei_vs_delay.csv')]:
        run_command(base, name, [sys.executable, f'scripts/{script}', '--cache-dir', str(cache),
            '--residuals-file', str(residual), *extra], inputs, [expected])


if __name__ == '__main__':
    main()
