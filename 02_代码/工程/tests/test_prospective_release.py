"""Independent causal orchestration and endpoint identity checks."""
import copy
import json
from repo_paths import Path, repository_root
import numpy as np
import pytest

from scripts import run_prospective_release as r
from windfarm_moe.release_gate import fit_rule, predict_rule


def bank(n=120, nodes=16):
    rng = np.random.default_rng(123)
    b = rng.uniform(1, 30, (n, nodes))
    c = b * .95
    x = np.stack([b, b, c, c-b, np.ones_like(b)], axis=-1)
    fb = np.concatenate([x, np.zeros((n, nodes, 6))], axis=-1)
    return dict(anchors=np.arange(100, 100+n), safe=b, cost=c,
        reference=b.copy(), shortfall=rng.uniform(0, 35, b.shape), mask=np.ones_like(b, dtype=bool),
        current_features=x, feedback_features=fb, metadata=dict(arm="P"))


def test_full_feedback_api_and_future_targets_do_not_enter_fit():
    b = bank()
    m, _ = fit_rule(b, 14, 201, slice(0, 70), 178, min_samples_leaf=32)
    assert m["n_features"] == 11
    bad = copy.deepcopy(b)
    bad["shortfall"][70:] = -999
    other, _ = fit_rule(bad, 14, 201, slice(0, 70), 178, min_samples_leaf=32)
    left, _ = predict_rule(m, r.prediction_view(b))
    right, _ = predict_rule(other, r.prediction_view(b))
    np.testing.assert_array_equal(left, right)
    assert not {"mask", "shortfall", "anchors"} & r.prediction_view(b).keys()


@pytest.mark.parametrize("rid,field", [(0,"safe"),(1,"cost")])
def test_endpoint_prediction_is_bit_exact(rid, field):
    b = bank()
    b["cost"][:] = 1e-12
    m, _ = fit_rule(b, rid, 201, slice(0, 70), 178)
    act, _ = predict_rule(m, r.prediction_view(b))
    assert act.tobytes() == b[field].tobytes()


def test_schedule_no_future_model_and_static_warmup():
    b = bank(n=8, nodes=2)
    b["anchors"] = np.array([28520,28526,28943,28944,29383,29384,30239,30240])
    models = {}
    for j, key in enumerate(r.SNAPSHOT_ORDER):
        for rid in (2,7):
            model, _ = fit_rule(bank(), 2, 201, slice(0,70), 178)
            model["alpha"] = (j+1)/10 if rid==7 else .1
            models[key,rid] = model
    acts, _ = r.scheduled_actions(b, models, 7)
    a = np.array([0,.1,.1,.2,.2,.3,.3,.4])[:,None]
    np.testing.assert_allclose(acts, b["safe"]+a*(b["cost"]-b["safe"]), rtol=0, atol=0)
    fixed, _ = r.scheduled_actions(b, models, 2)
    np.testing.assert_allclose(fixed,b["safe"]+.1*(b["cost"]-b["safe"]),rtol=0,atol=0)


@pytest.mark.parametrize("key", ["anchors","shortfall","mask","reference","safe","cost","current_features","feedback_features"])
def test_prefix_rejects_any_mutated_input(key):
    b=bank(); full=copy.deepcopy(b)
    assert r.verify_prefix(b, full)==120
    flat=full[key].flat
    flat[0] = not flat[0] if key=="mask" else flat[0]+1
    with pytest.raises(ValueError,match="prefix mismatch"):
        r.verify_prefix(b,full)


def test_full_family_preserves_all_parent_comparisons():
    root=Path(repository_root())
    p=root/"experiments/conditional_refine_20261025_v2/recovered/results/campaign/inference_span3.json"
    parent=json.loads(p.read_text())
    names, available, comps, aliases=r.build_extended_family(parent)
    assert len(names)==1256 and len(available)==1184
    assert len(comps)==5697 and len(aliases)==148
    assert all((f"GR{j:03d}_{a}","BR009_P") in comps for j in range(24) for a in r.META_ARMS)
    assert ("GR019_Z","GR022_Z") in comps
    assert ("GR014_P","GR008_P") in comps


def test_frozen_model_receipt_tamper(tmp_path):
    with pytest.raises(ValueError,match="All 24 models"):
        r._load_models(tmp_path,[])
    p=tmp_path/"m.joblib"; p.write_bytes(b"bad")
    q=tmp_path/"receipt.json"; q.write_text("{}")
    with pytest.raises(ValueError,match="hash mismatch"):
        r._load_models(tmp_path,[dict(path=p.name, receipt_path=q.name,sha256="bad",receipt_sha256="bad")])


def test_duplicate_freeze_refused_before_source_access(tmp_path):
    (tmp_path/"FINAL_FREEZE.json").write_text("{}")
    with pytest.raises(FileExistsError):
        r.run_freeze_stage(dict(freeze_wall_seconds=60),tmp_path)


def test_zero_target_is_valid_not_filtered():
    b=bank(); b["shortfall"][:]=0
    for rid in range(24):
        m, rec=fit_rule(b,rid,201,slice(0,70),178,min_samples_leaf=32)
        act,_=predict_rule(m,r.prediction_view(b))
        assert np.isfinite(act).all() and rec["valid_fit_cells"]==70*16


def test_complete_history_freeze_and_all_fifteen_evaluations(tmp_path,monkeypatch):
    """Exercise the actual runner and disk barrier with constructed observations."""
    b=bank(n=50,nodes=2)
    b["anchors"]=np.r_[np.arange(28087,28097),np.arange(28526,28536),
        np.arange(28944,28954),np.arange(29384,29394),np.arange(30000,30010)]
    b["metadata"]={}
    full=copy.deepcopy(b)
    for k in ("safe","cost","shortfall","mask","reference","current_features","feedback_features"):
        full[k]=np.concatenate([b[k],b[k][:10]])
    full["anchors"]=np.r_[b["anchors"],np.arange(30240,30250)]
    full["metadata"]={}
    from windfarm_moe.release_gate import build_recipes
    cfg=dict(history_wall_seconds=600,freeze_wall_seconds=60,evaluation_wall_seconds=120,recipes=build_recipes())
    monkeypatch.setattr(r,"verify_source_hashes",lambda *a,**k: {"x":"y"})
    monkeypatch.setattr(r,"verify_budget_and_recipes",lambda *a:cfg["recipes"])
    monkeypatch.setattr(r,"verify_direct_parent_provenance",lambda *a,**k:None)
    monkeypatch.setattr(r,"_verify_historical_bank_contract",lambda *a: {})
    monkeypatch.setattr(r,"EXPECTED_FULL_STEPS",60)
    monkeypatch.setattr(r,"EXPECTED_EVAL_VALID_CELLS",20)
    opens=[]
    def builder(cfg,seed,arm,include_evaluation=False,root=None):
        opens.append(include_evaluation)
        ans=copy.deepcopy(full if include_evaluation else b)
        ans["metadata"]["arm"]=arm
        return ans
    monkeypatch.setattr(r,"build_release_bank",builder)
    orig=r._score_canonical_or_raw_phase
    def score(**kw):
        # Constructed source has no archived endpoint: use direct scoring only.
        kw["recipe_id"]=2
        return orig(**kw)
    monkeypatch.setattr(r,"_score_canonical_or_raw_phase",score)
    ps=r._save_protocol_copies(cfg,tmp_path,None)
    for arm in r.META_ARMS:
        r.save(tmp_path/"s0"/f"{arm}_seed201_receipt.json",dict(status="COMPLETED",protocol_sha256=ps))
    for shard in range(15):
        rcpt=r.run_history_shard(cfg,tmp_path,shard)
        assert len(rcpt["models"])==96 and not rcpt["evaluation_touched"]
    assert not any(opens)
    freeze=r.run_freeze_stage(cfg,tmp_path)
    assert len(freeze["histories"])==15 and freeze["model_records"]==1440
    with pytest.raises(FileExistsError):r.run_freeze_stage(cfg,tmp_path)
    for shard in range(15):
        rcpt=r.run_evaluate_shard(cfg,tmp_path,shard)
        assert rcpt["evaluated_recipe_ids"]==list(range(24))
        assert rcpt["selection_did_not_filter"]
    assert sum(opens)==15
    hist=freeze["histories"][0]
    p=tmp_path/hist["models"][0]["path"]
    p.write_bytes(p.read_bytes()+b"tamper")
    with pytest.raises(ValueError,match="hash mismatch"):
        r._load_models(tmp_path,hist["models"])


def test_parallel_protocol_publication_is_atomic(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    cfg={"payload":"x"*100000}
    with ThreadPoolExecutor(max_workers=15) as pool:
        hashes=list(pool.map(lambda _:r._save_protocol_copies(cfg,tmp_path,None),range(45)))
    assert len(set(hashes))==1
    assert json.loads((tmp_path/"protocol_original.json").read_text())==cfg

