"""Nonnegative residual actions above a causal protection anchor.

The original target and scientific thresholds are unchanged. For optimization
only, C(b+v,S)=b/6+C(v,max(S-b,0)) when v>=0. Scoring always uses original S.
"""
import numpy as np


def residual_experts(experts,baseline):
    x=np.asarray(experts);b=np.asarray(baseline)
    if x.shape[:2]!=b.shape or not np.isfinite(b).all() or np.any(b<0):
        raise ValueError('Invalid causal baseline')
    delta=np.maximum(x-b[:,:,None],0)
    return np.concatenate([np.zeros((*b.shape,1)),delta],axis=-1)


def guarded_action(baseline,increments,weights):
    # Addition of a nonnegative increment preserves >=b even at strict floating
    # boundaries; summing full (b+delta) experts could lose this by one ulp.
    increment=np.sum(increments*np.asarray(weights),axis=-1)
    if np.any(increment<0) or not np.isfinite(increment).all():raise ValueError('Invalid nonnegative residual')
    result=np.asarray(baseline)+increment
    if np.any(result<baseline):raise FloatingPointError('Protection floor lost')
    return result
