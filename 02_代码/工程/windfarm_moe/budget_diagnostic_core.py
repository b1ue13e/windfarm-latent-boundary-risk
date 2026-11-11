"""Pure V2 budget mappings and fail-closed states; no asset I/O or execution CLI.

Float64 actions follow the frozen mappings. Exact binary-input rational arithmetic
certifies roots, residuals and point errors. This correctness-first core has not
been benchmarked for a full real-action bootstrap; no statistical CI is made here.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction as F
import hashlib
import json
import math
from typing import Mapping

import numpy as np

SEEDS = (201, 202, 203, 204, 205)
COORDINATES = ('AP_M_U','AP_M_V','AP_S_U','AP_S_V','AZ_M_U','AZ_M_V','AZ_S_U','AZ_S_V')
BUDGET_PRECISION = F(1, 100_000_000)
N_BOOT = 20000
FAMILY_ID = 'BUDGET_EXPLORATORY_8'
ALPHA = .05


def _f(value):
    if isinstance(value,F):return value
    if isinstance(value,(int,np.integer)):return F(int(value))
    return F.from_float(float(value))


def _source(actions, weights):
    a = np.array(actions, dtype=np.float64, copy=True)
    if a.ndim != 1:
        raise ValueError('Expected one-dimensional scored actions')
    w = [1]*len(a) if weights is None else list(weights)
    if len(w) != len(a):
        raise ValueError('Weight shape mismatch')
    if any(not math.isfinite(float(x)) or float(x)<0 or int(x)!=x for x in w):
        raise ValueError('Weights must be finite nonnegative integers')
    w = tuple(int(x) for x in w)
    positive = np.asarray([x>0 for x in w])
    if not np.isfinite(a[positive]).all() or np.any(a[positive]<0):
        raise ValueError('Invalid positive-weight source action')
    return a, w, positive


def _sum_budget(a, w):
    return sum((_f(x)*v for x,v in zip(a,w) if v), F(0))/6


def budget_of(actions, weights=None):
    """Exact sum of represented input actions, not a rounded-budget proxy."""
    a,w,_ = _source(actions,weights)
    if not sum(w):
        raise ValueError('Undefined population')
    return _sum_budget(a,w)


@dataclass(frozen=True)
class BudgetMapping:
    status: str
    method: str
    actions: np.ndarray | None = None
    weights: tuple[int,...] = ()
    budget: F | None = None
    base_budget: F | None = None
    coefficient: float | None = None
    ideal_coefficient: F | None = None
    ideal_actions: tuple[F,...] = ()
    residual: F | None = None
    action_error: F | None = None
    neighbors: tuple[np.ndarray,...] = ()
    branch: str = ''

    @property
    def supported(self):
        return self.status in ('ZERO_BUDGET','IDENTITY','SUPPORTED')

    @property
    def n_weight(self):
        return sum(self.weights)


def _readonly(values):
    a = np.asarray(values,dtype=np.float64).copy()
    a.flags.writeable = False
    return a


def _shift_root(a, w, b):
    grouped = {}
    for x,v in zip(a,w):
        if v: grouped[float(x)] = grouped.get(float(x),0)+v
    groups = sorted(grouped.items(),reverse=True)
    prefix, count = F(0),0
    for k,(value,weight) in enumerate(groups):
        prefix += _f(value)*weight; count += weight
        c = (6*b-prefix)/count
        next_inactive = k==len(groups)-1 or _f(groups[k+1][0])+c<=0
        if _f(value)+c>0 and next_inactive:
            return c
    raise ArithmeticError('No positive-budget active root')


def _apply(a,positive,coefficient,method):
    out = np.zeros_like(a)
    with np.errstate(over='ignore',invalid='ignore'):
        out[positive] = a[positive]*coefficient if method=='M' else np.maximum(a[positive]+coefficient,0.)
    return out


def _candidate(coef,a,w,positive,b,method):
    if not math.isfinite(coef) or (method=='M' and coef<=0):
        return None
    out = _apply(a,positive,coef,method)
    if not np.isfinite(out[positive]).all() or np.any(out[positive]<0):
        return None
    residual = (_sum_budget(out,w)-b)/sum(w)
    if abs(residual)>BUDGET_PRECISION:
        return None
    return residual,_readonly(out)


def _adjacent(coef):
    with np.errstate(over='ignore',invalid='ignore'):
        return (float(np.nextafter(coef,-np.inf)),float(np.nextafter(coef,np.inf)))


def budget_map(actions, budget, method, weights=None):
    """Map by actions/weights/budget only. Shortfalls cannot enter this API."""
    if method not in ('M','S'):
        raise ValueError('Unknown fixed mapping')
    try:
        a,w,positive = _source(actions,weights)
        b = _f(budget)
        if b<0: raise ValueError('Negative budget')
    except (ValueError,TypeError,OverflowError):
        return BudgetMapping('SOURCE_INVALID',method)
    n = sum(w)
    if not n:
        return BudgetMapping('UNDEFINED_POPULATION',method,weights=w,budget=b)
    base = _sum_budget(a,w)
    # Zero first, including A=B=0: trace coefficients are never the identity alias.
    if b==0:
        coefficient = 0. if method=='M' else -float(a[positive].max())
        return BudgetMapping('ZERO_BUDGET',method,_readonly(np.zeros_like(a)),w,b,base,
               coefficient,_f(coefficient),tuple(F(0) for _ in a),F(0),F(0),branch='ZERO_BUDGET')
    if b==base:
        ideal = tuple(_f(x) if v else F(0) for x,v in zip(a,w))
        coefficient = 1. if method=='M' else 0.
        return BudgetMapping('IDENTITY',method,_readonly(a),w,b,base,coefficient,
                _f(coefficient),ideal,F(0),F(0),branch='POSITIVE_IDENTITY')
    if method=='M' and base==0:
        return BudgetMapping('UNSUPPORTED_MULTIPLICATIVE',method,weights=w,budget=b,base_budget=base)
    try:
        exact_coefficient = b/base if method=='M' else _shift_root(a,w,b)
        rounded = float(exact_coefficient)
        candidates = []
        for coef in sorted(set((rounded,*_adjacent(rounded)))):
            found = _candidate(coef,a,w,positive,b,method)
            if found is not None:
                residual,out = found; candidates.append((abs(residual),coef,residual,out))
        if not candidates: raise ArithmeticError('No budget-valid float64 representation')
        _,coefficient,residual,out = min(candidates,key=lambda x:(x[0],x[1]))
        ideal = tuple(((_f(x)*exact_coefficient if method=='M' else max(_f(x)+exact_coefficient,F(0)))
                       if v else F(0)) for x,v in zip(a,w))
        error = sum((v*abs(_f(x)-y) for x,y,v in zip(out,ideal,w) if v),F(0))/(6*n)
        neighbors = []
        for coef in _adjacent(coefficient):
            found = _candidate(coef,a,w,positive,b,method)
            if found is not None: neighbors.append(found[1])
        return BudgetMapping('SUPPORTED',method,out,w,b,base,coefficient,exact_coefficient,
             ideal,residual,error,tuple(neighbors),'ZERO_BASE_SHIFT' if base==0 else 'GENERAL')
    except (ArithmeticError,OverflowError,ValueError):
        return BudgetMapping('SOLVER_NUMERIC_UNRESOLVED',method,weights=w,budget=b,base_budget=base)


@dataclass(frozen=True)
class MappedSetting:
    setting_id: str
    P: BudgetMapping
    Z: BudgetMapping


def map_pair(actions_p, actions_z, anchor_source, method, weights=None):
    """Keep AP/AZ identities even if budget ordering crosses or coincides."""
    if anchor_source not in ('P','Z') or method not in ('M','S'):
        raise ValueError('Unknown anchor or mapping')
    prefix='A'+anchor_source+'_'+method
    try:
        if len(actions_p)!=len(actions_z):raise ValueError('Population length mismatch')
        source=actions_p if anchor_source=='P' else actions_z
        a,w,_=_source(source,weights)
        if not sum(w):
            empty=BudgetMapping('UNDEFINED_POPULATION',method,weights=w)
            return MappedSetting(prefix,empty,empty)
        b=_sum_budget(a,w)
        return MappedSetting(prefix,budget_map(actions_p,b,method,w),budget_map(actions_z,b,method,w))
    except (ValueError,TypeError,OverflowError):
        bad=BudgetMapping('SOURCE_INVALID',method)
        return MappedSetting(prefix,bad,bad)


@dataclass(frozen=True)
class PairScore:
    U: float | None = None
    V: float | None = None
    U_error: F | None = None
    V_error: F | None = None
    ideal_U: F | None = None
    ideal_V: F | None = None
    U_state: str = 'SOURCE_UNAVAILABLE'
    V_state: str = 'SOURCE_UNAVAILABLE'
    P_V: float | None = None
    Z_V: float | None = None
    reasons: tuple[str,...] = ()


def _resolved(point,error):
    p = _f(point)
    return error==0 or p-error>0 or p+error<0


def score_pair(shortfalls, p: BudgetMapping, z: BudgetMapping):
    """Score after coefficient locking, with exact point-error certification."""
    if not p.supported or not z.supported:
        states=(p.status,z.status)
        state=('UNDEFINED_POPULATION' if 'UNDEFINED_POPULATION' in states else
               'NUMERIC_UNRESOLVED' if 'SOLVER_NUMERIC_UNRESOLVED' in states else
               'UNSUPPORTED_MAPPING' if 'UNSUPPORTED_MULTIPLICATIVE' in states else 'SOURCE_UNAVAILABLE')
        return PairScore(U_state=state,V_state=state,reasons=states)
    if p.weights!=z.weights or p.budget!=z.budget or len(p.actions)!=len(z.actions) \
       or not p.n_weight or any(len(x.ideal_actions)!=len(x.actions) for x in (p,z)):
        return PairScore()
    try:
        s = np.asarray(shortfalls,dtype=float)
        if s.ndim!=1 or len(s)!=len(p.actions):raise ValueError('Target shape')
        pos = np.asarray([w>0 for w in p.weights])
        if not np.isfinite(s[pos]).all() or np.any(s[pos]<0):raise ValueError('Invalid target')
        scores=[]; ideals=[]; sensitive=False
        for mapping in (p,z):
            u,v,ui,vi = F(0),0,F(0),0
            for i,w in enumerate(mapping.weights):
                if not w:continue
                target,action = _f(s[i]),_f(mapping.actions[i])
                ideal = mapping.ideal_actions[i]
                u += w*max(target-action,F(0)); ui += w*max(target-ideal,F(0))
                event,exact_event = target>action,target>ideal
                v += w*event; vi += w*exact_event
                if event!=exact_event:sensitive=True
                if any((target>_f(neighbor[i]))!=event for neighbor in mapping.neighbors):sensitive=True
            scores.append((u/(6*mapping.n_weight),F(v,mapping.n_weight)))
            ideals.append((ui/(6*mapping.n_weight),F(vi,mapping.n_weight)))
        actual_u,actual_v = (scores[1][j]-scores[0][j] for j in (0,1))
        ideal_u,ideal_v = (ideals[1][j]-ideals[0][j] for j in (0,1))
        u,v = float(actual_u),float(actual_v)
        eu,ev = abs(_f(u)-ideal_u),abs(_f(v)-ideal_v)
        return PairScore(u,v,eu,ev,ideal_u,ideal_v,
            'DEFINED' if _resolved(u,eu) else 'NUMERIC_UNRESOLVED',
            'DEFINED' if not sensitive and _resolved(v,ev) else 'NUMERIC_UNRESOLVED',
            float(scores[0][1]),float(scores[1][1]))
    except (ValueError,TypeError,OverflowError):
        return PairScore()


def combine_fits(scores: Mapping[int,PairScore]):
    """No four-fit substitution and no ensemble-action interpretation."""
    if set(scores)!=set(SEEDS):return PairScore()
    result={}
    for metric in ('U','V'):
        items=[scores[s] for s in SEEDS]
        if any(getattr(x,metric) is None or not math.isfinite(getattr(x,metric))
               or not isinstance(getattr(x,'ideal_'+metric),F)
               or getattr(x,metric+'_state') not in ('DEFINED','NUMERIC_UNRESOLVED') for x in items):
            result[metric+'_state']='SOURCE_UNAVAILABLE';continue
        canonical=sum((_f(getattr(x,metric)) for x in items),F(0))/5
        ideal=sum((getattr(x,'ideal_'+metric) for x in items),F(0))/5
        point=float(canonical);error=abs(_f(point)-ideal)
        result.update({metric:point,metric+'_error':error,'ideal_'+metric:ideal,
            metric+'_state':'DEFINED' if (metric=='U' or all(getattr(x,metric+'_state')=='DEFINED' for x in items))
                and _resolved(point,error) else 'NUMERIC_UNRESOLVED'})
    result['reasons']=tuple(dict.fromkeys(reason for x in scores.values() for reason in x.reasons))
    return PairScore(**result)


def validate_population(anchors_p,mask_p,target_p,anchors_z,mask_z,target_z,*,node_ids_p=None,node_ids_z=None):
    try:
        ap,az=np.asarray(anchors_p),np.asarray(anchors_z)
        mp,mz=np.asarray(mask_p),np.asarray(mask_z)
        sp,sz=np.asarray(target_p),np.asarray(target_z)
        if mp.dtype!=bool or mz.dtype!=bool:return 'SOURCE_MISMATCH'
        if mp.ndim!=2 or sp.shape!=mp.shape or sz.shape!=mp.shape:return 'SOURCE_MISMATCH'
        if ap.dtype.kind not in 'iu' or az.dtype.kind not in 'iu':return 'SOURCE_MISMATCH'
        if ap.shape!=(len(mp),) or not np.array_equal(ap,az) or np.any(np.diff(ap)<=0):return 'SOURCE_MISMATCH'
        if (node_ids_p is None)!=(node_ids_z is None):return 'SOURCE_MISMATCH'
        if node_ids_p is not None:
            ids_p,ids_z=tuple(node_ids_p),tuple(node_ids_z)
            if len(ids_p)!=mp.shape[1] or len(set(ids_p))!=len(ids_p) or ids_p!=ids_z:return 'SOURCE_MISMATCH'
        if not np.array_equal(mp,mz) or not np.array_equal(sp[mp],sz[mp]):return 'SOURCE_MISMATCH'
        if not np.isfinite(sp[mp]).all() or np.any(sp[mp]<0):return 'SOURCE_MISMATCH'
        return 'VALID' if mp.any() else 'UNDEFINED_POPULATION'
    except (ValueError,TypeError,IndexError):return 'SOURCE_MISMATCH'


@dataclass(frozen=True)
class NumericCertificate:
    """Arithmetic enclosures only, never a statistical-coverage certificate.

    budget_intervals produces these enclosures for the complete calculation.
    Map precision or a caller's boolean cannot replace its arithmetic derivation.
    """
    point: tuple[F,F]
    lower: tuple[F,F]
    upper: tuple[F,F]
    provenance: str
    binding: str = ''
    coordinate_id: str = ''
    span: int = 0
    record_digest: str = ''
    derivation_digest: str = ''

    @classmethod
    def exact(cls,point,lower,upper):
        """Accept independently derived exact values, never relabel float CIs."""
        if any(isinstance(v,bool) or not isinstance(v,(F,int)) for v in (point,lower,upper)):
            raise TypeError('An exact rational derivation is required; float bounds are not proof')
        p,l,u=map(_f,(point,lower,upper))
        return cls((p,p),(l,l),(u,u),'EXACT_ARITHMETIC')

    def valid(self):
        try:
            return self.provenance in ('EXACT_ARITHMETIC','OUTWARD_CERTIFIED_ARITHMETIC') \
                and all(len(x)==2 and all(isinstance(v,F) for v in x)
                and x[0]<=x[1] for x in (self.point,self.lower,self.upper)) \
                and self.lower[0]<=self.point[1] and self.point[0]<=self.upper[1]
        except (TypeError,ValueError):return False


@dataclass(frozen=True)
class CoordinateEvidence:
    coordinate_id: str
    span: int
    point: float | None
    lower: float | None
    upper: float | None
    numeric: NumericCertificate | None = None
    point_status: str = 'DEFINED'
    interval_status: str = 'ESTIMABLE_APPROX'
    all_draws_legal: bool = False
    n_draws: int = 0
    seed_ids: tuple[int,...] = SEEDS
    family_id: str = FAMILY_ID
    alpha: float = ALPHA
    critical_value: float | None = None
    source_binding: str = ''
    reason: str = ''


def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()


def _record_digest(row):
    c=row.numeric
    return _digest(dict(coordinate=row.coordinate_id,span=row.span,point=row.point,
        lower=row.lower,upper=row.upper,point_status=row.point_status,interval_status=row.interval_status,
        legal=row.all_draws_legal,n_draws=row.n_draws,seeds=row.seed_ids,family=row.family_id,
        alpha=row.alpha,critical=row.critical_value,source=row.source_binding,reason=row.reason,
        certificate=None if c is None else (c.point,c.lower,c.upper,c.provenance,c.derivation_digest)))


def bind_certificate(row, source_binding, derivation_digest=None):
    """Bind producer arithmetic to an immutable record; not a proof of honesty.

    The interval producer supplies a source+trace+algorithm fingerprint and its
    arithmetic derivation digest. This detects accidental swaps/tampering; the
    producer and independently tested arithmetic remain the trust boundary.
    """
    if len(source_binding)!=64 or any(x not in '0123456789abcdef' for x in source_binding):
        raise ValueError('Expected a SHA256 source/trace binding')
    row=replace(row,source_binding=source_binding)
    if row.numeric is None:return row
    derivation_digest=derivation_digest or _digest(('SYNTHETIC_HAND_FIXTURE',source_binding))
    if len(derivation_digest)!=64 or any(x not in '0123456789abcdef' for x in derivation_digest):
        raise ValueError('Expected an arithmetic-derivation SHA256')
    cert=replace(row.numeric,binding=source_binding,coordinate_id=row.coordinate_id,
                 span=row.span,derivation_digest=derivation_digest)
    row=replace(row,numeric=cert)
    return replace(row,numeric=replace(cert,record_digest=_record_digest(row)))


def _bound(row):
    c=row.numeric
    return bool(c and len(row.source_binding)==64 and c.binding==row.source_binding
                and c.coordinate_id==row.coordinate_id and c.span==row.span
                and len(c.derivation_digest)==64 and c.record_digest==_record_digest(row))


def assess_coordinate(row: CoordinateEvidence):
    if row.coordinate_id not in COORDINATES or row.span not in (1,3,7):
        raise ValueError('Unknown coordinate or original span')
    if row.point_status=='NOT_EXECUTED' and row.interval_status=='NOT_EXECUTED':return 'NOT_EXECUTED'
    if row.coordinate_id.endswith('_V') and row.point is not None and not -1<=row.point<=1:
        return 'UNAVAILABLE_OR_UNINFORMATIVE'
    if 'NUMERIC' in row.point_status or 'NUMERIC' in row.interval_status:return 'NUMERIC_UNRESOLVED'
    if row.point_status!='DEFINED' or row.interval_status!='ESTIMABLE_APPROX' or not row.all_draws_legal \
        or row.n_draws!=N_BOOT or tuple(row.seed_ids)!=SEEDS or row.family_id!=FAMILY_ID or row.alpha!=ALPHA \
        or row.critical_value is None or not math.isfinite(row.critical_value) or row.critical_value<=0:
        return 'UNAVAILABLE_OR_UNINFORMATIVE'
    if any(x is None or not math.isfinite(x) for x in (row.point,row.lower,row.upper)):
        return 'UNAVAILABLE_OR_UNINFORMATIVE'
    if not row.lower<=row.point<=row.upper:return 'UNAVAILABLE_OR_UNINFORMATIVE'
    c=row.numeric
    if c is None or not c.valid() or not _bound(row):return 'NUMERIC_UNRESOLVED'
    if row.coordinate_id.endswith('_V') and not -1<=c.point[0]<=c.point[1]<=1:
        return 'UNAVAILABLE_OR_UNINFORMATIVE'
    if row.upper<0:
        return 'SUPPORTED' if c.upper[1]<0 and c.point[1]<0 else 'NUMERIC_UNRESOLVED'
    if row.lower>0:
        return 'ADVERSE' if c.lower[0]>0 and c.point[0]>0 else 'NUMERIC_UNRESOLVED'
    return 'UNRESOLVED'


def _span_summary(rows,span,executed):
    found={}
    for row in rows:
        if row.span!=span or row.coordinate_id in found or row.coordinate_id not in COORDINATES:
            raise ValueError('Duplicate or mismatched coordinate')
        found[row.coordinate_id]=row
    if not executed and found:raise ValueError('Unexecuted declaration contains results')
    bindings={x.source_binding for x in found.values() if x.source_binding}
    if len(bindings)>1:raise ValueError('Different source/trace bindings cannot form one joint family')
    criticals={x.critical_value for x in found.values() if x.interval_status=='ESTIMABLE_APPROX'
               and x.critical_value is not None and math.isfinite(x.critical_value)}
    if len(criticals)>1:raise ValueError('Different critical values cannot form one joint family')
    states={k:assess_coordinate(found[k]) if k in found else
             ('UNAVAILABLE_OR_UNINFORMATIVE' if executed else 'NOT_EXECUTED') for k in COORDINATES}
    flags={metric:all(states[k]=='SUPPORTED' for k in COORDINATES if k.endswith('_'+metric))
           if executed else None for metric in ('U','V')}
    opposite={metric:any(states[k]=='SUPPORTED' for k in COORDINATES if k.endswith('_'+metric))
                      and any(states[k]=='ADVERSE' for k in COORDINATES if k.endswith('_'+metric)) for metric in ('U','V')}
    details={k:dict(point=found[k].point,lower=found[k].lower,upper=found[k].upper,
                   point_status=found[k].point_status,interval_status=found[k].interval_status,exact=False)
             if k in found else dict(point=None,lower=None,upper=None,
                   point_status='SOURCE_UNAVAILABLE' if executed else 'NOT_EXECUTED',
                   interval_status='SOURCE_UNAVAILABLE' if executed else 'NOT_EXECUTED',exact=False) for k in COORDINATES}
    any_estimate=any(x in ('SUPPORTED','ADVERSE','UNRESOLVED') for x in states.values())
    family_state=('EXPLORATORY_INTERVALS_SUPPLIED' if any_estimate else 'NO_ESTIMABLE_INTERVALS') if executed else 'NOT_EXECUTED'
    variation={m:False for m in ('U','V')}
    for m in variation:
        p=[x.point for k,x in found.items() if k.endswith('_'+m) and x.point is not None and math.isfinite(x.point)]
        variation[m]=bool(p) and min(p)<0<max(p)
    return dict(coordinates=states,U_supported=flags['U'],V_supported=flags['V'],
       joint_supported=(flags['U'] and flags['V']) if executed else None,
       unavailable_ids=[k for k,v in states.items() if v in ('UNAVAILABLE_OR_UNINFORMATIVE','NUMERIC_UNRESOLVED')],
       adverse_ids=[k for k,v in states.items() if v=='ADVERSE'],supported_opposite_directions=opposite,
       endpoint_values=details,point_sign_variation=variation,family_status=family_state,
       critical_value=next(iter(criticals)) if any_estimate and criticals else None,
       family_id=FAMILY_ID,alpha=ALPHA,
       critical_note='Supplied family critical value only; this state machine does not compute bootstrap')


def summarize_spans(evidence,executed=True):
    if not set(evidence).issubset({1,3,7}):raise ValueError('Unknown original span')
    spans={s:_span_summary(evidence.get(s,[]),s,executed) for s in (3,1,7)}
    primary=spans[3]
    robust={m:all(spans[s][m+'_supported'] is True for s in (3,1,7)) if executed else None for m in ('U','V')}
    return dict(primary=primary,spans=spans,U_span_robust=robust['U'],V_span_robust=robust['V'],
                joint_span_robust=(robust['U'] and robust['V']) if executed else None,
                post_selection_adjusted=False,coverage_certified=False,transformed_action_qualification='NOT_EVALUATED')
