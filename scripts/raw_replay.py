"""Versioned raw-data replay. Never silently substitutes historical trained weights.

freeze captures historical CONFIGURATIONS only; run starts all models from scratch.
Coverage and execution completion are deliberately distinct from claim withdrawal.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from replay_provenance import file_record, write_json, sha256, finalize, provenance

FAMILIES = {
    'forecast': 'artifacts/trainweight_full_rerun_20260830/wtb_full_seed{seed}',
    'aligned_force': 'artifacts/strictmask_ablation_rerun_wtb_full/wtb_bal_align_force_seed{seed}',
    'unaligned': 'artifacts/strictmask_ablation_rerun_wtb_full/wtb_bal_seed{seed}',
    'aligned': 'artifacts/strictmask_ablation_rerun_wtb_full/wtb_bal_align_seed{seed}',
    'dense_classifier': 'artifacts/dense_classifier_runs_20260904/canonical/wtb_bal_align_force_seed{seed}',
    'dense': 'artifacts/capacity_matched_dense_wtb/wtb_dense_seed{seed}',
}


def now():
    return datetime.now(timezone.utc).isoformat()


def verify_records(records):
    for r in records:
        if not Path(r['path']).is_file() or sha256(r['path']) != r['sha256']:
            raise ValueError(f"Evidence changed or missing: {r['path']}")


def verify_run_receipt(receipt):
    previous=json.loads(Path(receipt).read_text(encoding='utf-8'))
    if previous['status'] != 'EXECUTED':
        raise RuntimeError('Incomplete or failed run cannot be resumed as complete')
    verify_records(previous['inputs'])
    verify_records(previous['outputs'])
    for record in previous['outputs']:
        if Path(record['path']).name == 'output_manifest.json':
            verify_records(json.loads(Path(record['path']).read_text(encoding='utf-8')))
    for rel,digest in previous['source_sha256'].items():
        if sha256(ROOT/rel) != digest:
            raise ValueError(f'Source differs from completed run: {rel}; explicit versioned replay required')
    return previous


def freeze(out):
    import torch
    if (out / 'frozen_protocol.json').exists():
        raise FileExistsError('Frozen protocol already exists; do not refreeze after observing results')
    out.mkdir(parents=True, exist_ok=True)
    config_path = ROOT/'experiments/replay_20261015/frozen_wtb_configs.json'
    configs = json.loads(config_path.read_text(encoding='utf-8'))['configs']
    if {(c['family'], c['seed']) for c in configs} != {(f,s) for f in FAMILIES for s in range(201,206)}:
        raise ValueError('Frozen config coverage is not the registered 6 families x 5 seeds')
    for c in configs:
        if c['seed'] != c['train_config']['seed']:
            raise ValueError('Config seed mismatch')
    raw = [ROOT / 'wtbdata_245days.csv', ROOT / 'sdwpf_baidukddcup2022_turb_location.CSV']
    record = {'registered_utc': now(), 'seeds': list(range(201,206)), 'configs': configs,
              'raw_wtb': [file_record(p) for p in raw],
              'protocol': file_record(ROOT / 'docs/RAW_REPLAY_PROTOCOL_20261015.md'),
              'config_source': file_record(config_path),
              'historical_equality': 'exact masks/labels/targets; report feature differences without fitted tolerance',
              'scientific_success': 'not determined by favorable sign or matching historical numbers'}
    write_json(out / 'frozen_protocol.json', record)
    (out / 'environment.txt').write_text(subprocess.check_output(
        [sys.executable, '-m', 'pip', 'freeze'], text=True), encoding='utf-8')
    write_json(out / 'runtime.json', {'python': sys.version, 'torch': torch.__version__,
                                     'cuda': torch.version.cuda,
                                     'device': torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu'})
    original = json.loads((ROOT / 'artifacts/ARTIFACT_MANIFEST.json').read_text(encoding='utf-8-sig'))
    write_json(out / 'coverage.json', [{'historical_artifact': x['filename'],
                                      'claims': x.get('manuscript_claims_supported', []),
                                      'execution_status': 'NOT_RUN', 'claim_disposition': 'PENDING',
                                      'generating_script': x.get('generating_script'),
                                      'upstream_inputs': x.get('upstream_inputs', [])} for x in original])
    print('FROZEN_CONFIGS', len(configs), flush=True)


def run_command(out, name, argv, inputs, outputs, env_extra=None):
    logdir = out / 'execution' / name
    if logdir.exists():
        raise FileExistsError(f'Run exists; inspect its evidence instead of overwriting: {logdir}')
    logdir.mkdir(parents=True)
    commit = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    source = {str(p.relative_to(ROOT)): sha256(p) for folder in ['scripts','windfarm_moe']
              for p in (ROOT/folder).rglob('*.py')}
    record = {'name':name, 'argv':argv, 'start_utc':now(), 'git_commit':commit,
              'source_sha256':source, 'inputs':[file_record(p) for p in inputs], 'status':'RUNNING'}
    record['environment_overrides'] = dict(env_extra or {})
    record['execution_environment'] = {key:os.environ.get(key) for key in
        ('CUDA_VISIBLE_DEVICES','CUBLAS_WORKSPACE_CONFIG','PYTHONHASHSEED')}
    record['thread_limits'] = {'OMP_NUM_THREADS':'4','MKL_NUM_THREADS':'4'}
    write_json(logdir / 'record.json', record)
    env = os.environ.copy()
    env.update({'PYTHONUNBUFFERED':'1','OMP_NUM_THREADS':'4','MKL_NUM_THREADS':'4'})
    env.update(env_extra or {})
    with (logdir/'stdout_stderr.log').open('w', encoding='utf-8') as f:
        cp = subprocess.run(argv, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, env=env)
    record.update(end_utc=now(), exit_code=cp.returncode, status='FAILED' if cp.returncode else 'EXECUTED')
    record['outputs'] = [file_record(p) for p in outputs if Path(p).is_file()]
    record['missing_outputs'] = [str(p) for p in outputs if not Path(p).is_file()]
    if record['missing_outputs']:
        record['status'] = 'FAILED'
    write_json(logdir/'record.json', record)
    print(name, record['status'], 'exit', cp.returncode, flush=True)
    if record['status'] != 'EXECUTED':
        raise RuntimeError(f'{name} failed; inspect {logdir}')


def prepare(out):
    import numpy as np
    frozen = json.loads((out/'frozen_protocol.json').read_text(encoding='utf-8'))
    for r in frozen['raw_wtb']:
        if sha256(r['path']) != r['sha256']:
            raise ValueError('Raw data changed after freeze')
    raw = out/'cache_raw_recorded'/'wtb_245d'
    if raw.exists():
        raise FileExistsError('Fresh raw preprocessing requires a new empty cache path')
    run_command(out, 'preprocess_wtb', [sys.executable,'main.py','preprocess','--root-dir',str(ROOT),
                '--dataset','wtb','--cache-root',str(raw.parent)],
                [r['path'] for r in frozen['raw_wtb']], [raw/'metadata.json'])
    # Current preprocessing already enforces strict masks. Do not alter frozen labels.
    run_command(out, 'train_only_weights', [sys.executable,'scripts/build_train_weight_cache.py',
                '--source-cache',str(raw),'--target-cache',str(out/'cache_wtb')],
                [raw/'metadata.json'], [out/'cache_wtb'/'metadata.json'])
    reference = ROOT/'artifacts/cache_strictmask_trainweights/wtb_245d'
    comparison = []
    for p in sorted((out/'cache_wtb').glob('*.npy')):
        q = reference/p.name
        if not q.exists():
            comparison.append({'file':p.name,'historical':'MISSING'})
            continue
        a,b = np.load(p,mmap_mode='r'),np.load(q,mmap_mode='r')
        equal = a.shape == b.shape and np.array_equal(a,b,equal_nan=True)
        comparison.append({'file':p.name,'exact_equal':bool(equal),'new':file_record(p),'old':file_record(q)})
    write_json(out/'preprocessing_comparison.json', comparison)
    write_json(out/'cache_manifest.json', [file_record(p) for p in sorted((out/'cache_wtb').iterdir()) if p.is_file()])
    mandatory = ['target.npy','target_mask.npy','regime_primary.npy','regime_primary_valid.npy','time_index.npy']
    if any(not x.get('exact_equal',False) for x in comparison if x['file'] in mandatory):
        raise RuntimeError('Frozen target/population/label changed; training stopped')
    print('TARGET_MASK_LABEL_EXACT; inspect feature floating-point differences separately', flush=True)


def train_one(out, family, seed):
    import torch
    from windfarm_moe.config import ModelConfig, TrainConfig, EvalConfig
    from windfarm_moe.data import load_cache_bundle
    from windfarm_moe.train import train_model
    frozen = json.loads((out/'frozen_protocol.json').read_text(encoding='utf-8'))
    cfg = next(x for x in frozen['configs'] if x['family']==family and x['seed']==seed)
    target = out/'models'/family/f'seed{seed}'
    if target.exists():
        raise FileExistsError(f'Cannot overwrite training: {target}')
    cache_records=json.loads((out/'cache_manifest.json').read_text(encoding='utf-8'))
    verify_records(cache_records)
    provenance(target, [out/'frozen_protocol.json', out/'cache_manifest.json',
                        *[r['path'] for r in cache_records]],
               {'family':family,'seed':seed,'model_config':cfg['model_config'],'train_config':cfg['train_config']})
    bundle = load_cache_bundle(out/'cache_wtb', mmap_mode='r')
    if cfg['train_config'].get('limit_train_batches') is not None or cfg['train_config'].get('limit_val_batches') is not None:
        raise ValueError('Partial batch training cannot serve as full replay')
    train_model(bundle,target,ModelConfig(**cfg['model_config']),TrainConfig(**cfg['train_config']),
                EvalConfig(skip_visuals=True,save_predictions=True))
    finalize(target)


def run_wtb(out):
    frozen=json.loads((out/'frozen_protocol.json').read_text(encoding='utf-8'))
    cache=out/'cache_wtb'
    if not cache.exists():
        prepare(out)
    for cfg in frozen['configs']:
        family,seed=cfg['family'],cfg['seed']
        name=f'train_{family}_{seed}'
        receipt=out/'execution'/name/'record.json'
        if receipt.exists():
            verify_run_receipt(receipt)
            print('VERIFIED_RESUME',name,flush=True)
            continue
        target=out/'models'/family/f'seed{seed}'
        run_command(out,name,[sys.executable,'-u',__file__,'train-one','--output-dir',str(out),
                    '--family',family,'--seed',str(seed)],
                    [out/'frozen_protocol.json',out/'cache_manifest.json',
                     *sorted(cache.glob('*.npy')),cache/'metadata.json'],
                    [target/'best_model.pt',target/'training_summary.json',target/'output_manifest.json'])
    evaluate_wtb(out)


def evaluate_wtb(out):
    cache=out/'cache_wtb'
    for family in FAMILIES:
        for seed in range(201,206):
            verify_run_receipt(out/'execution'/f'train_{family}_{seed}'/'record.json')
    residual=out/'fixed_forecast_residuals.npz'
    run_command(out,'fixed_residuals',[sys.executable,'scripts/build_fixed_forecast_residuals.py',
                '--cache-dir',str(cache),'--runs-pattern',str(out/'models/forecast/seed{seed}'),
                '--output-file',str(residual)], [out/'frozen_protocol.json'],[residual])
    run_command(out,'strong_baseline',[sys.executable,'scripts/test_strong_baseline_closure.py',
                '--cache-dir',str(cache),'--residuals-file',str(residual),
                '--runs-pattern',str(out/'models/dense_classifier/seed{seed}')],
                [residual], [out/'strong_baseline/strong_baseline_closure_summary.csv'],
                {'STRONG_BASELINE_OUTPUT_DIR':str(out/'strong_baseline')})
    for name,script,extra,expected in [
        ('channels','run_channel_consequence_ablations.py',['--output-csv',str(out/'channels/summary.csv')],out/'channels/summary.csv'),
        ('exp02','run_exp02_zero_privileged_supervision.py',[
            '--oracle-pattern',str(out/'models/aligned/seed{seed}'), '--archive-dir',str(out/'exp02/runs'),
            '--output-csv',str(out/'exp02/results.csv'),'--output-report',str(out/'exp02/report.md'),
            '--output-blocks',str(out/'exp02/day_blocks.npz')],out/'exp02/results.csv'),
        ('exp03','run_exp03_async_benchmark.py',['--output-dir',str(out/'exp03'),
            '--output-report',str(out/'exp03/report.md')],out/'exp03/psrei_vs_delay.csv')]:
        run_command(out,name,[sys.executable,f'scripts/{script}','--cache-dir',str(cache),
                    '--residuals-file',str(residual),*extra],[residual],[expected])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['freeze','prepare-wtb','train-one','run-wtb'])
    p.add_argument('--output-dir',type=Path,default=ROOT/'artifacts/raw_replay_20261015_v2')
    p.add_argument('--family',choices=list(FAMILIES))
    p.add_argument('--seed',type=int)
    a=p.parse_args(); out=a.output_dir.resolve()
    if not out.is_relative_to(ROOT/'artifacts'):
        raise ValueError('Replay output must stay inside repository artifacts')
    if a.action=='freeze':freeze(out)
    elif a.action=='prepare-wtb':prepare(out)
    elif a.action=='train-one':train_one(out,a.family,a.seed)
    else:run_wtb(out)


if __name__=='__main__':
    main()
