"""Versioned four-condition factorial extension; not a scientific PASS gate.

May be deployed outside the frozen runtime tree with --workspace explicitly set.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

CONDITIONS=('clean','delay6','pitch_withheld','delay6_pitch_withheld')
FAMILIES=('unaligned','aligned','dense_classifier')
VARIANTS=('A_No_Alignment_Context','B_Aligned_Context','C_Posterior','D_Global',
    'E_Shuffled_Oracle_Diagnostic','F_Randomized_Posterior','G_Oracle_Diagnostic',
    'H_Shrinkage','I_Dense_Posterior','J_Posterior_Alias','K_Wind_Bins')


def condition_parameters(name):
    if name not in CONDITIONS:raise ValueError(name)
    return (6 if name.startswith('delay6') else 0,
            ('Pab_mean','Pab_std') if 'pitch_withheld' in name else ())


def physical_wind(batch,metadata):
    index=metadata['physics_names'].index('Wspd')
    stats=metadata.get('physics_model_stats',{}).get(str(index))
    if not stats or not all(k in stats for k in ('mean','std')):
        raise ValueError('Missing physical wind scaler')
    mean,std=float(stats['mean']),float(stats['std'])
    if not np.isfinite([mean,std]).all() or std<=0:raise ValueError('Invalid physical wind scaler')
    return batch['anchor_physics'][...,index].numpy()*std+mean


def check_shortfall(f,split,seed):
    pred=f[f'yhat_{split}_seed{seed}'];true=f[f'ytrue_{split}'];mask=f[f'mask_{split}']
    short=f[f'shortfall_{split}_seed{seed}']
    if len({x.shape for x in (pred,true,mask,short)})!=1:raise ValueError('Canonical residual shape mismatch')
    if not all(np.isfinite(x[mask>.5]).all() for x in (pred,true,short)):
        raise ValueError('Nonfinite canonical forecast/target/shortfall')
    expected=np.maximum(pred-true,0.)*mask
    if not np.array_equal(short,expected,equal_nan=True) or not np.isfinite(short[mask>.5]).all():
        raise ValueError('Canonical shortfall formula differs')


def check_inputs(batch,bundle,lag,withheld):
    anchors=batch['anchor_index'].numpy()
    expected=torch.from_numpy(np.array(bundle.physics_model[np.maximum(anchors-lag,0)],dtype=np.float32,copy=True))
    if withheld:
        idx=bundle.metadata['physics_names'].index('Pab_mean');expected[...,idx]=0
        indices=[bundle.metadata['feature_names'].index(c) for c in withheld]
        if torch.count_nonzero(batch['x_hist'][...,indices]) or torch.count_nonzero(batch['feature_mask_hist'][...,indices]):
            raise ValueError('Pitch features/masks leaked before forward')
    if not torch.equal(expected,batch['anchor_physics']):
        raise ValueError('Anchor physics does not match shared arrival source')
    if not torch.all(batch['lag_applied']==lag):raise ValueError('Unexpected applied lag')
    if lag:
        for key in ('x_hist','feature_mask_hist','edge_index_hist','edge_weight_hist'):
            values=batch[key];source=values[:,values.shape[1]-1-lag:values.shape[1]-lag]
            if not torch.equal(values[:,-lag:],source.expand_as(values[:,-lag:])):
                raise ValueError('Stalled history/graph differs: '+key)


def infer(run,bundle,split,condition,device,out):
    from windfarm_moe.arrival_feed import UnifiedArrivalDataset,DegradationSpec
    from windfarm_moe.mechanism_intervention import _load_model_from_checkpoint
    lag,withheld=condition_parameters(condition)
    spec=DegradationSpec(delay_steps=lag,corrupted_channels=('all',),
                         withheld_channels=withheld,history_policy='stalled')
    dataset=UnifiedArrivalDataset(bundle,split,hist_len=bundle.metadata['hist_len'],
        pred_len=bundle.metadata['pred_len'],degradation=spec)
    model=_load_model_from_checkpoint(run,bundle,device);model.eval()
    gates=[];contexts=[];winds=[]
    with torch.no_grad():
        for batch in DataLoader(dataset,batch_size=64,shuffle=False):
            check_inputs(batch,bundle,lag,withheld)
            winds.append(physical_wind(batch,bundle.metadata))
            _,gate,aux=model(*[batch[k].to(device) for k in
                ('x_hist','edge_index_hist','edge_weight_hist','feature_mask_hist','anchor_physics')])
            if gate is None:raise ValueError('Expected an actual classifier posterior')
            gates.append(gate.cpu().numpy());contexts.append(aux['context'].cpu().numpy())
    gate=np.concatenate(gates);context=np.concatenate(contexts);wind=np.concatenate(winds)
    if not all(np.isfinite(x).all() for x in (gate,context,wind)):raise ValueError('Nonfinite inference')
    anchors=dataset.anchor_indices
    history=anchors[:,None]-np.arange(bundle.metadata['hist_len']-1,-1,-1)[None,:]
    history=np.minimum(history,(anchors-lag)[:,None])
    out.mkdir(parents=True,exist_ok=False)
    np.save(out/'gate.npy',gate);np.save(out/'context.npy',context)
    np.savez_compressed(out/'observed_inputs.npz',wind=wind,anchor_indices=anchors,
        anchor_source_indices=np.maximum(anchors-lag,0),history_source_indices=history)
    (out/'degradation.json').write_text(json.dumps(asdict(spec),indent=2),encoding='utf-8')
    del model
    return gate,context,wind,anchors


def paired_blocks(reserves,shortfall,mask,day_ids):
    days=np.unique(day_ids);result={'days':days}
    for name,values in reserves.items():
        costs=[];procure=[];shortages=[];counts=[]
        for day in days:
            selected=mask & (day_ids==day)
            reserve=float(values[selected].sum()/6)
            shortage=float(np.maximum(shortfall[selected]-values[selected],0).sum()/6)
            procure.append(reserve);shortages.append(shortage);costs.append(reserve+10*shortage)
            counts.append(int(selected.sum()))
        result[name+'_cost_kwh']=np.array(costs)
        result[name+'_reserve_kwh']=np.array(procure)
        result[name+'_shortage_kwh']=np.array(shortages)
        result[name+'_n_cells']=np.array(counts)
    baseline=result['K_Wind_Bins_cost_kwh']
    for name in reserves:result[name+'_delta_vs_K_kwh']=result[name+'_cost_kwh']-baseline
    return result


def check_pair(c0,c1):
    from windfarm_moe.config import TrainConfig
    if c0['model_config']!=c1['model_config']:raise ValueError('A/B architecture mismatch')
    a,b=c0['train_config'],c1['train_config']
    ignored={'mode','label','aux_weight','smooth_weight','physics_force_weight','align_weight','balance_weight'}
    if any(a.get(k)!=b.get(k) for k in a.keys()|b.keys() if k not in ignored):
        raise ValueError('A/B optimizer/schedule/seed mismatch')
    la,lb=TrainConfig(**a).effective_loss_weights(),TrainConfig(**b).effective_loss_weights()
    if la['align']!=0 or lb['align']!=5000 or any(la[k]!=lb[k] for k in la if k!='align'):
        raise ValueError('A/B effective losses do not isolate alignment')


def execute(root,index,output,manifest):
    from windfarm_moe.data import load_cache_bundle
    from raw_replay import verify_run_receipt,verify_records
    from masked_representation import check_frozen_reference
    from replay_factorial import binned,categorical,linear_head
    from replay_provenance import provenance,finalize
    if output.exists():raise FileExistsError('Preserve old attempt: '+str(output))
    condition=CONDITIONS[index//5];seed=201+index%5
    base=root/'artifacts/raw_replay_20261015_v2';cache=base/'cache_wtb'
    verify_records(json.loads((base/'cache_manifest.json').read_text(encoding='utf-8')))
    verify_run_receipt(base/'execution/fixed_residuals/record.json')
    for family in FAMILIES:verify_run_receipt(base/'execution'/f'train_{family}_{seed}'/'record.json')
    inputs=[manifest,Path(__file__),base/'fixed_forecast_residuals.npz',base/'cache_manifest.json',
        cache/'metadata.json',*[base/f'models/{f}/seed{seed}/best_model.pt' for f in FAMILIES]]
    provenance(output,inputs,{'protocol':'RAW-FACTORIAL-FOUR-CONDITIONS-V2','condition':condition,
        'seed':seed,'pbs_job_id':os.environ.get('PBS_JOBID'),'torch':torch.__version__,
        'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0),
        'interpretation':'diagnostic only; K wind-only is not strongest fresh-pitch baseline'})
    shutil.copyfile(__file__,output/'executed_extension.py')
    shutil.copyfile(manifest,output/'extension_manifest.json')
    bundle=load_cache_bundle(cache,mmap_mode='r');f=np.load(base/'fixed_forecast_residuals.npz')
    check_pair(*[torch.load(base/f'models/{x}/seed{seed}/best_model.pt',map_location='cpu',weights_only=False)
        for x in ('unaligned','aligned')])
    anchors={s:f[f'anchor_indices_{s}'] for s in ('val','test')}
    for split in anchors:
        check_frozen_reference(bundle,f,split,anchors[split]);check_shortfall(f,split,seed)
    lat={};observed={};device=torch.device('cuda')
    for family in FAMILIES:
        lat[family]={}
        for split in anchors:
            g,c,w,idx=infer(base/f'models/{family}/seed{seed}',bundle,split,condition,device,output/f'{family}/{split}')
            if not np.array_equal(idx,anchors[split]):raise ValueError('Inference/canonical anchors mismatch')
            if split in observed and not np.array_equal(w,observed[split]):raise ValueError('Unequal observed wind across models')
            observed[split]=w
            lat[family][split]=(g[...,2].reshape(-1)/np.maximum(g[...,:3].sum(-1).reshape(-1),1e-9),c.reshape(-1,c.shape[-1]))
    raw_wind=np.asarray(bundle.physics[anchors['test'],:,bundle.metadata['physics_names'].index('Wspd')]).reshape(-1)
    z={s:np.asarray(bundle.regime_primary[anchors[s]]).reshape(-1) for s in anchors}
    wind={s:observed[s].reshape(-1) for s in anchors}
    day_ids=np.repeat(bundle.time_index[anchors['test'],0],len(bundle.node_ids));rows=[]
    for lead in (0,5):
        sv=f[f'shortfall_val_seed{seed}'][:,lead,:].reshape(-1);st=f[f'shortfall_test_seed{seed}'][:,lead,:].reshape(-1)
        mv=f['mask_val'][:,lead,:].reshape(-1)>.5;mt=f['mask_test'][:,lead,:].reshape(-1)>.5
        rng=np.random.default_rng(seed);gq=float(np.quantile(sv[mv],.9))
        pv,pt=lat['aligned']['val'][0],lat['aligned']['test'][0]
        rc,_,_=binned(pv,pt,sv,mv)
        pvi,pti=rng.permutation(len(pv)),rng.permutation(len(pt))
        rf,_,_=binned(pv[pvi],pt[pti],sv,mv)
        zvi,zti=rng.permutation(len(z['val'])),rng.permutation(len(z['test']))
        zv,zt=z['val'][zvi],z['test'][zti]
        indices=np.flatnonzero(mv)
        if len(indices)>20000:indices=rng.choice(indices,20000,replace=False)
        reserves={}
        for label,family in [('A_No_Alignment_Context','unaligned'),('B_Aligned_Context','aligned')]:
            reserve=linear_head(lat[family]['val'][1],lat[family]['test'][1],sv,indices,seed,output/f'h{lead+1}/{label}')
            reserves[label]=np.clip(reserve,0,float(np.max(sv[mv])*1.5))
        reserves.update(C_Posterior=rc,D_Global=np.full_like(st,gq),
            E_Shuffled_Oracle_Diagnostic=categorical(zv,zt,sv,mv),F_Randomized_Posterior=rf,
            G_Oracle_Diagnostic=categorical(z['val'],z['test'],sv,mv),H_Shrinkage=.95*rc+.05*gq,J_Posterior_Alias=rc)
        reserves['I_Dense_Posterior']=binned(lat['dense_classifier']['val'][0],lat['dense_classifier']['test'][0],sv,mv)[0]
        reserves['K_Wind_Bins']=binned(wind['val'],wind['test'],sv,mv,fixed_edges=np.linspace(0,25,11)[1:-1])[0]
        np.savez_compressed(output/f'h{lead+1}_predictions.npz',shortfall=st,mask=mt,
            anchor_indices=anchors['test'],anchor_time_index=bundle.time_index[anchors['test']],
            node_ids=bundle.node_ids,raw_wind=raw_wind,observed_wind=wind['test'],day_ids=day_ids,
            shuffled_val_labels=zv,shuffled_test_labels=zt,posterior_val_permutation=pvi,
            posterior_test_permutation=pti,oracle_val_permutation=zvi,oracle_test_permutation=zti,**reserves)
        for population,mask in [('Full',mt),('Boundary',mt & (np.abs(raw_wind-10.5)<=1.))]:
            if not mask.any():raise ValueError('Empty frozen population')
            for name,values in reserves.items():
                if not np.isfinite(values[mask]).all():raise ValueError('Nonfinite reserve')
                reserve=float(values[mask].sum()/6);short=float(np.maximum(st[mask]-values[mask],0).sum()/6)
                rows.append(dict(condition=condition,seed=seed,horizon=lead+1,population=population,
                    variant=name,n_cells=int(mask.sum()),reserve_kwh=reserve,shortage_kwh=short,
                    psrei_kwh=reserve+10*short,violation_rate=float(np.mean(st[mask]>values[mask]))))
            np.savez_compressed(output/f'h{lead+1}_{population}_day_blocks.npz',**paired_blocks(reserves,st,mask,day_ids))
    pd.DataFrame(rows).to_csv(output/'seed_results.csv',index=False)
    finalize(output)


def summarize(root,manifest):
    from raw_replay import verify_run_receipt
    from replay_provenance import provenance,finalize
    base=root/'artifacts/raw_replay_20261015_v2/factorial_four_conditions_v2'
    output=base/'aggregate'
    if output.exists():raise FileExistsError(output)
    frames=[];inputs=[manifest,Path(__file__)]
    for condition in CONDITIONS:
        for seed in range(201,206):
            receipt=base/'execution'/f'{condition}_{seed}'/'record.json'
            verify_run_receipt(receipt)
            csv=base/condition/f'seed{seed}/seed_results.csv'
            df=pd.read_csv(csv)
            if (len(df)!=44 or set(df.condition)!={condition} or set(df.seed)!={seed} or
                set(df.horizon)!={1,6} or set(df.population)!={'Full','Boundary'} or set(df.variant)!=set(VARIANTS) or
                df.duplicated(['condition','seed','horizon','population','variant']).any()):
                raise ValueError('Incomplete/duplicate factorial cells: '+str(csv))
            frames.append(df);inputs.extend([receipt,csv])
    result=pd.concat(frames,ignore_index=True)
    if not result.groupby(['condition','horizon','population','variant']).seed.nunique().eq(5).all():
        raise ValueError('Five matched seeds required in every summary')
    for seed in range(201,206):
        for lead in (1,6):
            with np.load(base/'clean'/f'seed{seed}/h{lead}_predictions.npz') as ref:
                for condition in CONDITIONS[1:]:
                    with np.load(base/condition/f'seed{seed}/h{lead}_predictions.npz') as other:
                        for key in ('shortfall','mask','anchor_indices','anchor_time_index','node_ids','raw_wind','day_ids'):
                            a,b=ref[key],other[key]
                            equal=np.array_equal(a,b,equal_nan=True) if a.dtype.kind in 'fc' else np.array_equal(a,b)
                            if not equal:raise ValueError('Cross-condition frozen population differs: '+key)
    provenance(output,inputs,{'scope':'all20 factorial condition/seed runs; descriptive mean/SD only'})
    shutil.copyfile(__file__,output/'executed_extension.py')
    result.to_csv(output/'all_seed_results.csv',index=False)
    result.groupby(['condition','horizon','population','variant']).agg(
        psrei_mean=('psrei_kwh','mean'),psrei_sd=('psrei_kwh','std'),n_seeds=('seed','nunique'),
        violation_mean=('violation_rate','mean'),reserve_mean=('reserve_kwh','mean'),
        shortage_mean=('shortage_kwh','mean')).to_csv(output/'summary.csv')
    (output/'report.md').write_text(
        '# Four-condition factorial diagnostics\n\nAll20 condition/seed runs are present. '
        'Canonical shortfalls and full/diagnostic populations were checked across conditions. '
        'Wind baseline reads the same arrived wind as models, but is wind-only and not the strongest fresh-pitch comparator. '
        'A/B isolate alignment on matched historical-pitch backbones. Oracle arms E/G are non-deployable; J aliases C. '
        'Tables contain descriptive five-seed means/SD, not invented p-values or a necessity/superiority verdict. '
        'Inspect per-seed reserves, masks, targets, head weights and paired day blocks before any scientific interpretation.\n',encoding='utf-8')
    finalize(output)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--index',type=int);p.add_argument('--execute',action='store_true')
    p.add_argument('--summarize',action='store_true')
    a=p.parse_args();root=a.workspace.resolve()
    if a.summarize==(a.index is not None):raise ValueError('Choose one array index or --summarize')
    if a.index is not None and not 0<=a.index<20:raise ValueError('Expected4 conditions x5 seeds')
    sys.path[:0]=[str(root/'scripts'),str(root)]
    from replay_provenance import sha256
    manifest=a.manifest.resolve();m=json.loads(manifest.read_text(encoding='utf-8'))
    for row in m['files']:
        if sha256(manifest.parent/row['name'])!=row['sha256']:raise ValueError('Extension manifest mismatch')
    if sha256(__file__)!=m['program_sha256']:raise ValueError('Executed extension differs')
    for row in m.get('frozen_files',[]):
        if sha256(root/row['relative_path'])!=row['sha256']:raise ValueError('Frozen runtime dependency differs')
    if not os.environ.get('PBS_JOBID'):raise RuntimeError('Run this extension through PBS, not on the login node')
    base=root/'artifacts/raw_replay_20261015_v2';dest=base/'factorial_four_conditions_v2'
    from raw_replay import run_command
    if a.summarize:
        if a.execute:summarize(root,manifest);return
        output=dest/'aggregate'
        run_command(dest,'aggregate',[sys.executable,'-u',str(Path(__file__).resolve()),
            '--workspace',str(root),'--manifest',str(manifest),'--summarize','--execute'],
            [manifest,Path(__file__),*[dest/'execution'/f'{condition}_{seed}/record.json'
                for condition in CONDITIONS for seed in range(201,206)]],
            [output/'all_seed_results.csv',output/'summary.csv',output/'output_manifest.json'])
        return
    if not torch.cuda.is_available():raise RuntimeError('Experiment requires allocated CUDA GPU')
    condition=CONDITIONS[a.index//5];seed=201+a.index%5;output=dest/condition/f'seed{seed}'
    if a.execute:execute(root,a.index,output,manifest);return
    run_command(dest,f'{condition}_{seed}',[sys.executable,'-u',str(Path(__file__).resolve()),
        '--workspace',str(root),'--manifest',str(manifest),'--index',str(a.index),'--execute'],
        [manifest,Path(__file__),base/'fixed_forecast_residuals.npz',base/'cache_manifest.json',
         *[base/f'models/{f}/seed{seed}/best_model.pt' for f in FAMILIES]],
        [output/'seed_results.csv',output/'output_manifest.json'])


if __name__=='__main__':main()
