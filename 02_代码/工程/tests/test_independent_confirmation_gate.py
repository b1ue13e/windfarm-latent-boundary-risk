import importlib.util
from repo_paths import Path, repository_root
import pytest

path=Path(repository_root())/'scripts/verify_independent_confirmation_gate.py'
spec=importlib.util.spec_from_file_location('confirmation_claim_gate_test',path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def fixture():
    primary=dict(labels=['P1','Full'],uses_test_selection=False,
        bounds={'groups':[dict(risk_upper=[[.06,.06]]*5,mean_cost=[100.5,100],
            relative_ratio_point=[[0,.005],[-1/201,0]],relative_ratio_upper=[[0,.01],[0,0]])]},
        verdict={'status':'ALL_FROZEN_CANDIDATES_CONFIRMED','candidates':[{'confirmed':True}]})
    choices=dict(uses_confirmation=False,groups=[dict(condition='pitch_withheld',labels=['P1','Full'],
        sets={'0.02':{'original_indices':[0]}},reference_index=1,reference_historically_qualified=True)])
    return primary,choices,dict(v_max=.1,primary_epsilon=.02)


def test_gate_accepts_bounded_noninferiority_not_only_cost_winners():
    assert m.check_primary(*fixture())=='ALL_FROZEN_CANDIDATES_CONFIRMED'


@pytest.mark.parametrize('change',['risk','cost','selection'])
def test_gate_rejects_overclaiming_confirmation(change):
    primary,choices,cfg=fixture()
    if change=='risk':primary['bounds']['groups'][0]['risk_upper'][0]=[.2,.06]
    if change=='cost':primary['bounds']['groups'][0]['relative_ratio_upper'][0][1]=.04
    if change=='selection':primary['uses_test_selection']=True
    with pytest.raises(AssertionError):m.check_primary(primary,choices,cfg)


def test_gate_preserves_truthful_negative_outcome():
    primary,choices,cfg=fixture();primary['bounds']['groups'][0]['relative_ratio_upper'][0][1]=.04
    primary['verdict']={'status':'CONFIRMATION_NOT_ESTABLISHED','candidates':[{'confirmed':False}]}
    assert m.check_primary(primary,choices,cfg)=='CONFIRMATION_NOT_ESTABLISHED'


def secondary_fixture():
    return dict(risk_lower=[[.15,.03]]*5,risk_upper=[[.2,.08]]*5,
       relative_ratio_lower=[[0,0],[0,0]],relative_ratio_upper=[[0,0],[.01,0]],resources=[[0,1,4],[1,1,5]],
       secondary_retrospective_full_q=[dict(epsilon=.02,sufficient_set=dict(minimum_resource_indices=[1],
          eligible_indices=[1],risk_qualified_indices=[1],possible_feasible_indices=[1]),
          minimum_audit=dict(status='FINITE_FAMILY_MINIMUM_IDENTIFIED',chosen=[1],smaller=[0],
                             excluded=[dict(index=0)],unresolved=[]))])


def test_secondary_gate_checks_exclusion_not_just_sufficient_set():
    group=secondary_fixture()
    assert m.check_secondary(group,{'v_max':.1})==['FINITE_FAMILY_MINIMUM_IDENTIFIED']
    group['risk_lower']=[[.05,.03]]*5
    group['secondary_retrospective_full_q'][0]['sufficient_set']['possible_feasible_indices']=[0,1]
    with pytest.raises(AssertionError,match='Secondary minimality overclaim'):
        m.check_secondary(group,{'v_max':.1})


def test_secondary_gate_accepts_unresolved_minimum():
    group=secondary_fixture();group['risk_lower']=[[.05,.03]]*5
    row=group['secondary_retrospective_full_q'][0];row['sufficient_set']['possible_feasible_indices']=[0,1]
    row['minimum_audit'].update(status='MINIMUM_UNRESOLVED',excluded=[],unresolved=[0])
    assert m.check_secondary(group,{'v_max':.1})==['MINIMUM_UNRESOLVED']
