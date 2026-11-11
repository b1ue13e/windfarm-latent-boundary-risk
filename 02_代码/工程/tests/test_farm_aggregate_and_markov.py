"""Unit tests for farm aggregate reserve sizing and honest Markov-Gilbert evaluation."""
from __future__ import annotations

import numpy as np
import pytest

from scripts.eval_farm_aggregate_reserve import (
    aggregate_farm_pcc_causal,
    compute_pinball_loss,
    fit_binned_policy,
    fit_gaussian_reserve,
    fit_optimal_quantile,
    ppitch_from_gate,
)
from scripts.eval_markov_gilbert_telemetry import (
    calc_detection_metrics,
    simulate_markov_gilbert,
)


def test_simulate_markov_gilbert_bounds_and_determinism():
    n_steps = 500
    rng1 = np.random.default_rng(123)
    states1, lags1 = simulate_markov_gilbert(n_steps, p_gb=0.1, p_bb=0.8, max_lag=6, rng=rng1)

    rng2 = np.random.default_rng(123)
    states2, lags2 = simulate_markov_gilbert(n_steps, p_gb=0.1, p_bb=0.8, max_lag=6, rng=rng2)

    assert np.array_equal(states1, states2)
    assert np.array_equal(lags1, lags2)
    assert np.all(np.isin(states1, [0, 1]))
    assert np.all((lags1 >= 0) & (lags1 <= 6))
    # In good state, lag must be 0
    assert np.all(lags1[states1 == 0] == 0)
    # In bad state, lag must be > 0
    assert np.all(lags1[states1 == 1] > 0)


def test_simulate_markov_gilbert_edge_cases():
    states, lags = simulate_markov_gilbert(0)
    assert len(states) == 0 and len(lags) == 0

    states, lags = simulate_markov_gilbert(1)
    assert len(states) == 1 and len(lags) == 1


def test_calc_detection_metrics_zero_division():
    y_pred = np.zeros((10, 5), dtype=bool)
    y_true = np.zeros((10, 5), dtype=bool)
    mask = np.ones((10, 5), dtype=bool)

    m = calc_detection_metrics(y_pred, y_true, mask)
    assert m["recall"] == 0.0
    assert m["precision"] == 0.0
    assert m["f1"] == 0.0
    assert m["evaluated_cells"] == 50

    # Perfect prediction
    y_pred = np.ones((10, 5), dtype=bool)
    y_true = np.ones((10, 5), dtype=bool)
    m = calc_detection_metrics(y_pred, y_true, mask)
    assert m["recall"] == 1.0
    assert m["precision"] == 1.0
    assert m["f1"] == 1.0


def test_ppitch_from_gate():
    gate = np.array([
        [[0.8, 0.2, 0.0, 0.0], [0.1, 0.2, 0.7, 0.0]],
        [[0.0, 0.0, 0.0, 0.0], [0.33, 0.33, 0.34, 0.0]]
    ], dtype=np.float32)

    p_pitch = ppitch_from_gate(gate)
    assert p_pitch.shape == (2, 2)
    assert np.isclose(p_pitch[0, 0], 0.0)
    assert np.isclose(p_pitch[0, 1], 0.7)
    assert np.isfinite(p_pitch[1, 0])  # zero division protected


def test_compute_pinball_loss():
    shortfall = np.array([10.0, 20.0, 30.0])
    reserve = np.array([20.0, 20.0, 20.0])
    q = 0.9

    # diff = [-10, 0, 10]
    # for -10: max(0.9 * -10, -0.1 * -10) = max(-9, 1.0) = 1.0
    # for 0: 0.0
    # for 10: max(0.9 * 10, -0.1 * 10) = max(9.0, -1) = 9.0
    # mean = (1.0 + 0.0 + 9.0) / 3 = 10.0 / 3
    loss = compute_pinball_loss(shortfall, reserve, q)
    assert np.isclose(loss, 10.0 / 3.0)


def test_fit_optimal_quantile():
    s_val = np.linspace(0, 100, 101)
    cost, q, r = fit_optimal_quantile(s_val, rho=10.0)
    assert cost > 0
    assert 0.5 <= q <= 0.99
    assert 0 <= r <= 100


def test_fit_gaussian_reserve():
    residuals = np.random.default_rng(42).normal(loc=10.0, scale=5.0, size=500)
    shortfall = np.maximum(residuals, 0.0)
    cost, r = fit_gaussian_reserve(residuals, shortfall, rho=10.0)
    assert cost > 0
    assert r >= 0


def test_fit_binned_policy():
    s_val = np.arange(100, dtype=float)
    signal_val = np.linspace(0, 1, 100)
    edges, reserves = fit_binned_policy(s_val, signal_val, n_bins=5, rho=10.0)
    assert len(edges) == 4
    assert len(reserves) == 5
    for b in range(5):
        assert reserves[b] >= 0


def test_aggregate_farm_pcc_causal_no_future_leakage():
    # Setup: 2 samples, 3 horizon steps, 4 turbines
    # Turbine 0: always online (mask=1 everywhere)
    # Turbine 1: online at t=0, fails at t=1,2 (mask=1 at t=0, mask=0 at t>0)
    # Turbine 2: offline at t=0, comes online at t=1 (mask=0 at t=0, mask=1 at t>0)
    # Turbine 3: always offline (mask=0 everywhere)
    n_samples = 2
    h = 3
    n_turbines = 4

    pred = np.ones((n_samples, h, n_turbines), dtype=np.float32) * 100.0
    target = np.ones((n_samples, h, n_turbines), dtype=np.float32) * 80.0

    mask = np.zeros((n_samples, h, n_turbines), dtype=np.float32)
    mask[:, :, 0] = 1.0  # turbine 0
    mask[:, 0, 1] = 1.0  # turbine 1 online only at t=0
    mask[:, 1:, 2] = 1.0  # turbine 2 offline at t=0, online at t>0
    # turbine 3 remains 0

    p_pred, p_target, valid, p_eval_sub, active = aggregate_farm_pcc_causal(
        pred, target, mask, min_active_turbines=1
    )

    # 1. Causal forecast P_pred MUST sum over anchor-available turbines (turbines 0 and 1) = 2 * 100 = 200
    # at ALL horizons, without presciently excluding turbine 1 at t=1,2 or including turbine 2 at t=1,2
    assert np.allclose(p_pred, 200.0)

    # 2. Target power P_target:
    # at t=0: turbines 0 and 1 are valid -> 2 * 80 = 160
    # at t=1,2: only turbine 0 is online and valid -> 1 * 80 = 80
    assert np.allclose(p_target[:, 0], 160.0)
    assert np.allclose(p_target[:, 1:], 80.0)

    # 3. Offline evaluated subset forecast P_pred_eval_subset:
    # at t=0: turbines 0 and 1 -> 2 * 100 = 200
    # at t=1,2: only turbine 0 -> 1 * 100 = 100
    assert np.allclose(p_eval_sub[:, 0], 200.0)
    assert np.allclose(p_eval_sub[:, 1:], 100.0)

    # 4. Proves strict separation and zero future leakage:
    # At t=1,2, p_pred (200.0) != p_eval_sub (100.0) because p_pred was not prescient
    assert not np.allclose(p_pred[:, 1:], p_eval_sub[:, 1:])

    # 5. Active count: 2 at t=0, 1 at t=1,2
    assert np.all(active[:, 0] == 2)
    assert np.all(active[:, 1:] == 1)
    assert np.all(valid)

