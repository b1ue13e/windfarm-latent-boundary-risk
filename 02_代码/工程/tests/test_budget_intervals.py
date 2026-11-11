"""Independent closed-form interval expectations on synthetic traces."""
from dataclasses import replace
from fractions import Fraction as F
import pytest
from windfarm_moe.budget_diagnostic_core import COORDINATES, assess_coordinate, summarize_spans
from windfarm_moe.budget_intervals import Interval, MetricRecord, infer_family


def identity(span=3):
    return dict(mode='SYNTHETIC',verified=True,span=span,
                source_sha256='1'*64,rules_sha256='2'*64,draw_sha256='3'*64)


@pytest.fixture(scope='module')
def closed_form():
    p={k:MetricRecord(F(-1,4),F(-1,4)) for k in COORDINATES}
    d={k:[MetricRecord(v,v) for v in [F(-1,8),F(-3,8)]*10000] for k in COORDINATES}
    return p,d,infer_family(p,d,span=3,source_identity=identity())


def test_complete_interval_against_closed_form_without_using_producer_sd(closed_form):
    _,_,(rows,metadata)=closed_form
    # Every absolute standardized deviation is (1/8)/sd, so radius=1/8.
    # This expectation uses no production variance/max/quantile implementation.
    for row in rows:
        assert row.lower == -3/8 and row.upper == -1/8
        assert row.numeric.lower[0]<=F(-3,8)<=row.numeric.lower[1]
        assert row.numeric.upper[0]<=F(-1,8)<=row.numeric.upper[1]
        assert assess_coordinate(row)=='SUPPORTED'
    assert metadata['order_statistic_position']==19000
    assert summarize_spans({3:rows})['primary']['joint_supported']
    assert not metadata['statistical_coverage_certified']


def test_certificate_and_source_mutation_are_detected(closed_form):
    _,_,(rows,meta)=closed_form
    row=rows[0]
    for change in [dict(coordinate_id='AZ_S_U'),dict(span=1),dict(source_binding='0'*64),dict(upper=-.01)]:
        assert assess_coordinate(replace(row,**change))!='SUPPORTED'
    assert meta['trace_sha256'] and meta['algorithm_sha256'] and meta['core_sha256']


def test_draw_failure_is_endpoint_specific_and_does_not_drop_draw_ids(closed_form):
    p,d,_=closed_form;draws={k:list(v) for k,v in d.items()}
    draws['AP_M_V'][123]=MetricRecord(None,None,'UNSUPPORTED_MAPPING','zero_base')
    rows,meta=infer_family(p,draws,span=3,source_identity=identity())
    by={x.coordinate_id:x for x in rows}
    assert by['AP_M_V'].interval_status=='UNINFORMATIVE_DRAW_SUPPORT'
    assert (by['AP_M_V'].lower,by['AP_M_V'].upper)==(-1.,1.)
    assert meta['failed_draw_ids']['AP_M_V']==[123]
    result=summarize_spans({3:rows})['primary']
    assert result['U_supported'] and not result['V_supported']


def test_constant_nonexact_family_has_null_critical():
    p={k:MetricRecord(F(),F()) for k in COORDINATES}
    d={k:[MetricRecord(F(),F())]*20000 for k in COORDINATES}
    rows,meta=infer_family(p,d,span=3,source_identity=identity())
    assert meta['critical_value'] is None and not meta['active_coordinate_ids']
    assert all(x.interval_status=='UNINFORMATIVE_VARIANCE' for x in rows)
    assert all(x.lower is None and x.upper is None for x in rows if x.coordinate_id.endswith('_U'))
    assert summarize_spans({3:rows})['primary']['family_status']=='NO_ESTIMABLE_INTERVALS'


def test_numeric_changes_cannot_manufacture_negative_upper(closed_form):
    p,d,_=closed_form
    # Represented traces are favorable; ideal complete interval crosses zero.
    true_p={k:replace(v,ideal=F()) for k,v in p.items()}
    true_d={k:[replace(v,ideal=v.ideal+F(1,4)) for v in values] for k,values in d.items()}
    rows,_=infer_family(true_p,true_d,span=3,source_identity=identity())
    assert all(assess_coordinate(row)=='NUMERIC_UNRESOLVED' for row in rows)


def test_no_new_minimum_effect_epsilon(closed_form):
    p,d,_=closed_form
    factor=F(1,10**30)
    # Shift point and both draws together: variability stays safely above sd cutoff,
    # but the upper endpoint is negative by only 1e-30.
    pp={k:MetricRecord(F(-1,8)-factor,F(-1,8)-factor) for k in COORDINATES}
    dd={k:[MetricRecord(v,v) for v in [-factor,F(-1,4)-factor]*10000] for k in COORDINATES}
    rows,_=infer_family(pp,dd,span=3,source_identity=identity())
    assert all(assess_coordinate(row)=='SUPPORTED' for row in rows)


def test_rational_outward_sqrt_and_division_contain_exact_value():
    for value in [F(2),F(1,3),F(1,10**60)]:
        result=Interval.rational(value).sqrt()
        assert F(result.lo)**2<=value<=F(result.hi)**2
    div=Interval.rational(F(2,3))/Interval.rational(F(7,11))
    assert F(div.lo)<=F(22,21)<=F(div.hi)


def test_missing_draw_is_rejected_not_replaced(closed_form):
    p,d,_=closed_form;d=dict(d);d['AP_M_U']=d['AP_M_U'][:-1]
    with pytest.raises(ValueError,match='Every original draw'):infer_family(p,d,span=3,source_identity=identity())


def test_joint_critical_against_independent_exact_squared_deviations():
    p={k:MetricRecord(F(-1,4),F(-1,4)) for k in COORDINATES}
    patterns=([F(-1,8),F(-3,8)], [F(-1,4)]*3+[F(3,4)],
              [F(-1,2),F(-1,4),F(),F(1,4)])
    columns={k:(list(patterns[j%3])*(20000//len(patterns[j%3]))) for j,k in enumerate(COORDINATES)}
    d={k:[MetricRecord(x,x) for x in values] for k,values in columns.items()}
    rows,meta=infer_family(p,d,span=3,source_identity=identity())
    n=20000;variances={}
    for key,values in columns.items():
        average=sum(values,F())/n
        variances[key]=sum(((x-average)**2 for x in values),F())/(n-1)
    # Squaring removes every square root; all order comparisons are exact rationals.
    squared_maxima=[max((columns[k][i]-p[k].represented)**2/variances[k] for k in COORDINATES) for i in range(n)]
    critical_squared=sorted(squared_maxima)[19000]
    for row in rows:
        radius_squared=critical_squared*variances[row.coordinate_id]
        center=p[row.coordinate_id].represented
        lower_lo,lower_hi=row.numeric.lower
        upper_lo,upper_hi=row.numeric.upper
        assert center-lower_lo>=0 and (center-lower_lo)**2>=radius_squared
        if center-lower_hi>=0:assert (center-lower_hi)**2<=radius_squared
        assert upper_hi-center>=0 and (upper_hi-center)**2>=radius_squared
        if upper_lo-center>=0:assert (upper_lo-center)**2<=radius_squared


def test_empirical_sd_threshold_is_preserved_on_both_sides():
    p={k:MetricRecord(F(),F()) for k in COORDINATES}
    d={}
    for j,k in enumerate(COORDINATES):
        delta=F(99 if j%2==0 else 101,100)*F.from_float(1e-14)
        d[k]=[MetricRecord(x,x) for x in [delta,-delta]*10000]
    rows,_=infer_family(p,d,span=3,source_identity=identity())
    for j,row in enumerate(rows):
        assert row.interval_status==('UNINFORMATIVE_VARIANCE' if j%2==0 else 'ESTIMABLE_APPROX')
