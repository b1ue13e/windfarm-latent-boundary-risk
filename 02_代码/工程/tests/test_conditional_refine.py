import copy
import json
import os
from repo_paths import Path, repository_root
import shutil

import numpy as np
import pytest

import scripts.run_conditional_pool as cp_runner
import scripts.run_conditional_refine as nr_runner
from scripts.run_meta_pool import (
    load_verified_causal_profile_and_anchors,
    load_verified_parent_stream_bank,
    resolve_meta_source_protocol,
    select_exact_anchor_slice,
)
from scripts.run_mixture_closed_loop import PHASES, SEEDS, save, score_actions, sha
from scripts.run_residual_meta import shard_assignment
from tests.test_conditional_pool import _make_synthetic_mp_parent_campaign
from windfarm_moe.conditional_convex_pool import (
    fit_context_cuts,
    initialize_anchor_record,
    predict_conditional_pool,
)
from windfarm_moe.meta_action_stream import join_banks
from windfarm_moe.residual_meta import META_ARMS


def _make_synthetic_cp_parent_campaign(tmp_path: Path):
    """Build synthetic parent CP campaign (1112 policies, 4599 comparisons, 1080 real-schema initializers)."""
    mp_cfg, _, root, hist_cache, eval_cache = _make_synthetic_mp_parent_campaign(tmp_path / "base_mp")
    mp_dir = Path(mp_cfg["parent_results"])
    mc_dir = Path(mp_cfg["stream_parent_results"])
    cp_dir = tmp_path / "parent_cp_campaign"
    cp_dir.mkdir(parents=True, exist_ok=True)

    mp_span3 = json.loads((mp_dir / "inference_span3.json").read_text(encoding="utf-8"))
    mp_freeze = json.loads((mp_dir / "FINAL_FREEZE.json").read_text(encoding="utf-8"))
    mc_freeze = json.loads((mc_dir / "FINAL_FREEZE.json").read_text(encoding="utf-8"))
    recipes = cp_runner.build_conditional_pool_recipes()

    # Ensure required common comparator MP010_Z exists in synthetic parent MP policy names
    if "MP010_Z" not in mp_span3["policy_names"]:
        old_name = mp_span3["policy_names"][-1]
        rmap = {old_name: "MP010_Z"}
        mp_span3["policy_names"] = [rmap.get(n, n) for n in mp_span3["policy_names"]]
        fd = mp_span3["family_definition"]
        fd["policy_names"] = [rmap.get(n, n) for n in fd["policy_names"]]
        fd["comparisons"] = [[rmap.get(p, p) for p in pair] for pair in fd["comparisons"]]
        fd["frozen_aliases"] = [[rmap.get(p, p) for p in pair] for pair in fd.get("frozen_aliases", [])]

    cp_names, mp_avail, cp_aliases, cp_comps, _ = cp_runner.build_extended_family(
        mp_span3, recipes, mp_freeze, expected_parent_policies=1040, expected_parent_comparisons=4107
    )
    cp_avail = mp_avail + [True] * 72
    assert len(cp_names) == 1112 and len(cp_comps) == 4599

    source_cfg, meta_dir = resolve_meta_source_protocol(mp_cfg, mc_dir, mc_freeze)
    mp_npz = np.load(mp_dir / "all_daily_ledger.npz")
    cp_ledger = np.ones((5, 1112, 35, 4), dtype=np.float64)
    cp_ledger[:, :1040] = mp_npz["ledger"]

    all_initializers: dict[str, str] = {}
    for si, seed in enumerate(SEEDS):
        hist_anchors, b_hist_full, hist_profile_sha, hist_manifest_sha = (
            load_verified_causal_profile_and_anchors(
                source_cfg, "historical", seed, meta_dir=meta_dir, parent_mc_dir=mc_dir
            )
        )
        eval_anchors, b_eval_full, eval_profile_sha, _ = load_verified_causal_profile_and_anchors(
            source_cfg, "evaluate", seed, meta_dir=meta_dir, parent_mc_dir=mc_dir
        )
        for ai, arm in enumerate(META_ARMS):
            inner_bank, _ = load_verified_parent_stream_bank(mc_dir, mc_freeze, "inner", seed, arm)
            outer_bank, _ = load_verified_parent_stream_bank(mc_dir, mc_freeze, "outer", seed, arm)
            eval_bank, _ = load_verified_parent_stream_bank(mc_dir, mc_freeze, "evaluate", seed, arm)
            joined_bank = join_banks([inner_bank, outer_bank])
            b_inner = select_exact_anchor_slice(hist_anchors, b_hist_full, inner_bank["anchors"])
            b_joined = select_exact_anchor_slice(hist_anchors, b_hist_full, joined_bank["anchors"])
            b_eval = select_exact_anchor_slice(eval_anchors, b_eval_full, eval_bank["anchors"])

            for phase in ("inner", "outer", "evaluate"):
                begin, _, _ = PHASES[phase]
                actual_begin = (
                    int(inner_bank["anchors"][0])
                    if phase == "inner"
                    else int(outer_bank["anchors"][0])
                    if phase == "outer"
                    else int(begin)
                )
                for recipe in recipes:
                    rid = int(recipe["id"])
                    g = int(recipe["groups"])
                    d = float(recipe["relief"])
                    mode = str(recipe["cap_mode"])
                    if phase == "inner":
                        rec = cp_runner._build_inner_no_prior_oof_record(
                            recipe=recipe,
                            seed=seed,
                            arm=arm,
                            episode_start=actual_begin,
                            source_manifest_sha256=hist_manifest_sha,
                            parent_profile_sha256=hist_profile_sha,
                        )
                    else:
                        oof_bank = inner_bank if phase == "outer" else joined_bank
                        b_oof = b_inner if phase == "outer" else b_joined
                        a_oof = np.asarray(oof_bank["anchors"], dtype=np.int64)
                        y_oof = np.asarray(oof_bank["shortfall"], dtype=np.float64)
                        m_oof = np.asarray(oof_bank["mask"], dtype=bool)
                        ref_oof = np.asarray(oof_bank["reference"], dtype=np.float64)
                        cuts = fit_context_cuts(ref_oof, g)
                        w = np.zeros((g, 25), dtype=np.float64)
                        if rid in nr_runner.DEFAULT_REFINED_RECIPE_IDS:
                            w[:, 0] = 1.0
                        else:
                            w[:, 0] = 0.75
                            w[:, 1] = 0.15
                            w[:, 2] = 0.10
                        y_v = y_oof[m_oof]
                        b_v = b_oof[m_oof]
                        u_a = float(np.maximum(y_v - b_v, 0.0).mean())
                        c_a = float((b_v + 10.0 * np.maximum(y_v - b_v, 0.0)).mean() / 6.0)
                        rec = initialize_anchor_record(groups=g, relief=d, cap_mode=mode)
                        oof_phases = list(
                            oof_bank["metadata"].get("phases") or [oof_bank["metadata"].get("phase")]
                        )
                        rec.update(
                            id=rid,
                            phase=phase,
                            seed=int(seed),
                            arm=str(arm),
                            status=("TIME_LIMIT" if rid in nr_runner.DEFAULT_REFINED_RECIPE_IDS else "OPTIMAL_NUMERICAL_BOUNDS"),
                            optimal=(rid not in nr_runner.DEFAULT_REFINED_RECIPE_IDS),
                            numerical_fitted=True,
                            cuts=cuts,
                            cuts_source=("HISTORICAL_REFERENCE_GRID_QUANTILES" if g == 3 else "SINGLE_POOL_NO_CUTS"),
                            weights=w.tolist(),
                            raw_weights=w.tolist(),
                            canonical_initial=w.tolist(),
                            objective=c_a,
                            lower_bound=(c_a - 0.25 if rid in nr_runner.DEFAULT_REFINED_RECIPE_IDS else c_a),
                            gap=(0.25 if rid in nr_runner.DEFAULT_REFINED_RECIPE_IDS else 0.0),
                            mean_uncovered_power=u_a,
                            uncovered_cap=(u_a if mode == "POOLED" else None),
                            day_caps=([u_a] if mode == "DAY" else None),
                            day_uncovered_power=([u_a] if mode == "DAY" else None),
                            anchor_objective=c_a,
                            anchor_mean_uncovered_power=u_a,
                            fit_window=[int(a_oof[0]), int(a_oof[-1]) + 1],
                            fit_anchor_start=int(a_oof[0]),
                            fit_anchor_end=int(a_oof[-1]),
                            fit_issue_count=int(a_oof.size),
                            valid_fit_cells=int(m_oof.sum()),
                            total_cells=int(b_oof.size),
                            episode_start=actual_begin,
                            last_label_release=int(a_oof[-1]) + 7,
                            source_manifest_sha256=str(hist_manifest_sha),
                            parent_profile_sha256=str(hist_profile_sha),
                            oof_source_phases=oof_phases,
                            oof_raw_actions_sha256=oof_bank["metadata"].get("raw_actions_sha256"),
                            actual_feasible=True,
                            raw_actual_feasible=True,
                            time_limit=8.0,
                            max_iter=1200,
                            relative_tolerance=1e-7,
                        )
                    rel = cp_runner.initializer_relpath(phase, arm, seed, rid)
                    rel_key = str(rel).replace("\\", "/")
                    full_init = cp_dir / rel
                    save(full_init, rec)
                    all_initializers[rel_key] = sha(full_init)

                    if phase == "evaluate":
                        xx = cp_runner.raw_experts_from_bank(eval_bank)
                        ref_e = np.asarray(eval_bank["reference"], dtype=np.float64)
                        yy_e = np.asarray(eval_bank["shortfall"], dtype=np.float64)
                        mm_e = np.asarray(eval_bank["mask"], dtype=bool)
                        aa_e = np.asarray(eval_bank["anchors"], dtype=np.int64)
                        act_e, _ = predict_conditional_pool(xx, b_eval, ref_e, rec)
                        led_e, _, _ = score_actions(act_e, yy_e, mm_e, aa_e)
                        cp_idx = 1040 + 3 * rid + ai
                        cp_ledger[si, cp_idx] = led_e

    assert len(all_initializers) == 1080
    np.savez_compressed(
        cp_dir / "all_daily_ledger.npz",
        ledger=cp_ledger,
        counts=mp_npz["counts"],
        day_ids=mp_npz["day_ids"],
    )
    save(
        cp_dir / "inference_span3.json",
        dict(
            schema="autonomous-campaign-inference-v1",
            policy_names=cp_names,
            available=cp_avail,
            family_definition=dict(
                policy_names=cp_names,
                comparisons=[list(p) for p in cp_comps],
                frozen_aliases=[list(p) for p in cp_aliases],
            ),
        ),
    )

    cp_proto = dict(
        study_id="conditional_pool_20261025_v1",
        parent_results=str(mp_dir),
        parent_freeze_sha256=sha(mp_dir / "FINAL_FREEZE.json"),
        parent_ledger_sha256=sha(mp_dir / "all_daily_ledger.npz"),
        parent_span3_sha256=sha(mp_dir / "inference_span3.json"),
        stream_parent_results=str(mc_dir),
        stream_parent_freeze_sha256=sha(mc_dir / "FINAL_FREEZE.json"),
    )
    save(cp_dir / "protocol_original.json", cp_proto)
    save(cp_dir / "protocol.json", cp_proto)
    cp_roles = {
        "C": dict(minimum_C_id=18, minimum_maxV_id=1),
        "P": dict(minimum_C_id=21, minimum_maxV_id=1),
        "Z": dict(minimum_C_id=21, minimum_maxV_id=1),
    }
    cp_freeze = dict(
        study_id="conditional_pool_20261025_v1",
        protocol_sha256=sha(cp_dir / "protocol_original.json"),
        parent_freeze_sha256=cp_proto["parent_freeze_sha256"],
        stream_parent_freeze_sha256=cp_proto["stream_parent_freeze_sha256"],
        historical_roles=dict(roles=cp_roles, qualification_did_not_filter_instances=True),
        all_initializers=all_initializers,
        all_streams=mc_freeze["all_streams"],
    )
    save(cp_dir / "FINAL_FREEZE.json", cp_freeze)
    save(
        cp_dir / "EVALUATION_OPEN.json",
        dict(
            freeze_sha256=sha(cp_dir / "FINAL_FREEZE.json"),
            protocol_sha256=cp_freeze["protocol_sha256"],
        ),
    )

    src_file = tmp_path / "dummy_conditional_refine_source.py"
    src_file.write_text("# synthetic conditional refine source\n", encoding="utf-8")

    cfg = dict(
        study_id="conditional_refine_20261025_synthetic",
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
        refined_recipe_ids=[16, 19, 22, 23],
        unchanged_control_recipe_ids=[
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 18, 20, 21
        ],
        budget_reservation=dict(
            new_candidates=24,
            cpu_seconds=14400,
            total_reserved_candidates=1550,
            total_accounted_plus_open_reservations_cpu=65808,
            global_cpu_limit_unchanged=86400,
            refined_recipe_ids=[16, 19, 22, 23],
            unchanged_control_recipe_ids=[
                0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 18, 20, 21
            ],
        ),
        expected_historical_grid=False,
        expected_evaluation_anchors=mp_cfg["expected_evaluation_anchors"],
        expected_evaluation_valid_cells=mp_cfg["expected_evaluation_valid_cells"],
        expected_parent_policies=1112,
        expected_parent_comparisons=4599,
        parent_results=str(cp_dir),
        parent_freeze_sha256=sha(cp_dir / "FINAL_FREEZE.json"),
        parent_ledger_sha256=sha(cp_dir / "all_daily_ledger.npz"),
        parent_span3_sha256=sha(cp_dir / "inference_span3.json"),
        stream_parent_results=str(mc_dir),
        stream_parent_freeze_sha256=sha(mc_dir / "FINAL_FREEZE.json"),
        recipes=nr_runner.build_conditional_pool_recipes(),
        source_hashes={"dummy_conditional_refine_source.py": sha(src_file)},
        inference=dict(spans=[3, 1, 7], n_boot=4, seed=20261022),
    )
    protocol_path = tmp_path / "protocol.json"
    save(protocol_path, cfg)
    return cfg, protocol_path, tmp_path, hist_cache, eval_cache


def test_isolation_honest_budget_and_extended_family(tmp_path):
    # Isolated private module does not mutate shared scripts.run_conditional_pool
    assert cp_runner.POLICY_PREFIX == "CP"
    assert nr_runner.POLICY_PREFIX == "NR"
    assert nr_runner._BASE.POLICY_PREFIX == "NR"
    assert nr_runner._BASE is not cp_runner

    cfg, _, _, _, _ = _make_synthetic_cp_parent_campaign(tmp_path / "fam")
    recipes = nr_runner.verify_budget_and_recipes(cfg)
    assert len(recipes) == 24

    # Honest budget validator rejects old 1526/60997 values and invalid refined IDs
    bad_old = copy.deepcopy(cfg)
    bad_old["budget_reservation"]["total_reserved_candidates"] = 1526
    bad_old["budget_reservation"]["total_accounted_plus_open_reservations_cpu"] = 60997
    with pytest.raises(ValueError, match="65808/86400/1550"):
        nr_runner.verify_budget_and_recipes(bad_old)

    bad_ids = copy.deepcopy(cfg)
    bad_ids["refined_recipe_ids"] = [16, 19, 22]
    with pytest.raises(ValueError, match="refined_recipe_ids"):
        nr_runner.verify_budget_and_recipes(bad_ids)

    cp_dir = Path(cfg["parent_results"])
    span3 = json.loads((cp_dir / "inference_span3.json").read_text(encoding="utf-8"))
    cp_freeze = json.loads((cp_dir / "FINAL_FREEZE.json").read_text(encoding="utf-8"))
    names, avail, aliases, comps, summary = nr_runner.build_extended_family(span3, recipes, cp_freeze)

    assert len(names) == 1112 + 72 == 1184
    assert len(avail) == 1112
    assert names[1112:1115] == ["NR000_C", "NR000_P", "NR000_Z"]
    assert names[-3:] == ["NR023_C", "NR023_P", "NR023_Z"]
    assert len(comps) == 4599 + 492 + 72 == 5163
    assert 11 * len(names) + 10 * len(comps) == 64654

    parent_aliases = span3["family_definition"]["frozen_aliases"]
    assert len(aliases) == len(parent_aliases) + 60
    assert summary["new_unchanged_control_alias_count"] == 60
    assert summary["new_comparison_breakdown"]["direct_refinement_vs_parent_cp_pairs"] == 72
    assert summary["new_comparison_breakdown"]["total_new_comparisons"] == 564

    # All 72 direct NR vs CP comparisons present; 60 non-refined aliases present; 4 refined IDs excluded from aliases
    for rid in range(24):
        for arm in META_ARMS:
            assert (f"NR{rid:03d}_{arm}", f"CP{rid:03d}_{arm}") in comps
            if rid in (16, 19, 22, 23):
                assert (f"NR{rid:03d}_{arm}", f"CP{rid:03d}_{arm}") not in aliases
            else:
                assert (f"NR{rid:03d}_{arm}", f"CP{rid:03d}_{arm}") in aliases


def test_focused_initializer_hook_warmstart_reuse_and_tamper_rejection(tmp_path):
    cfg, _, _, _, _ = _make_synthetic_cp_parent_campaign(tmp_path / "hook")
    cp_dir = Path(cfg["parent_results"])
    cp_freeze = json.loads((cp_dir / "FINAL_FREEZE.json").read_text(encoding="utf-8"))
    mc_dir = Path(cfg["stream_parent_results"])
    mc_freeze = json.loads((mc_dir / "FINAL_FREEZE.json").read_text(encoding="utf-8"))
    source_cfg, meta_dir = resolve_meta_source_protocol(cfg, mc_dir, mc_freeze)
    hist_anchors, b_hist_full, hist_profile_sha, hist_manifest_sha = (
        load_verified_causal_profile_and_anchors(
            source_cfg, "historical", 201, meta_dir=meta_dir, parent_mc_dir=mc_dir
        )
    )
    inner_bank, _ = load_verified_parent_stream_bank(mc_dir, mc_freeze, "inner", 201, "C")
    outer_bank, _ = load_verified_parent_stream_bank(mc_dir, mc_freeze, "outer", 201, "C")
    b_inner = select_exact_anchor_slice(hist_anchors, b_hist_full, inner_bank["anchors"])
    outer_start = int(outer_bank["anchors"][0])
    recipes = nr_runner.build_conditional_pool_recipes()

    kernel_calls: list[dict] = []
    real_kernel = nr_runner.kernel_mod.fit_conditional_pool

    def spy_kernel(x, b, y, mask, anchors, reference, **kwargs):
        kernel_calls.append(kwargs)
        return real_kernel(x, b, y, mask, anchors, reference, **kwargs)

    hook = nr_runner._make_initializer_hook(
        parent_cp_dir=cp_dir,
        parent_cp_freeze=cp_freeze,
        refined_ids={16, 19, 22, 23},
        orig_fit_oof=nr_runner._BASE.fit_oof_conditional_pool_initializer,
        kernel_fn=spy_kernel,
    )

    # 1. Non-refined recipe (id=0): kernel NOT called, weights exact match with parent
    parent_0 = json.loads((cp_dir / "initializers/outer/C_seed201/CP000.json").read_text(encoding="utf-8"))
    rec_0 = hook(
        phase="outer",
        seed=201,
        arm="C",
        recipe=recipes[0],
        oof_bank=inner_bank,
        b_oof=b_inner,
        episode_start=outer_start,
        source_manifest_sha256=hist_manifest_sha,
        parent_profile_sha256=hist_profile_sha,
        time_limit=8.0,
    )
    assert len(kernel_calls) == 0
    assert rec_0["newly_solved"] is False
    assert rec_0["reused_from_parent"] is True
    assert rec_0["weights"] == parent_0["weights"]
    assert rec_0["parent_initializer_sha256"] == cp_freeze["all_initializers"]["initializers/outer/C_seed201/CP000.json"]

    # 2. Refined recipe (id=16): kernel called with time_limit=60, time_budget_ceiling=60, warm_start_weights=parent
    parent_16 = json.loads((cp_dir / "initializers/outer/C_seed201/CP016.json").read_text(encoding="utf-8"))
    rec_16 = hook(
        phase="outer",
        seed=201,
        arm="C",
        recipe=recipes[16],
        oof_bank=inner_bank,
        b_oof=b_inner,
        episode_start=outer_start,
        source_manifest_sha256=hist_manifest_sha,
        parent_profile_sha256=hist_profile_sha,
        time_limit=8.0,
    )
    assert len(kernel_calls) == 1
    assert kernel_calls[0]["time_limit"] == 60.0
    assert kernel_calls[0]["time_budget_ceiling"] == 60.0
    assert np.array_equal(kernel_calls[0]["warm_start_weights"], np.asarray(parent_16["weights"]))
    assert rec_16["newly_solved"] is True
    assert rec_16["reused_from_parent"] is False
    assert rec_16["objective"] <= parent_16["objective"] + 1e-12

    # 3. Immature OOF window rejected
    with pytest.raises(ValueError, match="not strictly mature"):
        hook(
            phase="outer",
            seed=201,
            arm="C",
            recipe=recipes[16],
            oof_bank=inner_bank,
            b_oof=b_inner,
            episode_start=int(inner_bank["anchors"][-1]) + 7,
            source_manifest_sha256=hist_manifest_sha,
            parent_profile_sha256=hist_profile_sha,
        )

    # 4. Tampered parent initializer file rejected by SHA guard
    p16_path = cp_dir / "initializers/outer/C_seed201/CP016.json"
    orig_bytes = p16_path.read_bytes()
    try:
        p16_path.write_bytes(orig_bytes + b" ")
        with pytest.raises(ValueError, match="SHA-256 mismatch"):
            hook(
                phase="outer",
                seed=201,
                arm="C",
                recipe=recipes[16],
                oof_bank=inner_bank,
                b_oof=b_inner,
                episode_start=outer_start,
                source_manifest_sha256=hist_manifest_sha,
                parent_profile_sha256=hist_profile_sha,
            )
    finally:
        p16_path.write_bytes(orig_bytes)


def test_full_refinement_pipeline_120_new_600_reused_and_alias_verification(tmp_path, monkeypatch):
    cfg, protocol_path, root, _, eval_cache = _make_synthetic_cp_parent_campaign(tmp_path)
    out = tmp_path / "out"

    kernel_call_log: list[tuple[int, float, float]] = []

    def fast_refinement_kernel(
        x,
        b,
        y,
        mask,
        anchors,
        reference,
        *,
        groups=3,
        relief=0.03,
        cap_mode="POOLED",
        time_limit=60.0,
        time_budget_ceiling=60.0,
        warm_start_weights=None,
        max_iter=1200,
        tol=1e-7,
        **kwargs,
    ):
        assert time_limit == 60.0 and time_budget_ceiling == 60.0
        assert warm_start_weights is not None
        w_warm = np.asarray(warm_start_weights, dtype=np.float64)
        assert w_warm.shape == (groups, 25)
        kernel_call_log.append((int(groups), float(relief), float(time_budget_ceiling)))

        cuts = fit_context_cuts(reference, groups)
        y_v = y[mask]
        b_v = b[mask]
        u = float(np.maximum(y_v - b_v, 0.0).mean())
        c = float((b_v + 10.0 * np.maximum(y_v - b_v, 0.0)).mean() / 6.0)
        rec = initialize_anchor_record(groups=groups, relief=relief, cap_mode=cap_mode)
        rec.update(
            status="OPTIMAL_NUMERICAL_BOUNDS",
            optimal=True,
            numerical_fitted=True,
            cuts=cuts,
            cuts_source=("HISTORICAL_REFERENCE_GRID_QUANTILES" if groups == 3 else "SINGLE_POOL_NO_CUTS"),
            weights=w_warm.tolist(),
            raw_weights=w_warm.tolist(),
            canonical_initial=w_warm.tolist(),
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
            time_budget_ceiling=float(time_budget_ceiling),
            warm_start_provided=True,
            warm_start_accepted=True,
            warm_start_objective=c,
            max_iter=int(max_iter),
            relative_tolerance=float(tol),
        )
        return rec

    monkeypatch.setattr(nr_runner.kernel_mod, "fit_conditional_pool", fast_refinement_kernel)

    # Guard evaluation cache during history shards
    eval_cache_resolved = eval_cache.resolve()
    real_np_load = np.load

    def guarded_load(file, *args, **kwargs):
        if isinstance(file, (str, os.PathLike)):
            p = Path(file).resolve()
            if p == eval_cache_resolved or eval_cache_resolved in p.parents:
                raise AssertionError(f"Evaluation cache read during history stage: {p}")
        return real_np_load(file, *args, **kwargs)

    monkeypatch.setattr(np, "load", guarded_load)
    for shard in range(15):
        rec = nr_runner.run_history_shard(cfg, out, shard, protocol_path=protocol_path, root=root)
        assert rec["initializers_prepared"] == 72
        assert rec["initializers_numerical_fitted"] == 48
        assert rec["initializers_newly_solved"] == 8
        assert rec["initializers_reused_from_parent"] == 40
        assert rec["initializers_anchor_declared"] == 24
        assert rec["new_models_fitted"] == 0
    monkeypatch.setattr(np, "load", real_np_load)

    # Exactly 120 new solves across 15 shards (15 * 2 phases * 4 refined recipes); 0 calls for the other 20 recipes
    assert len(kernel_call_log) == 120

    freeze = nr_runner.run_freeze_stage(cfg, out, protocol_path=protocol_path, root=root)
    assert len(freeze["all_initializers"]) == 1080
    assert freeze["numerical_fits"] == 720
    assert freeze["actual_new_numerical_fits"] == 120
    assert freeze["reused_parent_numerical_fits"] == 600
    assert freeze["anchor_declarations"] == 360

    for shard in range(15):
        nr_runner.run_evaluate_shard(cfg, out, shard, protocol_path=protocol_path, root=root)

    # Tamper one non-refined daily ledger slot -> aggregate alias check must reject ledger mismatch
    d_c201_path = out / "instances/evaluate/C_seed201/daily.npz"
    orig_d_bytes = d_c201_path.read_bytes()
    try:
        d_npz = np.load(d_c201_path)
        bad_led = d_npz["ledger"].copy()
        bad_led[0, 0, 0] += 1.0  # Tamper NR000_C
        np.savez_compressed(
            d_c201_path,
            ledger=bad_led,
            reference=d_npz["reference"],
            counts=d_npz["counts"],
            days=d_npz["days"],
        )
        with pytest.raises(ValueError, match="5-fit daily ledger mismatch"):
            nr_runner.run_aggregate_stage(
                cfg, out, protocol_path=protocol_path, root=root, n_boot_override=4
            )
    finally:
        d_c201_path.write_bytes(orig_d_bytes)
        shutil.rmtree(out / "shards" / "aggregate", ignore_errors=True)
        (out / "failure.json").unlink(missing_ok=True)

    completion = nr_runner.run_aggregate_stage(
        cfg, out, protocol_path=protocol_path, root=root, n_boot_override=4
    )
    assert completion["status"] == "COMPLETED_ALL_PREDEFINED_INSTANCES"
    assert completion["total_planned_instances"] == 1080
    assert completion["numerical_fits"] == 720
    assert completion["actual_new_numerical_fits"] == 120
    assert completion["reused_parent_numerical_fits"] == 600
    assert completion["anchor_declarations"] == 360
    assert completion["new_models_fitted"] == 0
    assert completion["thresholds_changed"] is False

    all_names = json.loads((out / "all_policy_names.json").read_text(encoding="utf-8"))
    assert all_names["parent_policy_count"] == 1112
    assert all_names["new_policy_count"] == 72
    assert len(all_names["names"]) == 1184
    assert all_names["parent_comparison_count"] == 4599
    assert all_names["new_comparison_count"] == 564
    assert all_names["total_comparison_count"] == 5163
    assert all_names["nominal_family_size"] == 64654
    assert all_names["new_unchanged_control_alias_count"] == 60

    span3_out = json.loads((out / "inference_span3.json").read_text(encoding="utf-8"))
    verified_pairs = {
        (row["left"], row["right"]): row["verified"] for row in span3_out["alias_verification"]
    }
    for rid in nr_runner.DEFAULT_UNCHANGED_RECIPE_IDS:
        for arm in META_ARMS:
            assert verified_pairs[(f"NR{rid:03d}_{arm}", f"CP{rid:03d}_{arm}")] is True
    for rid in nr_runner.DEFAULT_REFINED_RECIPE_IDS:
        for arm in META_ARMS:
            assert (f"NR{rid:03d}_{arm}", f"CP{rid:03d}_{arm}") not in verified_pairs
