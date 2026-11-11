"""Constructed NPZ receipts exercise the real-format loader, not real assets."""
import json
from repo_paths import Path, repository_root
import hashlib
import numpy as np
import pytest
import windfarm_moe.budget_sources as source_module
from windfarm_moe.budget_sources import ARCHIVED_SPEC,file_sha256,verify_bound_archives
from windfarm_moe.budget_diagnostic_core import SEEDS


def test_hashed_archive_adapter_and_corruption_stop(tmp_path,monkeypatch):
    spec=ARCHIVED_SPEC;a=np.arange(spec.anchor_start,spec.anchor_stop)
    shape=(len(a),134);m=np.zeros(shape,bool);m.flat[:spec.n_scored]=True
    r=np.ones(shape);target=np.zeros(shape)
    coords=tmp_path/'coordinates.npz'
    np.savez_compressed(coords,evaluate__anchors=a,evaluate__mask=m,evaluate__shortfall=target)
    actions=tmp_path/'actions.npz';np.savez_compressed(actions,P=r,Z=r)
    manifest=tmp_path/'manifest.json';manifest.write_text('{}',encoding='utf-8')
    idx=np.tile(np.arange(35),(20000,1));trace=tmp_path/'trace.npz';np.savez_compressed(trace,indices=idx)
    rules=tmp_path/'rules.json'
    rules.write_text(json.dumps(dict(family=dict(coordinate_order=['AP_M_U','AP_M_V','AP_S_U','AP_S_V','AZ_M_U','AZ_M_V','AZ_S_U','AZ_S_V']),
        inference=dict(n_boot=20000),pair=dict(seeds=SEEDS),population=dict(anchors_half_open=[30240,35273],expected_scored_N=672939))),encoding='utf-8')
    runs=[]
    for seed in SEEDS:
        runs.append(dict(seed=seed,local_manifest=str(manifest),local_manifest_sha256=file_sha256(manifest),
            P_action_key='P',Z_action_key='Z',members={p.name:dict(bytes=p.stat().st_size,sha256=file_sha256(p)) for p in (coords,actions)}))
    binding=tmp_path/'bindings.json'
    binding.write_text(json.dumps(dict(source_references={},runs=runs,
        draw_traces=[dict(span=3,local_path=str(trace),file_sha256=file_sha256(trace),indices_key='indices',
            index_shape=[20000,35],original_draw_sha256=hashlib.sha256(idx.tobytes()).hexdigest())])),encoding='utf-8')
    # Only the synthetic fixture's allowlisted document hashes are patched. The
    # production frozen hashes are neither edited nor weakened in the module.
    monkeypatch.setattr(source_module,'FROZEN_RULES_SHA256',file_sha256(rules))
    monkeypatch.setattr(source_module,'FROZEN_BINDINGS_SHA256',file_sha256(binding))
    before=file_sha256(actions)
    qualified=verify_bound_archives(binding,rules,{s:tmp_path for s in SEEDS},span=3)
    assert qualified.identity['receipt']['verified_bytes'] and file_sha256(actions)==before
    assert qualified.spec==ARCHIVED_SPEC
    with actions.open('ab') as stream:stream.write(b'CORRUPTED_SYNTHETIC_FIXTURE')
    with pytest.raises(ValueError,match='Archive byte identity'):
        verify_bound_archives(binding,rules,{s:tmp_path for s in SEEDS},span=3)


def test_frozen_rule_hash_is_checked_before_loading_any_archive(tmp_path):
    binding=tmp_path/'binding.json';rules=tmp_path/'rules.json'
    binding.write_text('{}');rules.write_text('{}')
    with pytest.raises(ValueError,match='Frozen V2 rules/source-binding bytes changed'):
        verify_bound_archives(binding,rules,{},span=3)
