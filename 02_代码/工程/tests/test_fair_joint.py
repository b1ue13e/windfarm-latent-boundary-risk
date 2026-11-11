"""Counterexamples for matched encoding and joint guards."""
import numpy as np
from windfarm_moe.fair_joint import fair_features,historical_eligible,select_joint,assess_increment

TH=dict(cost_noninferiority=.01,signed_U_cap=.001,risk_cap=.1,important_gain=.01)
def row(metric,upper,key='x',lower=0,unknown=False):
    return dict(metric=metric,upper=upper,lower=lower,left=key,unknown=unknown)
def qualified():return [row('D',.005),*[row('H',.0005) for _ in range(5)],*[row('V',.09) for _ in range(5)]]

def test_cost_only_winner_cannot_bypass_severity_or_risk():
    a=qualified();assert historical_eligible(a,'x',TH)
    a[1]['upper']=.002;assert not historical_eligible(a,'x',TH)
    a=qualified();a[-1]['upper']=.11;assert not historical_eligible(a,'x',TH)
    assert select_joint({'cheap':1,'safe':2},['cheap','safe'],{'cheap':False,'safe':True})=='safe'
    assert select_joint({'x':1},['x'],{'x':False}) is None

def test_ignore_alias_is_not_a_scientific_zero_gain_claim():
    assert assess_increment([],[],[],True,TH)=='NO_HISTORICALLY_SELECTED_INCREMENT'
    assert assess_increment([],[],[],False,TH)=='UNAVAILABLE_HISTORICAL_PAIR'
    rows=[row('D',-.02),*[row('H',.0005) for _ in range(5)]]
    risk=[row('V',.09) for _ in range(5)]
    assert assess_increment(rows,risk,risk,False,TH).startswith('SUPPORTED')
    risk[0]['upper']=.11
    assert assess_increment(rows,risk,risk,False,TH)=='NO_JOINT_RISK_QUALIFICATION'

def test_power_dynamics_are_identical_for_full_g_and_z():
    rng=np.random.default_rng(201);data=rng.normal(size=(50,2,4)).astype(np.float32)
    anchors=np.array([36,40]);base=rng.normal(size=(4,40)).astype(np.float32)
    full=rng.normal(size=(4,112)).astype(np.float32);g=np.arange(4,dtype=np.float32)
    xx,ctx,_=fair_features(data,anchors,base,full,g)
    assert xx['FULL_DYN'].shape==(4,118)
    np.testing.assert_equal(xx['FULL_DYN_Z'][:,:118],xx['FULL_DYN'])
    np.testing.assert_equal(xx['FULL_DYN_G'][:,:118],xx['FULL_DYN'])
    changed=data.copy();changed[:,:,3]+=100
    yy,_,_=fair_features(changed,anchors,base,full,g)
    np.testing.assert_equal(xx['FULL_DYN'],yy['FULL_DYN'])


def test_historical_and_evaluation_families_keep_all_declared_slots():
    from pathlib import Path
    import json
    from scripts.run_fair_encoding_joint import keys_for,historical,evaluation
    cfg=json.loads((Path(__file__).resolve().parents[1]/'experiments/fair_encoding_joint_20261022/protocol.json').read_text(encoding='utf-8'))
    cfg['inference']['n_boot']=100
    keys=keys_for(cfg);assert len(keys)==48
    archives=[]
    rng=np.random.default_rng(201)
    for s in range(5):
        a={}
        for phase in ['select','evaluate']:
            n=np.array([10.,20.,30.,40.])
            reference=np.array([30.,40.,50.,40.1733216301867])
            # Exact weighted historical reference mean used by protocol.
            reference=np.array([cfg['reference']['Cstar']]*4)
            for j,key in enumerate(keys):
                c=reference if key==cfg['reference']['key'] else reference+(j+1)*.01+rng.normal(0,.01,4)
                for field,values in [('N',n),('C',c*n),('R',.9*c*n),('U',.01*c*n),('V',np.array([0,1,2,3],dtype=float))]:
                    a[key+'__'+phase+'__all__'+field]=values
        archives.append(a)
    hist,_=historical(archives,keys,cfg);assert len(hist)==528
    none,_=evaluation(archives,keys,cfg,dict(POWER=None,SCORE=None,PITCH=None),3)
    assert len(none)==620
    absent=[r for r in none if r['kind'].startswith('selected')]
    assert len(absent)==20 and all(r['point'] is None and r['unknown'] for r in absent)
    ref=cfg['reference']['key']
    exact,_=evaluation(archives,keys,cfg,dict(POWER=ref,SCORE=ref,PITCH=ref),3)
    identities=[r for r in exact if r['kind'].startswith('selected')]
    assert all(r['point']==r['lower']==r['upper']==0 and not r['unknown'] for r in identities)
