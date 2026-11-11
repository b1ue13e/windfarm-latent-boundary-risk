"""Frozen-calibration and historical reserve-budget controls; no fitting."""
from __future__ import annotations

import numpy as np

from .risk_frontier import shared_block_draws, simultaneous_envelope
from .state_measurement_review import specified_b

STATE_PAIRS = (("fresh_state", "F", "FZ"), ("old_state", "O6", "OZ6"),
               ("residual_state", "OP6", "OPZ6"))
CELLS = ("F", "FZ", "O6", "OP6", "OZ6", "OPZ6")
POLICIES = CELLS + tuple("Match_" + name for name, _, _ in STATE_PAIRS)
RECIPES = ("Original", "Common")


def common_level(upper, levels):
    """Smallest nominal level qualifying every supplied historical instance."""
    a = np.asarray(upper, float)
    if a.ndim != 3 or a.shape[-1] != len(levels) or np.isnan(a).any():
        raise ValueError("Invalid historical risk family")
    return next((q for q in range(len(levels)) if np.all(a[..., q] <= .1)), None)


def budget_shift(base, target, mask):
    """Match historical mean procurement using actions/mask only, not outcomes.

    Signed constant is allowed; inference is clip(calibrated_base+delta,0).
    The constant never uses evaluation-period actions or shortfalls.
    """
    x, z, m = np.asarray(base, float), np.asarray(target, float), np.asarray(mask)
    if x.shape != z.shape or m.shape != x.shape or m.dtype != bool or not m.any():
        raise ValueError("Invalid historical budget population")
    x, z = x[m], z[m]
    if not np.isfinite(x).all() or not np.isfinite(z).all() or np.any(x < 0) or np.any(z < 0):
        raise ValueError("Invalid historical actions")
    desired = float(z.mean())
    direct = desired - float(x.mean())
    if direct >= 0:
        delta = direct
    elif desired == 0:
        delta = -float(x.max())
    else:
        ordered = np.sort(x)
        prefix = np.r_[0., np.cumsum(ordered, dtype=np.float64)]
        lo, hi = -float(ordered[-1]), 0.
        for _ in range(70):
            mid = (lo + hi) / 2
            k = np.searchsorted(ordered, -mid, side="right")
            value = (prefix[-1] - prefix[k] + mid * (len(x) - k)) / len(x)
            if value < desired:
                lo = mid
            else:
                hi = mid
        delta = (lo + hi) / 2
    actual = float(np.maximum(x + delta, 0).mean())
    if abs(actual - desired) / 6 > 1e-8:
        raise ValueError("Historical procurement matching failed")
    return dict(delta_kw=delta, base_mean_r_kw=float(x.mean()), target_mean_r_kw=desired,
                matched_mean_r_kw=actual, absolute_R_mean_error=abs(actual - desired) / 6,
                cells=len(x), uses_shortfall_values=False)


def event_days(shortfall, reserve, mask, anchors):
    days = np.asarray(anchors) // 144
    unique = np.unique(days)
    if np.any(np.diff(unique) != 1):
        raise ValueError("Noncontiguous days")
    return np.bincount(days - unique[0], weights=np.sum(mask & (shortfall > reserve), axis=1),
                       minlength=len(unique)).astype(float)


def fast_account(shortfall, reserve, mask, anchors):
    s, r, m = np.asarray(shortfall, float), np.asarray(reserve, float), np.asarray(mask)
    if s.shape != r.shape or r.shape != m.shape or m.dtype != bool or not m.any():
        raise ValueError("Unpaired accounting")
    if not np.isfinite(s[m]).all() or not np.isfinite(r).all() or np.any(s[m] < 0) or np.any(r < 0):
        raise ValueError("Invalid action/target")
    days = np.asarray(anchors) // 144
    ids = np.unique(days)
    if len(ids) < 2 or np.any(np.diff(ids) != 1):
        raise ValueError("Invalid weather blocks")
    u = np.where(m, np.maximum(s - r, 0) / 6, 0)
    procurement = np.where(m, r / 6, 0)
    result = {}
    for k, v in (("C", procurement + 10 * u), ("R", procurement), ("U", u),
                 ("V", m & (s > r)), ("N", m)):
        result[k] = np.bincount(days - ids[0], weights=v.sum(axis=1, dtype=np.float64), minlength=len(ids))
    return result | {"days": ids}


def labels_and_comparisons():
    labels = [f"{recipe}:{est}:{cell}" for recipe in RECIPES for est in ("HGB", "MLP") for cell in POLICIES]
    comparisons = []
    original = (("fresh_state", "F", "FZ", "G"), ("old_state", "O6", "OZ6", "G"),
                ("old_power", "O6", "OP6", "G"), ("P_premium_vs_Z", "OP6", "OZ6", "D"),
                ("residual_state", "OP6", "OPZ6", "G"),
                ("severity_P_vs_Z", "OZ6", "OP6", "G"), ("severity_P_vs_PZ", "OPZ6", "OP6", "G"))
    for recipe in RECIPES:
        for est in ("HGB", "MLP"):
            prefix = f"{recipe}:{est}:"
            extra = [("budget_" + name, base, "Match_" + name, "G") for name, base, _ in STATE_PAIRS]
            extra += [("allocation_" + name, "Match_" + name, state, "G") for name, _, state in STATE_PAIRS]
            for name, a, b, kind in (*original, *extra):
                comparisons.append((prefix + name, labels.index(prefix + a), labels.index(prefix + b), kind))
    return labels, comparisons


def controls_envelope(arrays, comparisons, cstar, n_boot, span, seed):
    """Joint risk, cost, instance-U, mean-U and mean-R family, no seed draws."""
    c, v, u, r, n = (np.asarray(arrays[k], float) for k in ("C", "V", "U", "R", "N"))
    if c.ndim != 3 or any(x.shape != c.shape for x in (v, u, r)) or n.shape != (c.shape[-1],):
        raise ValueError("Unpaired totals")
    if cstar <= 0 or not all(np.isfinite(x).all() for x in (c, v, u, r, n)):
        raise ValueError("Invalid reference or totals")
    w, drawhash = shared_block_draws(len(n), n_boot, span, seed)
    d = w @ n
    if np.any(d <= 0) or np.any(c.sum(axis=-1).mean(axis=0) <= 0):
        raise ValueError("Nonpositive denominator")
    cp = c.sum(axis=-1).mean(axis=0) / n.sum()
    cd = w @ c.mean(axis=0).T / d[:, None]
    if np.any(cd <= 0):
        raise ValueError("Nonpositive resampled cost")
    points = [v.sum(axis=-1).ravel() / n.sum()]
    draws = [w @ v.reshape(-1, len(n)).T / d[:, None]]
    keys = [("risk", s, k) for s in range(c.shape[0]) for k in range(c.shape[1])]
    for name, a, b, kind in comparisons:
        ref = a if kind == "G" else b
        points.append(np.atleast_1d((cp[a] - cp[b]) / cp[ref]))
        draws.append(((cd[:, a] - cd[:, b]) / cd[:, ref])[:, None])
        keys.append((name, "cost", kind))
        delta = 10 * (u[:, b] - u[:, a]) / cstar
        points.append(delta.sum(axis=-1) / n.sum())
        draws.append(w @ delta.T / d[:, None])
        keys.extend((name, "instance_U", s) for s in range(c.shape[0]))
        for label, value in (("mean_U", delta.mean(axis=0)),
                             ("mean_R", (r[:, b] - r[:, a]).mean(axis=0) / cstar)):
            points.append(np.atleast_1d(value.sum() / n.sum()))
            draws.append(((w @ value) / d)[:, None])
            keys.append((name, label))
    point, boot = np.concatenate(points), np.column_stack(draws)
    result = simultaneous_envelope(point, boot, .05)
    result.update(point=point, labels=keys, family_size=len(point), span=span, n_boot=n_boot,
                  draw_sha256=drawhash, alpha=.05)
    return result


def corrected_routes(prefix, intervals, risks):
    """Actual corrected B entry point; preserve A/C definitions and thresholds."""
    pairs = {"fresh_state": ("F", "FZ", "G"), "old_state": ("O6", "OZ6", "G"),
             "old_power": ("O6", "OP6", "G"), "P_premium_vs_Z": ("OP6", "OZ6", "D"),
             "residual_state": ("OP6", "OPZ6", "G"),
             "severity_P_vs_Z": ("OZ6", "OP6", "G"), "severity_P_vs_PZ": ("OPZ6", "OP6", "G")}
    def check(name, low=None, high=None, severity=True):
        a, b, kind = pairs[name]
        value = intervals[prefix + name + "|cost|" + kind]
        ok = risks[prefix + a] and risks[prefix + b]
        if low is not None:
            ok &= value["lower"] > low
        if high is not None:
            ok &= value["upper"] <= high
        if severity:
            ok &= all(intervals[prefix + name + "|instance_U|" + str(s)]["upper"] <= .001 for s in range(5))
        return bool(ok)
    return dict(A=check("fresh_state", low=.01) or check("residual_state", low=.01),
                B=specified_b(check),
                C=all(check(name, high=.01, severity=False) for name in ("fresh_state", "old_state", "residual_state")))
