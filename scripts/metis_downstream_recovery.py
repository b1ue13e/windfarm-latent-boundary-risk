"""Unique PBS attempts for registered downstream recovery; no science certificate."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, allow_nan=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--tool', type=Path, required=True)
    p.add_argument('--mode', choices=['preflight', 'worker', 'payload', 'aggregate'], required=True)
    p.add_argument('--stage', choices=['phase', 'supervision', 'active_power'])
    p.add_argument('--seed', type=int, choices=range(201, 206))
    a = p.parse_args()
    root, tool = a.root.resolve(), a.tool.resolve()
    if not tool.is_relative_to(root / 'metis_execution') or not os.environ.get('PBS_JOBID'):
        raise RuntimeError('Use an isolated tool in an actual PBS allocation')
    os.environ['WINDFARM_REPO_ROOT'] = str(root)
    sys.path[:0] = [str(tool), str(root / 'scripts'), str(root)]
    os.chdir(root)
    from scripts.replay_provenance import file_record, finalize
    from scripts.raw_replay import verify_run_receipt, run_command
    manifest_path = tool / 'manifest.json'
    manifest = read(manifest_path)
    for row in manifest['files']:
        if digest(tool / row['name']) != row['sha256']:
            raise ValueError('Tool package changed: ' + row['name'])
    for row in manifest['frozen_files']:
        if digest(root / row['relative_path']) != row['sha256']:
            raise ValueError('Frozen dependency changed: ' + row['relative_path'])
    base = root / 'artifacts/raw_replay_20261015_v2'
    out = (base / manifest['output_name']).resolve()
    if out == base or not out.is_relative_to(base):
        raise ValueError('New outputs must stay inside the isolated raw replay')
    cache, res = base / 'cache_wtb', base / 'fixed_forecast_residuals.npz'
    checked = {}

    def check(rows):
        for row in rows:
            f = Path(row['path']); st = f.stat()
            key = (str(f), st.st_size, st.st_mtime_ns, row['sha256'])
            if key in checked:
                continue
            if st.st_size != row['bytes'] or digest(f) != row['sha256']:
                raise ValueError('Input/output hash differs: ' + str(f))
            if (st.st_size, st.st_mtime_ns) != (f.stat().st_size, f.stat().st_mtime_ns):
                raise ValueError('File changed during verification')
            checked[key] = True

    def success(path):
        r = verify_run_receipt(path)
        if r.get('exit_code') != 0 or not r.get('inputs') or not r.get('outputs') or r.get('missing_outputs'):
            raise ValueError('Real exit0/nonempty complete receipt required')
        return r

    label = a.mode if a.mode in ('preflight', 'aggregate') else a.stage + ('_' + str(a.seed) if a.stage == 'phase' else '')
    if a.mode != 'payload':
        before = tool / ('pbs_' + label + '.json')
        cp = subprocess.run(['/opt/pbs/bin/qstat', '-f', '-F', 'json', os.environ['PBS_JOBID']], capture_output=True)
        with before.open('xb') as f: f.write(cp.stdout)
        with before.with_suffix('.stderr').open('xb') as f: f.write(cp.stderr)
        cp.check_returncode()
        job = json.loads(cp.stdout)['Jobs'][os.environ['PBS_JOBID']]
        if job.get('job_state') != 'R' or not job.get('Job_Owner', '').startswith('junyu@'):
            raise ValueError('Wrong actual PBS execution identity')
    if a.mode == 'preflight':
        if out.exists():
            raise FileExistsError('New campaign output already exists')
        from metis_numeric_profile import configure
        profile = configure()
        # Execute the already reviewed full model artifact auditor in this allocation.
        subprocess.run([sys.executable, str(tool / 'audit_metis_fit_outputs.py'), '--workspace', str(root),
                        '--output-dir', str(tool / 'model_input_audit'), '--mode', 'completed'], check=True)
        audit = read(tool / 'model_input_audit/report.json')
        if len(audit['results']) != 45 or audit['pending'] or audit['failures']:
            raise ValueError('All real complete model artifacts required')
        receipt = success(base / 'execution/fixed_residuals/record.json')
        check(read(res.with_suffix('.evidence') / 'output_manifest.json'))
        check(read(base / 'cache_manifest.json'))
        from windfarm_moe.data import load_cache_bundle, RegimeWindowDataset
        from masked_representation import check_frozen_reference
        import numpy as np
        bundle = load_cache_bundle(cache, mmap_mode='r')
        with np.load(res) as f:
            for split in ('val', 'test'):
                anchors = RegimeWindowDataset(bundle, split, bundle.metadata['hist_len'], bundle.metadata['pred_len']).anchor_indices
                check_frozen_reference(bundle, f, split, anchors)
                for seed in range(201, 206):
                    mask = f['mask_' + split] > .5
                    pred, target, short = f[f'yhat_{split}_seed{seed}'], f['ytrue_' + split], f[f'shortfall_{split}_seed{seed}']
                    if not np.isfinite(short[mask]).all() or not np.array_equal(short, np.maximum(pred-target, 0.) * f['mask_' + split], equal_nan=True):
                        raise ValueError('Invalid canonical residual identity')
        test_env = dict(os.environ, PHASE_GUARD_SOURCE=str(tool/'eval_single_task_dense_phase_scan.py'))
        subprocess.run([sys.executable, '-m', 'pytest', str(tool / 'test_phase_head_target_guard.py'), '-q'], check=True, env=test_env)
        phase = runpy.run_path(str(tool / 'eval_single_task_dense_phase_scan.py'), run_name='phase_import_smoke')
        fail = base / 'dense_phase_scan/execution_arrays'
        with np.load(fail / 'seed201_head_moe_h1/training_targets.npz') as x, np.load(fail / 'seed201_head_dense_h1/training_targets.npz') as y:
            diagnosis = phase['assert_matched_head_training'](x, y)
        # Actual imports, not only compilation, catch isolated deployment failures.
        for script in ('run_clean_privileged_supervision_ablation.py', 'run_active_power_anchor_audit.py'):
            runpy.run_path(str(root / 'scripts' / script), run_name='downstream_import_smoke')
        inputs = [res, base/'cache_manifest.json', base/'frozen_protocol.json', root/'metis_input_manifest.json',
                  *sorted(cache.glob('*.npy')), cache/'metadata.json',
                  fail/'seed201_head_moe_h1/training_targets.npz',
                  fail/'seed201_head_dense_h1/training_targets.npz',
                  base/'execution/dense_phase_scan/record.json']
        for family in ('forecast', 'dense', 'aligned', 'unaligned'):
            for seed in range(201, 206):
                path = base / f'execution/train_{family}_{seed}/record.json'
                r = success(path)
                check(read(base / f'models/{family}/seed{seed}/output_manifest.json'))
                inputs += [path, base/f'models/{family}/seed{seed}/best_model.pt', base/f'models/{family}/seed{seed}/output_manifest.json']
        # Integrity only: preserve all completed core evidence; numerical audit is separate.
        completed = []
        for name, directory in [('channels','channels/evidence'), ('exp02','exp02'), ('exp03','exp03'),
                                ('run_matched_budget_frontier','matched_budget'), ('run_rho_sensitivity','matched_budget')]:
            r = success(base/f'execution/{name}/record.json')
            manifests = list((base/directory).rglob('output_manifest.json'))
            for m in manifests: check(read(m))
            completed.append(dict(name=name, receipt=file_record(base/f'execution/{name}/record.json'), deep_manifests=len(manifests)))
        save(tool/'preflight_report.json', dict(status='INPUTS_AND_SOFTWARE_VERIFIED', pbs_job_id=os.environ['PBS_JOBID'],
             manifest=file_record(manifest_path), inputs=[file_record(x) for x in inputs],
             model_audit=file_record(tool/'model_input_audit/report.json'), failed_target_diagnosis=diagnosis,
             numeric_profile=profile, completed_core_integrity=completed, scientific_completion=False))
        return
    preflight = read(tool / 'preflight_report.json')
    if preflight.get('status') != 'INPUTS_AND_SOFTWARE_VERIFIED' or preflight['manifest']['sha256'] != digest(manifest_path):
        raise ValueError('Matching successful preflight report required')
    if a.mode != 'payload':
        cp = subprocess.run(['/opt/pbs/bin/qstat', '-x', '-f', '-F', 'json', preflight['pbs_job_id']], capture_output=True)
        with (tool/f'preflight_pbs_{label}.stdout').open('xb') as f: f.write(cp.stdout)
        with (tool/f'preflight_pbs_{label}.stderr').open('xb') as f: f.write(cp.stderr)
        cp.check_returncode(); job = json.loads(cp.stdout)['Jobs'][preflight['pbs_job_id']]
        if job.get('job_state') != 'F' or job.get('Exit_status') != 0 or job.get('Job_Name') != 'p3_down_check' or not job.get('Job_Owner','').startswith('junyu@'):
            raise ValueError('Actual matching preflight F/exit0 required')
    check(preflight['inputs'])
    if a.mode == 'aggregate':
        import pandas as pd
        frames, abstentions, receipts = [], [], []
        for seed in range(201, 206):
            receipt_path=base/f'execution/downstream_v1_phase_{seed}/record.json'
            r=success(receipt_path);check(read(out/f'phase/seed{seed}/output_manifest.json'))
            f=pd.read_csv(out/f'phase/seed{seed}/phase_scan_results_by_seed.csv')
            expected={(lead,lag,ch) for lead in (0,2,5) for lag in (0,1,2,3,6) for ch in ('all','no_pitch')}
            if len(f)!=30 or set(f.seed)!={seed} or set(zip(f.lead_step,f.lag_steps,f.channel_mode))!=expected:
                raise ValueError('All original phase conditions required for each seed')
            z=pd.read_csv(out/f'phase/seed{seed}/phase_scan_risk_coverage_by_seed.csv')
            wanted={(ch,model,c) for ch in ('all','no_pitch') for model in ('Joint Routed','Frozen Backbone (MoE)','Single-Task Dense Backbone') for c in (.5,.6,.7,.8,.9,.95,1.)}
            if len(z)!=42 or set(z.seed)!={seed} or set(zip(z.channel_mode,z.model,z.coverage))!=wanted or set(z.lead_step)!={0} or set(z.lag_steps)!={6}:
                raise ValueError('All original abstention conditions required')
            frames.append(f);abstentions.append(z);receipts.append(file_record(receipt_path))
        destination=out/'phase_aggregate';destination.mkdir(parents=True,exist_ok=False)
        pd.concat(frames,ignore_index=True).to_csv(destination/'phase_scan_results_by_seed.csv',index=False)
        pd.concat(abstentions,ignore_index=True).to_csv(destination/'phase_scan_risk_coverage_by_seed.csv',index=False)
        save(destination/'aggregation_receipt.json',dict(pbs_job_id=os.environ['PBS_JOBID'],inputs=receipts,
             rows=150,abstention_rows=210,status='EXECUTED_PENDING_NUMERICAL_AUDIT',scientific_completion=False))
        finalize(destination)
        return
    if a.stage is None or (a.stage=='phase' and a.seed is None):
        raise ValueError('A registered independent stage/seed is required')
    destination = out / ('phase/seed'+str(a.seed) if a.stage=='phase' else a.stage)
    if a.mode=='worker':
        if destination.exists() or (base/f'execution/downstream_v1_{label}').exists():
            raise FileExistsError('Never overwrite a started attempt')
        argv=[sys.executable,'-u',str(tool/Path(__file__).name),'--root',str(root),'--tool',str(tool),
              '--mode','payload','--stage',a.stage]
        if a.seed is not None: argv+=['--seed',str(a.seed)]
        expected = ([destination/'phase_scan_results_by_seed.csv', destination/'phase_scan_risk_coverage_by_seed.csv']
                    if a.stage=='phase' else [destination/'results.csv',destination/'report.md'])
        run_command(base,'downstream_v1_'+label,argv,
                    [manifest_path,tool/'preflight_report.json',*[tool/x['name'] for x in manifest['files']],
                     *[Path(r['path']) for r in preflight['inputs']]],
                    [destination/'output_manifest.json',destination/'numeric_execution_profile.json',*expected])
        return
    from metis_numeric_profile import configure
    profile=configure()
    destination.mkdir(parents=True,exist_ok=False)
    save(destination/'numeric_execution_profile.json',profile)
    if a.stage=='phase':
        script=tool/'eval_single_task_dense_phase_scan.py'
        extra=['--seeds',str(a.seed),'--routed-pat',str(base/'models/forecast/seed{seed}'),
               '--dense-pat',str(base/'models/dense/seed{seed}'),'--output-dir',str(destination),
               '--frozen-residuals',str(res)]
    else:
        script=root/'scripts'/('run_clean_privileged_supervision_ablation.py' if a.stage=='supervision' else 'run_active_power_anchor_audit.py')
        extra=['--residuals-file',str(res),'--output-csv',str(destination/'results.csv'),'--output-md',str(destination/'report.md')]
        if a.stage=='supervision':
            extra+=['--unaligned-pattern',str(base/'models/unaligned/seed{seed}'),'--aligned-pattern',str(base/'models/aligned/seed{seed}')]
    sys.argv=[str(script),'--cache-dir',str(cache),*extra]
    runpy.run_path(str(script),run_name='__main__')
    finalize(destination)


if __name__=='__main__': main()
