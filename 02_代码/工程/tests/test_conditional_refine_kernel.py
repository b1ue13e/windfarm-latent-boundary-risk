import importlib.util
from repo_paths import Path, repository_root
import zipfile

import numpy as np
import pytest
from scipy.optimize import OptimizeResult

from windfarm_moe.bounded_relief import signed_experts
from windfarm_moe.conditional_convex_pool import (
    fit_conditional_pool,
    fit_context_cuts,
    initialize_anchor_record,
    predict_conditional_pool,
)
from tests.test_conditional_convex_pool import _solve_independent_full_lp_oracle


def _load_parent_conditional_pool_module():
    payload_zip = Path(repository_root()) / "experiments" / "conditional_pool_20261025" / "source_payload.zip"
    assert payload_zip.is_file(), f"Missing parent source payload: {payload_zip}"
    with zipfile.ZipFile(payload_zip, "r") as zf:
        source_bytes = zf.read("windfarm_moe/conditional_convex_pool.py")
    source_code = source_bytes.decode("utf-8")
    spec = importlib.util.spec_from_loader(
        "windfarm_moe._parent_conditional_convex_pool_9e9006bc3",
        loader=None,
        origin=f"{payload_zip}!windfarm_moe/conditional_convex_pool.py",
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "windfarm_moe"
    exec(compile(source_code, spec.origin, "exec"), module.__dict__)
    return module


@pytest.mark.parametrize("groups", [1, 3])
@pytest.mark.parametrize("cap_mode", ["COST", "POOLED", "DAY"])
@pytest.mark.parametrize("relief", [0.0, 0.03, 0.1, 1.0])
def test_default_branch_bitwise_matches_parent_source_payload(groups, cap_mode, relief):
    parent_mod = _load_parent_conditional_pool_module()
    rng = np.random.default_rng(20261025 + 31 * groups + int(100 * relief) + len(cap_mode))
    t_steps, n_nodes = 18, 4
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

    old_res = parent_mod.fit_conditional_pool(
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
    new_res = fit_conditional_pool(
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

    assert new_res["time_budget_ceiling"] == 8.0
    assert new_res["time_limit"] == 8.0
    assert new_res["warm_start_provided"] is False
    assert new_res["warm_start_accepted"] is False
    assert new_res["warm_start_objective"] is None

    for key in (
        "status",
        "optimal",
        "groups",
        "relief",
        "cap_mode",
        "cuts",
        "cuts_source",
        "weights",
        "raw_weights",
        "canonical_initial",
        "objective",
        "lower_bound",
        "gap",
        "mean_uncovered_power",
        "uncovered_cap",
        "day_caps",
        "day_uncovered_power",
        "day_ids",
        "day_valid_counts",
        "max_cap_violation",
        "anchor_objective",
        "anchor_mean_uncovered_power",
        "valid_fit_cells",
        "total_cells",
        "fit_issue_count",
        "group_total_counts",
        "group_valid_counts",
        "empty_groups",
        "actual_feasible",
        "raw_actual_feasible",
        "repaired_to_anchor",
        "repair_alpha",
        "repaired_candidate_attempted",
        "boundary_guard_count",
        "max_boundary_violation",
        "iterations",
        "numerical_tolerance",
        "mean_delta_by_group",
    ):
        assert new_res[key] == old_res[key], f"Mismatch on {key}"

    old_act, old_meta = parent_mod.predict_conditional_pool(x, b, reference, old_res)
    new_act, new_meta = predict_conditional_pool(x, b, reference, new_res)
    np.testing.assert_array_equal(new_act, old_act)
    assert new_meta == old_meta


def test_time_budget_ceiling_clamping_and_validation():
    rng = np.random.default_rng(101)
    t_steps, n_nodes = 12, 3
    anchors = np.arange(t_steps, dtype=np.int64)
    b = rng.uniform(5.0, 10.0, (t_steps, n_nodes))
    x = rng.uniform(0.0, 16.0, (t_steps, n_nodes, 24))
    y = rng.uniform(0.0, 14.0, (t_steps, n_nodes))
    ref = rng.uniform(1.0, 12.0, (t_steps, n_nodes))
    mask = np.ones((t_steps, n_nodes), dtype=bool)

    res_default = fit_conditional_pool(x, b, y, mask, anchors, ref, time_limit=100.0)
    assert res_default["time_budget_ceiling"] == 8.0
    assert res_default["time_limit"] == 8.0

    res_60 = fit_conditional_pool(
        x, b, y, mask, anchors, ref, time_limit=100.0, time_budget_ceiling=60.0
    )
    assert res_60["time_budget_ceiling"] == 60.0
    assert res_60["time_limit"] == 60.0

    res_sub60 = fit_conditional_pool(
        x, b, y, mask, anchors, ref, time_limit=25.0, time_budget_ceiling=60.0
    )
    assert res_sub60["time_budget_ceiling"] == 60.0
    assert res_sub60["time_limit"] == 25.0

    init_rec = initialize_anchor_record(groups=3, relief=0.1, cap_mode="POOLED")
    assert init_rec["time_budget_ceiling"] == 8.0
    assert init_rec["warm_start_provided"] is False
    assert init_rec["warm_start_accepted"] is False
    assert init_rec["warm_start_objective"] is None

    for bad_ceiling in (True, False, 0.0, -8.0, 15.0, 120.0, np.nan, np.inf, "60.0", None, [60.0]):
        with pytest.raises(ValueError, match="time_budget_ceiling"):
            fit_conditional_pool(
                x, b, y, mask, anchors, ref, time_limit=8.0, time_budget_ceiling=bad_ceiling  # type: ignore[arg-type]
            )


def test_warm_start_validation_and_strict_infeasible_rejection():
    t_steps, n_nodes = 12, 3
    anchors = np.r_[np.arange(6, dtype=np.int64), 144 + np.arange(6, dtype=np.int64)]
    b = np.full((t_steps, n_nodes), 10.0)
    ref = np.tile(np.array([1.0, 5.0, 9.0]), (t_steps, 1))
    x = np.full((t_steps, n_nodes, 24), 10.0)
    x[:, :, 0] = 0.0   # delta_1 = -d*b (reduces reserve, increases uncovered shortfall)
    x[:, :, 1] = 20.0  # delta_2 = +10.0 (increases reserve)
    y = np.full((t_steps, n_nodes), 10.0)
    mask = np.ones((t_steps, n_nodes), dtype=bool)

    # Invalid shapes / non-simplex warm starts reject
    for bad_w in (
        np.ones((2, 25)) / 25.0,
        np.ones((3, 24)) / 24.0,
        np.zeros((3, 25)),
        -0.1 * np.ones((3, 25)),
        np.full((3, 25), np.nan),
    ):
        with pytest.raises(ValueError, match="simplex weight matrix"):
            fit_conditional_pool(
                x, b, y, mask, anchors, ref, groups=3, relief=0.5, cap_mode="COST", warm_start_weights=bad_w
            )

    # Empty valid group must equal exact anchor e0
    mask_empty_g1 = mask.copy()
    mask_empty_g1[:, 1] = False
    y_empty_g1 = y.copy()
    y_empty_g1[:, 1] = np.nan
    w_bad_empty = np.zeros((3, 25), dtype=np.float64)
    w_bad_empty[:, 0] = 1.0
    w_bad_empty[1, 0] = 0.0
    w_bad_empty[1, 2] = 1.0
    with pytest.raises(ValueError, match="Empty valid group"):
        fit_conditional_pool(
            x,
            b,
            y_empty_g1,
            mask_empty_g1,
            anchors,
            ref,
            groups=3,
            relief=0.5,
            cap_mode="COST",
            warm_start_weights=w_bad_empty,
        )

    # Cap-infeasible warm start (even tiny violation) must reject strictly in POOLED and DAY modes
    # Here y == b == 10, so anchor uncovered cap is 0.0. Putting tiny weight 1e-11 on expert 0 (delta = -5)
    # lowers action below 10 and creates positive uncovered shortfall > 0.0.
    w_infeasible = np.zeros((3, 25), dtype=np.float64)
    w_infeasible[:, 0] = 1.0
    w_infeasible[0, 0] = 1.0 - 1e-11
    w_infeasible[0, 1] = 1e-11

    for mode in ("POOLED", "DAY"):
        with pytest.raises(ValueError, match="warm_start_weights violated historical cap feasibility"):
            fit_conditional_pool(
                x,
                b,
                y,
                mask,
                anchors,
                ref,
                groups=3,
                relief=0.5,
                cap_mode=mode,
                warm_start_weights=w_infeasible,
            )


def test_feasible_better_warm_start_retained_under_max_iter_1_and_adversarial_master(monkeypatch):
    rng = np.random.default_rng(2026)
    t_steps, n_nodes = 18, 4
    anchors = np.concatenate([
        np.arange(6, dtype=np.int64),
        144 + np.arange(6, dtype=np.int64),
        288 + np.arange(6, dtype=np.int64),
    ])
    b = rng.uniform(5.0, 12.0, (t_steps, n_nodes))
    x = rng.uniform(0.0, 20.0, (t_steps, n_nodes, 24))
    y = rng.uniform(0.0, 16.0, (t_steps, n_nodes))
    ref = rng.uniform(1.0, 15.0, (t_steps, n_nodes))
    mask = np.ones((t_steps, n_nodes), dtype=bool)

    oracle = _solve_independent_full_lp_oracle(
        x, b, y, mask, anchors, ref, groups=3, relief=0.1, cap_mode="POOLED"
    )
    full_fit = fit_conditional_pool(
        x, b, y, mask, anchors, ref, groups=3, relief=0.1, cap_mode="POOLED", time_limit=8.0, max_iter=1200
    )
    assert full_fit["actual_feasible"]
    assert full_fit["objective"] == pytest.approx(oracle["objective"], abs=2e-5)
    w_warm = np.asarray(full_fit["weights"], dtype=np.float64)
    assert full_fit["objective"] < full_fit["anchor_objective"] - 1e-3

    # Force master LP at iteration 1 to propose a suboptimal/infeasible candidate so only warm_start can preserve the optimum
    captured_A_ub = []

    def fake_linprog(c, A_ub=None, b_ub=None, A_eq=None, b_eq=None, bounds=None, method="highs", options=None):
        captured_A_ub.append((np.asarray(A_ub, dtype=np.float64), np.asarray(b_ub, dtype=np.float64), dict(options or {})))
        sol = np.zeros(len(c), dtype=np.float64)
        for grp in range(3):
            sol[grp * 25 + 1] = 1.0  # pure expert 0
        sol[-1] = 0.5 * full_fit["objective"]
        return OptimizeResult(x=sol, fun=0.5 * full_fit["objective"], status=0, success=True, message="optimal")

    monkeypatch.setattr("windfarm_moe.conditional_convex_pool.linprog", fake_linprog)
    refined = fit_conditional_pool(
        x,
        b,
        y,
        mask,
        anchors,
        ref,
        groups=3,
        relief=0.1,
        cap_mode="POOLED",
        time_limit=60.0,
        time_budget_ceiling=60.0,
        max_iter=1,
        warm_start_weights=w_warm,
    )
    assert len(captured_A_ub) == 1
    # Initial planes with warm start: 3 cost planes (warm, anchor, uniform) + 3 pooled cap planes = 6 rows
    assert captured_A_ub[0][0].shape[0] == 6
    assert captured_A_ub[0][2]["time_limit"] <= 60.0
    assert captured_A_ub[0][2]["time_limit"] > 8.0

    assert refined["warm_start_provided"] is True
    assert refined["warm_start_accepted"] is True
    assert refined["warm_start_objective"] == pytest.approx(full_fit["objective"], abs=1e-15)
    assert refined["actual_feasible"] is True
    assert refined["objective"] <= refined["warm_start_objective"]
    assert refined["objective"] == pytest.approx(full_fit["objective"], abs=1e-15)
    np.testing.assert_allclose(np.asarray(refined["weights"]), w_warm, rtol=0.0, atol=1e-15)


def test_independent_full_lp_objective_and_caps_unchanged_with_refinement_options():
    rng = np.random.default_rng(404)
    t_steps, n_nodes = 18, 3
    anchors = np.concatenate([
        np.arange(6, dtype=np.int64),
        144 + np.arange(6, dtype=np.int64),
        288 + np.arange(6, dtype=np.int64),
    ])
    b = rng.uniform(4.0, 11.0, (t_steps, n_nodes))
    x = rng.uniform(0.0, 18.0, (t_steps, n_nodes, 24))
    y = rng.uniform(0.0, 15.0, (t_steps, n_nodes))
    ref = rng.uniform(1.0, 14.0, (t_steps, n_nodes))
    mask = np.ones((t_steps, n_nodes), dtype=bool)

    for cap_mode in ("COST", "POOLED", "DAY"):
        oracle = _solve_independent_full_lp_oracle(
            x, b, y, mask, anchors, ref, groups=3, relief=0.1, cap_mode=cap_mode
        )
        stage1 = fit_conditional_pool(
            x, b, y, mask, anchors, ref, groups=3, relief=0.1, cap_mode=cap_mode, max_iter=3
        )
        assert stage1["actual_feasible"]
        stage2 = fit_conditional_pool(
            x,
            b,
            y,
            mask,
            anchors,
            ref,
            groups=3,
            relief=0.1,
            cap_mode=cap_mode,
            time_limit=60.0,
            time_budget_ceiling=60.0,
            max_iter=1200,
            warm_start_weights=stage1["weights"],
        )
        assert stage2["actual_feasible"]
        assert stage2["warm_start_accepted"] is True
        assert stage2["objective"] <= stage1["objective"] + 1e-15
        assert stage2["objective"] == pytest.approx(oracle["objective"], abs=3e-5)
        assert stage2["cuts"] == fit_context_cuts(ref, groups=3)
        if cap_mode == "POOLED":
            assert stage2["uncovered_cap"] == pytest.approx(oracle["pooled_cap"], abs=1e-12)
            assert stage2["mean_uncovered_power"] <= stage2["uncovered_cap"]
        elif cap_mode == "DAY":
            assert stage2["day_caps"] == pytest.approx(oracle["day_caps"], abs=1e-12)
            for u_d, c_d in zip(stage2["day_uncovered_power"], stage2["day_caps"]):
                assert u_d <= c_d
