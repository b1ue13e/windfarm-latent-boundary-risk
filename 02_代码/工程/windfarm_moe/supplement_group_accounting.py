"""Fixed-134 group scoring of archived turbine actions for the V3 supplement.

Future completeness is used only in this offline scoring module.  Membership
and actions are not selected from future validity.  Channel order W/P/Q/Z and
the finite-three-blade provenance of Z are source-contract responsibilities.
"""
from __future__ import annotations

import numpy as np


MEMBER_COUNT = 134


def _coordinates(data, anchors, forecast):
    values = np.asarray(data)
    raw_anchors = np.asarray(anchors)
    f = np.asarray(forecast, dtype=np.float64)
    if values.ndim != 3 or values.shape[1:] != (MEMBER_COUNT, 4):
        raise ValueError("Bound W/P/Q/Z data must contain exactly the fixed 134 members")
    if (raw_anchors.ndim != 1 or not len(raw_anchors)
            or raw_anchors.dtype.kind not in "iu"):
        raise ValueError("Issue anchors must be a nonempty integer vector")
    a = raw_anchors.astype(np.int64, copy=False)
    if (a[0] < 0 or a[-1] + 6 >= len(values) or np.any(np.diff(a) != 1)
            or f.shape != (len(a), MEMBER_COUNT)):
        raise ValueError("Complete contiguous issue calendar and aligned forecast required")
    return values, a, f


def fixed_group_masks(data, anchors, forecast) -> tuple[np.ndarray, np.ndarray]:
    """Return target and paired group masks, with no history-completeness filter.

    Z is the bound physical channel whose upstream producer already requires all
    three blade readings.  Missingness in W/Q or historical inputs does not add
    a group selector.  No alternate target-only population is chosen downstream.
    """
    values, a, f = _coordinates(data, anchors, forecast)
    target = np.isfinite(f).all(axis=1) & np.isfinite(values[a + 6, :, 1]).all(axis=1)
    pair = (target & np.isfinite(values[a, :, 1]).all(axis=1)
            & np.isfinite(values[a, :, 3]).all(axis=1))
    return target, pair


def group_account(data, anchors, forecast, reserves, pair_mask) -> dict[str, np.ndarray]:
    """Daily R/U/V/C/N and netting gap on the unique fixed paired population.

    The input action matrix must already exist for every issue/member and be
    finite, including issues later excluded from scoring.  The group target is
    formed from signed errors, never from turbine-positive shortfalls.  Every
    issue natural day remains in the daily ledger even if its paired count is
    zero.  Totals on such days are storage placeholders, not zero observations.
    """
    values, a, f = _coordinates(data, anchors, forecast)
    reserve = np.asarray(reserves, dtype=np.float64)
    pair = np.asarray(pair_mask)
    if (reserve.shape != f.shape or not np.isfinite(reserve).all()
            or np.any(reserve < 0)):
        raise ValueError("Precomputed finite nonnegative actions are required for all issues/members")
    target, expected_pair = fixed_group_masks(values, a, f)
    if pair.dtype != bool or pair.shape != (len(a),) or not np.array_equal(pair, expected_pair):
        raise ValueError("Only the exact fixed M_pair population may be scored")
    # Missing future measurements remain NaN outside M_pair.  They are never
    # interpreted as zero power.  Masking happens after group action formation.
    error = f - values[a + 6, :, 1].astype(np.float64)
    signed_group_error = error.sum(axis=1, dtype=np.float64)
    group_shortfall = np.maximum(signed_group_error, 0.)
    group_reserve = reserve.sum(axis=1, dtype=np.float64)
    raw_u = np.maximum(group_shortfall - group_reserve, 0.) / 6.
    individual_u_sum = (np.maximum(error - reserve, 0.) / 6.).sum(axis=1, dtype=np.float64)
    r = np.where(pair, group_reserve / 6., 0.)
    u = np.where(pair, raw_u, 0.)
    v = pair & (group_shortfall > group_reserve)
    gap = np.where(pair, individual_u_sum - raw_u, 0.)
    cost = r + 10. * u
    issue_days = a // 144
    days = np.arange(issue_days[0], issue_days[-1] + 1, dtype=np.int64)
    daily = {
        name: np.asarray([vector[issue_days == day].sum(dtype=np.float64) for day in days])
        for name, vector in (("C", cost), ("R", r), ("U", u), ("V", v),
                             ("N", pair), ("gap_U", gap), ("target_count", target))
    }
    return daily | {"days": days}
