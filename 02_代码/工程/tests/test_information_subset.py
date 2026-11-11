import numpy as np
import pytest

from windfarm_moe.information_subset import (subset_grid, telemetry_columns, nested_samples,
                                            fit_standardizer, standardize, PinballMLP)


def test_lattice_complete_and_strictly_nested():
    grid = subset_grid()
    assert len(grid) == 22
    for name, (channels, lookback) in grid.items():
        cols = telemetry_columns(channels, lookback, 0, False)
        assert len(cols) == 4 + len(channels) * lookback
        assert len(set(cols)) == len(cols)
        assert set(cols) <= set(telemetry_columns((0, 1, 2), 36, 0, False))
    assert set(telemetry_columns((0, 1), 6, 0, False)) < set(telemetry_columns((0, 1), 36, 0, False))


@pytest.mark.parametrize("delay", [0, 1, 2, 3, 6])
def test_no_unarrived_columns_or_shifted_event_window(delay):
    cols = telemetry_columns((0, 1, 2), 1, delay, True)
    for channel in range(3):
        assert 4 + 36 * channel + 35 - delay in cols
        assert all(4 + 36 * channel + t not in cols for t in range(36 - delay, 36))
    wide = telemetry_columns((0, 1, 2), 36, delay, False)
    assert len(wide) == 4 + 3 * (36 - delay)
    assert min(wide) == 0 and max(wide) < 4 + 3 * 36


def test_shared_nested_sample_no_regime_or_outcome_selection():
    mask = np.ones(100, bool)
    mask[::7] = False
    result = nested_samples(mask, [10, 30, 80], 201)
    np.testing.assert_array_equal(result[10], result[80][:10])
    np.testing.assert_array_equal(result[30], result[80][:30])
    assert mask[result[80]].all()
    np.testing.assert_array_equal(result[80], nested_samples(mask, [80], 201)[80])
    with pytest.raises(ValueError):
        nested_samples(mask, [90], 201)


def test_scaler_fit_history_only_and_all_empty_feature():
    x = np.array([[1., np.nan, 4], [3., np.nan, 4]])
    mean, scale = fit_standardizer(x)
    np.testing.assert_array_equal(mean, [2, 0, 4])
    np.testing.assert_array_equal(scale, [1, 1, 1])
    z = standardize(np.array([[100, np.nan, 4]]), mean, scale)
    np.testing.assert_array_equal(z, [[98, 0, 0, 0, 1, 0]])
    mean2, scale2 = fit_standardizer(np.array([[1., np.inf], [3., -np.inf]]))
    np.testing.assert_array_equal(mean2, [2, 0])
    np.testing.assert_array_equal(scale2, [1, 1])


def test_pinball_network_learns_upper_quantile_and_repeats():
    pytest.importorskip("torch")
    x = np.zeros((400, 2), np.float32)
    x[:, 1] = np.nan
    y = np.linspace(0, 100, 400)
    settings = dict(hidden=[8, 4], epochs=50, batch_size=100, learning_rate=.01, weight_decay=0)
    a, b = PinballMLP(201, settings).fit(x, y), PinballMLP(201, settings).fit(x, y)
    pa = a.predict(x)
    np.testing.assert_array_equal(pa, b.predict(x))
    assert 85 < pa.mean() < 95
    assert np.isfinite(a.training_trace_).all()
