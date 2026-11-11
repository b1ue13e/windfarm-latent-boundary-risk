"""Synthetic exact/independent checks for a historical fixed convex LP."""
from types import SimpleNamespace
import numpy as np
import pytest

import windfarm_moe.static_convex_reserve as mod
from windfarm_moe.static_convex_reserve import fit_static_convex, predict_static


def cost(x,s,w):
    r=np.sum(np.asarray(x)*np.asarray(w),axis=-1)
    return np.mean((r+10*np.maximum(np.asarray(s)-r,0))/6)


def test_hand_solution_mixture_beats_each_expert():
    x=np.array([[0.,2.],[2.,0.]]);s=np.array([1.,1.])
    r=fit_static_convex(x,s)
    assert r.optimal and r.status=='OPTIMAL'
    np.testing.assert_allclose(r.weights,[.5,.5],atol=1e-12)
    assert r.objective==pytest.approx(1/6)
    assert r.metadata['training_cost_not_above_best_expert_numerically'] is True
    assert r.primal_residual['max_inequality_violation']<=r.metadata['feasibility_tolerance']
    assert r.metadata['risk_guarantee'] is False
    assert not r.weights.flags.writeable


@pytest.mark.parametrize('seed',[201,202,203,204,205])
def test_two_expert_optimum_matches_independent_breakpoint_enumeration(seed):
    rng=np.random.default_rng(seed);x=rng.uniform(0,30,(11,2));s=rng.uniform(0,30,11)
    # In one simplex dimension the convex piecewise-linear minimum is attained
    # at an endpoint or an intersection S = alpha*X0+(1-alpha)*X1.
    points=[0.,1.]
    for row,target in zip(x,s):
        if row[0]!=row[1]:
            a=(target-row[1])/(row[0]-row[1])
            if 0<=a<=1:points.append(float(a))
    expected=min(cost(x,s,[a,1-a]) for a in points)
    result=fit_static_convex(x,s)
    assert result.optimal
    assert result.objective==pytest.approx(expected,rel=2e-11,abs=2e-11)


def test_three_expert_hand_optimum_and_original_mean_cost_units():
    x=np.array([[0.,3.,0.],[0.,0.,3.],[3.,0.,0.]]);s=np.ones(3)
    result=fit_static_convex(x,s)
    np.testing.assert_allclose(result.weights,[1/3]*3,atol=1e-12)
    assert result.optimal and result.objective==pytest.approx(1/6)
    np.testing.assert_allclose(predict_static(x,result.weights),np.ones(3),atol=1e-12)


def test_predict_uses_only_fixed_weights_and_current_expert_actions():
    x=np.array([[0.,2.],[2.,0.]]);s=np.ones(2)
    result=fit_static_convex(x,s)
    future=np.arange(24,dtype=float).reshape(3,4,2)
    before=predict_static(future,result.weights)
    fake_future_target=np.full((3,4),np.nan)
    fake_future_mask=np.zeros((3,4),bool)
    del fake_future_target,fake_future_mask
    np.testing.assert_array_equal(before,predict_static(future,result.weights))
    np.testing.assert_array_equal(before,np.sum(future*result.weights,axis=-1))


def test_explicit_training_indices_do_not_consume_unselected_targets_or_features():
    x=np.array([[0.,2.],[2.,0.],[1000.,0.],[np.nan,np.nan]])
    s=np.array([1.,1.,123456.,np.nan])
    result=fit_static_convex(x,s,training_indices=np.array([0,1]))
    assert result.optimal and result.metadata['fit_population']==2
    s[2]=-1e8;x[2]=[np.inf,-5.]
    changed=fit_static_convex(x,s,training_indices=[0,1])
    np.testing.assert_array_equal(result.weights,changed.weights)
    assert result.metadata['selection_mode']=='EXPLICIT_INDICES_NO_SUBSAMPLING'


def test_default_uses_all_samples_and_cannot_ignore_bad_tail():
    x=np.array([[0.,2.],[2.,0.],[1.,1.]])
    s=np.array([1.,1.,1.])
    result=fit_static_convex(x,s)
    assert result.metadata['fit_population']==3
    assert result.metadata['selection_mode']=='ALL_SUPPLIED_ROWS_NO_SUBSAMPLING'
    s[-1]=np.nan
    with pytest.raises(ValueError):fit_static_convex(x,s)


def test_single_expert_zero_targets_and_zero_cost_are_legitimate():
    for x,s in [(np.zeros((3,2)),np.zeros(3)),
                (np.array([[0.],[2.],[4.]]),np.array([0.,1.,10.]))]:
        result=fit_static_convex(x,s)
        assert result.optimal
        assert result.objective==pytest.approx(cost(x,s,result.weights))
        assert result.primal_residual['weight_sum_error']<=1e-12


def test_zero_population_keeps_undefined_identity_without_fake_optimum():
    r=fit_static_convex(np.empty((0,3)),np.empty(0))
    assert r.status=='UNDEFINED_POPULATION' and not r.optimal
    assert r.weights is None and r.objective is None
    r=fit_static_convex(np.ones((2,3)),np.ones(2),training_indices=[])
    assert r.status=='UNDEFINED_POPULATION'


@pytest.mark.parametrize('indices',[[-1],[2],[0,0],[True,False],[.5]])
def test_invalid_training_indices_rejected(indices):
    with pytest.raises(ValueError):fit_static_convex(np.ones((2,2)),np.ones(2),training_indices=indices)


@pytest.mark.parametrize('limit',[0,-1,np.nan,np.inf])
def test_invalid_time_limit_rejected(limit):
    with pytest.raises(ValueError):fit_static_convex(np.ones((2,2)),np.ones(2),time_limit=limit)


def test_limit_failure_does_not_claim_global_optimum(monkeypatch):
    monkeypatch.setattr(mod,'linprog',lambda *a,**k:SimpleNamespace(
        status=1,success=False,message='Time limit reached',x=None,fun=None,nit=0))
    r=fit_static_convex(np.ones((2,2)),np.ones(2),time_limit=.001)
    assert r.status=='TIME_LIMIT' and not r.optimal and r.weights is None
    assert r.metadata['training_cost_not_above_best_expert_numerically'] is False
    assert r.metadata['time_limit_seconds']==.001


def test_limit_with_incumbent_is_labelled_not_optimal(monkeypatch):
    monkeypatch.setattr(mod,'linprog',lambda *a,**k:SimpleNamespace(
        status=1,success=False,message='Time limit reached',x=np.array([1.,0.,0.,0.]),fun=1/6,nit=3))
    r=fit_static_convex(np.ones((2,2)),np.ones(2))
    assert not r.optimal and r.status=='TIME_LIMIT_FEASIBLE_INCUMBENT'
    np.testing.assert_array_equal(r.weights,[1,0])
    assert r.metadata['training_cost_not_above_best_expert_numerically'] is False


def test_false_optimal_status_with_infeasible_weights_is_not_certified(monkeypatch):
    monkeypatch.setattr(mod,'linprog',lambda *a,**k:SimpleNamespace(
        status=0,success=True,message='Optimal',x=np.array([.1,.1,0.,0.]),fun=0.,nit=0))
    r=fit_static_convex(np.ones((2,2)),np.ones(2))
    assert r.status=='OPTIMAL_NUMERIC_UNRESOLVED' and not r.optimal
    assert r.weights is None
    assert r.primal_residual['weight_sum_error']==pytest.approx(.8)


def test_solver_exception_is_preserved_without_fabricated_weights(monkeypatch):
    def bad(*args,**kwargs):raise RuntimeError('synthetic solver failure')
    monkeypatch.setattr(mod,'linprog',bad)
    r=fit_static_convex(np.ones((2,2)),np.ones(2))
    assert r.status=='SOLVER_ERROR' and not r.optimal and r.weights is None
    assert 'synthetic solver failure' in r.message


def test_solver_options_warnings_and_environment_recorded():
    r=fit_static_convex(np.array([[0.,2.],[2.,0.]]),np.ones(2),time_limit=3.)
    assert r.metadata['solver_options']['threads']==1
    assert r.metadata['threadpool_limit']==1
    assert r.metadata['scipy_version']
    assert 'highs_version' in r.metadata
    assert isinstance(r.metadata['warnings'],list)
    assert r.metadata['time_limit_seconds']==3.


@pytest.mark.parametrize('x,s',[
    (np.array([1.,2.]),np.ones(2)), (np.ones((2,0)),np.ones(2)),
    (np.ones((2,2)),np.ones(3)), (np.array([[-1.,2.],[2.,0.]]),np.ones(2)),
    (np.ones((2,2)),np.array([-1.,1.])),
])
def test_invalid_fit_inputs_rejected(x,s):
    with pytest.raises(ValueError):fit_static_convex(x,s)


@pytest.mark.parametrize('weights',[[0.,0.],[-.1,1.1],[.2,.2],[np.nan,1.],[1.]])
def test_invalid_prediction_weights_rejected(weights):
    with pytest.raises(ValueError):predict_static(np.ones((3,2)),weights)


def test_fit_and_predict_do_not_mutate_original_arrays():
    x=np.array([[0.,2.],[2.,0.]]);s=np.ones(2);oldx=x.copy();olds=s.copy()
    r=fit_static_convex(x,s);predict_static(x,r.weights)
    np.testing.assert_array_equal(x,oldx);np.testing.assert_array_equal(s,olds)


def test_protected_lp_can_be_costlier_than_unconstrained_single_expert_and_still_optimal():
    x=np.array([[0.,2.],[0.,100.]]);s=np.ones(2)
    unrestricted=fit_static_convex(x,s)
    protected=fit_static_convex(x,s,uncovered_cap=.2)
    assert unrestricted.optimal and protected.optimal
    np.testing.assert_allclose(unrestricted.weights,[.99,.01],atol=1e-11)
    np.testing.assert_allclose(protected.weights,[.7,.3],atol=1e-11)
    assert protected.objective==pytest.approx(17.3/6)
    assert protected.objective>protected.metadata['best_unconstrained_single_expert_cost']
    assert protected.metadata['feasible_single_expert_indices']==[1]
    assert protected.objective<=protected.metadata['best_single_expert_cost']
    assert protected.mean_uncovered_power==pytest.approx(.2)
    assert protected.uncovered_cap==.2
    assert protected.primal_residual['uncovered_cap_violation']<=1e-12


def test_cap_can_have_feasible_mixture_but_no_feasible_individual_expert():
    x=np.array([[0.,2.],[2.,0.]]);s=np.ones(2)
    result=fit_static_convex(x,s,uncovered_cap=.1)
    assert result.optimal
    assert result.metadata['feasible_single_expert_indices']==[]
    assert result.metadata['best_single_expert_cost'] is None
    assert result.metadata['training_cost_not_above_best_expert_numerically'] is None
    assert result.mean_uncovered_power<=.1


def test_infeasible_cap_is_preserved_as_infeasible_not_hidden():
    result=fit_static_convex(np.zeros((3,2)),np.ones(3),uncovered_cap=.5)
    assert result.status=='INFEASIBLE' and not result.optimal
    assert result.weights is None and result.objective is None


def test_zero_cap_is_allowed_and_satisfied_in_original_power_units():
    x=np.array([[0.,2.],[2.,0.]]);s=np.ones(2)
    result=fit_static_convex(x,s,uncovered_cap=0.)
    assert result.optimal and result.mean_uncovered_power<=1e-12
    assert result.primal_residual['slack_cap_violation']<=1e-12


@pytest.mark.parametrize('cap',[-1,np.inf,np.nan,True])
def test_invalid_uncovered_cap_rejected(cap):
    with pytest.raises(ValueError):fit_static_convex(np.ones((2,2)),np.ones(2),uncovered_cap=cap)


def test_claimed_optimum_violating_cap_is_not_accepted(monkeypatch):
    monkeypatch.setattr(mod,'linprog',lambda *a,**k:SimpleNamespace(
        status=0,success=True,message='Optimal',x=np.array([1.,0.,1.,1.]),fun=10/6,nit=1))
    result=fit_static_convex(np.zeros((2,2)),np.ones(2),uncovered_cap=.5)
    assert not result.optimal and result.status=='OPTIMAL_NUMERIC_UNRESOLVED'
    assert result.weights is None
    assert result.primal_residual['uncovered_cap_violation']==pytest.approx(.5)
    assert result.primal_residual['slack_cap_violation']==pytest.approx(.5)


def test_explicit_rows_keep_same_lp_population_with_cap_and_no_random_subsample():
    rng=np.random.default_rng(205)
    x=rng.uniform(0,40,(60,5));s=rng.uniform(0,40,60)
    cap=float(np.maximum(s-x[:,0],0).mean())
    result=fit_static_convex(x,s,uncovered_cap=cap,time_limit=10.)
    assert result.optimal and result.metadata['fit_population']==60
    assert result.mean_uncovered_power<=cap+result.metadata['feasibility_tolerance']
    assert result.objective<=result.metadata['best_single_expert_cost']+result.metadata['objective_tolerance']
    assert result.metadata['solver_options']['random_seed']==0
