import numpy as np
import pytest
from windfarm_moe.actual_mixture_update import MixtureConfig,project_simplex,actual_gradient,run_mixture,run_matched_ew


def example(t=30):
    x=np.broadcast_to([0.,10.],(t,2,2)).copy();y=np.full((t,2),5.)
    return x,y,np.ones_like(y,bool),np.arange(t)


def test_simplex_exact_examples_and_reactivation():
    np.testing.assert_allclose(project_simplex([[2,0],[-1,-1],[.4,.6]]),[[1,0],[.5,.5],[.4,.6]])
    assert project_simplex([[1.-.2,0.+.2]])[0,1]>.1


def test_independent_finite_difference_of_actual_loss():
    x=np.array([[2.,8.],[9.,1.],[4.,7.]])
    y=np.array([3.,11.,2.]);w=np.array([.3,.7]);r=x@w
    g=actual_gradient(x,y,r[None,:])[0]
    direction=np.array([1.,-1.]);eps=1e-6
    def loss(theta):
        pred=x@theta
        return np.mean(pred+10*np.maximum(y-pred,0))/600
    difference=(loss(w+eps*direction)-loss(w-eps*direction))/(2*eps)
    assert difference==pytest.approx(g@direction,abs=1e-9)


def test_analytical_optimal_mixture_is_not_driven_to_single_expert():
    x,y,m,a=example();result=run_mixture(x,y,m,a,[MixtureConfig(eta=30)], [.5,.5],return_actions=True)
    np.testing.assert_array_equal(result['actions'],5.)
    assert result['ledger'][:,:,0].sum()/m.sum()==pytest.approx(5/6)


def test_strict_maturity_future_targets_masks_and_no_tail_flush():
    x,y,m,a=example();cfg=[MixtureConfig(eta=3,severity_step=10)]
    first=run_mixture(x,y,m,a,cfg,[.9,.1],return_actions=True)
    y[5:]=200;m[6:,0]=False
    second=run_mixture(x,y,m,a,cfg,[.9,.1],return_actions=True)
    np.testing.assert_array_equal(first['actions'][:,:13],second['actions'][:,:13])
    assert first['metadata']['release_trace'][7]==-1
    assert first['metadata']['release_trace'][8]==7
    x,y,m,a=example(8);y[:]=np.nan
    result=run_mixture(x,y,m,a,cfg,[.5,.5],score=False)
    assert result['metadata']['feedback_updates']==0


def test_empty_mature_mask_has_no_update_and_targets_never_gate_actions():
    x,y,m,a=example();m[:]=False;y[:]=np.nan
    r=run_mixture(x,y,m,a,[MixtureConfig()],[.9,.1],score=False,return_actions=True)
    np.testing.assert_allclose(r['actions'],1.)


def test_actual_gradient_is_not_average_expert_gradient():
    x=np.array([[0.,10.]]);y=np.array([5.]);actual=np.array([[5.]])
    np.testing.assert_array_equal(actual_gradient(x,y,actual),0)


def test_all_configuration_instances_are_returned_including_bad_performance():
    x,y,m,a=example();configs=[MixtureConfig(eta=0),MixtureConfig(eta=3)]
    r=run_mixture(x,y,m,a,configs,[.9,.1],return_actions=True)
    assert r['ledger'].shape==(2,1,4)
    assert r['metadata']['final_weights'][0]==[.9,.1]


def test_gap_clock_and_sparse_cell_gradient_have_fixed_population_weight():
    x=np.array([[0.,10.]])
    y=np.array([5.]);act=np.array([[1.]])
    np.testing.assert_allclose(actual_gradient(x,y,act,node_count=2),actual_gradient(x,y,act)/2)
    xx,yy,mm,_=example(3)
    r=run_mixture(xx,yy,mm,np.array([0,2,20]),[MixtureConfig()],[.9,.1])
    assert r['metadata']['feedback_updates']==2


@pytest.mark.parametrize('weights',[[0,0],[-1,2],[np.nan,1]])
def test_bad_initial_weight_rejected(weights):
    with pytest.raises(ValueError):run_mixture(*example(),[MixtureConfig()],weights)


def test_matched_ew_first_legal_update_has_independent_expected_weights():
    x,y,m,a=example(9);prior=np.array([.3,.7])
    actions=run_matched_ew(x,y,m,a,prior)
    loss=np.array([50/6,10/6])*.95/100
    expected=prior*np.exp(-10*(loss-loss.min()));expected/=expected.sum()
    np.testing.assert_array_equal(actions[:8],7.)
    np.testing.assert_allclose(actions[8],10*expected[1],rtol=1e-15)


def test_primal_and_signed_severity_dual_first_update_exact_fraction_oracle():
    # One tail cell and19 zeros; expectation derived independently by hand.
    x=np.broadcast_to([10.,0.],(9,20,2)).copy();y=np.zeros((9,20));y[:,0]=100
    r=run_mixture(x,y,np.ones_like(y,bool),np.arange(9),
        [MixtureConfig(eta=1,schedule_power=0,severity_step=10)],[.5,.5],return_actions=True)
    np.testing.assert_allclose(r['metadata']['final_weights'][0],[119/240,121/240],atol=1e-14)
    assert r['metadata']['final_lambda_u'][0]==pytest.approx(1/24,abs=1e-14)
    np.testing.assert_allclose(r['actions'][0,8],119/24,atol=1e-13)
