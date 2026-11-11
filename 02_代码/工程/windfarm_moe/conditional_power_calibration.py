"""Finite calibration controls and fair feature interfaces for the WTB study."""
from __future__ import annotations
import numpy as np
from windfarm_moe.dynamic_addback import past_dynamics


def feature_sets(data,anchors,base,full,g):
    extras=past_dynamics(data,anchors)
    compact=np.column_stack((base,extras['level'],extras['trend'],extras['path'])).astype(np.float32)
    # Apply exactly the same causal dynamic definitions to the measured angle.
    angle_view=np.array(data[:,:, [0,3,2,1]],copy=False)
    pitch=past_dynamics(angle_view,anchors)
    z=np.column_stack((pitch['level'][:,0],pitch['trend'],pitch['path'])).astype(np.float32)
    context=np.column_stack((base[:,:4],extras['wind'].reshape(-1),extras['level'],extras['trend'],extras['path'])).astype(np.float32)
    score_input=np.column_stack((base,g,extras['level'],extras['trend'],extras['path'])).astype(np.float32)
    return {'COMPACT':compact,'FULL':full,'COMPACT_G':score_input,
            'COMPACT_Z':np.column_stack((compact,z)),'FULL_Z':np.column_stack((full,z))}, {
            'COMPACT':context,'FULL':context,'COMPACT_G':np.column_stack((context,g)),
            'COMPACT_Z':np.column_stack((context,z)),'FULL_Z':np.column_stack((context,z))}, extras


class GroupOffset:
    """Historical-only quantile offsets with a declared global shrinkage fallback."""
    def fit(self,power,wind,change,residual):
        p,w,c,y=map(lambda a:np.asarray(a,dtype=float),(power,wind,change,residual))
        if p.shape!=w.shape or p.shape!=c.shape or p.shape!=y.shape or not np.isfinite(y).all() or not len(y):
            raise ValueError('Invalid calibration rows')
        self.global_=float(np.quantile(y,.9,method='higher'))
        self.p_edges_=np.unique(np.quantile(p[np.isfinite(p)],[.25,.5,.75])) if np.isfinite(p).any() else np.array([])
        self.w_edges_=np.unique(np.quantile(w[np.isfinite(w)],[.25,.5,.75])) if np.isfinite(w).any() else np.array([])
        groups=self.groups(p,w,c);self.offsets_={}
        for k in np.unique(groups):
            if k<0:continue
            mask=groups==k;n=int(mask.sum())
            if n<50:continue
            q=float(np.quantile(y[mask],.9,method='higher'))
            self.offsets_[int(k)]=n/(n+200)*q+200/(n+200)*self.global_
        return self

    def groups(self,power,wind,change):
        p,w,c=map(np.asarray,(power,wind,change))
        category=np.ones(c.shape,dtype=np.int64)
        category[c<-150]=0;category[c>150]=2;category[~np.isfinite(c)]=3
        gid=(np.searchsorted(self.p_edges_,p,side='right')*(len(self.w_edges_)+1)+np.searchsorted(self.w_edges_,w,side='right'))*4+category
        gid[~np.isfinite(p)|~np.isfinite(w)]=-1
        return gid

    def predict(self,power,wind,change):
        groups=self.groups(power,wind,change)
        return np.asarray([self.offsets_.get(int(k),self.global_) for k in groups])


def choose_cost(table,keys):
    """One shared historical list order; no outcome or risk-based removal."""
    if not keys or any(k not in table or not np.isfinite(table[k]) for k in keys):
        raise ValueError('Incomplete historical selection table')
    return min(keys,key=lambda k:(table[k],keys.index(k)))


def choose_pitch(table,zkeys,power_key):
    """Exact power-program alias protects the option to ignore new pitch."""
    if power_key not in table:raise ValueError('Missing power winner')
    return choose_cost(table,[power_key,*zkeys])
