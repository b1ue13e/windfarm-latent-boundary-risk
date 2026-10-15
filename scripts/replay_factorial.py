"""Corrected factorial controls with matched architecture, randomization and population."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader,TensorDataset
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from windfarm_moe.data import load_cache_bundle
from windfarm_moe.config import TrainConfig
from masked_representation import infer_masked,check_frozen_reference
from replay_provenance import provenance,finalize,write_json


def binned(v,t,s,mask,bins=5,fixed_edges=None):
    valid=mask & np.isfinite(v) & np.isfinite(s)
    if not valid.any():raise ValueError('No calibration targets')
    edges=np.unique(np.quantile(v[valid],np.linspace(0,1,bins+1)[1:-1])) if fixed_edges is None else np.asarray(fixed_edges)
    vi=np.digitize(v,edges);ti=np.digitize(t,edges);global_q=float(np.quantile(s[valid],.9))
    q=np.array([np.quantile(s[valid & (vi==i)],.9) if np.sum(valid & (vi==i))>20 else global_q for i in range(len(edges)+1)])
    return q[ti],edges,q


def categorical(v,t,s,mask):
    global_q=float(np.quantile(s[mask],.9));reserve=np.full(t.shape,global_q,dtype=float)
    for label in (0,1,2):
        valid=mask & (v==label)
        reserve[t==label]=np.quantile(s[valid],.9) if valid.sum()>20 else global_q
    return reserve


def linear_head(xv,xt,sv,indices,seed,out):
    torch.manual_seed(seed)
    x=torch.from_numpy(xv[indices]).float();y=torch.from_numpy(sv[indices]).float()
    head=torch.nn.Linear(x.shape[-1],1)
    with torch.no_grad():head.weight.zero_();head.bias.fill_(float(torch.quantile(y,.9)))
    optimizer=torch.optim.Adam(head.parameters(),lr=.01)
    loader=DataLoader(TensorDataset(x,y),batch_size=2048,shuffle=True)
    history=[]
    for epoch in range(5):
        total,n=0.,0
        for bx,by in loader:
            u=by-head(bx).squeeze(-1);loss=torch.maximum(.9*u,-.1*u).mean()
            optimizer.zero_grad();loss.backward();optimizer.step()
            total+=float(loss.item())*len(bx);n+=len(bx)
        history.append({'epoch':epoch+1,'pinball_loss':total/n})
    out.mkdir(parents=True,exist_ok=False)
    torch.save({'model_state':head.state_dict(),'seed':seed,'history':history,'lr':.01,'epochs':5,'batch_size':2048},out/'head.pt')
    np.save(out/'selected_validation_indices.npy',indices)
    preds=[]
    with torch.no_grad():
        for start in range(0,len(xt),4096):preds.append(head(torch.from_numpy(xt[start:start+4096]).float()).squeeze(-1).numpy())
    return np.concatenate(preds)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--replay-root',type=Path,default=ROOT/'artifacts/raw_replay_20261015_v2')
    p.add_argument('--output-dir',type=Path,default=None)
    a=p.parse_args();base=a.replay_root;out=a.output_dir or base/'factorial_corrected'
    if out.exists():raise FileExistsError(out)
    cache=base/'cache_wtb';bundle=load_cache_bundle(cache)
    residuals=base/'fixed_forecast_residuals.npz';f=np.load(residuals)
    families=['unaligned','aligned','dense_classifier']
    provenance(out,[residuals,cache/'metadata.json',*sorted(cache.glob('*.npy')),
        *[base/f'models/{family}/seed{seed}/best_model.pt' for family in families for seed in range(201,206)]],vars(a))
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');rows=[]
    anchors={s:f[f'anchor_indices_{s}'] for s in ('val','test')}
    for split in anchors:check_frozen_reference(bundle,f,split,anchors[split])
    w={s:np.asarray(bundle.physics[anchors[s],:,0]).reshape(-1) for s in anchors}
    z={s:np.asarray(bundle.regime_primary[anchors[s]]).reshape(-1) for s in anchors}
    for seed in range(201,206):
        lat={}
        c0=torch.load(base/f'models/unaligned/seed{seed}/best_model.pt',map_location='cpu',weights_only=False)
        c1=torch.load(base/f'models/aligned/seed{seed}/best_model.pt',map_location='cpu',weights_only=False)
        l0=TrainConfig(**c0['train_config']).effective_loss_weights();l1=TrainConfig(**c1['train_config']).effective_loss_weights()
        if c0['model_config']!=c1['model_config'] or l0['align']!=0 or l1['align']!=5000 or any(l0[k]!=l1[k] for k in l0 if k!='align'):
            raise ValueError('A/B do not isolate regime alignment on the same architecture')
        for family in families:
            lat[family]={}
            for split in anchors:
                g,c,idx=infer_masked(base/f'models/{family}/seed{seed}',bundle,split,device,out/f'seed{seed}/{family}/{split}',True)
                if not np.array_equal(idx,anchors[split]):raise ValueError('Latent/reference anchors mismatch')
                score=g[...,2]/np.maximum(g[...,:3].sum(-1),1e-9)
                lat[family][split]=(score.reshape(-1),c.reshape(-1,c.shape[-1]))
        for lead in (0,5):
            sv=f[f'shortfall_val_seed{seed}'][:,lead,:].reshape(-1);st=f[f'shortfall_test_seed{seed}'][:,lead,:].reshape(-1)
            mv=f['mask_val'][:,lead,:].reshape(-1)>.5;mt=f['mask_test'][:,lead,:].reshape(-1)>.5
            rng=np.random.default_rng(seed);gq=float(np.quantile(sv[mv],.9))
            pv,pt=lat['aligned']['val'][0],lat['aligned']['test'][0]
            rc,_,_=binned(pv,pt,sv,mv)
            rf,_,_=binned(rng.permutation(pv),rng.permutation(pt),sv,mv)
            zv,zt=rng.permutation(z['val']),rng.permutation(z['test'])
            indices=np.flatnonzero(mv)
            if len(indices)>20000:indices=rng.choice(indices,20000,replace=False)
            rd={}
            for label,family in [('A_No_Alignment_Context','unaligned'),('B_Aligned_Context','aligned')]:
                r=linear_head(lat[family]['val'][1],lat[family]['test'][1],sv,indices,seed,out/f'seed{seed}/h{lead+1}/{label}')
                rd[label]=np.clip(r,0,float(np.max(sv[mv])*1.5))
            rd.update(C_Posterior=rc,D_Global=np.full_like(st,gq),E_Shuffled_Oracle_Diagnostic=categorical(zv,zt,sv,mv),
                F_Randomized_Posterior=rf,G_Oracle_Diagnostic=categorical(z['val'],z['test'],sv,mv),
                H_Shrinkage=.95*rc+.05*gq,J_Posterior_Alias=rc)
            rd['I_Dense_Posterior']=binned(lat['dense_classifier']['val'][0],lat['dense_classifier']['test'][0],sv,mv)[0]
            rd['K_Wind_Bins']=binned(w['val'],w['test'],sv,mv,fixed_edges=np.linspace(0,25,11)[1:-1])[0]
            np.savez_compressed(out/f'seed{seed}/h{lead+1}_all_predictions.npz',shortfall=st,mask=mt,
                anchor_indices=anchors['test'],shuffled_val_labels=zv,shuffled_test_labels=zt,**rd)
            for population,mask in [('Full',mt),('Boundary',mt & (np.abs(w['test']-10.5)<=1.))]:
                for name,r in rd.items():
                    if not np.isfinite(r[mask]).all():raise ValueError('Nonfinite reserves')
                    reserve=float(r[mask].sum()/6);short=float(np.maximum(st[mask]-r[mask],0).sum()/6)
                    rows.append(dict(seed=seed,horizon=lead+1,population=population,variant=name,
                        n_cells=int(mask.sum()),reserve_kwh=reserve,shortage_kwh=short,psrei_kwh=reserve+10*short,
                        violation_rate=float(np.mean(st[mask]>r[mask]))))
            pd.DataFrame(rows).to_csv(out/'seed_results.csv',index=False)
        del lat
    pd.DataFrame(rows).groupby(['horizon','population','variant']).agg(
        psrei_mean=('psrei_kwh','mean'),psrei_sd=('psrei_kwh','std'),n_seeds=('seed','nunique')).to_csv(out/'summary.csv')
    (out/'report.md').write_text('# Corrected factorial diagnostics\n\nAll decisions share frozen targets and populations. A/B isolate alignment with identical backbone configs; both historically observe pitch in training. E/G are non-deployable oracle diagnostics; unknown labels use global fallback. F randomizes BOTH calibration and test posteriors. J is an alias of C, not an independent method. K is the primary wind-bin comparator. Five-seed descriptive summaries do not by themselves establish significance or architecture necessity. See per-seed predictions and training artifacts.\n',encoding='utf-8')
    finalize(out)


if __name__=='__main__':main()
