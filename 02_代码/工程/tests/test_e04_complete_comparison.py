import importlib.util
import json
from repo_paths import Path, repository_root

import pytest

ROOT=Path(repository_root())
SPEC=importlib.util.spec_from_file_location('complete_compare',ROOT/'scripts/compare_e04_complete_slices.py')
analysis=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def test_percentage_point_delta_is_scaled_once():
    rows=[{'policy':'B','axis':'wind','group':'low','n':1000,'violations':100},
          {'policy':'C','axis':'wind','group':'low','n':1000,'violations':110},
          {'policy':'D','axis':'wind','group':'low','n':1000,'violations':100},
          {'policy':'D10','axis':'wind','group':'low','n':1000,'violations':100}]
    assert analysis.paired_count_deltas(rows)[0]['C_minus_B_violation_pp']==pytest.approx(1.)


def test_pairing_rejects_method_specific_population():
    rows=[{'policy':p,'axis':'wind','group':'low','n':100 if p!='C' else 99,'violations':10}
          for p in ['B','C','D','D10']]
    with pytest.raises(ValueError,match='population'):
        analysis.paired_count_deltas(rows)


def test_coverage_requires_complete_policy_family():
    rows=[{'policy':'B','axis':'wind','group':'low','n':100,'violations':10}]
    with pytest.raises(ValueError,match='four policies'):
        analysis.paired_count_deltas(rows)


def test_plan_rejects_future_label_and_legacy_test_reuse():
    plan=analysis.proposed_protocol()
    analysis.validate_protocol(plan)
    plan['data']['calibration_latest_target_index']=plan['data']['new_test_first_anchor']
    with pytest.raises(ValueError,match='mature'):
        analysis.validate_protocol(plan)
    plan=analysis.proposed_protocol()
    plan['data']['confirmation_reuses_legacy_test']=True
    with pytest.raises(ValueError,match='legacy'):
        analysis.validate_protocol(plan)


def test_plan_forbids_risk_cap_change_and_test_updates():
    plan=analysis.proposed_protocol()
    plan['gates']['v_max']=.12
    with pytest.raises(ValueError,match='threshold'):
        analysis.validate_protocol(plan)
    plan=analysis.proposed_protocol()
    plan['data']['update_using_new_test_labels']=True
    with pytest.raises(ValueError,match='test labels'):
        analysis.validate_protocol(plan)
    plan=analysis.proposed_protocol()
    plan['calibration']['score_quantile']=.95
    with pytest.raises(ValueError,match='quantile threshold'):
        analysis.validate_protocol(plan)


def test_saved_protocol_is_valid_but_not_activated():
    plan=json.loads((ROOT/'experiments/E07_history_only_recalibration/protocol.json').read_text(encoding='utf-8'))
    analysis.validate_protocol(plan)
    assert plan['status']=='DRAFT_NOT_EXECUTED_PENDING_ACTIVATION_MANIFESTS'
    assert plan['activation']['prospective_collection_spec_manifest_sha256'] is None
    assert plan['calibration']['bootstrap_upper_quantile_method']=='linear'
