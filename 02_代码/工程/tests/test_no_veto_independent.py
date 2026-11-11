import numpy as np
from scripts.audit_no_veto_replay import independent_no_veto,independent_daily

def test_independent_snapshot_and_historical_tie():
    a=np.array([29383,29384,29815,29816,30239,30240]);b=np.full((6,2),12.);c=np.full((6,2),6.)
    models={}
    for snap,start,alpha in [('C',29384,.25),('E',29816,.5),('D',30240,0)]:
        models[snap]=dict(episode_start=start,enabled_anchor=start,status='FITTED_OK',leaf_stats={'2':{'n_cells':10},'1':{'n_cells':10}},leaf_alphas={'2':1.,'1':alpha})
    action,rec=independent_no_veto(dict(anchors=a,safe=b,cost=c),models)
    np.testing.assert_array_equal(action[:,0],[12,10.5,10.5,9,9,12])
    assert all(v['leaf_id']==1 for v in rec.values())

def test_independent_shortfall_score_hand_values():
    r=np.array([[6.,12.],[6.,12.]])
    y=np.array([[0.,18.],[9.,0.]])
    m=np.ones_like(r,dtype=bool)
    ledger,counts,days=independent_daily(r,y,m,np.array([144,145]))
    # R=6kWh, U=1.5kWh, C=21kWh, two strict events.
    np.testing.assert_array_equal(ledger,[[21.,6.,1.5,2.]])
    assert counts.tolist()==[4] and days.tolist()==[1]
