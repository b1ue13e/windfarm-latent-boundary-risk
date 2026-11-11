from dataclasses import asdict
from fractions import Fraction
import importlib.util
from repo_paths import Path, repository_root
import sys
import zipfile

import numpy as np
import pytest

from windfarm_moe.actual_mixture_update import (
    MixtureConfig,
    actual_gradient,
    project_simplex,
    run_mixture,
)
from windfarm_moe.bounded_relief import (
    fit_signed,
    run_signed,
    signed_action,
    signed_experts,
)


def _load_frozen_parent_modules(tmp_path: Path):
    zip_path = (
        Path(__file__).resolve().parent.parent
        / "experiments"
        / "bounded_relief_20261024"
        / "source_payload.zip"
    )
    assert zip_path.is_file(), f"Missing frozen parent source zip: {zip_path}"
    extract_root = tmp_path / "frozen_parent"
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in (
            "windfarm_moe/__init__.py",
            "windfarm_moe/actual_mixture_update.py",
            "windfarm_moe/static_convex_bundle.py",
            "windfarm_moe/bounded_relief.py",
        ):
            zf.extract(member, extract_root)

    pkg_dir = extract_root / "windfarm_moe"
    pkg_name = f"_frozen_parent_pkg_{id(tmp_path)}"
    pkg_spec = importlib.util.spec_from_file_location(
        pkg_name,
        pkg_dir / "__init__.py",
        submodule_search_locations=[str(pkg_dir)],
    )
    pkg_mod = importlib.util.module_from_spec(pkg_spec)
    sys.modules[pkg_name] = pkg_mod
    pkg_spec.loader.exec_module(pkg_mod)

    loaded = {}
    for mod_short in ("actual_mixture_update", "static_convex_bundle", "bounded_relief"):
        full_name = f"{pkg_name}.{mod_short}"
        spec = importlib.util.spec_from_file_location(full_name, pkg_dir / f"{mod_short}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[full_name] = mod
        spec.loader.exec_module(mod)
        setattr(pkg_mod, mod_short, mod)
        loaded[mod_short] = mod
    return loaded


def test_mu0_bitwise_identical_to_frozen_parent_payload_and_br019_z_profile(tmp_path):
    frozen = _load_frozen_parent_modules(tmp_path)
    old_amu = frozen["actual_mixture_update"]
    old_br = frozen["bounded_relief"]

    rng = np.random.default_rng(20261024)
    x = rng.uniform(0.0, 26.0, (24, 5, 9))
    b = rng.uniform(3.0, 14.0, (24, 5))
    y = rng.uniform(0.0, 32.0, (24, 5))
    m = np.ones_like(y, dtype=bool)
    m[2, 1] = False
    m[9, :] = False
    a = np.arange(24, dtype=np.int64)
    w0 = rng.dirichlet(np.ones(10))

    # Include exact BR019_Z recipe parameters: relief=0.03, goal="COST", ONLINE_C (eta=0.3, schedule_power=0.5, severity_step=10.0)
    old_configs = [
        old_amu.MixtureConfig(eta=0.0, schedule_power=0.5, severity_step=0.0, cost_scale=100.0),
        old_amu.MixtureConfig(eta=0.03, schedule_power=0.5, severity_step=1.0, cost_scale=100.0),
        old_amu.MixtureConfig(eta=0.3, schedule_power=0.5, severity_step=1.0, cost_scale=100.0),
        old_amu.MixtureConfig(eta=0.3, schedule_power=0.5, severity_step=10.0, cost_scale=100.0),
    ]
    new_configs = [
        MixtureConfig(eta=0.0, schedule_power=0.5, severity_step=0.0, cost_scale=100.0),
        MixtureConfig(eta=0.03, schedule_power=0.5, severity_step=1.0, cost_scale=100.0, proximity_strength=0.0),
        MixtureConfig(eta=0.3, schedule_power=0.5, severity_step=1.0, cost_scale=100.0, proximity_strength=0.0),
        MixtureConfig(eta=0.3, schedule_power=0.5, severity_step=10.0, cost_scale=100.0, proximity_strength=0.0),
    ]

    for relief in (0.0, 0.03, 0.25):
        old_res = old_br.run_signed(
            x, b, y, m, a, old_configs, w0, relief=relief, score=True, return_actions=True
        )
        new_res = run_signed(
            x, b, y, m, a, new_configs, w0, relief=relief, score=True, return_actions=True
        )
        np.testing.assert_array_equal(new_res["actions"], old_res["actions"])
        np.testing.assert_array_equal(new_res["ledger"], old_res["ledger"])
        np.testing.assert_array_equal(new_res["counts"], old_res["counts"])
        np.testing.assert_array_equal(new_res["days"], old_res["days"])

        old_meta = old_res["metadata"]
        new_meta = new_res["metadata"]
        assert new_meta["proximity_strengths"] == [0.0, 0.0, 0.0, 0.0]
        for key, old_val in old_meta.items():
            if key == "configs":
                for old_c, new_c in zip(old_val, new_meta["configs"]):
                    expected_c = dict(old_c, proximity_strength=0.0)
                    assert new_c == expected_c
            else:
                assert new_meta[key] == old_val


def test_exact_fraction_proximal_first_update_three_active_coordinates_and_dual():
    # T=9 issues (0..8), N=4 turbines, K=10 signed increments (slot 0 anchor + 9 experts).
    # First 8 issues (0..7) have 0+7 < now false -> zero updates before i=8.
    # At i=0..7: b = 10, d = 0.5.
    # Raw expert 0 (slot 1): X=0  -> delta_1 = -5
    # Raw expert 1 (slot 2): X=22 -> delta_2 = +12
    # Raw experts 2..8 (slots 3..9): X=10 -> delta_3..9 = 0
    # Initial weights w0 = [1/8, 3/4, 1/8, 0, ..., 0]
    # Stored past actual action at issue 0:
    #   r_0 = 10 + (1/8)*0 + (3/4)*(-5) + (1/8)*12 = 31/4 = 7.75.
    # Targets at issue 0 across 4 cells: y = [25, 7.75, 4, 12]
    #   cell 0: 25 > 7.75   -> slope -9/600
    #   cell 1: 7.75 == 7.75 -> slope 0 (kink)
    #   cell 2: 4 < 7.75    -> slope +1/600
    #   cell 3: 12 > 7.75   -> slope -9/600
    # Mean slope over fixed N=4 cells = -17 / 2400.
    # Gradient g = (-17 / 2400) * [0, -5, 12, 0, ...] = [0, 85/2400, -204/2400, 0, ...].
    # Let eta = 1/2, schedule_power = 0.5 (elapsed = 0 -> factor = 1), so step = 1/2.
    # Let proximity_strength mu = 1/2, so step * mu = 1/4 and 1 + step * mu = 5/4.
    # Notice (w0 - step*g + step*mu*w0) / (1 + step*mu) = w0 - (step / (1 + step*mu)) * g
    # at the first step when w == w0, with effective step (1/2) / (5/4) = 2/5.
    # Exact Fractions for v:
    #   v_0 = 1/8
    #   v_1 = 3/4 - (2/5)*(85/2400) = 3/4 - 17/1200 = 883/1200
    #   v_2 = 1/8 + (2/5)*(204/2400) = 1/8 + 51/1500 = 239/1500
    #   v_3..9 = 0
    # Sum of the 3 positive coordinates of v:
    #   v_0 + v_1 + v_2 = 1/8 + 883/1200 + 239/1500 = (750 + 4415 + 956)/6000 = 6119/6000 > 1.
    # Excess over 1 is 119/6000, shared across the 3 active coordinates: theta = 119/18000.
    # Since v_0 = 2250/18000 > 119/18000 and 0 - 119/18000 < 0, active support is {0, 1, 2}:
    #   w1_0 = 2250/18000 - 119/18000 = 2131/18000
    #   w1_1 = 13245/18000 - 119/18000 = 13126/18000
    #   w1_2 = 2862/18000 - 119/18000 = 2743/18000
    #   w1_3..9 = 0.
    b = np.full((9, 4), 10.0)
    x = np.full((9, 4, 9), 10.0)
    x[:, :, 0] = 0.0
    x[:, :, 1] = 22.0
    y = np.tile(np.array([25.0, 7.75, 4.0, 12.0]), (9, 1))
    m = np.ones_like(y, dtype=bool)
    a = np.arange(9, dtype=np.int64)
    w0 = np.array([1 / 8, 3 / 4, 1 / 8] + [0.0] * 7)

    cfg = MixtureConfig(
        eta=0.5,
        schedule_power=0.5,
        severity_step=10.0,
        cost_scale=100.0,
        proximity_strength=0.5,
    )
    res = run_signed(x, b, y, m, a, [cfg], w0, relief=0.5, score=True, return_actions=True)

    assert res["metadata"]["release_trace"][:8] == [-1] * 8
    assert res["metadata"]["release_trace"][8] == 7
    assert res["metadata"]["feedback_updates"] == 1
    assert res["metadata"]["proximity_strengths"] == [0.5]
    np.testing.assert_allclose(res["actions"][0, :8], 7.75, rtol=0, atol=1e-15)

    w0_frac = [Fraction(1, 8), Fraction(3, 4), Fraction(1, 8)] + [Fraction(0)] * 7
    g_frac = [Fraction(0), Fraction(85, 2400), Fraction(-204, 2400)] + [Fraction(0)] * 7
    step_frac = Fraction(1, 2)
    mu_frac = Fraction(1, 2)
    v_frac = [
        (w_i - step_frac * g_i + step_frac * mu_frac * w0_i) / (1 + step_frac * mu_frac)
        for w_i, g_i, w0_i in zip(w0_frac, g_frac, w0_frac)
    ]
    theta_frac = (sum(v_frac[:3]) - Fraction(1)) / 3
    w1_frac = [max(v_i - theta_frac, Fraction(0)) for v_i in v_frac]
    assert w1_frac[:3] == [
        Fraction(2131, 18000),
        Fraction(13126, 18000),
        Fraction(2743, 18000),
    ]
    assert sum(w1_frac) == Fraction(1)

    expected_w1 = np.array([float(f) for f in w1_frac], dtype=np.float64)
    np.testing.assert_allclose(res["metadata"]["final_weights"][0], expected_w1, rtol=0, atol=1e-15)

    # Severity dual is unaffected by proximity_strength
    res_mu0 = run_signed(
        x,
        b,
        y,
        m,
        a,
        [MixtureConfig(eta=0.5, schedule_power=0.5, severity_step=10.0, proximity_strength=0.0)],
        w0,
        relief=0.5,
        score=True,
        return_actions=True,
    )
    assert res["metadata"]["final_lambda_u"][0] == pytest.approx(3 / 16, abs=1e-15)
    assert res["metadata"]["final_lambda_u"] == res_mu0["metadata"]["final_lambda_u"]

    r8_frac = Fraction(10) + Fraction(-5) * w1_frac[1] + Fraction(12) * w1_frac[2]
    np.testing.assert_allclose(res["actions"][0, 8], float(r8_frac), rtol=0, atol=1e-14)


def test_multistep_shrink_toward_initial_w0_and_reactivation_of_zeroed_coord():
    # Step 1 drives coordinate 0 to exact zero; Step 2 has zero gradient (kink y == actual)
    # and positive proximity_strength shrinks weights back toward w0, reactivating coordinate 0!
    b = np.full((3, 2), 10.0)
    x = np.full((3, 2, 9), 10.0)
    x[:, :, 0] = 6.0   # delta_1 = -4
    x[:, :, 1] = 14.0  # delta_2 = +4
    # Anchors [0, 8, 16]: issue 0 matures at i=1 (0+7<8); issue 1 matures at i=2 (8+7<16).
    a = np.array([0, 8, 16], dtype=np.int64)
    m = np.ones((3, 2), dtype=bool)
    w0 = np.array([0.2, 0.8] + [0.0] * 8)

    # At i=0, r_0 = 10 + 0.8*(-4) = 6.8.
    # Make y[0] = 20 > 6.8 so gradient strongly favors increasing action (reducing slot 1, increasing slot 2).
    # Specifically slope = -9/600 = -3/200 on both cells -> g = [0, +3/50, -3/50, 0...].
    # With eta = 10, schedule_power = 0, mu = 0.1 -> step = 10, step*mu = 1:
    # At step 1 (from w0 = [0.2, 0.8, 0...]):
    #   v = (w0 - 10*g + 1*w0) / 2 = w0 - 5*g = [0.2, 0.8 - 0.3, 0.0 + 0.3, 0...] = [0.2, 0.5, 0.3, 0...]
    #Wait: let's make slot 0 drop to 0 on step 1!
    # How does slot 0 drop to 0? If slot 2 has large negative gradient, v_2 becomes very large, so simplex projection subtracts theta > v_0!
    # Let's check: at issue 0, set x[0, :, 1] = 110 -> delta_2 = +100.
    # Then g = (-3/200) * [0, -4, 100, 0...] = [0, +0.06, -1.5, 0...].
    # With step = 2, mu = 0.5 (step*mu = 1, denom = 2):
    #   v = (w0 - 2*g + 1*w0) / 2 = w0 - g = [0.2, 0.8 - 0.06, 0 + 1.5, 0...] = [0.2, 0.74, 1.5, 0...].
    # Projecting [0.2, 0.74, 1.5] onto simplex:
    #   sorted: 1.5, 0.74, 0.2.
    #   top 2 sum = 2.24 -> theta_2 = (2.24 - 1)/2 = 0.62 > 0.2!
    #   Since 0.74 - 0.62 = 0.12 > 0 and 0.2 - 0.62 < 0, coordinate 0 is projected to EXACT ZERO:
    #   w1 = [0.0, 0.12, 0.88, 0...]!
    x[0, :, 1] = 110.0
    # At i=1, with w1 = [0.0, 0.12, 0.88, 0...] and x[1, :, 1] = 14.0 (delta_2 = +4):
    #   r_1 = 10 + 0.12*(-4) + 0.88*(+4) = 10 - 0.48 + 3.52 = 13.04.
    # Set y[1] = 13.04 (exact kink!) so gradient at issue 1 is EXACT ZERO!
    # Then at i=2, when issue 1 matures:
    #   g_2 = 0!
    #   v_2 = (w1 - 2*0 + 1*w0) / (1 + 1) = 0.5 * w1 + 0.5 * w0
    #       = [0.1, 0.46, 0.44, 0...] (already on simplex!).
    # Coordinate 0 was 0.0 at w1 and is reactivated to 0.1 > 0 toward w0[0] = 0.2,
    # and ||w2 - w0||_2 = 0.5 * ||w1 - w0||_2 < ||w1 - w0||_2!
    y = np.full((3, 2), 20.0)
    y[1, :] = 13.04

    cfg_prox = MixtureConfig(eta=2.0, schedule_power=0.0, severity_step=0.0, proximity_strength=0.5)
    cfg_no_prox = MixtureConfig(eta=1.0, schedule_power=0.0, severity_step=0.0, proximity_strength=0.0)

    # Check after 1 update (slicing first 2 issues)
    res_step1 = run_signed(x[:2], b[:2], y[:2], m[:2], a[:2], [cfg_prox], w0, relief=0.5)
    w1 = np.asarray(res_step1["metadata"]["final_weights"][0])
    np.testing.assert_allclose(w1[:3], [0.0, 0.12, 0.88], rtol=0, atol=1e-15)
    assert w1[0] == 0.0

    # Check after 2 updates: prox shrinks back toward w0 and reactivates slot 0; unregularized stays at w1
    res_step2 = run_signed(x, b, y, m, a, [cfg_prox, cfg_no_prox], w0, relief=0.5)
    w2_prox = np.asarray(res_step2["metadata"]["final_weights"][0])
    w2_unreg = np.asarray(res_step2["metadata"]["final_weights"][1])

    np.testing.assert_allclose(w2_prox[:3], [0.1, 0.46, 0.44], rtol=0, atol=1e-15)
    assert w2_prox[0] > 0.0
    np.testing.assert_allclose(w2_unreg[:3], [0.0, 0.12, 0.88], rtol=0, atol=1e-15)
    assert np.linalg.norm(w2_prox - w0) < np.linalg.norm(w1 - w0)


def test_proximal_elapsed_schedule_uses_stored_past_actual_action_and_initial_w0():
    # Two updates with elapsed schedule power=1.0: anchors [0, 72, 144].
    # Verify step 2 uses stored past actual action r_1 (NOT current or initial action),
    # factor_2 = (1 + 72/144)^(-1) = 2/3, lam_1 from step 1, and shrinks toward initial w0 (NOT w1).
    b = np.full((3, 2), 10.0)
    x = np.full((3, 2, 9), 10.0)
    x[:, :, 0] = 6.0   # delta_1 = -4
    x[:, :, 1] = 14.0  # delta_2 = +4
    y = np.full((3, 2), 12.0)
    m = np.ones((3, 2), dtype=bool)
    a = np.array([0, 72, 144], dtype=np.int64)
    w0 = np.array([0.0, 0.75, 0.25] + [0.0] * 7)
    cfg = MixtureConfig(
        eta=1.0,
        schedule_power=1.0,
        severity_step=10.0,
        cost_scale=100.0,
        proximity_strength=0.5,
    )
    res = run_signed(x, b, y, m, a, [cfg], w0, relief=0.5, return_actions=True)

    # Exact Fraction oracle for step 1 (issue 0, elapsed=0, factor=1, step=1, mu=1/2 -> denom=3/2):
    # r_0 = 10 + 0.75*(-4) + 0.25*(4) = 8 < 12 -> slope = -9/600 = -3/200.
    # g1 = [0, 3/50, -3/50, 0...].
    # v1 = (w0 - 1*g1 + (1/2)*w0) / (3/2) = w0 - (2/3)*g1 = [0, 3/4 - 1/25, 1/4 + 1/25, 0...] = [0, 71/100, 29/100, 0...].
    # Already on simplex!
    # r_1 = 10 + (71/100)*(-4) + (29/100)*(4) = 10 - 168/100 = 832/100 = 8.32.
    # lam_1 = 10 * 1 * 10 * ((12 - 8)/6 - (12 - 10)/6) / 100 = 1/3.
    np.testing.assert_allclose(res["actions"][0, 0], 8.0, rtol=0, atol=1e-15)
    np.testing.assert_allclose(res["actions"][0, 1], 8.32, rtol=0, atol=1e-14)

    # Step 2 (issue 1, elapsed=72, factor=2/3, step=2/3, mu=1/2 -> step*mu = 1/3, denom = 4/3):
    # Stored past actual action at issue 1 is r_1 = 8.32 < 12.
    # With lam_1 = 1/3, slope = (-9 - 10/3) / 600 = -37 / 1800.
    # g2 = (-37 / 1800) * [0, -4, 4, 0...] = [0, 37/450, -37/450, 0...].
    # v2 = (w1 - (2/3)*g2 + (1/3)*w0) / (4/3) = (3/4)*w1 - (1/2)*g2 + (1/4)*w0.
    # Notice the shrink pulls toward w0 = [0, 3/4, 1/4], NOT toward w1!
    w1_1 = Fraction(71, 100)
    w1_2 = Fraction(29, 100)
    g2_1 = Fraction(37, 450)
    g2_2 = Fraction(-37, 450)
    w2_1 = (w1_1 - Fraction(2, 3) * g2_1 + Fraction(1, 3) * Fraction(3, 4)) / Fraction(4, 3)
    w2_2 = (w1_2 - Fraction(2, 3) * g2_2 + Fraction(1, 3) * Fraction(1, 4)) / Fraction(4, 3)
    assert w2_1 + w2_2 == Fraction(1)
    expected_w2 = np.array([0.0, float(w2_1), float(w2_2)] + [0.0] * 7)
    np.testing.assert_allclose(res["metadata"]["final_weights"][0], expected_w2, rtol=0, atol=1e-15)
    # Dual at step 2 uses stored actual r_1 = 8.32:
    expected_lam2 = 1 / 3 + 10.0 * (2 / 3) * 10.0 * ((12.0 - 8.32) / 6.0 - 2.0 / 6.0) / 100.0
    assert res["metadata"]["final_lambda_u"][0] == pytest.approx(expected_lam2, abs=1e-15)


def test_br019_z_stability_across_proximity_strength_grid_and_stored_past_actions():
    # Targeted stability check around BR019_Z (relief=0.03, COST initializer, eta=0.3, schedule_power=0.5, severity_step=10.0)
    # across the planned proximity_strength grid [0.0, 0.001, 0.01, 0.1] with shared initial weights.
    rng = np.random.default_rng(1903)
    b_hist = rng.uniform(6.0, 14.0, (40, 4))
    x_hist = np.clip(b_hist[:, :, None] + rng.normal(0.0, 4.0, (40, 4, 9)), 0.0, None)
    y_hist = np.clip(b_hist + rng.normal(0.0, 5.0, (40, 4)), 0.0, None)

    init = fit_signed(x_hist, b_hist, y_hist, relief=0.03, goal="COST", time_limit=5.0)
    w0 = np.asarray(init["weights"], dtype=np.float64)

    t_eval, n_eval = 32, 4
    b_eval = rng.uniform(6.0, 14.0, (t_eval, n_eval))
    x_eval = np.clip(b_eval[:, :, None] + rng.normal(0.0, 4.5, (t_eval, n_eval, 9)), 0.0, None)
    y_eval = np.clip(b_eval + rng.normal(0.0, 5.5, (t_eval, n_eval)), 0.0, None)
    m_eval = np.ones_like(y_eval, dtype=bool)
    a_eval = np.arange(t_eval, dtype=np.int64)

    strengths = [0.0, 0.001, 0.01, 0.1]
    configs = [
        MixtureConfig(
            eta=0.3,
            schedule_power=0.5,
            severity_step=10.0,
            cost_scale=100.0,
            proximity_strength=mu,
        )
        for mu in strengths
    ]
    res = run_signed(
        x_eval, b_eval, y_eval, m_eval, a_eval, configs, w0, relief=0.03, score=True, return_actions=True
    )
    assert res["metadata"]["proximity_strengths"] == strengths
    assert res["actions"].shape == (4, t_eval, n_eval)

    # First 8 issues (0..7) must be bitwise identical across all proximity strengths
    for idx in range(1, len(strengths)):
        np.testing.assert_array_equal(res["actions"][idx, :8], res["actions"][0, :8])

    # Distance to initial w0 decreases monotonically as proximity_strength increases on this trajectory
    final_w = np.asarray(res["metadata"]["final_weights"], dtype=np.float64)
    dists = [float(np.linalg.norm(final_w[idx] - w0)) for idx in range(len(strengths))]
    assert dists[3] < dists[0]
    assert np.allclose(final_w.sum(axis=1), 1.0, atol=1e-12, rtol=0.0)
    assert (final_w >= 0.0).all()

    # Future label invariance: mutating y_eval[8:] cannot change actions up to issue 15 (since 8+7 < 15 is False)
    y_mut = y_eval.copy()
    y_mut[8:] = 999.0
    res_mut = run_signed(
        x_eval, b_eval, y_mut, m_eval, a_eval, configs, w0, relief=0.03, score=True, return_actions=True
    )
    np.testing.assert_array_equal(res["actions"][:, :16], res_mut["actions"][:, :16])


def test_config_validation_rejects_invalid_proximity_strength_and_guards_run_mixture():
    b = np.full((9, 2), 10.0)
    x = np.full((9, 2, 9), 12.0)
    y = np.full((9, 2), 11.0)
    m = np.ones((9, 2), dtype=bool)
    a = np.arange(9, dtype=np.int64)
    w0 = np.full(10, 0.1)

    for bad_mu in (-0.001, -1.0, np.nan, np.inf, -np.inf, True, False, np.bool_(True), np.bool_(False)):
        with pytest.raises(ValueError, match="Invalid frozen numerical configuration"):
            run_signed(
                x,
                b,
                y,
                m,
                a,
                [MixtureConfig(eta=0.3, schedule_power=0.5, severity_step=1.0, proximity_strength=bad_mu)],
                w0,
                relief=0.03,
            )
        with pytest.raises(ValueError, match="Invalid frozen numerical configuration"):
            run_signed(
                x,
                b,
                y,
                m,
                a,
                [dict(eta=0.3, schedule_power=0.5, severity_step=1.0, proximity_strength=bad_mu)],
                w0,
                relief=0.03,
            )

    # run_mixture must keep default proximity_strength=0.0 working and explicitly reject nonzero proximity_strength
    delta = signed_experts(x, b, relief=0.0)
    ok = run_mixture(delta, np.maximum(y - b, 0.0), m, a, [MixtureConfig()], w0, score=False)
    assert ok["metadata"]["configs"][0] == asdict(MixtureConfig())

    for bad_rm_mu in (0.001, 0.1, -0.1, np.nan, np.inf, True, False):
        with pytest.raises(ValueError, match="Invalid frozen numerical configuration"):
            run_mixture(
                delta,
                np.maximum(y - b, 0.0),
                m,
                a,
                [MixtureConfig(proximity_strength=bad_rm_mu)],
                w0,
                score=False,
            )


def test_all_48_proximal_recipe_combinations_evaluate_without_qualification_filtering():
    rng = np.random.default_rng(48)
    b = rng.uniform(5.0, 12.0, (12, 3))
    x = rng.uniform(0.0, 20.0, (12, 3, 9))
    y = rng.uniform(0.0, 22.0, (12, 3))
    m = np.ones_like(y, dtype=bool)
    a = np.arange(12, dtype=np.int64)
    w0 = rng.dirichlet(np.ones(10))

    # 4 reliefs * 2 goals * 2 online base modes * 3 nonzero proximity strengths = 48 recipes
    configs = []
    for _relief in (0.01, 0.03, 0.1, 0.3):
        for _goal in ("COST", "CAP"):
            for eta, gamma in ((0.03, 1.0), (0.3, 10.0)):
                for mu in (0.001, 0.01, 0.1):
                    configs.append(
                        MixtureConfig(
                            eta=eta,
                            schedule_power=0.5,
                            severity_step=gamma,
                            cost_scale=100.0,
                            proximity_strength=mu,
                        )
                    )
    assert len(configs) == 48
    res = run_signed(x, b, y, m, a, configs, w0, relief=0.03, score=True, return_actions=True)
    assert res["actions"].shape == (48, 12, 3)
    assert res["ledger"].shape == (48, 1, 4)
    assert len(res["metadata"]["final_weights"]) == 48
    assert len(res["metadata"]["proximity_strengths"]) == 48
