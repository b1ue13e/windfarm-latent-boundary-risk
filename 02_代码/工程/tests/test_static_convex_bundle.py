import numpy as np
import pytest
from windfarm_moe.static_convex_bundle import fit_bundle
from windfarm_moe.static_convex_reserve import fit_static_convex


def test_exact_piecewise_optimum():
    # r=2w0: the kink r=1 is the unique minimizer for both target rows.
    result=fit_bundle(np.array([[0.,2.],[0.,2.]]),np.ones(2))
    assert result.optimal
    assert np.allclose(result.weights,[.5,.5],atol=1e-7)
    assert abs(result.objective-1/6)<1e-8
    assert result.gap<=result.numerical_tolerance


@pytest.mark.parametrize('cap',[None,.5,0.])
def test_independent_full_lp_oracle(cap):
    rng=np.random.default_rng(124)
    x=rng.uniform(0,5,(200,4));x[:,0]=10
    y=rng.uniform(0,7,200)
    actual=fit_bundle(x,y,uncovered_cap=cap,time_limit=5)
    exact=fit_static_convex(x,y,uncovered_cap=cap,time_limit=5)
    assert exact.optimal and actual.optimal
    assert abs(actual.objective-exact.objective)<2e-6
    assert actual.lower_bound<=exact.objective+2e-6
    if cap is not None: assert actual.mean_uncovered_power<=cap


def test_iteration_limit_preserves_feasible_incumbent():
    rng=np.random.default_rng(5);x=rng.uniform(0,10,(600,9));y=rng.uniform(0,12,600)
    result=fit_bundle(x,y,max_iter=1)
    assert not result.optimal
    assert np.isfinite(result.objective) and result.gap>0
    assert (result.weights>=0).all() and np.isclose(result.weights.sum(),1)


@pytest.mark.parametrize('seed',[2,7,201])
def test_reference_cap_boundary_retains_true_feasible_upper_bound(seed):
    rng=np.random.default_rng(seed)
    x=rng.uniform(0,12,(600,5));y=rng.uniform(0,12,600)
    cap=float(np.maximum(y-x[:,0],0).mean())
    actual=fit_bundle(x,y,uncovered_cap=cap,time_limit=5)
    exact=fit_static_convex(x,y,uncovered_cap=cap,time_limit=5)
    assert exact.optimal and actual.optimal
    assert np.maximum(y-x@actual.weights,0).mean()<=cap
    assert abs(actual.objective-exact.objective)<3e-6
