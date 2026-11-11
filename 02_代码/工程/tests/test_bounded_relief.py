import numpy as np
import pytest

from windfarm_moe.actual_mixture_update import MixtureConfig, actual_gradient, run_mixture
from windfarm_moe.bounded_relief import fit_signed, run_signed, signed_action, signed_experts
from windfarm_moe.protected_residual import guarded_action, residual_experts
from windfarm_moe.static_convex_bundle import BundleResult


def test_zero_relief_reproduces_protected_residual_bitwise():
    rng = np.random.default_rng(20261024)
    x = rng.uniform(0.0, 25.0, (18, 4, 9))
    b = rng.uniform(2.0, 15.0, (18, 4))
    y = rng.uniform(0.0, 30.0, (18, 4))
    m = np.ones_like(y, dtype=bool)
    m[3, 1] = False
    a = np.arange(18, dtype=np.int64)
    w = rng.dirichlet(np.ones(10))

    parent_delta = residual_experts(x, b)
    child_delta = signed_experts(x, b, relief=0.0)
    np.testing.assert_array_equal(child_delta, parent_delta)
    np.testing.assert_array_equal(child_delta[:, :, 0], 0.0)

    parent_act = guarded_action(b, parent_delta, w)
    child_act, info = signed_action(b, child_delta, w, relief=0.0, return_info=True)
    np.testing.assert_array_equal(child_act, parent_act)
    assert info["boundary_guard_count"] == 0

    anchor_w = np.zeros(10)
    anchor_w[0] = 1.0
    np.testing.assert_array_equal(signed_action(b, child_delta, anchor_w, relief=0.0), b)

    cfg = [MixtureConfig(eta=0.3, schedule_power=0.5, severity_step=1.0)]
    parent_run = run_mixture(
        parent_delta,
        np.maximum(y - b, 0.0),
        m,
        a,
        cfg,
        w,
        score=False,
        return_actions=True,
    )
    child_run = run_signed(x, b, y, m, a, cfg, w, relief=0.0, score=True, return_actions=True)
    np.testing.assert_array_equal(child_run["actions"][0], b + parent_run["actions"][0])
    assert child_run["metadata"]["final_weights"] == parent_run["metadata"]["final_weights"]
    assert child_run["metadata"]["final_lambda_u"] == pytest.approx(parent_run["metadata"]["final_lambda_u"])
    assert child_run["metadata"]["release_trace"] == parent_run["metadata"]["release_trace"]


@pytest.mark.parametrize("d", [0.0, 0.1, 0.25, 0.5, 1.0])
def test_floor_nonnegative_and_floating_boundary_guard_counter(d):
    rng = np.random.default_rng(42)
    b = rng.uniform(0.5, 20.0, (12, 3))
    x = np.zeros((12, 3, 9))
    delta = signed_experts(x, b, relief=d)
    np.testing.assert_allclose(
        delta[:, :, 1:], np.broadcast_to(-d * b[:, :, None], (12, 3, 9)), rtol=0, atol=1e-15
    )

    for _ in range(10):
        w = rng.dirichlet(np.ones(10))
        act, info = signed_action(b, delta, w, relief=d, return_info=True)
        floor = (1.0 - d) * b
        assert np.all(act >= floor)
        assert np.all(act >= 0.0)
        assert info["boundary_guard_count"] >= 0

    # Force a sub-tolerance floating roundoff below (1 - d)*b with d > 0
    if d > 0.0:
        b_tiny = np.array([[10.0, 10.0]])
        inc_tiny = np.zeros((1, 2, 3))
        inc_tiny[0, 0, 1:] = -d * 10.0 - 1e-13
        inc_tiny[0, 1, 1:] = 0.0
        w_tiny = np.array([0.0, 0.5, 0.5])
        repaired, guard_info = signed_action(b_tiny, inc_tiny, w_tiny, relief=d, return_info=True)
        assert guard_info["boundary_guard_count"] == 1
        assert guard_info["max_boundary_violation"] > 0.0
        assert repaired[0, 0] == (1.0 - d) * 10.0


def test_independent_hand_fraction_oracle_first_delayed_step_and_anchor_severity_dual():
    # T=9 issues (anchors 0..8), N=4 turbines, K_raw=9 experts -> K=10 signed increments.
    # Issue 0 matures only at i=8 (0 + 7 < 8). First 8 issues (0..7) must have zero updates.
    # Let b = 10 everywhere, d = 0.5.
    # Raw experts at all issues:
    #   expert 1 (slot 1): X=0  -> delta_1 = max(0 - 10, -5) = -5
    #   expert 2 (slot 2): X=22 -> delta_2 = max(22 - 10, -5) = +12
    #   experts 3..9 (slots 3..9): X=10 -> delta_3..9 = 0
    #   slot 0 is anchor increment 0.
    # Initial weights w0: [1/4, 1/2, 1/4, 0, ..., 0]
    # Stored past actual action at issue 0 (and issues 0..7):
    #   r = 10 + (1/4)*0 + (1/2)*(-5) + (1/4)*12 = 10 - 5/2 + 3 = 21/2 = 10.5 on all 4 cells.
    # Note: raw expert 1 has X=0, whereas causal anchor b=10!
    # At issue 0, targets on the 4 cells are:
    #   cell 0: y = 25 > 10.5 (deficit: y - r = 14.5 > 0; anchor deficit: y - b = 15)
    #   cell 1: y = 10.5 == r (kink: zero subgradient! anchor deficit: y - b = 0.5)
    #   cell 2: y = 4 < 10.5  (surplus: y - r < 0; anchor deficit: max(4 - 10, 0) = 0)
    #   cell 3: y = 12 > 10.5 (deficit: y - r = 1.5 > 0; anchor deficit: y - b = 2)
    #
    # Subgradient of C = (r + 10*max(y - r, 0)) / (6 * 100) wrt r at issue 0 (lambda=0 initially):
    #   cell 0: -9 / 600
    #   cell 1:  0 / 600 (kink)
    #   cell 2: +1 / 600
    #   cell 3: -9 / 600
    # Sum of slopes across the 4 valid cells = (-9 + 0 + 1 - 9) / 600 = -17 / 600.
    # Fixed population division by N=4 gives mean slope = -17 / 2400.
    # Since delta is identical across the 4 cells: [0, -5, 12, 0, ..., 0],
    # gradient g = (-17 / 2400) * [0, -5, 12, 0, ...] = [0, 85/2400, -204/2400, 0, ...].
    # With eta = 1, schedule_power = 0.5, elapsed = a[0] - a[0] = 0 -> factor = 1:
    # Unprojected v = w0 - g:
    #   v_0 = 1/4 = 600/2400
    #   v_1 = 1/2 - 85/2400 = 1115/2400
    #   v_2 = 1/4 + 204/2400 = 804/2400
    #   v_3..9 = 0
    # For simplex projection, the 3 positive entries sum to (600 + 1115 + 804)/2400 = 2519/2400.
    # Excess over 1 is 119/2400, distributed equally over the 3 active coordinates (theta = 119/7200),
    # since 600/2400 > 119/7200 and 0 - 119/7200 < 0.
    # Exact updated weights w1:
    #   w1_0 = 600/2400 - 119/7200 = 1681/7200
    #   w1_1 = 1115/2400 - 119/7200 = 3226/7200
    #   w1_2 = 804/2400 - 119/7200 = 2293/7200
    #   w1_3..9 = 0.
    # Action at issue 8:
    #   r_8 = 10 + (-5)*(3226/7200) + 12*(2293/7200) = 10 + 11386/7200 = 83386/7200 = 41693/3600.
    #
    # Severity multiplier update (references actual anchor b=10, NOT raw expert X[:,:,0]=0):
    #   actual_u = ((25 - 10.5) + 0 + 0 + (12 - 10.5)) / (6 * 4) = 16 / 24 = 2/3.
    #   reference_u (at b=10) = ((25 - 10) + (10.5 - 10) + 0 + (12 - 10)) / (6 * 4) = 17.5 / 24 = 35/48.
    #   Wait: actual_u - reference_u = 32/48 - 35/48 = -3/48 < 0 -> clipped to 0 if actual_u < reference_u.
    # Let's also test a second case or choose y so actual_u > reference_u!
    # Wait: if r = 9.5 < b = 10 (by setting w0 = [1/4, 3/4, 0, ...] so r = 10 - 15/4 = 25/4 = 6.25 < 10),
    # then actual_u > reference_u! Let's check:
    # With w0 = [1/4, 1/2, 1/4], r = 10.5 > b = 10, so actual_u < reference_u and lambda clips to 0.
    # What if w0 = [1/8, 3/4, 1/8, 0, ...]?
    # Let's compute with w0 = [1/8, 3/4, 1/8, 0, ...]:
    #   r = 10 + (1/8)*0 + (3/4)*(-5) + (1/8)*12 = 10 - 15/4 + 6/4 = 31/4 = 7.75!
    #   Notice r = 7.75 < b = 10! That exercises the signed relief below anchor b!
    #   And at y = [25, 7.75, 4, 12]:
    #   cell 0: y=25 > 7.75 (slope -9/600)
    #   cell 1: y=7.75 == r (kink, slope 0)
    #   cell 2: y=4 < 7.75 (slope +1/600)
    #   cell 3: y=12 > 7.75 (slope -9/600)
    #   Mean slope is STILL -17 / 2400!
    #   g = [0, 85/2400, -204/2400, 0, ...].
    #   Unprojected v = w0 - g:
    #     v_0 = 300/2400
    #     v_1 = 1800/2400 - 85/2400 = 1715/2400
    #     v_2 = 300/2400 + 204/2400 = 504/2400
    #   Sum of top 3 is (300 + 1715 + 504)/2400 = 2519/2400 -> theta = 119/7200!
    #   w1_0 = 781/7200, w1_1 = 5026/7200, w1_2 = 1393/7200!
    #   And what is actual_u vs reference_u (with b=10 vs X[:,:,0]=0)?
    #   actual_u (at r=7.75):
    #     cell 0: 25 - 7.75 = 17.25
    #     cell 1: 7.75 - 7.75 = 0
    #     cell 2: 0
    #     cell 3: 12 - 7.75 = 4.25
    #     sum = 21.5 -> actual_u = 21.5 / 24 = 43 / 48.
    #   reference_u at causal anchor b = 10:
    #     cell 0: 25 - 10 = 15
    #     cell 1: max(7.75 - 10, 0) = 0
    #     cell 2: 0
    #     cell 3: 12 - 10 = 2
    #     sum = 17 -> reference_u = 17 / 24 = 34 / 48.
    #   (Whereas if reference_u erroneously used raw expert 0 X[:,:,0]=0, sum would be 25+7.75+4+12 = 48.75 -> actual_u < ref_u -> lambda=0!)
    #   With gamma = 10, factor = 1:
    #     lambda_1 = 0 + 10 * 1 * 10 * (43/48 - 34/48) / 100 = (9 / 48) = 3 / 16 = 0.1875!
    b = np.full((9, 4), 10.0)
    x = np.full((9, 4, 9), 10.0)
    x[:, :, 0] = 0.0
    x[:, :, 1] = 22.0
    y = np.tile(np.array([25.0, 7.75, 4.0, 12.0]), (9, 1))
    m = np.ones_like(y, dtype=bool)
    a = np.arange(9, dtype=np.int64)
    w0 = np.array([1 / 8, 3 / 4, 1 / 8] + [0.0] * 7)
    cfg = MixtureConfig(eta=1.0, schedule_power=0.5, severity_step=10.0, cost_scale=100.0)

    res = run_signed(x, b, y, m, a, [cfg], w0, relief=0.5, score=True, return_actions=True)

    # First 8 steps have no feedback
    assert res["metadata"]["release_trace"][:8] == [-1] * 8
    assert res["metadata"]["release_trace"][8] == 7
    assert res["metadata"]["feedback_updates"] == 1
    np.testing.assert_allclose(res["actions"][0, :8], 7.75, rtol=0, atol=1e-15)

    expected_w1 = np.array([781 / 7200, 5026 / 7200, 1393 / 7200] + [0.0] * 7)
    np.testing.assert_allclose(res["metadata"]["final_weights"][0], expected_w1, rtol=0, atol=1e-15)
    assert res["metadata"]["final_lambda_u"][0] == pytest.approx(3 / 16, abs=1e-15)
    expected_r8 = 10.0 + (-5.0) * (5026 / 7200) + 12.0 * (1393 / 7200)
    np.testing.assert_allclose(res["actions"][0, 8], expected_r8, rtol=0, atol=1e-14)


def test_elapsed_schedule_and_stored_past_action_with_nonzero_lambda():
    # Two updates: anchors [0, 72, 144].
    # At i=0 (a=0): r_0 = 8.
    # At i=1 (a=72): 0 + 7 < 72 -> issue 0 updates with elapsed = 0, factor = 1.
    # At i=2 (a=144): 72 + 7 < 144 -> issue 1 updates with elapsed = 72, factor = (1 + 72/144)^(-1) = 2/3,
    # and uses stored past action from i=1 and lambda from step 1.
    b = np.full((3, 2), 10.0)
    x = np.full((3, 2, 9), 10.0)
    x[:, :, 0] = 6.0   # delta_1 = -4
    x[:, :, 1] = 14.0  # delta_2 = +4
    y = np.full((3, 2), 12.0)
    m = np.ones((3, 2), dtype=bool)
    a = np.array([0, 72, 144], dtype=np.int64)
    w0 = np.array([0.0, 0.5, 0.5] + [0.0] * 7)  # r_0 = 10 + 0.5*(-4) + 0.5*(+4) = 10
    # Wait: make w0 = [0.0, 0.75, 0.25, 0...] so r_0 = 10 - 3 + 1 = 8 < 10 < 12!
    w0 = np.array([0.0, 0.75, 0.25] + [0.0] * 7)
    cfg = MixtureConfig(eta=1.0, schedule_power=1.0, severity_step=10.0)
    res = run_signed(x, b, y, m, a, [cfg], w0, relief=0.5, return_actions=True)

    # Step 1 (from issue 0, r_0 = 8, y = 12, lam = 0, factor = 1):
    # slope = -9 / 600 = -3 / 200 on both cells.
    # g = (-3 / 200) * [0, -4, 4, 0...] = [0, 12/200, -12/200, 0...] = [0, 0.06, -0.06, 0...]
    # w1 = [0, 0.75 - 0.06, 0.25 + 0.06, 0...] = [0, 0.69, 0.31, 0...] (already on simplex!)
    # actual_u = (12 - 8)/6 = 4/6; reference_u (at b=10) = (12 - 10)/6 = 2/6.
    # lam_1 = 10 * 1 * 10 * (2/6) / 100 = 1/3.
    # Action at i=1: r_1 = 10 + 0.69*(-4) + 0.31*(4) = 10 - 1.52 = 8.48.
    np.testing.assert_allclose(res["actions"][0, 1], 8.48, rtol=0, atol=1e-14)

    # Step 2 (from issue 1, stored actual r_1 = 8.48 < 12, lam_1 = 1/3, factor = (1 + 72/144)^(-1) = 2/3):
    # slope with lam_1 = 1/3: (-9 - (1/3)*10) / 600 = (-37/3) / 600 = -37 / 1800.
    # g2 = (-37 / 1800) * [0, -4, 4, 0...] = [0, 148/1800, -148/1800, 0...].
    # step = eta * factor * g2 = (2/3) * (148/1800) = 148 / 2700 = 37 / 675.
    # w2 = [0, 0.69 - 37/675, 0.31 + 37/675, 0...].
    expected_w2 = np.array([0.0, 0.69 - 37 / 675, 0.31 + 37 / 675] + [0.0] * 7)
    np.testing.assert_allclose(res["metadata"]["final_weights"][0], expected_w2, rtol=0, atol=1e-14)
    expected_lam2 = 1 / 3 + 10.0 * (2 / 3) * 10.0 * ((12.0 - 8.48) / 6.0 - 2.0 / 6.0) / 100.0
    assert res["metadata"]["final_lambda_u"][0] == pytest.approx(expected_lam2, abs=1e-14)


def test_asymmetric_sparse_mask_and_invalid_unmasked_targets_excluded():
    b = np.full((10, 3), 10.0)
    x = np.full((10, 3, 9), 12.0)
    x[:, :, 0] = 6.0
    y = np.full((10, 3), 15.0)
    m = np.ones((10, 3), dtype=bool)
    # Mask out cells with NaN or negative values; unmasked future/masked cells must not crash
    m[0, 1:] = False
    y[0, 1] = np.nan
    y[0, 2] = -999.0
    m[1, :] = False
    y[1, :] = np.nan
    a = np.arange(10, dtype=np.int64)
    w0 = np.full(10, 0.1)
    cfg = [MixtureConfig(eta=0.3, schedule_power=0.5, severity_step=1.0)]

    res = run_signed(x, b, y, m, a, cfg, w0, relief=0.25, score=True, return_actions=True)
    # Only issue 0 had valid>0 among matured issues {0, 1} at i=9
    assert res["metadata"]["feedback_updates"] == 1
    assert np.isfinite(res["actions"]).all()
    assert np.isfinite(res["ledger"]).all()

    # Check fixed node_count=3 division on issue 0 (1 valid cell out of 3)
    delta0 = signed_experts(x[:1], b[:1], relief=0.25)[0]
    r0 = signed_action(b[0], delta0, w0, relief=0.25)
    g_expected = actual_gradient(delta0[:1], y[0, :1], r0[None, :1], node_count=3)
    w1_expected = run_signed(
        x[:9], b[:9], y[:9], m[:9], a[:9], [MixtureConfig(eta=1.0, schedule_power=0.0)], w0, relief=0.25
    )["metadata"]["final_weights"][0]
    from windfarm_moe.actual_mixture_update import project_simplex
    np.testing.assert_allclose(w1_expected, project_simplex(w0[None, :] - g_expected)[0], rtol=0, atol=1e-14)


def test_invalid_inputs_and_matured_invalid_targets_rejected():
    b = np.full((9, 2), 5.0)
    x = np.full((9, 2, 9), 6.0)
    y = np.full((9, 2), 4.0)
    m = np.ones((9, 2), dtype=bool)
    a = np.arange(9, dtype=np.int64)
    w0 = np.full(10, 0.1)

    with pytest.raises(ValueError):
        signed_experts(x, b, relief=-0.1)
    with pytest.raises(ValueError):
        signed_experts(x, b, relief=1.1)
    with pytest.raises(ValueError):
        signed_experts(x, -b, relief=0.2)
    with pytest.raises(ValueError):
        signed_experts(-x, b, relief=0.2)

    bad_inc = signed_experts(x, b, relief=0.2)
    bad_inc_slot0 = bad_inc.copy()
    bad_inc_slot0[0, 0, 0] = 1.0
    with pytest.raises(ValueError):
        signed_action(b, bad_inc_slot0, w0, relief=0.2)

    bad_inc_floor = bad_inc.copy()
    bad_inc_floor[0, 0, 1] = -0.5 * b[0, 0]
    with pytest.raises(ValueError):
        signed_action(b, bad_inc_floor, w0, relief=0.2)

    # Matured valid target with NaN or negative must raise ValueError
    y_bad = y.copy()
    y_bad[0, 0] = np.nan
    with pytest.raises(ValueError, match="Invalid matured target"):
        run_signed(x, b, y_bad, m, a, [MixtureConfig()], w0, relief=0.2, score=False)

    y_neg = y.copy()
    y_neg[0, 0] = -1.0
    with pytest.raises(ValueError, match="Invalid matured target"):
        run_signed(x, b, y_neg, m, a, [MixtureConfig()], w0, relief=0.2, score=False)

    # Scored valid target with NaN must raise ValueError when score=True
    y_score_bad = y.copy()
    y_score_bad[5, 0] = np.nan
    with pytest.raises(ValueError, match="Invalid scored target"):
        run_signed(x, b, y_score_bad, m, a, [MixtureConfig()], w0, relief=0.2, score=True)


def test_group_configs_broadcast_eta0_static_and_no_qualification_gating():
    rng = np.random.default_rng(7)
    b = rng.uniform(4.0, 12.0, (16, 3))
    x = rng.uniform(0.0, 20.0, (16, 3, 9))
    y = rng.uniform(0.0, 25.0, (16, 3))
    m = np.ones_like(y, dtype=bool)
    a = np.arange(16, dtype=np.int64)
    w0 = np.array([0.4, 0.6] + [0.0] * 8)

    configs = [
        MixtureConfig(eta=0.0, schedule_power=0.5, severity_step=0.0),
        MixtureConfig(eta=0.3, schedule_power=0.5, severity_step=0.0),
        MixtureConfig(eta=30.0, schedule_power=0.0, severity_step=10.0),
    ]
    res = run_signed(x, b, y, m, a, configs, w0, relief=0.25, score=True, return_actions=True)
    assert res["actions"].shape == (3, 16, 3)
    assert res["ledger"].shape == (3, 1, 4)

    delta = signed_experts(x, b, relief=0.25)
    static_act = signed_action(b, delta, w0, relief=0.25)
    # eta=0 is bitwise static across the entire episode
    np.testing.assert_array_equal(res["actions"][0], static_act)
    assert res["metadata"]["final_weights"][0] == w0.tolist()
    # All configs share identical actions on the first 8 steps before feedback matures
    for c_idx in range(3):
        np.testing.assert_array_equal(res["actions"][c_idx, :8], static_act[:8])


def test_fit_signed_cost_and_cap_feasibility_and_bisection_repair(monkeypatch):
    rng = np.random.default_rng(19)
    b = rng.uniform(5.0, 10.0, (25, 2))
    x = rng.uniform(0.0, 18.0, (25, 2, 9))
    y = rng.uniform(0.0, 16.0, (25, 2))

    cost_fit = fit_signed(x, b, y, relief=0.25, goal="COST", time_limit=99.0)
    assert cost_fit["time_limit"] == 10.0
    assert cost_fit["support_smoothing"] == 0.0
    np.testing.assert_array_equal(cost_fit["weights"], cost_fit["canonical_initial"])
    assert np.isclose(np.sum(cost_fit["weights"]), 1.0)
    assert (np.asarray(cost_fit["weights"]) >= 0.0).all()

    cap_fit = fit_signed(x, b, y, relief=0.25, goal="CAP", time_limit=5.0)
    assert cap_fit["uncovered_cap"] == pytest.approx(cap_fit["anchor_mean_uncovered_power"])
    assert cap_fit["mean_uncovered_power"] <= cap_fit["uncovered_cap"]
    assert cap_fit["actual_affine_feasible"]

    # Simulate a numerical CAP violation from fit_bundle and verify bisection repair toward anchor
    violating_w = np.zeros(10)
    violating_w[1] = 1.0
    b_simple = np.full((10, 2), 10.0)
    x_simple = np.zeros((10, 2, 9))
    y_simple = np.full((10, 2), 9.0)  # anchor b=10 has uncovered_cap = 0.0; expert 1 has action 5.0 -> uncovered = 4.0 > 0

    def fake_fit_bundle(shifted, y_flat, *, uncovered_cap=None, time_limit=10.0, max_iter=1000, relative_tolerance=1e-7):
        return BundleResult(
            weights=violating_w.copy(),
            status="OPTIMAL_NUMERICAL_BOUNDS",
            optimal=True,
            objective=1.0,
            lower_bound=0.9,
            gap=0.1,
            mean_uncovered_power=0.0,
            uncovered_cap=uncovered_cap,
            iterations=5,
            elapsed_seconds=0.01,
            numerical_tolerance=1e-7,
        )

    monkeypatch.setattr("windfarm_moe.bounded_relief.fit_bundle", fake_fit_bundle)
    repaired = fit_signed(x_simple, b_simple, y_simple, relief=0.5, goal="CAP", time_limit=5.0)
    assert repaired["repaired_to_anchor"]
    assert not repaired["raw_actual_affine_feasible"]
    assert repaired["repair_alpha"] > 0.0
    assert not repaired["optimal"]
    assert repaired["status"].endswith("_CAP_REPAIRED")
    assert repaired["mean_uncovered_power"] <= repaired["uncovered_cap"]
    assert repaired["actual_affine_feasible"]

    # Simulate an internal solver exception and verify numerical failure/status retention
    def broken_fit_bundle(*args, **kwargs):
        raise RuntimeError("solver crash")

    monkeypatch.setattr("windfarm_moe.bounded_relief.fit_bundle", broken_fit_bundle)
    failed = fit_signed(x_simple, b_simple, y_simple, relief=0.5, goal="CAP", time_limit=5.0)
    assert not failed["optimal"]
    assert failed["status"] == "BUNDLE_NUMERICAL_FAILURE_ANCHOR_FALLBACK"
    assert "solver crash" in failed["numerical_failure"]
    np.testing.assert_array_equal(failed["weights"], [1.0] + [0.0] * 9)
    assert failed["actual_affine_feasible"]

