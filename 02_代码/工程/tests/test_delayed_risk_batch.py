"""Synthetic comparisons against the separately frozen scalar aggregator."""
import numpy as np
import pytest

from windfarm_moe.delayed_risk_aggregation import AggregationConfig, aggregate_delayed
from windfarm_moe.delayed_risk_batch import aggregate_batch


def inputs(seed=201, t=27, n=3, k=4):
    rng = np.random.default_rng(seed)
    x = rng.uniform(0, 25, (t,n,k)); y = rng.uniform(0,25,(t,n))
    m = rng.random((t,n)) > .25
    return x, y, m, np.arange(t)


def configurations():
    return [AggregationConfig(method='equal'), AggregationConfig(method='fixed'),
        AggregationConfig(method='exponential', eta=.3, temperature=.7),
        AggregationConfig(method='discounted', eta=.7, discount=.91),
        AggregationConfig(method='dual', eta=.4, dual_eta_v=.6, dual_eta_u=.8),
        AggregationConfig(method='discounted_dual', discount=.87, eta=.2,
            temperature=1.3, dual_eta_v=.5, dual_eta_u=.7, reference_index=1)]


def prior_matrix(k=4):
    priors = np.array([[1,1,1,1], [1,0,0,0], [.1,.2,.3,.4],
                       [.4,.3,.2,.1], [1,1,1,1], [.5,.2,.2,.1]], dtype=float)
    return priors[:, :k]


def metrics(actions, target, mask, lo, hi):
    mm = mask[lo:hi]; yy = target[lo:hi][mm]; rr = actions[lo:hi][mm]
    if not len(yy): return np.full(4, np.nan)
    u = np.maximum(yy-rr,0)/6; reserve = rr/6
    return np.array([(reserve+10*u).mean(), reserve.mean(), u.mean(), (yy>rr).mean()])


@pytest.mark.parametrize('seed', [201,202,203,204,205])
@pytest.mark.parametrize('gaps', [False,True])
def test_all_methods_and_priors_match_scalar(seed, gaps):
    x,y,m,a = inputs(seed)
    if gaps: a = np.cumsum(np.random.default_rng(seed+99).integers(1,5,len(a)))
    confs = configurations(); priors=prior_matrix()
    result = aggregate_batch(x,y,m,a,confs,priors=priors,score_slice=(5,24),return_actions=True)
    assert result.actions.shape == (len(confs),len(a),x.shape[1])
    for j, conf in enumerate(confs):
        scalar = aggregate_delayed(x,y,m,a,conf,
            historical_weights=None if conf.method=='equal' else priors[j])
        np.testing.assert_array_equal(result.actions[j], scalar.action)
        np.testing.assert_allclose(result.metrics[j], metrics(scalar.action,y,m,5,24), rtol=3e-15,atol=2e-15)
    assert result.metadata['max_pending_feedback_rows'] <= 8
    assert result.metadata['feedback_rule'] == 'source_anchor + 7 < decision_anchor'
    releases=np.asarray(result.metadata['last_feedback_release_by_decision'])
    assert np.all(releases < a)


def test_nonstored_actions_have_same_metrics():
    x,y,m,a=inputs(); confs=configurations(); priors=prior_matrix()
    full=aggregate_batch(x,y,m,a,confs,priors=priors,return_actions=True)
    compact=aggregate_batch(x,y,m,a,confs,priors=priors)
    assert compact.actions is None
    np.testing.assert_array_equal(compact.metrics,full.metrics)


def test_future_target_mask_expert_perturbation_preserves_earlier_actions():
    x,y,m,a=inputs(t=30); confs=configurations(); priors=prior_matrix()
    before=aggregate_batch(x,y,m,a,confs,priors=priors,return_actions=True)
    yy=y.copy(); mm=m.copy(); xx=x.copy()
    yy[5:]+=100; mm[5:]=~mm[5:]
    after=aggregate_batch(x,yy,mm,a,confs,priors=priors,return_actions=True)
    np.testing.assert_array_equal(before.actions[:,:13],after.actions[:,:13])
    xx[10:]+=123
    later=aggregate_batch(xx,y,m,a,confs,priors=priors,return_actions=True)
    np.testing.assert_array_equal(before.actions[:,:10],later.actions[:,:10])


def test_exact_release_tick_not_consumed_and_trace_keeps_release_plus_seven():
    x,y,m,a=inputs(t=10)
    r=aggregate_batch(x,y,m,a,[AggregationConfig()],return_actions=True)
    assert r.metadata['last_feedback_release_by_decision'][7] == -1
    assert r.metadata['last_feedback_release_by_decision'][8] == 7
    assert r.metadata['feedback_rows_used'] == 2


def test_empty_scoring_population_and_zero_nodes_keep_slots():
    x,y,m,a=inputs(); m[:]=False; y[:]=np.nan
    confs=[AggregationConfig(method='dual'),AggregationConfig(method='equal')]
    r=aggregate_batch(x,y,m,a,confs,return_actions=True)
    assert np.isnan(r.metrics).all()
    assert r.metadata['score_status']=='UNDEFINED_POPULATION'
    np.testing.assert_allclose(r.actions, np.broadcast_to(x.mean(axis=2),(2,)+y.shape))
    empty=aggregate_batch(np.empty((10,0,2)),np.empty((10,0)),np.empty((10,0),bool),
        np.arange(10),confs)
    assert np.isnan(empty.metrics).all()


def test_no_candidates_and_no_time_are_defined_empty_outputs():
    x,y,m,a=inputs()
    r=aggregate_batch(x,y,m,a,[],return_actions=True)
    assert r.metrics.shape==(0,4) and r.actions.shape==(0,len(a),3)
    r=aggregate_batch(x[:0],y[:0],m[:0],a[:0],[AggregationConfig()],return_actions=True)
    assert r.actions.shape==(1,0,3) and np.isnan(r.metrics).all()


def test_mixture_event_dual_not_average_expert_event():
    x=np.broadcast_to([0.,2.],(12,1,2)).copy(); y=np.ones((12,1));m=np.ones((12,1),bool)
    conf=[AggregationConfig(method='dual',dual_eta_v=1.)]
    r=aggregate_batch(x,y,m,np.arange(12),conf,return_actions=True)
    scalar=aggregate_delayed(x,y,m,np.arange(12),conf[0])
    np.testing.assert_array_equal(r.actions[0],scalar.action)
    assert r.metadata['final_lambda_v'][0] == scalar.trace['lambda_v'][-1]


def test_large_eta_temperature_and_zero_priors_match_scalar():
    x,y,m,a=inputs(t=15)
    conf=[AggregationConfig(eta=1e200,temperature=1e-200),AggregationConfig(method='fixed')]
    priors=np.array([[1.,1.,0.,1.],[0.,0.,1.,0.]])
    r=aggregate_batch(x,y,m,a,conf,priors=priors,return_actions=True)
    for j,c in enumerate(conf):
        scalar=aggregate_delayed(x,y,m,a,c,historical_weights=priors[j])
        np.testing.assert_array_equal(r.actions[j],scalar.action)


@pytest.mark.parametrize('slice_', [(-1,4),(0,100),(5,4),(0.,4),(True,4)])
def test_invalid_score_slice_rejected(slice_):
    x,y,m,a=inputs()
    with pytest.raises(ValueError): aggregate_batch(x,y,m,a,[AggregationConfig()],score_slice=slice_)


def test_inputs_and_original_scalar_sources_not_modified():
    x,y,m,a=inputs(); copies=[v.copy() for v in (x,y,m,a)]
    aggregate_batch(x,y,m,a,[AggregationConfig()])
    for v,old in zip((x,y,m,a),copies): np.testing.assert_array_equal(v,old)


def test_invalid_priors_and_equal_nonuniform_priors_rejected():
    x,y,m,a=inputs()
    for conf, prior in [([AggregationConfig(method='equal')],[[1,2,3,4]]),
                         ([AggregationConfig()],[[0,0,0,0]]),
                         ([AggregationConfig()],[[1,1,1]]),
                         ([AggregationConfig(method='fixed')],None)]:
        with pytest.raises(ValueError): aggregate_batch(x,y,m,a,conf,priors=prior)


def test_nan_scored_target_is_not_silently_dropped():
    x,y,m,a=inputs(); m[0,0]=True; y[0,0]=np.nan
    with pytest.raises(ValueError): aggregate_batch(x,y,m,a,[AggregationConfig()])


def test_unscored_unmatured_tail_targets_can_be_missing():
    x,y,m,a=inputs(t=12); y[4:]=np.nan
    r=aggregate_batch(x,y,m,a,[AggregationConfig()],score_slice=(0,4),return_actions=True)
    scalar=aggregate_delayed(x,y,m,a,AggregationConfig())
    np.testing.assert_array_equal(r.actions[0],scalar.action)


@pytest.mark.parametrize('seed',[201,202,203,204,205])
def test_larger_original_node_count_and_pairwise_summation_match(seed):
    x,y,m,a=inputs(seed,t=48,n=134,k=17)
    confs=configurations()
    rng=np.random.default_rng(seed+401)
    priors=rng.uniform(.01,1,(len(confs),17)); priors[0]=1.
    priors[1]=0.; priors[1,0]=1.
    priors[2,2::3]=0.; priors[-1,3::4]=0.
    result=aggregate_batch(x,y,m,a,confs,priors=priors,return_actions=True)
    for j,conf in enumerate(confs):
        oracle=aggregate_delayed(x,y,m,a,conf,
            historical_weights=None if conf.method=='equal' else priors[j])
        np.testing.assert_array_equal(result.actions[j],oracle.action)
        np.testing.assert_allclose(result.metrics[j],metrics(oracle.action,y,m,0,len(a)),rtol=4e-15)


def test_partial_score_window_cannot_change_online_policy():
    x,y,m,a=inputs(t=40);confs=configurations();priors=prior_matrix()
    a1=aggregate_batch(x,y,m,a,confs,priors=priors,return_actions=True)
    a2=aggregate_batch(x,y,m,a,confs,priors=priors,score_slice=(9,11),return_actions=True)
    np.testing.assert_array_equal(a1.actions,a2.actions)
    np.testing.assert_array_equal(a1.metadata['final_weights'],a2.metadata['final_weights'])
