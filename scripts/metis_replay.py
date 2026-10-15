"""PBS stage entry points for an isolated raw replay; never certifies completion."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from raw_replay import FAMILIES,freeze,prepare,evaluate_wtb,run_command,verify_run_receipt
from replay_provenance import write_json,sha256


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['wtb-prepare','wtb-fit','wtb-core','diagnostics',
        'external-prepare','external-fit','external-transfer'])
    p.add_argument('--index',type=int,default=None)
    a=p.parse_args()
    os.environ['RAW_REPLAY_EXTERNAL_CACHE_MAP']=str(ROOT/'metis_cache_map.json')
    out=ROOT/'artifacts/raw_replay_20261015_v2'
    ext=ROOT/'artifacts/raw_replay_external_models_20261015'
    expected=json.loads((ROOT/'metis_input_manifest.json').read_text(encoding='utf-8'))
    for r in expected:
        if r['relative_path'].startswith('data/external_wind/') and not a.stage.startswith('external-'):
            continue
        if sha256(ROOT/r['relative_path'])!=r['sha256']:
            raise ValueError('Deployment/raw input hash mismatch: '+r['relative_path'])
    task=f'{a.stage}_{a.index}' if a.index is not None else a.stage
    import torch
    write_json(ROOT/'metis_execution'/f'{task}_runtime.json',{
        'hostname':platform.node(),'python':sys.version,'torch':torch.__version__,
        'cuda':torch.version.cuda,'cuda_available':torch.cuda.is_available(),
        'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        'pbs_job_id':os.environ.get('PBS_JOBID'),'pbs_array_index':os.environ.get('PBS_ARRAY_INDEX')})
    if a.stage not in ('wtb-prepare','external-prepare') and not torch.cuda.is_available():
        raise RuntimeError('GPU stage must run in a real allocated CUDA environment')
    if a.stage=='wtb-prepare':
        subprocess.run([sys.executable,'-m','pytest','tests/test_replay_integrity.py',
            'tests/test_external_wind.py','tests/test_exp02_protocol.py',
            'tests/test_exp03_async_arrival.py','tests/test_f4_verdict_regression.py',
            'tests/test_f4_hierarchical_bootstrap.py','-q'],cwd=ROOT,check=True)
        freeze(out)
        write_json(out/'historical_ARTIFACT_MANIFEST.json',json.loads(
            (ROOT/'artifacts/ARTIFACT_MANIFEST.json').read_text(encoding='utf-8-sig')))
        prepare(out)
    elif a.stage=='wtb-fit':
        if a.index is None or not 0<=a.index<30:raise ValueError('Expected array index0..29')
        cfg=json.loads((out/'frozen_protocol.json').read_text(encoding='utf-8'))['configs'][a.index]
        family,seed=cfg['family'],cfg['seed']; target=out/'models'/family/f'seed{seed}'
        run_command(out,f'train_{family}_{seed}',[sys.executable,'-u','scripts/raw_replay.py',
            'train-one','--output-dir',str(out),'--family',family,'--seed',str(seed)],
            [out/'frozen_protocol.json',out/'cache_manifest.json'],
            [target/'best_model.pt',target/'training_summary.json',target/'output_manifest.json'])
    elif a.stage=='wtb-core':evaluate_wtb(out)
    elif a.stage=='diagnostics':
        subprocess.run([sys.executable,'-u','scripts/replay_after_wtb.py'],cwd=ROOT,check=True)
        cache=out/'cache_wtb'; res=out/'fixed_forecast_residuals.npz'
        for name,script,args in [
            ('supervision','run_clean_privileged_supervision_ablation.py',[
                '--unaligned-pattern',str(out/'models/unaligned/seed{seed}'),
                '--aligned-pattern',str(out/'models/aligned/seed{seed}')]),
            ('active_power','run_active_power_anchor_audit.py',[])]:
            dest=out/name
            run_command(out,name,[sys.executable,'-u',f'scripts/{script}','--cache-dir',str(cache),
                '--residuals-file',str(res),'--output-csv',str(dest/'results.csv'),
                '--output-md',str(dest/'report.md'),*args],
                [res,out/'cache_manifest.json'],[dest/'results.csv',dest/'report.md'])
        run_command(out,'factorial',[sys.executable,'-u','scripts/replay_factorial.py',
            '--replay-root',str(out),'--output-dir',str(out/'factorial')],
            [res,out/'cache_manifest.json'],[out/'factorial/seed_results.csv',out/'factorial/output_manifest.json'])
    elif a.stage=='external-prepare':
        for farm in ['la_haute_borne','kelmarsh','penmanshiel']:
            run_command(ext,'raw_'+farm,[sys.executable,'-u','scripts/replay_external_raw.py','--farm',farm],
                sorted(p for p in (ROOT/'data/external_wind'/farm).iterdir() if p.suffix.lower() in ('.csv','.zip')),
                [ROOT/f'artifacts/raw_replay_external_20261015/{farm}/output_manifest.json'])
    elif a.stage=='external-fit':
        if a.index is None or not 0<=a.index<15:raise ValueError('Expected array index0..14')
        farm=['la_haute_borne','kelmarsh','penmanshiel'][a.index//5];seed=201+a.index%5
        target=ext/farm/f'seed{seed}'
        run_command(ext,f'{farm}_{seed}',[sys.executable,'-u','scripts/replay_external_train.py',
            'train-one','--output-root',str(ext),'--farm',farm,'--seed',str(seed)],
            [ROOT/'experiments/replay_20261015/frozen_external_configs.json',
             ROOT/f'artifacts/raw_replay_external_20261015/{farm}/output_manifest.json'],
            [target/'best_model.pt',target/'training_summary.json',target/'output_manifest.json'])
    else:
        from replay_external_train import transfer
        for seed in range(201,206):
            verify_run_receipt(out/'execution'/f'train_aligned_force_{seed}'/'record.json')
        for farm in ['la_haute_borne','kelmarsh','penmanshiel']:
            for seed in range(201,206):
                verify_run_receipt(ext/'execution'/f'{farm}_{seed}'/'record.json')
        transfer(ext)
        status=json.loads((ext/'transfer_status.json').read_text(encoding='utf-8'))
        if status.get('status')!='EXECUTED_PENDING_INDEPENDENT_REVIEW':
            raise RuntimeError('Transfer did not execute; submission/dependency is not a result')


if __name__=='__main__':main()
