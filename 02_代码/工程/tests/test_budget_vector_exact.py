from fractions import Fraction as F
from dataclasses import asdict
import numpy as np
import pytest
from windfarm_moe.budget_vector_exact import exact_sum,PreparedActions,budget_map_fast,map_pair_fast,score_pair_fast
from windfarm_moe.budget_diagnostic_core import budget_map,map_pair,score_pair


@pytest.mark.parametrize('seed',[201,202,203,204,205])
def test_exact_limb_accumulation_matches_fraction(seed):
    rng=np.random.default_rng(seed)
    a=np.ldexp(rng.random(100),rng.integers(-1000,1000,100))
    a[:5]=[0.,np.nextafter(0.,1.),np.finfo(float).max,.1,1e8]
    w=rng.integers(0,36,100)
    expected=sum((F.from_float(float(x))*int(v) for x,v in zip(a,w)),F())
    assert exact_sum(a,w)==expected
    assert exact_sum([.1,2.],[10**12,1])==F.from_float(.1)*10**12+2


@pytest.mark.parametrize('method',['M','S'])
@pytest.mark.parametrize('seed',[201,202,203,204,205])
def test_vectorized_mappings_and_scores_equal_reference(seed,method):
    rng=np.random.default_rng(seed)
    for _ in range(12):
        p=rng.random(11)*100;z=rng.random(11)*50;s=rng.random(11)*120
        w=rng.integers(0,12,11);w[0]=1
        for anchor in ('P','Z'):
            old=map_pair(p,z,anchor,method,w);new=map_pair_fast(p,z,anchor,method,w)
            for a,b in zip((old.P,old.Z),(new.P,new.Z)):
                assert a.status==b.status
                assert a.ideal_coefficient==b.ideal_coefficient and a.coefficient==b.coefficient
                np.testing.assert_array_equal(a.actions,b.actions)
                assert a.residual==b.residual
                assert b.action_error>=a.action_error
            assert asdict(score_pair(s,old.P,old.Z))==asdict(score_pair_fast(s,new.P,new.Z))


@pytest.mark.parametrize('method',['M','S'])
@pytest.mark.parametrize('p,z,s,w',[
    ([1e8,1e8],[.1,.1],[.1,0.],[1,1]),
    ([0.,0.],[1.,3.],[0.,3.],[1,7]),
    ([0.,0.],[0.,0.],[1.,0.],[1,2]),
    ([1e-300,2e-300],[0.,1e-300],[1e-300,0.],[1,2]),
    ([1.,3.,8.],[1.,1.,4.],[1.,4.,8.],[2,0,3]),
])
def test_boundary_mapping_and_scoring_equivalence(method,p,z,s,w):
    for anchor in ('P','Z'):
        a=map_pair(p,z,anchor,method,w);b=map_pair_fast(p,z,anchor,method,w)
        assert [a.P.status,a.Z.status]==[b.P.status,b.Z.status]
        assert asdict(score_pair(s,a.P,a.Z))==asdict(score_pair_fast(s,b.P,b.Z))


def test_positive_zero_base_shift_handles_overflowing_total_but_finite_mean():
    p=[0.,0.];z=[1e308,1e308];w=[1,1]
    old=map_pair(p,z,'Z','S',w);new=map_pair_fast(p,z,'Z','S',w)
    assert old.P.supported and new.P.supported
    np.testing.assert_array_equal(old.P.actions,new.P.actions)
    assert new.P.residual==old.P.residual==0


@pytest.mark.parametrize('weights',[[.5,1.],[-1,2],[float('nan'),1]])
def test_noninteger_or_invalid_weights_are_not_truncated(weights):
    mapped=map_pair_fast([1.,2.],[2.,1.],'P','M',weights)
    assert mapped.P.status==mapped.Z.status=='SOURCE_INVALID'


def test_prepared_cache_cannot_be_staled_by_external_array_mutation():
    source=np.array([1.,2.]);prepared=PreparedActions.make(source);w=np.array([1,1])
    assert prepared.budget(w)==F(1,2)
    source[:]=100.
    assert prepared.budget(w)==F(1,2)
    assert not prepared.values.flags.writeable and not prepared.order.flags.writeable


def test_large_active_boundary_group_matches_reference_without_perturbation():
    p=np.r_[np.ones(1024),np.full(1024,4.)];z=np.full(2048,1.5)
    s=np.linspace(0.,4.,2048);w=np.ones(2048,dtype=np.int64)
    old=map_pair(p,z,'Z','S',w);new=map_pair_fast(p,z,'Z','S',w)
    assert old.P.ideal_coefficient==new.P.ideal_coefficient==F(-1)
    assert asdict(score_pair(s,old.P,old.Z))==asdict(score_pair_fast(s,new.P,new.Z))
