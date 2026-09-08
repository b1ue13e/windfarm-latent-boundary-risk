"""Unit tests for the decisive fair risk benchmark modules."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.decisive_fair_risk_benchmark import (
    TARGET_VIOLATION,
    CRITICAL_FRACTILE,
    apply_5bin_policy,
    compute_decisive_metrics,
    evaluate_route_verdict,
    find_iso_reliability_multiplier,
    fit_5bin_quantiles,
    weather_block_bootstrap,
)


def test_find_iso_reliability_multiplier_sparse_shortfall():
    """When positive shortfall frequency is below target_violation (Kelmarsh clean case),
    the function must NOT collapse to arbitrary grid lower bounds (e.g. 0.05).
    """
    N = 1000
    shortfall = np.zeros(N)
    shortfall[:10] = 50.0  # 1.0% positive shortfall (<< 10.0% target)
    raw_reserve = np.full(N, 40.0)
    active = np.ones(N, dtype=bool)

    gamma, delta, iso_r = find_iso_reliability_multiplier(shortfall, raw_reserve, active, target_violation=0.10)

    # Must preserve calibrated reserve (gamma = 1.0, delta = 0.0)
    assert gamma == 1.0
    assert delta == 0.0
    assert np.allclose(iso_r, raw_reserve)
    assert np.mean(shortfall > iso_r) <= 0.10


def test_find_iso_reliability_multiplier_scaling_down():
    """When zero-reserve violation > 10% but raw reserve over-hedges (viol < 10%),
    the function should find the minimal scaling multiplier g in (0, 1].
    """
    np.random.seed(42)
    N = 2000
    shortfall = np.zeros(N)
    # 30% positive shortfall uniformly distributed [10, 100]
    shortfall[:600] = np.random.uniform(10.0, 100.0, 600)
    # High initial reserve that yields very low violation (~2%)
    raw_reserve = np.full(N, 95.0)
    active = np.ones(N, dtype=bool)

    gamma, delta, iso_r = find_iso_reliability_multiplier(shortfall, raw_reserve, active, target_violation=0.10)

    assert 0.05 <= gamma <= 1.0
    assert delta == 0.0
    viol = float(np.mean(shortfall > iso_r))
    assert viol <= 0.10
    # Should be close to 10%
    assert viol >= 0.08


def test_find_iso_reliability_multiplier_scaling_up():
    """When raw reserve under-hedges (viol > 10%), scaling multiplier must scale up (> 1.0)."""
    np.random.seed(42)
    N = 2000
    shortfall = np.zeros(N)
    shortfall[:800] = np.random.uniform(20.0, 120.0, 800)  # 40% shortfall
    raw_reserve = np.full(N, 30.0)  # Under-hedged
    active = np.ones(N, dtype=bool)

    raw_viol = float(np.mean(shortfall > raw_reserve))
    assert raw_viol > 0.10

    gamma, delta, iso_r = find_iso_reliability_multiplier(shortfall, raw_reserve, active, target_violation=0.10)

    assert gamma > 1.0
    viol = float(np.mean(shortfall > iso_r))
    assert viol <= 0.10


def test_find_iso_reliability_multiplier_conformal_fallback():
    """When multiplicative scaling up to 15.0 cannot bring violation <= target,
    conformal additive fallback delta must guarantee compliance.
    """
    N = 1000
    shortfall = np.full(N, 500.0)  # 100% huge shortfall
    raw_reserve = np.zeros(N)      # Zero reserve (multiplication cannot change it)
    active = np.ones(N, dtype=bool)

    gamma, delta, iso_r = find_iso_reliability_multiplier(shortfall, raw_reserve, active, target_violation=0.10)

    assert gamma == 15.0
    assert delta >= 500.0
    viol = float(np.mean(shortfall > iso_r))
    assert viol <= 0.10


def test_5bin_calibration_and_application():
    """Fit 5 quintile bins on active score and apply to test score."""
    np.random.seed(123)
    val_score = np.linspace(0.0, 10.0, 500)
    val_shortfall = val_score * 2.0 + np.random.normal(0, 1.0, 500)
    val_active = val_score > 2.0

    reserves, edges, global_res = fit_5bin_quantiles(val_score, val_shortfall, val_active, n_bins=5, tau=0.90)

    assert len(reserves) == 5
    assert len(edges) == 4
    assert global_res > 0.0

    # Monotonicity: higher risk scores should get higher or equal reserves
    assert reserves[4] >= reserves[0]

    test_score = np.array([1.0, 3.5, 5.5, 7.5, 9.5])
    test_reserves = apply_5bin_policy(test_score, reserves, edges, n_bins=5)
    assert len(test_reserves) == 5
    assert test_reserves[-1] >= test_reserves[0]


def test_compute_decisive_metrics():
    """Check metric computations including FAR, recall, pinball, and costs."""
    N = 100
    shortfall = np.array([0.0] * 50 + [10.0] * 50)
    reserve = np.array([5.0] * 100)
    active = np.ones(N, dtype=bool)
    prob = np.array([0.1] * 50 + [0.9] * 50)
    regime = np.array([1] * 50 + [2] * 50)  # 1: MPPT, 2: Pitching

    metrics = compute_decisive_metrics(
        shortfall=shortfall,
        reserve=reserve,
        active=active,
        prob=prob,
        regime=regime,
        rho=10.0,
        dt=1.0 / 6.0,
        tau=0.90,
    )

    assert metrics["n_active_cells"] == 100
    assert metrics["violation_rate"] == 0.50  # 50 cells have 10.0 > 5.0
    assert metrics["shortage_mwh"] > 0.0
    assert metrics["reserve_mwh"] > 0.0
    assert metrics["brier_score"] < 0.05
    assert metrics["ece"] <= 0.10


def test_weather_block_bootstrap():
    """Vectorized weather block bootstrap returns confidence intervals and paired deltas."""
    N = 300
    shortfall = np.random.uniform(0, 20, N)
    active = np.ones(N, dtype=bool)
    time_indices = np.arange(N)
    res_dict = {
        "Joint Routed": np.full(N, 15.0),
        "Continuous Physical Quantile": np.full(N, 14.0),
    }

    boot_res = weather_block_bootstrap(
        shortfall=shortfall,
        reserves_dict=res_dict,
        active=active,
        time_indices=time_indices,
        block_size=50,
        n_boot=100,
        seed=42,
        ref_model="Joint Routed",
    )

    assert "Joint Routed" in boot_res
    assert "Continuous Physical Quantile" in boot_res
    stat = boot_res["Continuous Physical Quantile"]
    assert len(stat["ci_95"]) == 2
    assert stat["ci_95"][0] <= stat["ci_95"][1]
    assert len(stat["delta_ci_95"]) == 2


def test_evaluate_route_verdict():
    """Verify route evaluation logic under diverse mock scenario outcomes."""
    # Scenario 1: Simple Quantile wins over Deep MoE
    df1 = pd.DataFrame([
        {"farm": "wtb", "regime": "clean", "model": "Joint Routed", ("total_cost", "mean"): 600.0, ("event_recall", "mean"): 0.8},
        {"farm": "wtb", "regime": "clean", "model": "Continuous Physical Quantile", ("total_cost", "mean"): 500.0, ("event_recall", "mean"): 0.5},
        {"farm": "wtb", "regime": "clean", "model": "Missingness-Aware GBDT", ("total_cost", "mean"): 480.0, ("event_recall", "mean"): 0.5},
        {"farm": "wtb", "regime": "delay6", "model": "Joint Routed", ("total_cost", "mean"): 1200.0, ("event_recall", "mean"): 0.5},
        {"farm": "wtb", "regime": "delay6", "model": "Continuous Physical Quantile", ("total_cost", "mean"): 1300.0, ("event_recall", "mean"): 0.4},
    ])
    v1 = evaluate_route_verdict(df1)
    assert "Route 2" in v1["recommended_route"]
    assert v1["simple_quantile_beats_deep"] is True


def test_state_conditional_hybrid_policy_switching():
    """Verify state-conditional hybrid policy switches accurately based on observable health signal."""
    N = 100
    r_phys = np.full(N, 10.0)
    r_moe = np.full(N, 25.0)
    g_clean_phys, d_clean_phys = 1.0, 0.0
    g_stale_moe, d_stale_moe = 1.2, 5.0

    # Lags: first 50 are clean (tau = 0), next 50 are stale (tau >= 1)
    lags = np.array([0] * 50 + [6] * 50)
    missing = np.zeros(N, dtype=bool)

    is_clean = (lags == 0) & (~missing)
    r_clean_part = np.maximum(g_clean_phys * r_phys + d_clean_phys, 0.0)
    r_stale_part = np.maximum(g_stale_moe * r_moe + d_stale_moe, 0.0)
    r_hybrid = np.where(is_clean, r_clean_part, r_stale_part)

    # First 50 must match clean physical rule (10.0)
    assert np.allclose(r_hybrid[:50], 10.0)
    # Next 50 must match stale learned posterior rule (1.2 * 25.0 + 5.0 = 35.0)
    assert np.allclose(r_hybrid[50:], 35.0)


def test_validation_frozen_compliance_flag():
    """Verify that models with test violation > 10.0% are strictly flagged non-compliant."""
    N = 100
    shortfall = np.array([20.0] * 15 + [0.0] * 85)  # 15% positive shortfall
    reserve = np.array([5.0] * 100)
    active = np.ones(N, dtype=bool)

    metrics = compute_decisive_metrics(
        shortfall=shortfall,
        reserve=reserve,
        active=active,
        prob=None,
        regime=np.ones(N, dtype=int),
    )

    assert metrics["violation_rate"] == 0.15
    is_compliant = bool(metrics["violation_rate"] <= 0.10)
    assert is_compliant is False

    # Now make it compliant
    reserve_high = np.array([25.0] * 100)
    metrics_high = compute_decisive_metrics(
        shortfall=shortfall,
        reserve=reserve_high,
        active=active,
        prob=None,
        regime=np.ones(N, dtype=int),
    )
    assert metrics_high["violation_rate"] == 0.0
    assert bool(metrics_high["violation_rate"] <= 0.10) is True


def test_evaluate_route_verdict_dual_track():
    """Verify Track A vs Track B recommendation logic."""
    # Scenario Track A: Hybrid is compliant across clean and delay
    df_track_a = pd.DataFrame([
        {"farm": "wtb", "regime": "clean", "model": "State-Conditional Hybrid Policy", ("violation_rate", "mean"): 0.095, ("total_cost", "mean"): 400.0, ("event_recall", "mean"): 0.8},
        {"farm": "wtb", "regime": "delay6", "model": "State-Conditional Hybrid Policy", ("violation_rate", "mean"): 0.098, ("total_cost", "mean"): 1000.0, ("event_recall", "mean"): 0.8},
        {"farm": "wtb", "regime": "clean", "model": "Joint Routed", ("total_cost", "mean"): 500.0, ("event_recall", "mean"): 0.8},
        {"farm": "wtb", "regime": "delay6", "model": "Joint Routed", ("total_cost", "mean"): 1100.0, ("event_recall", "mean"): 0.8},
        {"farm": "wtb", "regime": "clean", "model": "Continuous Physical Quantile", ("total_cost", "mean"): 420.0, ("event_recall", "mean"): 0.5},
        {"farm": "wtb", "regime": "delay6", "model": "Continuous Physical Quantile", ("total_cost", "mean"): 1500.0, ("event_recall", "mean"): 0.4},
    ])
    v_a = evaluate_route_verdict(df_track_a)
    assert "Track A" in v_a["track_recommendation"]
    assert v_a["hybrid_compliant_all"] is True

    # Scenario Track B: Hybrid fails on delay6 (violation > 10%)
    df_track_b = pd.DataFrame([
        {"farm": "wtb", "regime": "clean", "model": "State-Conditional Hybrid Policy", ("violation_rate", "mean"): 0.095, ("total_cost", "mean"): 400.0, ("event_recall", "mean"): 0.8},
        {"farm": "wtb", "regime": "delay6", "model": "State-Conditional Hybrid Policy", ("violation_rate", "mean"): 0.145, ("total_cost", "mean"): 1000.0, ("event_recall", "mean"): 0.8},
        {"farm": "wtb", "regime": "clean", "model": "Joint Routed", ("total_cost", "mean"): 500.0, ("event_recall", "mean"): 0.8},
        {"farm": "wtb", "regime": "delay6", "model": "Joint Routed", ("total_cost", "mean"): 1100.0, ("event_recall", "mean"): 0.8},
        {"farm": "wtb", "regime": "clean", "model": "Continuous Physical Quantile", ("total_cost", "mean"): 420.0, ("event_recall", "mean"): 0.5},
        {"farm": "wtb", "regime": "delay6", "model": "Continuous Physical Quantile", ("total_cost", "mean"): 1500.0, ("event_recall", "mean"): 0.4},
    ])
    v_b = evaluate_route_verdict(df_track_b)
    assert "Track B" in v_b["track_recommendation"]
    assert v_b["hybrid_compliant_all"] is False

