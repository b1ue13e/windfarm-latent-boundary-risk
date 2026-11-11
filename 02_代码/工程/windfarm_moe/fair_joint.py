"""Matched explicit power encoding and joint decision qualification."""
from __future__ import annotations
import numpy as np
from windfarm_moe.conditional_power_calibration import feature_sets


def fair_features(data,anchors,base,full,g):
    old,ctx,extra=feature_sets(data,anchors,base,full,g)
    dyn=np.column_stack((extra['trend'],extra['path']))
    fd=np.column_stack((full,dyn)).astype(np.float32)
    pitch=old['FULL_Z'][:,full.shape[1]:]
    return {'FULL_DYN':fd,'FULL_DYN_G':np.column_stack((fd,g)),
            'FULL_DYN_Z':np.column_stack((fd,pitch))}, {
            'FULL_DYN':ctx['FULL'],'FULL_DYN_G':ctx['COMPACT_G'],
            'FULL_DYN_Z':ctx['FULL_Z']}, extra


def historical_eligible(rows,key,thresholds):
    found=[r for r in rows if r['left']==key]
    d=[r for r in found if r['metric']=='D']
    h=[r for r in found if r['metric']=='H']
    v=[r for r in found if r['metric']=='V']
    return (len(d)==1 and len(h)==5 and len(v)==5 and
        all(r['upper'] is not None and not r['unknown'] for r in found) and
        d[0]['upper']<=thresholds['cost_noninferiority'] and
        all(r['upper']<=thresholds['signed_U_cap'] for r in h) and
        all(r['upper']<=thresholds['risk_cap'] for r in v))


def select_joint(costs,keys,eligibility):
    qualified=[k for k in keys if eligibility.get(k,False)]
    if not qualified:return None
    if any(k not in costs or not np.isfinite(costs[k]) for k in qualified):raise ValueError('Missing historical cost')
    return min(qualified,key=lambda k:(costs[k],keys.index(k)))


def assess_increment(pair_rows,power_risk,candidate_risk,ignore,thresholds):
    if ignore:return 'NO_HISTORICALLY_SELECTED_INCREMENT'
    if not pair_rows or len(power_risk)!=5 or len(candidate_risk)!=5:return 'UNAVAILABLE_HISTORICAL_PAIR'
    d=[r for r in pair_rows if r['metric']=='D'];h=[r for r in pair_rows if r['metric']=='H']
    if len(d)!=1 or len(h)!=5:return 'UNAVAILABLE_ENDPOINTS'
    required=[*d,*h,*power_risk,*candidate_risk]
    if any(r['upper'] is None or r['unknown'] for r in required):return 'UNRESOLVED_UNCERTAINTY'
    if any(r['upper']>thresholds['risk_cap'] for r in [*power_risk,*candidate_risk]):return 'NO_JOINT_RISK_QUALIFICATION'
    if any(r['upper']>thresholds['signed_U_cap'] for r in h):return 'NO_JOINT_SEVERITY_QUALIFICATION'
    if d[0]['upper'] < -thresholds['important_gain']:return 'SUPPORTED_IMPORTANT_JOINT_INCREMENT_DEVELOPMENT'
    if d[0]['upper'] <= thresholds['cost_noninferiority']:return 'JOINT_COST_NONINFERIOR_NOT_IMPORTANT_GAIN'
    return 'UNRESOLVED_OR_UNQUALIFIED_COST'
