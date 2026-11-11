from __future__ import annotations

import importlib.util
import json
from repo_paths import Path, repository_root
import shutil

import numpy as np
import pytest

import scripts.run_bounded_relief as runner
from scripts.run_mixture_closed_loop import save, sha
from windfarm_moe.actual_mixture_update import MixtureConfig
from windfarm_moe.bounded_relief import run_signed, signed_action, signed_experts


def _load_bounded_runner_test_module():
    path = Path(__file__).resolve().parent / "test_bounded_relief_runner.py"
    spec = importlib.util.spec_from_file_location("_test_bounded_relief_runner_mod", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_BR_TEST_MOD = _load_bounded_runner_test_module()
_build_synthetic_campaign_fixture = _BR_TEST_MOD._build_synthetic_campaign_fixture


def _fast_fit_signed(x, b, y, *, relief=0.0, goal="COST", time_limit=10.0, **kwargs):
    w = np.zeros(10, dtype=np.float64)
    w[0] = 0.75 if goal == "COST" else 0.55
    w[1] = 1.0 - w[0]
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


def _extend_parent_to_512_policies_and_1311_comps(parent_dir: Path, br_recipes: list[dict] | None = None) -> tuple[str, str]:
    """Extend the 416-policy / 807-comparison synthetic parent fixture to 512 policies / 1311 comparisons."""
    if br_recipes is None:
        br_recipes = runner.build_recipes()
    span3_path = parent_dir / "inference_span3.json"
    ledger_path = parent_dir / "all_daily_ledger.npz"

    span3 = json.loads(span3_path.read_text(encoding="utf-8"))
    names_512, avail_416, aliases, comps_1311 = runner.build_extended_family(
        span3,
        br_recipes,
        design="bounded_relief",
        expected_parent_policies=416,
        expected_parent_comparisons=807,
    )
    assert len(names_512) == 512
    assert len(comps_1311) == 1311

    z = np.load(ledger_path)
    old_ledger = np.asarray(z["ledger"], dtype=np.float64)
    counts = np.asarray(z["counts"])
    day_ids = np.asarray(z["day_ids"])
    assert old_ledger.shape == (5, 416, 35, 4)

    extra = np.repeat(old_ledger[:, :1, :, :], 96, axis=1)
    ledger_512 = np.concatenate([old_ledger, extra], axis=1)
    assert ledger_512.shape == (5, 512, 35, 4)

    np.savez_compressed(ledger_path, ledger=ledger_512, counts=counts, day_ids=day_ids)
    span3_512 = dict(
        schema="autonomous-campaign-inference-v1",
        policy_names=names_512,
        available=list(avail_416) + [True] * 96,
        family_definition=dict(
            policy_names=names_512,
            comparisons=[list(p) for p in comps_1311],
            frozen_aliases=[list(p) for p in aliases],
        ),
    )
    save(span3_path, span3_512)
    return sha(ledger_path), sha(span3_path)


def test_proximal_recipe_grid_and_protocol_verification():
    recipes = runner.build_proximal_recipes()
    assert len(recipes) == 48
    assert [r["id"] for r in recipes] == list(range(48))

    assert recipes[0] == dict(
        id=0,
        relief=0.0,
        goal="COST",
        mode="FIXED",
        config=dict(eta=0.0, schedule_power=0.5, severity_step=0.0, cost_scale=100.0, proximity_strength=0.0),
    )
    assert recipes[1] == dict(
        id=1,
        relief=0.0,
        goal="COST",
        mode="PROX_A",
        config=dict(eta=0.3, schedule_power=0.5, severity_step=10.0, cost_scale=100.0, proximity_strength=0.001),
    )
    assert recipes[2]["mode"] == "PROX_B" and recipes[2]["config"]["proximity_strength"] == 0.01
    assert recipes[3]["mode"] == "PROX_C" and recipes[3]["config"]["proximity_strength"] == 0.1
    assert recipes[47] == dict(
        id=47,
        relief=1.0,
        goal="CAP",
        mode="PROX_C",
        config=dict(eta=0.3, schedule_power=0.5, severity_step=10.0, cost_scale=100.0, proximity_strength=0.1),
    )

    for r in recipes:
        cfg = r["config"]
        assert set(cfg.keys()) == {"eta", "schedule_power", "severity_step", "cost_scale", "proximity_strength"}
        assert cfg["schedule_power"] == 0.5
        assert cfg["cost_scale"] == 100.0
        if r["mode"] == "FIXED":
            assert cfg["eta"] == 0.0 and cfg["severity_step"] == 0.0 and cfg["proximity_strength"] == 0.0
        else:
            assert cfg["eta"] == 0.3 and cfg["severity_step"] == 10.0
            assert cfg["proximity_strength"] in (0.001, 0.01, 0.1)

    assert runner.get_design({}) == "bounded_relief"
    assert runner.policy_prefix_for_design("bounded_relief") == "BR"
    assert runner.get_design({"design": "proximal_relief"}) == "proximal_relief"
    assert runner.policy_prefix_for_design("proximal_relief") == "PR"

    valid_prox_cfg = dict(design="proximal_relief", max_candidates=48, max_cpu_seconds=14400, recipes=recipes)
    assert runner.verify_budget_and_recipes(valid_prox_cfg) == recipes

    # Cross-design mismatch must be rejected
    with pytest.raises(ValueError, match="Recipe 0 does not match"):
        runner.verify_budget_and_recipes(
            dict(design="proximal_relief", max_candidates=48, max_cpu_seconds=14400, recipes=runner.build_recipes())
        )
    with pytest.raises(ValueError, match="Recipe 0 does not match"):
        runner.verify_budget_and_recipes(
            dict(design="bounded_relief", max_candidates=48, max_cpu_seconds=14400, recipes=recipes)
        )
    with pytest.raises(ValueError, match="Unsupported campaign design"):
        runner.get_design({"design": "unknown_design"})


def test_dynamic_extended_family_512_to_608_and_direct_br_pairings(tmp_path, monkeypatch):
    cfg, _, _ = _build_synthetic_campaign_fixture(tmp_path, monkeypatch)
    parent_dir = Path(cfg["parent_results"])

    # 1. Verify provisional 416 -> 512 generic extension works without hardcoding when parent is 416/807
    span3_416 = json.loads((parent_dir / "inference_span3.json").read_text(encoding="utf-8"))
    names_from_416, _, _, comps_from_416 = runner.build_extended_family(
        span3_416,
        runner.build_recipes(),
        design="bounded_relief",
    )
    assert len(names_from_416) == 512
    assert len(comps_from_416) == 1311

    # 2. Extend parent descriptor to 512 roles / 1311 comparisons (matching actual stage-1 bounded_relief output)
    _extend_parent_to_512_policies_and_1311_comps(parent_dir)
    span3_512 = json.loads((parent_dir / "inference_span3.json").read_text(encoding="utf-8"))

    prox_recipes = runner.build_proximal_recipes()
    names_608, parent_avail, aliases, comps_1911 = runner.build_extended_family(
        span3_512,
        prox_recipes,
        design="proximal_relief",
        expected_parent_policies=512,
        expected_parent_comparisons=1311,
    )
    assert len(names_608) == 608
    assert len(parent_avail) == 512
    assert names_608[512] == "PR000_P"
    assert names_608[-1] == "PR047_Z"
    assert len(comps_1911) == 1911
    assert 11 * len(names_608) + 10 * len(comps_1911) == 25798

    new_comps = comps_1911[1311:]
    assert len(new_comps) == 600
    comp_set = set(new_comps)

    # Check direct new FIXED vs old BR FIXED (24 pairs) and new PR online vs old BR ONLINE_C base_id+3 (72 pairs)
    fixed_vs_br_fixed = []
    online_vs_br_online_c = []
    for r in prox_recipes:
        rid = int(r["id"])
        base_id = (rid // 4) * 4
        for arm in ("P", "Z"):
            pol = f"PR{rid:03d}_{arm}"
            if r["mode"] == "FIXED":
                pair = (pol, f"BR{rid:03d}_{arm}")
                assert pair in comp_set
                fixed_vs_br_fixed.append(pair)
            else:
                pair = (pol, f"BR{base_id + 3:03d}_{arm}")
                assert pair in comp_set
                online_vs_br_online_c.append(pair)
                # Also paired with same-d, same-goal PR FIXED
                assert (pol, f"PR{base_id:03d}_{arm}") in comp_set
    assert len(fixed_vs_br_fixed) == 24
    assert len(online_vs_br_online_c) == 72

    # Missing BR parent policy in proximal_relief design must raise ValueError
    broken_span3 = json.loads(json.dumps(span3_512))
    broken_names = [n if n != "BR003_P" else "REMOVED_BR003_P" for n in broken_span3["policy_names"]]
    broken_span3["policy_names"] = broken_names
    broken_span3["family_definition"]["policy_names"] = broken_names
    with pytest.raises(ValueError, match="Missing parent ONLINE_C comparator policy BR003_P"):
        runner.build_extended_family(broken_span3, prox_recipes, design="proximal_relief")


def test_exact_360_parent_initializer_reuse_tamper_guards_and_full_proximal_pipeline(tmp_path, monkeypatch):
    cfg_br, proto_br, root = _build_synthetic_campaign_fixture(tmp_path, monkeypatch)
    parent_dir = Path(cfg_br["parent_results"])

    # Step 1: Populate 360 genuine synthetic parent initializers + FINAL_FREEZE.json in parent_dir
    monkeypatch.setattr(runner, "fit_signed", _fast_fit_signed)
    for shard in range(10):
        runner.run_history_shard(cfg_br, parent_dir, shard, protocol_path=proto_br, root=root)
    parent_freeze = runner.run_freeze_stage(cfg_br, parent_dir, protocol_path=proto_br, root=root)
    assert len(parent_freeze["all_initializers"]) == 360
    parent_freeze_sha = sha(parent_dir / "FINAL_FREEZE.json")

    # Extend parent_dir to 512 policies / 1311 comparisons
    ledger_sha, span3_sha = _extend_parent_to_512_policies_and_1311_comps(parent_dir, cfg_br["recipes"])

    # Step 2: Build proximal_relief protocol reusing exact 360 parent initializers
    prox_recipes = runner.build_proximal_recipes()
    cfg_pr = dict(
        cfg_br,
        study_id="proximal_relief_synthetic_test",
        design="proximal_relief",
        reuse_parent_initializers=True,
        parent_freeze_sha256=parent_freeze_sha,
        parent_ledger_sha256=ledger_sha,
        parent_span3_sha256=span3_sha,
        expected_parent_policies=512,
        expected_parent_comparisons=1311,
        recipes=prox_recipes,
    )
    proto_pr = tmp_path / "protocol_proximal.json"
    save(proto_pr, cfg_pr)

    # Monkeypatch fit_signed to unconditionally raise if called during proximal reuse
    def _forbidden_fit_signed(*args, **kwargs):
        raise AssertionError("fit_signed must NOT be called when reuse_parent_initializers=True")

    monkeypatch.setattr(runner, "fit_signed", _forbidden_fit_signed)

    # Verify tamper rejections on shard 0 before running the clean pipeline
    # (a) Tampered parent_freeze_sha256 rejected
    bad_freeze_cfg = dict(cfg_pr, parent_freeze_sha256="0" * 64)
    bad_freeze_proto = tmp_path / "proto_bad_freeze.json"
    save(bad_freeze_proto, bad_freeze_cfg)
    with pytest.raises(ValueError, match="Parent FINAL_FREEZE.json sha256 mismatch"):
        runner.run_history_shard(bad_freeze_cfg, tmp_path / "out_bad_freeze", 0, protocol_path=bad_freeze_proto, root=root)

    # (b) Tampered parent initializer file bytes rejected against parent FINAL_FREEZE.json
    target_parent_init = parent_dir / runner.initializer_relpath("inner", "P", 201, "COST", 0.0)
    orig_init_bytes = target_parent_init.read_bytes()
    try:
        tampered_rec = json.loads(orig_init_bytes.decode("utf-8"))
        tampered_rec["objective"] = 12345.678
        save(target_parent_init, tampered_rec)
        with pytest.raises(ValueError, match="sha256 mismatch against parent FINAL_FREEZE.json"):
            runner.run_history_shard(cfg_pr, tmp_path / "out_bad_init_sha", 0, protocol_path=proto_pr, root=root)
    finally:
        target_parent_init.write_bytes(orig_init_bytes)

    # (c) Tampered parent initializer metadata (e.g., valid_fit_cells mismatch) even when FINAL_FREEZE has matching hash
    orig_freeze_bytes = (parent_dir / "FINAL_FREEZE.json").read_bytes()
    try:
        tampered_rec = json.loads(orig_init_bytes.decode("utf-8"))
        tampered_rec["valid_fit_cells"] = 999999
        save(target_parent_init, tampered_rec)
        freeze_mod = json.loads(orig_freeze_bytes.decode("utf-8"))
        rel_k = str(runner.initializer_relpath("inner", "P", 201, "COST", 0.0)).replace("\\", "/")
        freeze_mod["all_initializers"][rel_k] = sha(target_parent_init)
        save(parent_dir / "FINAL_FREEZE.json", freeze_mod)
        cfg_meta_bad = dict(cfg_pr, parent_freeze_sha256=sha(parent_dir / "FINAL_FREEZE.json"))
        proto_meta_bad = tmp_path / "proto_meta_bad.json"
        save(proto_meta_bad, cfg_meta_bad)
        with pytest.raises(ValueError, match="Parent initializer metadata binding mismatch"):
            runner.run_history_shard(cfg_meta_bad, tmp_path / "out_bad_meta", 0, protocol_path=proto_meta_bad, root=root)
    finally:
        target_parent_init.write_bytes(orig_init_bytes)
        (parent_dir / "FINAL_FREEZE.json").write_bytes(orig_freeze_bytes)

    # Step 3: Run all 10 history shards with reuse_parent_initializers=True and fit_signed raising if called
    out_pr = tmp_path / "out_pr"
    for shard in range(10):
        rec = runner.run_history_shard(cfg_pr, out_pr, shard, protocol_path=proto_pr, root=root)
        assert rec["initializers_prepared"] == 36
        assert rec["initializers_fitted"] == 0
        assert rec["initializers_reused_from_parent"] is True
        assert rec["parent_freeze_sha256"] == parent_freeze_sha
        assert not rec["evaluation_cache_read"]
        assert all(item.get("reused_from_parent") is True for item in rec["initializers"])

    # Assert all 360 copied initializers are byte-for-byte identical to parent initializers
    copied_files = list((out_pr / "initializers").rglob("*.json"))
    assert len(copied_files) == 360
    for f in copied_files:
        rel = f.relative_to(out_pr)
        assert f.read_bytes() == (parent_dir / rel).read_bytes()

    # Step 4: Freeze stage verifies all 360 reused initializers and records design='proximal_relief'
    freeze_pr = runner.run_freeze_stage(cfg_pr, out_pr, protocol_path=proto_pr, root=root)
    assert freeze_pr["design"] == "proximal_relief"
    assert freeze_pr["initializers_reused_from_parent"] is True
    assert freeze_pr["parent_freeze_sha256"] == parent_freeze_sha
    assert freeze_pr["all_initializers"] == parent_freeze["all_initializers"]

    # Step 5: Verify first 8 actions identical between FIXED and proximal online updates on evaluation data
    eval_cache = Path(cfg_pr["evaluation_cache"])
    ea = np.load(eval_cache / "anchors.npy")
    ey = np.load(eval_cache / "shortfall.npy")
    em = np.load(eval_cache / "mask.npy")
    ex = np.load(eval_cache / "P_seed201.npy")
    eb, _, _ = runner.load_verified_parent_profile(cfg_pr, "evaluate", 201)
    init_0 = json.loads((out_pr / runner.initializer_relpath("evaluate", "P", 201, "COST", 0.1)).read_text(encoding="utf-8"))
    w0 = np.asarray(init_0["canonical_initial"], dtype=np.float64)
    delta_0 = signed_experts(ex, eb, relief=0.1)
    fixed_act = signed_action(eb, delta_0, w0, relief=0.1)
    online_cfgs = [MixtureConfig(**r["config"]) for r in prox_recipes if r["relief"] == 0.1 and r["goal"] == "COST" and r["mode"] != "FIXED"]
    online_res = run_signed(delta_0, eb, ey, em, ea, online_cfgs, w0, relief=0.1, score=True, return_actions=True)
    for idx in range(len(online_cfgs)):
        np.testing.assert_array_equal(online_res["actions"][idx, :8], fixed_act[:8])

    # Step 6: Run evaluate shards; on shard 0 inject failure for all 48 recipes to verify all 48 phase failures retained,
    # and on shard 1 inject a single online recipe failure (PROX_C at d=1.0, CAP -> recipe 47) to test batch fallback.
    real_run_signed = runner.run_signed
    real_signed_action = runner.signed_action

    def _fail_all_48_signed_action(*args, **kwargs):
        raise RuntimeError("synthetic all-48 fixed failure on shard 0")

    def _fail_all_48_run_signed(*args, **kwargs):
        raise RuntimeError("synthetic all-48 online failure on shard 0")

    monkeypatch.setattr(runner, "signed_action", _fail_all_48_signed_action)
    monkeypatch.setattr(runner, "run_signed", _fail_all_48_run_signed)
    runner.run_evaluate_shard(cfg_pr, out_pr, 0, protocol_path=proto_pr, root=root)

    r_shard0 = json.loads((out_pr / "instances/evaluate/P_seed201/receipt.json").read_text(encoding="utf-8"))
    d_shard0 = np.load(out_pr / "instances/evaluate/P_seed201/daily.npz")
    assert r_shard0["completed"] == 0 and r_shard0["complete_expected"] == 48
    assert all(r_shard0["status"][str(i)] == "FAILED_PRESERVED" for i in range(48))
    assert d_shard0["ledger"].shape == (48, 35, 4)
    assert np.isnan(d_shard0["ledger"]).all()

    # Restore signed_action and inject isolated recipe 47 failure on shard 1
    monkeypatch.setattr(runner, "signed_action", real_signed_action)

    def _fail_prox_c_d1_run_signed(delta, b, y, m, a, configs, w0, *, relief=0.0, **kwargs):
        if float(relief) == 1.0 and any(getattr(c, "proximity_strength", 0.0) == 0.1 for c in configs):
            raise FloatingPointError("synthetic PROX_C failure at d=1.0")
        return real_run_signed(delta, b, y, m, a, configs, w0, relief=relief, **kwargs)

    monkeypatch.setattr(runner, "run_signed", _fail_prox_c_d1_run_signed)
    runner.run_evaluate_shard(cfg_pr, out_pr, 1, protocol_path=proto_pr, root=root)

    r_shard1 = json.loads((out_pr / "instances/evaluate/Z_seed201/receipt.json").read_text(encoding="utf-8"))
    assert r_shard1["completed"] == 46
    assert r_shard1["status"]["43"] == "FAILED_PRESERVED"
    assert r_shard1["status"]["47"] == "FAILED_PRESERVED"
    assert r_shard1["status"]["46"] == "COMPLETED"
    assert r_shard1["metadata"]["46"]["proximity_strength"] == 0.01

    monkeypatch.setattr(runner, "run_signed", real_run_signed)
    for shard in range(2, 10):
        runner.run_evaluate_shard(cfg_pr, out_pr, shard, protocol_path=proto_pr, root=root)

    # Step 7: Aggregate stage produces 608 policies, 1911 comparisons, 25798 nominal coordinates
    completion = runner.run_aggregate_stage(cfg_pr, out_pr, protocol_path=proto_pr, root=root, n_boot_override=4)
    assert completion["status"] == "COMPLETED_WITH_PRESERVED_FAILURES"
    assert completion["all_planned_instances_retained"] is True
    assert not completion["scientific_qualification_used_to_filter"]
    assert completion["complete_per_phase"] == {"inner": 480, "outer": 480, "evaluate": 480 - 48 - 2}
    assert completion["failed_per_phase"] == {"inner": 0, "outer": 0, "evaluate": 50}
    assert sum(completion["complete_per_phase"].values()) + sum(completion["failed_per_phase"].values()) == 1440

    all_names = json.loads((out_pr / "all_policy_names.json").read_text(encoding="utf-8"))
    assert len(all_names["names"]) == 608
    assert all_names["parent_policy_count"] == 512
    assert all_names["new_policy_count"] == 96
    assert all_names["parent_comparison_count"] == 1311
    assert all_names["total_comparison_count"] == 1911
    assert all_names["nominal_family_size"] == 25798

    # All P_seed201 recipes failed on shard 0 -> all PR*_P unavailable; PR046_Z succeeded on all Z shards -> available
    pr000_p_idx = all_names["names"].index("PR000_P")
    pr046_z_idx = all_names["names"].index("PR046_Z")
    pr047_z_idx = all_names["names"].index("PR047_Z")
    assert not all_names["available"][pr000_p_idx]
    assert all_names["available"][pr046_z_idx]
    assert not all_names["available"][pr047_z_idx]

    span3_out = json.loads((out_pr / "inference_span3.json").read_text(encoding="utf-8"))
    assert span3_out["family_size"] == 25798
    assert len(span3_out["coordinates"]) == 25798
    assert len(span3_out["policy_names"]) == 608
    assert len(span3_out["comparisons"]) == 1911

    # Step 8: Freeze stage tamper guards when reuse_parent_initializers=True
    def _fresh_pr_history_out(name: str) -> Path:
        dest = tmp_path / name
        shutil.copytree(out_pr / "shards" / "history", dest / "shards" / "history")
        shutil.copytree(out_pr / "initializers", dest / "initializers")
        shutil.copytree(out_pr / "instances" / "inner", dest / "instances" / "inner")
        shutil.copytree(out_pr / "instances" / "outer", dest / "instances" / "outer")
        return dest

    # (a) Tampered history shard receipt initializers_fitted != 0 rejected by freeze
    out_freeze_bad_fit = _fresh_pr_history_out("out_freeze_bad_fit")
    r0_hist_path = out_freeze_bad_fit / "shards" / "history" / "shard_00_P_seed201" / "receipt.json"
    bad_r0_hist = json.loads(r0_hist_path.read_text(encoding="utf-8"))
    bad_r0_hist["initializers_fitted"] = 36
    save(r0_hist_path, bad_r0_hist)
    with pytest.raises(ValueError, match="History shard 0 parent initializer reuse binding mismatch"):
        runner.run_freeze_stage(cfg_pr, out_freeze_bad_fit, protocol_path=proto_pr, root=root)

    # (b) Tampered source file rejected by verify_source_hashes at freeze
    out_freeze_bad_src = _fresh_pr_history_out("out_freeze_bad_src")
    src_file = root / "dummy_source.py"
    orig_src = src_file.read_bytes()
    try:
        src_file.write_text("# tampered source\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Source hash mismatch for dummy_source.py"):
            runner.run_freeze_stage(cfg_pr, out_freeze_bad_src, protocol_path=proto_pr, root=root)
    finally:
        src_file.write_bytes(orig_src)

