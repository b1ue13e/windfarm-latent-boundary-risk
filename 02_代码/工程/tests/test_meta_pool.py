import json
import os
from repo_paths import Path, repository_root
import shutil

import numpy as np
import pytest

import scripts.run_meta_calibration as mc_runner
import scripts.run_meta_pool as runner
from scripts.run_mixture_closed_loop import save, score_actions, sha
from windfarm_moe.actual_mixture_update import MixtureConfig
from windfarm_moe.bounded_relief import fit_signed, run_signed, signed_action, signed_experts
from windfarm_moe.meta_action_stream import join_banks, save_bank
from windfarm_moe.residual_meta import META_ARMS
from tests.test_meta_calibration import _make_synthetic_parent_campaign


def _write_minimal_cache(cache_dir: Path, anchors: np.ndarray, y: np.ndarray, m: np.ndarray) -> str:
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(cache_dir / "anchors.npy", anchors)
    np.save(cache_dir / "shortfall.npy", y)
    np.save(cache_dir / "mask.npy", m)
    files = {p.name: dict(bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(cache_dir.glob("*.npy"))}
    save(cache_dir / "manifest.json", dict(files=files))
    return sha(cache_dir / "manifest.json")


def _make_synthetic_mc_parent_campaign(tmp_path: Path, *, coincide_roles: bool = False):
    """Build synthetic parent MC campaign (968 policies, 3639 comparisons) using existing test fixture."""
    mc_cfg_base, _, _, bank_store = _make_synthetic_parent_campaign(tmp_path / "base_mr")
    meta_root = Path(mc_cfg_base["parent_results"])
    mc_dir = tmp_path / "parent_mc_campaign"
    mc_dir.mkdir(parents=True, exist_ok=True)

    # Full historical cache (starts at 27648, covers inner 28087..28096 and outer 28944..28953)
    ha_pre = np.arange(27648, 27656, dtype=np.int64)
    ha_in = bank_store[("inner", 201, "C")]["anchors"]
    ha_out = bank_store[("outer", 201, "C")]["anchors"]
    ha_full = np.concatenate([ha_pre, ha_in, ha_out])
    hy_full = np.ones((len(ha_full), 2), dtype=np.float64) * 6.0
    hm_full = np.ones_like(hy_full, dtype=bool)
    hm_full[len(ha_pre) + 1, 1] = False
    hy_full[len(ha_pre) + 1, 1] = np.nan
    hist_cache = tmp_path / "hist_cache"
    hist_manifest_sha = _write_minimal_cache(hist_cache, ha_full, hy_full, hm_full)

    ea_full = bank_store[("evaluate", 201, "C")]["anchors"]
    ey_full = bank_store[("evaluate", 201, "C")]["shortfall"]
    em_full = bank_store[("evaluate", 201, "C")]["mask"]
    eval_cache = tmp_path / "eval_cache"
    eval_manifest_sha = _write_minimal_cache(eval_cache, ea_full, ey_full, em_full)

    profiles_dir = meta_root / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    parent_profiles = {}
    for si, seed in enumerate(runner.SEEDS):
        b_h = np.full_like(hy_full, 4.5 + 0.1 * si, dtype=np.float64)
        p_h = profiles_dir / f"historical_seed{seed}.npy"
        np.save(p_h, b_h)
        parent_profiles[f"profiles/historical_seed{seed}.npy"] = dict(
            path=str(p_h), sha256=sha(p_h), bytes=p_h.stat().st_size
        )
        b_e = np.full_like(ey_full, 5.0 + 0.1 * si, dtype=np.float64)
        p_e = profiles_dir / f"evaluate_seed{seed}.npy"
        np.save(p_e, b_e)
        parent_profiles[f"profiles/evaluate_seed{seed}.npy"] = dict(
            path=str(p_e), sha256=sha(p_e), bytes=p_e.stat().st_size
        )

    meta_proto = dict(
        study_id="residual_meta_20261024_v1",
        historical_cache=str(hist_cache),
        historical_manifest_sha256=hist_manifest_sha,
        evaluation_cache=str(eval_cache),
        evaluation_manifest_sha256=eval_manifest_sha,
        parent_profiles=parent_profiles,
    )
    save(meta_root / "protocol_original.json", meta_proto)
    save(meta_root / "protocol.json", meta_proto)
    save(
        meta_root / "FINAL_FREEZE.json",
        dict(study_id="residual_meta_20261024_v1", protocol_sha256=sha(meta_root / "protocol_original.json")),
    )

    # Extend 680/2199 MR family to 968/3639 MC family via run_meta_calibration.build_extended_family
    mr_span3 = json.loads((meta_root / "inference_span3.json").read_text(encoding="utf-8"))
    mc_recipes = mc_runner.build_calibration_recipes()
    mc_names, mr_avail, mc_aliases, mc_comps, _ = mc_runner.build_extended_family(
        mr_span3, mc_recipes, expected_parent_policies=680, expected_parent_comparisons=2199
    )
    mc_avail = mr_avail + [True] * 288
    assert len(mc_names) == 968 and len(mc_comps) == 3639

    mr_npz = np.load(meta_root / "all_daily_ledger.npz")
    mc_ledger = np.ones((5, 968, 35, 4), dtype=np.float64)
    mc_ledger[:, :680] = mr_npz["ledger"]
    for rid in range(96):
        base_id = rid // 4
        cal_id = rid % 4
        for ai in range(3):
            mc_idx = 680 + 3 * rid + ai
            mr_idx = 608 + 3 * base_id + ai
            if cal_id == 0:
                mc_ledger[:, mc_idx] = mr_npz["ledger"][:, mr_idx]
            else:
                mc_ledger[:, mc_idx] = mr_npz["ledger"][:, mr_idx] + 0.01 * cal_id
    np.savez_compressed(
        mc_dir / "all_daily_ledger.npz",
        ledger=mc_ledger,
        counts=mr_npz["counts"],
        day_ids=mr_npz["day_ids"],
    )
    save(
        mc_dir / "inference_span3.json",
        dict(
            schema="autonomous-campaign-inference-v1",
            policy_names=mc_names,
            available=mc_avail,
            family_definition=dict(
                policy_names=mc_names,
                comparisons=[list(p) for p in mc_comps],
                frozen_aliases=[list(p) for p in mc_aliases],
            ),
        ),
    )

    all_streams = {}
    for shard in range(15):
        seed, arm = runner.shard_assignment(shard)
        for phase in ("inner", "outer", "evaluate"):
            s_rel = str(runner.stream_relpath(phase, arm, seed)).replace("\\", "/")
            m_rel = str(runner.stream_metadata_relpath(phase, arm, seed)).replace("\\", "/")
            b_raw = dict(bank_store[(phase, seed, arm)])
            b_meta = dict(b_raw["metadata"])
            b_meta["source_manifest_sha256"] = eval_manifest_sha if phase == "evaluate" else hist_manifest_sha
            b_meta["historical_manifest_sha256"] = hist_manifest_sha
            b_meta["parent_profile_sha256"] = parent_profiles[
                f"profiles/{'evaluate' if phase == 'evaluate' else 'historical'}_seed{seed}.npy"
            ]["sha256"]
            b_raw["metadata"] = b_meta
            manifest = save_bank(mc_dir / s_rel, b_raw)
            rec = dict(
                phase=phase,
                seed=seed,
                arm=arm,
                npz_path=s_rel,
                npz_sha256=manifest["npz_sha256"],
                metadata_path=m_rel,
                metadata_sha256=manifest["metadata_sha256"],
                raw_actions_sha256=manifest["raw_actions_sha256"],
                raw_action_sha256=b_meta["raw_action_sha256"],
            )
            if phase in ("inner", "outer"):
                all_streams[s_rel] = rec
            else:
                eval_s_dir = mc_dir / "shards" / "evaluate" / f"shard_{shard:02d}_{arm}_seed{seed}"
                eval_s_dir.mkdir(parents=True, exist_ok=True)
                save(eval_s_dir / "receipt.json", dict(status="COMPLETED", evaluate_stream=rec))
                inst_e_dir = mc_dir / "instances" / "evaluate" / f"{arm}_seed{seed}"
                inst_e_dir.mkdir(parents=True, exist_ok=True)
                save(inst_e_dir / "receipt.json", dict(phase="evaluate", seed=seed, arm=arm, bank_npz_sha256=manifest["npz_sha256"]))

    mc_proto = dict(study_id="meta_calibration_20261025_v2", parent_results=str(meta_root))
    save(mc_dir / "protocol_original.json", mc_proto)
    save(mc_dir / "protocol.json", mc_proto)
    roles = {
        "C": dict(minimum_C_id=12, minimum_maxV_id=(12 if coincide_roles else 35)),
        "P": dict(minimum_C_id=24, minimum_maxV_id=67),
        "Z": dict(minimum_C_id=40, minimum_maxV_id=91),
    }
    mc_freeze = dict(
        study_id="meta_calibration_20261025_v2",
        protocol_sha256=sha(mc_dir / "protocol_original.json"),
        historical_roles=dict(roles=roles, qualification_did_not_filter_instances=True),
        all_streams=all_streams,
    )
    save(mc_dir / "FINAL_FREEZE.json", mc_freeze)
    save(
        mc_dir / "EVALUATION_OPEN.json",
        dict(freeze_sha256=sha(mc_dir / "FINAL_FREEZE.json"), protocol_sha256=mc_freeze["protocol_sha256"]),
    )

    src_file = tmp_path / "dummy_pool_source.py"
    src_file.write_text("# synthetic meta pool source\n", encoding="utf-8")

    cfg = dict(
        study_id="meta_pool_20261025_synthetic",
        max_candidates=24,
        max_cpu_seconds=14400,
        history_wall_seconds=300,
        evaluation_wall_seconds=300,
        freeze_wall_seconds=60,
        aggregate_wall_seconds=1200,
        independent_audit_wall_seconds=300,
        local_retry_reserve_seconds=3840,
        maximum_science_parallel_jobs=15,
        per_job_ncpus=1,
        aggregate_mem_gb=96,
        budget_reservation=dict(
            new_candidates=24,
            cpu_seconds=14400,
            total_reserved_candidates=1502,
            total_accounted_plus_open_reservations_cpu=75687,
            global_cpu_limit_unchanged=86400,
        ),
        expected_historical_grid=False,
        expected_evaluation_anchors=len(ea_full),
        expected_evaluation_valid_cells=int(em_full.sum()),
        expected_parent_policies=968,
        expected_parent_comparisons=3639,
        parent_results=str(mc_dir),
        parent_freeze_sha256=sha(mc_dir / "FINAL_FREEZE.json"),
        parent_ledger_sha256=sha(mc_dir / "all_daily_ledger.npz"),
        parent_span3_sha256=sha(mc_dir / "inference_span3.json"),
        recipes=runner.build_pool_recipes(),
        source_hashes={"dummy_pool_source.py": sha(src_file)},
        inference=dict(spans=[3, 1, 7], n_boot=4, seed=20261022),
    )
    protocol_path = tmp_path / "protocol.json"
    save(protocol_path, cfg)
    return cfg, protocol_path, tmp_path, hist_cache, eval_cache


def test_24_recipe_grid_budget_and_family_comparator_deduplication(tmp_path):
    recipes = runner.build_pool_recipes()
    assert len(recipes) == 24
    assert [r["id"] for r in recipes] == list(range(24))
    assert 15 * 300 + 15 * 300 + 60 + 1200 + 300 + 3840 == 14400

    for idx, d in enumerate(runner.RELIEF_GRID):
        for gi, g in enumerate(runner.GOALS):
            for mi, (m, eta, gamma) in enumerate([("FIXED", 0.0, 0.0), ("ONLINE", 0.3, 10.0)]):
                rid = idx * 4 + gi * 2 + mi
                assert recipes[rid] == dict(
                    id=rid,
                    relief=float(d),
                    goal=g,
                    mode=m,
                    config=dict(
                        eta=eta,
                        schedule_power=0.5,
                        severity_step=gamma,
                        cost_scale=100.0,
                        proximity_strength=0.0,
                    ),
                )

    # Distinct historical MC roles -> 3639 + 468 = 4107 comparisons (968 + 72 = 1040 roles)
    cfg1, _, _, _, _ = _make_synthetic_mc_parent_campaign(tmp_path / "distinct", coincide_roles=False)
    mc_dir1 = Path(cfg1["parent_results"])
    span3_1 = json.loads((mc_dir1 / "inference_span3.json").read_text(encoding="utf-8"))
    freeze_1 = json.loads((mc_dir1 / "FINAL_FREEZE.json").read_text(encoding="utf-8"))
    names1, _, aliases1, comps1, mc_comp1 = runner.build_extended_family(span3_1, recipes, freeze_1)
    assert len(names1) == 1040
    assert len(comps1) == 3639 + 468
    assert names1[968:971] == ["MP000_C", "MP000_P", "MP000_Z"]
    assert names1[-3:] == ["MP023_C", "MP023_P", "MP023_Z"]
    assert mc_comp1["C"] == dict(minimum_C="MC012_C", minimum_maxV="MC035_C")
    assert len(aliases1) == len(span3_1["family_definition"]["frozen_aliases"])

    # Coinciding historical MC roles on arm C (minC == minmaxV == MC012_C) -> 24 duplicates deduplicated -> 468 - 24 = 444 new
    cfg2, _, _, _, _ = _make_synthetic_mc_parent_campaign(tmp_path / "coincide", coincide_roles=True)
    mc_dir2 = Path(cfg2["parent_results"])
    span3_2 = json.loads((mc_dir2 / "inference_span3.json").read_text(encoding="utf-8"))
    freeze_2 = json.loads((mc_dir2 / "FINAL_FREEZE.json").read_text(encoding="utf-8"))
    names2, _, _, comps2, mc_comp2 = runner.build_extended_family(span3_2, recipes, freeze_2)
    assert len(names2) == 1040
    assert mc_comp2["C"] == dict(minimum_C="MC012_C", minimum_maxV="MC012_C")
    assert len(comps2) == 3639 + 444


def test_raw_24_experts_api_floors_and_hand_oracle():
    """Verify passing RAW 24 experts [T, N, 24] (not 25 signed increments) to run_signed and fit_signed."""
    t_steps, n_nodes = 9, 2
    b = np.full((t_steps, n_nodes), 10.0, dtype=np.float64)
    # 24 raw Meta experts; expert 0 is 0.0 (< b), expert 1 is 22.0 (> b), experts 2..23 are 10.0 (== b)
    raw_actions = np.full((24, t_steps, n_nodes), 10.0, dtype=np.float64)
    raw_actions[0] = 0.0
    raw_actions[1] = 22.0
    bank = dict(raw_actions=raw_actions)
    x24 = runner.raw_experts_from_bank(bank)
    assert x24.shape == (t_steps, n_nodes, 24)

    # Notice x24[:, :, 0] == 0.0 and x24 >= 0.0: run_signed must treat x24 as 24 RAW experts and prepend anchor slot 0 -> 25 weights!
    for d in runner.RELIEF_GRID:
        delta25 = signed_experts(x24, b, relief=d)
        assert delta25.shape == (t_steps, n_nodes, 25)
        np.testing.assert_array_equal(delta25[:, :, 0], 0.0)
        np.testing.assert_allclose(delta25[:, :, 1], -d * 10.0)
        np.testing.assert_allclose(delta25[:, :, 2], 12.0)

        w = np.zeros(25, dtype=np.float64)
        w[1] = 1.0  # pure lowest expert
        act = signed_action(b, delta25, w, relief=d)
        np.testing.assert_allclose(act, (1.0 - d) * 10.0, rtol=0.0, atol=1e-14)
        if d == 0.0:
            assert np.all(act >= b)

    # Hand-computed 1-step online update with 24 raw experts (25 simplex weights) at d=0.5:
    y = np.tile(np.array([25.0, 7.75]), (t_steps, 1))
    m = np.ones_like(y, dtype=bool)
    a = np.arange(t_steps, dtype=np.int64)
    w0 = np.zeros(25, dtype=np.float64)
    w0[0], w0[1], w0[2] = 1 / 8, 3 / 4, 1 / 8  # r_0 = 10 + 0 - 3.75 + 1.5 = 7.75
    cfg = MixtureConfig(eta=1.0, schedule_power=0.5, severity_step=10.0, cost_scale=100.0, proximity_strength=0.0)
    res = run_signed(x24, b, y, m, a, [cfg], w0, relief=0.5, score=True, return_actions=True)
    static_act = signed_action(b, signed_experts(x24, b, relief=0.5), w0, relief=0.5)
    np.testing.assert_array_equal(res["actions"][0, :8], static_act[:8])
    assert len(res["metadata"]["final_weights"][0]) == 25
    assert res["metadata"]["feedback_updates"] == 1
    assert not np.array_equal(res["actions"][0, 8], static_act[8])


def test_oof_fit_mask_nan_handling_and_causal_maturity_enforced(monkeypatch):
    """Verify masked NaNs/Inf/negatives outside mask are ignored, valid NaNs rejected, and causal maturity enforced."""
    anchors = np.arange(28087, 28095, dtype=np.int64)  # last=28094, release=28101 < outer start 28944
    raw = np.full((24, len(anchors), 2), 6.0, dtype=np.float64)
    raw[0] = 4.0
    raw[1] = 9.0
    y = np.full((len(anchors), 2), 7.0, dtype=np.float64)
    m = np.ones_like(y, dtype=bool)
    m[2, 1] = False
    m[5, 0] = False
    y[2, 1] = np.nan
    y[5, 0] = np.nan
    b = np.full_like(y, 5.0)

    bank = dict(
        anchors=anchors,
        shortfall=y,
        mask=m,
        reference=b,
        raw_actions=raw,
        metadata=dict(phase="inner", phases=["inner"], raw_actions_sha256="a" * 64),
    )

    rec1 = runner.fit_oof_pool_initializer(
        phase="outer",
        seed=201,
        arm="C",
        relief=0.1,
        goal="CAP",
        oof_bank=bank,
        b_oof=b,
        episode_start=28944,
        source_manifest_sha256="1" * 64,
        parent_profile_sha256="2" * 64,
        time_limit=2.0,
    )
    assert rec1["numerical_fitted"] is True
    assert rec1["valid_fit_cells"] == int(m.sum())
    assert rec1["fit_window"] == [28087, 28095]
    assert rec1["last_label_release"] == 28094 + 7 < 28944
    assert len(rec1["weights"]) == 25
    assert rec1["weights"] == rec1["canonical_initial"]

    # Mutate unmasked (~m) target cells to -999 or +inf: fitted weights and objective must be bitwise identical
    for sentinel in (-999.0, np.inf, np.nan):
        y_alt = y.copy()
        y_alt[~m] = sentinel
        bank_alt = dict(bank, shortfall=y_alt)
        rec_alt = runner.fit_oof_pool_initializer(
            phase="outer",
            seed=201,
            arm="C",
            relief=0.1,
            goal="CAP",
            oof_bank=bank_alt,
            b_oof=b,
            episode_start=28944,
            source_manifest_sha256="1" * 64,
            parent_profile_sha256="2" * 64,
            time_limit=2.0,
        )
        assert rec_alt["weights"] == rec1["weights"]
        assert rec_alt["objective"] == rec1["objective"]

    # Valid masked cell containing NaN or negative value must be rejected immediately
    y_bad_valid = y.copy()
    y_bad_valid[0, 0] = np.nan
    with pytest.raises(ValueError, match="Valid masked OOF shortfall"):
        runner.fit_oof_pool_initializer(
            phase="outer",
            seed=201,
            arm="C",
            relief=0.1,
            goal="COST",
            oof_bank=dict(bank, shortfall=y_bad_valid),
            b_oof=b,
            episode_start=28944,
            source_manifest_sha256="1" * 64,
            parent_profile_sha256="2" * 64,
        )

    # Immature OOF window (last_anchor + 7 >= episode_start) or pre-28087 anchor must be rejected
    with pytest.raises(ValueError, match="not strictly mature"):
        runner.fit_oof_pool_initializer(
            phase="outer",
            seed=201,
            arm="C",
            relief=0.1,
            goal="COST",
            oof_bank=bank,
            b_oof=b,
            episode_start=28101,  # == 28094 + 7
            source_manifest_sha256="1" * 64,
            parent_profile_sha256="2" * 64,
        )

    bank_early = dict(bank, anchors=np.arange(28080, 28088, dtype=np.int64))
    with pytest.raises(ValueError, match="before 28087"):
        runner.fit_oof_pool_initializer(
            phase="outer",
            seed=201,
            arm="C",
            relief=0.1,
            goal="COST",
            oof_bank=bank_early,
            b_oof=b,
            episode_start=28944,
            source_manifest_sha256="1" * 64,
            parent_profile_sha256="2" * 64,
        )


def test_full_pipeline_15_shards_1080_slots_540_initializers_and_tamper_barriers(tmp_path, monkeypatch):
    cfg, protocol_path, root, hist_cache, eval_cache = _make_synthetic_mc_parent_campaign(tmp_path)
    out = tmp_path / "out"

    # Mock fit_signed for fast 360 fits while injecting a solver failure on the very first outer fit
    call_counter = {"n": 0}

    def fast_fit_signed(x, b, y, *, relief=0.0, goal="COST", time_limit=10.0, **kwargs):
        call_counter["n"] += 1
        assert x.ndim == 2 and x.shape[1] == 24
        if call_counter["n"] == 1:
            raise RuntimeError("synthetic solver failure on first OOF fit")
        w = np.zeros(25, dtype=np.float64)
        w[0] = 0.6
        w[1] = 0.25
        w[2] = 0.15
        u = float(np.maximum(y - b, 0.0).mean())
        c = float((b + 10.0 * np.maximum(y - b, 0.0)).mean() / 6.0)
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
            raw_actual_affine_feasible=True,
            actual_affine_feasible=True,
            repaired_to_anchor=False,
            repair_alpha=0.0,
            boundary_guard_count=0,
            max_boundary_violation=0.0,
            relief=float(relief),
            goal=str(goal),
            time_limit=float(time_limit),
            support_smoothing=0.0,
        )

    monkeypatch.setattr(runner, "fit_signed", fast_fit_signed)

    # Guard evaluation cache and parent evaluate stream during history stage
    eval_cache_resolved = eval_cache.resolve()
    eval_streams_resolved = (Path(cfg["parent_results"]) / "streams" / "evaluate").resolve()
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

    # 1. Early freeze or evaluate before history -> rejected
    with pytest.raises(ValueError, match="Missing history shard receipt"):
        runner.run_freeze_stage(cfg, tmp_path / "early_fz", protocol_path=protocol_path, root=root)
    with pytest.raises(ValueError, match="FINAL_FREEZE.json"):
        runner.run_evaluate_shard(cfg, tmp_path / "early_ev", 0, protocol_path=protocol_path, root=root)

    # 2. Run all 15 history shards with evaluation guard active
    monkeypatch.setattr(np, "load", guarded_load)
    for shard in range(15):
        rec = runner.run_history_shard(cfg, out, shard, protocol_path=protocol_path, root=root)
        assert rec["initializers_prepared"] == 36
        assert rec["initializers_numerical_fitted"] == 24
        assert rec["initializers_anchor_declared"] == 12
        assert rec["new_models_fitted"] == 0
        assert rec["evaluation_cache_read"] is False
    monkeypatch.setattr(np, "load", real_np_load)
    assert call_counter["n"] == 360

    # Verify inner initializer is NO_PRIOR_OOF_ANCHOR with e0=[1, 0..0] (25 weights), and fallback outer is e0
    inner_init = json.loads(
        (out / runner.initializer_relpath("inner", "C", 201, "COST", 0.0)).read_text(encoding="utf-8")
    )
    assert inner_init["status"] == "NO_PRIOR_OOF_ANCHOR"
    assert inner_init["numerical_fitted"] is False
    assert inner_init["weights"] == [1.0] + [0.0] * 24

    outer_fb = json.loads(
        (out / runner.initializer_relpath("outer", "C", 201, "COST", 0.0)).read_text(encoding="utf-8")
    )
    assert outer_fb["status"] == "INITIALIZER_ERROR_DECLARED_ANCHOR_FALLBACK"
    assert outer_fb["numerical_fitted"] is True
    assert outer_fb["weights"] == [1.0] + [0.0] * 24

    # 3. Freeze stage: 540 initializers (360 numerical + 180 anchor), exclusive write
    freeze = runner.run_freeze_stage(cfg, out, protocol_path=protocol_path, root=root)
    assert len(freeze["all_initializers"]) == 540
    assert freeze["numerical_fits"] == 360
    assert freeze["anchor_declarations"] == 180
    assert len(freeze["all_streams"]) == 30

    before_freeze_bytes = (out / "FINAL_FREEZE.json").read_bytes()
    with pytest.raises(FileExistsError):
        runner.run_freeze_stage(cfg, out, protocol_path=protocol_path, root=root)
    assert (out / "FINAL_FREEZE.json").read_bytes() == before_freeze_bytes

    # 4. Tamper evaluate initializer or parent stream bank after freeze -> rejected by evaluate shard
    init_e_path = out / runner.initializer_relpath("evaluate", "C", 201, "COST", 0.0)
    orig_init_bytes = init_e_path.read_bytes()
    try:
        init_e_path.write_bytes(orig_init_bytes + b" ")
        with pytest.raises(ValueError, match="Initializer missing or modified since freeze"):
            runner.run_evaluate_shard(cfg, out, 0, protocol_path=protocol_path, root=root)
    finally:
        init_e_path.write_bytes(orig_init_bytes)
        shutil.rmtree(out / "shards" / "evaluate" / "shard_00_C_seed201")

    parent_inner_npz = Path(cfg["parent_results"]) / runner.stream_relpath("inner", "C", 201)
    orig_bank_bytes = parent_inner_npz.read_bytes()
    try:
        parent_inner_npz.write_bytes(orig_bank_bytes + b"corrupt")
        with pytest.raises(ValueError, match="SHA-256 mismatch"):
            runner.run_evaluate_shard(cfg, out, 0, protocol_path=protocol_path, root=root)
    finally:
        parent_inner_npz.write_bytes(orig_bank_bytes)
        shutil.rmtree(out / "shards" / "evaluate" / "shard_00_C_seed201")

    # 5. Inject single online recipe failure on shard 0 evaluate (d=1.0, CAP, ONLINE -> recipe 23)
    real_run_signed = runner.run_signed

    def faulty_run_signed(x, b, y, m, a, configs, w0, *, relief=0.0, **kwargs):
        if float(relief) == 1.0 and np.isclose(b[0, 0], 5.0) and any(c.eta > 0 for c in configs):
            raise FloatingPointError("synthetic online failure on MP023")
        return real_run_signed(x, b, y, m, a, configs, w0, relief=relief, **kwargs)

    monkeypatch.setattr(runner, "run_signed", faulty_run_signed)
    runner.run_evaluate_shard(cfg, out, 0, protocol_path=protocol_path, root=root)
    monkeypatch.setattr(runner, "run_signed", real_run_signed)
    for shard in range(1, 15):
        runner.run_evaluate_shard(cfg, out, shard, protocol_path=protocol_path, root=root)

    # Inspect shard 0 evaluate receipt: MP021 and MP023 (d=1.0 ONLINE) failed -> NaN preserved, MP022 (FIXED) completed
    r0_eval = json.loads((out / "instances/evaluate/C_seed201/receipt.json").read_text(encoding="utf-8"))
    d0_eval = np.load(out / "instances/evaluate/C_seed201/daily.npz")
    assert d0_eval["ledger"].shape == (24, 35, 4)
    assert r0_eval["status"]["23"] == "FAILED_PRESERVED"
    assert np.isnan(d0_eval["ledger"][23]).all()
    assert r0_eval["status"]["22"] == "COMPLETED"
    assert np.isfinite(d0_eval["ledger"][22]).all()

    # 6. Aggregate stage: 1080 total slots, 540 weights JSON saved, 968+72=1040 policies, 3639+468=4107 comparisons
    completion = runner.run_aggregate_stage(cfg, out, protocol_path=protocol_path, root=root, n_boot_override=4)
    assert completion["status"] == "COMPLETED_WITH_PRESERVED_FAILURES"
    assert completion["planned_recipes"] == 24
    assert completion["planned_instances_per_phase"] == 360
    assert completion["total_planned_instances"] == 1080
    assert completion["complete_per_phase"]["inner"] == 360
    assert completion["complete_per_phase"]["outer"] == 360
    assert completion["complete_per_phase"]["evaluate"] == 358
    assert completion["failed_per_phase"]["evaluate"] == 2
    assert completion["total_initializers"] == 540
    assert completion["numerical_fits"] == 360
    assert completion["anchor_declarations"] == 180
    assert completion["new_models_fitted"] == 0

    weights_json = json.loads((out / "all_initializer_weights.json").read_text(encoding="utf-8"))
    assert len(weights_json) == 540

    all_names = json.loads((out / "all_policy_names.json").read_text(encoding="utf-8"))
    assert all_names["parent_policy_count"] == 968
    assert all_names["new_policy_count"] == 72
    assert len(all_names["names"]) == 1040
    assert all_names["parent_comparison_count"] == 3639
    assert all_names["total_comparison_count"] == 4107
    assert all_names["nominal_family_size"] == 11 * 1040 + 10 * 4107
    assert all_names["available"][-3:] == [False, True, True]

    for span in (3, 1, 7):
        assert (out / f"inference_span{span}.json").exists()
