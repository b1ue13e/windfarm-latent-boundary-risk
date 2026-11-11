import csv
from repo_paths import Path, repository_root
import numpy as np
import pytest
from windfarm_moe.pitch_group_inference import (bootstrap_calendar,decision,
    historical_definitions,infer_group_family,historical_qualification)


def fixture_data(days=7,names=('P_G','Z0_G')):
    counts=np.arange(days,dtype=float)+2
    ledger=np.zeros((5,len(names),days,4))
    for fit in range(5):
        for role in range(len(names)):
            r=np.arange(days)+10.+fit;u=np.arange(days)*.1+.2+role*.03
            ledger[fit,role]=np.column_stack([r+10*u,r,u,np.arange(days)%2])
    return ledger,counts,list(names)


def test_calendar_reproducible_all_days_and_no_fit_axis():
    i,w=bootstrap_calendar(7,span=3,n_boot=101,seed=11)
    assert i.shape==(101,7) and w.shape==(101,7)
    assert np.array_equal(w.sum(1),np.full(101,7))
    assert np.array_equal(i,bootstrap_calendar(7,span=3,n_boot=101,seed=11)[0])


def test_h_uses_u_not_cost_and_scales_exactly():
    data,n,names=fixture_data()
    definitions=[dict(id='H',kind='paired_severity',left='Z0_G',right='P_G',metric='H_U',fit=201)]
    result=infer_group_family(data,n,names,definitions,cstar=40.,n_boot=101)
    row=result['coordinates'][0]
    expected=10*(data[0,1,:,2]-data[0,0,:,2]).sum()/n.sum()/40
    assert row['point']==pytest.approx(expected)
    changed=data.copy();changed[:,1,:,0]+=10000
    result2=infer_group_family(changed,n,names,definitions,cstar=40.,n_boot=101)
    assert row==result2['coordinates'][0]


def test_constant_difference_not_assumed_exact():
    data,n,names=fixture_data()
    data[:,1]=data[:,0]
    d=[dict(id='U',kind='paired_mean',left='Z0_G',right='P_G',metric='U',fit=None)]
    row=infer_group_family(data,n,names,d,cstar=40,n_boot=100)['coordinates'][0]
    assert row['status']=='ZERO_EMPIRICAL_VARIANCE' and row['upper'] is None
    assert decision(row,0.) is None


def test_verified_program_alias_or_self_zero():
    data,n,names=fixture_data();data[:,1]=data[:,0]
    d=[dict(id='U',kind='paired_mean',left='Z0_G',right='P_G',metric='U',fit=None)]
    row=infer_group_family(data,n,names,d,cstar=40,n_boot=100,aliases=[('Z0_G','P_G')])['coordinates'][0]
    assert row['status']=='EXACT_ALGEBRAIC_ZERO' and row['upper']==0
    data[0,1,0,1]+=1
    with pytest.raises(ValueError,match='alias'):infer_group_family(data,n,names,d,cstar=40,n_boot=100,aliases=[('Z0_G','P_G')])


def test_zero_count_draw_is_uninformative_not_deleted():
    data,n,names=fixture_data();n[:]=0;n[0]=2;data[:,:,1:]=0
    d=[dict(id='V',kind='absolute_risk',left='P_G',right=None,metric='V',fit=201)]
    result=infer_group_family(data,n,names,d,cstar=40,span=1,n_boot=200)
    row=result['coordinates'][0]
    assert row['n_invalid_draws']>0 and row['status']=='ZERO_DRAW_DENOMINATOR'
    assert result['n_boot']==200 and row['upper']==1


def test_unavailable_role_preserves_nominal_endpoint():
    data,n,names=fixture_data();data[:,1]=np.nan
    d=[dict(id='C',kind='paired_mean',left='Z0_G',right='P_G',metric='C',fit=None)]
    result=infer_group_family(data,n,names,d,cstar=40,n_boot=100,available=[True,False])
    assert result['family_size']==1 and result['coordinates'][0]['status']=='SOURCE_UNAVAILABLE'


def test_regime_interaction_is_direct_difference_of_paired_effects():
    data,n,names=fixture_data();low=data.copy();high=data.copy()
    high[:,1,:,0]-=1.;low[:,1,:,0]+=.5
    d=[dict(id='INT',kind='direct_regime_interaction',left='Z0_G',right='P_G',metric='C',fit=None)]
    result=infer_group_family(data,n,names,d,cstar=40,n_boot=100,
        regime_ledgers={'high':high,'low':low},regime_counts={'high':n,'low':n})
    assert result['coordinates'][0]['point']==pytest.approx(-1.5*len(n)/n.sum())


def test_historical_all132_and_reference_self_qualified():
    names=[f'{a}_{m}' for a in ['P','Z0','ZD'] for m in ['G','C','A','L']]
    data,n,_=fixture_data(names=names)
    data[:,:,:,3]=0.01*np.arange(len(n))[None,None,:]
    # Exact integral event counts are required. V=0 with differing exposure
    # still has zero variance, so retain unknown risk rather than false pass.
    data[:,:,:,3]=np.arange(len(n))[None,None,:]%2
    definitions=historical_definitions(names);assert len(definitions)==132
    result=infer_group_family(data,n,names,definitions,cstar=40,n_boot=100)
    q=historical_qualification(result,names)
    assert q['P_G']['cost_noninferior'] is True and q['P_G']['five_instance_H_U_noninferior'] is True


def test_full406_schema_without_hardcoded35days():
    root=Path(repository_root())
    with (root/'research_audit/pitch_increment_go_kill_v2_20261025/MATRIX.csv').open(encoding='utf-8-sig') as f:names=[r['id'] for r in csv.DictReader(f)]
    with (root/'research_audit/pitch_increment_go_kill_v2_20261025/COORDINATES.csv').open(encoding='utf-8-sig') as f:d=list(csv.DictReader(f))
    data,n,_=fixture_data(days=9,names=names)
    result=infer_group_family(data,n,names,d,cstar=40,n_boot=100,
        regime_ledgers={k:data for k in ['high','low','unknown']},regime_counts={k:n for k in ['high','low','unknown']})
    assert result['family_size']==406 and result['n_days']==9
