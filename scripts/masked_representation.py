"""Explicit pitch-withheld inference; never relabel ordinary cached gates as masked."""
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import DataLoader
from windfarm_moe.arrival_feed import UnifiedArrivalDataset, DegradationSpec
from windfarm_moe.mechanism_intervention import _load_model_from_checkpoint


def check_frozen_reference(bundle,frozen,split,anchors):
    if not np.array_equal(anchors,frozen[f'anchor_indices_{split}']):
        raise ValueError('Frozen reference anchors differ')
    if not np.array_equal(bundle.time_index[anchors],frozen[f'anchor_time_index_{split}']) or not np.array_equal(bundle.node_ids,frozen['node_ids']):
        raise ValueError('Frozen reference time/node identity differs')
    for lead in (0,5):
        mask=frozen[f'mask_{split}'][:,lead,:]>0.5
        actual_mask=np.asarray(bundle.target_mask[anchors+lead+1])>0.5
        target=np.asarray(bundle.target[anchors+lead+1])
        if not np.array_equal(mask,actual_mask) or not np.array_equal(target[mask],frozen[f'ytrue_{split}'][:,lead,:][mask],equal_nan=True):
            raise ValueError('Frozen reference physical target/mask differs')


def infer_masked(run_dir,bundle,split,device,archive_dir,include_context=False):
    archive_dir=Path(archive_dir);archive_dir.mkdir(parents=True,exist_ok=False)
    ds=UnifiedArrivalDataset(bundle,split,hist_len=bundle.metadata['hist_len'],
        pred_len=bundle.metadata['pred_len'],degradation=DegradationSpec(delay_steps=0,withheld_channels=('Pab_mean','Pab_std')))
    model=_load_model_from_checkpoint(Path(run_dir),bundle,device);model.eval()
    feature_indices=[bundle.metadata['feature_names'].index(x) for x in ('Pab_mean','Pab_std')]
    physical_index=bundle.metadata['physics_names'].index('Pab_mean')
    gates=[];contexts=[]
    with torch.no_grad():
        for batch in DataLoader(ds,batch_size=64,shuffle=False):
            if torch.count_nonzero(batch['x_hist'][...,feature_indices]) or torch.count_nonzero(batch['feature_mask_hist'][...,feature_indices]) or torch.count_nonzero(batch['anchor_physics'][...,physical_index]):
                raise ValueError('Pitch withholding failed before forward')
            _,gate,aux=model(*[batch[k].to(device) for k in
                ('x_hist','edge_index_hist','edge_weight_hist','feature_mask_hist','anchor_physics')])
            gates.append(gate.cpu().numpy())
            if include_context:contexts.append(aux['context'].cpu().numpy())
    gate=np.concatenate(gates)
    np.save(archive_dir/'gate_prob.npy',gate)
    np.save(archive_dir/'anchor_index.npy',ds.anchor_indices)
    context=np.concatenate(contexts) if include_context else None
    if context is not None:np.save(archive_dir/'context.npy',context)
    del model
    return gate,context,ds.anchor_indices
