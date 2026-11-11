import numpy as np
import pytest
from scripts.diagnose_endpoint_reversal import attribution

def test_piecewise_cost_consequences_hand_calculated():
    # Release 6kW: no shortage / partial shortage / already short. Add analogues.
    b=np.array([[12.,12.,12.,6.,6.,6.,3.]])
    c=np.array([[6.,6.,6.,12.,12.,12.,3.]])
    s=np.array([[0.,9.,18.,0.,9.,18.,100.]])
    mask=np.ones_like(b,dtype=bool)
    out=attribution(b,c,s,mask)
    # Individual ΔC = [-1,4,9,1,-4,-9,0].
    assert out['delta_C']==pytest.approx(0)
    assert out['groups']['release']['delta_C_contribution']==pytest.approx(12/7)
    assert out['groups']['add']['delta_C_contribution']==pytest.approx(-12/7)
    assert out['groups']['equal']['delta_C_contribution']==0

def test_masked_source_values_are_not_scored_and_zero_denominator_is_none():
    b=np.array([[12.,5.]]);c=np.array([[12.,np.nan]]);s=np.array([[0.,np.nan]])
    out=attribution(b,c,s,np.array([[True,False]]))
    assert out['cells']==1 and out['delta_C']==0
    assert out['groups']['release']['shortage_to_procurement_ratio'] is None
    with pytest.raises(ValueError,match='Empty'):attribution(b,c,s,np.array([[False,False]]))
