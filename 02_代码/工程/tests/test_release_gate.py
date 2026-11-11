from fractions import Fraction
from repo_paths import Path, repository_root
import numpy as np
import pytest
from scipy.optimize import linprog
from sklearn.tree import DecisionTreeRegressor

from windfarm_moe.release_gate import (
    BISECTION_STEPS,
    CALIBRATION_QUANTILE_GRID,
    CONSTANT_ALPHA_GRID,
    GATE_DEPTH_GRID,
    GATE_FEATURE_SETS,
    GATE_LAMBDA_U_GRID,
    MIN_SAMPLES_LEAF,
    MIN_SAMPLES_SPLIT,
    RELEASE_GATE_SCHEMA,
    ReleaseGateRecipe,
    actual_cell_loss,
    build_recipes,
    build_release_gate_recipes,
    coerce_recipe,
    compute_regret_label,
    extract_feature_matrix,
    fit_rule,
    load_release_gate_model,
    make_decision_tree,
    predict_rule,
    save_release_gate_model,
    solve_leaf_alpha,
)


def _solve_lp_epigraph_oracle(safe: np.ndarray, cost: np.ndarray, shortfall: np.ndarray, lambda_u: float = 0.0) -> dict:
    """Independent full LP epigraph oracle: 1 variable alpha in [0, 1] plus N row uncovered variables u_i >= 0.

    Minimizes (1 / N) * sum_i ( (safe_i + alpha * (cost_i - safe_i)) / 6 + (10 + 10 * lambda_u) * u_i )
    subject to:
      u_i >= (shortfall_i - safe_i - alpha * (cost_i - safe_i)) / 6
      u_i >= 0
      (1 / N) * sum_i u_i <= (1 / N) * sum_i max(shortfall_i - safe_i, 0) / 6
      0 <= alpha <= 1
    """
    b = np.asarray(safe, dtype=np.float64).reshape(-1)
    c = np.asarray(cost, dtype=np.float64).reshape(-1)
    y = np.asarray(shortfall, dtype=np.float64).reshape(-1)
    d = c - b
    n = b.size
    rho_eff = 10.0 + 10.0 * float(lambda_u)
    u_safe = np.maximum(y - b, 0.0) / 6.0
    cap_u_sum = float(np.sum(u_safe))

    # Variables: x[0] = alpha, x[1..n] = u_1..u_n (in kWh)
    obj = np.zeros(1 + n, dtype=np.float64)
    obj[0] = float(np.sum(d) / (6.0 * n))
    obj[1:] = rho_eff / float(n)
    const_term = float(np.sum(b) / (6.0 * n))

    # Inequality constraints:
    # 1..n: - (d_i / 6) * alpha - u_i <= - (y_i - b_i) / 6
    # n+1: sum_i u_i <= cap_u_sum
    A_ub = np.zeros((n + 1, 1 + n), dtype=np.float64)
    b_ub = np.zeros(n + 1, dtype=np.float64)
    A_ub[:n, 0] = -d / 6.0
    A_ub[np.arange(n), 1 + np.arange(n)] = -1.0
    b_ub[:n] = -(y - b) / 6.0
    A_ub[n, 1:] = 1.0
    b_ub[n] = cap_u_sum

    bounds = [(0.0, 1.0)] + [(0.0, None)] * n
    res = linprog(obj, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
    assert res.success, f"LP oracle failed: {res.message}"
    alpha_lp = float(res.x[0])
    r_lp = b + alpha_lp * d
    u_lp = np.maximum(y - r_lp, 0.0) / 6.0
    pen_lp = float(np.mean(r_lp / 6.0 + rho_eff * u_lp))
    return dict(
        alpha=alpha_lp,
        lp_objective_kwh=float(res.fun + const_term),
        actual_penalized_kwh=pen_lp,
        actual_U_kwh=float(np.mean(u_lp)),
        safe_U_kwh=float(np.mean(u_safe)),
    )


def _make_synthetic_release_bank(t_steps: int = 24, n_nodes: int = 64, seed: int = 201, arm: str = "P") -> dict:
    rng = np.random.default_rng(seed)
    anchors = np.arange(28000, 28000 + t_steps, dtype=np.int64)
    reference = rng.uniform(2.0, 8.0, size=(t_steps, n_nodes))
    safe = reference + rng.uniform(1.0, 5.0, size=(t_steps, n_nodes))
    # Mix of cost < safe, cost == safe, and cost > safe
    delta = rng.uniform(-3.0, 2.5, size=(t_steps, n_nodes))
    delta[:, 0] = 0.0
    cost = np.maximum(safe + delta, 0.2)
    width = rng.uniform(0.5, 4.0, size=(t_steps, n_nodes))
    cur = np.stack([reference, safe, cost, cost - safe, width], axis=-1)
    fb_row = rng.normal(0.0, 0.2, size=(t_steps, 6))
    fb_row[:, 5] = np.linspace(0.1, 1.0, t_steps)
    fb = np.broadcast_to(fb_row[:, None, :], (t_steps, n_nodes, 6)).copy()

    # Shortfall depends on features so trees make nontrivial splits
    shortfall = np.maximum(safe - 1.5 + 2.5 * (cur[:, :, 3] > -0.5) + rng.uniform(-1.0, 3.0, size=(t_steps, n_nodes)), 0.0)
    mask = np.ones((t_steps, n_nodes), dtype=bool)
    mask[min(1, t_steps - 1), min(3, n_nodes - 1)] = False
    mask[min(5, t_steps - 1), min(7, n_nodes - 1)] = False
    shortfall[~mask] = np.nan

    return dict(
        anchors=anchors,
        shortfall=shortfall,
        mask=mask,
        reference=reference,
        safe=safe,
        cost=cost,
        current_features=cur,
        feedback_features=fb,
        metadata=dict(schema="prospective-release-bank-v1", seed=seed, arm=arm),
    )


def test_exact_fraction_handmix_actual_c_differs_from_weighted_expert_loss():
    """Verify via exact Fraction arithmetic that actual C(r(alpha)) != (1-alpha)*C(safe) + alpha*C(cost)."""
    # Cell 0: safe=10, cost=4, S=6 -> safe covers S (U=0), cost has shortfall 2 (U=2/6); at alpha=1/2, r=7 covers S (U=0)!
    # Cell 1: safe=4, cost=10, S=8 -> safe has shortfall 4, cost covers S; at alpha=1/2, r=7 has shortfall 1.
    safe_f = [Fraction(10, 1), Fraction(4, 1)]
    cost_f = [Fraction(4, 1), Fraction(10, 1)]
    s_f = [Fraction(6, 1), Fraction(8, 1)]
    alpha_f = Fraction(1, 2)

    def cell_c_u(r: Fraction, y: Fraction) -> tuple[Fraction, Fraction]:
        u = max(y - r, Fraction(0, 1)) / Fraction(6, 1)
        c = r / Fraction(6, 1) + Fraction(10, 1) * u
        return c, u

    c_safe_list, u_safe_list = zip(*(cell_c_u(b, y) for b, y in zip(safe_f, s_f)))
    c_cost_list, u_cost_list = zip(*(cell_c_u(c, y) for c, y in zip(cost_f, s_f)))
    r_mix_list = [b + alpha_f * (c - b) for b, c in zip(safe_f, cost_f)]
    c_mix_list, u_mix_list = zip(*(cell_c_u(r, y) for r, y in zip(r_mix_list, s_f)))

    mean_c_safe = sum(c_safe_list) / 2
    mean_c_cost = sum(c_cost_list) / 2
    weighted_expert_c = (1 - alpha_f) * mean_c_safe + alpha_f * mean_c_cost
    actual_mixture_c = sum(c_mix_list) / 2
    actual_mixture_u = sum(u_mix_list) / 2
    weighted_expert_u = (1 - alpha_f) * (sum(u_safe_list) / 2) + alpha_f * (sum(u_cost_list) / 2)

    # Exact Fraction values:
    # Cell 0: c_safe = 10/6, c_cost = 24/6, c_mix(r=7) = 7/6
    # Cell 1: c_safe = 44/6, c_cost = 10/6, c_mix(r=7) = 17/6
    assert mean_c_safe == Fraction(27, 6)
    assert mean_c_cost == Fraction(17, 6)
    assert weighted_expert_c == Fraction(22, 6)
    assert actual_mixture_c == Fraction(12, 6)
    assert actual_mixture_c < weighted_expert_c
    assert actual_mixture_u == Fraction(1, 12) < weighted_expert_u == Fraction(3, 12)

    # Check our numpy implementation matches the exact Fraction values
    c_np, u_np, _ = actual_cell_loss(np.array([7.0, 7.0]), np.array([6.0, 8.0]))
    assert np.isclose(np.mean(c_np), float(actual_mixture_c), atol=1e-15, rtol=0.0)
    assert np.isclose(np.mean(u_np), float(actual_mixture_u), atol=1e-15, rtol=0.0)

    # And solve_leaf_alpha finds the exact kink alpha = 2/3 where both cells are covered (r0=6, r1=8)
    sol = solve_leaf_alpha(np.array([10.0, 4.0]), np.array([4.0, 10.0]), np.array([6.0, 8.0]), lambda_u=0.0)
    assert np.isclose(sol["alpha"], float(Fraction(2, 3)), atol=1e-14, rtol=0.0)
    assert np.isclose(sol["actual_C_kwh"], float(Fraction(7, 6)), atol=1e-14, rtol=0.0)
    assert sol["actual_U_kwh"] == 0.0


@pytest.mark.parametrize("case_id", range(8))
@pytest.mark.parametrize("lambda_u", [0.0, 1.0, 10.0])
def test_solve_leaf_alpha_matches_independent_lp_epigraph_oracle(case_id: int, lambda_u: float):
    """Compare solve_leaf_alpha against independent SciPy HiGHS full LP epigraph oracle across interior, kink, and boundary cases."""
    rng = np.random.default_rng(1000 + case_id)
    if case_id == 0:
        # Interior kink optimum, cap non-binding
        safe = np.array([10.0, 4.0, 8.0, 5.0])
        cost = np.array([4.0, 10.0, 5.0, 9.0])
        shortfall = np.array([6.0, 8.0, 6.0, 7.0])
    elif case_id == 1:
        # Cap strictly binding in (0, 1): cost reduces reserve and creates new shortfall, balanced by another cell
        safe = np.array([10.0, 10.0, 4.0, 10.0])
        cost = np.array([2.0, 2.0, 10.0, 4.0])
        shortfall = np.array([6.0, 5.0, 8.0, 2.0])
    elif case_id == 2:
        # Boundary alpha = 0 optimal (cost much worse than safe everywhere)
        safe = np.array([6.0, 7.0, 8.0])
        cost = np.array([1.0, 2.0, 1.5])
        shortfall = np.array([6.0, 7.0, 8.0])
    elif case_id == 3:
        # Boundary alpha = 1 optimal (cost strictly cheaper and still covers shortfall everywhere)
        safe = np.array([12.0, 14.0, 10.0, 9.0])
        cost = np.array([6.0, 7.0, 5.0, 4.0])
        shortfall = np.array([5.0, 6.0, 4.0, 3.0])
    elif case_id == 4:
        # Degenerate y == b with negative d, positive d, and zero d
        safe = np.array([6.0, 6.0, 6.0, 8.0, 5.0])
        cost = np.array([3.0, 9.0, 6.0, 2.0, 8.0])
        shortfall = np.array([6.0, 6.0, 6.0, 4.0, 7.0])
    elif case_id == 5:
        # Identical kinks from multiple cells
        safe = np.array([10.0, 12.0, 4.0, 2.0])
        cost = np.array([4.0, 6.0, 10.0, 8.0])
        shortfall = np.array([7.0, 9.0, 7.0, 5.0])
    else:
        # Random mixed sign d with 50 cells
        safe = rng.uniform(2.0, 14.0, size=50)
        cost = np.maximum(safe + rng.uniform(-5.0, 4.0, size=50), 0.1)
        cost[::7] = safe[::7]  # exact zero delta cells
        shortfall = rng.uniform(0.0, 12.0, size=50)
        shortfall[1::9] = safe[1::9]  # exact y == b kink cells

    sol = solve_leaf_alpha(safe, cost, shortfall, lambda_u=lambda_u)
    oracle = _solve_lp_epigraph_oracle(safe, cost, shortfall, lambda_u=lambda_u)

    # Strict feasibility without tolerance relaxation
    assert 0.0 <= sol["alpha"] <= sol["alpha_max"] <= 1.0
    assert sol["actual_U_kwh"] <= sol["safe_U_kwh"]
    assert np.isclose(sol["penalized_objective_kwh"], oracle["actual_penalized_kwh"], atol=1e-9, rtol=1e-9)
    assert np.isclose(sol["alpha"], oracle["alpha"], atol=1e-7, rtol=1e-7)
    assert sol["subgradient_lower_bound_kwh"] <= sol["penalized_objective_kwh"] + 1e-12


def test_regret_label_and_5d_11d_feature_schemas():
    """Verify exact regret label formula and 5D/11D feature extraction without touching shortfall/mask."""
    safe = np.array([8.0, 4.0])
    cost = np.array([5.0, 7.0])
    y = np.array([6.0, 6.0])
    # Cell 0: safe=8 (U=0, C=8/6), cost=5 (U=1/6, C=15/6) -> C_diff = 7/6, 10*U_diff = 10/6
    # Cell 1: safe=4 (U=2/6, C=24/6), cost=7 (U=0, C=7/6) -> C_diff = -17/6, 10*U_diff = -20/6
    lbl0 = compute_regret_label(safe, cost, y, lambda_u=0.0)
    lbl2 = compute_regret_label(safe, cost, y, lambda_u=2.0)
    assert np.allclose(lbl0, [7.0 / 6.0, -17.0 / 6.0], atol=1e-15, rtol=0.0)
    assert np.allclose(lbl2, [(7.0 + 20.0) / 6.0, (-17.0 - 40.0) / 6.0], atol=1e-15, rtol=0.0)

    bank = _make_synthetic_release_bank(t_steps=10, n_nodes=4)
    # Poison shortfall and mask to prove extract_feature_matrix does not read them
    bank_no_target = dict(bank, shortfall=None, mask=None)
    f_cur = extract_feature_matrix(bank_no_target, "current")
    f_fb = extract_feature_matrix(bank_no_target, "feedback")
    assert f_cur.shape == (10, 4, 5)
    assert f_fb.shape == (10, 4, 11)
    assert np.array_equal(f_fb[:, :, :5], f_cur)
    assert np.array_equal(f_fb[:, :, 5:], bank["feedback_features"])


def test_deterministic_24_recipes_and_explicit_tree_criterion():
    """Verify all 24 recipes, conditional calibration feature parity, and exact DecisionTreeRegressor params."""
    recipes = build_release_gate_recipes()
    assert build_recipes() == recipes
    assert len(recipes) == 24
    assert [r["id"] for r in recipes] == list(range(24))
    assert recipes[0]["kind"] == "SAFE" and recipes[0]["alpha"] == 0.0
    assert recipes[1]["kind"] == "COST" and recipes[1]["alpha"] == 1.0
    assert [recipes[i]["alpha"] for i in range(2, 7)] == list(CONSTANT_ALPHA_GRID)
    assert recipes[7]["kind"] == "GLOBAL_FIT"

    gate_ids = list(range(8, 20))
    expected_gates = [
        (fset, depth, lam)
        for fset in GATE_FEATURE_SETS
        for depth in GATE_DEPTH_GRID
        for lam in GATE_LAMBDA_U_GRID
    ]
    for gid, (fset, depth, lam) in zip(gate_ids, expected_gates):
        r = recipes[gid]
        assert r["kind"] == "GATE"
        assert (r["feature_set"], r["max_depth"], r["lambda_u"]) == (fset, depth, lam)

    # Strongest gate (IDs 17..19) uses feature_set='feedback' and max_depth=2; calibration (20..23) matches exactly
    for cid, q in zip(range(20, 24), CALIBRATION_QUANTILE_GRID):
        r = recipes[cid]
        assert r["kind"] == "CONDITIONAL_CALIBRATION"
        assert r["feature_set"] == "feedback"
        assert r["max_depth"] == 2
        assert r["q"] == q
        assert coerce_recipe(cid) == r
        assert coerce_recipe(ReleaseGateRecipe(**r)) == r

    tree = make_decision_tree(max_depth=2, seed=203)
    params = tree.get_params(deep=False)
    assert params["criterion"] == "squared_error"
    assert params["splitter"] == "best"
    assert params["max_depth"] == 2
    assert params["min_samples_leaf"] == MIN_SAMPLES_LEAF == 512
    assert params["min_samples_split"] == MIN_SAMPLES_SPLIT == 1024
    assert params["random_state"] == 203


def test_causality_guard_and_nan_mask_enforcement():
    """Verify fit_rule rejects unmatured anchors (anchor + 7 >= episode_start) and NaN violations."""
    bank = _make_synthetic_release_bank(t_steps=20, n_nodes=32)
    # Anchors are 28000..28019. If episode_start = 28015, max legal anchor is 28007 (28007 + 7 = 28014 < 28015).
    with pytest.raises(ValueError, match="unmatured anchor"):
        fit_rule(bank, 7, seed=201, fit_selector=slice(0, 9), episode_start=28015)

    # Legal selector slice(0, 8) -> anchors 28000..28007 all satisfy +7 < 28015
    model, rcpt = fit_rule(bank, 7, seed=201, fit_selector=slice(0, 8), episode_start=28015)
    assert model["status"] == "FITTED_OK"
    assert rcpt["selected_issue_count"] == 8

    # Masked finite values are legitimate source bytes, not training labels.
    bad_bank = dict(bank, shortfall=bank["shortfall"].copy())
    bad_bank["shortfall"][~bad_bank["mask"]] = 0.0
    other, _ = fit_rule(bad_bank, 7, seed=201, fit_selector=slice(0, 8), episode_start=28015)
    assert other["alpha"] == model["alpha"]


def test_insufficient_rows_fallback_all_24_predict_without_quality_screen():
    """When valid history < 512 (or empty), all 24 recipes still fit/predict without quality filtering."""
    bank = _make_synthetic_release_bank(t_steps=10, n_nodes=16)  # 10 * 16 = 160 < 512 cells
    ep_start = int(bank["anchors"][-1]) + 10
    for rid in range(24):
        model, rcpt = fit_rule(bank, rid, seed=201, fit_selector=slice(0, 5), episode_start=ep_start)
        act, meta = predict_rule(model, bank, selector=slice(5, 10))
        assert act.shape == (5, 16)
        assert np.isfinite(act).all() and np.all(act >= 0.0)
        if rid in range(0, 7):
            assert model["status"] == "FIXED_CONSTANT_OK"
        elif rid == 7:
            assert model["status"] == "FITTED_OK"
        else:
            assert model["status"] == "UNTRAINED_ANCHOR"
            assert model["fallback_to_safe"] is True
            assert rcpt["status"] == "UNTRAINED_ANCHOR"
            assert np.array_equal(act, bank["safe"][5:10])

    # Empty history (0 selected rows) falls back for GLOBAL_FIT as well
    m_empty, r_empty = fit_rule(bank, 7, seed=201, fit_selector=slice(0, 0), episode_start=ep_start)
    assert m_empty["status"] == "UNTRAINED_ANCHOR" and r_empty["fallback_to_safe"] is True
    act_e, _ = predict_rule(m_empty, bank)
    assert np.array_equal(act_e, bank["safe"])


def test_full_support_fit_joblib_serialization_and_adversarial_future_invariance(tmp_path: Path):
    """Verify full >=512-per-leaf fit, bitwise joblib roundtrip, calibration quantiles, and future-target invariance."""
    bank = _make_synthetic_release_bank(t_steps=38, n_nodes=64, seed=202)  # 20 * 64 = 1280 valid fit cells (>= 2 * 512)
    fit_sel = slice(0, 20)
    pred_sel = slice(28, 38)
    ep_start = int(bank["anchors"][28])  # 28028 > max fit anchor 28019 + 7 = 28026

    for rid in (0, 1, 4, 7, 13, 19, 20, 22):
        model, rcpt = fit_rule(bank, rid, seed=202, fit_selector=fit_sel, episode_start=ep_start)
        assert rcpt["schema"] == RELEASE_GATE_SCHEMA
        if rid >= 8:
            assert model["status"] == "FITTED_OK"
            for lstat in model["leaf_stats"].values():
                assert lstat["n_cells"] >= MIN_SAMPLES_LEAF
                if rid < 20:
                    assert lstat["actual_U_kwh"] <= lstat["safe_U_kwh"]

        act1, meta1 = predict_rule(model, bank, selector=pred_sel)
        pkl_path = tmp_path / f"model_{rid}.joblib"
        save_release_gate_model(pkl_path, model)
        loaded = load_release_gate_model(pkl_path)
        act2, meta2 = predict_rule(loaded, bank, selector=pred_sel)
        assert np.array_equal(act1, act2)
        assert meta1["leaf_support"] == meta2["leaf_support"]

        # Adversarial mutation of shortfall and mask on prediction slice AND training slice during predict
        adv_bank = dict(
            bank,
            shortfall=np.full_like(bank["shortfall"], np.nan),
            mask=np.zeros_like(bank["mask"], dtype=bool),
        )
        act_adv, _ = predict_rule(loaded, adv_bank, selector=pred_sel)
        assert np.array_equal(act1, act_adv)

        # Adversarial mutation of future rows (20..29) before fitting must have zero effect on fit or prediction
        bank_future_changed = dict(bank, shortfall=bank["shortfall"].copy(), mask=bank["mask"].copy())
        bank_future_changed["shortfall"][20:] = 9999.0
        bank_future_changed["mask"][20:] = True
        model_fc, rcpt_fc = fit_rule(bank_future_changed, rid, seed=202, fit_selector=fit_sel, episode_start=ep_start)
        act_fc, _ = predict_rule(model_fc, bank, selector=pred_sel)
        assert rcpt["valid_row_sha256"] == rcpt_fc["valid_row_sha256"]
        assert np.array_equal(act1, act_fc)

    # Check calibration quantile monotonic shift ordering on identical feedback features + depth 2
    cal_actions = []
    for rid in range(20, 24):
        m_cal, _ = fit_rule(bank, rid, seed=202, fit_selector=fit_sel, episode_start=ep_start)
        a_cal, _ = predict_rule(m_cal, bank, selector=pred_sel)
        cal_actions.append(a_cal)
    for lo_act, hi_act in zip(cal_actions[:-1], cal_actions[1:]):
        assert np.all(hi_act >= lo_act - 1e-12)
