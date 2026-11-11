"""Synthetic boundaries, independent of empirical result directions."""
import numpy as np
import pytest
from windfarm_moe.conditional_power_calibration import feature_sets,GroupOffset,choose_cost,choose_pitch


def test_feature_interfaces_do_not_leak_pitch_to_power_or_future_to_any_arm():
    rng=np.random.default_rng(201);data=rng.normal(size=(18,2,4)).astype(np.float32)
    anchors=np.array([8,10]);base=np.ones((4,40),dtype=np.float32);full=np.ones((4,112),dtype=np.float32);g=np.arange(4)
    a,ca,_=feature_sets(data,anchors,base,full,g)
    changed=data.copy();changed[:,:,3]+=1e6
    b,cb,_=feature_sets(changed,anchors,base,full,g)
    for k in ['COMPACT','FULL','COMPACT_G']:
        np.testing.assert_equal(a[k],b[k]);np.testing.assert_equal(ca[k],cb[k])
    changed=data.copy();changed[11:]=1e9
    b,cb,_=feature_sets(changed,anchors,base,full,g)
    for k in a:np.testing.assert_equal(a[k],b[k]);np.testing.assert_equal(ca[k],cb[k])
    assert a['COMPACT_Z'].shape[1]-a['COMPACT'].shape[1]==7
    assert a['FULL_Z'].shape[1]-a['FULL'].shape[1]==7


def test_reused_compact_and_score_models_keep_exact_column_order():
    from windfarm_moe.dynamic_addback import past_dynamics,matrices
    rng=np.random.default_rng(201);data=rng.normal(size=(20,2,4)).astype(np.float32)
    anchors=np.array([8,12]);base=rng.normal(size=(4,40)).astype(np.float32)
    full=rng.normal(size=(4,112)).astype(np.float32);g=np.arange(4,dtype=np.float32)
    old=matrices(base,full,g,g,past_dynamics(data,anchors))
    new,_,_=feature_sets(data,anchors,base,full,g)
    np.testing.assert_equal(old['PQ_TV'],new['COMPACT'])
    np.testing.assert_equal(old['G_PQ_TV'],new['COMPACT_G'])


def test_full_pipeline_accepts_signed_conditional_residuals_and_missing_features():
    from scripts.run_decision_information_development import learner
    from threadpoolctl import threadpool_limits
    rng=np.random.default_rng(201);x=rng.normal(size=(100,4));x[::5,0]=np.nan
    raw=np.maximum(x[:,1]+3,0);target=np.maximum(raw+rng.normal(size=100)-1,0)
    residual=target-raw
    with threadpool_limits(limits=1):
        m=learner(dict(max_iter=3,max_leaf_nodes=3,min_samples_leaf=5,learning_rate=.1,l2_regularization=1),201,True)
        m.fit(np.column_stack((x[:60],raw[:60])),residual[:60])
        correction=m.predict(np.column_stack((x[60:],raw[60:])))
    action=np.maximum(raw[60:]+correction,0)
    assert np.isfinite(action).all() and np.all(action>=0)


def test_registered_family_has_55_contrasts_without_risk_filtering():
    import json
    from pathlib import Path
    from scripts.run_strong_power_calibration import pairs,candidate_keys
    cfg=json.loads((Path(__file__).resolve().parents[1]/'experiments/strong_power_calibration_20261022/protocol.json').read_text(encoding='utf-8'))
    keys=candidate_keys(cfg)
    assert len(keys)==len(set(keys))==30
    choices=dict(POWER=keys[0],SCORE=keys[12],PITCH=keys[0])
    assert len(pairs(cfg,choices))==55


@pytest.mark.parametrize('lo,hi',[(10,14),(10,12),(12,14),(11,13)])
def test_stage_adapter_slices_time_arrays_and_flattened_features_together(monkeypatch,lo,hi):
    import scripts.run_strong_power_calibration as worker
    anchors=np.arange(10,14);data=np.zeros((30,2,4))
    original=dict(anchors=anchors,forecast=np.arange(8).reshape(4,2),
        shortfall=np.arange(8).reshape(4,2),mask=np.ones((4,2),dtype=bool),
        A=np.arange(24).reshape(8,3),B=np.arange(40).reshape(8,5))
    monkeypatch.setattr(worker,'load_stage',lambda *args:original)
    out=worker.get_stage(None,data,'any',lo,hi)
    np.testing.assert_equal(out['anchors'],np.arange(lo,hi))
    np.testing.assert_equal(out['A'],original['A'][(lo-10)*2:(hi-10)*2])
    np.testing.assert_equal(out['B'],original['B'][(lo-10)*2:(hi-10)*2])
    assert out['mask'].shape==(hi-lo,2) and out['A'].shape==(2*(hi-lo),3)


def test_group_calibration_uses_signed_residual_and_missing_fallback():
    n=240;p=np.ones(n);w=np.ones(n);change=np.zeros(n);residual=np.full(n,-3.)
    m=GroupOffset().fit(p,w,change,residual)
    before=m.p_edges_.copy()
    np.testing.assert_allclose(m.predict([1,np.nan,99],[1,1,np.nan],[0,0,0]),[-3,-3,-3])
    np.testing.assert_equal(m.p_edges_,before)
    assert np.maximum(np.array([2,5])+m.predict([1,1],[1,1],[0,0]),0).tolist()==[0,2]


def test_group_shrinkage_and_small_group_global_fallback():
    p=np.ones(300);w=np.ones(300);c=np.zeros(300);c[:80]=-200
    y=np.zeros(300);y[:80]=10
    m=GroupOffset().fit(p,w,c,y)
    expected=80/280*10+200/280*m.global_
    assert m.predict([1],[1],[-200])[0]==expected
    np.testing.assert_equal(m.predict([1],[1],[200]),[m.global_])


def test_historical_choice_and_ignore_z_alias_never_force_pitch():
    values={'P':1.,'Z1':2.,'Z2':1.}
    assert choose_pitch(values,['Z1','Z2'],'P')=='P'
    assert choose_cost({'A':1,'B':1},['A','B'])=='A'
    with pytest.raises(ValueError):choose_cost({'A':np.nan},['A'])
