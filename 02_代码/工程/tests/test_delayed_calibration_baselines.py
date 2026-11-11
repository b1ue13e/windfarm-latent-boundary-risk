"""Synthetic causal and clock tests; no model weights or project data are read."""
from dataclasses import replace

import numpy as np
import pytest

from windfarm_moe.delayed_calibration_baselines import (
    DelayedCalibrationConfig as Config,
    run_delayed_calibration as run,
)


def example(t=40, n=3):
    anchors = np.arange(t, dtype=np.int64)
    ref = np.full((t, n), 2.0)
    target = np.arange(t * n, dtype=float).reshape(t, n) % 7
    mask = np.ones((t, n), dtype=bool)
    return ref, target, mask, anchors


@pytest.mark.parametrize("method", ["global_shift", "tracker", "rolling", "aci"])
def test_future_targets_and_masks_cannot_change_current_actions(method):
    ref, s, m, a = example()
    cfg = Config(method=method, step_size=2., gamma=.05, window_steps=20)
    first = run(ref, s, m, a, cfg)
    changed_s = s.copy()
    changed_s[12:] += 100
    changed_m = m.copy()
    changed_m[12:] = False
    # Issue12 is first usable at issue20, never at issue19.
    second = run(ref, changed_s, changed_m, a, cfg)
    np.testing.assert_array_equal(first.actions[:20], second.actions[:20])
    third = run(ref, changed_s, m, a, cfg)
    np.testing.assert_array_equal(first.actions[:20], third.actions[:20])


@pytest.mark.parametrize("method", ["tracker", "rolling", "aci"])
def test_strict_seven_step_release_boundary(method):
    r = np.zeros((3, 1)); s = np.full_like(r, 4); m = np.ones_like(r, bool)
    out = run(r, s, m, np.array([0, 7, 8]), Config(method=method, step_size=1))
    np.testing.assert_array_equal(out.actions[:2], 0.)
    assert out.actions[2, 0] > 0
    np.testing.assert_array_equal(out.trace["released_issues"], [0, 0, 1])


def test_tracker_has_hand_computed_update_and_no_repeat():
    r = np.zeros((4, 2)); s = np.ones_like(r); m = np.ones_like(r, bool)
    out = run(r, s, m, np.array([0, 8, 9, 10]), Config(method="tracker", step_size=2., target_event_rate=.1))
    np.testing.assert_allclose(out.actions[:, 0], [0, 1.8, 1.8, 1.8], rtol=0, atol=0)
    np.testing.assert_array_equal(out.trace["updated_issues"], [0, 1, 1, 1])
    assert out.observed_feedback_cells == 2


def test_gaps_release_all_past_issues_once():
    r = np.zeros((3, 1)); s = np.full_like(r, 4); m = np.ones_like(r, bool)
    out = run(r, s, m, np.array([0, 1, 100]), Config(method="tracker", step_size=1., target_event_rate=.1))
    assert out.actions[-1, 0] == 1.8
    assert out.processed_feedback_issues == 2
    assert out.observed_feedback_issues == 2


@pytest.mark.parametrize("method", ["tracker", "rolling", "aci"])
def test_zero_population_does_not_update_or_remove_actions(method):
    r, s, m, a = example()
    m[:] = False; s[:] = np.nan
    out = run(r, s, m, a, Config(method=method))
    np.testing.assert_array_equal(out.actions, r)
    assert out.observed_feedback_issues == out.observed_feedback_cells == 0
    assert out.processed_feedback_issues == 32
    if method == "aci": np.testing.assert_array_equal(out.trace["alpha"], .1)


def test_equality_is_not_an_event():
    r = np.full((2, 2), 5.); m = np.ones_like(r, bool)
    out = run(r, r.copy(), m, np.array([0, 8]), Config(method="tracker", step_size=2., target_event_rate=.1))
    np.testing.assert_allclose(out.actions[-1], 4.8, rtol=0, atol=0)
    assert out.trace["last_feedback_event_rate"][-1] == 0


def test_rolling_quantile_uses_signed_reference_residual_not_adjusted_residual():
    r = np.full((3, 2), 10.); s = np.array([[12., 14.], [11., 13.], [50., 50.]])
    out = run(r, s, np.ones_like(r, bool), np.array([0, 8, 16]), Config(method="rolling", quantile=.5, window_steps=144))
    np.testing.assert_array_equal(out.actions[:, 0], [10., 14., 13.])
    # Higher median of original residuals [2,4,1,3] is3, not a residual of action14.
    assert out.trace["window_cells"][-1] == 4


@pytest.mark.parametrize("method", ["rolling", "aci"])
def test_rolling_window_is_issue_clock_not_compressed_valid_time(method):
    r = np.zeros((3, 1)); s = np.full_like(r, 5); m = np.ones_like(r, bool)
    out = run(r, s, m, np.array([0, 8, 200]), Config(method=method, window_steps=144))
    np.testing.assert_array_equal(out.actions[:, 0], [0., 5., 0.])
    np.testing.assert_array_equal(out.trace["window_cells"], [0, 1, 0])


def test_negative_residual_can_reduce_action_and_final_action_is_nonnegative():
    r = np.full((2, 1), 10.); s = np.zeros_like(r)
    out = run(r, s, np.ones_like(r, bool), np.array([0, 8]), Config(method="rolling"))
    np.testing.assert_array_equal(out.actions[:, 0], [10., 0.])


def test_aci_direction_and_numerical_projection():
    r = np.zeros((3, 1)); s = np.ones_like(r); m = np.ones_like(r, bool)
    out = run(r, s, m, np.array([0, 8, 16]), Config(method="aci", gamma=1., target_event_rate=.1))
    np.testing.assert_allclose(out.trace["alpha"], [.1, .001, .101], rtol=0, atol=1e-15)
    assert out.trace["quantile"][1] == .999
    # At issue8 action is1, hence equality at issue8 produces no event at16.
    np.testing.assert_array_equal(out.actions[:, 0], [0., 1., 1.])


def test_aci_upper_projection():
    r = np.ones((2, 1)); s = np.zeros_like(r); m = np.ones_like(r, bool)
    out = run(r, s, m, np.array([0, 8]), Config(method="aci", gamma=20, target_event_rate=.1))
    assert out.trace["alpha"][-1] == .999


@pytest.mark.parametrize("rate", [.05, .075, .09, .10])
def test_target_rate_is_a_learning_parameter_and_has_no_qualification_output(rate):
    r, s, m, a = example()
    out = run(r, s, m, a, Config(method="tracker", target_event_rate=rate))
    assert out.config.target_event_rate == rate
    assert not hasattr(out, "qualified")
    assert out.trace is not None and "qualification" not in out.trace


@pytest.mark.parametrize("window", [144, 432, 1008])
@pytest.mark.parametrize("q", [.9, .925, .95, .975])
def test_required_rolling_hyperparameters(window, q):
    out = run(*example(15), Config(method="rolling", window_steps=window, quantile=q))
    assert np.isfinite(out.actions).all()
    assert out.trace["quantile"][-1] == q


@pytest.mark.parametrize("method", ["fixed", "tracker", "rolling", "aci"])
def test_trace_disabled_preserves_exact_actions_and_input_arrays(method):
    args = example(); before = [v.copy() for v in args]
    first = run(*args, Config(method=method))
    second = run(*args, Config(method=method), save_trace=False)
    np.testing.assert_array_equal(first.actions, second.actions)
    assert second.trace is None
    assert not first.actions.flags.writeable
    for a, b in zip(args, before): np.testing.assert_array_equal(a, b)


def test_initial_residual_history_needs_maturity_and_expires():
    r = np.zeros((2, 1)); s = np.ones_like(r); m = np.zeros_like(r, bool)
    out = run(r, s, m, np.array([20, 200]), Config(method="rolling", window_steps=144),
              initial_residuals=np.array([1., 5.]), initial_residual_anchors=np.array([1, 0]))
    np.testing.assert_array_equal(out.actions[:, 0], [5., 0.])
    with pytest.raises(ValueError, match="matured"):
        run(r, s, m, np.array([20, 200]), Config(method="rolling"),
            initial_residuals=[1.], initial_residual_anchors=np.array([13]))


@pytest.mark.parametrize("mutator", ["reference_nan", "negative_reference", "target_nan", "negative_target", "duplicate_clock", "float_clock", "nonbool_mask"])
def test_malformed_source_rejected(mutator):
    r, s, m, a = example()
    if mutator == "reference_nan": r[-1, -1] = np.nan
    if mutator == "negative_reference": r[0, 0] = -1
    if mutator == "target_nan": s[-1, -1] = np.nan
    if mutator == "negative_target": s[0, 0] = -1
    if mutator == "duplicate_clock": a[1] = a[0]
    if mutator == "float_clock": a = a.astype(float)
    if mutator == "nonbool_mask": m = m.astype(int)
    with pytest.raises(ValueError): run(r, s, m, a, Config())


@pytest.mark.parametrize("updates", [{"method":"unknown"}, {"gamma":-1}, {"step_size":-1}, {"target_event_rate":0}, {"quantile":1.01}, {"window_steps":0}, {"window_steps":1.5}, {"initial_alpha":0}])
def test_malformed_config_rejected(updates):
    with pytest.raises(ValueError): run(*example(), replace(Config(), **updates))


def test_empty_grid_is_well_defined():
    out = run(np.zeros((0, 2)), np.zeros((0, 2)), np.zeros((0, 2), bool), np.array([], dtype=np.int64), Config(method="aci"))
    assert out.actions.shape == (0, 2)
    assert out.processed_feedback_issues == 0


def test_global_shift_is_external_fixed_and_clipped_at_zero():
    r, s, m, a = example()
    out = run(r, s, m, a, Config(method="global_shift", fixed_shift=-3.))
    np.testing.assert_array_equal(out.actions, 0.)


def test_mask_cannot_hide_invalid_reference_actions():
    r, s, m, a = example(); r[-1, -1] = np.nan; m[-1, -1] = False
    with pytest.raises(ValueError, match="complete grid"): run(r, s, m, a, Config())


@pytest.mark.parametrize("method", ["global_shift", "quantile_tracker", "rolling_quantile", "aci"])
def test_independent_scalar_clock_oracle_and_prefix_replay(method):
    rng = np.random.default_rng(20261022)
    a = np.cumsum(rng.integers(1, 8, 50)).astype(np.int64)
    r = rng.uniform(0, 10, (50, 4)); s = rng.uniform(0, 14, r.shape)
    m = rng.random(r.shape) > .2; m[3] = False
    cfg = Config(method=method, step_size=.7, target_event_rate=.075,
                 gamma=.013, fixed_shift=-.5, window_steps=31, quantile=.925)
    expected = np.zeros_like(r)
    used = set(); b = 0.; alpha = .075
    for i, t in enumerate(a):
        # Directly enumerate clocks, independently of the production queue.
        arrived = [j for j in range(i) if int(a[j]) + 7 < int(t)]
        for j in arrived:
            if j in used: continue
            used.add(j)
            n = sum(bool(v) for v in m[j])
            if not n: continue
            events = sum(float(s[j, k]) > float(expected[j, k]) for k in range(4) if m[j, k]) / n
            b += cfg.step_size * (events - cfg.target_event_rate)
            alpha = min(.999, max(.001, alpha + cfg.gamma * (cfg.target_event_rate - events)))
        residual = sorted(float(s[j,k] - r[j,k]) for j in arrived if int(a[j]) >= int(t)-31
                          for k in range(4) if m[j,k])
        q = .925 if method == "rolling_quantile" else 1-alpha
        shift = {"global_shift": -.5, "quantile_tracker": b}.get(method)
        if shift is None:
            shift = residual[int(np.ceil(q * (len(residual)-1)))] if residual else 0.
        for k in range(4): expected[i,k] = max(0., r[i,k] + shift)
    actual = run(r, s, m, a, cfg)
    np.testing.assert_array_equal(actual.actions, expected)
    prefix = run(r[:23], s[:23], m[:23], a[:23], cfg)
    np.testing.assert_array_equal(actual.actions[:23], prefix.actions)
