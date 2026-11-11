"""Synthetic counterexamples for the risk/near-optimality decision logic."""
import numpy as np
import pytest

from windfarm_moe.risk_frontier import offset_grid, shared_block_draws, simultaneous_envelope, near_optimal_set


def test_offset_fit_uses_signed_residual_and_never_uses_invalid_target():
    s = np.array([1., 4., 9., np.nan])
    raw = np.array([-2., 3., 4., 999.])
    result = offset_grid(s, raw, np.array([1, 1, 1, 0], bool), [0.5, 1.0])
    np.testing.assert_array_equal(result, [1., 5.])
    action = np.maximum(np.maximum(raw[:3], 0) + result[0], 0)
    np.testing.assert_array_equal(action, [1., 4., 5.])


def test_shared_draws_keep_complete_circular_segments_and_counts():
    weights, identity = shared_block_draws(7, 100, 3, 42)
    again, same = shared_block_draws(7, 100, 3, 42)
    np.testing.assert_array_equal(weights, again)
    np.testing.assert_array_equal(weights.sum(axis=1), np.full(100, 7))
    assert identity == same


def test_envelope_handles_unseen_risk_and_known_identity_differently():
    p = np.array([0.0, 0.0, 0.5])
    draws = np.column_stack((np.zeros(100), np.zeros(100), np.linspace(0.4, 0.6, 100)))
    b = simultaneous_envelope(p, draws, 0.05, exact=np.array([0, 1, 0], bool))
    assert np.isneginf(b['lower'][0]) and np.isposinf(b['upper'][0])
    assert b['lower'][1] == b['upper'][1] == 0.0
    assert b['lower'][2] < 0.5 < b['upper'][2]


def test_simple_safe_model_not_selected_when_it_forfeits_large_savings():
    # Both safe, but simple m0 can lose 30%; must retain the more complex m1.
    lower = np.array([[.05, .04], [.04, .03]])
    upper = np.array([[.09, .08], [.08, .07]])
    regret = np.array([[0., .30], [-.15, 0.]])
    r = near_optimal_set(lower, upper, regret, [True, True], [(1, 1, 10), (3, 1, 30)], .01)
    assert r['minimum_resource_indices'] == [1]
    assert r['possible_feasible_indices'] == [0, 1]


def test_uncertain_potential_competitor_cannot_be_silently_removed():
    lower = np.array([[.05, .07]])
    upper = np.array([[.09, .15]])
    regret = np.array([[0., .10], [0., 0.]])
    r = near_optimal_set(lower, upper, regret, [True, True], [(1, 1, 10), (2, 2, 20)], .01)
    assert r['possible_feasible_indices'] == [0, 1]
    assert r['minimum_resource_indices'] == []


def test_worst_seed_risk_and_historical_failure_block_deployment():
    lower = np.array([[.03, .02], [.02, .01]])
    upper = np.array([[.08, .07], [.14, .09]])
    regret = np.zeros((2, 2))
    r = near_optimal_set(lower, upper, regret, [True, False], [(1, 1, 10), (2, 1, 20)], .02)
    assert r['risk_qualified_indices'] == []
    assert r['minimum_resource_indices'] == []


def test_equal_resources_preserve_ties_instead_of_inventing_unique_minimum():
    r = near_optimal_set(np.zeros((1, 2)), np.full((1, 2), .05), np.zeros((2, 2)),
                         [True, True], [(3, 2, 20), (3, 2, 20)], .01)
    assert r['minimum_resource_indices'] == [0, 1]


@pytest.mark.parametrize('quantiles', [[], [-.1], [1.1], [.9, .8]])
def test_offset_rejects_invalid_grid(quantiles):
    with pytest.raises(ValueError):
        offset_grid(np.array([1.]), np.array([0.]), np.array([True]), quantiles)
