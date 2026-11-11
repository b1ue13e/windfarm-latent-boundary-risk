import numpy as np
import importlib.util
import json
from repo_paths import Path, repository_root
from types import SimpleNamespace
import zipfile
import pytest

from windfarm_moe.independent_confirmation import (
    anchor_window, features, historical_selection, confirmation_verdict, START_NS, STEP_NS)


def envelope(k):
    return dict(risk_lower=np.zeros((5, k)), risk_upper=np.full((5, k), .08),
                mean_cost=np.ones(k), relative_ratio_upper=np.zeros((k, k)))


def test_maturity_and_published_forecast_history():
    a = anchor_window('2024-07-01T00:00:00Z', '2025-01-01T00:00:00Z', 6)
    boundary = (np.datetime64('2025-01-01', 'ns').astype('i8') - START_NS) // STEP_NS
    assert a[-1] + 6 + 1 < boundary
    assert a[-1] + 1 + 6 + 1 == boundary
    data = np.arange(80*2*4, dtype=float).reshape(80, 2, 4)
    old = features(data, np.array([45]), np.ones((1, 2)), 6)
    data[40:] = -9876
    np.testing.assert_array_equal(old, features(data, np.array([45]), np.ones((1, 2)), 6))


def test_historical_no_selection_and_ties_are_preserved():
    labels = ['P1/HGB/q.9', 'P1/MLP/q.9', 'WPQ36/HGB/q.9', 'WPQ36/MLP/q.9']
    e = envelope(4)
    r = historical_selection(e, labels, [[1,1,5],[1,1,5],[3,1,112],[3,1,112]], [.9], [.02], .1)
    assert r['sets']['0.02']['original_indices'] == [0,1]
    e['relative_ratio_upper'][:] = .2
    np.fill_diagonal(e['relative_ratio_upper'], 0)
    r = historical_selection(e, labels, [[1,1,5]]*4, [.9], [.02], .1)
    assert r['sets']['0.02']['original_indices'] == []
    assert not r['uses_confirmation']


def test_zero_variance_unknown_and_unsafe_reference_cannot_confirm():
    e = envelope(2)
    assert confirmation_verdict(e, [], 1, .02, .1, True)['status'] == 'NO_HISTORICAL_SELECTION'
    assert confirmation_verdict(e, [0], 1, .02, .1, True)['candidates'][0]['confirmed']
    assert not confirmation_verdict(e, [0], 1, .02, .1, False)['candidates'][0]['confirmed']
    e['risk_upper'][4,0] = 1
    assert not confirmation_verdict(e, [0], 1, .02, .1, True)['candidates'][0]['confirmed']


def load_runner():
    path = Path(repository_root()) / 'scripts/run_independent_confirmation.py'
    spec = importlib.util.spec_from_file_location('independent_runner_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_raw_blade_cancellation_at_year_boundary_is_rejected(tmp_path):
    m = load_runner()
    table = 'tblSCTurbine'
    fields = m.qualifier.TABLES[table]
    archive = tmp_path / '2025.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        for month in range(1,13):
            values = [5, 11, 9, 10] if month == 1 else [5, 10, 10, 10]
            text = 'TimeStamp,StationId,' + ','.join(fields) + '\n'
            text += f'2025-{month:02d}-01T00:00:00Z,2304510,' + ','.join(map(str,values)) + '\n'
            z.writestr(f'{table}_2025_{month:02d}.csv', text)
    storage = np.full(((365*144+1)*21,4), np.nan)
    seen = np.zeros(len(storage),bool)
    storage[0], seen[0] = [5,10,10,10], True
    with pytest.raises(ValueError, match='Conflicting consumed'):
        m.read_table(archive,2025,table,storage,seen)
    np.testing.assert_array_equal(storage[0], [5,10,10,10])


def test_unlock_rejects_missing_freeze_before_opening_test(tmp_path, monkeypatch):
    m = load_runner()
    def forbidden(*args, **kwargs):
        raise AssertionError('Sealed ZIP was opened')
    monkeypatch.setattr(m.zipfile, 'ZipFile', forbidden)
    args = SimpleNamespace(output=tmp_path, protocol=tmp_path/'protocol.json')
    with pytest.raises(FileNotFoundError):
        m.unlock(args,{})
    assert not (tmp_path/'UNLOCK_EVENT.json').exists()


def test_raw_boundary_freeze_keeps_presence_and_all_six_fields(tmp_path):
    m = load_runner()
    archive = tmp_path/'2024.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for table, fields in m.qualifier.TABLES.items():
            values = [-2, 10, 10, 10] if len(fields)==4 else [-10, 0]
            text='TimeStamp,StationId,'+','.join(fields)+'\n'
            text+='2025-01-01T00:00:00Z,2304510,'+','.join(map(str,values))+'\n'
            z.writestr(f'{table}_2024_12.csv',text)
    for table, fields in m.qualifier.TABLES.items():
        storage, seen=np.full((21,len(fields)),np.nan),np.zeros(21,bool)
        m.read_table(archive,2024,table,storage,seen,boundary_only=True)
        assert seen[0] and not seen[1:].any()
        assert storage[0,0] < 0


def test_point_fit_matures_before_first_publication():
    first_policy = anchor_window('2023-07-01T00:00:00Z','2024-01-01T00:00:00Z',6)[0]
    boundary = np.datetime64('2023-07-01') - 6*np.timedelta64(600,'s')
    point = anchor_window('2023-01-01',str(boundary),12)
    assert point[-1]+13 < first_policy-6


def test_frozen_model_tamper_is_rejected(tmp_path):
    m = load_runner()
    args = SimpleNamespace(protocol=tmp_path/'protocol.json')
    args.protocol.write_text('{}')
    out=tmp_path/'bundle';out.mkdir()
    (out/'model.joblib').write_bytes(b'original model')
    m.save(out/'receipt.json',dict(status='COMPLETE',protocol_sha256=m.sha(args.protocol),sources={}))
    m.save(out/'manifest.json',{p.name:dict(bytes=p.stat().st_size,sha256=m.sha(p)) for p in out.iterdir()})
    m.verify(out,args,{'source_files':[]})
    (out/'model.joblib').write_bytes(b'altered model!')
    with pytest.raises(ValueError,match='Bundle identity mismatch'):
        m.verify(out,args,{'source_files':[]})


def test_old_passing_preflight_cannot_unlock_different_sources(tmp_path,monkeypatch):
    m=load_runner();monkeypatch.setattr(m,'ROOT',tmp_path)
    monkeypatch.setattr(m,'verify',lambda *args: {})
    args=SimpleNamespace(protocol=tmp_path/'protocol.json',output=tmp_path/'results')
    args.protocol.write_text('{}')
    chosen=args.output/'chosen';chosen.mkdir(parents=True)
    m.save(tmp_path/'preflight_receipt.json',dict(exit_code=0,pbs_job='old.job',sources={'old':'wrong'},
           protocol_sha256=m.sha(args.protocol),git_commit='commit'))
    m.save(tmp_path/'deployment_manifest.json',dict(git_commit='commit',sources={},protocol_sha256=m.sha(args.protocol)))
    m.save(chosen/'freeze.json',dict(preflight_receipt_sha256=m.sha(tmp_path/'preflight_receipt.json'),
           deployment_sha256=m.sha(tmp_path/'deployment_manifest.json'),sources={},protocol_sha256=m.sha(args.protocol)))
    with pytest.raises(ValueError,match='Preflight/deployment provenance'):
        m.validate_freeze(args,{'source_files':[]})
