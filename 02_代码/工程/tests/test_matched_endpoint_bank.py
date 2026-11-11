import numpy as np
import pytest
from windfarm_moe.matched_endpoint_bank import select_legal_anchors,run_fixed_trajectory

def data():
    rng=np.random.default_rng(422)
    a=np.r_[np.arange(100,130),np.arange(137,177)]
    b=rng.uniform(50,90,(len(a),4))
    xp=rng.uniform(20,110,(*b.shape,9))
    raw=rng.uniform(10,100,b.shape)
    y=rng.uniform(0,130,b.shape);m=np.ones_like(y,dtype=bool)
    w=np.ones(10)/10
    return xp,b,raw,y,m,a,w

def test_legal_version_and_population():
    a=np.arange(27648,35273)
    assert select_legal_anchors(a,'inner').sum()==2139
    assert select_legal_anchors(a,'outer').sum()==1289
    assert select_legal_anchors(a,'inner',True).sum()==7172
    assert select_legal_anchors(a,'outer',True).sum()==6322
    with pytest.raises(ValueError):select_legal_anchors(a,'evaluate',True)

def test_one_continuous_run_has_exact_causal_prefix():
    xp,b,raw,y,m,a,w=data()
    safe,cost,info=run_fixed_trajectory(xp,b,raw,y,m,a,w,.123)
    hs,hc,_=run_fixed_trajectory(xp[:30],b[:30],raw[:30],y[:30],m[:30],a[:30],w,.123)
    assert safe[:30].tobytes()==hs.tobytes()
    assert cost[:30].tobytes()==hc.tobytes()
    # Resetting at the second interval is detectably a different endpoint.
    rs,rc,_=run_fixed_trajectory(xp[30:],b[30:],raw[30:],y[30:],m[30:],a[30:],w,.123)
    assert not np.array_equal(safe[30:],rs)
    assert not np.array_equal(cost[30:],rc)
    assert info['phase_restarts']==0

def test_future_outcomes_cannot_change_current_or_immature_actions():
    xp,b,raw,y,m,a,w=data()
    sa,ca,_=run_fixed_trajectory(xp,b,raw,y,m,a,w,0)
    y2=y.copy();m2=m.copy();y2[20:]=400;m2[20:]=False
    sb,cb,_=run_fixed_trajectory(xp,b,raw,y2,m2,a,w,0)
    # source index20 anchor120 matures strictly after127.
    use=a<=127
    assert sa[use].tobytes()==sb[use].tobytes()
    assert ca[use].tobytes()==cb[use].tobytes()

def test_carried_shift_is_not_reestimated_at_boundary():
    xp,b,raw,y,m,a,w=data()
    _,cost,_=run_fixed_trajectory(xp,b,raw,y,m,a,w,.3125)
    np.testing.assert_array_equal(cost[:8],np.maximum(raw[:8]+.3125,0))
