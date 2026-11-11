import importlib.util
from repo_paths import Path, repository_root

import numpy as np
import pytest

ROOT=Path(repository_root())
SPEC=importlib.util.spec_from_file_location('e07_inventory',ROOT/'scripts/audit_e07_window_inventory.py')
audit=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def test_245_day_cache_cannot_supply_registered_future_window():
    record=audit.assess_coordinates(np.arange(35280),np.arange(1,135))
    assert record['missing_required_time_positions']==5064
    assert not record['structurally_covers_E07']


def test_padding_is_required_even_with_all_test_issue_times():
    record=audit.assess_coordinates(np.arange(40320),np.arange(1,135))
    assert record['missing_required_time_positions']==24
    assert not record['structurally_covers_E07']


def test_future_shapes_do_not_prove_unseen_or_source_identity():
    record=audit.assess_coordinates(np.arange(40344),np.arange(1,135))
    assert record['structurally_covers_E07']
    assert not record['eligible_confirmatory_window']
    assert 'UNVIEWED_STATUS_UNVERIFIED' in record['rejection_reasons']


def test_reordered_or_different_nodes_are_not_silently_accepted():
    record=audit.assess_coordinates(np.arange(40344),np.arange(134,0,-1))
    assert not record['node_order_exact']
    assert not record['eligible_confirmatory_window']


def test_cache_reader_never_loads_target_payload(tmp_path,monkeypatch):
    import json
    (tmp_path/'metadata.json').write_text(json.dumps({'dataset':'wtb','num_steps':35280,'num_nodes':134}))
    time=np.stack([np.arange(35280)//144+1,np.arange(35280)%144],axis=1)
    np.save(tmp_path/'time_index.npy',time)
    np.save(tmp_path/'node_ids.npy',np.arange(1,135))
    # Header is allowed; payload would contain a deliberately irrelevant sentinel.
    np.save(tmp_path/'target.npy',np.array([[99999999.]],dtype=np.float32))
    original=np.load
    def safe_load(path,*args,**kwargs):
        assert Path(path).name in ('time_index.npy','node_ids.npy')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(np,'load',safe_load)
    record=audit.inspect_cache(tmp_path/'metadata.json')
    assert record['target_header']['shape']==[1,1]
    assert record['target_payload_read'] is False
    assert not record['eligible_confirmatory_window']


def test_raw_csv_projects_identity_columns_only(tmp_path):
    path=tmp_path/'wtbdata.csv'
    path.write_text('TurbID,Day,Tmstamp,Patv\n1,245,23:50,DO_NOT_PARSE\n2,245,23:50,DO_NOT_PARSE\n')
    record=audit.inspect_raw_csv(path)
    assert record['projected_columns']==['TurbID','Day','Tmstamp']
    assert record['max_day']==245
    assert record['outcome_columns_interpreted'] is False
    assert record['raw_sha256']==audit.sha(path)


def test_error_or_structural_candidate_is_not_reported_as_definitive_absence():
    spec=importlib.util.spec_from_file_location('e07_final',ROOT/'scripts/finalize_e07_data_audit.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    record={'structural_future_candidate_count':0,'confirmed_eligible_window_count':0,'walk_and_inspection_errors':[]}
    assert module.evaluate_inventory_reports([record])=='NO_ELIGIBLE_WINDOW_FOUND_IN_AUDITED_SCOPES'
    assert module.evaluate_inventory_reports([{**record,'structural_future_candidate_count':1}])=='STRUCTURAL_CANDIDATE_REQUIRES_BLINDED_FOLLOWUP'
    assert module.evaluate_inventory_reports([{**record,'walk_and_inspection_errors':['unreadable']}])=='NO_VERIFIED_WINDOW_SEARCH_HAS_UNRESOLVED_ERRORS'


def test_protocol_binds_only_negative_audit_not_confirmatory_data():
    import json
    plan=json.loads((ROOT/'experiments/E07_history_only_recalibration/protocol.json').read_text(encoding='utf-8'))
    before=json.loads((ROOT/'analyses/e07_data_availability_audit_20261018/protocol_before_availability_audit.json').read_text(encoding='utf-8'))
    evidence=plan['activation']['data_availability_audit']
    assert audit.sha(ROOT/evidence['audit_manifest'])==evidence['audit_manifest_sha256']
    assert evidence['confirmed_eligible_window_count']==0
    assert plan['activation']['prospective_collection_spec_manifest_sha256'] is None
    for section in ('data','frozen_objects','gates','calibration','evaluation'):
        assert plan[section]==before[section]
