"""F4 regression tests for block-level joint bootstrap semantics."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.hierarchical_bootstrap import compute_hierarchical_joint_bootstrap


def test_joint_bootstrap_exposes_noninferiority_probability_alias():
    """P(delta<=0) is named non-inferiority, with legacy alias preserved."""
    result = compute_hierarchical_joint_bootstrap(
        {201: np.array([-3.0, -2.0, -1.0]), 202: np.array([-2.0, -1.0, -4.0])},
        n_boot=2000,
        random_seed=7,
    )
    assert result["joint_p_non_inferior"] == result["joint_p_val_superiority"]
    assert result["joint_p_non_inferior"] == 1.0


def test_joint_bootstrap_positive_cost_delta_has_low_noninferiority_probability():
    """Positive cost deltas are disfavored: P(delta<=0) should be zero."""
    result = compute_hierarchical_joint_bootstrap(
        {201: np.array([1.0, 2.0, 3.0]), 202: np.array([2.0, 1.0, 4.0])},
        n_boot=2000,
        random_seed=7,
    )
    assert result["joint_p_non_inferior"] == 0.0
    assert result["joint_p_val_superiority"] == 0.0
