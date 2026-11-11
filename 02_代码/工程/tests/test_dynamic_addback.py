"""Boundary fixtures for the new causal probe; no empirical claims."""
import numpy as np
import pytest
from windfarm_moe.dynamic_addback import past_dynamics,matrices,clock_qualified,daily


def test_features_are_past_only_and_linear_window_has_zero_residual():
    data=np.zeros((20,2,4),dtype=np.float32)
    data[:,:,1]=1000-40*np.arange(20)[:,None]
    data[:,:,2]=np.arange(20)[:,None]*3
    issues=np.array([8,10])
    a=past_dynamics(data,issues)
    changed=data.copy();changed[11:]=1e8
    b=past_dynamics(changed,issues)
    for name in a:np.testing.assert_equal(a[name],b[name])
    np.testing.assert_allclose(a['trend'],np.tile([-40,-240,-40],(4,1)))
    np.testing.assert_allclose(a['path'],np.tile([0,200,5],(4,1)))
    assert np.all(a['group']==1)


def test_missing_values_never_backfill_and_group_unknown_retained():
    data=np.ones((10,1,4),dtype=np.float32)
    data[7,0,1]=np.nan
    a=past_dynamics(data,np.array([8]))
    assert np.isnan(a['trend'][0,0]) and np.isnan(a['trend'][0,2])
    assert np.isnan(a['path']).all() and a['group'][0,0]==2
    assert np.isfinite(a['level']).all()


def test_feature_sets_keep_levels_and_only_true_arm_consumes_pitch():
    data=np.arange(10*2*4,dtype=np.float32).reshape(10,2,4)
    a=past_dynamics(data,np.array([8]))
    base=np.ones((2,4));full=np.ones((2,8));g=np.arange(2);risk=g+2
    result=matrices(base,full,g,risk,a)
    np.testing.assert_equal(result['G_PQ'][:,-2:],a['level'])
    np.testing.assert_equal(result['G_PQ_TV'][:,:7],result['G_PQ'])
    a['pitch'][:]=1e9
    altered=matrices(base,full,g,risk,a)
    for name in result:
        if name!='TRUE_PQ':np.testing.assert_equal(result[name],altered[name])
    assert result['RISK'].shape==result['G'].shape


def test_first_six_probe_issues_removed_by_release_clock():
    # Original point fit ends at12947; last release=12959, publication=t-6.
    issues=np.arange(12960,12968)
    np.testing.assert_equal(clock_qualified(issues,12947),[False]*6+[True]*2)


def test_accounting_groups_partition_the_full_population_and_keep_zero_days():
    s=np.array([[0.,3.],[4.,1.]])
    r=np.array([[2.,1.],[1.,1.]])
    valid=np.ones_like(s,dtype=bool)
    groups=np.array([[0,1],[2,0]],dtype=np.int8)
    out=daily(s,r,valid,np.array([0,288]),groups)
    assert len(out['days'])==3 and out['all__N'][1]==0
    for name in ['N','C','R','U','V']:
        np.testing.assert_allclose(out['all__'+name],sum(out[g+'__'+name] for g in ['other','down','unknown']))
    np.testing.assert_allclose(out['all__C'],out['all__R']+10*out['all__U'])
    assert out['all__R'][0]>0


def test_rejects_incomplete_past():
    with pytest.raises(ValueError):past_dynamics(np.zeros((10,2,4)),np.array([5]))


def test_tiny_all_arm_fit_calibration_and_accounting():
    from scripts.run_decision_information_development import learner
    from threadpoolctl import threadpool_limits
    rng=np.random.default_rng(201)
    data=rng.normal(size=(60,2,4)).astype(np.float32)
    issues=np.arange(6,56)
    extra=past_dynamics(data,issues)
    base=rng.normal(size=(100,8)).astype(np.float32)
    full=np.column_stack((base,rng.normal(size=(100,12))))
    arms=matrices(base,full,rng.normal(size=100),rng.normal(size=100),extra)
    target=np.abs(rng.normal(size=100))*5
    with threadpool_limits(limits=1):
        for x in arms.values():
            model=learner(dict(max_iter=3,max_leaf_nodes=3,min_samples_leaf=3,
                learning_rate=.08,l2_regularization=1),201,True)
            model.fit(x[:60],target[:60])
            pred=np.maximum(model.predict(x[60:]),0)
            offset=np.quantile(target[60:80]-pred[:20],.9,method='higher')
            r=np.maximum(pred[20:]+offset,0).reshape(10,2)
            out=daily(target[80:].reshape(10,2),r,np.ones((10,2),dtype=bool),
                      issues[-10:],extra['group'][-10:])
            assert out['all__N'].sum()==20 and np.isfinite(out['all__C']).all()


def test_zero_group_denominator_is_unresolved_not_dropped():
    from scripts.run_dynamic_addback import interval
    result=interval(np.nan,np.full(100,np.nan),58)
    assert result['lower'] is None and result['upper'] is None
    assert result['status']=='UNRESOLVED_ZERO_DENOMINATOR_NO_REDRAW'
    constant=interval(0.,np.zeros(100),58)
    assert constant['point']==0 and constant['lower'] is None and constant['upper'] is None
    assert constant['status']=='UNRESOLVED_EMPIRICAL_ZERO_VARIANCE'
