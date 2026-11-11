import pytest
from scripts.audit_em1_008 import subtract_intervals,ratio_contrast_intervals,valid_interval

def test_shared_reference_interval_bridge_independent_corner_values():
    # G/S in [-1/5,1/10], P/S in [-1/10,1/5].
    # G/P extrema: (4/5)/(6/5)-1=-1/3, (11/10)/(9/10)-1=2/9.
    bound=ratio_contrast_intervals([-.2,.1],[-.1,.2])
    assert bound==pytest.approx([-1/3,2/9])
    assert subtract_intervals([2,5],[-3,4])==[-2,8]

def test_undefined_and_zero_denominator_never_become_zero_or_success():
    assert ratio_contrast_intervals([-.1,.2],[-1,.2]) is None
    assert ratio_contrast_intervals(None,[0,.2]) is None
    assert subtract_intervals([0,1],None) is None
    assert valid_interval(dict(status='ZERO_EMPIRICAL_VARIANCE',lower=None,upper=None)) is None
    assert valid_interval(dict(status='EXACT_ALGEBRAIC_ZERO',lower=0,upper=0))==[0,0]
