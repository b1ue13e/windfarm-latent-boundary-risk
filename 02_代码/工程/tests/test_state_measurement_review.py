from repo_paths import Path, repository_root

import numpy as np

from windfarm_moe.state_measurement import information_matrix
from windfarm_moe.state_measurement_review import (specified_b, original_b_expression,
                                                  independent_features, deficit_profile)


def test_registered_b_and_actual_legacy_code_have_distinct_update_guards():
    source = Path(__file__).parents[1] / "scripts/run_state_measurement_pilot.py"
    def all_costs_risks_and_required_guards_pass(name, low=None, high=None, severity=True):
        return not (name in ("old_state", "old_power") and severity)
    assert specified_b(all_costs_risks_and_required_guards_pass)
    assert not original_b_expression(source, all_costs_risks_and_required_guards_pass)


def test_required_replacement_guard_cannot_be_removed():
    def fail_one_required_guard(name, low=None, high=None, severity=True):
        return name != "severity_P_vs_PZ"
    assert not specified_b(fail_one_required_guard)


def test_independent_time_node_constructor_matches_all_six_actual_cells():
    rng = np.random.default_rng(819)
    d = rng.normal(size=(100, 3, 4)).astype(np.float32)
    d[38, 0, 1] = np.nan
    d[40, 1, 3] = np.nan
    a = np.arange(40, 75)
    f = rng.uniform(0, 1000, size=(len(a), 3)).astype(np.float32)
    rows = np.array([0, 1, 2, 7, 34, 78, 104])
    for cell in ("F", "FZ", "O6", "OP6", "OZ6", "OPZ6"):
        independent = independent_features(d, a, f, cell, rows)
        production = information_matrix(d, a, f, cell)[rows]
        assert np.array_equal(np.isnan(independent), np.isnan(production))
        assert np.allclose(independent, production, rtol=1e-6, atol=2e-5, equal_nan=True)
    changed = d.copy()
    changed[75:] = 1e10
    assert np.array_equal(independent_features(changed, a, f, "OPZ6", rows),
                          independent_features(d, a, f, "OPZ6", rows), equal_nan=True)


def test_small_deficit_bins_preserve_strict_event_count_and_missing_target():
    s = np.array([[0., .001, .01, .1, 1., 10., 11., np.nan]])
    p = deficit_profile(s, np.zeros_like(s), np.isfinite(s))
    assert p["strict_events"] == 6
    assert p["counts"] == [2, 1, 1, 1, 1]
    assert sum(p["counts"]) == p["strict_events"]
