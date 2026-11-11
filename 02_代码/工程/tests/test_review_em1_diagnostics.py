import pytest
from scripts.review_em1_diagnostics import retention

def test_retention_is_reference_dependent_and_zero_case_undefined():
    assert retention(12,10,20)==pytest.approx(.8)
    assert retention(12,10,14)==pytest.approx(.5)
    assert retention(10,10,10) is None

def test_aggregate_ratio_not_arithmetic_average_of_per_fit_ratios():
    # Fit1 gain10, retained9; fit2 gain1, retained0. Aggregate is9/11, not.45.
    aggregate=retention((11+20)/2,(10+19)/2,20)
    assert aggregate==pytest.approx(9/11)
    assert aggregate!=pytest.approx((.9+0)/2)
