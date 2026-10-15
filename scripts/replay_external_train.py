"""Train site-frozen forecasts from corrected raw caches, then matched transfer evaluation."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from raw_replay import run_command, verify_records
from replay_provenance import provenance, finalize, write_json
import os


def raw_directory(farm):
    map_path=Path(os.environ.get('RAW_REPLAY_EXTERNAL_CACHE_MAP',
        ROOT/'experiments/replay_20261015/external_cache_roots.json'))
    mapping=json.loads(map_path.read_text(encoding='utf-8')) if map_path.exists() else {}
    return ROOT/mapping.get(farm,f'artifacts/raw_replay_external_20261015/{farm}'),map_path


def train_one(root,farm,seed):
    from windfarm_moe.config import ModelConfig,TrainConfig,EvalConfig
    from windfarm_moe.data import load_cache_bundle
    from windfarm_moe.train import train_model
    cfg_path=ROOT/'experiments/replay_20261015/frozen_external_configs.json'
    cfg=next(c for c in json.loads(cfg_path.read_text(encoding='utf-8'))['configs'] if c['farm']==farm and c['seed']==seed)
    raw_dir,map_path=raw_directory(farm)
    cache=raw_dir/'cache'
    verify_records(json.loads((raw_dir/'output_manifest.json').read_text(encoding='utf-8')))
    target=root/farm/f'seed{seed}'
    if target.exists():raise FileExistsError(target)
    provenance(target,[cfg_path,*([map_path] if map_path.exists() else []),
                       *sorted(cache.glob('*.npy')),cache/'metadata.json'],
               dict(cfg,resolved_cache=str(cache)))
    train_model(load_cache_bundle(cache),target,ModelConfig(**cfg['model_config']),
                TrainConfig(**cfg['train_config']),EvalConfig(skip_visuals=True,save_predictions=True))
    finalize(target)


def run(root,wait_for_wtb):
    cfg_path=ROOT/'experiments/replay_20261015/frozen_external_configs.json'
    for farm in ['la_haute_borne','kelmarsh','penmanshiel']:
        cache=raw_directory(farm)[0]/'cache'
        for seed in range(201,206):
            target=root/farm/f'seed{seed}'
            run_command(root,f'{farm}_{seed}',[sys.executable,'-u',__file__,'train-one',
                '--output-root',str(root),'--farm',farm,'--seed',str(seed)],
                [cfg_path,cache/'metadata.json',*sorted(cache.glob('*.npy'))],
                [target/'best_model.pt',target/'training_summary.json',target/'output_manifest.json'])
    transfer(root,wait_for_wtb)


def transfer(root,wait_for_wtb=False):
    wtb=ROOT/'artifacts/raw_replay_20261015_v2/models/aligned_force'
    while not all((wtb/f'seed{s}/output_manifest.json').is_file() for s in range(201,206)):
        write_json(root/'transfer_status.json',{'status':'WAITING_FOR_WTB_SOURCE','not_a_result':True})
        if not wait_for_wtb:return
        time.sleep(30)
    for s in range(201,206):
        verify_records(json.loads((wtb/f'seed{s}/output_manifest.json').read_text(encoding='utf-8')))
    cache_map=root/'cache_map.json'
    write_json(cache_map,{f:str(raw_directory(f)[0]/'cache') for f in ['kelmarsh','penmanshiel']})
    out=root/'matched_transfer'
    run_command(root,'matched_transfer',[sys.executable,'scripts/repair_exp01_pitch_withheld_v3.py',
        '--source-pattern',str(wtb/'seed{seed}'),'--forecast-pattern',str(root/'{farm}/seed{seed}'),
        '--cache-map',str(cache_map),'--output-dir',str(out)],
        [cache_map,*[wtb/f'seed{s}/best_model.pt' for s in range(201,206)]],
        [out/'exp01_pitchmasked_v3_joint_statistics.csv',out/'exp01_native_day_blocks_v4.npz'])
    write_json(root/'transfer_status.json',{'status':'EXECUTED_PENDING_INDEPENDENT_REVIEW',
        'scientific_certification':False,'result_directory':str(out)})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['run','train-one'])
    p.add_argument('--output-root',type=Path,default=ROOT/'artifacts/raw_replay_external_models_20261015')
    p.add_argument('--farm',choices=['la_haute_borne','kelmarsh','penmanshiel'])
    p.add_argument('--seed',type=int)
    p.add_argument('--wait-for-wtb',action='store_true')
    a=p.parse_args();root=a.output_root.resolve()
    if not root.is_relative_to(ROOT/'artifacts'):raise ValueError('Output outside repository artifacts')
    if a.action=='train-one':train_one(root,a.farm,a.seed)
    else:run(root,a.wait_for_wtb)


if __name__=='__main__':main()
