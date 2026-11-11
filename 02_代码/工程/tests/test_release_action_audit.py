import numpy as np
from scripts.audit_release_actions import traverse
from scripts.run_prospective_release import prediction_view
from windfarm_moe.release_gate import fit_rule,predict_rule


def test_independent_tree_traversal_all_recipes():
    rng=np.random.default_rng(71)
    b=rng.uniform(2,50,(180,12));c=b+rng.normal(0,1,b.shape);c=np.maximum(c,0)
    x=np.stack([b,b,c,c-b,np.ones_like(b)],axis=-1)
    bank=dict(anchors=np.arange(180),safe=b,cost=c,shortfall=rng.uniform(0,55,b.shape),
        mask=np.ones_like(b,dtype=bool),current_features=x,
        feedback_features=np.concatenate([x,rng.normal(size=(180,12,6))],axis=-1),metadata={})
    for rid in range(24):
        model,_=fit_rule(bank,rid,201,slice(0,120),128,min_samples_leaf=32)
        sel=np.arange(180)>=128
        expected,_=predict_rule(model,prediction_view(bank),sel)
        actual=traverse(model,bank,sel)
        np.testing.assert_array_equal(actual,expected)
