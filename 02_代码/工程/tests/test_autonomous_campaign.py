import numpy as np
from windfarm_moe.autonomous_campaign import capacity_grid,online_grid,prior,shortlist,pick_recipes,protected_objective


def test_finite_grid_is_unique_paired_and_reproducible():
    a=online_grid(9,'a'*64);b=online_grid(9,'a'*64)
    assert a==b and len(a)==1968 and len(capacity_grid())==32
    assert len({r['recipe_sha256'] for r in a})==1968
    assert all(r['config'].get('cost_scale',100)==100 for r in a)
    for r in a:
        if r['kind']=='aggregation':
            p=prior(r,9);assert np.all(p>=0) and abs(p.sum()-1)<1e-14


def test_risk_guard_does_not_hide_unqualified_cost_winner():
    r=online_grid(9,'a'*64)[:2]
    m=np.tile([40.,30.,1.,.09],(5,2,1));bad=m.copy();bad[:,:,0]=38;bad[:,:,3]=.15
    rows=[dict(recipe=r[0],metrics=m.tolist(),status='COMPLETED'),dict(recipe=r[1],metrics=bad.tolist(),status='COMPLETED')]
    assert pick_recipes(rows,'best',0,m,42.)['recipe']==r[1]
    assert pick_recipes(rows,'protected',0,m,42.)['recipe']==r[0]


def test_shortlist_never_uses_evaluation_fields():
    records=[]
    for i,r in enumerate(online_grid(9,'a'*64)):
        if r['family']=='static':continue
        m=np.tile([50-i/10000,30,2,.1],(5,2,1))
        records.append(dict(recipe=r,metrics=m.tolist(),status='COMPLETED',evaluation_cost=10000-i))
    first=[r['recipe']['recipe_id'] for r in shortlist(records)]
    for r in records:r['evaluation_cost']=-r['evaluation_cost']
    assert first==[r['recipe']['recipe_id'] for r in shortlist(records)] and len(first)<=16


def test_shortlist_keeps_protection_even_when_it_is_not_cost_top_two():
    grid=online_grid(9,'a'*64);ref=grid[0]
    rr=np.tile([40.,30.,1.,.09],(5,2,1))
    records=[dict(recipe=ref,metrics=rr.tolist(),status='COMPLETED')]
    simple=[r for r in grid if r['family']=='simple'][:6]
    for i,r in enumerate(simple):
        m=rr.copy();m[:,:,0]=35+i*.5;m[:,:,3]=.15 if i<5 else .08
        records.append(dict(recipe=r,metrics=m.tolist(),status='COMPLETED'))
    selected=shortlist(records)
    assert simple[-1]['recipe_id'] in {r['recipe']['recipe_id'] for r in selected}
    assert protected_objective(records[-1]['metrics'],0,rr)


def test_coordinate_bridge_checks_targets_not_only_mask(tmp_path):
    from scripts.run_autonomous_risk_optimization import assert_coordinates
    import pytest
    a=np.array([1,2]);m=np.ones((2,2),bool);s=np.ones((2,2))
    for name,value in [('anchors',a),('mask',m),('shortfall',s)]:np.save(tmp_path/(name+'.npy'),value)
    assert_coordinates(tmp_path,a,s,m)
    with pytest.raises(ValueError,match='shortfall'):assert_coordinates(tmp_path,a,s+1,m)
