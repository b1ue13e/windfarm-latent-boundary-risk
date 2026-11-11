"""Synthetic-only exact expectations; no experiment assets or bootstrap."""
from dataclasses import replace
from fractions import Fraction as F
import inspect

import numpy as np
import pytest

from windfarm_moe.budget_diagnostic_core import (
    COORDINATES, SEEDS, CoordinateEvidence, NumericCertificate, assess_coordinate,
    budget_map, budget_of, combine_fits, map_pair, score_pair, summarize_spans,
    validate_population, bind_certificate,
)


def rational(x):
    return F.from_float(float(x))


def oracle_shift(actions, weights, budget):
    """Independent rational bisection, not the implementation's active-set solver."""
    pairs=[(rational(x),int(w)) for x,w in zip(actions,weights) if w]
    n=sum(w for _,w in pairs)
    if budget==0:return -max(x for x,_ in pairs),-max(x for x,_ in pairs)
    lo=-max(x for x,_ in pairs);hi=6*budget/n
    def value(c):return sum((w*max(x+c,F(0)) for x,w in pairs),F(0))/6
    if value(hi)==budget:return hi,hi
    for _ in range(320):
        mid=(lo+hi)/2;v=value(mid)
        if v==budget:return mid,mid
        if v<budget:lo=mid
        else:hi=mid
    return lo,hi


@pytest.mark.parametrize('method',['M','S'])
@pytest.mark.parametrize('actions',[[0.,0.,0.],[1.,7.,3.]])
def test_zero_budget_precedes_identity_and_never_divides(method,actions):
    result=budget_map(actions,F(0),method)
    assert result.status=='ZERO_BUDGET'
    np.testing.assert_array_equal(result.actions,np.zeros(3))
    assert result.coefficient==(0. if method=='M' else -max(actions))
    assert result.residual==0 and result.action_error==0


def test_positive_budget_zero_base_is_method_specific():
    m=budget_map([0.,0.],F(1),'M')
    s=budget_map([0.,0.],F(1),'S')
    assert m.status=='UNSUPPORTED_MULTIPLICATIVE' and m.actions is None
    assert s.supported
    np.testing.assert_array_equal(s.actions,[3.,3.])


@pytest.mark.parametrize('method',['M','S'])
def test_positive_own_budget_is_bitwise_identity(method):
    a=np.asarray([1.,-0.,3.,8.]);original=a.copy()
    result=budget_map(a,budget_of(a),method)
    assert result.status=='IDENTITY'
    assert result.actions.tobytes()==a.tobytes()
    assert not result.actions.flags.writeable
    np.testing.assert_array_equal(a,original)


@pytest.mark.parametrize('actions,weights,budget,expected',[
    ([1.,3.,8.],[1,1,1],F(4,6),F(-4)),
    ([1.,3.,8.],[2,0,3],F(12,6),F(-4)),
    ([1.,1.,4.],[1,3,2],F(6,6),F(-1)),
    ([0.,0.,0.],[1,9,2],F(1),F(1,2)),
])
def test_clipped_root_exact_precomputed_expectations(actions,weights,budget,expected):
    result=budget_map(actions,budget,'S',weights)
    assert result.supported and result.ideal_coefficient==expected
    lo,hi=oracle_shift(actions,weights,budget)
    assert lo<=result.ideal_coefficient<=hi
    assert abs(result.residual)<=F(1,10**8)


@pytest.mark.parametrize('seed',[201,202,203,204,205])
@pytest.mark.parametrize('method',['M','S'])
def test_exact_oracle_on_fixed_synthetic_weighted_cases(seed,method):
    rng=np.random.default_rng(seed)
    for _ in range(8):
        a=rng.integers(0,80,9)/8
        w=rng.integers(0,12,9);w[0]=1
        b=F(int(rng.integers(1,150)),24)
        result=budget_map(a,b,method,w)
        assert result.supported
        if method=='S':
            lo,hi=oracle_shift(a,w,b)
            assert lo<=result.ideal_coefficient<=hi
        else:
            exact=sum((int(v)*rational(x) for x,v in zip(a,w)),F(0))/6
            assert result.ideal_coefficient==b/exact
        actual=sum((int(v)*rational(x) for x,v in zip(result.actions,w)),F(0))/6
        assert result.residual==(actual-b)/sum(map(int,w))
        error=sum((int(v)*abs(rational(x)-ideal) for x,ideal,v in zip(result.actions,result.ideal_actions,w)),F(0))/(6*sum(map(int,w)))
        assert result.action_error==error


def test_zero_weights_do_not_define_population_or_maximum():
    x=budget_map([1.,1e100],F(0),'S',[1,0])
    assert x.coefficient==-1
    assert x.n_weight==1
    assert budget_map([1.],F(1),'S',[0]).status=='UNDEFINED_POPULATION'


@pytest.mark.parametrize('a,w,b',[
    ([np.nan],[1],F(1)),([-1.],[1],F(1)),([1.],[-1],F(1)),
    ([1.],[.5],F(1)),([1.],[1],float('inf')),([1.],[1],F(-1)),
])
def test_invalid_source_is_not_coerced(a,w,b):
    assert budget_map(a,b,'S',w).status=='SOURCE_INVALID'


def test_high_dynamic_range_error_is_certified_not_hidden_by_budget_tolerance():
    p=budget_map([1e8],rational(.1)/6,'S')
    z=budget_map([.1],budget_of([.1]),'S')
    assert p.supported and abs(p.residual)<F(1,10**8)
    score=score_pair([.1],p,z)
    assert score.ideal_U==0
    assert score.U_error>=abs(rational(score.U))
    assert score.U_state=='NUMERIC_UNRESOLVED'
    assert score.V_state=='NUMERIC_UNRESOLVED'


def test_exact_target_equality_is_not_an_event_and_zero_purchase_not_zero_risk():
    p=budget_map([1.,2.],budget_of([1.,2.]),'M')
    equal=score_pair([1.,2.],p,p)
    assert equal.U==equal.V==0
    zero=budget_map([1.,2.],F(0),'M')
    scored=score_pair([1.,2.],zero,zero)
    assert scored.P_V==scored.Z_V==1 and scored.U==scored.V==0


def test_target_cannot_affect_mapping_or_coefficient():
    assert 'shortfall' not in inspect.signature(budget_map).parameters
    p=budget_map([1.,2.],F(1),'S');before=p.actions.tobytes(),p.coefficient
    score_pair([0.,2.],p,p);score_pair([100.,200.],p,p)
    assert before==(p.actions.tobytes(),p.coefficient)


def test_pair_budget_or_weight_mismatch_is_not_scored():
    p=budget_map([1.,2.],F(1),'S')
    z=budget_map([1.,2.],F(2),'S')
    assert score_pair([1.,2.],p,z).U_state=='SOURCE_UNAVAILABLE'


def test_common_population_validation_and_masked_missingness():
    a=np.asarray([10,11]);m=np.asarray([[True,False],[True,True]])
    s=np.asarray([[1.,np.nan],[0.,2.]])
    assert validate_population(a,m,s,a.copy(),m.copy(),s.copy())=='VALID'
    changed=s.copy();changed[1,0]=3
    assert validate_population(a,m,s,a,m,changed)=='SOURCE_MISMATCH'
    assert validate_population(a,m,s,a[::-1],m,s)=='SOURCE_MISMATCH'


def ev(key='AP_M_U',point=F(-1,5),lower=F(-3,10),upper=F(-1,10),**kwargs):
    settings=dict(critical_value=3.,all_draws_legal=True,n_draws=20000)
    settings.update(kwargs)
    return bind_certificate(CoordinateEvidence(key,3,float(point),float(lower),float(upper),
        numeric=NumericCertificate.exact(point,lower,upper),**settings),'a'*64)


def test_budget_or_point_precision_alone_cannot_certify_interval_direction():
    assert assess_coordinate(replace(ev(),numeric=None))=='NUMERIC_UNRESOLVED'
    tiny=ev(point=F(-2,10**12),lower=F(-3,10**12),upper=F(-1,10**12))
    certificate=NumericCertificate.exact(F(-1,10**12),F(-4,10**12),F(0))
    assert assess_coordinate(replace(tiny,numeric=certificate))=='NUMERIC_UNRESOLVED'


@pytest.mark.parametrize('change',[
    dict(all_draws_legal=False),dict(n_draws=19999),dict(seed_ids=(201,202,203,204)),
    dict(interval_status='UNINFORMATIVE_VARIANCE'),dict(point_status='UNSUPPORTED_MAPPING'),
])
def test_missing_support_seed_or_variance_cannot_pass(change):
    assert assess_coordinate(replace(ev(),**change))=='UNAVAILABLE_OR_UNINFORMATIVE'


def test_rounded_zero_and_nonfinite_bounds_are_not_success():
    assert assess_coordinate(ev(upper=F(0)))=='UNRESOLVED'
    assert assess_coordinate(replace(ev(),upper=float('nan')))=='UNAVAILABLE_OR_UNINFORMATIVE'
    assert assess_coordinate(replace(ev(),interval_status='NUMERIC_UNRESOLVED'))=='NUMERIC_UNRESOLVED'


def test_U_V_joint_and_sensitivity_are_separate():
    primary=[ev(k) if k.endswith('_U') else ev(k,point=F(0),lower=F(-1),upper=F(1)) for k in COORDINATES]
    result=summarize_spans({3:primary})
    assert result['primary']['U_supported'] is True
    assert result['primary']['V_supported'] is False and result['primary']['joint_supported'] is False
    all_good=[ev(k) for k in COORDINATES]
    other=[bind_certificate(replace(e,span=1),'a'*64) for e in all_good]
    seven=[bind_certificate(replace(e,span=7),'a'*64) for e in all_good]
    no_rescue=summarize_spans({3:primary,1:other,7:seven})
    assert no_rescue['V_span_robust'] is False
    assert no_rescue['U_span_robust'] is True
    missing=summarize_spans({3:all_good[:-1]})
    assert COORDINATES[-1] in missing['primary']['unavailable_ids']
    assert missing['primary']['U_supported'] and not missing['primary']['joint_supported']


def test_not_executed_flags_remain_null_and_family_keeps_eight_slots():
    result=summarize_spans({},executed=False)
    assert result['primary']['U_supported'] is None
    assert result['primary']['joint_supported'] is None
    assert len(result['primary']['coordinates'])==8


def test_adverse_and_partial_results_do_not_trigger_early_return():
    rows=[ev(k) for k in COORDINATES]
    rows[1]=ev(COORDINATES[1],point=F(2,10),lower=F(1,10),upper=F(3,10))
    r=summarize_spans({3:rows})['primary']
    assert r['U_supported'] and not r['V_supported']
    assert COORDINATES[1] in r['adverse_ids']
    assert r['supported_opposite_directions']['V']


def test_five_fit_contrasts_not_ensemble_actions_and_missing_fit_not_replaced():
    scores={}
    for seed,power in zip(SEEDS,[[0.,2.],[0.,2.],[0.,2.],[2.,0.],[2.,0.]]):
        p=budget_map(power,budget_of(power),'M')
        z=budget_map([1.,1.],budget_of(power),'M')
        scores[seed]=score_pair([1.,1.],p,z)
    combined=combine_fits(scores)
    assert combined.ideal_U==F(-1,12)
    assert combined.U!=float(F(-1,60))  # Counterfactual ensemble-action endpoint.
    del scores[205]
    assert combine_fits(scores).U_state=='SOURCE_UNAVAILABLE'


def test_malformed_numeric_certificate_cannot_force_support():
    invalid=NumericCertificate((float('-inf'),float('-inf')),(F(-3),F(-3)),(F(-1),F(-1)),'untrusted')
    assert assess_coordinate(replace(ev(),numeric=invalid))=='NUMERIC_UNRESOLVED'


def test_bad_fit_metric_does_not_destroy_the_other_metric():
    p=budget_map([1.,2.],budget_of([1.,2.]),'M')
    score=score_pair([1.,2.],p,p)
    scores={s:score for s in SEEDS};scores[205]=replace(score,U=float('nan'))
    combined=combine_fits(scores)
    assert combined.U_state=='SOURCE_UNAVAILABLE'
    assert combined.V==0 and combined.V_state=='DEFINED'


def test_node_axis_order_is_part_of_source_identity():
    a=np.asarray([10]);m=np.asarray([[True,True]]);s=np.asarray([[1.,1.]])
    assert validate_population(a,m,s,a,m,s,node_ids_p=[1,2],node_ids_z=[2,1])=='SOURCE_MISMATCH'


def test_empty_variance_family_keeps_points_without_default_zero_critical():
    rows=[replace(ev(k,point=F(0),lower=F(-1),upper=F(1)),interval_status='UNINFORMATIVE_VARIANCE') for k in COORDINATES]
    r=summarize_spans({3:rows})['primary']
    assert r['family_status']=='NO_ESTIMABLE_INTERVALS' and r['critical_value'] is None
    assert all(r['endpoint_values'][k]['point']==0 for k in COORDINATES)
    assert not r['joint_supported']


def test_V_only_support_remains_when_U_is_numeric_unresolved():
    rows=[replace(ev(k),point_status='NUMERIC_SENSITIVE') if k.endswith('_U') else ev(k) for k in COORDINATES]
    r=summarize_spans({3:rows})['primary']
    assert r['V_supported'] and not r['U_supported'] and not r['joint_supported']


def test_unknown_ids_and_spans_are_not_silently_dropped():
    with pytest.raises(ValueError):summarize_spans({3:[replace(ev(),coordinate_id='EXTRA_U')]})
    with pytest.raises(ValueError):summarize_spans({5:[]})
    with pytest.raises(ValueError):summarize_spans({3:[ev(),ev()]})


def test_extreme_weights_and_unselected_missing_values_have_exact_root_certificate():
    a=[1e8,.1,3.];w=[1,10**12,17];b=budget_of(a,w)*F(3,5)
    mapped=budget_map(a,b,'S',w)
    assert mapped.supported
    lo,hi=oracle_shift(a,w,b)
    assert lo<=mapped.ideal_coefficient<=hi
    masked=budget_map([2.,np.nan],F(1,6),'M',[1,0])
    assert masked.supported and score_pair([1.,np.nan],masked,masked).U==0


def test_exact_certificate_detects_error_even_without_neighbor_warning():
    p=budget_map([1.],budget_of([1.]),'M')
    bad_actions=np.asarray([1.-1e-9]);bad_actions.flags.writeable=False
    injected=replace(p,actions=bad_actions,neighbors=())
    score=score_pair([1.],injected,p)
    assert score.U_state==score.V_state=='NUMERIC_UNRESOLVED'


def test_near_equal_budget_cost_identity_uses_actual_residual_not_exact_zero():
    p=budget_map([1e8],rational(.1)/6,'S');z=budget_map([.1],budget_of([.1]),'S')
    s=rational(.1)
    rp,rz=rational(p.actions[0])/6,rational(z.actions[0])/6
    up,uz=max(s-rational(p.actions[0]),F(0))/6,max(s-rational(z.actions[0]),F(0))/6
    dc=(rz+10*uz)-(rp+10*up)
    assert dc-10*(uz-up)==rz-rp and rz-rp!=0


def test_anchor_identity_never_follows_high_or_low_budget_and_no_slot_is_removed():
    for a,b in [([10.,2.],[1.,1.]),([1.,1.],[10.,2.]),([1.,1.],[1.,1.])]:
        for anchor in ['P','Z']:
            for method in ['M','S']:
                mapped=map_pair(a,b,anchor,method)
                assert mapped.setting_id=='A'+anchor+'_'+method
                assert mapped.P.budget==mapped.Z.budget==budget_of(a if anchor=='P' else b)


def test_all_four_favorable_action_settings_do_not_create_information_claim():
    a=[1.,2.,3.,4.,5.];b=[1.,3.,5.,8.,11.];s=[0.,0.,0.,4.1,10.]
    for anchor in ['P','Z']:
        for method in ['M','S']:
            setting=map_pair(a,b,anchor,method)
            score=score_pair(s,setting.P,setting.Z)
            assert score.ideal_U<0 and score.ideal_V<0
    flags=summarize_spans({3:[ev(k) for k in COORDINATES]})
    assert not flags['post_selection_adjusted'] and not flags['coverage_certified']
    assert flags['transformed_action_qualification']=='NOT_EVALUATED'


@pytest.mark.parametrize('change',[
    dict(family_id='OLD_620'),dict(alpha=.1),dict(critical_value=None),dict(critical_value=0.)
])
def test_old_or_incomplete_family_metadata_cannot_pass(change):
    assert assess_coordinate(replace(ev(),**change))=='UNAVAILABLE_OR_UNINFORMATIVE'


def test_two_pointwise_critical_values_cannot_masquerade_as_one_joint_family():
    rows=[ev(k) for k in COORDINATES];rows[-1]=replace(rows[-1],critical_value=1.96)
    with pytest.raises(ValueError,match='one joint family'):
        summarize_spans({3:rows})


def test_float_interval_bounds_cannot_be_relabelled_as_exact_arithmetic():
    with pytest.raises(TypeError,match='exact rational'):
        NumericCertificate.exact(-2.,-3.,-1.)


def test_exact_integer_certificate_does_not_round_through_binary64():
    value=10**20+1
    c=NumericCertificate.exact(-value,-value-1,-value+1)
    assert c.point==(F(-value),F(-value))
