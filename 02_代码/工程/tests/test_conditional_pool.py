import json
import os
from repo_paths import Path, repository_root
import shutil

import numpy as np
import pytest

import scripts.run_conditional_pool as runner
import scripts.run_meta_pool as mp_runner
from scripts.run_mixture_closed_loop import save, sha
from tests.test_meta_pool import _make_synthetic_mc_parent_campaign
from windfarm_moe.conditional_convex_pool import (
    fit_conditional_pool,
    fit_context_cuts,
    initialize_anchor_record,
    predict_conditional_pool,
)


def _make_synthetic_mp_parent_campaign(tmp_path: Path):
    """Build synthetic parent MP campaign (1040 policies, 4107 comparisons) + grandparent MCV2 streams."""
    mp_cfg, _, _, hist_cache, eval_cache = _make_synthetic_mc_parent_campaign(
        tmp_path / "base_mc", coincide_roles=False
    )
    mc_dir = Path(mp_cfg["parent_results"])
    mp_dir = tmp_path / "parent_mp_campaign"
    mp_dir.mkdir(parents=True, exist_ok=True)

    mc_span3 = json.loads((mc_dir / "inference_span3.json").read_text(encoding="utf-8"))
    mc_freeze = json.loads((mc_dir / "FINAL_FREEZE.json").read_text(encoding="utf-8"))
    # Rewrite one synthetic parent slot (index 435 -> PARENT_0435, matching real BR009_Z slot)
    # consistently across top-level/family_definition names, comparisons, and frozen_aliases.
    if "BR009_Z" not in mc_span3["policy_names"]:
        old_synth_name = mc_span3["policy_names"][435]
        rename_map = {old_synth_name: "BR009_Z"}
        mc_span3["policy_names"] = [rename_map.get(n, n) for n in mc_span3["policy_names"]]
        fd = mc_span3["family_definition"]
        fd["policy_names"] = [rename_map.get(n, n) for n in fd["policy_names"]]
        fd["comparisons"] = [[rename_map.get(p, p) for p in pair] for pair in fd["comparisons"]]
        fd["frozen_aliases"] = [[rename_map.get(p, p) for p in pair] for pair in fd.get("frozen_aliases", [])]
    mp_recipes = mp_runner.build_pool_recipes()
    mp_names, mc_avail, mp_aliases, mp_comps, _ = mp_runner.build_extended_family(
        mc_span3, mp_recipes, mc_freeze, expected_parent_policies=968, expected_parent_comparisons=3639
    )
    mp_avail = mc_avail + [True] * 72
    assert len(mp_names) == 1040 and len(mp_comps) == 4107

    mc_npz = np.load(mc_dir / "all_daily_ledger.npz")
    mp_ledger = np.ones((5, 1040, 35, 4), dtype=np.float64)
    mp_ledger[:, :968] = mc_npz["ledger"]
    for rid in range(24):
        for ai in range(3):
            mp_idx = 968 + 3 * rid + ai
            mp_ledger[:, mp_idx] = mc_npz["ledger"][:, 0] + 0.005 * (rid + 1)
    np.savez_compressed(
        mp_dir / "all_daily_ledger.npz",
        ledger=mp_ledger,
        counts=mc_npz["counts"],
        day_ids=mc_npz["day_ids"],
    )
    save(
        mp_dir / "inference_span3.json",
        dict(
            schema="autonomous-campaign-inference-v1",
            policy_names=mp_names,
            available=mp_avail,
            family_definition=dict(
                policy_names=mp_names,
                comparisons=[list(p) for p in mp_comps],
                frozen_aliases=[list(p) for p in mp_aliases],
            ),
        ),
    )

    mp_proto = dict(
        study_id="meta_pool_20261025_v1",
        parent_results=str(mc_dir),
        parent_freeze_sha256=sha(mc_dir / "FINAL_FREEZE.json"),
    )
    save(mp_dir / "protocol_original.json", mp_proto)
    save(mp_dir / "protocol.json", mp_proto)
    mp_roles = {
        "C": dict(minimum_C_id=20, minimum_maxV_id=1),
        "P": dict(minimum_C_id=23, minimum_maxV_id=1),
        "Z": dict(minimum_C_id=23, minimum_maxV_id=1),
    }
    mp_freeze = dict(
        study_id="meta_pool_20261025_v1",
        protocol_sha256=sha(mp_dir / "protocol_original.json"),
        parent_freeze_sha256=mp_proto["parent_freeze_sha256"],
        historical_roles=dict(roles=mp_roles, qualification_did_not_filter_instances=True),
        all_streams=mc_freeze["all_streams"],
    )
    save(mp_dir / "FINAL_FREEZE.json", mp_freeze)
    save(
        mp_dir / "EVALUATION_OPEN.json",
        dict(freeze_sha256=sha(mp_dir / "FINAL_FREEZE.json"), protocol_sha256=mp_freeze["protocol_sha256"]),
    )

    src_file = tmp_path / "dummy_conditional_pool_source.py"
    src_file.write_text("# synthetic conditional pool source\n", encoding="utf-8")

    cfg = dict(
        study_id="conditional_pool_20261025_synthetic",
        max_candidates=24,
        max_cpu_seconds=14400,
        history_wall_seconds=600,
        evaluation_wall_seconds=120,
        freeze_wall_seconds=60,
        aggregate_wall_seconds=1200,
        independent_audit_wall_seconds=300,
        local_retry_reserve_seconds=2040,
        maximum_science_parallel_jobs=15,
        per_job_ncpus=1,
        aggregate_mem_gb=96,
        budget_reservation=dict(
            new_candidates=24,
            cpu_seconds=14400,
            total_reserved_candidates=1526,
            total_accounted_plus_open_reservations_cpu=60997,
            global_cpu_limit_unchanged=86400,
        ),
        expected_historical_grid=False,
        expected_evaluation_anchors=mp_cfg["expected_evaluation_anchors"],
        expected_evaluation_valid_cells=mp_cfg["expected_evaluation_valid_cells"],
        expected_parent_policies=1040,
        expected_parent_comparisons=4107,
        parent_results=str(mp_dir),
        parent_freeze_sha256=sha(mp_dir / "FINAL_FREEZE.json"),
        parent_ledger_sha256=sha(mp_dir / "all_daily_ledger.npz"),
        parent_span3_sha256=sha(mp_dir / "inference_span3.json"),
        stream_parent_results=str(mc_dir),
        stream_parent_freeze_sha256=sha(mc_dir / "FINAL_FREEZE.json"),
        recipes=runner.build_conditional_pool_recipes(),
        source_hashes={"dummy_conditional_pool_source.py": sha(src_file)},
        inference=dict(spans=[3, 1, 7], n_boot=4, seed=20261022),
    )
    protocol_path = tmp_path / "protocol.json"
    save(protocol_path, cfg)
    return cfg, protocol_path, tmp_path, hist_cache, eval_cache


def test_24_recipe_grid_budget_and_492_family_comparisons(tmp_path):
    recipes = runner.build_conditional_pool_recipes()
    assert len(recipes) == 24
    assert [r["id"] for r in recipes] == list(range(24))
    assert 15 * 600 + 15 * 120 + 60 + 1200 + 300 + 2040 == 14400

    for gi, grp in enumerate(runner.GROUPS_GRID):
        for ri, d in enumerate(runner.RELIEF_GRID):
            for ci, mode in enumerate(runner.CAP_MODES):
                rid = gi * 12 + ri * 3 + ci
                assert recipes[rid] == dict(
                    id=rid,
                    groups=int(grp),
                    relief=float(d),
                    cap_mode=str(mode),
                )

    cfg, _, _, _, _ = _make_synthetic_mp_parent_campaign(tmp_path / "fam")
    mp_dir = Path(cfg["parent_results"])
    span3 = json.loads((mp_dir / "inference_span3.json").read_text(encoding="utf-8"))
    mp_freeze = json.loads((mp_dir / "FINAL_FREEZE.json").read_text(encoding="utf-8"))
    names, avail, aliases, comps, summary = runner.build_extended_family(span3, recipes, mp_freeze)

    assert len(names) == 1112
    assert len(avail) == 1040
    assert names[1040:1043] == ["CP000_C", "CP000_P", "CP000_Z"]
    assert names[-3:] == ["CP023_C", "CP023_P", "CP023_Z"]
    assert len(comps) == 4107 + 492 == 4599
    assert 11 * len(names) + 10 * len(comps) == 58222
    assert len(aliases) == len(span3["family_definition"]["frozen_aliases"])
    assert summary["new_comparison_breakdown"] == dict(
        common_comparator_pairs=360,
        within_recipe_representation_pairs=72,
        g3_vs_g1_context_pairs=36,
        day_vs_pooled_cap_pairs=24,
        total_new_comparisons=492,
    )

    new_comps = comps[4107:]
    # Check specific g3 vs g1 and DAY vs POOLED pairs
    # CP012 (groups=3, relief=0.01, COST) vs CP000 (groups=1, relief=0.01, COST)
    assert ("CP012_Z", "CP000_Z") in new_comps
    # CP002 (groups=1, relief=0.01, DAY) vs CP001 (groups=1, relief=0.01, POOLED)
    assert ("CP002_P", "CP001_P") in new_comps
    # CP023 (groups=3, relief=1.0, DAY) vs CP011 (groups=1, relief=1.0, DAY) and vs CP022 (groups=3, relief=1.0, POOLED)
    assert ("CP023_C", "CP011_C") in new_comps
    assert ("CP023_C", "CP022_C") in new_comps


def test_oof_maturity_masked_nan_cuts_consistency_and_no_mask_gating():
    anchors = np.arange(28087, 28095, dtype=np.int64)  # last=28094, release=28101 < outer start 28944
    raw_c = np.full((24, len(anchors), 3), 6.0, dtype=np.float64)
    raw_c[0] = 3.5
    raw_c[1] = 8.5
    raw_p = raw_c + 0.25
    raw_z = raw_c + 0.50

    ref = np.linspace(2.0, 14.0, len(anchors) * 3, dtype=np.float64).reshape(len(anchors), 3)
    y = np.full((len(anchors), 3), 7.0, dtype=np.float64)
    m = np.ones_like(y, dtype=bool)
    m[1, 2] = False
    m[4, 0] = False
    y[1, 2] = np.nan
    y[4, 0] = np.nan
    b = np.full_like(y, 5.0)

    recipe_g3_day = dict(id=14, groups=3, relief=0.1, cap_mode="DAY")
    cuts_expected = fit_context_cuts(ref, 3)

    recs = {}
    for arm, raw in (("C", raw_c), ("P", raw_p), ("Z", raw_z)):
        bank = dict(
            anchors=anchors,
            shortfall=y,
            mask=m,
            reference=ref,
            raw_actions=raw,
            metadata=dict(phase="inner", phases=["inner"], raw_actions_sha256="a" * 64),
        )
        recs[arm] = runner.fit_oof_conditional_pool_initializer(
            phase="outer",
            seed=201,
            arm=arm,
            recipe=recipe_g3_day,
            oof_bank=bank,
            b_oof=b,
            episode_start=28944,
            source_manifest_sha256="1" * 64,
            parent_profile_sha256="2" * 64,
            time_limit=2.0,
        )

    assert recs["C"]["cuts"] == cuts_expected
    assert recs["P"]["cuts"] == cuts_expected
    assert recs["Z"]["cuts"] == cuts_expected
    assert np.asarray(recs["C"]["weights"]).shape == (3, 25)
    assert recs["C"]["actual_feasible"] is True

    # Mutating unmasked (~m) target values to -999 or +inf must leave cuts, weights, and objective identical
    for sentinel in (-999.0, np.inf, np.nan):
        y_alt = y.copy()
        y_alt[~m] = sentinel
        bank_alt = dict(
            anchors=anchors,
            shortfall=y_alt,
            mask=m,
            reference=ref,
            raw_actions=raw_c,
            metadata=dict(phase="inner", phases=["inner"], raw_actions_sha256="a" * 64),
        )
        rec_alt = runner.fit_oof_conditional_pool_initializer(
            phase="outer",
            seed=201,
            arm="C",
            recipe=recipe_g3_day,
            oof_bank=bank_alt,
            b_oof=b,
            episode_start=28944,
            source_manifest_sha256="1" * 64,
            parent_profile_sha256="2" * 64,
            time_limit=2.0,
        )
        assert rec_alt["cuts"] == recs["C"]["cuts"]
        assert rec_alt["weights"] == recs["C"]["weights"]
        assert rec_alt["objective"] == recs["C"]["objective"]

    # Prediction does not take mask or target, and does not recompute cuts on prediction reference
    x_pred = np.moveaxis(raw_c, 0, -1)
    act1, meta1 = predict_conditional_pool(x_pred, b, ref, recs["C"])
    assert meta1["recomputed_cuts_on_prediction"] is False
    assert meta1["mask_gated_prediction"] is False
    assert act1.shape == b.shape

    # Immature OOF window rejected
    with pytest.raises(ValueError, match="not strictly mature"):
        runner.fit_oof_conditional_pool_initializer(
            phase="outer",
            seed=201,
            arm="C",
            recipe=recipe_g3_day,
            oof_bank=bank_alt,
            b_oof=b,
            episode_start=28101,
            source_manifest_sha256="1" * 64,
            parent_profile_sha256="2" * 64,
        )


def test_full_pipeline_15_shards_1080_initializers_and_tamper_barriers(tmp_path, monkeypatch):
    cfg, protocol_path, root, hist_cache, eval_cache = _make_synthetic_mp_parent_campaign(tmp_path)
    out = tmp_path / "out"

    call_counter = {"n": 0}

    def fast_fit_conditional_pool(
        x,
        b,
        y,
        mask,
        anchors,
        reference,
        *,
        groups=3,
        relief=0.01,
        cap_mode="COST",
        time_limit=8.0,
        max_iter=1200,
        tol=1e-7,
        **kwargs,
    ):
        call_counter["n"] += 1
        assert x.shape == (*b.shape, 24)
        if call_counter["n"] == 1:
            raise RuntimeError("synthetic solver failure on first outer conditional pool fit")
        rec = initialize_anchor_record(groups=groups, relief=relief, cap_mode=cap_mode)
        cuts = fit_context_cuts(reference, groups)
        w = np.zeros((groups, 25), dtype=np.float64)
        w[:, 0] = 0.7
        w[:, 1] = 0.2
        w[:, 2] = 0.1
        y_v = y[mask]
        b_v = b[mask]
        u = float(np.maximum(y_v - b_v, 0.0).mean())
        c = float((b_v + 10.0 * np.maximum(y_v - b_v, 0.0)).mean() / 6.0)
        rec.update(
            status="OPTIMAL_NUMERICAL_BOUNDS",
            optimal=True,
            numerical_fitted=True,
            cuts=cuts,
            cuts_source=("HISTORICAL_REFERENCE_GRID_QUANTILES" if groups == 3 else "SINGLE_POOL_NO_CUTS"),
            weights=w.tolist(),
            raw_weights=w.tolist(),
            canonical_initial=w.tolist(),
            objective=c,
            lower_bound=c,
            gap=0.0,
            mean_uncovered_power=u,
            uncovered_cap=(u if cap_mode == "POOLED" else None),
            day_caps=([u] if cap_mode == "DAY" else None),
            day_uncovered_power=([u] if cap_mode == "DAY" else None),
            anchor_objective=c,
            anchor_mean_uncovered_power=u,
            valid_fit_cells=int(mask.sum()),
            total_cells=int(b.size),
            fit_issue_count=int(anchors.size),
            actual_feasible=True,
            raw_actual_feasible=True,
            time_limit=float(time_limit),
            max_iter=int(max_iter),
            relative_tolerance=float(tol),
        )
        return rec

    monkeypatch.setattr(runner, "fit_conditional_pool", fast_fit_conditional_pool)

    # Guard evaluation cache and grandparent evaluate streams during history stage
    eval_cache_resolved = eval_cache.resolve()
    eval_streams_resolved = (Path(cfg["stream_parent_results"]) / "streams" / "evaluate").resolve()
    real_np_load = np.load

    def guarded_load(file, *args, **kwargs):
        if isinstance(file, (str, os.PathLike)):
            p = Path(file).resolve()
            if (
                p == eval_cache_resolved
                or eval_cache_resolved in p.parents
                or p == eval_streams_resolved
                or eval_streams_resolved in p.parents
            ):
                raise AssertionError(f"Evaluation artifact read during history stage: {p}")
        return real_np_load(file, *args, **kwargs)

    # 1. Run all 15 history shards with evaluation guard active
    monkeypatch.setattr(np, "load", guarded_load)
    for shard in range(15):
        rec = runner.run_history_shard(cfg, out, shard, protocol_path=protocol_path, root=root)
        assert rec["initializers_prepared"] == 72
        assert rec["initializers_numerical_fitted"] == 48
        assert rec["initializers_anchor_declared"] == 24
        assert rec["new_models_fitted"] == 0
        assert rec["evaluation_cache_read"] is False
    monkeypatch.setattr(np, "load", real_np_load)
    assert call_counter["n"] == 720

    # Verify inner initializers have [] (G=1) and [0.0, 0.0] (G=3), and fallback outer CP000 is e0
    inner_g1 = json.loads((out / runner.initializer_relpath("inner", "C", 201, 0)).read_text(encoding="utf-8"))
    inner_g3 = json.loads((out / runner.initializer_relpath("inner", "C", 201, 12)).read_text(encoding="utf-8"))
    assert inner_g1["status"] == "NO_PRIOR_OOF_ANCHOR"
    assert inner_g1["cuts"] == []
    assert inner_g1["weights"] == [[1.0] + [0.0] * 24]
    assert inner_g3["status"] == "NO_PRIOR_OOF_ANCHOR"
    assert inner_g3["cuts"] == [0.0, 0.0]
    assert inner_g3["weights"] == [[1.0] + [0.0] * 24] * 3

    outer_fb = json.loads((out / runner.initializer_relpath("outer", "C", 201, 0)).read_text(encoding="utf-8"))
    assert outer_fb["status"] == "INITIALIZER_ERROR_DECLARED_ANCHOR_FALLBACK"
    assert outer_fb["numerical_fitted"] is True
    assert outer_fb["weights"] == [[1.0] + [0.0] * 24]

    # 2. Tamper one arm's cuts before freeze -> freeze must reject cuts mismatch across C/P/Z
    init_p_g3 = out / runner.initializer_relpath("outer", "P", 201, 12)
    r_p_path = out / "shards/history/shard_01_P_seed201/receipt.json"
    orig_init_p = init_p_g3.read_bytes()
    orig_r_p = r_p_path.read_bytes()
    try:
        bad_init = json.loads(orig_init_p.decode("utf-8"))
        bad_init["cuts"] = [bad_init["cuts"][0] + 0.5, bad_init["cuts"][1] + 0.5]
        save(init_p_g3, bad_init)
        bad_sha = sha(init_p_g3)
        r_p_data = json.loads(orig_r_p.decode("utf-8"))
        for item in r_p_data["initializers"]:
            if item["path"] == "initializers/outer/P_seed201/CP012.json":
                item["sha256"] = bad_sha
        save(r_p_path, r_p_data)
        with pytest.raises(ValueError, match="Context cuts mismatch across arms"):
            runner.run_freeze_stage(cfg, out, protocol_path=protocol_path, root=root)
    finally:
        init_p_g3.write_bytes(orig_init_p)
        r_p_path.write_bytes(orig_r_p)
        shutil.rmtree(out / "shards" / "freeze")

    # 3. Freeze stage succeeds: 1080 initializers (720 numerical + 360 anchor), cuts consistent
    freeze = runner.run_freeze_stage(cfg, out, protocol_path=protocol_path, root=root)
    assert len(freeze["all_initializers"]) == 1080
    assert freeze["numerical_fits"] == 720
    assert freeze["anchor_declarations"] == 360
    assert freeze["cuts_consistent_across_arms"] is True
    assert len(freeze["all_streams"]) == 30

    with pytest.raises(FileExistsError):
        runner.run_freeze_stage(cfg, out, protocol_path=protocol_path, root=root)

    # 4. Tamper evaluate initializer after freeze -> rejected by evaluate shard
    init_e_path = out / runner.initializer_relpath("evaluate", "C", 201, 0)
    orig_e_bytes = init_e_path.read_bytes()
    try:
        init_e_path.write_bytes(orig_e_bytes + b" ")
        with pytest.raises(ValueError, match="Initializer missing or modified since freeze"):
            runner.run_evaluate_shard(cfg, out, 0, protocol_path=protocol_path, root=root)
    finally:
        init_e_path.write_bytes(orig_e_bytes)
        shutil.rmtree(out / "shards" / "evaluate" / "shard_00_C_seed201")

    # 5. Inject single recipe prediction failure on shard 0 evaluate (CP023)
    real_predict = runner.predict_conditional_pool

    def faulty_predict(x, b, ref, record):
        if int(record.get("id", -1)) == 23 and record.get("phase") == "evaluate" and record.get("arm") == "C" and int(record.get("seed", 0)) == 201:
            raise FloatingPointError("synthetic prediction failure on CP023_C seed 201")
        return real_predict(x, b, ref, record)

    monkeypatch.setattr(runner, "predict_conditional_pool", faulty_predict)
    runner.run_evaluate_shard(cfg, out, 0, protocol_path=protocol_path, root=root)
    monkeypatch.setattr(runner, "predict_conditional_pool", real_predict)
    for shard in range(1, 15):
        runner.run_evaluate_shard(cfg, out, shard, protocol_path=protocol_path, root=root)

    r0_eval = json.loads((out / "instances/evaluate/C_seed201/receipt.json").read_text(encoding="utf-8"))
    d0_eval = np.load(out / "instances/evaluate/C_seed201/daily.npz")
    assert d0_eval["ledger"].shape == (24, 35, 4)
    assert r0_eval["status"]["23"] == "FAILED_PRESERVED"
    assert np.isnan(d0_eval["ledger"][23]).all()
    assert r0_eval["status"]["22"] == "COMPLETED"
    assert np.isfinite(d0_eval["ledger"][22]).all()

    # 6. Aggregate stage: 1080 slots, 1080 weights JSON, 1040+72=1112 policies, 4107+492=4599 comparisons
    completion = runner.run_aggregate_stage(cfg, out, protocol_path=protocol_path, root=root, n_boot_override=4)
    assert completion["status"] == "COMPLETED_WITH_PRESERVED_FAILURES"
    assert completion["planned_recipes"] == 24
    assert completion["planned_instances_per_phase"] == 360
    assert completion["total_planned_instances"] == 1080
    assert completion["complete_per_phase"]["inner"] == 360
    assert completion["complete_per_phase"]["outer"] == 360
    assert completion["complete_per_phase"]["evaluate"] == 359
    assert completion["failed_per_phase"]["evaluate"] == 1
    assert completion["total_initializers"] == 1080
    assert completion["numerical_fits"] == 720
    assert completion["anchor_declarations"] == 360
    assert completion["new_models_fitted"] == 0

    weights_json = json.loads((out / "all_initializer_weights.json").read_text(encoding="utf-8"))
    assert len(weights_json) == 1080

    all_names = json.loads((out / "all_policy_names.json").read_text(encoding="utf-8"))
    assert all_names["parent_policy_count"] == 1040
    assert all_names["new_policy_count"] == 72
    assert len(all_names["names"]) == 1112
    assert all_names["parent_comparison_count"] == 4107
    assert all_names["new_comparison_count"] == 492
    assert all_names["total_comparison_count"] == 4599
    assert all_names["nominal_family_size"] == 58222
    assert all_names["available"][-3:] == [False, True, True]

    for span in (3, 1, 7):
        assert (out / f"inference_span{span}.json").exists()
