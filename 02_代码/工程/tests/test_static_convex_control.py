import numpy as np
import pytest
from scripts.run_static_convex_control import training_rows, daily_ledger


def test_training_rows_never_select_outer_or_future():
    a=np.arange(27648,35273)
    y=np.zeros((len(a),134));m=np.ones_like(y,dtype=bool)
    ix=training_rows(a,y,m)
    assert a[ix].min()==27648 and a[ix].max()==28936
    y[a>=28937]=np.nan
    assert np.isfinite(y[ix]).all()


def test_missing_inner_anchor_is_rejected():
    a=np.arange(27649,28937)
    with pytest.raises(ValueError,match='window'):
        training_rows(a,np.zeros((len(a),134)),np.ones((len(a),134),bool))


def test_daily_ledger_has_original_units_population_and_strict_events():
    a=np.arange(30240,35273)
    y=np.full((len(a),134),12.);m=np.ones_like(y,dtype=bool)
    m.ravel()[-(m.size-672939):]=False
    r=np.full_like(y,6.)
    result=daily_ledger(r,y,m,a)
    assert np.allclose(result.sum(axis=0)/m.sum(),[11.,1.,1.,1.])
    assert np.all(daily_ledger(y,y,m,a)[:,3]==0)
