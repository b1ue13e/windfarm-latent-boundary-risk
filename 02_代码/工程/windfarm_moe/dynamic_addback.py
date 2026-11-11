"""Causal information add-back probes; no model fitting in this module."""
from __future__ import annotations

import numpy as np


def past_dynamics(data: np.ndarray, anchors: np.ndarray) -> dict[str, np.ndarray]:
    """Use only fixed endpoints at or before each issue; never search past NaNs."""
    data, anchors = np.asarray(data), np.asarray(anchors)
    if data.ndim != 3 or data.shape[2] != 4 or anchors.ndim != 1 or anchors.dtype.kind not in 'iu':
        raise ValueError('Expected time/node/WPQP array and integer issue indices')
    if np.any(anchors < 6) or np.any(anchors >= len(data)):
        raise ValueError('Incomplete fixed past window or invalid issue')
    p = np.asarray(data[anchors[:, None] - np.arange(5, -1, -1), :, 1], dtype=np.float64)
    p = p.transpose(0, 2, 1)  # issue,node,event-time
    current = np.asarray(data[anchors, :, 1:3], dtype=np.float64)
    endpoint = np.asarray(data[anchors - 6, :, 1], dtype=np.float64)
    delta1, delta6 = p[..., -1] - p[..., -2], p[..., -1] - endpoint
    valid = np.isfinite(p).all(axis=-1)
    x = np.arange(6, dtype=np.float64) - 2.5
    safe = np.where(np.isfinite(p), p, 0.0)
    slope = ((safe - safe.mean(axis=-1, keepdims=True)) * x).sum(axis=-1) / (x @ x)
    detrended = safe - safe.mean(axis=-1, keepdims=True) - slope[..., None] * x
    residual_std = np.sqrt(np.mean(detrended**2, axis=-1))
    drawdown = np.maximum.accumulate(safe, axis=-1) - safe
    maximum_drawdown = drawdown.max(axis=-1)
    changes = np.diff(p, axis=-1)
    run = np.zeros(p.shape[:2], dtype=np.float64)
    trailing = np.ones(p.shape[:2], dtype=bool)
    for j in range(4, -1, -1):
        trailing &= np.isfinite(changes[..., j]) & (changes[..., j] < 0)
        run += trailing
    for value in (slope, residual_std, maximum_drawdown, run):
        value[~valid] = np.nan
    trend = np.stack((delta1, delta6, slope), axis=-1)
    path = np.stack((residual_std, maximum_drawdown, run), axis=-1)
    group_valid = np.isfinite(delta6) & np.isfinite(changes[..., -3:]).all(axis=-1)
    group = np.full(p.shape[:2], 2, dtype=np.int8)  # 0 other,1 persistent down,2 unknown
    group[group_valid] = ( (delta6 < -150) & (changes[..., -3:] < 0).all(axis=-1))[group_valid]
    return dict(level=current.reshape(-1, 2).astype(np.float32),
                trend=trend.reshape(-1, 3).astype(np.float32),
                path=path.reshape(-1, 3).astype(np.float32), group=group,
                wind=np.asarray(data[anchors, :, 0]), pitch=np.asarray(data[anchors, :, 3]))


def matrices(base: np.ndarray, full: np.ndarray, g: np.ndarray, risk: np.ndarray,
             extra: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Keep nested feature sets and current P/Q in all indicated configurations."""
    n = len(base)
    if len(full) != n or np.asarray(g).shape != (n,) or np.asarray(risk).shape != (n,):
        raise ValueError('Row alignment failure')
    level, trend, path = (extra[k] for k in ('level', 'trend', 'path'))
    if any(len(a) != n for a in (level, trend, path)):
        raise ValueError('Feature alignment failure')
    z = np.asarray(g, dtype=np.float32)[:, None]
    pq = np.column_stack((base, level))
    gpq = np.column_stack((base, z, level))
    return dict(A=base, FULL=full, G=np.column_stack((base,z)),
                G_P=np.column_stack((base,z,level[:, :1])), G_PQ=gpq,
                G_PQ_T=np.column_stack((gpq,trend)),
                G_PQ_TV=np.column_stack((gpq,trend,path)), PQ=pq,
                PQ_TV=np.column_stack((pq,trend,path)),
                RISK=np.column_stack((base,risk)),
                TRUE_PQ=np.column_stack((pq,extra['pitch'].reshape(-1))),
                FULL_G=np.column_stack((full,z)))


def clock_qualified(issues: np.ndarray, point_fit_end: int, horizon: int = 6,
                    age: int = 6, release: int = 1) -> np.ndarray:
    """Point fit target releases must strictly precede nominal publication."""
    final_release = point_fit_end - 1 + horizon + age + release
    return np.asarray(issues) - age > final_release


def daily(shortfall: np.ndarray, actions: np.ndarray, valid: np.ndarray,
          anchors: np.ndarray, groups: np.ndarray) -> dict[str, np.ndarray]:
    """Full day calendar, disjoint groups, numerator/count accounting."""
    s,r,m=np.asarray(shortfall),np.asarray(actions),np.asarray(valid,dtype=bool)
    if s.shape != r.shape or s.shape != m.shape or groups.shape != s.shape:
        raise ValueError('Accounting population mismatch')
    if not np.isfinite(s[m]).all() or not np.isfinite(r[m]).all() or np.any(s[m]<0) or np.any(r[m]<0):
        raise ValueError('Invalid scored shortfall/action')
    ids=np.asarray(anchors)//144
    days=np.arange(ids.min(),ids.max()+1)
    masks=[m]+[m & (groups==k) for k in (0,1,2)]
    result={'days':days}
    for name,mask in zip(('all','other','down','unknown'),masks):
        u=np.where(mask,np.maximum(s-r,0)/6,0)
        reserve=np.where(mask,r/6,0)
        v=mask & (s>r)
        for field,grid in [('N',mask),('R',reserve),('U',u),('C',reserve+10*u),('V',v)]:
            result[name+'__'+field]=np.asarray([grid[ids==d].sum(dtype=np.float64) for d in days])
    return result
