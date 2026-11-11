"""Independent receipt-based action reconstruction for NV_MAJOR_Z.

This module imports neither the production no-veto kernel nor gate predictor.
The caller provides frozen historical model receipts and matched endpoint arrays.
"""
from __future__ import annotations
from collections.abc import Mapping
import numpy as np

TIMES={'C':(29384,29816),'E':(29816,30240),'D':(30240,10**12)}

def independent_no_veto(bank,receipts):
    a=np.asarray(bank['anchors'],dtype=np.int64)
    safe=np.asarray(bank['safe'],dtype=np.float64);cost=np.asarray(bank['cost'],dtype=np.float64)
    if safe.shape!=cost.shape or safe.ndim!=2 or safe.shape[0]!=len(a):raise ValueError('Endpoint grid mismatch')
    action=safe.copy();chosen={}
    for snap,(lo,hi) in TIMES.items():
        r=receipts[snap]
        if r['episode_start']!=lo or r['enabled_anchor']!=lo:raise ValueError('Historical snapshot clock differs')
        if r.get('fallback_to_safe') or r['status']=='UNTRAINED_ANCHOR':
            alpha=0.;leaf=None;support=0
        else:
            leaf=min((int(k) for k in r['leaf_stats']),key=lambda k:(-int(r['leaf_stats'][str(k)]['n_cells']),k))
            support=int(r['leaf_stats'][str(leaf)]['n_cells'])
            alpha=float(r['leaf_alphas'][str(leaf)])
        if not np.isfinite(alpha) or alpha<0 or alpha>1:raise ValueError('Frozen coefficient invalid')
        # Reconstruct by issue row rather than the production boolean segments.
        for i,t in enumerate(a):
            if lo<=t<hi:
                action[i]=np.maximum(safe[i]+alpha*(cost[i]-safe[i]),0.)
        chosen[snap]=dict(alpha=alpha,leaf_id=leaf,historical_cells=support)
    return action,chosen

def independent_daily(action,shortfall,mask,anchors):
    a=np.asarray(anchors,dtype=np.int64);rows=[];counts=[];days=np.unique(a//144)
    for day in days:
        use=a//144==day;valid=np.asarray(mask[use],dtype=bool)
        r=np.asarray(action[use])[valid];s=np.asarray(shortfall[use])[valid]
        u=np.maximum(s-r,0.)/6.
        rows.append([float(np.sum(r/6.+10.*u)),float(np.sum(r/6.)),float(np.sum(u)),int(np.count_nonzero(s>r))])
        counts.append(int(valid.sum()))
    return np.asarray(rows),np.asarray(counts),days
