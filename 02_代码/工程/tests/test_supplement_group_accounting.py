"""Deterministic fixed-member scoring fixtures; no raw research data."""
import numpy as np
import pytest

from windfarm_moe.supplement_group_accounting import fixed_group_masks, group_account


def fixture(anchors=None):
    a = np.arange(140, 146) if anchors is None else np.asarray(anchors, dtype=np.int64)
    data = np.zeros((int(a[-1]) + 7, 134, 4), dtype=np.float64)
    data[..., 1] = 10.
    data[..., 3] = 1.
    forecast = np.full((len(a), 134), 10.)
    reserves = np.zeros_like(forecast)
    return data, a, forecast, reserves


def test_t05_population_exact_intersection_and_unrelated_history_not_a_selector():
    data, anchors, f, _ = fixture()
    data[anchors[0] + 6, 0, 1] = np.nan
    data[anchors[1], 1, 1] = np.nan
    data[anchors[2], 2, 3] = np.nan
    f[3, 3] = np.nan
    data[anchors[4], :, 0] = np.nan
    data[anchors[4] - 10, :, 1] = np.nan
    target, pair = fixed_group_masks(data, anchors, f)
    np.testing.assert_array_equal(target, [False, True, True, False, True, True])
    np.testing.assert_array_equal(pair, [False, False, False, False, True, True])


def test_signed_group_errors_allow_cancellation_and_same_pair_gap_is_correct():
    data, anchors, f, r = fixture([140, 141])
    # Two turbine errors cancel exactly: +12 and -12 kW.  Turbine U=2kWh,
    # while the correct signed-error group U is zero.
    f[0, 0], f[0, 1] = 22., -2.
    # Second interval: sum signed errors=18, group action=6 -> U=2kWh.
    f[1, 0] = 28.
    r[1, 0] = 6.
    _, pair = fixed_group_masks(data, anchors, f)
    result = group_account(data, anchors, f, r, pair)
    assert result["U"].sum() == 2.
    assert result["R"].sum() == 1.
    assert result["C"].sum() == 21.
    assert result["V"].sum() == 1.
    assert result["N"].sum() == 2.
    assert result["gap_U"].sum() == 2.


def test_t06_zero_group_shortfalls_keep_procurement_cost_and_netting_gap():
    data, anchors, f, r = fixture()
    f[:, 0], f[:, 1] = 22., -2.
    r[:, 0] = np.arange(len(anchors), dtype=float)
    _, pair = fixed_group_masks(data, anchors, f)
    result = group_account(data, anchors, f, r, pair)
    assert result["U"].sum() == result["V"].sum() == 0.
    assert result["R"].sum() == result["C"].sum() == np.arange(6).sum() / 6.
    assert result["gap_U"].sum() > 0 and result["N"].sum() == 6.


def test_t08_zero_valid_day_remains_in_original_calendar_and_counts_disclosed():
    data, anchors, f, r = fixture(np.arange(140, 290))
    # Exclude every issue in the middle natural day via pitch, keeping future
    # targets intact and allowing surrounding days to remain visible.
    data[np.arange(144, 288), 0, 3] = np.nan
    _, pair = fixed_group_masks(data, anchors, f)
    result = group_account(data, anchors, f, r, pair)
    np.testing.assert_array_equal(result["days"], [0, 1, 2])
    np.testing.assert_array_equal(result["N"], [4, 0, 2])
    np.testing.assert_array_equal(result["target_count"], [4, 144, 2])
    assert all(result[key][1] == 0 for key in ["C", "R", "U", "V", "gap_U"])


def test_all_empty_pair_has_count_zero_without_changing_actions_or_target_population():
    data, anchors, f, r = fixture()
    data[anchors, 0, 3] = np.nan
    r[:] = 2.
    before = r.copy()
    target, pair = fixed_group_masks(data, anchors, f)
    result = group_account(data, anchors, f, r, pair)
    assert target.all() and not pair.any()
    assert result["N"].sum() == 0 and result["target_count"].sum() == len(anchors)
    np.testing.assert_array_equal(r, before)


@pytest.mark.parametrize("bad_mask", ["target_fallback", "subset", "wrong_dtype"])
def test_alternate_success_populations_rejected(bad_mask):
    data, anchors, f, r = fixture()
    data[anchors[0], 0, 3] = np.nan
    target, pair = fixed_group_masks(data, anchors, f)
    if bad_mask == "target_fallback":
        pair = target
    elif bad_mask == "subset":
        pair[-1] = False
    else:
        pair = pair.astype(int)
    with pytest.raises(ValueError, match="exact fixed M_pair"):
        group_account(data, anchors, f, r, pair)


def test_missing_future_measurement_is_excluded_not_zero_power():
    data, anchors, f, r = fixture([140, 141])
    data[anchors[0] + 6, 0, 1] = np.nan
    _, pair = fixed_group_masks(data, anchors, f)
    result = group_account(data, anchors, f, r, pair)
    assert result["N"].sum() == 1 and result["U"].sum() == 0.


def test_future_missingness_cannot_justify_missing_precomputed_action():
    data, anchors, f, r = fixture()
    data[anchors[0] + 6, 0, 1] = np.nan
    r[0, 0] = np.nan
    _, pair = fixed_group_masks(data, anchors, f)
    with pytest.raises(ValueError, match="actions are required for all"):
        group_account(data, anchors, f, r, pair)


@pytest.mark.parametrize("bad", ["members", "calendar", "future", "forecast_shape"])
def test_fixed_identity_and_full_calendar_shape_contract(bad):
    data, anchors, f, _ = fixture()
    if bad == "members":
        data = data[:, :133]
        f = f[:, :133]
    elif bad == "calendar":
        anchors = anchors[[0, 2, 3, 4, 5]]
        f = f[[0, 2, 3, 4, 5]]
    elif bad == "future":
        data = data[:-1]
    else:
        f = f[:, :-1]
    with pytest.raises(ValueError):
        fixed_group_masks(data, anchors, f)
