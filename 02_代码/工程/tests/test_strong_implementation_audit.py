"""Check the independent scalar audit definitions with transparent fixtures."""
import numpy as np
from scripts.verify_strong_power_implementation import six_path,manual_rows,materialize
from windfarm_moe.conditional_power_calibration import feature_sets


def test_manual_linear_and_oscillating_paths():
    np.testing.assert_allclose(six_path([10,8,6,4,2,0]),[-2,0,10,5])
    slope,std,drawdown,run=six_path([1,4,2,5,3,0])
    assert drawdown==5 and run==2 and std>0
    assert np.isnan(six_path([1,2,np.nan,4,5,6])).all()


def test_independent_row_order_and_channel_semantics():
    from scripts.run_decision_information_development import feature_groups
    rng=np.random.default_rng(201);data=rng.normal(size=(50,3,4)).astype(np.float32)
    anchors=np.array([36,38,40]);forecast=rng.normal(size=(3,3)).astype(np.float32)
    ix=np.array([0,1,4,8]);rows=manual_rows(data,anchors,forecast,ix);g=np.arange(9,dtype=np.float32)
    old=feature_groups(data,anchors,forecast,36,0,False)
    xx,cc,_=feature_sets(data,anchors,old['A'],old['B'],g)
    manual,contexts=materialize(rows,g[ix])
    for key in xx:
        np.testing.assert_allclose(xx[key][ix],manual[key],atol=1e-6,rtol=1e-6,equal_nan=True)
        np.testing.assert_allclose(cc[key][ix],contexts[key],atol=1e-6,rtol=1e-6,equal_nan=True)
