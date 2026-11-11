"""Paired measured-state development experiment; no causal/safety certificate."""
from __future__ import annotations

import numpy as np

from .decision_information import arrived_history
from .risk_frontier import shared_block_draws, simultaneous_envelope

CELLS = ("F", "FZ", "O6", "OP6", "OZ6", "OPZ6")
PAIRS = (("F", "FZ"), ("O6", "OZ6"), ("O6", "OP6"),
         ("OP6", "OZ6"), ("OP6", "OPZ6"))


def information_matrix(data, anchors, forecast, cell):
    """Fixed 36 event slots, WPQ only; updates at the identical issue slot."""
    if cell not in CELLS:
        raise ValueError("Unknown information cell")
    a = np.asarray(anchors, dtype=np.int64)
    f = np.asarray(forecast)
    nn = data.shape[1]
    if a.ndim != 1 or np.any(a < 35) or f.shape != (len(a), nn) or not np.isfinite(f).all():
        raise ValueError("Invalid issue/forecast coordinates")
    age = 0 if cell in ("F", "FZ") else 6
    history = arrived_history(data[..., :3], a, 36, age)
    x = history.transpose(0, 1, 3, 2).reshape(len(a) * nn, 108)
    phase = 2 * np.pi * (a % 144) / 144
    common = np.column_stack((f.ravel(), np.repeat(np.sin(phase), nn),
                              np.repeat(np.cos(phase), nn),
                              np.tile(np.arange(nn) / max(nn - 1, 1), len(a))))
    p = history[..., 1]
    last = 35 - age
    tail = p[..., last - 5:last + 1].astype(np.float64)
    # Any missing required slot makes its summary missing; no older-value search.
    mean = tail.mean(axis=-1)
    std = tail.std(axis=-1, ddof=0)
    slope = ((tail - mean[..., None]) * (np.arange(6) - 2.5)).sum(axis=-1) / 17.5
    summaries = np.stack((mean, std, slope, p[..., last] - p[..., last - 1],
                          p[..., last] - p[..., last - 6], f - p[..., last]), axis=-1)
    parts = [common, x, summaries.reshape(-1, 6)]
    if cell in ("OP6", "OPZ6"):
        fresh = data[a, :, 1]
        parts.append(np.stack((fresh, f - fresh, fresh - p[..., last]), axis=-1).reshape(-1, 3))
    if cell in ("FZ", "OZ6", "OPZ6"):
        parts.append(data[a, :, 3].reshape(-1, 1))
    return np.column_stack(parts).astype(np.float32)


def populations(data, anchors):
    a = np.asarray(anchors)
    target = np.isfinite(data[a + 6, :, 1])
    p = np.isfinite(data[a, :, 1])
    z = np.isfinite(data[a, :, 3])
    return target, target & p & z


def account(shortfall, reserve, mask, anchors):
    """Float64 daily R/U/V/C on one explicit, immutable population."""
    s, r, m = np.asarray(shortfall, float), np.asarray(reserve, float), np.asarray(mask)
    if s.shape != r.shape or s.shape != m.shape or m.dtype != bool or len(anchors) != len(s):
        raise ValueError("Unpaired accounting arrays")
    if not np.isfinite(s[m]).all() or not np.isfinite(r).all() or np.any(s[m] < 0) or np.any(r < 0):
        raise ValueError("Invalid shortfall/action")
    days = np.asarray(anchors) // 144
    unique = np.unique(days)
    if len(unique) < 2 or np.any(np.diff(unique) != 1):
        raise ValueError("Daily block sequence must be contiguous")
    ss = np.where(m, s, 0)
    rr = np.where(m, r, 0)
    u = np.where(m, np.maximum(ss - rr, 0) / 6, 0)
    reserve_energy = rr / 6
    cost = reserve_energy + 10 * u
    event = m & (ss > rr)
    return {name: np.asarray([value[days == day].sum(dtype=np.float64) for day in unique])
            for name, value in (("C", cost), ("U", u), ("R", reserve_energy),
                                ("V", event), ("N", m))} | {"days": unique}


def joint_coordinates(costs, violations, uncovered, counts, comparisons, cstar,
                      n_boot=20000, span=3, seed=20261030, alpha=.05):
    """One joint family: every instance risk, mean cost, signed instance U.

    Comparisons are (label, A index, B index, kind). G=(CA-CB)/CA;
    D=(CA-CB)/CB. Severity always means candidate B minus reference A.
    Conditional on five instances; shared weather blocks, never seed resampling.
    """
    c, v, u, n = map(lambda x: np.asarray(x, float), (costs, violations, uncovered, counts))
    if c.ndim != 3 or c.shape != v.shape or c.shape != u.shape or n.shape != (c.shape[-1],):
        raise ValueError("Invalid seed/policy/day shapes")
    if not all(np.isfinite(x).all() for x in (c, v, u, n)) or np.any(n < 0) or n.sum() <= 0:
        raise ValueError("Invalid observed totals")
    if np.any(c < 0) or np.any(v < 0) or np.any(v > n) or np.any(u < 0) or cstar <= 0:
        raise ValueError("Invalid totals or frozen reference")
    weights, drawhash = shared_block_draws(len(n), n_boot, span, seed)
    denom = weights @ n
    if np.any(denom <= 0):
        raise ValueError("Empty resampled population")
    ns, nk, _ = c.shape
    cp = c.mean(axis=0).sum(axis=-1) / n.sum()
    cd = weights @ c.mean(axis=0).T / denom[:, None]
    if np.any(cp <= 0) or np.any(cd <= 0):
        raise ValueError("Nonpositive cost denominator")
    vp = v.sum(axis=-1).ravel() / n.sum()
    vd = weights @ v.reshape(-1, len(n)).T / denom[:, None]
    points, draws = [vp], [vd]
    labels = [("risk", s, k) for s in range(ns) for k in range(nk)]
    for label, a, b, kind in comparisons:
        if kind not in ("G", "D") or a == b:
            raise ValueError("Invalid comparison")
        ref = a if kind == "G" else b
        points.append(np.atleast_1d((cp[a] - cp[b]) / cp[ref]))
        draws.append(((cd[:, a] - cd[:, b]) / cd[:, ref])[:, None])
        labels.append((label, "cost", kind))
        delta = 10 * (u[:, b] - u[:, a]) / cstar
        points.append(delta.sum(axis=-1) / n.sum())
        draws.append(weights @ delta.T / denom[:, None])
        labels.extend((label, "severity_candidate_minus_reference", s) for s in range(ns))
    point, boot = np.concatenate(points), np.column_stack(draws)
    result = simultaneous_envelope(point, boot, alpha)
    result.update(point=point, labels=labels, draw_sha256=drawhash, family_size=len(point),
                  n_boot=n_boot, span=span, alpha=alpha)
    return result


def choose_offset(costs, risk_upper, levels):
    """No historical fallback: one level shared by all fixed instances."""
    c, upper = np.asarray(costs, float), np.asarray(risk_upper, float)
    if c.shape != upper.shape or c.ndim != 2 or c.shape[1] != len(levels):
        raise ValueError("Invalid historical choice grid")
    feasible = [q for q in range(len(levels)) if np.all(upper[:, q] <= .1)]
    return min(feasible, key=lambda q: (c[:, q].mean(), -levels[q])) if feasible else None
