"""Constructed-cache tests; no project measurement or Metis access."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from repo_paths import Path, repository_root

import joblib
import numpy as np
import pytest
import sklearn

from scripts import autonomous_capacity_candidates as mod


def record(p):
    return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def make_cache(root):
    root.mkdir();rng=np.random.default_rng(201)
    for phase,anchors in {"fit":np.arange(19440,19470),"calfit":np.arange(25200,25220),
                          "select":np.r_[np.arange(27648,27660),np.arange(28944,28956)]}.items():
        n=len(anchors);p=rng.normal(size=(n*2,3)).astype(np.float32)
        z=np.column_stack([p,rng.normal(size=n*2)]).astype(np.float32)
        y=(np.maximum(2+p[:,0]+rng.normal(0,.1,n*2),0)).reshape(n,2)
        mask=np.ones_like(y,bool);mask[0,0]=False;y[0,0]=np.nan
        for name,value in {"X_P":p,"X_Z":z,"shortfall":y,"mask":mask,"anchors":anchors}.items():
            np.save(root/f"{phase}_{name}.npy",value,allow_pickle=False)
    ix=np.flatnonzero(np.load(root/"fit_mask.npy").ravel())
    for seed in mod.SEEDS:np.save(root/f"policy_indices_seed{seed}.npy",ix)
    files={p.name:record(p) for p in root.iterdir()}
    (root/"cache_manifest.json").write_text(json.dumps(dict(schema=mod.SCHEMA,status="COMPLETED",
        scope="SYNTHETIC_UNIT_TEST_ONLY",evaluate_read=False,files=files)),encoding="utf-8")
    return root


def config():
    return dict(candidate_id=3,settings=dict(max_iter=3,max_leaf_nodes=3,min_samples_leaf=3,
        learning_rate=.08,l2_regularization=1.),expected_sklearn_version=sklearn.__version__,cpu_threads=1,
        score_outer=True)


def future():return datetime.now(timezone.utc)+timedelta(minutes=5)


def test_actual_hgb_fit_pairing_calibration_and_independent_accounting(tmp_path):
    cache=make_cache(tmp_path/"cache");out=tmp_path/"candidate"
    result=mod.run_capacity_candidate(config(),cache,out,mod.SEEDS,future())
    assert result["status"]=="COMPLETED_HISTORICAL_DEVELOPMENT"
    assert result["evaluate_read"] is False
    assert set(result["per_seed"])=={str(s) for s in mod.SEEDS}
    for seed in mod.SEEDS:
        ix=np.load(out/f"seed{seed}"/"policy_indices.npy")
        np.testing.assert_array_equal(ix,np.flatnonzero(np.load(cache/"fit_mask.npy").ravel()))
        for arm in ("P","Z"):
            model=joblib.load(out/f"seed{seed}"/f"{arm}_model.joblib")
            assert model.named_steps["regressor"].quantile==.9
            assert model.named_steps["regressor"].early_stopping is False
            calibration=json.loads((out/f"seed{seed}"/f"{arm}_calibration.json").read_text())
            m=np.load(cache/"calfit_mask.npy").ravel()
            raw=np.maximum(model.predict(np.load(cache/f"calfit_X_{arm}.npy")),0)
            residual=np.load(cache/"calfit_shortfall.npy").ravel()[m]-raw[m]
            expected=sorted(float(v) for v in residual)[int(np.ceil(.9*(len(residual)-1)))]
            assert calibration["offset"]==expected
            r=np.load(out/f"seed{seed}"/f"{arm}_select.npy")
            s=np.load(cache/"select_shortfall.npy");mask=np.load(cache/"select_mask.npy")
            a=np.load(cache/"select_anchors.npy")
            for name,span in (("inner",mod.INNER),("outer",mod.OUTER)):
                valid=mask&((a>=span[0])&(a<span[1]))[:,None]
                expected_cost=sum(float(x)/6+10*max(float(y)-float(x),0)/6 for x,y in zip(r[valid],s[valid]))/valid.sum()
                got=result["per_seed"][str(seed)]["metrics"][name][arm]
                assert got["C"]==pytest.approx(expected_cost,abs=1e-14)
                assert got["N"]==int(valid.sum())
    with pytest.raises(FileExistsError):mod.run_capacity_candidate(config(),cache,out,mod.SEEDS,future())


def test_cache_tamper_rejected_before_fit(tmp_path):
    cache=make_cache(tmp_path/"cache")
    np.save(cache/"fit_X_P.npy",np.zeros((60,3)))
    with pytest.raises(ValueError,match="identity"):mod.run_capacity_candidate(config(),cache,tmp_path/"out",mod.SEEDS,future())


def test_evaluation_cache_member_rejected(tmp_path):
    cache=make_cache(tmp_path/"cache");p=cache/"evaluate_X_P.npy";np.save(p,np.ones((1,1)))
    info=json.loads((cache/"cache_manifest.json").read_text());info["files"][p.name]=record(p)
    (cache/"cache_manifest.json").write_text(json.dumps(info))
    with pytest.raises(ValueError,match="evaluation"):mod.run_capacity_candidate(config(),cache,tmp_path/"out",mod.SEEDS,future())


def test_expired_deadline_starts_no_output(tmp_path):
    with pytest.raises(TimeoutError):
        mod.run_capacity_candidate(config(),tmp_path/"absent",tmp_path/"out",mod.SEEDS,datetime.now(timezone.utc)-timedelta(seconds=1))
    assert not (tmp_path/"out").exists()


@pytest.mark.parametrize("change",["wrong_version","quantile","incomplete_seed","extra_setting","float_id"])
def test_frozen_hgb_contract_cannot_be_silently_changed(tmp_path,change):
    cfg=config();seeds=mod.SEEDS
    if change=="wrong_version":cfg["expected_sklearn_version"]="nonexistent"
    if change=="quantile":cfg["quantile"]=.95
    if change=="incomplete_seed":seeds=[201]
    if change=="extra_setting":cfg["settings"]["quantile"]=.95
    if change=="float_id":cfg["candidate_id"]=3.0
    with pytest.raises(ValueError):mod.run_capacity_candidate(cfg,tmp_path/"absent",tmp_path/"out",seeds,future())


def test_prepare_rejects_wrong_parent_manifest_before_cache_creation(tmp_path):
    prepared=tmp_path/"prepared";prepared.mkdir();(prepared/"output_manifest.json").write_text("{}")
    cfg=dict(parent_prepared=str(prepared),parent_prepared_manifest_sha256="0"*64,parent_protocol_sha256="1"*64)
    with pytest.raises(ValueError,match="manifest identity"):mod.prepare_feature_cache(cfg,tmp_path/"cache")
    assert not (tmp_path/"cache").exists()


def test_metrics_zero_population_and_strict_equality():
    s=np.array([[1.,2.]]);a=np.array([27648]);r=s.copy()
    assert mod._metrics(s,r,np.ones_like(s,bool),a,mod.INNER)["V"]==0
    assert mod._metrics(s,r,np.zeros_like(s,bool),a,mod.INNER)==dict(C=None,R=None,U=None,V=None,N=0)


def test_outer_metrics_are_not_scored_by_default(tmp_path,monkeypatch):
    cache=make_cache(tmp_path/"cache");cfg=config();cfg.pop("score_outer")
    original=mod._metrics
    def forbidden_outer(s,r,mask,anchors,span):
        assert span==mod.INNER, "Outer target statistics were read before shortlist freeze"
        return original(s,r,mask,anchors,span)
    monkeypatch.setattr(mod,"_metrics",forbidden_outer)
    out=mod.run_capacity_candidate(cfg,cache,tmp_path/"out",mod.SEEDS,future())
    for seed in mod.SEEDS:
        for arm in ("P","Z"):
            assert out["per_seed"][str(seed)]["metrics"]["outer"][arm]=={"status":"NOT_SCORED"}
            assert (tmp_path/"out"/f"seed{seed}"/f"{arm}_select.npy").is_file()


def test_real_feature_cache_path_uses_only_historical_forecasts(tmp_path,monkeypatch):
    prepared=tmp_path/"prepared";prepared.mkdir()
    rng=np.random.default_rng(20261022)
    data=np.empty((30240,2,4),np.float32)
    data[:,:,0]=rng.uniform(2,15,(30240,2))
    data[:,:,1]=rng.uniform(-1,800,(30240,2))
    data[:,:,2]=rng.normal(0,20,(30240,2))
    data[:,:,3]=rng.uniform(0,8,(30240,2))
    np.save(prepared/"physical_channels.npy",data)
    for name,lo,hi in (("policy_fit",19440,25193),("calibration",25200,30233)):
        anchors=np.arange(lo,hi,dtype=np.int64)
        np.savez(prepared/f"{name}_forecast.npz",anchors=anchors,target_indices=anchors+6,
                 forecast=np.full((len(anchors),2),500.,np.float32))
    (prepared/"data_manifest.json").write_text(json.dumps({"stages":mod.STAGES}))
    protocol="a"*64
    (prepared/"execution_receipt.json").write_text(json.dumps(dict(status="COMPLETED_DEVELOPMENT_NOT_CERTIFIED",protocol_sha256=protocol)))
    manifest={p.name:record(p) for p in prepared.iterdir()}
    (prepared/"output_manifest.json").write_text(json.dumps(manifest))
    cfg=dict(parent_prepared=str(prepared),parent_prepared_manifest_sha256=record(prepared/"output_manifest.json")["sha256"],
             parent_protocol_sha256=protocol,physical_channels_sha256=record(prepared/"physical_channels.npy")["sha256"])
    original_load=np.load
    def forbid_evaluation(file,*args,**kwargs):
        assert "evaluation" not in str(file) and "evaluate" not in str(file)
        return original_load(file,*args,**kwargs)
    monkeypatch.setattr(np,"load",forbid_evaluation)
    cache=tmp_path/"cache";info=mod.prepare_feature_cache(cfg,cache)
    assert info["scope"]=="HISTORICAL_ONLY" and info["evaluate_read"] is False
    assert all("evaluate" not in name for name in info["files"])
    for phase,(lo,hi) in mod.STAGES.items():
        p=original_load(cache/f"{phase}_X_P.npy");z=original_load(cache/f"{phase}_X_Z.npy")
        np.testing.assert_array_equal(z[:,:p.shape[1]],p)
        assert z.shape[1]==p.shape[1]+7
        np.testing.assert_array_equal(original_load(cache/f"{phase}_anchors.npy"),np.arange(lo,hi))
        y=original_load(cache/f"{phase}_shortfall.npy")
        np.testing.assert_array_equal(y,np.maximum(500-data[np.arange(lo,hi)+6,:,1].astype(float),0))
    with pytest.raises(FileExistsError):mod.prepare_feature_cache(cfg,cache)


def test_fit_deadline_failure_preserves_attempt_record(tmp_path,monkeypatch):
    cache=make_cache(tmp_path/"cache");calls=[]
    def timeout_after_fit(deadline):
        calls.append(1)
        if len(calls)==4:raise TimeoutError("Synthetic after-fit deadline")
    monkeypatch.setattr(mod,"_check_deadline",timeout_after_fit)
    out=tmp_path/"out"
    with pytest.raises(TimeoutError):mod.run_capacity_candidate(config(),cache,out,mod.SEEDS,future())
    saved=json.loads((out/"summary.json").read_text())
    assert saved["status"]=="DEADLINE_EXCEEDED"
    assert saved["per_seed"]["201"]["models"]["P"]["status"]=="FITTED_PENDING_CALIBRATION"
    assert (out/"output_manifest.json").is_file()
    assert not (out/"seed202").exists()
