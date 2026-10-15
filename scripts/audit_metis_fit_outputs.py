"""PBS-only, read-only audit of real completed fits or factorial input readiness.

Writes new reports outside the frozen experiment tree; never certifies science.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys
import traceback
import numpy as np
import torch


def require_success(record):
    if record.get('status')!='EXECUTED' or record.get('exit_code')!=0 or not record.get('inputs') or not record.get('outputs'):
        raise ValueError('A completed status requires actual exit0 and nonempty input/output evidence')


def require_matrix(rows,families):
    actual=[(r['family'],r['seed']) for r in rows]
    expected={(f,s) for f in families for s in range(201,206)}
    if set(actual)!=expected or len(actual)!=len(expected):raise ValueError('Incomplete/duplicate frozen model-family x seed matrix')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--mode',choices=('completed','factorial-readiness'),required=True)
    args=p.parse_args();root=args.workspace.resolve();out=args.output_dir.resolve()
    if not out.is_relative_to(root/'metis_execution'):raise ValueError('Audit output must be outside frozen experiment outputs')
    out.mkdir(parents=True,exist_ok=False)
    if not os.environ.get('PBS_JOBID'):raise RuntimeError('Run audit in a PBS CPU allocation')
    sys.path[:0]=[str(root/'scripts'),str(root)]
    from raw_replay import verify_run_receipt
    from replay_provenance import sha256,file_record
    from windfarm_moe.data import load_cache_bundle,RegimeWindowDataset
    from windfarm_moe.config import TrainConfig,ModelConfig
    from repair_exp01_pitch_withheld_v3 import assert_forecast_alignment
    verified={};bundles={};checked_raw=set();results=[];pending=[];failures=[]

    def check(rows):
        for row in rows:
            path=Path(row['path']);stat=path.stat()
            signature=(row['sha256'],stat.st_size,stat.st_mtime_ns)
            if verified.get(str(path))==signature:continue
            if stat.st_size!=row['bytes'] or sha256(path)!=row['sha256']:
                raise ValueError('Input hash mismatch: '+str(path))
            after=path.stat()
            if (after.st_size,after.st_mtime_ns)!=(stat.st_size,stat.st_mtime_ns):raise ValueError('Input changed during audit')
            verified[str(path)]=signature

    base=root/'artifacts/raw_replay_20261015_v2'
    protocol=json.loads((base/'frozen_protocol.json').read_text())
    check([protocol['config_source']])
    wtb=protocol['configs']
    require_matrix(wtb,('forecast','aligned_force','unaligned','aligned','dense_classifier','dense'))
    external=json.loads((root/'experiments/replay_20261015/frozen_external_configs.json').read_text())['configs']
    candidates=[]
    for cfg in wtb:
        family,seed=cfg['family'],cfg['seed']
        if args.mode=='factorial-readiness' and family not in ('forecast','unaligned','aligned','dense_classifier'):continue
        candidates.append((f'train_{family}_{seed}',base/'execution'/f'train_{family}_{seed}/record.json',
            base/f'models/{family}/seed{seed}',base/'cache_wtb','wtb',cfg))
    if args.mode=='completed':
        mapping=json.loads((root/'metis_cache_map.json').read_text())
        for cfg in external:
            farm,seed=cfg['farm'],cfg['seed'];directory=root/'artifacts/raw_replay_external_models_20261015'
            candidates.append((f'{farm}_{seed}',directory/'execution'/f'{farm}_{seed}/record.json',
                directory/farm/f'seed{seed}',root/mapping[farm]/'cache',farm,cfg))
    for name,receipt,run,cache,site,cfg in candidates:
        state=json.loads(receipt.read_text()).get('status') if receipt.exists() else 'NOT_RUN'
        if state!='EXECUTED':
            pending.append({'name':name,'status':state})
            if state=='FAILED':failures.append({'name':name,'error':'Training execution receipt FAILED','receipt':str(receipt)})
            continue
        try:
            rec=verify_run_receipt(receipt)
            require_success(rec)
            prov=json.loads((run/'provenance.json').read_text());check(prov['inputs'])
            if str(cache) not in bundles:bundles[str(cache)]=load_cache_bundle(cache,mmap_mode='r')
            bundle=bundles[str(cache)]
            checkpoint=torch.load(run/'best_model.pt',map_location='cpu',weights_only=False)
            if checkpoint['train_config']!=TrainConfig(**cfg['train_config']).__dict__:
                raise ValueError('Actual checkpoint training config differs from frozen config')
            expected_model=ModelConfig(**cfg['model_config']).__dict__
            # These are the two data-derived assignments in frozen train_model.
            expected_model.update(primary_num_classes=bundle.metadata['primary_num_classes'],
                                  gate_physics_dim=bundle.physics.shape[-1])
            if checkpoint['model_config']!=expected_model:raise ValueError('Actual model config differs from frozen config/declared data dimensions')
            if not all(bool(torch.isfinite(t).all()) for t in checkpoint['model_state'].values()):
                raise ValueError('Nonfinite checkpoint tensor')
            del checkpoint
            if site not in checked_raw:
                if site=='wtb':
                    check(json.loads((base/'cache_manifest.json').read_text()))
                    check(json.loads((base/'frozen_protocol.json').read_text())['raw_wtb'])
                else:
                    check(json.loads((cache.parent/'output_manifest.json').read_text()))
                    check(json.loads((cache.parent/'provenance.json').read_text())['inputs'])
                checked_raw.add(site)
            splits=[]
            for split in ('val','test'):
                metric=run/(split+'_metrics');anchors=np.load(metric/'anchor_index.npy')
                expected=RegimeWindowDataset(bundle,split,bundle.metadata['hist_len'],bundle.metadata['pred_len']).anchor_indices
                if not np.array_equal(anchors,expected):raise ValueError('Incomplete evaluation anchor window')
                leads=np.arange(1,bundle.metadata['pred_len']+1)
                target=np.asarray(bundle.target[anchors[:,None]+leads[None,:]])
                mask=np.asarray(bundle.target_mask[anchors[:,None]+leads[None,:]])>.5
                assert_forecast_alignment(metric,bundle,anchors,target,mask)
                pred=np.load(metric/'pred.npy',mmap_mode='r')
                if pred.shape!=target.shape or not np.isfinite(pred[mask]).all():raise ValueError('Invalid prediction population')
                splits.append({'split':split,'shape':list(pred.shape),'valid_cells':int(mask.sum())})
            history=json.loads((run/'training_history.json').read_text());summary=json.loads((run/'training_summary.json').read_text())
            if [h['epoch'] for h in history]!=list(range(1,len(history)+1)) or not history:
                raise ValueError('Incomplete epoch history')
            if not 1<=summary['best_epoch']<=len(history):raise ValueError('Invalid best epoch')
            results.append({'name':name,'status':'VERIFIED_MODEL_ARTIFACTS_ONLY','epochs':len(history),
                'family':cfg.get('family',cfg.get('farm')),'seed':cfg['seed'],
                'receipt':file_record(receipt),'output_manifest':file_record(run/'output_manifest.json'),'splits':splits})
        except Exception as exc:
            failures.append({'name':name,'error':str(exc),'traceback':traceback.format_exc()})
            print(traceback.format_exc(),flush=True)
    canonical=None
    if args.mode=='factorial-readiness' and not pending and not failures:
        try:
            from masked_representation import check_frozen_reference
            res=base/'fixed_forecast_residuals.npz'
            receipt=base/'execution/fixed_residuals/record.json'
            require_success(verify_run_receipt(receipt))
            evidence=res.with_suffix('.evidence')
            check(json.loads((evidence/'provenance.json').read_text())['inputs'])
            check(json.loads((evidence/'output_manifest.json').read_text()))
            bundle=load_cache_bundle(base/'cache_wtb',mmap_mode='r')
            with np.load(res) as f:
                for split in ('val','test'):
                    expected=RegimeWindowDataset(bundle,split,bundle.metadata['hist_len'],bundle.metadata['pred_len']).anchor_indices
                    check_frozen_reference(bundle,f,split,expected)
                    for seed in range(201,206):
                        pred=f[f'yhat_{split}_seed{seed}'];target=f[f'ytrue_{split}'];mask=f[f'mask_{split}'];short=f[f'shortfall_{split}_seed{seed}']
                        if len({x.shape for x in (pred,target,mask,short)})!=1:raise ValueError('Residual shape mismatch')
                        if not all(np.isfinite(x[mask>.5]).all() for x in (pred,target,short)):
                            raise ValueError('Nonfinite canonical values')
                        if not np.array_equal(short,np.maximum(pred-target,0.)*mask,equal_nan=True):raise ValueError('Canonical shortfall formula mismatch')
            canonical={'receipt':file_record(receipt),'residual':file_record(res),'provenance':file_record(evidence/'provenance.json')}
        except Exception as exc:
            failures.append({'name':'canonical_residuals','error':str(exc),'traceback':traceback.format_exc()})
            print(traceback.format_exc(),flush=True)
    required={(f,s) for f in ('forecast','unaligned','aligned','dense_classifier') for s in range(201,206)}
    actual=[(r['family'],r['seed']) for r in results]
    ready=(args.mode=='factorial-readiness' and len(actual)==20 and set(actual)==required
           and not pending and not failures and canonical is not None)
    report={'recorded_utc':datetime.now(timezone.utc).isoformat(),'pbs_job_id':os.environ['PBS_JOBID'],
        'mode':args.mode,'readiness':'INPUTS_VERIFIED' if ready else 'NOT_CERTIFIED',
        'audit_program':file_record(Path(__file__)),'results':results,'pending':pending,'failures':failures,
        'canonical':canonical,'scientific_completion':False,
        'scope':'artifact/config/population readiness only; no scientific or whole-experiment reproduction certificate'}
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'verified_models':len(results),'pending':len(pending),'failures':len(failures),
        'readiness':report['readiness'],'report':str(out/'report.json'),'scientific_completion':False}),flush=True)
    if failures or (args.mode=='factorial-readiness' and not ready):raise SystemExit(1)


if __name__=='__main__':main()
