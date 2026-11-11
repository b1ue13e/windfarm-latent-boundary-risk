import numpy as np
import pytest

from windfarm_moe.state_measurement import account
from windfarm_moe.state_measurement_controls import (budget_shift, common_level, fast_account,
    labels_and_comparisons, controls_envelope, corrected_routes)


def test_budget_match_handles_extra_procurement_negative_shift_and_clipping():
    x = np.array([[0., 0., 2., 8.]])
    m = np.ones_like(x, bool)
    for target in (0., .2, 1., 2.5, 5.):
        z = np.full_like(x, target)
        fit = budget_shift(x, z, m)
        assert np.maximum(x + fit["delta_kw"], 0).mean() == pytest.approx(target, abs=1e-9)
    assert budget_shift(x, np.ones_like(x), m)["delta_kw"] < 0
    assert budget_shift(x, np.full_like(x, 5), m)["delta_kw"] > 0


def test_budget_uses_only_declared_population_and_never_refits_on_application():
    x, z = np.array([[0., 4., 999.]]), np.array([[2., 6., np.nan]])
    m = np.array([[True, True, False]])
    fit = budget_shift(x, z, m)
    assert fit["delta_kw"] == 2
    future = np.array([[100., 200.]])
    assert np.maximum(future + fit["delta_kw"], 0).mean() == 152
    with pytest.raises(ValueError):
        budget_shift(x, z, np.ones_like(m))


def test_common_level_requires_every_fixed_instance_and_no_fallback():
    upper = np.ones((5, 12, 5)) * .08
    upper[4, 11, 0] = .100001
    assert common_level(upper, [.9, .925, .95, .975, .99]) == 1
    assert common_level(np.ones_like(upper) * .11, range(5)) is None


def test_new_account_matches_independent_legacy_and_keeps_missing_targets():
    rng = np.random.default_rng(918)
    a = np.arange(120, 500)
    s = rng.uniform(0, 50, (len(a), 4)); r = rng.uniform(0, 50, s.shape)
    s[5, 2] = np.nan
    m = np.isfinite(s)
    first, second = fast_account(s, r, m, a), account(s, r, m, a)
    for k in first:
        assert np.allclose(first[k], second[k], atol=1e-10)
    assert first["N"].sum() == s.size - 1


def test_corrected_B_does_not_add_legacy_update_U_guards():
    prefix = "Original:HGB:"
    risk = {prefix + c: True for c in ("F", "FZ", "O6", "OZ6", "OP6", "OPZ6")}
    ints = {}
    for name in ("fresh_state", "old_state", "old_power", "P_premium_vs_Z", "residual_state", "severity_P_vs_Z", "severity_P_vs_PZ"):
        kind = "D" if name == "P_premium_vs_Z" else "G"
        value = dict(lower=.02, upper=.03) if name in ("old_state", "old_power") else dict(lower=-.001, upper=.001)
        ints[prefix + name + "|cost|" + kind] = value
        for s in range(5):
            ints[prefix + name + "|instance_U|" + str(s)] = dict(lower=-.01, upper=.02 if name in ("old_state", "old_power") else 0)
    assert corrected_routes(prefix, ints, risk)["B"]
    ints[prefix + "severity_P_vs_PZ|instance_U|3"]["upper"] = .002
    assert not corrected_routes(prefix, ints, risk)["B"]


def test_joint_family_has_596_coordinates_and_signed_R_U():
    labels, pairs = labels_and_comparisons()
    assert len(labels) == 36 and len(pairs) == 52
    days = np.arange(12)
    c = np.stack([np.stack([100 + days + k for k in range(36)]) for _ in range(5)])
    arrays = dict(C=c, U=c / 100, R=c * .9, V=c / 1000, N=np.ones(12) * 100)
    result = controls_envelope(arrays, pairs, 40, 100, 3, 19)
    assert result["family_size"] == 596
    k = result["labels"].index(("Original:HGB:allocation_residual_state", "mean_R"))
    # Match_residual_state is at index8; OPZ6 index5, so target buys less here.
    assert result["point"][k] < 0
