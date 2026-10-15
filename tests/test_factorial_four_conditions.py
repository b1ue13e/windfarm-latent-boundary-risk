"""Regressions for wrong-window wind, withheld inputs and paired day accounting.

Software fixtures only; no experimental evidence is produced by these tests.
"""
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import torch

PROGRAM=Path(os.environ.get('FACTORIAL_EXTENSION_SOURCE',
    Path(__file__).resolve().parents[1]/'scripts/replay_factorial_four_conditions.py'))
spec=importlib.util.spec_from_file_location('factorial_four',PROGRAM)
extension=importlib.util.module_from_spec(spec);spec.loader.exec_module(extension)


def test_delayed_baseline_uses_observed_physical_wind_and_its_own_scaler():
    # Raw issue wind could be20m/s; observed standardized -1 means8m/s,
    # not -1m/s or20m/s. The primary comparator must see exactly this8.
    metadata={'physics_names':['Wspd','Pab_mean'],'physics_model_stats':{'0':{'mean':10.,'std':2.}}}
    batch={'anchor_physics':torch.tensor([[[-1.,0.]]])}
    assert extension.physical_wind(batch,metadata).item()==8.


@pytest.mark.parametrize('stats',[None,{}, {'mean':0.,'std':0.},{'mean':0.,'std':float('nan')}])
def test_standardized_wind_cannot_be_relabelled_as_physical_without_a_valid_scaler(stats):
    metadata={'physics_names':['Wspd'],'physics_model_stats':{'0':stats}}
    with pytest.raises(ValueError,match='scaler'):
        extension.physical_wind({'anchor_physics':torch.tensor([[[1.]]])},metadata)


def test_residual_target_cannot_change_even_if_anchor_and_observed_power_match():
    frozen={'yhat_test_seed201':np.array([[[20.]]]),'ytrue_test':np.array([[[12.]]]),
        'mask_test':np.ones((1,1,1)),'shortfall_test_seed201':np.array([[[8.]]])}
    extension.check_shortfall(frozen,'test',201)
    frozen['shortfall_test_seed201'][0,0,0]=7.
    with pytest.raises(ValueError,match='formula'):extension.check_shortfall(frozen,'test',201)
    frozen['yhat_test_seed201'][0,0,0]=-np.inf
    frozen['shortfall_test_seed201'][0,0,0]=0.
    with pytest.raises(ValueError,match='Nonfinite'):extension.check_shortfall(frozen,'test',201)


@pytest.mark.parametrize('condition',extension.CONDITIONS)
def test_all_conditions_check_stalled_graph_and_actual_anchor_source(condition):
    lag,withheld=extension.condition_parameters(condition)
    physics=np.arange(60,dtype=np.float32).reshape(10,2,3)
    metadata={'physics_names':['Wspd','Pab_mean','wake_score'],
              'feature_names':['Wspd','Pab_mean','Pab_std']}
    bundle=SimpleNamespace(physics_model=physics,metadata=metadata)
    values=torch.arange(48,dtype=torch.float32).reshape(1,8,2,3)
    batch={'anchor_index':torch.tensor([9]),'lag_applied':torch.tensor([lag]),
        'anchor_physics':torch.from_numpy(physics[9-lag:10-lag].copy()),
        'x_hist':values.clone(),'feature_mask_hist':torch.ones_like(values),
        'edge_index_hist':torch.arange(32).reshape(1,8,2,2),
        'edge_weight_hist':torch.arange(16,dtype=torch.float32).reshape(1,8,2)}
    if lag:
        for key in ('x_hist','feature_mask_hist','edge_index_hist','edge_weight_hist'):
            source=batch[key][:,1:2].clone();batch[key][:,2:]=source
    if withheld:
        batch['x_hist'][...,1:]=0;batch['feature_mask_hist'][...,1:]=0
        batch['anchor_physics'][...,1]=0
    extension.check_inputs(batch,bundle,lag,withheld)
    if lag:
        batch['anchor_physics'][...,0]=torch.from_numpy(physics[9:10,:,0].copy())
        with pytest.raises(ValueError,match='arrival source'):extension.check_inputs(batch,bundle,lag,withheld)
    elif withheld:
        batch['feature_mask_hist'][...,-1]=1
        with pytest.raises(ValueError,match='leaked'):extension.check_inputs(batch,bundle,lag,withheld)


def test_saved_day_contrasts_preserve_the_full_mask_and_canonical_sign():
    reserves={'K_Wind_Bins':np.array([1.,2.,3.,4.]),'Challenger':np.array([2.,2.,9.,4.])}
    shortfall=np.array([3.,3.,10.,5.]);mask=np.array([True,True,False,True]);days=np.array([0,0,1,1])
    result=extension.paired_blocks(reserves,shortfall,mask,days)
    assert result['K_Wind_Bins_n_cells'].tolist()==[2,1]
    for name,values in reserves.items():
        expected=(values[mask]+10*np.maximum(shortfall[mask]-values[mask],0)).sum()/6
        assert result[name+'_cost_kwh'].sum()==pytest.approx(expected)
    assert result['Challenger_delta_vs_K_kwh'].sum()==pytest.approx(-1.5)
