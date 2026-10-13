"""Regression tests for F4 verdict semantics and model-role assignment."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.exp02_verdict import (
    assign_model_role,
    is_oracle_role,
    derive_verdict,
    threshold_sensitivity,
    VerdictInputs,
    VERDICT_SUPPORTED,
    VERDICT_DIRECTIONAL,
    VERDICT_NULL,
)


def v(h, mean, p, viol=0.0, shortage=0.0):
    return VerdictInputs(h, mean, p, viol, shortage)


def test_zero_privileged_challenger_is_not_oracle():
    for name in (
        "Zero-Privileged Challenger (eps=50)",
        "Zero-Privileged Challenger (eps=20)",
        "Zero-Privileged Challenger (eps=100)",
    ):
        assert not is_oracle_role(name)
    assert assign_model_role("Zero-Privileged Challenger (eps=50)") == "Primary Challenger"


def test_privileged_stgq_is_oracle_reference():
    assert is_oracle_role("Privileged STGQ (Oracle Reference)")
    assert assign_model_role("Privileged STGQ (Oracle Reference)") == "Oracle Upper Reference (Non-Competitive)"


def test_baseline_and_secondary_roles():
    assert assign_model_role("Site-Local Wspd-Bins") == "Primary Baseline"
    assert assign_model_role("Direct Consequence Quantile MLP") == "Secondary Baseline / Sensitivity Probe"


def test_p_delta_is_non_inferiority_probability_and_direction_is_correct():
    """High P(delta<=0) is favorable for a cost; old p<0.05 rule was backwards."""
    assert derive_verdict(v("h=1", -500_000.0, 0.98)).code == VERDICT_SUPPORTED
    assert derive_verdict(v("h=1", -365_904.0, 0.88)).code == VERDICT_DIRECTIONAL
    assert derive_verdict(v("h=6", +3_435_465.4, 0.48)).code == VERDICT_NULL


def test_c1_c2_are_gates_but_diagnostics_are_not():
    assert derive_verdict(v("h=1", -100.0, 0.96)).code == VERDICT_SUPPORTED
    assert derive_verdict(v("h=1", -100.0, 0.94)).code == VERDICT_DIRECTIONAL
    assert derive_verdict(v("h=6", +100.0, 0.99)).code == VERDICT_NULL

    # Even degraded reserve/shortage diagnostics do not alter the pre-registered C1/C2 verdict.
    verdict = derive_verdict(v("h=1", -500.0, 0.97, +2.0, +50_000.0))
    assert verdict.code == VERDICT_SUPPORTED
    assert any(not passed for _, passed, _ in verdict.diagnostics)


def test_frozen_exp02_primary_challenger_verdicts():
    assert derive_verdict(v("h=1", -365_904.0, 0.8805, +0.6208, +58_762.5)).code == VERDICT_DIRECTIONAL
    assert derive_verdict(v("h=6", +3_435_465.4, 0.4837, +7.8984, +558_694.3)).code == VERDICT_NULL


def test_threshold_sensitivity_is_data_driven():
    results = threshold_sensitivity(v("h=1", -365_904.0, 0.88))
    assert results == [
        (0.5, VERDICT_SUPPORTED),
        (0.8, VERDICT_SUPPORTED),
        (0.9, VERDICT_NULL),
        (0.95, VERDICT_NULL),
        (0.975, VERDICT_NULL),
    ]
