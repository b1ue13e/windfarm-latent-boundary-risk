"""Repair regressions on constructed values; no real action input."""
from dataclasses import replace
from fractions import Fraction as F
import pytest
from windfarm_moe.budget_diagnostic_core import (
    COORDINATES, SEEDS, CoordinateEvidence, NumericCertificate, bind_certificate,
    budget_map, map_pair, score_pair, combine_fits, assess_coordinate, summarize_spans,
)


def fixture(key='AP_M_U', **changes):
    row = CoordinateEvidence(key,3,-.2,-.3,-.1,
        NumericCertificate.exact(F(-1,5),F(-3,10),F(-1,10)),
        all_draws_legal=True,n_draws=20000,critical_value=3.)
    return bind_certificate(replace(row,**changes),'a'*64)


def test_U_mean_not_vetoed_by_finite_per_fit_rounding():
    zero=map_pair([1e8,1e8],[.1,.1],'Z','S')
    good=map_pair([0.,2.],[1.,1.],'Z','S')
    scores={s:score_pair([.1,0.],good.P,good.Z) for s in SEEDS}
    scores[201]=score_pair([.1,0.],zero.P,zero.Z)
    out=combine_fits(scores)
    assert out.U_state=='DEFINED' and F.from_float(out.U)+out.U_error<0
    assert out.V_state=='NUMERIC_UNRESOLVED'


def test_V_invalid_point_cannot_pass_even_with_binding():
    row=fixture('AP_M_V',point=-2.,lower=-3.,upper=-1.,numeric=NumericCertificate.exact(-2,-3,-1))
    assert assess_coordinate(row)=='UNAVAILABLE_OR_UNINFORMATIVE'


def test_certificate_cannot_be_moved_or_changed():
    row=fixture()
    assert assess_coordinate(row)=='SUPPORTED'
    for changes in [dict(coordinate_id='AZ_S_U'),dict(span=1),dict(point=-.21),dict(source_binding='b'*64)]:
        assert assess_coordinate(replace(row,**changes))!='SUPPORTED'
    raw=replace(row,numeric=NumericCertificate.exact(F(-1,5),F(-3,10),F(-1,10)))
    assert assess_coordinate(raw)=='NUMERIC_UNRESOLVED'


def test_numeric_solver_reason_and_empty_family_preserved():
    failed=budget_map([1.],F(10)**400,'M')
    score=score_pair([1.],failed,failed)
    assert score.U_state==score.V_state=='NUMERIC_UNRESOLVED'
    assert 'SOLVER_NUMERIC_UNRESOLVED' in score.reasons
    rows=[fixture(k,point_status='NUMERIC_UNRESOLVED') for k in COORDINATES]
    out=summarize_spans({3:rows})['primary']
    assert out['family_status']=='NO_ESTIMABLE_INTERVALS' and out['critical_value'] is None


def test_draw_completeness_is_not_a_default_claim():
    row=CoordinateEvidence('AP_M_U',3,-.2,-.3,-.1)
    assert row.all_draws_legal is False and row.n_draws==0


def test_entire_records_from_other_source_cannot_be_mixed_into_family():
    rows=[fixture(k) for k in COORDINATES]
    rows[-1]=bind_certificate(rows[-1],'b'*64)
    with pytest.raises(ValueError,match='source/trace bindings'):
        summarize_spans({3:rows})
