"""Full-population cutting-plane solver for a fixed convex reserve baseline.

This is a numerical backend for the already specified optimization problem,
not a new forecasting or risk-control method. Master LP lower bounds and actual
feasible upper bounds are both retained; a resource limit is never optimality.
"""
from __future__ import annotations
from dataclasses import dataclass
import time
import numpy as np
from scipy.optimize import linprog
from threadpoolctl import threadpool_limits


@dataclass(frozen=True)
class BundleResult:
    weights: np.ndarray
    status: str
    optimal: bool
    objective: float
    lower_bound: float
    gap: float
    mean_uncovered_power: float
    uncovered_cap: float | None
    iterations: int
    elapsed_seconds: float
    numerical_tolerance: float


def fit_bundle(x, y, *, uncovered_cap=None, time_limit=30., max_iter=1000,
               relative_tolerance=1e-7):
    x=np.asarray(x,dtype=np.float64);y=np.asarray(y,dtype=np.float64)
    if (x.ndim!=2 or x.shape[0]==0 or x.shape[1]==0 or y.shape!=(len(x),)
        or not np.isfinite(x).all() or not np.isfinite(y).all()
        or np.any(x<0) or np.any(y<0)):
        raise ValueError('Expected complete finite nonnegative historical rows')
    if (not np.isfinite(time_limit) or time_limit<=0 or max_iter<1
        or not np.isfinite(relative_tolerance) or relative_tolerance<=0):
        raise ValueError('Invalid numerical budget')
    if uncovered_cap is not None and (not np.isfinite(uncovered_cap) or uncovered_cap<0):
        raise ValueError('Invalid historical uncovered cap')
    start=time.monotonic();n,k=x.shape
    cost_planes=[];cap_planes=[];best=None;upper=np.inf;lower=0.;best_h=np.inf
    feasible_vertices=[]
    mean_x=x.mean(axis=0)
    def evaluate(w):
        r=x@w;z=np.maximum(y-r,0);h=float(z.mean())
        f=float((r+10*z).mean()/6)
        gh=-(x.T@(y>r))/n
        g=(mean_x+10*gh)/6
        cost_planes.append(np.r_[g, f-g@w])
        if uncovered_cap is not None:cap_planes.append(np.r_[gh,h-gh@w])
        return f,h
    with threadpool_limits(limits=1):
        # Every single expert and the uniform mixture are feasible simplex points.
        for w in [*np.eye(k), np.full(k,1/k)]:
            f,h=evaluate(w)
            if (uncovered_cap is None or h<=uncovered_cap) and f<upper:
                best=w.copy();upper=f;best_h=h
            if uncovered_cap is not None and h<=uncovered_cap:
                feasible_vertices.append((h,w.copy()))
        if best is None:
            raise ValueError('No feasible initial vertex; this backend requires a cap-feasible reference expert')
        status='ITERATION_LIMIT';iterations=0
        for iterations in range(1,max_iter+1):
            remaining=time_limit-(time.monotonic()-start)
            if remaining<=0:status='TIME_LIMIT';break
            planes=np.asarray(cost_planes)
            A=np.c_[planes[:,:k],-np.ones(len(planes))];b=-planes[:,k]
            if cap_planes:
                cp=np.asarray(cap_planes)
                A=np.r_[A,np.c_[cp[:,:k],np.zeros(len(cp))]]
                b=np.r_[b,uncovered_cap-cp[:,k]]
            solved=linprog(np.r_[np.zeros(k),1.],A_ub=A,b_ub=b,
                A_eq=np.r_[np.ones(k),0.][None,:],b_eq=[1.],bounds=[(0.,1.)]*k+[(0.,None)],
                method='highs',options={'threads':1,'time_limit':remaining,'primal_feasibility_tolerance':1e-8,
                    'dual_feasibility_tolerance':1e-8})
            if not solved.success:status='MASTER_'+str(solved.status);break
            # A master optimum supplies a numerical lower bound, not field safety.
            lower=max(lower,float(solved.fun))
            raw=solved.x[:k]
            if np.min(raw)<-1e-8 or abs(raw.sum()-1)>1e-8:
                status='MASTER_NUMERIC_UNRESOLVED';break
            w=np.maximum(raw,0);w=w/w.sum()
            f,h=evaluate(w)
            if uncovered_cap is not None and h>uncovered_cap:
                # Keep an actual feasible upper bound, rather than accepting a
                # floating-point excess as a relaxed scientific constraint.
                anchor_h,anchor=min(feasible_vertices,key=lambda item:item[0])
                alpha0=((h-uncovered_cap)/(h-anchor_h)
                        if anchor_h<uncovered_cap else 1e-12)
                for alpha in sorted(set([min(1.,max(0.,alpha0)*(1+1e-6)+1e-12),
                        1e-10,1e-8,1e-6,1e-4,.01,.1,.5,1.])):
                    adjusted=(1-alpha)*w+alpha*anchor
                    adjusted=np.maximum(adjusted,0);adjusted/=adjusted.sum()
                    ah=float(np.maximum(y-x@adjusted,0).mean())
                    if ah<=uncovered_cap:
                        af=float(((x@adjusted)+10*np.maximum(y-x@adjusted,0)).mean()/6)
                        if af<upper:best=adjusted.copy();upper=af;best_h=ah
                        break
            # Tiny cap violations are not silently accepted as scientific gains.
            if (uncovered_cap is None or h<=uncovered_cap) and f<upper:
                best=w.copy();upper=f;best_h=h
            tol=relative_tolerance*max(1.,abs(upper))
            if lower>upper+tol:
                status='BOUND_CONTRADICTION';break
            if upper-lower<=tol:
                status='OPTIMAL_NUMERICAL_BOUNDS';break
    gap=max(0.,upper-lower)
    return BundleResult(best,status,status=='OPTIMAL_NUMERICAL_BOUNDS',upper,lower,gap,
        best_h,uncovered_cap,iterations,time.monotonic()-start,
        relative_tolerance*max(1.,abs(upper)))
