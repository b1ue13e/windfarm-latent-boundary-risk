import importlib.util
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from run_channel_consequence_ablations import residual_at_horizon, compute_transition_recall
from run_exp03_async_benchmark import simulate_asynchronous_scada_stream
from run_exp02_zero_privileged_supervision import physical_proxy_channels
from raw_replay import verify_run_receipt
from replay_provenance import file_record, write_json
import pytest


def test_h6_uses_sixth_residual_not_second():
    a = np.arange(12).reshape(2, 6, 1)
    result = residual_at_horizon({'shortfall_test_seed201': a}, 'test', 201, 6)
    assert result[:, 0].tolist() == [5, 11]


def test_invalid_adjacent_labels_do_not_create_transition_events():
    labels = np.array([1, 0, 1, 1])[:, None]
    valid = np.array([1, 0, 1, 1], dtype=bool)[:, None]
    _, legacy_n = compute_transition_recall(labels, labels, return_count=True)
    recall, n = compute_transition_recall(labels, labels, valid=valid, return_count=True)
    assert legacy_n > 0
    assert n == 0 and recall == 0


def test_async_full_archive_reconstructs_all_inputs_without_future_packets(tmp_path):
    names = ['Wspd', 'Patv_hist', 'Etmp', 'Itmp', 'Prtv']
    raw = np.arange(60, dtype=np.float32).reshape(6, 2, 5) + 17
    path = tmp_path / 'packets.npz'
    observed, missing, stats, _ = simulate_asynchronous_scada_stream(
        raw, names, mean_delay=6, max_lateness=4, seed=20261012, archive_path=path)
    z = np.load(path)
    assert z['delays'].shape == raw.shape
    for t in range(6):
        for n in range(2):
            for c in range(5):
                source = z['selected_source'][t,n,c]
                if source < 0:
                    assert observed[t,n,c] == 0
                else:
                    assert source + z['delays'][source,n,c] <= t
                    assert observed[t,n,c] == raw[source,n,c]
    assert np.array_equal(z['contaminated_features'], observed)
    assert np.array_equal(z['dropped_mask'], missing)
    assert stats['initial_value_standardized'] == 0


def test_exp02_proxy_uses_physical_power_not_other_channels_scaler(tmp_path):
    write_json(tmp_path/'metadata.json', {'physics_names':['Wspd','Pab_mean','wake_score','Patv'],
               'feature_stats':{'Patv_hist':{'mean':999,'std':99}},
               'physics_model_stats':{'3':{'mean':0,'std':1}}})
    np.save(tmp_path/'physics.npy',np.array([[[11.,0.,0.,1449.]],[[11.,0.,0.,1451.]]]))
    w,p=physical_proxy_channels(tmp_path,np.array([0,1]))
    assert ((w>10.5)&(p<1450)).ravel().tolist()==[True,False]


def test_resume_rejects_tampered_prediction_inside_manifest(tmp_path):
    pred=tmp_path/'prediction.npy'; np.save(pred,np.array([1.]))
    manifest=tmp_path/'output_manifest.json';write_json(manifest,[file_record(pred)])
    receipt=tmp_path/'receipt.json'
    write_json(receipt,{'status':'EXECUTED','inputs':[], 'outputs':[file_record(manifest)],'source_sha256':{}})
    verify_run_receipt(receipt)
    np.save(pred,np.array([2.]))
    with pytest.raises(ValueError,match='Evidence changed'):
        verify_run_receipt(receipt)


def test_external_coordinates_require_real_source_and_resolve_explicit_alias(tmp_path):
    from windfarm_moe.external_wind import _read_external_coords
    with pytest.raises(FileNotFoundError):
        _read_external_coords(tmp_path,['T01'])
    (tmp_path/'WT_static.csv').write_text('Alternative Title,Latitude,Longitude\nKWF1,52.4,-0.9\nKWF2,52.5,-1.0\n,,\n,,\n',encoding='utf-8')
    c=_read_external_coords(tmp_path,['T01','T02'])
    assert c.node_id.tolist()==['T01','T02']
    assert not np.all(c.y.to_numpy()==0)
    with pytest.raises(ValueError,match='mismatch'):
        _read_external_coords(tmp_path,['T03'])


def test_equal_anchor_indices_cannot_hide_a_shifted_forecast_target(tmp_path):
    from repair_exp01_pitch_withheld_v3 import assert_forecast_alignment
    from types import SimpleNamespace
    np.save(tmp_path/'target.npy',np.array([[[100.]]]))
    np.save(tmp_path/'mask.npy',np.ones((1,1,1)))
    bundle=SimpleNamespace(metadata={},time_index=np.array([[1,0]]),node_ids=np.array([0]))
    with pytest.raises(ValueError,match='different physical window'):
        assert_forecast_alignment(tmp_path,bundle,np.array([0]),np.array([[[200.]]]),np.ones((1,1,1),dtype=bool))


def test_phase_target_and_population_use_fixed_physical_inputs():
    from eval_single_task_dense_phase_scan import frozen_phase_population
    from types import SimpleNamespace
    bundle=SimpleNamespace(metadata={'physics_names':['Wspd']},physics=np.array([[[10.5]],[[20.]],[[9.9]]]),
        target=np.array([[0.],[100.],[200.]]),target_mask=np.ones((3,1)),time_index=np.array([[1,0],[1,1],[1,2]]),node_ids=np.array([7]))
    frozen={'anchor_indices_test':np.array([0,1]),'shortfall_test_seed201':np.array([[[5.]],[[7.]]]),
        'mask_test':np.ones((2,1,1)),'ytrue_test':np.array([[[100.]],[[200.]]]),
        'anchor_time_index_test':np.array([[1,0],[1,1]]),'node_ids':np.array([7])}
    shortfall,mask=frozen_phase_population(bundle,'test',201,0,np.array([0,1]),frozen)
    assert shortfall.tolist()==[5.,7.] and mask.tolist()==[True,False]
    frozen['ytrue_test'][0,0,0]=999
    with pytest.raises(ValueError,match='physical target'):
        frozen_phase_population(bundle,'test',201,0,np.array([0,1]),frozen)


def test_channel_window_memory_reduction_preserves_values():
    from run_channel_consequence_ablations import extract_channel_features
    from types import SimpleNamespace
    rng=np.random.default_rng(8)
    f=rng.normal(size=(10,2,2)).astype(np.float32)
    physics=rng.normal(size=(10,2,4)).astype(np.float32)
    b=SimpleNamespace(metadata={'hist_len':3,'pred_len':1,'split_bounds':{'train':[0,10]},
        'feature_names':['Patv_hist','Prtv']},features=f,physics_model=physics,
        regime_primary=np.zeros((10,2),dtype=int),regime_primary_valid=np.ones((10,2)))
    x,_,_=extract_channel_features(b,'train',['Patv_hist','wake_score'])
    idx=np.arange(2,9)[:,None]-np.arange(3)[None,::-1]
    cols=[]
    for c in [f[idx][...,0:1],physics[idx][...,2:3]]:
        cols.extend([c[:,-1],np.mean(c,axis=1),np.std(c,axis=1),np.max(c,axis=1)])
    assert np.array_equal(x,np.concatenate(cols,axis=-1))


def test_auxiliary_heads_share_reference_targets_despite_different_forecasters(tmp_path):
    import torch
    from torch.utils.data import DataLoader
    from eval_single_task_dense_phase_scan import train_frozen_quantile_head_dynamic
    class ToyForecaster(torch.nn.Module):
        def __init__(self,value):
            super().__init__();self.weight=torch.nn.Parameter(torch.tensor(float(value)))
        def forward(self,x,ei,ew,fm,ap):
            return self.weight.expand(x.shape[0],1,2),None,{'context':x.mean(1)}
    records=[{'x_hist':torch.zeros(1,2,3),'edge_index_hist':torch.zeros(1,2,1,dtype=torch.long),
              'edge_weight_hist':torch.ones(1,2,1),'feature_mask_hist':torch.ones(1,2,3),
              'anchor_physics':torch.zeros(2,4),'target':torch.ones(1,2),
              'target_mask':torch.ones(1,2),'anchor_index':torch.tensor(i)} for i in range(4)]
    loader=DataLoader(records,batch_size=2,shuffle=True)
    reference,other=ToyForecaster(2),ToyForecaster(100)
    torch.manual_seed(201)
    train_frozen_quantile_head_dynamic(reference,loader,torch.device('cpu'),max_cache_batches=2,
        epochs=1,archive_dir=tmp_path/'reference',forecast_reference=reference)
    torch.manual_seed(201)
    train_frozen_quantile_head_dynamic(other,loader,torch.device('cpu'),max_cache_batches=2,
        epochs=1,archive_dir=tmp_path/'other',forecast_reference=reference,
        shared_targets=tmp_path/'reference/training_targets.npz')
    a=np.load(tmp_path/'reference/training_targets.npz');b=np.load(tmp_path/'other/training_targets.npz')
    assert np.array_equal(a['anchor_indices'],b['anchor_indices'])
    assert np.all(b['shortfall']==1)  # Not the second forecaster's shortfall of99.


def test_raw_replay_gate_rejects_deleted_scope_even_with_pass_review(tmp_path):
    from verify_raw_replay import verify
    from replay_provenance import sha256
    write_json(tmp_path/'historical_ARTIFACT_MANIFEST.json',[{'filename':'required_experiment.csv'}])
    write_json(tmp_path/'coverage.json',[])
    write_json(tmp_path/'final_independent_review.json',{'scope':'raw-data-to-manuscript','verdict':'PASS',
        'coverage_sha256':sha256(tmp_path/'coverage.json')})
    failures,_,_=verify(tmp_path)
    assert any('scope was removed' in x for x in failures)


def test_factorial_unknown_state_uses_calibrated_global_fallback():
    from replay_factorial import categorical
    result=categorical(np.array([0,1,2]),np.array([3,0,1]),np.array([10.,20.,30.]),np.array([True,True,True]))
    assert result[0]==28. and np.all(result>0)
