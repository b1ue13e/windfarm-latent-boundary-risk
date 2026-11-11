import numpy as np
from windfarm_moe.protected_residual import residual_experts,guarded_action
from windfarm_moe.actual_mixture_update import MixtureConfig,run_mixture


def test_original_cost_equals_internal_residual_cost_plus_constant():
    rng=np.random.default_rng(124);s=rng.uniform(0,10,100);b=rng.uniform(0,10,100);v=rng.uniform(0,10,100)
    original=(b+v+10*np.maximum(s-b-v,0))/6
    internal=(v+10*np.maximum(np.maximum(s-b,0)-v,0))/6
    np.testing.assert_allclose(original,internal+b/6,rtol=1e-14,atol=1e-14)


def test_bitwise_floor_and_target_endpoint_dominance():
    x=np.array([[[0.,5.],[3.,9.]]]);b=np.array([[5.,8.]])
    delta=residual_experts(x,b);w=np.array([.123456789,.4,.476543211])
    r=guarded_action(b,delta,w);assert (r>=b).all()
    for target in [np.array([[5.,8.]]),np.array([[6.,12.]]),np.zeros_like(b)]:
        assert np.all(np.maximum(target-r,0)<=np.maximum(target-b,0))
        assert np.all((target>r)<=(target>b))


def test_zero_increment_baseline_and_mature_feedback_remain_legal():
    b=np.ones((20,2))*5;x=np.ones((20,2,2))*4
    delta=residual_experts(x,b);target=np.ones_like(b)*6
    internal=np.maximum(target-b,0)
    result=run_mixture(delta,internal,np.ones_like(b,bool),np.arange(20),[MixtureConfig()],np.full(3,1/3),return_actions=True)
    r=b+result['actions'][0]
    np.testing.assert_array_equal(r,b)
    assert result['metadata']['release_trace'][7]==-1 and result['metadata']['release_trace'][8]==7
