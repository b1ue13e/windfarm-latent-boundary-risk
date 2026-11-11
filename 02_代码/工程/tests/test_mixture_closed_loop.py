import json,time
from repo_paths import Path, repository_root
import numpy as np
from scripts.run_mixture_closed_loop import control_initial,score_actions,execute_task
from windfarm_moe.delayed_risk_batch import aggregate_batch
from windfarm_moe.delayed_risk_aggregation import AggregationConfig
from windfarm_moe.actual_mixture_update import run_mixture,MixtureConfig,run_matched_ew
from windfarm_moe.mixture_campaign_design import recipes_for_loop,comparison_family


def test_same_initial_weights_are_bitwise_shared_by_all_three_methods():
    weights=np.array([0.,.123456789,.876543211]);raw,canonical=control_initial(weights)
    assert (canonical>0).all()
    rng=np.random.default_rng(1);x=rng.uniform(0,40,(10,3,3));y=rng.uniform(0,40,(10,3));m=np.ones_like(y,bool);a=np.arange(10)
    fixed=np.sum(x*canonical,axis=-1)
    old=run_matched_ew(x,y,m,a,canonical)
    new=run_mixture(x,y,m,a,[MixtureConfig()],canonical,return_actions=True)
    np.testing.assert_array_equal(old[:8],fixed[:8])
    np.testing.assert_array_equal(new['actions'][0,:8],fixed[:8])


def test_zero_endpoint_and_original_energy_units():
    a=np.array([0,1]);y=np.array([[0.,6.],[0.,12.]]);r=np.array([[0.,6.],[0.,6.]]);m=np.ones_like(y,bool)
    sums,counts,days=score_actions(r,y,m,a)
    np.testing.assert_array_equal(sums,[[12.,2.,1.,1.]])
    assert counts.tolist()==[4]


def test_each_candidate_is_attempted_after_a_batch_or_individual_error(tmp_path,monkeypatch):
    import scripts.run_mixture_closed_loop as mod
    cache=tmp_path/'cache';cache.mkdir();out=tmp_path/'out';out.mkdir()
    a=np.arange(12);x=np.ones((12,2,9));y=np.ones((12,2));m=np.ones_like(y,bool)
    for name,value in [('anchors',a),('shortfall',y),('mask',m),('P_seed201',x)]:np.save(cache/(name+'.npy'),value)
    folder=out/'initializers/inner';folder.mkdir(parents=True)
    for goal in ['COST','CAP']:
        (folder/f'{goal}_P_seed201.json').write_text(json.dumps(dict(weights=[1.]+[0.]*8,
            canonical_initial=[1.]+[0.]*8,raw_smoothed_prior=[1.]+[0.]*8,status='TEST',optimal=True)))
    monkeypatch.setitem(mod.PHASES,'inner',(8,12,8))
    real=mod.run_mixture
    def wrapper(x,y,m,a,configs,initial,**kwargs):
        if len(configs)>1 or configs[0].eta==99:raise ValueError('intentional isolated synthetic failure')
        return real(x,y,m,a,configs,initial,**kwargs)
    monkeypatch.setattr(mod,'run_mixture',wrapper)
    recipes=[dict(id=0,kind='actual',goal='COST',config=dict(eta=99)),dict(id=1,kind='actual',goal='COST',config=dict(eta=1))]
    cfg=dict(historical_cache=str(cache),historical_manifest_sha256='synthetic')
    receipt=execute_task((cfg,str(out),'inner',201,'P',recipes,time.time()+60))
    data=json.loads((out/'instances/inner/P_seed201/receipt.json').read_text())
    assert receipt['expected']==2 and receipt['completed']==1
    assert data['status']['0']=='FAILED_PRESERVED' and data['status']['1']=='COMPLETED'


def test_factory_and_full_comparison_duties_on_archived_metadata():
    root=Path(repository_root());old=root/'research_audit/autonomous_optimization_20261022/results'
    planned=json.loads((old/'online_candidates.json').read_text())
    completed=[json.loads(p.read_text()) for p in (old/'inner_results').glob('*.json')]
    outer={r['recipe']['recipe_id'] for r in json.loads((old/'outer_results.json').read_text())}
    recipes=recipes_for_loop(planned,completed,outer)
    assert len(recipes)==198
    assert sum(r['kind']=='actual' for r in recipes)==48
    assert sum(r['family']=='coverage' for r in recipes)==128
    assert all(r['legacy']['recipe_id']>=1056 for r in recipes if r['family']=='coverage')
    parent_info=json.loads((root/'research_audit/autonomous_optimization_review_20261024/bridge_intervals/intervals_span3.json').read_text())
    names=parent_info['policy_names'];fd=parent_info['family_definition']
    parent=dict(policy_names=names,comparisons=[(names[l],names[r]) for l,r in fd['comparisons']],
        aliases=[(names[l],names[r]) for l,r in fd['frozen_aliases']])
    family=comparison_family(recipes,parent)
    assert len(family['names'])==412 and family['nominal_family_size']==12522
