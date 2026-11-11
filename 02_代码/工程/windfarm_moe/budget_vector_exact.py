"""Vectorized binary64 mappings with exact limb sums and exact score totals.

This is an equivalent implementation candidate, not a new mapping or estimator.
Every coefficient still comes from the original exact formula and tie rule.
"""
from dataclasses import dataclass
from fractions import Fraction as F
import hashlib
import math
import numpy as np

from .budget_diagnostic_core import BUDGET_PRECISION, PairScore, MappedSetting, _f, _resolved, _shift_root


def exact_sum(values,weights,mask=None):
    """Exact nonnegative binary64 sum via 26/27-bit limbs and exponent bins.

    Each bincount addition is an integer <=2**53 and therefore exactly represented.
    The dynamic bound is checked *before* multiplication. Large-weight boundary
    fixtures fall back to scalar rationals, never to approximate accumulation.
    """
    values=np.asarray(values,dtype=np.float64);w=np.asarray(weights,dtype=np.int64)
    take=w>0
    if mask is not None:take &= np.asarray(mask,dtype=bool)
    a=values[take];w=w[take]
    if not len(a):return F()
    if not np.isfinite(a).all() or np.any(a<0):raise ValueError('Exact sum requires finite nonnegative values')
    n=sum(map(int,w)) if int(w.max())*len(w)>2**63-1 else int(w.sum())
    if n*((1<<27)-1)>2**53:
        return sum((F.from_float(float(x))*int(v) for x,v in zip(a,w)),F())
    bits=a.view(np.uint64)
    exponent=((bits>>52)&2047).astype(np.int64)
    mantissa=(bits&((1<<52)-1))|np.where(exponent>0,np.uint64(1<<52),np.uint64(0))
    low=(mantissa&((1<<26)-1)).astype(np.int64)*w
    high=(mantissa>>26).astype(np.int64)*w
    lo=np.bincount(exponent,weights=low.astype(float),minlength=2048)
    hi=np.bincount(exponent,weights=high.astype(float),minlength=2048)
    total=F()
    for raw in np.flatnonzero((lo!=0)|(hi!=0)):
        integer=int(lo[raw])+(int(hi[raw])<<26)
        power=int(raw)-1075 if raw else -1074
        total += F(integer<<power) if power>=0 else F(integer,1<<(-power))
    return total


def _above_value(values,threshold):
    rounded=float(threshold)
    result=values>rounded
    equal=values==rounded
    if equal.any():result[equal]=F.from_float(rounded)>threshold
    return result


@dataclass
class PreparedActions:
    values: np.ndarray
    order: np.ndarray
    last_weight_key: bytes | None = None
    last_budget: F | None = None

    @classmethod
    def make(cls,values):
        a=np.array(values,dtype=np.float64,copy=True)
        if a.ndim!=1:raise ValueError('One-dimensional actions required')
        a.flags.writeable=False
        order=np.argsort(a,kind='stable');order.flags.writeable=False
        return cls(a,order)

    def budget(self,w):
        key=hashlib.sha256(memoryview(np.ascontiguousarray(w)).cast('B')).digest()
        if key!=self.last_weight_key:
            self.last_budget=exact_sum(self.values,w)/6;self.last_weight_key=key
        return self.last_budget


@dataclass(frozen=True)
class VectorMapping:
    status: str
    method: str
    source_actions: np.ndarray
    weights: np.ndarray
    budget: F
    base_budget: F | None = None
    coefficient: float | None = None
    ideal_coefficient: F | None = None
    actions: np.ndarray | None = None
    residual: F | None = None
    action_error: F | None = None  # Certified upper bound, not an exact L1 value.
    neighbors: tuple = ()
    branch: str = ''

    @property
    def supported(self):return self.status in ('SUPPORTED','IDENTITY','ZERO_BUDGET')
    @property
    def n_weight(self):return int(self.weights.sum())
    @property
    def action_error_kind(self):return 'CERTIFIED_L1_UPPER_BOUND'


def _root(prepared,w,b):
    a=prepared.values
    order=prepared.order[w[prepared.order]>0][::-1]
    r=a[order];v=w[order]
    try:
        with np.errstate(over='ignore',invalid='ignore',divide='ignore'):
            prefix=np.cumsum(r*v);count=np.cumsum(v)
            candidates=(float(6*b)-prefix)/count
            next_value=np.r_[r[1:],-np.inf]
            valid=(r+candidates>0)&(next_value+candidates<=0)
        indices=np.flatnonzero(valid)
        cguess=float(candidates[indices[0]]) if len(indices) else float(6*(b-prepared.budget(w))/int(w.sum()))
    except OverflowError:
        cguess=float(6*(b-prepared.budget(w))/int(w.sum()))
    active=(a+cguess>0)&(w>0)
    for _ in range(64):
        if not active.any():break
        coefficient=(6*b-exact_sum(a,w,active))/int(w[active].sum())
        actual=_above_value(a,-coefficient)&(w>0)
        if np.array_equal(active,actual):return coefficient
        active=actual
    # Fixed outcome-free fallback to the preserved exact active-set formula.
    return _shift_root(a,tuple(map(int,w)),b)


def _weights(values):
    raw=np.asarray(values)
    if raw.ndim!=1 or raw.dtype.kind not in 'iuf' or not np.isfinite(raw).all() or np.any(raw<0) \
       or np.any(raw!=np.floor(raw)) or np.any(raw>np.iinfo(np.int64).max):
        raise ValueError('Finite nonnegative integer weights required')
    result=raw.astype(np.int64)
    if int(result.max(initial=0))*len(result)>np.iinfo(np.int64).max and sum(map(int,result))>np.iinfo(np.int64).max:
        raise ValueError('Weight total exceeds the vector integer domain')
    return result


def _ideal_bounds(a,c,method):
    rounded=float(c)
    lo=float(np.nextafter(rounded,-np.inf));hi=float(np.nextafter(rounded,np.inf))
    with np.errstate(over='ignore',under='ignore',invalid='ignore'):
        if method=='M':
            lower=np.maximum(np.nextafter(a*max(lo,0.),-np.inf),0.)
            upper=np.nextafter(a*hi,np.inf)
            lower[a==0]=0.;upper[a==0]=0.
        else:
            lower=np.maximum(np.nextafter(a+lo,-np.inf),0.)
            upper=np.maximum(np.nextafter(a+hi,np.inf),0.)
    return lower,upper


def budget_map_fast(prepared,budget,method,weights):
    a=prepared.values;b=F(budget)
    try:w=_weights(weights)
    except ValueError:return VectorMapping('SOURCE_INVALID',method,a,np.zeros(len(a),dtype=np.int64),b)
    n=int(w.sum());pos=w>0
    if method not in ('M','S'):raise ValueError('Unknown mapping')
    if w.shape!=a.shape or np.any(w<0) or b<0 or not np.isfinite(a[pos]).all() or np.any(a[pos]<0):
        return VectorMapping('SOURCE_INVALID',method,a,w,b)
    if n==0:return VectorMapping('UNDEFINED_POPULATION',method,a,w,b)
    base=prepared.budget(w)
    if b==0:
        coef=0. if method=='M' else -float(a[pos].max())
        out=np.zeros_like(a);out.flags.writeable=False
        return VectorMapping('ZERO_BUDGET',method,a,w,b,base,coef,F.from_float(coef),out,F(),F(),(), 'ZERO_BUDGET')
    if b==base:
        out=a.copy();out.flags.writeable=False;coef=1. if method=='M' else 0.
        return VectorMapping('IDENTITY',method,a,w,b,base,coef,F.from_float(coef),out,F(),F(),(), 'POSITIVE_IDENTITY')
    if method=='M' and base==0:return VectorMapping('UNSUPPORTED_MULTIPLICATIVE',method,a,w,b,base)
    try:
        c=b/base if method=='M' else 6*b/n if base==0 else _root(prepared,w,b)
        rounded=float(c)
        def candidate(coef):
            if not math.isfinite(coef) or (method=='M' and coef<=0):return None
            out=np.zeros_like(a)
            with np.errstate(over='ignore',invalid='ignore'):
                out[pos]=a[pos]*coef if method=='M' else np.maximum(a[pos]+coef,0.)
            if not np.isfinite(out[pos]).all():return None
            residual=(exact_sum(out,w)/6-b)/n
            if abs(residual)>BUDGET_PRECISION:return None
            out.flags.writeable=False
            return residual,out
        choices=[]
        for coef in sorted({rounded,float(np.nextafter(rounded,-np.inf)),float(np.nextafter(rounded,np.inf))}):
            found=candidate(coef)
            if found:choices.append((abs(found[0]),coef,*found))
        if not choices:raise ArithmeticError('No canonical float64 representation')
        _,coef,residual,out=min(choices,key=lambda x:(x[0],x[1]))
        neighbors=[]
        for v in (float(np.nextafter(coef,-np.inf)),float(np.nextafter(coef,np.inf))):
            found=candidate(v)
            if found:neighbors.append(found[1])
        low,high=_ideal_bounds(a,c,method)
        bound=(exact_sum(high,w)-exact_sum(low,w))/(6*n) if np.isfinite(high[pos]).all() else None
        return VectorMapping('SUPPORTED',method,a,w,b,base,coef,c,out,residual,bound,tuple(neighbors),
                             'ZERO_BASE_SHIFT' if base==0 else 'GENERAL')
    except (ValueError,ArithmeticError,OverflowError):
        return VectorMapping('SOLVER_NUMERIC_UNRESOLVED',method,a,w,b,base)


def map_pair_fast(p,z,anchor,method,weights,prepared=None):
    if anchor not in ('P','Z') or method not in ('M','S'):raise ValueError('Unknown fixed setting')
    arms=prepared or (PreparedActions.make(p),PreparedActions.make(z))
    try:w=_weights(weights)
    except ValueError:
        bad=VectorMapping('SOURCE_INVALID',method,arms[0].values,np.zeros(len(p),dtype=np.int64),F())
        return MappedSetting('A'+anchor+'_'+method,bad,bad)
    try:budget=arms[0 if anchor=='P' else 1].budget(w)
    except ValueError:
        bad=VectorMapping('SOURCE_INVALID',method,arms[0].values,w,F())
        return MappedSetting('A'+anchor+'_'+method,bad,bad)
    return MappedSetting('A'+anchor+'_'+method,*(budget_map_fast(arm,budget,method,w) for arm in arms))


def _ideal_event(target,mapping):
    a=mapping.source_actions;w=mapping.weights;c=mapping.ideal_coefficient
    if mapping.status in ('IDENTITY','ZERO_BUDGET'):return (target>mapping.actions)&(w>0)
    low,high=_ideal_bounds(a,c,mapping.method)
    result=(target>high)&(w>0)
    uncertain=(target>low)&(target<=high)&(w>0)
    # target<=lower is certainly not a strict event, including exact zero.
    for i in np.flatnonzero(uncertain):
        source=F.from_float(float(a[i]));s=F.from_float(float(target[i]))
        ideal=source*c if mapping.method=='M' else max(source+c,F())
        result[i]=s>ideal
    return result


def score_pair_fast(shortfalls,p,z):
    if not p.supported or not z.supported:
        states=(p.status,z.status)
        state='NUMERIC_UNRESOLVED' if 'SOLVER_NUMERIC_UNRESOLVED' in states else 'UNDEFINED_POPULATION' if 'UNDEFINED_POPULATION' in states else 'UNSUPPORTED_MAPPING' if 'UNSUPPORTED_MULTIPLICATIVE' in states else 'SOURCE_UNAVAILABLE'
        return PairScore(U_state=state,V_state=state,reasons=states)
    if p.budget!=z.budget or not np.array_equal(p.weights,z.weights):return PairScore()
    target=np.asarray(shortfalls,dtype=np.float64);w=p.weights;n=p.n_weight;pos=w>0
    if target.shape!=p.actions.shape or not np.isfinite(target[pos]).all() or np.any(target[pos]<0):return PairScore()
    actual=[];ideals=[];sensitive=False
    for mapping in (p,z):
        event=(target>mapping.actions)&pos;ideal_event=_ideal_event(target,mapping)
        sensitive |= bool(np.any(event!=ideal_event))
        sensitive |= any(np.any(((target>x)&pos)!=event) for x in mapping.neighbors)
        u=(exact_sum(target,w,event)-exact_sum(mapping.actions,w,event))/(6*n)
        v=F(int(w[event].sum()),n)
        if mapping.status in ('IDENTITY','ZERO_BUDGET'):ui=u
        else:
            a=mapping.source_actions;c=mapping.ideal_coefficient
            if mapping.method=='M':
                ideal_total=c*exact_sum(a,w,ideal_event)
            else:
                active=ideal_event&_above_value(a,-c)
                ideal_total=exact_sum(a,w,active)+c*int(w[active].sum())
            ui=(exact_sum(target,w,ideal_event)-ideal_total)/(6*n)
        vi=F(int(w[ideal_event].sum()),n)
        actual.append((u,v));ideals.append((ui,vi))
    du,dv=actual[1][0]-actual[0][0],actual[1][1]-actual[0][1]
    iu,iv=ideals[1][0]-ideals[0][0],ideals[1][1]-ideals[0][1]
    u,v=float(du),float(dv);eu,ev=abs(F.from_float(u)-iu),abs(F.from_float(v)-iv)
    return PairScore(u,v,eu,ev,iu,iv,'DEFINED' if _resolved(u,eu) else 'NUMERIC_UNRESOLVED',
        'DEFINED' if not sensitive and _resolved(v,ev) else 'NUMERIC_UNRESOLVED',float(actual[0][1]),float(actual[1][1]))
