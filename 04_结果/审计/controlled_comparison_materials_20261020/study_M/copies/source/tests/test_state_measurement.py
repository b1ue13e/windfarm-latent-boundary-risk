import numpy as np
import pytest

from windfarm_moe.state_measurement import (information_matrix, populations, account,
                                           joint_coordinates, choose_offset)


def fixture():
    data = np.arange(100 * 2 * 4, dtype=float).reshape(100, 2, 4)
    return data, np.arange(40, 45), np.ones((5, 2)) * 500


def test_exact_freshness_and_no_hidden_pitch_or_future():
    d, a, f = fixture()
    old = information_matrix(d, a, f, "O6")
    op = information_matrix(d, a, f, "OP6")
    oz = information_matrix(d, a, f, "OZ6")
    assert np.array_equal(op[:, :118], old, equal_nan=True)
    assert np.array_equal(op[:, 118], d[a, :, 1].ravel())
    assert np.array_equal(oz[:, -1], d[a, :, 3].ravel())
    assert np.isnan(old[:, 4 + 30:4 + 36]).all()
    assert np.array_equal(old[:, 4 + 36 + 29], d[a - 6, :, 1].ravel())
    changed = d.copy()
    changed[..., 3] = -999
    changed[a[-1] + 1:] = 123456
    assert np.array_equal(information_matrix(changed, a, f, "F"),
                          information_matrix(d, a, f, "F"), equal_nan=True)
    assert information_matrix(d, a, f, "F").shape[1] == 118
    assert information_matrix(d, a, f, "FZ").shape[1] == 119


def test_dynamic_summaries_preserve_missing_slot_and_signed_power():
    d, a, f = fixture()
    d[:, :, 1] = np.arange(100)[:, None] - 80
    x = information_matrix(d, a, f, "O6")
    assert x[0, 114] == 1  # slope
    assert x[0, 115] == 1 and x[0, 116] == 6
    assert x[0, 112] < 0
    d[32, 0, 1] = np.nan
    x = information_matrix(d, a, f, "O6")
    assert np.isnan(x[0, 112:115]).all()
    assert x[0, 115] == 1  # unrelated two slots still observed


def test_population_and_target_missing_not_zero():
    d, a, _ = fixture()
    d[a[0] + 6, 0, 1] = np.nan
    d[a[1], 1, 3] = np.nan
    d[a[2], 0, 1] = -1
    target, primary = populations(d, a)
    assert not target[0, 0] and not primary[0, 0]
    assert target[1, 1] and not primary[1, 1]
    assert primary[2, 0]


def test_independent_action_accounting_and_unit():
    a = np.array([143, 144, 145])
    s = np.array([[12., np.nan], [0., 3.], [2., 4.]])
    r = np.array([[6., 500.], [1., 5.], [2., 1.]])
    m = np.isfinite(s)
    z = account(s, r, m, a)
    assert z["N"].sum() == 5
    assert z["V"].sum() == 2
    assert z["U"].sum() == 1.5
    assert z["C"].sum() == pytest.approx(15 + 15 / 6)
    assert np.allclose(z["C"], z["R"] + 10 * z["U"])
    with pytest.raises(ValueError):
        account(s, -r, m, a)


def test_joint_signed_severity_and_seed_not_resampled():
    days = np.arange(12.)
    c = np.stack([np.stack([20 + days, 19 + days]) for _ in range(5)])
    v = np.stack([np.stack([days / 10, days / 20]) for _ in range(5)])
    u = np.stack([np.stack([2 + days / 10, 3 + days / 10]) for _ in range(5)])
    n = np.ones(12) * 100
    r = joint_coordinates(c, v, u, n, [("x", 0, 1, "G"), ("y", 1, 0, "D")],
                          5, n_boot=100, span=3)
    assert r["family_size"] == 10 + 2 * 6
    assert r["point"][11] > 0 and r["point"][-1] < 0
    assert r["point"][10] > 0
    assert r["draw_sha256"] == joint_coordinates(c, v, u, n,
            [("x", 0, 1, "G"), ("y", 1, 0, "D")], 5, n_boot=100)["draw_sha256"]


def test_historical_no_choice_and_exact_tie_higher_q():
    c = np.ones((5, 5))
    levels = [.9, .925, .95, .975, .99]
    assert choose_offset(c, np.ones_like(c) * .11, levels) is None
    assert choose_offset(c, np.ones_like(c) * .09, levels) == 4
    upper = np.ones_like(c) * .09
    upper[2, 4] = .101
    assert choose_offset(c, upper, levels) == 3


def test_empirical_zero_uncertainty_is_unknown():
    c = np.ones((5, 2, 8)) * 10
    v = np.zeros_like(c)
    r = joint_coordinates(c, v, v, np.ones(8) * 20, [("x", 0, 1, "G")], 1,
                          n_boot=100)
    assert np.isposinf(r["upper"]).all()
