from fractions import Fraction
import json

import numpy as np
import pytest
from scipy.optimize import linprog

from windfarm_moe.bounded_relief import fit_signed, signed_experts
from windfarm_moe.conditional_convex_pool import (
    context_ids,
    fit_conditional_pool,
    fit_context_cuts,
    initialize_anchor_record,
    predict_conditional_pool,
)


def _solve_independent_full_lp_oracle(
    x: np.ndarray,
    b: np.ndarray,
    y: np.ndarray,
    mask: np.ndarray,
    anchors: np.ndarray,
    reference: np.ndarray,
    *,
    groups: int,
    relief: float,
    cap_mode: str,
    cuts: list[float] | None = None,
) -> dict:
    """Independent full-row epigraph LP oracle built directly from row constraints without cutting-plane code."""
    if cuts is None:
        cuts = [] if groups == 1 else [float(v) for v in np.quantile(reference.reshape(-1), [1.0 / 3.0, 2.0 / 3.0], method="linear")]
    ctx = np.zeros(reference.shape, dtype=np.int64) if len(cuts) == 0 else np.searchsorted(cuts, reference, side="right")

    delta = signed_experts(x, b, relief)
    valid = np.asarray(mask, dtype=bool)
    b_v = b[valid]
    y_v = y[valid]
    d_v = delta[valid]
    c_v = ctx[valid]
    day_grid = np.broadcast_to((anchors // 144)[:, None], b.shape)
    day_v = day_grid[valid]

    n_valid = int(b_v.size)
    k = 25
    dim_w = groups * k
    # Variables: [w_{0,0}..w_{G-1,24}, u_0..u_{n_valid-1}]
    n_vars = dim_w + n_valid

    # Objective: (1 / (6 * n_valid)) * sum_i (b_i + sum_k delta_{i,k} w_{c_i, k} + 10 * u_i)
    # The constant sum(b_i)/(6*n_valid) is added after solving.
    c_obj = np.zeros(n_vars, dtype=np.float64)
    for idx in range(n_valid):
        grp = int(c_v[idx])
        c_obj[grp * k : (grp + 1) * k] += d_v[idx] / (6.0 * n_valid)
    c_obj[dim_w:] = 10.0 / (6.0 * n_valid)
    const_term = float(b_v.sum() / (6.0 * n_valid))

    # Row epigraph constraints: -sum_k delta_{i,k} w_{c_i,k} - u_i <= -(y_i - b_i)
    A_rows = []
    b_rows = []
    for idx in range(n_valid):
        row = np.zeros(n_vars, dtype=np.float64)
        grp = int(c_v[idx])
        row[grp * k : (grp + 1) * k] = -d_v[idx]
        row[dim_w + idx] = -1.0
        A_rows.append(row)
        b_rows.append(-(float(y_v[idx] - b_v[idx])))

    anchor_z = np.maximum(y_v - b_v, 0.0)
    pooled_cap = float(anchor_z.mean())
    unique_days = np.unique(day_v)
    day_caps = [float(anchor_z[day_v == d_id].mean()) for d_id in unique_days]

    if cap_mode == "POOLED":
        cap_row = np.zeros(n_vars, dtype=np.float64)
        cap_row[dim_w:] = 1.0 / float(n_valid)
        A_rows.append(cap_row)
        b_rows.append(pooled_cap)
    elif cap_mode == "DAY":
        for d_id, cap_d in zip(unique_days, day_caps):
            dm = day_v == d_id
            n_d = int(np.count_nonzero(dm))
            cap_row = np.zeros(n_vars, dtype=np.float64)
            cap_row[dim_w + np.flatnonzero(dm)] = 1.0 / float(n_d)
            A_rows.append(cap_row)
            b_rows.append(cap_d)

    A_ub = np.asarray(A_rows, dtype=np.float64)
    b_ub = np.asarray(b_rows, dtype=np.float64)

    A_eq = np.zeros((groups, n_vars), dtype=np.float64)
    for grp in range(groups):
        A_eq[grp, grp * k : (grp + 1) * k] = 1.0
    b_eq = np.ones(groups, dtype=np.float64)

    bounds = []
    for grp in range(groups):
        if int(np.count_nonzero(c_v == grp)) == 0:
            bounds.append((1.0, 1.0))
            bounds.extend([(0.0, 0.0)] * (k - 1))
        else:
            bounds.extend([(0.0, 1.0)] * k)
    bounds.extend([(0.0, None)] * n_valid)

    res = linprog(
        c_obj,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
        options={"threads": 1, "primal_feasibility_tolerance": 1e-9, "dual_feasibility_tolerance": 1e-9},
    )
    assert res.success, f"Oracle LP failed: {res.message}"
    w_opt = res.x[:dim_w].reshape(groups, k)
    obj_opt = float(res.fun + const_term)
    return dict(
        weights=w_opt,
        objective=obj_opt,
        pooled_cap=pooled_cap,
        day_caps=day_caps,
        cuts=cuts,
    )


@pytest.mark.parametrize("groups", [1, 3])
@pytest.mark.parametrize("cap_mode", ["COST", "POOLED", "DAY"])
@pytest.mark.parametrize("relief", [0.0, 0.03, 0.1, 1.0])
def test_independent_full_lp_epigraph_oracle_agreement(groups, cap_mode, relief):
    rng = np.random.default_rng(20261025 + 100 * groups + int(100 * relief) + len(cap_mode))
    t_steps, n_nodes = 18, 4
    # Span 3 weather days (6 steps per day)
    anchors = np.concatenate([
        np.arange(6, dtype=np.int64),
        144 + np.arange(6, dtype=np.int64),
        288 + np.arange(6, dtype=np.int64),
    ])
    b = rng.uniform(4.0, 12.0, (t_steps, n_nodes))
    x = rng.uniform(0.0, 20.0, (t_steps, n_nodes, 24))
    reference = rng.uniform(1.0, 18.0, (t_steps, n_nodes))
    y = rng.uniform(0.0, 18.0, (t_steps, n_nodes))
    mask = np.ones((t_steps, n_nodes), dtype=bool)
    mask[1, 2] = False
    mask[8, 0] = False
    y[~mask] = np.nan

    actual = fit_conditional_pool(
        x,
        b,
        y,
        mask,
        anchors,
        reference,
        groups=groups,
        relief=relief,
        cap_mode=cap_mode,
        time_limit=8.0,
        max_iter=1200,
        tol=1e-7,
    )
    oracle = _solve_independent_full_lp_oracle(
        x,
        b,
        y,
        mask,
        anchors,
        reference,
        groups=groups,
        relief=relief,
        cap_mode=cap_mode,
    )

    # JSON round-trip check
    dumped = json.dumps(actual, allow_nan=False)
    loaded = json.loads(dumped)
    assert loaded["groups"] == groups
    assert loaded["cap_mode"] == cap_mode

    assert actual["actual_feasible"]
    assert actual["cuts"] == pytest.approx(oracle["cuts"], abs=1e-12)
    assert actual["lower_bound"] <= oracle["objective"] + 2e-6
    assert actual["objective"] == pytest.approx(oracle["objective"], abs=3e-5)

    w_arr = np.asarray(actual["weights"], dtype=np.float64)
    assert w_arr.shape == (groups, 25)
    assert np.all(w_arr >= 0.0)
    np.testing.assert_allclose(w_arr.sum(axis=1), 1.0, rtol=0.0, atol=1e-12)

    if cap_mode == "POOLED":
        assert actual["uncovered_cap"] == pytest.approx(oracle["pooled_cap"], abs=1e-12)
        assert actual["mean_uncovered_power"] <= actual["uncovered_cap"]
    elif cap_mode == "DAY":
        assert actual["day_caps"] == pytest.approx(oracle["day_caps"], abs=1e-12)
        for u_day, c_day in zip(actual["day_uncovered_power"], actual["day_caps"]):
            assert u_day <= c_day


def test_multi_context_strict_cost_gain_over_single_pool_and_day_guard_tradeoff():
    t_steps, n_nodes = 21, 3
    anchors = np.r_[np.arange(20, dtype=np.int64), 144]
    b = np.full((t_steps, n_nodes), 10.0)
    reference = np.tile(np.array([1.0, 5.0, 9.0]), (t_steps, 1))
    cuts = fit_context_cuts(reference, groups=3)
    ctx = context_ids(reference, cuts)
    assert np.all(ctx[:, 0] == 0) and np.all(ctx[:, 1] == 1) and np.all(ctx[:, 2] == 2)

    x = np.full((t_steps, n_nodes, 24), 10.0)
    x[:, :, 0] = 0.0
    x[:, :, 1] = 20.0

    y = np.zeros((t_steps, n_nodes), dtype=np.float64)
    y[:20, :] = np.array([0.0, 10.0, 20.0])
    y[20, :] = np.array([8.0, 10.0, 10.0])
    mask = np.ones_like(y, dtype=bool)

    fit_g1 = fit_conditional_pool(x, b, y, mask, anchors, reference, groups=1, relief=1.0, cap_mode="COST", tol=1e-7)
    fit_g3 = fit_conditional_pool(x, b, y, mask, anchors, reference, groups=3, relief=1.0, cap_mode="COST", tol=1e-7)
    oracle_g1 = _solve_independent_full_lp_oracle(x, b, y, mask, anchors, reference, groups=1, relief=1.0, cap_mode="COST")
    oracle_g3 = _solve_independent_full_lp_oracle(x, b, y, mask, anchors, reference, groups=3, relief=1.0, cap_mode="COST")
    assert fit_g1["actual_feasible"] and fit_g3["actual_feasible"]
    assert fit_g1["objective"] == pytest.approx(oracle_g1["objective"], abs=1e-7)
    assert fit_g3["objective"] == pytest.approx(oracle_g3["objective"], abs=1e-7)
    assert fit_g3["objective"] < fit_g1["objective"]

    fit_pooled = fit_conditional_pool(x, b, y, mask, anchors, reference, groups=3, relief=1.0, cap_mode="POOLED", tol=1e-7)
    fit_day = fit_conditional_pool(x, b, y, mask, anchors, reference, groups=3, relief=1.0, cap_mode="DAY", tol=1e-7)
    oracle_pooled = _solve_independent_full_lp_oracle(
        x, b, y, mask, anchors, reference, groups=3, relief=1.0, cap_mode="POOLED"
    )
    oracle_day = _solve_independent_full_lp_oracle(
        x, b, y, mask, anchors, reference, groups=3, relief=1.0, cap_mode="DAY"
    )
    assert fit_pooled["actual_feasible"] and fit_day["actual_feasible"]
    assert fit_pooled["objective"] == pytest.approx(oracle_pooled["objective"], abs=1e-7)
    assert fit_day["objective"] == pytest.approx(oracle_day["objective"], abs=1e-7)
    assert fit_pooled["mean_uncovered_power"] <= fit_pooled["uncovered_cap"] + 1e-12
    assert fit_day["day_caps"][1] == 0.0
    assert fit_day["day_uncovered_power"][1] == pytest.approx(0.0, abs=1e-12)

    act_pooled, _ = predict_conditional_pool(x, b, reference, fit_pooled)
    u_lastday_pooled = float(np.maximum(y[20:] - act_pooled[20:], 0.0).mean())
    assert u_lastday_pooled == pytest.approx(8.0 / 3.0, abs=1e-7)
    assert fit_pooled["objective"] < fit_day["objective"]





def test_g1_cost_and_pooled_match_fit_signed_objective():
    rng = np.random.default_rng(99)
    t_steps, n_nodes = 14, 3
    anchors = np.arange(t_steps, dtype=np.int64)
    b = rng.uniform(5.0, 11.0, (t_steps, n_nodes))
    x = rng.uniform(0.0, 18.0, (t_steps, n_nodes, 24))
    y = rng.uniform(0.0, 16.0, (t_steps, n_nodes))
    reference = rng.uniform(2.0, 14.0, (t_steps, n_nodes))
    mask = np.ones((t_steps, n_nodes), dtype=bool)

    for cap_mode, signed_goal in [("COST", "COST"), ("POOLED", "CAP")]:
        cond = fit_conditional_pool(
            x, b, y, mask, anchors, reference, groups=1, relief=0.1, cap_mode=cap_mode, time_limit=8.0
        )
        signed = fit_signed(x, b, y, relief=0.1, goal=signed_goal, time_limit=8.0)
        assert cond["optimal"] and signed["optimal"]
        assert cond["objective"] == pytest.approx(signed["objective"], abs=2e-5)
        if cap_mode == "POOLED":
            assert cond["uncovered_cap"] == pytest.approx(signed["uncovered_cap"], abs=1e-12)
            assert cond["mean_uncovered_power"] <= cond["uncovered_cap"]


def test_cut_invariance_to_targets_and_masks_and_cpz_shared_reference():
    rng = np.random.default_rng(314)
    t_steps, n_nodes = 12, 4
    anchors = np.arange(t_steps, dtype=np.int64)
    b = rng.uniform(3.0, 10.0, (t_steps, n_nodes))
    x_c = rng.uniform(0.0, 15.0, (t_steps, n_nodes, 24))
    x_p = rng.uniform(0.0, 15.0, (t_steps, n_nodes, 24))
    x_z = rng.uniform(0.0, 15.0, (t_steps, n_nodes, 24))
    ref = rng.uniform(1.0, 12.0, (t_steps, n_nodes))

    y1 = rng.uniform(0.0, 20.0, (t_steps, n_nodes))
    m1 = np.ones((t_steps, n_nodes), dtype=bool)

    y2 = rng.uniform(0.0, 50.0, (t_steps, n_nodes))
    m2 = np.zeros((t_steps, n_nodes), dtype=bool)
    m2[0, 0] = True
    y2[~m2] = np.nan

    res_c = fit_conditional_pool(x_c, b, y1, m1, anchors, ref, groups=3, relief=0.03, cap_mode="COST")
    res_p = fit_conditional_pool(x_p, b, y2, m2, anchors, ref, groups=3, relief=0.03, cap_mode="POOLED")
    res_z = fit_conditional_pool(x_z, b, y2, np.zeros_like(m1), anchors, ref, groups=3, relief=0.03, cap_mode="DAY")

    expected_cuts = fit_context_cuts(ref, groups=3)
    assert res_c["cuts"] == expected_cuts
    assert res_p["cuts"] == expected_cuts
    assert res_z["cuts"] == expected_cuts
    assert res_z["status"] == "EMPTY_VALID_POPULATION_ANCHOR"
    assert not res_z["optimal"]


def test_ties_empty_valid_groups_fallback_to_anchor_and_all_masked_fallback():
    # Constant reference -> cuts = [5.0, 5.0], searchsorted([5.0, 5.0], 5.0, side='right') == 2.
    # Groups 0 and 1 have 0 total and 0 valid cells; only group 2 is populated!
    t_steps, n_nodes = 8, 3
    anchors = np.arange(t_steps, dtype=np.int64)
    b = np.full((t_steps, n_nodes), 8.0)
    x = np.full((t_steps, n_nodes, 24), 12.0)
    y = np.full((t_steps, n_nodes), 10.0)
    mask = np.ones((t_steps, n_nodes), dtype=bool)
    ref_ties = np.full((t_steps, n_nodes), 5.0)

    res = fit_conditional_pool(x, b, y, mask, anchors, ref_ties, groups=3, relief=0.1, cap_mode="COST")
    assert res["cuts"] == [5.0, 5.0]
    assert res["group_total_counts"] == [0, 0, 24]
    assert res["group_valid_counts"] == [0, 0, 24]
    assert res["empty_groups"] == [0, 1]
    w = np.asarray(res["weights"], dtype=np.float64)
    np.testing.assert_array_equal(w[0], np.r_[1.0, np.zeros(24)])
    np.testing.assert_array_equal(w[1], np.r_[1.0, np.zeros(24)])

    # Also test when reference has 3 distinct groups on grid, but group 1 is completely masked out
    ref_distinct = np.tile(np.array([1.0, 5.0, 9.0]), (t_steps, 1))
    mask_g1_empty = np.ones((t_steps, n_nodes), dtype=bool)
    mask_g1_empty[:, 1] = False
    y_masked = y.copy()
    y_masked[:, 1] = np.nan
    res_g1_empty = fit_conditional_pool(
        x, b, y_masked, mask_g1_empty, anchors, ref_distinct, groups=3, relief=0.1, cap_mode="POOLED"
    )
    assert res_g1_empty["group_total_counts"] == [8, 8, 8]
    assert res_g1_empty["group_valid_counts"] == [8, 0, 8]
    assert res_g1_empty["empty_groups"] == [1]
    w_g1_empty = np.asarray(res_g1_empty["weights"], dtype=np.float64)
    np.testing.assert_array_equal(w_g1_empty[1], np.r_[1.0, np.zeros(24)])


def test_initialize_anchor_record_and_frozen_test_prediction_without_mask_or_cut_recompute():
    init_g3 = initialize_anchor_record(groups=3, relief=0.03, cap_mode="DAY")
    assert init_g3["status"] == "NO_PRIOR_OOF_ANCHOR"
    assert not init_g3["optimal"]
    assert init_g3["cuts"] == [0.0, 0.0]
    assert init_g3["cuts_source"] == "NO_PRIOR_OOF_ANCHOR_NO_HISTORICAL_CUTS"
    w_init = np.asarray(init_g3["weights"], dtype=np.float64)
    assert w_init.shape == (3, 25)
    np.testing.assert_array_equal(w_init[:, 0], [1.0, 1.0, 1.0])
    np.testing.assert_array_equal(w_init[:, 1:], 0.0)

    rng = np.random.default_rng(777)
    x_eval = rng.uniform(0.0, 25.0, (10, 4, 24))
    b_eval = rng.uniform(2.0, 14.0, (10, 4))
    ref_eval = rng.uniform(0.0, 30.0, (10, 4))

    # Under initialize_anchor_record, all ref >= 0 map to group 2 via cuts=[0.0, 0.0] and produce exact anchor b
    act_init, meta_init = predict_conditional_pool(x_eval, b_eval, ref_eval, init_g3)
    np.testing.assert_array_equal(act_init, b_eval)
    assert meta_init["group_cell_counts"] == [0, 0, 40]
    assert not meta_init["recomputed_cuts_on_prediction"]
    assert not meta_init["mask_gated_prediction"]

    # Verify frozen cuts from historical fit are never recomputed on test reference even when test reference distribution shifts
    custom_record = dict(init_g3)
    custom_record["cuts"] = [10.0, 20.0]
    w_custom = np.zeros((3, 25), dtype=np.float64)
    w_custom[0, 0] = 1.0  # group 0: anchor b
    w_custom[1, 1] = 1.0  # group 1: expert 0
    w_custom[2, 2] = 1.0  # group 2: expert 1
    custom_record["weights"] = w_custom.tolist()
    custom_record["relief"] = 1.0

    # All ref_eval = 15.0 -> with frozen cuts [10.0, 20.0], every cell must land in group 1!
    # If cuts were erroneously recomputed on ref_eval, cuts would be [15.0, 15.0] and cells would land in group 2.
    ref_shifted = np.full((10, 4), 15.0)
    act_shifted, meta_shifted = predict_conditional_pool(x_eval, b_eval, ref_shifted, custom_record)
    assert meta_shifted["cuts"] == [10.0, 20.0]
    assert meta_shifted["group_cell_counts"] == [0, 40, 0]
    np.testing.assert_allclose(act_shifted, x_eval[:, :, 0], rtol=0.0, atol=1e-14)


def test_hand_fraction_prediction_subgradient_and_floating_floor_guard():
    # Exact hand-fraction check of context assignment, static action, and subgradient:
    # 1 step, 3 cells with reference = [2, 4, 8] -> cuts = [10/3, 6.0] (linear quantile at 1/3, 2/3 for [2, 4, 8]:
    # index 0 + (2)*(1/3) = 2/3 -> 2 + (2/3)*(4-2) = 10/3; index 0 + (2)*(2/3) = 4/3 -> 4 + (1/3)*(8-4) = 16/3).
    ref = np.array([[2.0, 4.0, 8.0]])
    cuts = fit_context_cuts(ref, groups=3)
    assert cuts[0] == pytest.approx(float(Fraction(10, 3)), abs=1e-15)
    assert cuts[1] == pytest.approx(float(Fraction(16, 3)), abs=1e-15)
    ctx = context_ids(ref, cuts)
    np.testing.assert_array_equal(ctx, [[0, 1, 2]])

    # Exact fraction action check: b = [10, 10, 10], d = 1/2 -> floor = 5.
    # Expert 0 has X=0 -> delta_1 = -5; Expert 1 has X=22 -> delta_2 = +12; others X=10 -> delta = 0.
    b = np.array([[10.0, 10.0, 10.0]])
    x = np.full((1, 3, 24), 10.0)
    x[:, :, 0] = 0.0
    x[:, :, 1] = 22.0

    w = np.zeros((3, 25), dtype=np.float64)
    # Group 0: [1/8, 3/4, 1/8, 0...] -> r = 10 + (3/4)*(-5) + (1/8)*(12) = 31/4 = 7.75
    w[0, :3] = [float(Fraction(1, 8)), float(Fraction(3, 4)), float(Fraction(1, 8))]
    # Group 1: [0, 1, 0...] -> r = 10 + 1*(-5) = 5.0 (exact mathematical floor (1-d)*b)
    w[1, 1] = 1.0
    # Group 2: [1/4, 0, 3/4, 0...] -> r = 10 + (3/4)*(12) = 19.0
    w[2, :3] = [0.25, 0.0, 0.75]

    rec = dict(groups=3, relief=0.5, cap_mode="COST", cuts=cuts, weights=w.tolist())
    act, meta = predict_conditional_pool(x, b, ref, rec)
    expected = np.array([[float(Fraction(31, 4)), 5.0, 19.0]])
    np.testing.assert_allclose(act, expected, rtol=0.0, atol=1e-15)
    assert np.all(act >= (1.0 - 0.5) * b)
    assert meta["boundary_guard_count"] == 0


def test_nonoptimal_iteration_limit_and_bisection_repair_status(monkeypatch):
    rng = np.random.default_rng(55)
    t_steps, n_nodes = 20, 4
    anchors = np.arange(t_steps, dtype=np.int64)
    b = rng.uniform(5.0, 12.0, (t_steps, n_nodes))
    x = rng.uniform(0.0, 20.0, (t_steps, n_nodes, 24))
    y = rng.uniform(0.0, 18.0, (t_steps, n_nodes))
    ref = rng.uniform(1.0, 15.0, (t_steps, n_nodes))
    mask = np.ones((t_steps, n_nodes), dtype=bool)

    res_iter1 = fit_conditional_pool(
        x, b, y, mask, anchors, ref, groups=3, relief=0.1, cap_mode="POOLED", max_iter=1
    )
    assert not res_iter1["optimal"]
    assert res_iter1["status"] == "ITERATION_LIMIT"
    assert res_iter1["actual_feasible"]
    assert res_iter1["mean_uncovered_power"] <= res_iter1["uncovered_cap"]

    b_s = np.full((6, 2), 10.0)
    x_rep = np.full((6, 2, 24), 10.0)
    x_rep[:5, :, 0] = 0.0
    x_rep[5, :, 0] = 20.0
    y_rep = np.full((6, 2), 9.0)
    y_rep[5, :] = 12.0
    m_rep = np.ones((6, 2), dtype=bool)
    a_rep = np.arange(6, dtype=np.int64)
    ref_rep = np.ones((6, 2))

    from scipy.optimize import OptimizeResult

    def fake_linprog(c, A_ub=None, b_ub=None, A_eq=None, b_eq=None, bounds=None, method="highs", options=None):
        sol = np.zeros(len(c), dtype=np.float64)
        sol[1] = 0.3
        sol[2] = 0.7
        sol[-1] = 1.0
        return OptimizeResult(x=sol, fun=1.0, status=0, success=True, message="optimal")

    monkeypatch.setattr("windfarm_moe.conditional_convex_pool.linprog", fake_linprog)
    repaired = fit_conditional_pool(
        x_rep, b_s, y_rep, m_rep, a_rep, ref_rep, groups=1, relief=0.5, cap_mode="POOLED", max_iter=1
    )
    assert repaired["repaired_candidate_attempted"]
    assert repaired["actual_feasible"]
    assert repaired["mean_uncovered_power"] <= repaired["uncovered_cap"]
    assert not repaired["optimal"]
    assert repaired["status"] in ("ITERATION_LIMIT", "REPAIRED_FEASIBLE_UNKNOWN_OPTIMALITY")
    if repaired["repaired_to_anchor"]:
        assert repaired["status"] == "REPAIRED_FEASIBLE_UNKNOWN_OPTIMALITY"
    else:
        assert repaired["status"] == "ITERATION_LIMIT"

    delta_rep = signed_experts(x_rep, b_s, 0.5)
    cap_rep = float(np.maximum(y_rep - b_s, 0.0).mean())
    candidate_weights = [np.eye(25, dtype=np.float64)[idx] for idx in range(25)]
    candidate_weights.append(np.full(25, 1.0 / 25.0))
    feasible_costs = []
    for w_cand in candidate_weights:
        r_cand = b_s + np.tensordot(delta_rep, w_cand, axes=([2], [0]))
        u_cand = np.maximum(y_rep - r_cand, 0.0)
        if float(u_cand.mean()) <= cap_rep + 1e-12:
            feasible_costs.append(float((r_cand + 10.0 * u_cand).mean() / 6.0))
    best_init_cost = min(feasible_costs)
    assert repaired["objective"] <= best_init_cost + 1e-12



