"""Boundary fixtures; these are software tests, not scientific experiments."""
import numpy as np
import pytest
from windfarm_moe.state_rescue import dynamics,matrices,group_masks,day_accounting,circular_weights,endpoint,joint_bounds,matched_score_indices


def data_fixture():
    data=np.zeros((20,2,4),dtype=np.float32)
    data[:,:,0]=6;data[:,:,1]=np.arange(20)[:,None]*10;data[:,:,2]=-3;data[:,:,3]=1
    return data


def test_future_changes_cannot_change_dynamic_or_current_inputs():
    data=data_fixture();other=data.copy();other[11:]=999999
    issues=np.array([10])
    np.testing.assert_array_equal(dynamics(data,issues),dynamics(other,issues))
    stage={'anchors':issues,'A':np.ones((2,40))}
    a,c=matrices(stage,data,np.ones(2),np.ones(2)*2)
    b,d=matrices(stage,other,np.ones(2),np.ones(2)*2)
    for name in a:np.testing.assert_array_equal(a[name],b[name])
    np.testing.assert_array_equal(c,d)


def test_both_score_targets_use_same_causally_mature_rows_without_resampling():
    anchors=np.arange(10,21,dtype=int);pitch=np.ones(22);shortfall=np.ones(22)
    shortfall[16]=np.nan;pitch[17]=np.nan
    old=np.arange(22,dtype=int)
    chosen=matched_score_indices(old,anchors,2,pitch,shortfall,point_release=9,policy_start=28)
    # publication must be strictly after 9; issue 16 and later are possible.
    assert np.all(np.repeat(anchors,2)[chosen]-6>9)
    assert np.all(np.repeat(anchors,2)[chosen]+7<28)
    assert 16 not in chosen and 17 not in chosen
    np.testing.assert_array_equal(chosen,[12,13,14,15,18,19,20,21])


def test_same_endpoint_but_distinct_paths_retain_oscillation_information():
    data=data_fixture();data[4:11,0,1]=[0,10,20,30,40,50,60]
    data[4:11,1,1]=[0,50,0,50,0,50,60]
    d=dynamics(data,np.array([10]))
    assert d[0,1]==d[1,1]==60
    assert d[0,2]==d[0,3]==d[0,4]==0
    assert d[1,2]>0 and d[1,3]>0 and d[1,4]>0


def test_missing_history_summary_is_missing_without_removing_rows():
    data=data_fixture();data[5,0,1]=np.nan
    d=dynamics(data,np.array([10]))
    assert d.shape==(2,5) and np.isfinite(d[0,:2]).all() and np.isnan(d[0,2:]).all()
    stage={'anchors':np.array([10]),'A':np.ones((2,40))}
    m,_=matrices(stage,data,np.ones(2),np.ones(2))
    assert all(len(x)==2 for x in m.values())


def test_representation_contrasts_have_equal_scalar_width_and_correct_endpoints():
    data=data_fixture();stage={'anchors':np.array([10]),'A':np.ones((2,40))}
    m,c=matrices(stage,data,np.ones(2)*7,np.ones(2)*8)
    assert m['R2'].shape==m['S0'].shape==m['T0'].shape==(2,43)
    np.testing.assert_array_equal(m['R2'][:,-1],[7,7])
    np.testing.assert_array_equal(m['S0'][:,-1],[8,8])
    assert m['R0'].shape[1]==41 and m['R3'].shape[1]==48
    np.testing.assert_array_equal(m['R1'][:,-2],data[10,:,1])
    np.testing.assert_array_equal(m['R2'][:,-3:-1],data[10,:,1:3])
    assert c.shape==(2,12)


def test_groups_partition_without_using_future_state():
    data=data_fixture();data[10,1,3]=np.nan
    groups=group_masks(data,np.array([10]));other=data.copy();other[11:,:,3]=40
    assert sum(groups[t].astype(int) for t in ('down','flat','up','missing')).tolist()==[1,1]
    assert sum(groups[g].astype(int) for g in groups if ':' in g).tolist()==[1,1]
    for key in groups:np.testing.assert_array_equal(groups[key],group_masks(other,np.array([10]))[key])


def test_zero_shortfall_keeps_positive_procurement_and_cost():
    _,counts,totals=day_accounting(np.array([[0.,3.]]),np.array([[6.,1.]]),np.ones((1,2),bool),np.array([144]),{'all':np.ones(2,bool)})
    assert counts['all'][0]==2
    assert totals['all|R'][0]==pytest.approx(7/6)
    assert totals['all|U'][0]==pytest.approx(2/6)
    assert totals['all|C'][0]==pytest.approx(27/6)
    assert totals['all|V'][0]==1


def test_zero_denominator_only_invalidates_that_endpoint_and_no_draw_is_removed():
    weights=np.array([[1,0],[0,1],[1,1]],dtype=float)
    bad=endpoint([(1,[1,0],[1,0])],weights)
    good=endpoint([(1,[1,4],[1,1])],weights)
    none=endpoint([(1,[0,0],[0,0])],weights)
    assert bad['point']==1 and bad['status']=='ZERO_DRAW_DENOMINATOR'
    assert good['status']=='ESTIMABLE' and len(good['draws'])==3
    assert none['point'] is None
    joint_bounds([bad,good,none]);assert np.isinf(bad['upper']) and np.isfinite(good['upper'])


def test_empirical_zero_is_uninformative_not_exact_coverage():
    x=endpoint([(1,[0,0],[2,2])],np.array([[1,0],[0,1]]),domain=(0,1))
    joint_bounds([x]);assert x['point']==0 and x['lower']==0 and x['upper']==1


def test_block_draws_keep_calendar_and_pair_reversal():
    indices,w=circular_weights(7,150,3,42)
    assert indices.shape==(150,7) and np.all(w.sum(axis=1)==7)
    a=endpoint([(1,np.arange(7.),np.ones(7)),(-1,np.arange(7.)**2,np.ones(7))],w)
    b=endpoint([(-1,np.arange(7.),np.ones(7)),(1,np.arange(7.)**2,np.ones(7))],w)
    joint_bounds([a,b]);assert a['point']==-b['point']
    assert a['lower']==pytest.approx(-b['upper'])
