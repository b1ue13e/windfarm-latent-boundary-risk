import importlib.util
from repo_paths import Path, repository_root

import numpy as np
import pytest

PATH = Path(repository_root()) / 'scripts/analyze_e04_regime_slices.py'
SPEC = importlib.util.spec_from_file_location('e04_slices', PATH)
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def test_alignment_rejects_one_step_target_shift():
    cache = np.arange(30, dtype=np.float32).reshape(15, 2)
    anchors = np.arange(3, 7)
    values = cache[anchors + 2]
    analysis.assert_target_alignment(values, cache, anchors, 2)
    with pytest.raises(ValueError, match='target alignment'):
        analysis.assert_target_alignment(values, cache, anchors, 1)


def test_native_block_is_not_calendar_day():
    anchors = np.arange(35, 35 + 288)
    blocks = analysis.native_blocks(anchors)
    assert blocks[143] == 0 and blocks[144] == 1
    assert anchors[143] // 144 != anchors[0] // 144
    with pytest.raises(ValueError, match='contiguous'):
        analysis.native_blocks(np.array([35, 37]))


def test_transition_dilation_does_not_wrap_to_end():
    states = np.zeros((12, 1), dtype=int)
    states[1:] = 1
    mask = analysis.transition_mask(states)
    assert mask[:5].all()
    assert not mask[-3:].any()


def test_partition_preserves_counts_and_signed_excess():
    valid = np.array([True, True, True, False])
    violation = np.array([True, False, True, True])
    groups = np.array(['low', 'low', 'high', 'high'])
    rows = analysis.summarize_partition(groups, valid, violation, np.ones(4), np.ones(4), np.ones(4))
    assert sum(r['n'] for r in rows) == 3
    assert sum(r['violations'] for r in rows) == 2
    assert sum(r['signed_excess_count'] for r in rows) == pytest.approx(1.7)


def test_daily_closure_rejects_different_violation_locations():
    reference = {'n': np.array([2., 2.]), 'B_viol': np.array([1., 1.]), 'B_cost': np.array([2., 2.])}
    valid = np.ones(4, dtype=bool)
    with pytest.raises(ValueError, match='daily violation closure'):
        analysis.check_daily_closure('B', np.array([0, 0, 1, 1]), valid,
                                     np.array([True, True, False, False]), np.ones(4), reference)


def test_cost_drift_is_not_accepted_when_daily_violations_match():
    reference = {'n': np.array([2.]), 'B_viol': np.array([1.]), 'B_cost': np.array([2.])}
    with pytest.raises(ValueError, match='exact daily cost closure'):
        analysis.check_daily_closure('B', np.zeros(2, dtype=int), np.ones(2, dtype=bool),
                                     np.array([True, False]), np.array([1., 1.000001]), reference)


def test_metadata_localized_path_is_disclosed_but_numeric_changes_are_rejected():
    bound = {'class_weight_source_cache': '/remote/cache', 'feature_stats': {'mean': 5.0}}
    local = {**bound, 'class_weight_source_cache': 'E:/cache'}
    assert set(analysis.metadata_path_difference(local, bound)) == {'class_weight_source_cache'}
    with pytest.raises(ValueError, match='numeric or schema'):
        analysis.metadata_path_difference({**local, 'feature_stats': {'mean': 6.0}}, bound)


def test_pooling_weights_denominators_and_excludes_incomplete_policy():
    path = PATH.with_name('summarize_e04_regime_slices.py')
    spec = importlib.util.spec_from_file_location('pool_e04', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    def row(policy, n, v, mean):
        return dict(policy=policy, axis='wind', group='low', n=n, violations=v,
                    signed_excess_count=v-.1*n, shortage_kwh=0,
                    mean_reserve_kw=mean, mean_shortfall_kw=mean, mean_forecast_error_kw=mean)
    pooled = module.pool_rows([row('B', 10, 5, 100), row('B', 90, 9, 0), row('C', 100, 0, 0)], ['B'])
    assert len(pooled) == 1
    assert pooled[0]['violation_rate'] == pytest.approx(.14)
    assert pooled[0]['mean_reserve_kw'] == pytest.approx(10.)
