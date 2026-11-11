"""Independent small-fixture tests; no measurements, models or resampling."""
import numpy as np
import pytest

from windfarm_moe.pitch_group_core import (
    account_group, array_sha256, build_group_features, group_target_masks,
    rolling_residual_actions,
)


def fixture_data(n=2, t=80):
    data=np.empty((t,n,4),dtype=np.float64)
    for k in range(n):
        data[:,k,0]=9.+k
        data[:,k,1]=np.arange(t)+k*100
        data[:,k,2]=2*np.arange(t)+k*10
        data[:,k,3]=3*np.arange(t)+k
    return data


def test_signed_group_netting_hand_calculation():
    data=fixture_data();a=np.array([40]);f=np.array([[56.,136.]])
    # Future powers46,146: +10 and-10 error -> zero net, not10.
    out=group_target_masks(data,a,f)
    assert out['target_mask'].tolist()==[True]
    assert out['pair_mask'].tolist()==[True]
    assert out['signed_group_error'].tolist()==[0.]
    assert out['shortfall'].tolist()==[0.]


def test_shapes_schema_and_exact_nested_prefix():
    data=fixture_data();a=np.array([40,41,45]);f=np.ones((3,2))*30
    xp,np_=build_group_features(data,a,f,'P',node_ids=['one','two'])
    x0,n0=build_group_features(data,a,f,'Z0',node_ids=['one','two'])
    xd,nd=build_group_features(data,a,f,'ZD',node_ids=['one','two'])
    assert xp.shape==(3,2+3+2*3*36+2*2*6)
    assert x0.shape==(3,xp.shape[1]+2) and xd.shape==(3,xp.shape[1]+14)
    assert xp.dtype==np.float32 and len(np_)==len(set(np_))
    assert n0[:len(np_)]==nd[:len(np_)]==np_
    assert x0[:,:xp.shape[1]].tobytes()==xd[:,:xp.shape[1]].tobytes()==xp.tobytes()
    assert np_[:5]==['forecast:one','forecast:two','forecast_sum','clock_sin','clock_cos']


def test_history_member_channel_order_and_current_values():
    data=fixture_data();a=np.array([40]);f=np.array([[1.,2.]])
    x,names=build_group_features(data,a,f,'P',node_ids=['a','b'])
    assert x[0,names.index('P:a:lag35')]==5.
    assert x[0,names.index('P:a:lag0')]==40.
    assert x[0,names.index('P:b:lag0')]==140.
    assert x[0,names.index('Q:b:lag0')]==90.
    assert x[0,names.index('forecast_sum')]==3.


def test_dynamic_values_from_independent_linear_sequence():
    data=fixture_data();a=np.array([40]);f=np.ones((1,2))
    x,n=build_group_features(data,a,f,'ZD')
    for ch,slope in [('P',1.),('Q',2.),('Z',3.)]:
        expected={'delta1':slope,'delta6':6*slope,'ols_slope6':slope,
                  'detrended_std6':0.,'max_drawdown6':0.,'trailing_negative_count6':0.}
        for name,value in expected.items():
            assert x[0,n.index(f'{ch}:0:{name}')]==pytest.approx(value)


def test_drawdown_and_trailing_negative_count_independent_example():
    data=fixture_data();data[35:41,0,1]=[8,10,7,5,4,2]
    x,n=build_group_features(data,np.array([40]),np.ones((1,2)))
    assert x[0,n.index('P:0:max_drawdown6')]==8.
    assert x[0,n.index('P:0:trailing_negative_count6')]==4.
    assert x[0,n.index('P:0:delta1')]==-2.


def test_missing_dynamics_support_does_not_search_backwards():
    data=fixture_data();data[36,0,1]=np.nan
    x,n=build_group_features(data,np.array([40]),np.ones((1,2)))
    assert x[0,n.index('P:0:delta1')]==1.
    assert x[0,n.index('P:0:delta6')]==6.
    for name in ['ols_slope6','detrended_std6','max_drawdown6','trailing_negative_count6']:
        assert np.isnan(x[0,n.index('P:0:'+name)])
    assert np.isnan(x[0,n.index('P:0:lag4')])
    assert x[0,n.index('Q:0:lag4')]==72.


def test_missing_tminus6_only_invalidates_delta6():
    data=fixture_data();data[34,0,2]=np.nan
    x,n=build_group_features(data,np.array([40]),np.ones((1,2)))
    assert np.isnan(x[0,n.index('Q:0:delta6')])
    assert x[0,n.index('Q:0:ols_slope6')]==2.
    assert x[0,n.index('Q:0:delta1')]==2.


def test_future_mutation_cannot_affect_past_features():
    data=fixture_data();a=np.array([40,41]);f=np.ones((2,2));before={}
    for arm in ['P','Z0','ZD']:before[arm]=build_group_features(data,a,f,arm)[0]
    changed=data.copy();changed[42:]=np.nan
    for arm in ['P','Z0','ZD']:
        after=build_group_features(changed,a,f,arm)[0]
        assert before[arm].tobytes()==after.tobytes()


def test_power_arm_cannot_read_pitch_values():
    data=fixture_data();a=np.array([40]);f=np.ones((1,2))
    before,_=build_group_features(data,a,f,'P');data[:,:,3]=np.nan
    after,_=build_group_features(data,a,f,'P')
    assert before.tobytes()==after.tobytes()


def test_missing_target_retained_nan_and_current_pitch_only_changes_pair():
    data=fixture_data();a=np.array([40,41]);f=np.ones((2,2))*1000
    data[40,0,3]=np.nan;data[47,0,1]=np.nan
    out=group_target_masks(data,a,f)
    assert out['target_mask'].tolist()==[True,False]
    assert out['pair_mask'].tolist()==[False,False]
    assert np.isfinite(out['shortfall'][0]) and np.isnan(out['shortfall'][1])


def test_zero_and_negative_future_power_not_dropped():
    data=fixture_data();a=np.array([40]);f=np.array([[5.,8.]])
    data[46,:,1]=[0.,-2.]
    out=group_target_masks(data,a,f)
    assert out['target_mask'][0] and out['pair_mask'][0]
    assert out['shortfall'][0]==15.


def test_regime_equal_weight_mean_and_missing_w_not_scoring_filter():
    data=fixture_data();a=np.array([40,41,42]);f=np.ones((3,2))
    data[40,:,0]=[10.,11.];data[41,:,0]=[0.,20.];data[42,0,0]=np.nan
    out=group_target_masks(data,a,f)
    assert out['regime'].tolist()==[1,0,2]
    assert out['pair_mask'].all() and out['target_mask'].all()
    assert out['group_wind'][0]==10.5 and np.isnan(out['group_wind'][2])


def test_member_identity_order_fails_closed():
    with pytest.raises(ValueError,match='order/identity'):
        build_group_features(fixture_data(),np.array([40]),np.ones((1,2)),
                             node_ids=['b','a'],expected_node_ids=['a','b'])
    with pytest.raises(ValueError,match='unique'):
        build_group_features(fixture_data(),np.array([40]),np.ones((1,2)),node_ids=['a','a'])


@pytest.mark.parametrize('anchors',[np.array([40.,41.]),np.array([41,40]),np.array([40,40]),np.array([34])])
def test_invalid_feature_anchors_refused(anchors):
    with pytest.raises(ValueError):build_group_features(fixture_data(),anchors,np.ones((len(anchors),2)))


def test_134_members_still_one_group_label_per_issue():
    data=fixture_data(n=134);a=np.array([40,41]);f=np.ones((2,134))
    out=group_target_masks(data,a,f)
    x,n=build_group_features(data,a,f)
    assert out['shortfall'].shape==(2,) and out['pair_mask'].shape==(2,)
    assert x.shape[0]==2 and len(n)==x.shape[1]


def test_strict_maturity_equality_and_next_issue_boundary():
    a=np.array([0,7,8]);raw=np.array([1.,10.,20.]);target=np.array([6.,999.,999.])
    action,t=rolling_residual_actions(raw,target,a,np.array([True,True,True]),2.)
    np.testing.assert_array_equal(action,[3.,12.,25.])
    np.testing.assert_array_equal(t['support'],[0,0,1])
    np.testing.assert_array_equal(t['last_source_anchor'],[-1,-1,0])


def test_rolling_quantile_higher_independently_sorted_example():
    a=np.array([0,1,2,3,12]);raw=np.zeros(5);target=np.array([0.,1.,2.,3.,50.])
    action,t=rolling_residual_actions(raw,target,a,np.ones(5,dtype=bool),4.,q=.5)
    # At12 all0,1,2,3 labels are mature; higher median index ceil(3*.5)=2.
    assert action[-1]==2. and t['support'][-1]==4


def test_real_issue_window_not_last_n_rows_and_inclusive_left_edge():
    a=np.array([0,100,144,145,250]);raw=np.zeros(5);y=np.array([1.,2.,3.,4.,5.])
    out,t=rolling_residual_actions(raw,y,a,np.ones(5,dtype=bool),99.,q=.925)
    assert t['support'][2]==2 and t['first_source_anchor'][2]==0
    assert t['support'][3]==1 and t['first_source_anchor'][3]==100
    assert t['support'][4]==2 and t['first_source_anchor'][4]==144
    assert out.tolist()==[99.,1.,2.,2.,4.]


def test_unmatured_target_value_and_validity_mutations_do_not_leak():
    a=np.arange(20);raw=np.ones(20);y=np.arange(20.)
    mask=np.ones(20,dtype=bool);before,t=rolling_residual_actions(raw,y,a,mask,3.)
    # Source12 is still unavailable at t19: equality12+7=19 is forbidden.
    altered=y.copy();altered[12:]=np.nan;changed=mask.copy();changed[12:]=False
    after,tt=rolling_residual_actions(raw,altered,a,changed,3.)
    assert before.tobytes()==after.tobytes()
    assert t['offset'].tobytes()==tt['offset'].tobytes()


def test_invalid_target_only_fails_when_matured_and_marked_valid():
    raw=np.ones(2);y=np.array([np.nan,3.]);valid=np.ones(2,dtype=bool)
    # No post-release issue -> unknown source value is never consumed.
    action,_=rolling_residual_actions(raw,y,np.array([0,7]),valid,2.)
    assert action.tolist()==[3.,3.]
    with pytest.raises(ValueError,match='Matured'):
        rolling_residual_actions(raw,y,np.array([0,8]),valid,2.)
    valid[0]=False
    action,_=rolling_residual_actions(raw,y,np.array([0,8]),valid,2.)
    assert action.tolist()==[3.,3.]


def test_signed_offset_and_final_clamp_are_preserved():
    action,t=rolling_residual_actions(np.array([10.,4.]),np.array([0.,4.]),np.array([0,8]),
        np.ones(2,dtype=bool),-2.)
    assert action.tolist()==[8.,0.] and t['offset'][-1]==-10.


def test_no_labels_in_short_window_falls_back_even_with_older_history():
    action,t=rolling_residual_actions(np.ones(2),np.array([100.,0.]),np.array([0,500]),
        np.ones(2,dtype=bool),3.)
    assert action.tolist()==[4.,4.] and t['used_fallback'].all()


def test_daily_hand_calculated_cruv_and_zero_count_calendar_day():
    # Day0 r6 S12 => C11/R1/U1/V1; day2 r12 S6 => C2/R2/U0/V0.
    r=np.array([6.,12.,3.]);s=np.array([12.,6.,np.nan]);m=np.array([True,True,False]);a=np.array([0,288,289])
    out=account_group(r,s,m,a)
    np.testing.assert_array_equal(out['days'],[0,1,2])
    np.testing.assert_array_equal(out['counts'],[1,0,1])
    np.testing.assert_array_equal(out['ledger'],[[11.,1.,1.,1.],[0.,0.,0.,0.],[2.,2.,0.,0.]])


def test_zero_shortfall_retains_procurement_and_no_event():
    out=account_group(np.array([0.,6.]),np.array([0.,0.]),np.array([True,True]),np.array([0,1]))
    assert out['R'][0]==out['C'][0]==1. and out['U'][0]==out['V'][0]==0.
    assert out['N'][0]==2


def test_scoring_mask_is_not_action_availability():
    with pytest.raises(ValueError,match='every issue'):
        account_group(np.array([np.nan]),np.array([np.nan]),np.array([False]),np.array([0]))
    out=account_group(np.array([1.]),np.array([np.nan]),np.array([False]),np.array([0]))
    assert out['N'][0]==0 and (out['ledger']==0).all()


def test_scored_invalid_targets_refused_and_binary_int_mask_not_silently_cast():
    with pytest.raises(ValueError,match='Scored'):
        account_group(np.array([1.]),np.array([np.nan]),np.array([True]),np.array([0]))
    with pytest.raises(ValueError,match='boolean'):
        account_group(np.array([1.]),np.array([0.]),np.array([1]),np.array([0]))


def test_strict_event_boundary_does_not_gain_epsilon():
    r=np.array([1.,1.]);s=np.array([1.,np.nextafter(1.,np.inf)])
    out=account_group(r,s,np.ones(2,dtype=bool),np.array([0,1]))
    assert out['V'][0]==1. and out['U'][0]>0.


def test_array_identity_and_no_input_mutation():
    data=fixture_data();a=np.array([40,41]);f=np.ones((2,2));saved=data.copy()
    x,_=build_group_features(data,a,f,'ZD');assert array_sha256(x)==array_sha256(x.copy())
    np.testing.assert_array_equal(data,saved)
    out=group_target_masks(data,a,f);action,_=rolling_residual_actions(np.ones(2),out['shortfall'],a,out['target_mask'],0.)
    account_group(action,out['shortfall'],out['pair_mask'],a)
    np.testing.assert_array_equal(data,saved)
