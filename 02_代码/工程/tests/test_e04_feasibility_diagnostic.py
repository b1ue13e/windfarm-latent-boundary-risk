import importlib.util
from repo_paths import Path, repository_root

import numpy as np
import pytest


SCRIPT = Path(repository_root()) / 'scripts' / 'analyze_e04_feasibility.py'
SPEC = importlib.util.spec_from_file_location('e04_diagnostic', SCRIPT)
diagnostic = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagnostic)


def test_gap_decomposition_does_not_erase_observed_exceedance():
    result = diagnostic.decompose_gap(0.103, np.array([0.09, 0.10, 0.11, 0.12]), 0.10)
    assert result['observed_excess_pp'] == pytest.approx(0.3)
    assert result['observed_excess_pp'] + result['uncertainty_margin_pp'] == pytest.approx(result['ucb_excess_pp'])
    assert result['lcb95'] < 0.10 < result['ucb95']


def test_synchronized_days_preserve_shared_test_uncertainty():
    counts = np.full((5, 35), 100.0)
    violations = np.tile(np.r_[np.zeros(17), np.full(18, 20.0)], (5, 1))
    seed_only = diagnostic.sensitivity_draws(counts, violations, 3000, 11, 'seed_only', 1)
    shared = diagnostic.sensitivity_draws(counts, violations, 3000, 11, 'shared_days', 1)
    assert np.std(seed_only) < 1e-14
    assert np.std(shared) > 0.01
    assert np.array_equal(shared, diagnostic.sensitivity_draws(counts, violations, 3000, 11, 'shared_days', 1))


def test_weighted_rate_and_leave_one_day_out_keep_unequal_denominators():
    counts = np.array([[10.0, 90.0], [10.0, 90.0]])
    violations = np.array([[5.0, 9.0], [5.0, 9.0]])
    stats = diagnostic.day_summary(counts, violations)
    assert stats['observed_rate'] == pytest.approx(0.14)
    assert stats['leave_one_day_out_min'] == pytest.approx(0.10)
    assert stats['leave_one_day_out_max'] == pytest.approx(0.50)


def test_point_constraints_retain_cost_failure_even_if_violation_passes():
    assert diagnostic.constraint_failures(1.0, -0.01, 0.09) == ['cost_delta']
    assert diagnostic.constraint_failures(0.0, 0.0, 0.101) == ['absolute_violation']


def test_invalid_counts_fail_closed():
    with pytest.raises(ValueError, match='violation counts'):
        diagnostic.validate_arrays(np.ones((5, 35)), np.full((5, 35), 2.0))


def test_existing_diagnostic_directory_is_never_overwritten(tmp_path):
    with pytest.raises(FileExistsError, match='never overwritten'):
        diagnostic.run(tmp_path / 'inputs', tmp_path)


def test_analysis_cannot_write_into_frozen_input_directory(tmp_path):
    inputs = tmp_path / 'inputs'
    inputs.mkdir()
    with pytest.raises(ValueError, match='outside the frozen result directory'):
        diagnostic.run(inputs, inputs / 'new_output')
