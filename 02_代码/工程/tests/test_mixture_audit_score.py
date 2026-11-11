import numpy as np
from scripts.audit_mixture_closed_loop import independent_days,deficit_bins


def test_independent_energy_and_strict_events():
    a=np.array([0,1]);y=np.array([[0.,6.],[0.,12.]]);r=np.array([[0.,6.],[0.,6.]]);m=np.ones_like(y,bool)
    np.testing.assert_array_equal(independent_days(r,y,m,a),[[12,2,1,1]])


def test_descriptive_bins_do_not_redefine_zero_endpoint():
    y=np.array([[0.,.1,1.,1.1,5.,6.,20.,21.]]);r=np.zeros_like(y);m=np.ones_like(y,bool)
    assert deficit_bins(r,y,m)==[2,2,2,1]
    assert sum(deficit_bins(r,y,m))==np.count_nonzero(y>r)
