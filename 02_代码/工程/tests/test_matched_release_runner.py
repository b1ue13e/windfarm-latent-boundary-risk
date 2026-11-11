from repo_paths import Path, repository_root
import copy,json
import numpy as np
import pytest
from scripts import run_matched_release as r
from windfarm_moe.release_gate import build_recipes
from windfarm_moe.matched_endpoint_bank import select_legal_anchors

def test_real_parent_full_family():
    root=Path(repository_root())
    parent=json.loads((root/'experiments/prospective_release_20261025/recovered/results/campaign/inference_span3.json').read_text())
    names,avail,pairs,aliases=r.build_family(parent)
    assert (len(names),len(avail),len(pairs),len(aliases))==(1400,1256,7257,152)
    assert names[:1256]==parent['policy_names']

def test_constructed_complete_history_freeze_evaluation(tmp_path,monkeypatch):
    def builder(cfg,seed,arm,v,include_evaluation=False,root=None):
        a=np.arange(27648,35273)
        sel=select_legal_anchors(a,v,include_evaluation);a=a[sel]
        n=len(a);base=np.broadcast_to(20+np.sin(a[:,None]/144), (n,3)).copy()
        cost=base+np.broadcast_to(np.cos(a[:,None]/155),base.shape)
        cur=np.stack([base,base,cost,cost-base,np.ones_like(base)],axis=-1)
        fb=np.concatenate([cur,np.zeros((n,3,6))],axis=-1)
        return dict(anchors=a,safe=base,cost=cost,shortfall=np.full_like(base,10),mask=np.ones_like(base,dtype=bool),
            reference=base.copy(),current_features=cur,feedback_features=fb,metadata=dict(vintage=v,
                phase_restarts=0,include_evaluation=include_evaluation,feedback_release_trace=(a-8).tolist()))
    monkeypatch.setattr(r,'build_matched_bank',builder)
    original_check=r.check_bank
    def check(b,v,evaluate=False):
        if not evaluate:original_check(b,v,False)
        else:assert len(b['anchors'])==(7172 if v=='inner' else 6322)
    monkeypatch.setattr(r,'check_bank',check)
    cfg=dict(recipes=build_recipes(),source_hashes={})
    r._save_protocol_copies(cfg,tmp_path,None);proto=r.sha(tmp_path/'protocol_original.json')
    for arm in ('C','P','Z'):r.save(tmp_path/'s0'/f'{arm}.json',dict(status='COMPLETED',protocol_sha256=proto))
    for shard in range(15):r.history(cfg,tmp_path,shard,deadline=10**20)
    assert not (tmp_path/'full_bank_metadata').exists()
    r.freeze(cfg,tmp_path,deadline=10**20)
    f=json.loads((tmp_path/'FINAL_FREEZE.json').read_text())
    assert (f['model_records'],f['actual_tree_fits'],f['actual_global_fits'])==(2520,1680,105)
    with pytest.raises(FileExistsError):r.freeze(cfg,tmp_path,deadline=10**20)
    for shard in range(15):r.evaluate(cfg,tmp_path,shard,deadline=10**20)
    for v in ('inner','outer'):
        rec,arr=r.read_phase(tmp_path,v,'evaluate',201,'Z')
        assert arr['ledger'].shape==(24,35,4)
        assert len(rec['policies'])==24
    record=f['histories'][0]['versions']['inner']['models'][0]
    p=tmp_path/record['path'];p.write_bytes(p.read_bytes()+b'tamper')
    with pytest.raises(ValueError,match='identity changed'):
        r._load_models(tmp_path,f['histories'][0]['versions']['inner']['models'],'inner')

