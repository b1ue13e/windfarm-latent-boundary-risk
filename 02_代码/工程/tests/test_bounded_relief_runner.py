import hashlib
import json
import os
from repo_paths import Path, repository_root
import time

import numpy as np
import pytest

import scripts.run_bounded_relief as runner
from scripts.run_mixture_closed_loop import save, score_actions, sha
from windfarm_moe.actual_mixture_update import MixtureConfig
from windfarm_moe.bounded_relief import run_signed, signed_action, signed_experts


def _write_cache_with_manifest(cache_dir: Path, anchors: np.ndarray, y: np.ndarray, m: np.ndarray, seeds=(201, 202, 203, 204, 205)):
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(cache_dir / "anchors.npy", anchors)
    np.save(cache_dir / "shortfall.npy", y)
    np.save(cache_dir / "mask.npy", m)
    rng = np.random.default_rng(1024)
    for seed in seeds:
        for arm_idx, arm in enumerate(("P", "Z")):
            x = rng.uniform(1.0, 15.0, (*y.shape, 9))
            x[:, :, 0] = 4.0
            np.save(cache_dir / f"{arm}_seed{seed}.npy", x)

    files = {}
    for p in sorted(cache_dir.glob("*.npy")):
        files[p.name] = dict(bytes=p.stat().st_size, sha256=sha(p))
    save(cache_dir / "manifest.json", dict(files=files))
    return sha(cache_dir / "manifest.json")


def _build_synthetic_campaign_fixture(tmp_path: Path, monkeypatch):
    hist_cache = tmp_path / "hist_cache"
    eval_cache = tmp_path / "eval_cache"
    parent_dir = tmp_path / "parent_results"
    profiles_dir = parent_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)

    # Historical anchors: 27648..27671 (24 steps)
    # inner: [27658, 27664), cut=27650 -> fit [27648, 27650) max=27649, 27649+7=27656 < 27658
    # outer: [27664, 27670), cut=27656 -> fit [27648, 27656) max=27655, 27655+7=27662 < 27664
    # evaluate: [30240, 35275), cut=27664 -> fit [27648, 27664) max=27663, 27663+7=27670 < 30240
    monkeypatch.setitem(runner.PHASES, "inner", (27658, 27664, 27650))
    monkeypatch.setitem(runner.PHASES, "outer", (27664, 27670, 27656))
    monkeypatch.setitem(runner.PHASES, "evaluate", (30240, 35275, 27664))

    ha = np.arange(27648, 27672, dtype=np.int64)
    hy = np.full((len(ha), 2), 6.0, dtype=np.float64)
    hy[::2, 1] = 11.0
    hm = np.ones_like(hy, dtype=bool)
    hm[12, 1] = False
    hist_manifest_sha = _write_cache_with_manifest(hist_cache, ha, hy, hm)

    # 35 natural days on evaluation: first 8 anchors are 1-step apart on day 210 so first 8 actions precede any maturity,
    # followed by 34 anchors across days 211..244 (total 35 natural days).
    ea_day0 = 210 * 144 + np.arange(8, dtype=np.int64)
    ea_rest = np.arange(211, 245, dtype=np.int64) * 144 + 10
    ea = np.concatenate([ea_day0, ea_rest])
    monkeypatch.setitem(runner.PHASES, "evaluate", (int(ea[0]), int(ea[-1]) + 1, 27664))
    ey = np.full((len(ea), 2), 7.0, dtype=np.float64)
    ey[1::3, 0] = 13.0
    em = np.ones_like(ey, dtype=bool)
    em[4, 1] = False
    eval_manifest_sha = _write_cache_with_manifest(eval_cache, ea, ey, em)

    parent_profiles = {}
    for seed in runner.SEEDS:
        b_h = np.full_like(hy, 5.0 + 0.05 * (seed - 201))
        p_h = profiles_dir / f"historical_seed{seed}.npy"
        np.save(p_h, b_h)
        parent_profiles[f"profiles/historical_seed{seed}.npy"] = dict(
            path=str(p_h), sha256=sha(p_h), bytes=p_h.stat().st_size
        )

        b_e = np.full_like(ey, 5.5 + 0.05 * (seed - 201))
        p_e = profiles_dir / f"evaluate_seed{seed}.npy"
        np.save(p_e, b_e)
        parent_profiles[f"profiles/evaluate_seed{seed}.npy"] = dict(
            path=str(p_e), sha256=sha(p_e), bytes=p_e.stat().st_size
        )

    # Construct 416 parent policies and 807 parent comparisons
    parent_names = ["REF"]
    for i in range(1, 412):
        if i == 365:
            parent_names.append("R0182_P")
        elif i == 373:
            parent_names.append("R0186_P")
        elif i == 374:
            parent_names.append("R0186_Z")
        else:
            parent_names.append(f"PARENT_{i:04d}")
    parent_names.extend(["GUARDED_FIXED_P", "GUARDED_FIXED_Z", "GUARDED_ONLINE_P", "GUARDED_ONLINE_Z"])
    assert len(parent_names) == 416

    parent_comps = []
    for idx in range(1, 416):
        parent_comps.append([idx, 0])
    for idx in range(1, 393):
        parent_comps.append([idx, (idx % 415) + 1 if (idx % 415) + 1 != idx else 0])
    assert len(parent_comps) == 807

    parent_ledger = np.ones((5, 416, 35, 4), dtype=np.float64)
    eval_counts = None
    eval_days = None
    for si, seed in enumerate(runner.SEEDS):
        x_p = np.load(eval_cache / f"P_seed{seed}.npy")
        ref_led, counts, day_ids = score_actions(x_p[:, :, 0], ey, em, ea)
        parent_ledger[si, :] = ref_led[None, :, :]
        eval_counts = counts
        eval_days = day_ids

    np.savez_compressed(
        parent_dir / "all_daily_ledger.npz",
        ledger=parent_ledger,
        counts=eval_counts,
        day_ids=eval_days,
    )
    parent_span3 = dict(
        schema="autonomous-campaign-inference-v1",
        policy_names=parent_names,
        available=[True] * 416,
        family_definition=dict(
            policy_names=parent_names,
            comparisons=parent_comps,
            frozen_aliases=[[2, 1]],
        ),
    )
    save(parent_dir / "inference_span3.json", parent_span3)

    src_file = tmp_path / "dummy_source.py"
    src_file.write_text("# synthetic source\n", encoding="utf-8")

    cfg = dict(
        study_id="bounded_relief_synthetic_test",
        max_candidates=48,
        max_cpu_seconds=14400,
        shard_wall_seconds=600,
        aggregate_wall_seconds=1200,
        fit_time_limit_seconds=1.0,
        expected_historical_grid=False,
        expected_evaluation_anchors=len(ea),
        expected_evaluation_valid_cells=int(em.sum()),
        historical_cache=str(hist_cache),
        historical_manifest_sha256=hist_manifest_sha,
        evaluation_cache=str(eval_cache),
        evaluation_manifest_sha256=eval_manifest_sha,
        parent_results=str(parent_dir),
        parent_ledger_sha256=sha(parent_dir / "all_daily_ledger.npz"),
        parent_span3_sha256=sha(parent_dir / "inference_span3.json"),
        parent_profiles=parent_profiles,
        recipes=runner.build_recipes(),
        source_hashes={"dummy_source.py": sha(src_file)},
        inference=dict(spans=[3, 1, 7], n_boot=4, seed=20261022),
    )
    protocol_path = tmp_path / "protocol.json"
    save(protocol_path, cfg)
    return cfg, protocol_path, tmp_path


def test_recipe_factory_and_shard_mapping_deterministic():
    recipes = runner.build_recipes()
    assert len(recipes) == 48
    assert [r["id"] for r in recipes] == list(range(48))
    assert recipes[0] == dict(
        id=0,
        relief=0.0,
        goal="COST",
        mode="FIXED",
        config=dict(eta=0.0, schedule_power=0.5, severity_step=0.0, cost_scale=100.0),
    )
    assert recipes[47] == dict(
        id=47,
        relief=1.0,
        goal="CAP",
        mode="ONLINE_C",
        config=dict(eta=0.3, schedule_power=0.5, severity_step=10.0, cost_scale=100.0),
    )
    for r in recipes:
        assert "proximity" not in r["config"]
        assert set(r["config"].keys()) == {"eta", "schedule_power", "severity_step", "cost_scale"}
        assert r["config"]["schedule_power"] == 0.5
        assert r["config"]["cost_scale"] == 100.0

    mapped = [runner.shard_assignment(s) for s in range(10)]
    assert mapped == [
        (201, "P"), (201, "Z"),
        (202, "P"), (202, "Z"),
        (203, "P"), (203, "Z"),
        (204, "P"), (204, "Z"),
        (205, "P"), (205, "Z"),
    ]


def test_current_mask_does_not_gate_actions_and_raw_target_scored():
    rng = np.random.default_rng(77)
    b = rng.uniform(4.0, 10.0, (10, 3))
    x = rng.uniform(0.0, 18.0, (10, 3, 9))
    y = rng.uniform(0.0, 20.0, (10, 3))
    a = np.arange(10, dtype=np.int64)
    w0 = np.full(10, 0.1)
    cfgs = [MixtureConfig(eta=0.03, schedule_power=0.5, severity_step=1.0)]

    m1 = np.ones_like(y, dtype=bool)
    m2 = m1.copy()
    # Mask out current issue i=8 (after issue 0 matures) and check action at i=8 is identical
    m2[8, :] = False
    y2 = y.copy()
    y2[8, :] = np.nan

    res1 = run_signed(x, b, y, m1, a, cfgs, w0, relief=0.1, score=False, return_actions=True)
    res2 = run_signed(x, b, y2, m2, a, cfgs, w0, relief=0.1, score=False, return_actions=True)
    np.testing.assert_array_equal(res1["actions"], res2["actions"])

    # Verify first 8 actions match static signed_action bitwise
    delta = signed_experts(x, b, relief=0.1)
    static = signed_action(b, delta, w0, relief=0.1)
    np.testing.assert_array_equal(res1["actions"][0, :8], static[:8])


def test_barrier_freeze_rejects_missing_history_and_evaluate_rejects_unfrozen(tmp_path, monkeypatch):
    cfg, protocol_path, root = _build_synthetic_campaign_fixture(tmp_path, monkeypatch)
    out = tmp_path / "out"

    # Freeze before any history shard -> rejected
    with pytest.raises(ValueError, match="Missing history shard receipt"):
        runner.run_freeze_stage(cfg, out, protocol_path=protocol_path, root=root)

    # Evaluate before freeze -> rejected
    with pytest.raises(ValueError, match="FINAL_FREEZE.json"):
        runner.run_evaluate_shard(cfg, out, 0, protocol_path=protocol_path, root=root)


def test_full_synthetic_pipeline_and_preserved_failure_slots(tmp_path, monkeypatch):
    cfg, protocol_path, root = _build_synthetic_campaign_fixture(tmp_path, monkeypatch)
    out = tmp_path / "out"

    # Simplify fit_signed to fast deterministic weights so 360 fits run in <0.5s,
    # and inject one initializer failure on shard 0 to test anchor e0 fallback.
    real_fit_signed = runner.fit_signed
    call_counter = {"count": 0}

    def fast_fit_signed(x, b, y, *, relief=0.0, goal="COST", time_limit=10.0, **kwargs):
        call_counter["count"] += 1
        if call_counter["count"] == 1:
            raise RuntimeError("synthetic solver failure on first initializer")
        w = np.zeros(10, dtype=np.float64)
        w[0] = 0.7
        w[1] = 0.3
        u = float(np.maximum(y.reshape(-1) - b.reshape(-1), 0.0).mean())
        c = float((b.reshape(-1) + 10.0 * np.maximum(y.reshape(-1) - b.reshape(-1), 0.0)).mean() / 6.0)
        return dict(
            weights=w.tolist(),
            raw_bundle_weights=w.tolist(),
            canonical_initial=w.tolist(),
            status="OPTIMAL_NUMERICAL_BOUNDS",
            bundle_status="OPTIMAL_NUMERICAL_BOUNDS",
            optimal=True,
            bundle_optimal=True,
            objective=c,
            bundle_objective=c,
            lower_bound=c,
            gap=0.0,
            mean_uncovered_power=u,
            bundle_mean_uncovered_power=u,
            uncovered_cap=(u if goal == "CAP" else None),
            anchor_mean_uncovered_power=u,
            anchor_objective=c,
            actual_affine_feasible=True,
            repaired_to_anchor=False,
            repair_alpha=0.0,
            boundary_guard_count=0,
            max_boundary_violation=0.0,
            relief=float(relief),
            goal=goal,
            time_limit=float(time_limit),
            support_smoothing=0.0,
        )

    monkeypatch.setattr(runner, "fit_signed", fast_fit_signed)

    # Ensure history never reads evaluation_cache by spying on verify_cache and np.load while keeping cfg == protocol
    eval_cache_resolved = Path(cfg["evaluation_cache"]).resolve()
    real_np_load = runner.np.load
    real_verify_cache = runner.verify_cache

    def guarded_np_load(file, *args, **kwargs):
        if isinstance(file, (str, os.PathLike)):
            p = Path(file).resolve()
            if p == eval_cache_resolved or eval_cache_resolved in p.parents:
                raise AssertionError(f"Evaluation cache read during history stage: {p}")
        return real_np_load(file, *args, **kwargs)

    def guarded_verify_cache(cache_dir, manifest_sha):
        p = Path(cache_dir).resolve()
        if p == eval_cache_resolved or eval_cache_resolved in p.parents:
            raise AssertionError(f"Evaluation cache verified during history stage: {p}")
        return real_verify_cache(cache_dir, manifest_sha)

    monkeypatch.setattr(np, "load", guarded_np_load)
    monkeypatch.setattr(runner, "verify_cache", guarded_verify_cache)
    for shard in range(10):
        rec = runner.run_history_shard(cfg, out, shard, protocol_path=protocol_path, root=root)
        assert rec["initializers_fitted"] == 36
        assert not rec["evaluation_cache_read"]
    monkeypatch.setattr(np, "load", real_np_load)
    monkeypatch.setattr(runner, "verify_cache", real_verify_cache)

    # Check fallback initializer on shard 0 (P_seed201, inner, COST, d=0.0)
    fb_init = json.loads(
        (out / runner.initializer_relpath("inner", "P", 201, "COST", 0.0)).read_text(encoding="utf-8")
    )
    assert fb_init["status"] == "INITIALIZER_ERROR_DECLARED_ANCHOR_FALLBACK"
    assert fb_init["canonical_initial"] == [1.0] + [0.0] * 9
    assert fb_init["last_label_release"] < fb_init["episode_start"]

    # Freeze stage
    freeze = runner.run_freeze_stage(cfg, out, protocol_path=protocol_path, root=root)
    assert len(freeze["all_initializers"]) == 360
    assert (out / "EVALUATION_OPEN.json").exists()
    outer_sel = json.loads((out / "outer_selection.json").read_text(encoding="utf-8"))
    assert outer_sel["qualification_did_not_filter_instances"]
    assert set(outer_sel["roles"].keys()) == {"COST_P", "CAP_P", "COST_Z", "CAP_Z"}

    # Capture all existing freeze bytes before duplicate freeze attempt
    freeze_files = [
        out / "FINAL_FREEZE.json",
        out / "EVALUATION_OPEN.json",
        out / "shards" / "freeze" / "state.json",
        out / "protocol_original.json",
        out / "protocol.json",
        out / "source_versions.json",
    ]
    before_bytes = {p: p.read_bytes() for p in freeze_files}

    # Second freeze attempt must fail BEFORE ANY write and keep all existing freeze bytes identical
    with pytest.raises(FileExistsError):
        runner.run_freeze_stage(cfg, out, protocol_path=protocol_path, root=root)
    for p, raw in before_bytes.items():
        assert p.read_bytes() == raw
    assert not (out / "shards" / "freeze" / "failure.json").exists()
    runner.verify_freeze_barrier(cfg, out, protocol_path=protocol_path, root=root)

    # Inject a single recipe failure on shard 0 evaluate for ONLINE_C (gamma=10, d=1.0, CAP -> recipe 47)
    real_run_signed = runner.run_signed

    def faulty_run_signed(delta, b, y, m, a, configs, w0, *, relief=0.0, **kwargs):
        if float(relief) == 1.0 and any(c.severity_step == 10.0 for c in configs):
            if len(configs) > 1 or configs[0].severity_step == 10.0:
                raise FloatingPointError("synthetic isolated recipe failure on recipe 47")
        return real_run_signed(delta, b, y, m, a, configs, w0, relief=relief, **kwargs)

    monkeypatch.setattr(runner, "run_signed", faulty_run_signed)
    runner.run_evaluate_shard(cfg, out, 0, protocol_path=protocol_path, root=root)

    # Restore normal run_signed for shards 1..9
    monkeypatch.setattr(runner, "run_signed", real_run_signed)
    for shard in range(1, 10):
        runner.run_evaluate_shard(cfg, out, shard, protocol_path=protocol_path, root=root)

    # Inspect shard 0 evaluate receipt: recipe 47 and 43 failed (both have d=1.0 and gamma=10.0), others completed
    r0 = json.loads((out / "instances/evaluate/P_seed201/receipt.json").read_text(encoding="utf-8"))
    d0 = np.load(out / "instances/evaluate/P_seed201/daily.npz")
    assert d0["ledger"].shape == (48, 35, 4)
    assert r0["status"]["47"] == "FAILED_PRESERVED"
    assert np.isnan(d0["ledger"][47]).all()
    assert r0["status"]["46"] == "COMPLETED"
    assert np.isfinite(d0["ledger"][46]).all()

    # Aggregate stage
    completion = runner.run_aggregate_stage(cfg, out, protocol_path=protocol_path, root=root, n_boot_override=4)
    assert completion["status"] == "COMPLETED_WITH_PRESERVED_FAILURES"
    assert completion["all_planned_instances_retained"]
    assert not completion["scientific_qualification_used_to_filter"]
    assert not completion["independent_confirmation"]
    assert completion["planned_recipes"] == 48
    assert completion["planned_instances_per_phase"] == 480
    assert completion["complete_per_phase"]["inner"] == 480
    assert completion["complete_per_phase"]["outer"] == 480
    assert completion["complete_per_phase"]["evaluate"] == 478
    assert completion["failed_per_phase"]["inner"] == 0
    assert completion["failed_per_phase"]["outer"] == 0
    assert completion["failed_per_phase"]["evaluate"] == 2
    assert sum(completion["complete_per_phase"].values()) + sum(completion["failed_per_phase"].values()) == 1440

    all_names = json.loads((out / "all_policy_names.json").read_text(encoding="utf-8"))
    assert len(all_names["names"]) == 512
    assert all_names["parent_policy_count"] == 416
    assert all_names["new_policy_count"] == 96
    assert all_names["parent_comparison_count"] == 807
    assert all_names["total_comparison_count"] == 807 + 504
    # BR047_P (index 416 + 2*47 = 510) has NaN on seed 201 -> available=False; BR047_Z (511) has available=True
    assert not all_names["available"][416 + 2 * 47]
    assert all_names["available"][416 + 2 * 47 + 1]

    for span in (3, 1, 7):
        assert (out / f"inference_span{span}.json").exists()

    # Verify rejection checks directly on fresh copies of the frozen `out` fixture
    import shutil

    def _fresh_frozen_out(name: str) -> Path:
        dest = tmp_path / name
        shutil.copytree(out / "initializers", dest / "initializers")
        shutil.copyfile(out / "FINAL_FREEZE.json", dest / "FINAL_FREEZE.json")
        shutil.copyfile(out / "EVALUATION_OPEN.json", dest / "EVALUATION_OPEN.json")
        return dest

    # 0. Mutating cfg while retaining original protocol_path is caught at protocol semantic barrier
    out_pop0 = _fresh_frozen_out("out_pop0")
    bad_pop_cfg = dict(cfg, expected_evaluation_valid_cells=999999)
    with pytest.raises(ValueError, match="Supplied cfg differs from parsed original protocol"):
        runner.run_evaluate_shard(bad_pop_cfg, out_pop0, 0, protocol_path=protocol_path, root=root)
    assert (out_pop0 / "shards" / "evaluate" / "shard_00_P_seed201" / "failure.json").exists()

    # 1. Wrong evaluation population rejected (when protocol_path is None and protocol_original is not present)
    out_pop1 = _fresh_frozen_out("out_pop1")
    with pytest.raises(ValueError, match="Evaluation population differs"):
        runner.run_evaluate_shard(bad_pop_cfg, out_pop1, 0, protocol_path=None, root=root)
    assert (out_pop1 / "shards" / "evaluate" / "shard_00_P_seed201" / "failure.json").exists()

    # 2. Tampered parent profile file rejected on disk against frozen protocol SHA
    out_pop2 = _fresh_frozen_out("out_pop2")
    eval_prof_202 = Path(cfg["parent_profiles"]["profiles/evaluate_seed202.npy"]["path"])
    orig_prof_bytes = eval_prof_202.read_bytes()
    try:
        np.save(eval_prof_202, np.ones((len(cfg["parent_profiles"]) and int(cfg["expected_evaluation_anchors"]), 2), dtype=np.float64) * 9.99)
        with pytest.raises(ValueError, match="Parent profile (sha256|byte size) mismatch"):
            runner.run_evaluate_shard(cfg, out_pop2, 2, protocol_path=protocol_path, root=root)
    finally:
        eval_prof_202.write_bytes(orig_prof_bytes)

    # 3. Tampered parent ledger file on disk rejected in aggregate
    parent_ledger_file = Path(cfg["parent_results"]) / "all_daily_ledger.npz"
    orig_ledger_bytes = parent_ledger_file.read_bytes()
    try:
        parent_ledger_file.write_bytes(b"corrupted_npz")
        with pytest.raises(ValueError, match="Parent all_daily_ledger.npz missing or SHA mismatch"):
            runner.run_aggregate_stage(cfg, out, protocol_path=protocol_path, root=root, n_boot_override=4)
    finally:
        parent_ledger_file.write_bytes(orig_ledger_bytes)

    # 4. Tampered parent span3 file on disk rejected in aggregate
    parent_span3_file = Path(cfg["parent_results"]) / "inference_span3.json"
    orig_span3_bytes = parent_span3_file.read_bytes()
    try:
        parent_span3_file.write_text('{"tampered": true}\n', encoding="utf-8")
        with pytest.raises(ValueError, match="Parent inference_span3.json missing or SHA mismatch"):
            runner.run_aggregate_stage(cfg, out, protocol_path=protocol_path, root=root, n_boot_override=4)
    finally:
        parent_span3_file.write_bytes(orig_span3_bytes)

    # 5. Tampered evaluate shard receipt freeze_sha256 or bindings rejected in aggregate
    eval_r0_path = out / "shards" / "evaluate" / "shard_00_P_seed201" / "receipt.json"
    orig_eval_r0 = eval_r0_path.read_bytes()
    try:
        bad_r0 = json.loads(orig_eval_r0.decode("utf-8"))
        bad_r0["freeze_sha256"] = "0" * 64
        save(eval_r0_path, bad_r0)
        with pytest.raises(ValueError, match="Evaluate shard 0 freeze_sha256 does not match current FINAL_FREEZE.json"):
            runner.run_aggregate_stage(cfg, out, protocol_path=protocol_path, root=root, n_boot_override=4)

        bad_r0 = json.loads(orig_eval_r0.decode("utf-8"))
        bad_r0["parent_profile_sha256"] = "1" * 64
        save(eval_r0_path, bad_r0)
        with pytest.raises(ValueError, match="Evaluate shard 0 parent_profile_sha256 mismatch"):
            runner.run_aggregate_stage(cfg, out, protocol_path=protocol_path, root=root, n_boot_override=4)
    finally:
        eval_r0_path.write_bytes(orig_eval_r0)

    # 6. Targeted freeze rejection tests for tampered history receipt protocol_sha256, initializer sha256, and freeze_wall_seconds
    def _fresh_history_out(name: str) -> Path:
        dest = tmp_path / name
        shutil.copytree(out / "shards" / "history", dest / "shards" / "history")
        shutil.copytree(out / "initializers", dest / "initializers")
        shutil.copytree(out / "instances" / "inner", dest / "instances" / "inner")
        shutil.copytree(out / "instances" / "outer", dest / "instances" / "outer")
        return dest

    # 6a. Freeze deadline uses freeze_wall_seconds (default 60), so freeze_wall_seconds=10 (<30s safety margin) triggers immediate TimeoutError
    out_tamper_a = _fresh_history_out("out_tamper_a")
    cfg_short_freeze = dict(cfg, freeze_wall_seconds=10, shard_wall_seconds=600)
    short_proto = tmp_path / "protocol_short_freeze.json"
    save(short_proto, cfg_short_freeze)
    with pytest.raises(TimeoutError):
        runner.run_freeze_stage(cfg_short_freeze, out_tamper_a, protocol_path=short_proto, root=root)

    # 6b. Tampered history shard receipt protocol_sha256 rejected by freeze
    out_tamper_b = _fresh_history_out("out_tamper_b")
    hist_r3_path = out_tamper_b / "shards" / "history" / "shard_03_Z_seed202" / "receipt.json"
    bad_h3 = json.loads(hist_r3_path.read_text(encoding="utf-8"))
    bad_h3["protocol_sha256"] = "a" * 64
    save(hist_r3_path, bad_h3)
    with pytest.raises(ValueError, match="History shard 3 protocol_sha256 differs from current protocol"):
        runner.run_freeze_stage(cfg, out_tamper_b, protocol_path=protocol_path, root=root)

    # 6c. Tampered initializer file on disk rejected against recorded history receipt initializer sha256 BEFORE recertifying
    out_tamper_c = _fresh_history_out("out_tamper_c")
    target_init = out_tamper_c / runner.initializer_relpath("evaluate", "P", 201, "COST", 0.0)
    tampered_init = json.loads(target_init.read_text(encoding="utf-8"))
    tampered_init["objective"] = 999999.0
    save(target_init, tampered_init)
    with pytest.raises(ValueError, match="sha256 mismatch against history shard 0 receipt"):
        runner.run_freeze_stage(cfg, out_tamper_c, protocol_path=protocol_path, root=root)


