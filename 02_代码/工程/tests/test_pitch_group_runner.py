import hashlib
import importlib.util
import json
from repo_paths import Path, repository_root
import numpy as np
import pytest
from scripts import run_pitch_group as r


def test_strict_maturity_and_future_target_mutation():
    a=np.arange(20);score=np.full(20,3.);y=np.arange(20,dtype=float);valid=np.ones(20,bool)
    actions,trace=r.online_residual(score,y,a,valid,1.)
    assert actions[7]==4. and trace['support'][7]==0 and trace['support'][8]==1
    altered=y.copy();altered[13:]=1e9
    new,_=r.online_residual(score,altered,a,valid,1.)
    np.testing.assert_array_equal(actions[:20],new[:20])


def test_online_real_clock_window_gaps_and_no_current_validity_input():
    a=np.array([0,1,2,200,201]);score=np.ones(5);y=np.array([9.,9.,9.,np.nan,np.nan]);valid=np.array([1,1,1,0,0],bool)
    actions,trace=r.online_residual(score,y,a,valid,2.)
    np.testing.assert_array_equal(actions,[3,3,3,3,3]);assert trace['support'][-1]==0


def test_online_prewarm_does_not_claim_future_offset_decisions():
    a=np.arange(20);score=np.ones(20);y=np.arange(20,dtype=float);valid=np.ones(20,bool)
    action,trace=r.online_residual(score,y,a,valid,100.,active_start=12)
    np.testing.assert_array_equal(action[:12],np.ones(12))
    assert trace['support'][12]==5 and action[12]==4.


def test_daily_loss_hand_example_and_zero_count_day_retained():
    ledger,n,day=r.daily_account(np.array([6.,2.,3.]),np.array([12.,np.nan,6.]),np.array([1,0,1],bool),np.array([0,144,288]))
    np.testing.assert_array_equal(ledger,[[11.,1.,1.,1.],[0,0,0,0],[5.5,.5,.5,1.]])
    np.testing.assert_array_equal(n,[1,0,1]);np.testing.assert_array_equal(day,[0,1,2])


def test_linear_quantile_training_missingness_and_constant_column():
    x=np.array([[0.,7.],[1.,7.],[2.,7.],[3.,7.],[np.nan,7.]])
    y=np.array([1.,3.,5.,7.,4.])
    model=r.fit_linear_quantile(x,y,timeout_seconds=10)
    assert np.isfinite(r.predict_linear(model,x)).all() and model['quantile']==.9
    assert model['std'][1]==1. and model['alpha']==1e-4


def test_signed_offset_uses_higher_and_not_borrowed():
    assert r.safe_offset(np.array([5.,5.,5.]),np.array([1.,2.,3.]),np.ones(3,bool))==-2.


def test_production_hgb_recipe_fixed():
    params=r.make_hgb(203)['model'].get_params();res=r.make_hgb(203,residual=True)['model'].get_params()
    assert params['max_iter']==100 and params['max_leaf_nodes']==15 and params['quantile']==.9
    assert params['min_samples_leaf']==50 and params['learning_rate']==.08 and not params['early_stopping']
    assert res['min_samples_leaf']==100 and res['learning_rate']==.05


def _prepared(tmp_path,evaluation=False):
    phases=['evaluation'] if evaluation else ['fit','calfit','offset','selection']
    names=[]
    for p in phases:
        start,end=r.STAGES['evaluate' if p=='evaluation' else p]
        anchors=np.arange(start,min(start+20,end))
        y=np.arange(len(anchors),dtype=float)+1
        path=tmp_path/f'phase_{p}.npz';np.savez_compressed(path,anchors=anchors,S_G=y,target_mask=np.ones(len(y),bool),pair_mask=np.ones(len(y),bool),regime=np.arange(len(y))%2)
        names.append(path.name)
        for arm,dim in [('P',2),('Z0',3),('ZD',4)]:
            x=np.column_stack([np.arange(len(y)),np.ones(len(y))]+[np.zeros(len(y))]*(dim-2)).astype(np.float32)
            q=tmp_path/f'X_{arm}_{p}.npy';np.save(q,x);names.append(q.name)
    manifest={name:r.binding(tmp_path/name) for name in names};r.write_new(tmp_path/'manifest.json',manifest)
    return manifest


def test_phase_loader_never_opens_evaluation_files(tmp_path,monkeypatch):
    _prepared(tmp_path)
    # A future evaluation file can exist but has no historical source binding.
    (tmp_path/'phase_evaluation.npz').write_bytes(b'future must not open')
    bank=r.load_prepared(tmp_path,r.sha(tmp_path/'manifest.json'))
    assert len(bank['anchors'])==80 and bank['anchors'][-1]<30240


def test_prepared_tamper_fails(tmp_path):
    _prepared(tmp_path);p=tmp_path/'X_P_fit.npy'
    with p.open('ab') as f:f.write(b'changed')
    with pytest.raises(ValueError,match='identity'):r.load_prepared(tmp_path)


def test_no_overwrite_and_five_fit_barrier(tmp_path):
    r.write_new(tmp_path/'f.json',{'x':1})
    with pytest.raises(FileExistsError):r.write_new(tmp_path/'f.json',{'x':2})
    with pytest.raises(FileNotFoundError):r.freeze_history({'source_hashes':{},'history_manifest_sha256':'x'},tmp_path)


def _historical_fixture():
    rows=[]
    for name in r.CANDIDATES:
        rows.append(dict(id=f'HD:{name}',status='ESTIMABLE_APPROX',lower=-.5,upper=0.))
        for seed in r.SEEDS:
            rows.append(dict(id=f'HH:{name}:{seed}',status='ESTIMABLE_APPROX',lower=-.001,upper=0.))
            rows.append(dict(id=f'HV:{name}:{seed}',status='ESTIMABLE_APPROX',lower=.01,upper=.09))
    data=np.zeros((5,12,2,4));data[:,:,:,0]=10.
    data[:,r.CANDIDATES.index('P_L'),:,0]=2.
    data[:,r.CANDIDATES.index('Z0_G'),:,0]=2.
    return {'coordinates':rows},data,np.ones(2)


def test_history_selection_ignores_ineligible_cheaper_power_and_prefers_exact_ignore_tie():
    inference,data,n=_historical_fixture()
    data[:,r.CANDIDATES.index('P_C'),:,0]=.1
    row=next(x for x in inference['coordinates'] if x['id']=='HH:P_C:201')
    row.update(lower=.002,upper=.003)
    choice=r._historical_select(inference,data,n)
    assert choice['P_STAR']=='P_L' and choice['P_LINEAR_REF']=='P_L'
    assert choice['Z_STAR']=='P_L' and choice['selected_ignore'] is True


def test_history_no_power_reference_does_not_select_pitch_using_evaluation():
    inference,data,n=_historical_fixture()
    for row in inference['coordinates']:
        if row['id'].startswith('HV:P_'):row.update(lower=.11,upper=.2)
    choice=r._historical_select(inference,data,n)
    assert choice['P_STAR'] is None and choice['Z_STAR'] is None and choice['P_LINEAR_REF'] is None
    assert choice['status']=='NO_HISTORY_P_REFERENCE' and choice['uses_evaluation'] is False


def test_all_candidate_order_and_synthetic_fit(tmp_path):
    prepared=tmp_path/'prepared';prepared.mkdir();_prepared(prepared)
    cfg={'history_prepared':str(prepared),'history_manifest_sha256':r.sha(prepared/'manifest.json'),'source_hashes':{},'linear_time_limit_seconds':10}
    out=tmp_path/'campaign'
    r.fit_instance(cfg,out,201,synthetic_test=True)
    receipt=r.read(out/'fit/seed201/receipt.json')
    assert receipt['names']==list(r.CANDIDATES) and receipt['optimization_count']==9
    assert receipt['evaluation_touched'] is False and receipt['history_qualification_filters_evaluation'] is False
    with np.load(out/'fit/seed201/selection_daily.npz') as z:assert z['ledger'].shape[0]==12


def test_exact_ignore_and_missing_legacy_are_not_zero_imputed(tmp_path):
    bank={'path':tmp_path,'anchors':np.arange(4)}
    actions={name:np.arange(4,dtype=float) for name in r.CANDIDATES}
    names=[*r.CANDIDATES,*[f'IGNORE_P_{m}' for m in r.METHODS],'OLD_OP_SUM','P_STAR','Z_STAR','P_LINEAR_REF']
    choice=dict(P_STAR='P_C',Z_STAR='P_C',P_LINEAR_REF=None)
    out,availability,aliases=r._expand_actions(actions,bank,201,choice,names)
    assert not availability['OLD_OP_SUM'] and 'OLD_OP_SUM' not in out
    assert not availability['P_LINEAR_REF'] and np.array_equal(out['Z_STAR'],out['P_C'])
    assert ('Z_STAR','P_C') in aliases


def test_five_fit_freeze_evaluation_full406_flow_on_constructed_data(tmp_path):
    root=Path(repository_root())
    hist=tmp_path/'history';hist.mkdir();_prepared(hist)
    ev=tmp_path/'evaluation';ev.mkdir()
    a=np.arange(*r.STAGES['evaluate']);t=np.arange(len(a))
    target=(t%20+1).astype(float);regime=np.where(t%3==0,2,t%2)
    np.savez_compressed(ev/'phase_evaluation.npz',anchors=a,S_G=target,target_mask=np.ones(len(a),bool),pair_mask=np.ones(len(a),bool),regime=regime)
    names=['phase_evaluation.npz']
    for arm,dim in [('P',2),('Z0',3),('ZD',4)]:
        x=np.column_stack([t%20,np.ones(len(a))]+[np.zeros(len(a))]*(dim-2)).astype(np.float32)
        path=ev/f'X_{arm}_evaluation.npy';np.save(path,x);names.append(path.name)
    r.write_new(ev/'manifest.json',{name:r.binding(ev/name) for name in names})
    cfg={'history_prepared':str(hist),'history_manifest_sha256':r.sha(hist/'manifest.json'),
         'evaluation_prepared':str(ev),'evaluation_manifest_sha256':r.sha(ev/'manifest.json'),
         'source_hashes':{},'linear_time_limit_seconds':10,
         'matrix_path':'research_audit/pitch_increment_go_kill_v2_20261025/MATRIX.csv',
         'comparisons_path':'research_audit/pitch_increment_go_kill_v2_20261025/COMPARISONS.csv',
         'coordinates_path':'research_audit/pitch_increment_go_kill_v2_20261025/COORDINATES.csv'}
    out=tmp_path/'campaign'
    for seed in r.SEEDS:r.fit_instance(cfg,out,seed,synthetic_test=True)
    r.freeze_history(cfg,out,n_boot_override=100)
    assert r.read(out/'FINAL_FREEZE.json')['completed_optimization_count']==45
    for seed in r.SEEDS:r.evaluate_instance(cfg,out,seed)
    r.aggregate(cfg,out,n_boot_override=100)
    complete=r.read(out/'aggregate/completion.json')
    assert complete['status']=='COMPLETED' and complete['qualification_filter'] is False
    for span in [1,3,7]:
        inference=r.read(out/f'aggregate/inference_span{span}.json')
        assert inference['family_size']==406 and len(inference['labels']['comparisons'])==27
        assert not inference['available'][inference['policy_names'].index('OLD_OP_SUM')]
