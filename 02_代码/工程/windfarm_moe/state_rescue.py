"""Causal feature restoration and endpoint-safe development inference."""
from __future__ import annotations
import numpy as np

VARIANTS=('R0','R1','R2','R3','P0','Pdyn','T0','S0','Zdyn')
STATES=('idle','mppt','pitch','ambiguous','unknown')
TRENDS=('down','flat','up','missing')


def matched_score_indices(parent_indices,anchors,n_nodes,pitch,shortfall,point_release,policy_start):
    """Keep the same mature rows for both supervision targets, without resampling."""
    issues=np.repeat(np.asarray(anchors),n_nodes)
    indices=np.asarray(parent_indices)
    if indices.dtype.kind not in 'iu' or indices.ndim!=1 or np.any(indices<0) or np.any(indices>=len(issues)):
        raise ValueError('Invalid archived score rows')
    if np.shape(pitch)!=(len(issues),) or np.shape(shortfall)!=(len(issues),):raise ValueError('Score target identity differs')
    eligible=np.isfinite(pitch)&np.isfinite(shortfall)&(issues-6>point_release)&(issues+7<policy_start)
    return indices[eligible[indices]]


def dynamics(data, anchors):
    """Five fixed summaries of completed P records, with no imputation."""
    anchors=np.asarray(anchors)
    if data.ndim!=3 or data.shape[2]<4 or anchors.ndim!=1 or anchors.dtype.kind not in 'iu':
        raise ValueError('Expected time/node/channel data and integer issues')
    if len(anchors)==0 or anchors.min()<6 or anchors.max()>=len(data):
        raise ValueError('Six prior intervals required')
    values=np.asarray(data[anchors[:,None]-np.arange(6,-1,-1)[None,:],:,1],dtype=np.float64)
    values=values.transpose(0,2,1).reshape(-1,7)
    differences=np.diff(values,axis=1)
    complete=np.isfinite(differences).all(axis=1)
    result=np.full((len(values),5),np.nan,dtype=np.float64)
    result[:,0]=values[:,-1]-values[:,-2]
    result[:,1]=values[:,-1]-values[:,0]
    result[complete,2]=np.maximum(-differences[complete],0).mean(axis=1)
    result[complete,3]=(differences[complete]<0).mean(axis=1)
    result[complete,4]=np.maximum(np.abs(differences[complete]).sum(axis=1)-np.abs(result[complete,1]),0)
    return result.astype(np.float32)


def matrices(stage,data,pitch_score,shortfall_score):
    a=np.asarray(stage['A'],dtype=np.float32)
    anchors=stage['anchors']
    current=np.asarray(data[anchors],dtype=np.float32).reshape(-1,4)
    d=dynamics(data,anchors)
    if len(a)!=len(current) or np.shape(pitch_score)!=(len(a),) or np.shape(shortfall_score)!=(len(a),):
        raise ValueError('Score and row identities differ')
    def join(*parts):return np.column_stack(parts).astype(np.float32)
    p,pq=current[:,1:2],current[:,1:3]
    return {
        'R0':join(a,pitch_score),'R1':join(a,p,pitch_score),
        'R2':join(a,pq,pitch_score),'R3':join(a,pq,d,pitch_score),
        'P0':join(a,pq),'Pdyn':join(a,pq,d),
        'T0':join(a,pq,current[:,3]),'S0':join(a,pq,shortfall_score),
        'Zdyn':join(a,pq,d,current[:,3]),
    },join(a[:,:4],current[:,:3],d)


def group_masks(data,anchors):
    current=np.asarray(data[anchors]).reshape(-1,4)
    delta=dynamics(data,anchors)[:,1]
    trend=np.full(len(current),'missing',dtype='<U9')
    trend[np.isfinite(delta)&(delta<-150)]='down'
    trend[np.isfinite(delta)&(np.abs(delta)<=150)]='flat'
    trend[np.isfinite(delta)&(delta>150)]='up'
    w,z=current[:,0],current[:,3]
    valid=np.isfinite(w)&np.isfinite(z)
    state=np.full(len(current),'unknown',dtype='<U9')
    state[valid]='ambiguous'
    state[valid&(w<3)]='idle'
    state[valid&(w>=3)&(w<=10.5)&(z<2)]='mppt'
    state[valid&(w>10.5)&(z>=2)]='pitch'
    groups={'all':np.ones(len(current),dtype=bool)}
    groups.update({g:trend==g for g in TRENDS})
    groups.update({s+':'+g:(state==s)&(trend==g) for s in STATES for g in TRENDS})
    return groups


def day_accounting(shortfall,action,valid,anchors,groups):
    """Return additive numerators; zero deficits never cancel procurement."""
    s=np.asarray(shortfall,dtype=np.float64).reshape(-1)
    r=np.asarray(action,dtype=np.float64).reshape(-1)
    mask=np.asarray(valid,dtype=bool).reshape(-1)
    if len(s)!=len(r) or len(mask)!=len(s) or len(s)%len(anchors):raise ValueError('Shape mismatch')
    if not np.isfinite(r).all() or np.any(r<0) or not np.isfinite(s[mask]).all() or np.any(s[mask]<0):
        raise ValueError('Invalid action or target')
    days=np.repeat(np.asarray(anchors)//144,len(s)//len(anchors))
    calendar=np.unique(days)
    lookup=np.searchsorted(calendar,days)
    u=np.zeros(len(s));u[mask]=np.maximum(s[mask]-r[mask],0)/6
    rr=r/6
    values={'C':rr+10*u,'R':rr,'U':u,'V':(s>r).astype(float)}
    counts={};totals={}
    for group,gm in groups.items():
        if gm.shape!=mask.shape:raise ValueError('Group changes population shape')
        selected=mask&gm
        counts[group]=np.bincount(lookup[selected],minlength=len(calendar)).astype(float)
        for metric,grid in values.items():
            totals[group+'|'+metric]=np.bincount(lookup[selected],weights=grid[selected],minlength=len(calendar))
    return calendar,counts,totals


def circular_weights(n_days,n_boot,span,seed):
    if n_days<1 or n_boot<2 or not 1<=span<=n_days:raise ValueError('Invalid draw specification')
    starts=np.random.default_rng(seed).integers(0,n_days,size=(n_boot,(n_days+span-1)//span))
    indices=((starts[:,:,None]+np.arange(span))%n_days).reshape(n_boot,-1)[:,:n_days]
    weights=np.zeros((n_boot,n_days),dtype=np.int32)
    np.add.at(weights,(np.repeat(np.arange(n_boot),n_days),indices.ravel()),1)
    return indices,weights


def endpoint(terms,weights,domain=(-np.inf,np.inf)):
    """Each term is sign, daily numerator, daily denominator. Never redraw."""
    point=0.;draws=np.zeros(len(weights));valid=True
    for sign,numerator,denominator in terms:
        n=np.asarray(numerator,dtype=float);d=np.asarray(denominator,dtype=float)
        if np.any(d<0) or not np.isfinite(n).all() or not np.isfinite(d).all():raise ValueError('Invalid totals')
        if d.sum()==0:
            return {'point':None,'draws':None,'status':'NO_OBSERVED_POPULATION','bounds':list(domain)}
        point+=sign*n.sum()/d.sum()
        den=weights@d
        if np.any(den==0):valid=False
        if valid:draws+=sign*(weights@n)/den
    if not valid:return {'point':float(point),'draws':None,'status':'ZERO_DRAW_DENOMINATOR','bounds':list(domain)}
    sd=float(draws.std(ddof=1))
    if sd==0 or not np.isfinite(sd):
        return {'point':float(point),'draws':None,'status':'ZERO_EMPIRICAL_VARIANCE','bounds':list(domain)}
    return {'point':float(point),'draws':draws,'sd':sd,'status':'ESTIMABLE','bounds':list(domain)}


def joint_bounds(endpoints,alpha=.05):
    usable=[x for x in endpoints if x['status']=='ESTIMABLE']
    if usable:
        maxdev=np.max(np.stack([np.abs(x['draws']-x['point'])/x['sd'] for x in usable]),axis=0)
        critical=float(np.quantile(maxdev,1-alpha,method='higher'))
    else:critical=None
    for x in endpoints:
        if x['status']=='ESTIMABLE':
            lo,hi=x['bounds'];width=critical*x['sd']
            x['lower']=max(lo,x['point']-width);x['upper']=min(hi,x['point']+width)
        else:x['lower'],x['upper']=x['bounds']
    return critical
