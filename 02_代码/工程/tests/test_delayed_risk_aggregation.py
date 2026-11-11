"""Synthetic causal, arithmetic and boundary tests for delayed aggregation."""
import numpy as np
import pytest

from windfarm_moe.delayed_risk_aggregation import (
    AggregationConfig, aggregate_delayed, delayed_risk_aggregation,
)


def fixture(t=20, n=2):
    experts = np.broadcast_to(np.array([0., 2.]), (t, n, 2)).copy()
    target = np.ones((t, n))
    return experts, target, np.ones((t, n), dtype=bool), np.arange(t)


def cfg(method='exponential', **kwargs):
    return AggregationConfig(cost_scale=10., method=method, **kwargs)


def test_equal_and_fixed_are_exact_convex_decisions():
    x, s, m, a = fixture()
    eq = aggregate_delayed(x, s, m, a, cfg('equal'))
    np.testing.assert_array_equal(eq.action, 1.)
    fixed = aggregate_delayed(x, s, m, a, cfg('fixed'), historical_weights=[.25, .75])
    np.testing.assert_array_equal(fixed.action, 1.5)
    np.testing.assert_array_equal(fixed.weights, np.broadcast_to([.25, .75], (20, 2)))


def test_only_first_target_is_usable_at_strictly_after_seven_step_release():
    x, s, m, a = fixture()
    r = aggregate_delayed(x, s, m, a, cfg())
    np.testing.assert_array_equal(r.weights[:8], .5)
    # C0=10/6, C1=2/6; scores divided by fixed scale=10.
    p = np.exp(-np.array([10/6, 2/6])/10); p /= p.sum()
    np.testing.assert_allclose(r.weights[8], p, rtol=1e-14)
    assert r.trace['feedback_rows'][7] == 0
    assert r.trace['feedback_rows'][8] == 1
    assert r.trace['last_feedback_anchor'][8] == 0
    assert r.trace['last_feedback_release'][8] == 7


@pytest.mark.parametrize('method', ['exponential', 'discounted', 'dual', 'discounted_dual'])
def test_future_targets_and_future_masks_do_not_change_earlier_decisions(method):
    x, s, m, a = fixture(25)
    conf = cfg(method, discount=.8 if 'discounted' in method else 1.)
    before = aggregate_delayed(x, s, m, a, conf)
    ss, mm = s.copy(), m.copy()
    ss[5:] = 1000.; mm[6:, 0] = False
    after = aggregate_delayed(x, ss, mm, a, conf)
    np.testing.assert_array_equal(before.action[:13], after.action[:13])
    np.testing.assert_array_equal(before.weights[:13], after.weights[:13])


def test_last_eight_unmatured_targets_are_never_validated_or_used():
    x, s, m, a = fixture(12)
    baseline = aggregate_delayed(x, s, m, a, cfg())
    s[4:] = np.nan
    result = aggregate_delayed(x, s, m, a, cfg())
    np.testing.assert_array_equal(result.action, baseline.action)


def test_current_scoring_mask_does_not_gate_current_action():
    x, s, m, a = fixture()
    before = aggregate_delayed(x, s, m, a, cfg())
    m[3] = False
    after = aggregate_delayed(x, s, m, a, cfg())
    np.testing.assert_array_equal(before.action[:11], after.action[:11])
    assert not np.array_equal(before.action[11:], after.action[11:])


def test_masked_nan_and_zero_feedback_leave_initial_weights():
    x, s, m, a = fixture()
    m[:] = False; s[:] = np.nan
    r = aggregate_delayed(x, s, m, a, cfg('dual'), historical_weights=[.7, .3])
    np.testing.assert_allclose(r.weights, np.broadcast_to([.7, .3], (20, 2)))
    assert r.trace['feedback_cells'].sum() == 0
    assert r.trace['lambda_v'].max() == r.trace['lambda_u'].max() == 0


def test_disjoint_anchors_assimilate_all_matured_rows_and_discount_by_event_time():
    x, s, m, _ = fixture(3, 1)
    a = np.array([0, 2, 20])
    r = aggregate_delayed(x, s, m, a, cfg('discounted', discount=.5))
    score = np.array([10/6, 2/6])/10
    expected_ledger = (.5**13 + .5**11)*score
    expected = np.exp(-expected_ledger); expected /= expected.sum()
    np.testing.assert_allclose(r.weights[-1], expected)
    assert r.trace['feedback_rows'][-1] == 2
    assert r.trace['last_feedback_anchor'][-1] == 2


def test_duals_use_real_mixture_event_not_average_expert_events():
    x, s, m, a = fixture(9, 1)
    r = aggregate_delayed(x, s, m, a, cfg('dual', dual_eta_v=1., dual_eta_u=1.))
    # Mixture action equals S: strict event is false, although half experts fail.
    assert r.action[0, 0] == 1.
    assert r.trace['lambda_v'][8] == 0.
    assert r.trace['lambda_u'][8] == 0.


def test_dual_exact_violation_and_signed_severity_update():
    x = np.zeros((9, 1, 2)); s = np.full((9, 1), 10.); m = np.ones_like(s, bool)
    r = aggregate_delayed(x, s, m, np.arange(9), cfg('dual', dual_eta_v=2., dual_eta_u=3.))
    assert r.trace['lambda_v'][8] == pytest.approx(1.8)
    # All experts, aggregate and reference have equal U: signed severity=0.
    assert r.trace['lambda_u'][8] == 0.


def test_reference_index_changes_only_the_signed_severity_baseline():
    x, s, m, a = fixture(9, 1)
    r = aggregate_delayed(x, s, m, a,
        cfg('dual', reference_index=1, dual_eta_u=1.), historical_weights=[1., 0.])
    assert r.trace['lambda_u'][8] == pytest.approx(10*(1/6)/10)
    assert r.trace['lambda_v'][8] > 0


def test_no_large_trace_mode_preserves_actions_and_final_state():
    x, s, m, a = fixture()
    full = aggregate_delayed(x, s, m, a, cfg('dual'), store_ledger=True)
    compact = aggregate_delayed(x, s, m, a, cfg('dual'), store_weights=False)
    np.testing.assert_array_equal(full.action, compact.action)
    np.testing.assert_array_equal(full.final_weights, compact.final_weights)
    assert compact.weights is None
    assert 'ledger' not in compact.trace
    assert full.trace['ledger'].shape == (20, 2)


def test_empty_time_zero_nodes_and_single_expert():
    r = aggregate_delayed(np.empty((0, 2, 1)), np.empty((0, 2)),
        np.empty((0, 2), bool), np.array([], dtype=int), cfg())
    assert r.action.shape == (0, 2)
    np.testing.assert_array_equal(r.final_weights, [1.])
    r = aggregate_delayed(np.empty((10, 0, 1)), np.empty((10, 0)),
        np.empty((10, 0), bool), np.arange(10), cfg())
    assert r.action.shape == (10, 0)
    assert not r.trace['feedback_cells'].any()


def test_extreme_eta_and_costs_do_not_overflow_exponential_weights():
    x, s, m, a = fixture()
    r = aggregate_delayed(x, s*1e200, m, a, cfg(eta=1e200))
    assert np.isfinite(r.action).all()
    assert np.isfinite(r.weights).all()
    np.testing.assert_allclose(r.weights.sum(axis=1), 1.)


def test_inputs_are_not_modified_and_alias_is_same_api():
    x, s, m, a = fixture()
    old = [v.copy() for v in (x, s, m, a)]
    one = aggregate_delayed(x, s, m, a, cfg())
    two = delayed_risk_aggregation(x, s, m, a, cfg())
    np.testing.assert_array_equal(one.action, two.action)
    for p, q in zip((x, s, m, a), old): np.testing.assert_array_equal(p, q)


@pytest.mark.parametrize('bad', [
    dict(cost_scale=0), dict(cost_scale=np.inf), dict(eta=-1), dict(temperature=0),
    dict(discount=0), dict(discount=1.1), dict(dual_eta_v=-1),
    dict(method='oracle'), dict(reference_index=-1),
])
def test_invalid_configuration_rejected(bad):
    x, s, m, a = fixture()
    params = dict(cost_scale=10.); params.update(bad)
    with pytest.raises(ValueError): aggregate_delayed(x, s, m, a, AggregationConfig(**params))


@pytest.mark.parametrize('weights', [[0, 0], [-1, 2], [np.nan, 1], [1], [np.inf, 1]])
def test_invalid_historical_weights_rejected(weights):
    x, s, m, a = fixture()
    with pytest.raises(ValueError): aggregate_delayed(x, s, m, a, cfg('fixed'), historical_weights=weights)


def test_invalid_matured_target_raises_instead_of_dropping_row():
    x, s, m, a = fixture()
    s[0, 0] = np.nan
    with pytest.raises(ValueError, match='matured'): aggregate_delayed(x, s, m, a, cfg())


def test_bad_action_mask_anchor_and_shapes_rejected():
    x, s, m, a = fixture()
    for xx, ss, mm, aa in [
        (x[:-1], s, m, a), (x, s, m.astype(int), a),
        (x, s, m, a.astype(float)), (x, s, m, a[::-1]),
        (np.full_like(x, -1.), s, m, a),
        (np.full_like(x, np.nan), s, m, a),
    ]:
        with pytest.raises(ValueError): aggregate_delayed(xx, ss, mm, aa, cfg())


def test_no_oracle_tail_feedback_is_flushed_after_last_decision():
    x, s, m, a = fixture(8)
    r = aggregate_delayed(x, s, m, a, cfg())
    assert r.metadata['feedback_rows_used'] == 0
    assert r.metadata['pending_feedback_rows'] == 8
    assert r.metadata['risk_guarantee'] is False
    assert r.metadata['horizon_steps'] == 6
    assert r.metadata['label_release_steps'] == 1


def test_sparse_matured_rows_have_original_cell_weight_not_equal_issue_weight():
    x, s, m, a = fixture(10, 2)
    m[0, 1] = False
    r = aggregate_delayed(x, s, m, a, cfg(), store_ledger=True)
    cost = np.array([10/6, 2/6])/10
    np.testing.assert_allclose(r.trace['ledger'][8], .5*cost)
    np.testing.assert_allclose(r.trace['ledger'][9], 1.5*cost)


def test_future_expert_actions_cannot_affect_earlier_weights_or_actions():
    x, s, m, a = fixture(20)
    before = aggregate_delayed(x, s, m, a, cfg('discounted', discount=.9))
    x[10:] += 1234
    after = aggregate_delayed(x, s, m, a, cfg('discounted', discount=.9))
    np.testing.assert_array_equal(before.action[:10], after.action[:10])
    np.testing.assert_array_equal(before.weights[:18], after.weights[:18])


def test_independent_scalar_exponential_reconstruction_on_uneven_mask_and_anchors():
    import math
    rng = np.random.default_rng(301)
    x = rng.uniform(0, 20, size=(24, 3, 4)); s = rng.uniform(0, 20, size=(24, 3))
    m = rng.random((24, 3)) > .4
    a = np.cumsum(rng.integers(1, 4, size=24))
    result = aggregate_delayed(x, s, m, a, cfg(eta=.75, temperature=1.3))
    expected = np.empty((24, 3)); scalar_weights = np.empty((24, 4))
    for i, now in enumerate(a):
        losses = []
        for expert in range(4):
            total = 0.
            for j in range(i):
                if int(a[j])+7 >= int(now):
                    continue
                for node in range(3):
                    if m[j, node]:
                        r = float(x[j, node, expert]); target = float(s[j, node])
                        total += (r+10*max(target-r, 0))/(6*3*10)
            losses.append(total)
        logits = [-.75*(v-min(losses))/1.3 for v in losses]
        raw = [math.exp(v) for v in logits]; weights = [v/sum(raw) for v in raw]
        scalar_weights[i] = weights
        for node in range(3):
            expected[i, node] = sum(float(x[i,node,k])*weights[k] for k in range(4))
    np.testing.assert_allclose(result.weights, scalar_weights, rtol=2e-14, atol=2e-16)
    np.testing.assert_allclose(result.action, expected, rtol=2e-14, atol=2e-14)


def test_no_original_qualification_statistics_are_consumed():
    x, s, m, a = fixture()
    result = aggregate_delayed(x, s, m, a, AggregationConfig())
    assert result.metadata['cost_scale_fixed_before_run'] == 100.
    assert result.metadata['uses_historical_Cstar'] is False
    assert result.metadata['feedback_release_offset'] == 7
    assert result.metadata['minimum_consecutive_grid_lag'] == 8
    assert result.metadata['signed_severity_learning_target'] == 0.
