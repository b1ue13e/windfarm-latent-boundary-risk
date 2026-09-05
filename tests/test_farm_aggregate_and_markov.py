"""Unit tests for farm aggregate reserve sizing and honest Markov-Gilbert evaluation."""
from __future__ import annotations

import numpy as np
import pytest

from scripts.eval_farm_aggregate_reserve import (
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
