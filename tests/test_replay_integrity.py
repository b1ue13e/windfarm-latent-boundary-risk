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
    (tmp_path/'WT_static.csv').write_text('Alternative Title,Latitude,Longitude\nKWF1,52.4,-0.9\nKWF2,52.5,-1.0\n',encoding='utf-8')
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
