"""Delayed projected updates of the actual convex-mixture loss.

This is a developmental optimizer, not a risk guarantee. Strict event risk is
scored separately and is never replaced by averaged expert event indicators.
"""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class MixtureConfig:
    eta: float = .3
    schedule_power: float = .5
    severity_step: float = 0.
    cost_scale: float = 100.
    proximity_strength: float = 0.


def project_simplex(values):
    v=np.asarray(values,dtype=np.float64)
    if v.ndim!=2 or not v.shape[1] or not np.isfinite(v).all():
        raise ValueError('Expected finite candidate-by-expert vectors')
    # Translation leaves a simplex projection invariant and avoids summing a
    # large common component. This is numerical conditioning, not clipping.
    v=v-v.max(axis=1,keepdims=True)
    u=np.sort(v,axis=1)[:,::-1]
    css=np.cumsum(u,axis=1)-1
    active=u-css/np.arange(1,v.shape[1]+1)>0
    rho=active.sum(axis=1)-1
    theta=css[np.arange(len(v)),rho]/(rho+1)
    w=np.maximum(v-theta[:,None],0)
    w/=w.sum(axis=1,keepdims=True)
    if not np.isfinite(w).all():raise FloatingPointError('Projection overflow')
    return w


def actual_gradient(x, y, action, *, cost_scale=100., multipliers=None, node_count=None):
    """Subgradient at the actual past action, with zero chosen at its kink.

    x[N,K], y[N], action[C,N]. Dividing by fixed node_count preserves the
    original valid-cell weighting when a past issue has missing targets.
    """
    n=len(y) if node_count is None else node_count
    if n<=0:raise ValueError('Positive fixed population required')
    delta=np.asarray(y)[None,:]-action
    slope=np.where(delta>0,-9.,np.where(delta<0,1.,0.))/(6*cost_scale)
    if multipliers is not None:
        slope=slope-np.asarray(multipliers)[:,None]*(delta>0)*10/(6*cost_scale)
    return (slope@x)/n


def run_mixture(x,y,mask,anchors,configs,initial_weights,*,score=True,return_actions=False):
    """Run a new matched episode; only episode issues can supply feedback.

    Warm-start weights must have been fitted on labels strictly mature before
    the first issue. No action is retroactively assigned to an earlier issue.
    Each update uses its stored past action and source_anchor+7<current_anchor.
    """
    x=np.asarray(x,dtype=np.float64);y=np.asarray(y,dtype=np.float64)
    m=np.asarray(mask);a=np.asarray(anchors);configs=list(configs)
    if (x.ndim!=3 or x.shape[1]<1 or y.shape!=x.shape[:2] or m.shape!=y.shape
        or m.dtype!=bool or a.shape!=(len(x),) or a.dtype.kind not in 'iu'
        or np.any(a<0) or np.any(a[1:]<=a[:-1]) or not np.isfinite(x).all() or np.any(x<0)):
        raise ValueError('Invalid expert, target, mask or clock arrays')
    c=len(configs);t,n,k=x.shape
    if not c:raise ValueError('At least one frozen configuration is required')
    w=np.asarray(initial_weights,dtype=float).copy()
    if w.ndim==1:w=np.broadcast_to(w,(c,k)).copy()
    if w.shape!=(c,k) or not np.isfinite(w).all() or np.any(w<0) or not np.allclose(w.sum(axis=1),1,atol=1e-12,rtol=0):
        raise ValueError('Invalid shared warm-start weights')
    for cfg in configs:
        if (isinstance(cfg.proximity_strength,(bool,np.bool_)) or not np.isfinite([cfg.eta,cfg.schedule_power,cfg.severity_step,cfg.cost_scale,cfg.proximity_strength]).all()
            or cfg.eta<0 or cfg.severity_step<0 or cfg.schedule_power not in (0.,.5,1.) or cfg.cost_scale!=100. or cfg.proximity_strength!=0.):
            raise ValueError('Invalid frozen numerical configuration')
    eta=np.array([cfg.eta for cfg in configs]);power=np.array([cfg.schedule_power for cfg in configs])
    gamma=np.array([cfg.severity_step for cfg in configs]);lam=np.zeros(c)
    days=np.unique(a//144);day_index={int(d):i for i,d in enumerate(days)}
    ledger=np.zeros((c,len(days),4));counts=np.zeros(len(days),dtype=np.int64)
    saved=np.empty((c,t,n)) if return_actions else None
    pending={};cursor=0;last_release=-1;trace=np.full(t,-1,dtype=np.int64)
    maximum_lambda=np.zeros(c);updates=0
    for i,now in enumerate(a):
        while cursor<i and int(a[cursor])+7<int(now):
            valid=m[cursor];count=int(valid.sum())
            previous=pending.pop(cursor)
            last_release=int(a[cursor])+7
            if count:
                yy=y[cursor,valid];xx=x[cursor,valid]
                if not np.isfinite(yy).all() or np.any(yy<0):raise ValueError('Invalid matured target')
                actual=previous[:,valid]
                factor=(1+(int(a[cursor])-int(a[0]))/144.)**(-power)
                gradient=actual_gradient(xx,yy,actual,multipliers=lam,node_count=n)
                active=eta>0
                if active.any():
                    w[active]=project_simplex(w[active]-(eta[active]*factor[active])[:,None]*gradient[active])
                actual_u=np.maximum(yy[None,:]-actual,0).sum(axis=1)/(6*n)
                reference_u=np.maximum(yy-xx[:,0],0).sum()/(6*n)
                lam=np.maximum(0,lam+gamma*factor*10*(actual_u-reference_u)/100.)
                if not np.isfinite(lam).all():raise FloatingPointError('Nonfinite severity multiplier')
                maximum_lambda=np.maximum(maximum_lambda,lam);updates+=1
            cursor+=1
        current=np.sum(x[i][None,:,:]*w[:,None,:],axis=-1)
        if not np.isfinite(current).all():raise FloatingPointError('Nonfinite actual mixture action')
        pending[i]=current.copy();trace[i]=last_release
        if saved is not None:saved[:,i]=current
        if score:
            di=day_index[int(now)//144];valid=m[i];count=int(valid.sum());counts[di]+=count
            if count:
                yy=y[i,valid]
                if not np.isfinite(yy).all() or np.any(yy<0):raise ValueError('Invalid scored target')
                rr=current[:,valid]/6;uu=np.maximum(yy[None,:]-current[:,valid],0)/6
                ledger[:,di,0]+=np.sum(rr+10*uu,axis=1);ledger[:,di,1]+=rr.sum(axis=1)
                ledger[:,di,2]+=uu.sum(axis=1);ledger[:,di,3]+=(yy[None,:]>current[:,valid]).sum(axis=1)
    return dict(actions=saved,ledger=ledger,counts=counts,days=days,metadata=dict(
        configs=[cfg.__dict__ for cfg in configs],final_weights=w.tolist(),
        final_lambda_u=lam.tolist(),maximum_lambda_u=maximum_lambda.tolist(),
        release_trace=trace.tolist(),feedback_updates=updates,pending_rows=t-cursor,
        feedback_rule='source_anchor+7<decision_anchor',zero_kink_subgradient=True,
        node_weighting='valid-cell sum / fixed node count',cost_scale=100.,
        strict_V_is_not_optimized_or_certified=True,episode_restart=True))


def run_matched_ew(x,y,mask,anchors,initial_weights,*,eta=10.,discount=.95):
    """Expert-loss control with an exact shared warm start.

    No log/exp round trip is applied before the first feedback. This separate
    entry preserves the old expert-loss equations without rewriting old code
    or giving the fixed and adaptive controls different initial actions.
    """
    x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float);m=np.asarray(mask);a=np.asarray(anchors)
    if (x.ndim!=3 or y.shape!=x.shape[:2] or m.shape!=y.shape or m.dtype!=bool
        or a.shape!=(len(x),) or a.dtype.kind not in 'iu' or np.any(a<0)
        or np.any(a[1:]<=a[:-1]) or not np.isfinite(x).all() or np.any(x<0)
        or not np.isfinite([eta,discount]).all() or eta<0 or not 0<discount<=1):
        raise ValueError('Invalid matched-EW episode')
    prior=np.asarray(initial_weights,dtype=float).copy()
    if prior.shape!=(x.shape[-1],) or np.any(prior<=0) or abs(prior.sum()-1)>1e-12:
        raise ValueError('Shared EW prior must have full support')
    w=prior.copy();scores=np.zeros(len(w));actions=np.empty(x.shape[:2]);cursor=0;observed=False
    for i,now in enumerate(a):
        if i:scores*=discount**(int(now)-int(a[i-1]))
        changed=False
        while cursor<i and int(a[cursor])+7<int(now):
            valid=m[cursor]
            if valid.any():
                yy=y[cursor,valid];xx=x[cursor,valid]
                if not np.isfinite(yy).all():raise ValueError('Invalid mature EW target')
                costs=np.sum((xx+10*np.maximum(yy[:,None]-xx,0))/6,axis=0)/x.shape[1]
                scores+=discount**(int(now)-int(a[cursor])-7)*costs/100.;changed=True;observed=True
            cursor+=1
        if changed or (i and observed):
            penalty=np.minimum(eta*(scores-scores.min()),700.)
            raw=prior*np.exp(-penalty);w=raw/raw.sum()
        actions[i]=np.sum(x[i]*w,axis=-1)
    return actions
