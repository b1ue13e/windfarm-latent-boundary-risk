"""Unit tests for EXP-02 Zero-Privileged Supervision Protocol & Hard Assertions.
"""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pytest
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_exp02_zero_privileged_supervision import (
    assert_zero_pitch_features,
    assert_zero_pitch_supervision,
    assert_zero_pitch_model_selection,
    ZeroPrivilegedRepresentationNet,
    PinballLoss,
    compute_psrei_components,
    fit_wspd_bins,
    apply_wspd_bins,
    V_RATED,
    P_RATED,
    EPSILON_DEFAULT,
    EPSILON_GRID,
)


def test_zero_pitch_feature_assertion():
    """Verify that assert_zero_pitch_features catches any leaked pitch signal."""
    # Clean feature array: Pab_mean is strictly 0.0
    clean_arr = np.zeros((10, 4))
    channel_names = ["Wspd", "Pab_mean", "wake_score", "Patv"]
    clean_arr[:, 0] = 5.0  # Wspd
    clean_arr[:, 3] = 500.0  # Patv
    # Should pass cleanly
    assert_zero_pitch_features(clean_arr, channel_names, "clean_arr")

    # Leaked array: Pab_mean has non-zero values
    leaked_arr = clean_arr.copy()
    leaked_arr[2, 1] = 1.5  # 1.5 degrees pitch
    with pytest.raises(AssertionError) as exc_info:
        assert_zero_pitch_features(leaked_arr, channel_names, "leaked_arr")
    assert "Strict zero-privileged pitch withholding violated" in str(exc_info.value)


def test_zero_pitch_supervision_assertion():
    """Verify that supervision target dictionary cannot include pitch-derived regime."""
    clean_targets = {"proxy_target": torch.zeros(10), "shortfall": torch.ones(10)}
    assert_zero_pitch_supervision(clean_targets)

    forbidden_targets = {"regime_primary": torch.ones(10)}
    with pytest.raises(AssertionError) as exc_info:
        assert_zero_pitch_supervision(forbidden_targets)
    assert "Supervision target contains forbidden pitch key" in str(exc_info.value)


def test_zero_pitch_model_selection_assertion():
    """Verify that early stopping and checkpoint selection cannot use pitch metrics."""
    assert_zero_pitch_model_selection("val_pinball_loss")
    assert_zero_pitch_model_selection("validation_mse")

    with pytest.raises(AssertionError):
        assert_zero_pitch_model_selection("test_pitch_nmi")

    with pytest.raises(AssertionError):
        assert_zero_pitch_model_selection("val_regime_accuracy")


def test_proxy_label_construction_and_sensitivity_grid():
    """Verify proxy label formula Z_tilde = I(v > v_rated and P < P_rated - eps)."""
    wspd = np.array([8.0, 11.0, 11.0, 12.0])
    patv = np.array([400.0, 1480.0, 1400.0, 1500.0])

    for eps in EPSILON_GRID:
        z = ((wspd > V_RATED) & (patv < (P_RATED - eps))).astype(int)
        # Point 0: v=8.0 <= 10.5 -> 0
        assert z[0] == 0
        # Point 3: P=1500 >= 1500-eps -> 0
        assert z[3] == 0
        # Point 2: v=11.0 > 10.5 and P=1400 < 1500-eps (for eps=20, 50) -> 1
        if eps <= 50.0:
            assert z[2] == 1


def test_zero_privileged_net_forward():
    """Test model forward pass with and without auxiliary proxy head."""
    net_with_proxy = ZeroPrivilegedRepresentationNet(in_features=7, hidden_dim=32, use_proxy_head=True)
    x = torch.randn(16, 7)
    r, proxy_logits = net_with_proxy(x)
    assert r.shape == (16,)
    assert proxy_logits.shape == (16, 2)
    assert torch.all(r >= 0.0)  # Non-negative reserves

    net_direct = ZeroPrivilegedRepresentationNet(in_features=7, hidden_dim=32, use_proxy_head=False)
    r_dir, proxy_dir = net_direct(x)
    assert r_dir.shape == (16,)
    assert proxy_dir is None


def test_psrei_computation():
    """Test matched-budget PSREI computation logic."""
    s = np.array([10.0, 20.0, 0.0, 5.0])
    r = np.array([10.0, 15.0, 5.0, 5.0])
    mask = np.ones(4, dtype=bool)

    # s - r: [0, 5, -5, 0] -> shortage = [0, 5, 0, 0]
    # sum(r) = 35.0, sum(sh) = 5.0
    # DT = 1/6, rho = 10.0 -> total = (35 + 10 * 5) / 6 = 85 / 6 = 14.1667
    comp = compute_psrei_components(s, r, mask)
    expected_cost = (35.0 + 10.0 * 5.0) / 6.0
    assert np.isclose(comp["psrei_kwh"], expected_cost)
    assert np.isclose(comp["violation_rate_pct"], 25.0)  # 1 out of 4 violated (s > r)
