import math
import numpy as np
import pytest

from windfarm_moe.autonomous_campaign_inference import infer_campaign, THRESHOLDS
from windfarm_moe.stable_contrast_inference import infer_stable_campaign


def _ledger(offset=0.):
    count=np.full(35,4,dtype=np.int64)
    day=np.arange(35,dtype=float)
    a=np.empty((5,3,35,4))
    for fit in range(5):
        for policy in range(3):
            u=offset+4+(fit+1)*.125+day*.25+policy*(np.mod(day,7)-3)/64
            r=offset+100+day+policy*(np.mod(day,5)-2)/32
            a[fit,policy,:,1]=r
            a[fit,policy,:,2]=u
            a[fit,policy,:,0]=r+10*u
            a[fit,policy,:,3]=np.mod(np.arange(35)+fit+policy,4)
    return a,count


def _reference(data,count,result,n_boot,span,seed):
    rng=np.random.default_rng(seed)
    start=rng.integers(0,35,size=(n_boot,math.ceil(35/span)))
    draws=((start[...,None]+np.arange(span))%35).reshape(n_boot,-1)[:,:35]
    samples={};errors={};maximum=np.zeros(n_boot)
    for row in result['coordinates']:
        if row['status']!='ESTIMABLE_APPROX':continue
        d=row['definition'];metric=d['metric'];col=0 if metric=='D' else 2 if metric=='H' else ['C','R','U','V'].index(metric)
        ids=range(5) if d['fit'] is None else [d['fit']]
        # Independent scalar reductions over input float64 contrasts; no
        # production draw builder, statistics or decision helper is imported.
        daily=np.array([math.fsum(float(data[f,d['left'],day,col])-(0 if d['right'] is None else float(data[f,d['right'],day,col])) for f in ids)/len(ids) for day in range(35)])
        numerator=np.array([math.fsum(float(daily[k]) for k in draw) for draw in draws])
        if metric=='D':
            denom_day=np.array([math.fsum(float(data[f,d['right'],day,0]) for f in range(5))/5 for day in range(35)])
            denominator=np.array([math.fsum(float(denom_day[k]) for k in draw) for draw in draws])
        else:denominator=count[draws].sum(axis=1)
        sample=numerator/denominator*(10/42.058880543674675 if metric=='H' else 1.)
        sd=float(np.std(sample,ddof=1));samples[row['id']]=(row,sd)
        maximum=np.maximum(maximum,abs(sample-row['point'])/sd)
        errors[row['id']]=abs(sd-row['standard_error'])
    critical=float(np.sort(maximum)[math.ceil(.95*(n_boot-1))])
    assert abs(critical-result['critical_value'])<1e-8
    assert max(errors.values())<1e-9
    for row,sd in samples.values():
        lower=row['point']-critical*sd;upper=row['point']+critical*sd
        if row['domain'][0] is not None:lower=max(lower,row['domain'][0])
        if row['domain'][1] is not None:upper=min(upper,row['domain'][1])
        assert abs(lower-row['lower'])<1e-8
        assert abs(upper-row['upper'])<1e-8


@pytest.mark.parametrize('span',[1,3,7])
@pytest.mark.parametrize('offset',[0.,2.**36])
def test_independent_scalar_resampling_with_large_common_component(span,offset):
    a,count=_ledger(offset)
    result=infer_stable_campaign(a,count,['REF','A','B'],[('A','B'),('B','REF')],span=span,n_boot=120,seed=17)
    assert result['thresholds']==THRESHOLDS
    assert not result['scientific_thresholds_changed']
    _reference(a,count,result,120,span,17)


def test_full_family_aliases_and_old_well_conditioned_labels_retained():
    a,count=_ledger()
    a[:,2]=a[:,1]
    kwargs=dict(span=3,n_boot=120,seed=19,aliases=[('A','B')])
    old=infer_campaign(a,count,['REF','A','B'],[('A','B'),('A','REF')],**kwargs)
    new=infer_stable_campaign(a,count,['REF','A','B'],[('A','B'),('A','REF')],**kwargs)
    assert old['nominal_coordinate_ids']==new['nominal_coordinate_ids']
    assert old['family_sha256']==new['family_sha256']
    assert old['qualification']==new['qualification']
    assert old['comparisons']==new['comparisons']
    assert old['bootstrap_indices_sha256']==new['bootstrap_indices_sha256']
    assert new['coordinates'][33]['status']=='EXACT_ALGEBRAIC_ZERO'


def test_unregistered_zero_variance_and_zero_denominator_are_uninformative():
    a,count=_ledger()
    a[:,1]=a[:,0]
    z=infer_stable_campaign(a,count,['REF','A','B'],[('A','REF')],span=3,n_boot=100,seed=2)
    assert z['coordinates'][11]['status']=='ZERO_EMPIRICAL_VARIANCE'
    assert z['qualification']['A']['cost_noninferior'] is None
    z=infer_stable_campaign(np.zeros_like(a),np.zeros_like(count),['REF','A','B'],[('A','REF')],span=3,n_boot=100,seed=2)
    assert z['coordinates'][11]['status']=='ZERO_OBSERVED_DENOMINATOR'
    assert z['qualification']['A']['qualified'] is None
