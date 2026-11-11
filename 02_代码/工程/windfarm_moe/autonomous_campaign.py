"""Finite candidate generation and historical-only selection for a new campaign."""
from dataclasses import asdict
import hashlib,json,itertools
import numpy as np
from .delayed_risk_aggregation import AggregationConfig

SEEDS=(201,202,203,204,205)
ARMS=('P','Z')
METRICS=('C','R','U','V')
INNER=(27648,28937)
OUTER=(28944,30233)
EVALUATE=(30240,35273)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def capacity_grid(n=32):
    all_settings=[dict(max_iter=i,max_leaf_nodes=l,min_samples_leaf=m,learning_rate=lr,l2_regularization=reg)
        for i,l,m,lr,reg in itertools.product([100,200,300,500],[7,15,31,63],[50,150,400],[.03,.05,.08,.12],[0.,1.,10.])]
    rng=np.random.default_rng(20261022)
    return [dict(candidate_id=i,settings=all_settings[int(j)],cpu_threads=1,
                 expected_sklearn_version='1.9.1',score_outer=False)
            for i,j in enumerate(rng.permutation(len(all_settings))[:n])]


def prior(recipe,k):
    mode=recipe.get('prior','uniform')
    if mode=='uniform':return np.full(k,1/k)
    if mode=='reference_half':
        w=np.full(k,.5/(k-1));w[0]=.5;return w
    if mode.startswith('expert_'):
        w=np.zeros(k);w[int(mode.split('_')[1])]=1;return w
    if mode.startswith('blend_'):
        _,index,alpha=mode.split('_');alpha=float(alpha)
        w=np.zeros(k);w[0]=1-alpha;w[int(index)]+=alpha;return w
    raise ValueError('Unknown fixed prior')


def online_grid(k,expert_set_digest,n=1968):
    recipes=[]
    def agg(method,pr='uniform',**kw):
        cfg=AggregationConfig(method=method,reference_index=0,cost_scale=100.,**kw)
        recipes.append(dict(kind='aggregation',prior=pr,config=asdict(cfg),family='dual' if 'dual' in method else 'static' if method in ('fixed','equal') else 'ew'))
    for index in range(k):agg('fixed',f'expert_{index}',eta=0.,dual_eta_v=0.,dual_eta_u=0.)
    agg('equal',eta=0.,dual_eta_v=0.,dual_eta_u=0.)
    for index in range(1,k):
        for alpha in [.25,.5,.75]:agg('fixed',f'blend_{index}_{alpha}',eta=0.,dual_eta_v=0.,dual_eta_u=0.)
    # Published simple adaptation principles are mandatory controls, not novelty claims.
    for base in sorted({0,4,k-2}):
        for rate,step in itertools.product([.05,.075,.09,.10],[.03,.1,.3,1.,3.,10.,30.]):
            recipes.append(dict(kind='calibration',family='simple',base_index=base,config=dict(method='tracker',target_event_rate=rate,step_size=step)))
        for window,q in itertools.product([144,432,1008],[.90,.925,.95,.975]):
            recipes.append(dict(kind='calibration',family='simple',base_index=base,config=dict(method='rolling',window_steps=window,quantile=q)))
        for window,rate,gamma in itertools.product([144,432,1008],[.05,.075,.09,.10],[.0001,.0003,.001,.003,.01,.03]):
            recipes.append(dict(kind='calibration',family='simple',base_index=base,config=dict(method='aci',window_steps=window,target_event_rate=rate,gamma=gamma)))
    etas=[.001,.003,.01,.03,.1,.3,1.,3.,10.]
    discounts=[1.,.999,.995,.98,.95]
    for eta,d,pr in itertools.product(etas,discounts,['uniform','reference_half']):
        agg('exponential' if d==1 else 'discounted',pr,eta=eta,discount=d,dual_eta_v=0.,dual_eta_u=0.)
    dual=[]
    for eta,d,dv,du,pr in itertools.product(etas,discounts,[0.,.003,.01,.03,.1,.3,1.],[0.,.01,.1,1.],['uniform','reference_half']):
        if dv==du==0:continue
        cfg=AggregationConfig(method='dual' if d==1 else 'discounted_dual',reference_index=0,cost_scale=100.,eta=eta,discount=d,dual_eta_v=dv,dual_eta_u=du)
        dual.append(dict(kind='aggregation',prior=pr,config=asdict(cfg),family='dual'))
    rng=np.random.default_rng(20261023)
    dual=[dual[int(i)] for i in rng.permutation(len(dual))]
    # Baseline/controls are run first; the rest is a fixed outcome-free permutation.
    recipes.extend(dual[:max(0,n-len(recipes))])
    if len(recipes)>n:raise ValueError('Candidate budget cannot cover mandatory controls')
    result=[];seen=set()
    for i,row in enumerate(recipes):
        row=dict(row,expert_set_digest=expert_set_digest)
        digest=fingerprint(row)
        if digest in seen:raise ValueError('Duplicate recipe')
        seen.add(digest);result.append(dict(row,recipe_id=32+i,recipe_sha256=digest))
    return result


def mean_metrics(metrics,arm):
    a=np.asarray(metrics,dtype=float)
    if a.shape!=(5,2,4) or not np.isfinite(a).all():raise ValueError('All five fits and both arms must be scored')
    return a[:,arm].mean(axis=0)


def protected_objective(metrics,arm,reference_metrics):
    """Historical learning target, deliberately stricter than report-only H cap.

    No Cstar or later-window label aggregate enters this optimization proxy.
    It is not a scientific qualification or an excuse to hide other candidates.
    """
    a=np.asarray(metrics,dtype=float)[:,arm];ref=np.asarray(reference_metrics,dtype=float)[:,arm]
    return bool(np.all(a[:,3]<=.1) and np.all(a[:,2]<=ref[:,2]) and a[:,0].mean()<=1.01*ref[:,0].mean())


def pick_recipes(records,role,arm,reference_metrics,cstar):
    """Ranking uses historical scores only; qualification remains a separate report."""
    allowed={'static':['static'],'simple':['simple'],'ew':['ew'],'dual':['dual'],'best':['static','simple','ew','dual']}
    pool=[r for r in records if r['recipe']['family'] in allowed.get(role,allowed['best']) and r.get('status')=='COMPLETED']
    if role=='protected':
        pool=[r for r in pool if protected_objective(r['metrics'],arm,reference_metrics)]
    if not pool:return None
    return min(pool,key=lambda r:(mean_metrics(r['metrics'],arm)[0],r['recipe']['recipe_id']))


def shortlist(records,limit=16):
    selected={}
    ref=next((r for r in records if r.get('status')=='COMPLETED' and r['recipe'].get('prior')=='expert_0'),None)
    if ref is not None:
        for arm in (0,1):
            guarded=[r for r in records if r.get('status')=='COMPLETED' and protected_objective(r['metrics'],arm,ref['metrics'])]
            if guarded:
                row=min(guarded,key=lambda r:(mean_metrics(r['metrics'],arm)[0],r['recipe']['recipe_id']))
                selected[row['recipe']['recipe_id']]=row
    # Mandatory static baselines are evaluated in outer regardless of this shortlist.
    for arm in (0,1):
        for family in ('simple','ew','dual'):
            pool=[r for r in records if r.get('status')=='COMPLETED' and r['recipe']['family']==family]
            for row in sorted(pool,key=lambda r:(mean_metrics(r['metrics'],arm)[0],r['recipe']['recipe_id']))[:2]:selected[row['recipe']['recipe_id']]=row
    for row in sorted([r for r in records if r.get('status')=='COMPLETED' and r['recipe']['family']!='static'],key=lambda r:(mean_metrics(r['metrics'],0)[0],r['recipe']['recipe_id'])):
        if len(selected)>=limit:break
        selected[row['recipe']['recipe_id']]=row
    return [selected[k] for k in sorted(selected)]
