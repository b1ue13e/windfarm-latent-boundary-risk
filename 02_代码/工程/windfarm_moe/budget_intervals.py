"""Fixed eight-coordinate exploratory envelopes with outward arithmetic.

Consumes precomputed frozen-draw scores only; never generates indices or trains.
Arithmetic certification is distinct from statistical or post-selection coverage.
"""
from dataclasses import dataclass
from decimal import Decimal as D, Context, ROUND_FLOOR, ROUND_CEILING
from fractions import Fraction as F
import hashlib
import json
from repo_paths import Path, repository_root

from .budget_diagnostic_core import (
    ALPHA, COORDINATES, N_BOOT, SEEDS, CoordinateEvidence, NumericCertificate,
    bind_certificate, _digest,
)

PRECISION = 80  # Fixed arithmetic precision, not an effect/acceptance threshold.
DOWN = Context(prec=PRECISION, rounding=ROUND_FLOOR)
UP = Context(prec=PRECISION, rounding=ROUND_CEILING)
ZERO = D(0)


@dataclass(frozen=True)
class Interval:
    lo: D
    hi: D

    @classmethod
    def rational(cls, value):
        value=F(value)
        return cls(DOWN.divide(D(value.numerator),D(value.denominator)),
                   UP.divide(D(value.numerator),D(value.denominator)))

    def __add__(self, other):
        return Interval(DOWN.add(self.lo,other.lo),UP.add(self.hi,other.hi))

    def __sub__(self, other):
        return Interval(DOWN.subtract(self.lo,other.hi),UP.subtract(self.hi,other.lo))

    def __mul__(self, other):
        lows=[DOWN.multiply(x,y) for x in (self.lo,self.hi) for y in (other.lo,other.hi)]
        highs=[UP.multiply(x,y) for x in (self.lo,self.hi) for y in (other.lo,other.hi)]
        return Interval(min(lows),max(highs))

    def __truediv__(self, other):
        if other.lo<=0<=other.hi:raise ArithmeticError('Division enclosure contains zero')
        return self*Interval(DOWN.divide(D(1),other.hi),UP.divide(D(1),other.lo))

    def square(self):
        low=ZERO if self.lo<=0<=self.hi else min(DOWN.multiply(self.lo,self.lo),DOWN.multiply(self.hi,self.hi))
        return Interval(low,max(UP.multiply(self.lo,self.lo),UP.multiply(self.hi,self.hi)))

    def absolute(self):
        if self.lo>=0:return self
        if self.hi<=0:return Interval(self.hi.copy_negate(),self.lo.copy_negate())
        return Interval(ZERO,max(self.lo.copy_negate(),self.hi))

    def sqrt(self):
        if self.lo<0:raise ArithmeticError('Negative square-root enclosure')
        # Decimal.sqrt is correctly rounded to nearest; adjacent decimals give
        # outward bounds independently of its rounding-mode convention.
        a=DOWN.sqrt(self.lo); b=UP.sqrt(self.hi)
        lo=ZERO if self.lo==0 else DOWN.next_minus(a)
        hi=ZERO if self.hi==0 else UP.next_plus(b)
        assert F(lo)**2<=F(self.lo) and F(hi)**2>=F(self.hi)
        return Interval(lo,hi)

    def fractions(self):return F(self.lo),F(self.hi)
    def mid_float(self):return float((F(self.lo)+F(self.hi))/2)


@dataclass(frozen=True)
class MetricRecord:
    represented: F | None
    ideal: F | None
    state: str = 'DEFINED'
    reason: str = ''

    def legal(self, metric):
        return isinstance(self.represented,F) and isinstance(self.ideal,F) and \
            self.state in ('DEFINED','NUMERIC_UNRESOLVED') and \
            (metric=='U' or (self.state=='DEFINED' and -1<=self.represented<=1 and -1<=self.ideal<=1))


def metric_record(score, metric):
    point=getattr(score,metric)
    return MetricRecord(None if point is None else F.from_float(point),getattr(score,'ideal_'+metric),
                        getattr(score,metric+'_state'),';'.join(score.reasons))


def _sum(values):
    result=Interval.rational(0)
    for value in values:result=result+value
    return result


def _sd(column):
    n=len(column)
    converted=[Interval.rational(x) for x in column]
    mean=_sum(converted)/Interval.rational(n)
    return (_sum([(x-mean).square() for x in converted])/Interval.rational(n-1)).sqrt(),converted


def _one_envelope(points, columns, eligible):
    """Outward sd, maxima and order-statistic calculation; no float quantile."""
    n=len(next(iter(columns.values()))) if columns else N_BOOT
    sigma={}; converted={}; rejected={}
    cutoff=Interval.rational(F.from_float(1e-14))
    for key in eligible:
        col=columns[key]
        if all(x==col[0] for x in col):
            rejected[key]='UNINFORMATIVE_VARIANCE';continue
        sd,values=_sd(col)
        if sd.hi<=cutoff.lo:rejected[key]='UNINFORMATIVE_VARIANCE';continue
        if sd.lo<=cutoff.hi:rejected[key]='NUMERIC_UNRESOLVED';continue
        sigma[key]=sd;converted[key]=values
    return sigma,converted,rejected


def _bounds(points, sigma, converted, keys):
    if not keys:return {},None,None
    n=len(converted[keys[0]])
    lo=[ZERO]*n;hi=[ZERO]*n
    for key in keys:
        p=Interval.rational(points[key])
        for i,value in enumerate(converted[key]):
            deviation=(value-p).absolute()/sigma[key]
            lo[i]=max(lo[i],deviation.lo);hi[i]=max(hi[i],deviation.hi)
    position=((n-1)*95+99)//100  # Original ceil((n-1)*(1-alpha)), alpha=.05.
    critical=Interval(sorted(lo)[position],sorted(hi)[position])
    bounds={}
    for key in keys:
        p=Interval.rational(points[key]);radius=critical*sigma[key]
        bounds[key]=(p-radius,p+radius)
    return bounds,critical,position


def infer_family(points, draws, *, span, source_identity):
    """Produce all nominal slots, retaining every supplied original draw ID.

    `source_identity` comes from the source adapter; its mode and byte hashes are
    carried into a trace+code binding. This function has no real-data I/O or RNG.
    """
    if span not in (1,3,7) or set(points)!=set(COORDINATES) or set(draws)!=set(COORDINATES):
        raise ValueError('Exactly the original span and eight nominal coordinates are required')
    if any(len(draws[k])!=N_BOOT for k in COORDINATES):raise ValueError('Every original draw must remain')
    if source_identity.get('mode') not in ('SYNTHETIC','ARCHIVED') or source_identity.get('verified') is not True:
        raise ValueError('Verified source identity required')
    for name in ('source_sha256','rules_sha256','draw_sha256'):
        value=source_identity.get(name,'')
        if len(value)!=64 or any(x not in '0123456789abcdef' for x in value):raise ValueError('Missing source identity '+name)
    if source_identity.get('span')!=span:raise ValueError('Source/draw span mismatch')
    # Hash numeric values, original row order, all states and every nominal slot.
    trace_hash=hashlib.sha256()
    for key in COORDINATES:
        trace_hash.update(key.encode())
        for record in (points[key],*draws[key]):
            trace_hash.update(json.dumps((str(record.represented),str(record.ideal),record.state,record.reason),separators=(',',':')).encode())
            trace_hash.update(b'\n')
    algorithm_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    core_hash=hashlib.sha256(Path(__file__).with_name('budget_diagnostic_core.py').read_bytes()).hexdigest()
    identity=dict(source_identity,trace_sha256=trace_hash.hexdigest(),algorithm_sha256=algorithm_hash,core_sha256=core_hash,
                  coordinate_ids=COORDINATES,seed_ids=SEEDS,n_draws=N_BOOT,alpha=ALPHA,precision=PRECISION)
    binding=_digest(identity)
    eligible=[];states={};point_states={};failures={}
    for key in COORDINATES:
        metric=key[-1];p=points[key]
        point_states[key]=p.state if p.legal(metric) else ('NUMERIC_UNRESOLVED' if p.state=='NUMERIC_UNRESOLVED' else 'SOURCE_UNAVAILABLE')
        bad=[i for i,r in enumerate(draws[key]) if not r.legal(metric)]
        failures[key]=bad
        if not p.legal(metric):states[key]='NUMERIC_UNRESOLVED' if p.state=='NUMERIC_UNRESOLVED' else 'SOURCE_UNAVAILABLE'
        elif bad:states[key]='UNINFORMATIVE_DRAW_SUPPORT'
        elif p.state!='DEFINED':states[key]='NUMERIC_UNRESOLVED'
        else:eligible.append(key)
    represented={k:[x.represented for x in draws[k]] for k in eligible}
    ideals={k:[x.ideal for x in draws[k]] for k in eligible}
    raw_points={k:points[k].represented for k in eligible};ideal_points={k:points[k].ideal for k in eligible}
    rs,rv,rbad=_one_envelope(raw_points,represented,eligible)
    es,ev,ebad=_one_envelope(ideal_points,ideals,eligible)
    for key in eligible:
        if key in rbad or key in ebad:
            values=(rbad.get(key),ebad.get(key))
            states[key]='NUMERIC_UNRESOLVED' if 'NUMERIC_UNRESOLVED' in values or rbad.get(key)!=ebad.get(key) else 'UNINFORMATIVE_VARIANCE'
    active=[k for k in eligible if k not in states]
    raw_bounds,rc,position=_bounds(raw_points,rs,rv,active)
    exact_bounds,ec,_=_bounds(ideal_points,es,ev,active)
    critical=rc.mid_float() if rc else None
    rows=[];proof={}
    for key in COORDINATES:
        p=points[key];point=None if p.represented is None else float(p.represented)
        status=states.get(key,'ESTIMABLE_APPROX')
        lower,upper=(None,None) if key[-1]=='U' else (-1.,1.)
        cert=None
        if status=='ESTIMABLE_APPROX':
            rl,ru=raw_bounds[key];el,eu=exact_bounds[key]
            lower,upper=rl.mid_float(),ru.mid_float()
            # Include display-to-binary64 rounding as well as both entire calculations.
            pp=(min(p.represented,p.ideal,F.from_float(point)),max(p.represented,p.ideal,F.from_float(point)))
            ll=(min(*rl.fractions(),*el.fractions(),F.from_float(lower)),max(*rl.fractions(),*el.fractions(),F.from_float(lower)))
            uu=(min(*ru.fractions(),*eu.fractions(),F.from_float(upper)),max(*ru.fractions(),*eu.fractions(),F.from_float(upper)))
            cert=NumericCertificate(pp,ll,uu,'OUTWARD_CERTIFIED_ARITHMETIC')
            proof[key]=dict(raw_sd=rs[key].fractions(),ideal_sd=es[key].fractions(),
                raw_critical=rc.fractions(),ideal_critical=ec.fractions(),point=pp,lower=ll,upper=uu)
        reason=points[key].reason or status
        row=CoordinateEvidence(key,span,point,lower,upper,cert,point_states[key],status,
            not failures[key],N_BOOT,SEEDS,critical_value=critical if status=='ESTIMABLE_APPROX' else None,
            source_binding=binding,reason=reason)
        rows.append(bind_certificate(row,binding,_digest(proof.get(key,dict(status=status,failed_draw_ids=failures[key])))))
    metadata=dict(identity,binding_sha256=binding,active_coordinate_ids=active,
        family_status='EXPLORATORY_INTERVALS_COMPUTED' if active else 'NO_ESTIMABLE_INTERVALS',
        critical_value=critical,order_statistic_position=position,failed_draw_ids=failures,
        arithmetic_proof=proof,statistical_coverage_certified=False,post_selection_adjusted=False)
    return tuple(rows),metadata
