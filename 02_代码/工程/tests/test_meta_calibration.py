import json
import os
from dataclasses import asdict
from repo_paths import Path, repository_root
import shutil

import numpy as np
import pytest

import scripts.run_meta_calibration as runner
from scripts.run_mixture_closed_loop import save, score_actions, sha
from scripts.run_residual_meta import build_extended_family as build_meta_parent_family
from windfarm_moe.delayed_calibration_baselines import (
    DelayedCalibrationConfig,
    run_delayed_calibration,
)
from windfarm_moe.meta_action_stream import prefix_sha256
from windfarm_moe.residual_meta import META_ARMS, build_meta_recipes


def _make_synthetic_parent_campaign(tmp_path: Path):
    """Build synthetic parent Meta campaign (680 policies, 2199 comparisons) and fast fake phase banks."""
    parent_dir = tmp_path / "parent_meta_campaign"
    parent_dir.mkdir(parents=True, exist_ok=True)

    # Inner: 28087..28096 (10 steps)
    # Outer: 28944..28953 (10 steps) -> gap = 28944 - 28096 = 848 > 7
    # Evaluate: 35 days (day 210..244), first day has 8 steps (30240..30247), days 211..244 have 1 step each -> 42 steps
    ha_inner = np.arange(28087, 28097, dtype=np.int64)
    ha_outer = np.arange(28944, 28954, dtype=np.int64)
    ea_day0 = 210 * 144 + np.arange(8, dtype=np.int64)
    ea_rest = np.arange(211, 245, dtype=np.int64) * 144 + 10
    ea = np.concatenate([ea_day0, ea_rest])

    phase_grids = {
        "inner": ha_inner,
        "outer": ha_outer,
        "evaluate": ea,
    }

    # Base 608-policy / 1911-comparison fixture extended to 680 policies / 2199 comparisons via build_meta_parent_family
    base_names = ["REF"]
    for i in range(1, 608):
        if i == 365:
            base_names.append("R0182_P")
        elif i == 373:
            base_names.append("R0186_P")
        elif i == 374:
            base_names.append("R0186_Z")
        elif i == 412:
            base_names.append("GUARDED_FIXED_P")
        elif i == 413:
            base_names.append("GUARDED_FIXED_Z")
        else:
            base_names.append(f"PARENT_{i:04d}")
    base_comps = []
    seen = set()
    for idx in range(1, 608):
        base_comps.append([idx, 0])
        seen.add((idx, 0))
    step = 1
    while len(base_comps) < 1911:
        for idx in range(1, 608):
            right = ((idx + step - 1) % 607) + 1
            if right != idx and (idx, right) not in seen:
                base_comps.append([idx, right])
                seen.add((idx, right))
                if len(base_comps) == 1911:
                    break
        step += 1

    base_span3 = dict(
        schema="autonomous-campaign-inference-v1",
        policy_names=base_names,
        available=[True] * 608,
        family_definition=dict(
            policy_names=base_names,
            comparisons=base_comps,
            frozen_aliases=[[2, 1]],
        ),
    )
    meta_recipes = build_meta_recipes()
    parent_names, parent_avail_base, parent_aliases, parent_comps = build_meta_parent_family(
        base_span3,
        meta_recipes,
        expected_parent_policies=608,
        expected_parent_comparisons=1911,
    )
    parent_avail = parent_avail_base + [True] * 72
    assert len(parent_names) == 680
    assert len(parent_comps) == 2199

    bank_store: dict[tuple[str, int, str], dict] = {}
    parent_ledger = np.ones((5, 680, 35, 4), dtype=np.float64)
    eval_counts = None
    eval_days = None

    for si, seed in enumerate(runner.SEEDS):
        for phase, anchors in phase_grids.items():
            t_steps = len(anchors)
            n_nodes = 2
            rng_t = np.random.default_rng(10000 + seed * 10 + len(phase))
            shortfall = rng_t.uniform(4.0, 12.0, (t_steps, n_nodes)).astype(np.float64)
            mask = np.ones((t_steps, n_nodes), dtype=bool)
            mask[1, 1] = False
            shortfall[1, 1] = np.nan
            reference = np.full((t_steps, n_nodes), 5.0 + 0.1 * si, dtype=np.float64)
            ref_led, counts, days = score_actions(reference, shortfall, mask, anchors)
            if phase == "evaluate":
                parent_ledger[si, :608] = ref_led[None, :, :]
                eval_counts = counts
                eval_days = days

            for ai, arm in enumerate(META_ARMS):
                raw_actions = np.empty((24, t_steps, n_nodes), dtype=np.float64)
                raw_shas = {}
                model_shas = {}
                rcpt_shas = {}
                ledgers = np.empty((24, len(days), 4), dtype=np.float64)
                status = {}
                for rid in range(24):
                    act = reference + 0.15 * rid + 0.05 * ai
                    raw_actions[rid] = act
                    raw_shas[str(rid)] = prefix_sha256(act)
                    model_shas[str(rid)] = f"{rid:02d}" + "a" * 62
                    rcpt_shas[str(rid)] = f"{rid:02d}" + "b" * 62
                    led, _, _ = score_actions(act, shortfall, mask, anchors)
                    ledgers[rid] = led
                    status[str(rid)] = "COMPLETED"
                    if phase == "evaluate":
                        mr_idx = 608 + 3 * rid + ai
                        parent_ledger[si, mr_idx] = led

                inst_dir = parent_dir / "instances" / phase / f"{arm}_seed{seed}"
                inst_dir.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(
                    inst_dir / "daily.npz",
                    ledger=ledgers,
                    reference=ref_led,
                    counts=counts,
                    days=days,
                )
                save(
                    inst_dir / "receipt.json",
                    dict(
                        phase=phase,
                        seed=seed,
                        arm=arm,
                        ids=list(range(24)),
                        status=status,
                        action_sha256=raw_shas,
                        source_manifest_sha256="1" * 64 if phase != "evaluate" else "2" * 64,
                        parent_profile_sha256=f"{seed}" + "c" * 61,
                        complete_expected=24,
                        completed=24,
                    ),
                )

                for arr in (anchors, shortfall, mask, reference, raw_actions):
                    arr.flags.writeable = False
                bank_store[(phase, seed, arm)] = dict(
                    anchors=anchors,
                    shortfall=shortfall,
                    mask=mask,
                    reference=reference,
                    raw_actions=raw_actions,
                    metadata=dict(
                        schema="meta-action-stream-bank-v1",
                        phase=phase,
                        phases=[phase],
                        seed=seed,
                        arm=arm,
                        n_recipes=24,
                        n_steps=t_steps,
                        n_turbines=n_nodes,
                        valid_cells=int(mask.sum()),
                        anchor_start=int(anchors[0]),
                        anchor_end=int(anchors[-1]),
                        clock_rule="source_anchor+7<decision_anchor",
                        parent_results=str(parent_dir),
                        protocol_sha256="3" * 64,
                        freeze_sha256="4" * 64,
                        source_manifest_sha256="1" * 64 if phase != "evaluate" else "2" * 64,
                        historical_manifest_sha256="1" * 64,
                        parent_profile_sha256=f"{seed}" + "c" * 61,
                        source_hashes={"dummy_source.py": "5" * 64},
                        model_sha256=model_shas,
                        model_receipt_sha256=rcpt_shas,
                        raw_action_sha256=raw_shas,
                        raw_actions_sha256=prefix_sha256(raw_actions),
                        reference_sha256=prefix_sha256(reference),
                        independent_confirmation=False,
                    ),
                )

    np.savez_compressed(
        parent_dir / "all_daily_ledger.npz",
        ledger=parent_ledger,
        counts=eval_counts,
        day_ids=eval_days,
    )
    parent_span3 = dict(
        schema="autonomous-campaign-inference-v1",
        policy_names=parent_names,
        available=parent_avail,
        family_definition=dict(
            policy_names=parent_names,
            comparisons=[list(p) for p in parent_comps],
            frozen_aliases=[list(p) for p in parent_aliases],
        ),
    )
    save(parent_dir / "inference_span3.json", parent_span3)
    save(parent_dir / "FINAL_FREEZE.json", dict(study_id="residual_meta_20261024_v1", recipes=meta_recipes))

    src_file = tmp_path / "dummy_source.py"
    src_file.write_text("# synthetic meta calibration source\n", encoding="utf-8")

    ea = phase_grids["evaluate"]
    em = bank_store[("evaluate", 201, "C")]["mask"]
    cfg = dict(
        study_id="meta_calibration_synthetic_test",
        max_candidates=96,
        max_cpu_seconds=28800,
        history_wall_seconds=600,
        evaluation_wall_seconds=900,
        freeze_wall_seconds=60,
        aggregate_wall_seconds=1800,
        independent_audit_wall_seconds=600,
        local_retry_reserve_seconds=3840,
        maximum_science_parallel_jobs=15,
        budget_reservation=dict(
            new_candidates=96,
            cpu_seconds=28800,
            total_reserved_candidates=1478,
            total_accounted_plus_open_reservations_cpu=61287,
            global_cpu_limit_unchanged=86400,
        ),
        expected_historical_grid=False,
        expected_evaluation_anchors=len(ea),
        expected_evaluation_valid_cells=int(em.sum()),
        expected_parent_policies=680,
        expected_parent_comparisons=2199,
        parent_results=str(parent_dir),
        parent_freeze_sha256=sha(parent_dir / "FINAL_FREEZE.json"),
        parent_ledger_sha256=sha(parent_dir / "all_daily_ledger.npz"),
        parent_span3_sha256=sha(parent_dir / "inference_span3.json"),
        recipes=runner.build_calibration_recipes(),
        source_hashes={"dummy_source.py": sha(src_file)},
        inference=dict(spans=[3, 1, 7], n_boot=4, seed=20261022),
    )
    protocol_path = tmp_path / "protocol.json"
    save(protocol_path, cfg)
    return cfg, protocol_path, tmp_path, bank_store


def test_96_recipe_grid_and_4_calibration_modes_exact_full_defaults():
    recipes = runner.build_calibration_recipes()
    assert len(recipes) == 96
    assert [r["id"] for r in recipes] == list(range(96))

    c0 = asdict(DelayedCalibrationConfig())
    c1 = asdict(DelayedCalibrationConfig(method="tracker", target_event_rate=0.05, step_size=0.03))
    c2 = asdict(DelayedCalibrationConfig(method="tracker", target_event_rate=0.05, step_size=0.10))
    c3 = asdict(DelayedCalibrationConfig(method="aci", window_steps=1008, target_event_rate=0.05, gamma=0.0003))

    for base_id in range(24):
        for cal_id, exp_mode, exp_cfg in [
            (0, "NONE", c0),
            (1, "TRACKER_003", c1),
            (2, "TRACKER_010", c2),
            (3, "ACI_1008", c3),
        ]:
            rid = 4 * base_id + cal_id
            rec = recipes[rid]
            assert rec["id"] == rid
            assert rec["base_meta_id"] == base_id
            assert rec["calibration_id"] == cal_id
            assert rec["calibration_mode"] == exp_mode
            assert rec["calibration_config"] == exp_cfg
            # Verify full DelayedCalibrationConfig defaults are explicitly saved
            assert set(rec["calibration_config"].keys()) == {
                "method",
                "fixed_shift",
                "initial_shift",
                "step_size",
                "target_event_rate",
                "window_steps",
                "quantile",
                "gamma",
                "initial_alpha",
            }


def test_real_calibration_prefix_invariance_cold_start_and_7_step_gap():
    """Verify real run_delayed_calibration across inner+outer+evaluate with 7-step gaps and future label invariance."""
    ha_inner = np.arange(28087, 28102, dtype=np.int64)  # 15 steps
    ha_outer = np.arange(28944, 28959, dtype=np.int64)  # 15 steps (gap = 28944 - 28101 = 843 > 7)
    ea = np.arange(30240, 30255, dtype=np.int64)        # 15 steps (gap = 30240 - 28958 = 1282 > 7)

    a_hist = np.concatenate([ha_inner, ha_outer])
    a_full = np.concatenate([a_hist, ea])
    rng = np.random.default_rng(20261025)
    raw_full = rng.uniform(3.0, 9.0, (len(a_full), 3))
    y_full = rng.uniform(1.0, 15.0, (len(a_full), 3))
    m_full = np.ones((len(a_full), 3), dtype=bool)
    m_full[4, 1] = False
    m_full[18, 2] = False
    m_full[33, 0] = False
    y_full[4, 1] = np.nan
    y_full[18, 2] = np.nan
    y_full[33, 0] = np.nan

    recipes = runner.build_calibration_recipes()[:4]  # base_meta_id=0, cal_id=0..3
    for rec in recipes:
        act_hist, _, _ = runner._calibrate_single_recipe_stream(
            rec,
            raw_full[: len(a_hist)],
            y_full[: len(a_hist)],
            m_full[: len(a_hist)],
            a_hist,
        )
        # Mutate outer labels & masks: inner slice [:15] must be bitwise identical
        y_hist_mod = y_full[: len(a_hist)].copy()
        y_hist_mod[len(ha_inner) :] += 500.0
        m_hist_mod = m_full[: len(a_hist)].copy()
        m_hist_mod[len(ha_inner) :] = False
        act_hist_mod, _, _ = runner._calibrate_single_recipe_stream(
            rec,
            raw_full[: len(a_hist)],
            y_hist_mod,
            m_hist_mod,
            a_hist,
        )
        np.testing.assert_array_equal(act_hist[: len(ha_inner)], act_hist_mod[: len(ha_inner)])

        # Arbitrary invalid masked target values (-777.0, +inf, NaN) do not alter prefix or control scores
        for invalid_masked in (-777.0, np.inf, np.nan):
            y_masked_alt = y_full.copy()
            y_masked_alt[~m_full] = invalid_masked
            act_masked_alt, _, _ = runner._calibrate_single_recipe_stream(
                rec, raw_full, y_masked_alt, m_full, a_full
            )
            np.testing.assert_array_equal(act_masked_alt, runner._calibrate_single_recipe_stream(rec, raw_full, y_full, m_full, a_full)[0])
            assert prefix_sha256(act_masked_alt[: len(a_hist)]) == prefix_sha256(act_hist)
            led_orig, _, _ = score_actions(act_hist, y_full[: len(a_hist)], m_full[: len(a_hist)], a_hist)
            led_alt, _, _ = score_actions(act_masked_alt[: len(a_hist)], y_masked_alt[: len(a_hist)], m_full[: len(a_hist)], a_hist)
            np.testing.assert_array_equal(led_alt, led_orig)

        # First 8 inner steps must equal uncalibrated raw actions (cold start, no initial_residuals)
        np.testing.assert_array_equal(act_hist[:8], raw_full[:8])

        # Combined history + evaluate stream: history prefix must be bitwise identical to frozen history actions
        y_full_mod = y_full.copy()
        y_full_mod[len(a_hist) :] += 999.0
        act_combined, _, _ = runner._calibrate_single_recipe_stream(
            rec, raw_full, y_full_mod, m_full, a_full
        )
        assert prefix_sha256(act_combined[: len(a_hist)]) == prefix_sha256(act_hist)


def test_full_distributed_pipeline_15_shards_4320_instances_288_roles_1440_comps_and_barriers(tmp_path, monkeypatch):
    cfg, protocol_path, root, bank_store = _make_synthetic_parent_campaign(tmp_path)
    out = tmp_path / "out"

    eval_Read_called = {"called": False}

    def fake_build_phase_bank(parent_results, phase, seed, arm, *, root=None):
        if phase == "evaluate":
            eval_Read_called["called"] = True
        return bank_store[(str(phase), int(seed), str(arm))]

    monkeypatch.setattr(runner, "build_phase_bank", fake_build_phase_bank)

    # 1. Freeze before history -> rejected
    with pytest.raises(ValueError, match="Missing history shard receipt"):
        runner.run_freeze_stage(cfg, tmp_path / "out_early_freeze", protocol_path=protocol_path, root=root)

    # 2. Evaluate before freeze -> rejected
    with pytest.raises(ValueError, match="FINAL_FREEZE.json"):
        runner.run_evaluate_shard(cfg, tmp_path / "out_early_eval", 0, protocol_path=protocol_path, root=root)

    # 3. Run all 15 history shards; verify evaluate bank is never built during history
    for shard in range(15):
        rec = runner.run_history_shard(cfg, out, shard, protocol_path=protocol_path, root=root)
        assert rec["recipes_completed"] == 96
        assert rec["new_models_fitted"] == 0
        assert rec["evaluation_cache_read"] is False
        assert rec["scientific_qualification_used_to_filter"] is False
    assert eval_Read_called["called"] is False

    # 4. Raw NONE control mismatch detection: if parent receipt action_sha256 is tampered, history shard rejects it
    parent_inner_rcpt = Path(cfg["parent_results"]) / "instances/inner/C_seed201/receipt.json"
    orig_parent_rcpt_bytes = parent_inner_rcpt.read_bytes()
    tampered_rcpt = json.loads(orig_parent_rcpt_bytes.decode("utf-8"))
    tampered_rcpt["action_sha256"]["0"] = "f" * 64
    save(parent_inner_rcpt, tampered_rcpt)
    try:
        out_bad_none = tmp_path / "out_bad_none"
        runner.run_history_shard(cfg, out_bad_none, 0, protocol_path=protocol_path, root=root)
        bad_inst_rcpt = json.loads((out_bad_none / "instances/inner/C_seed201/receipt.json").read_text(encoding="utf-8"))
        assert bad_inst_rcpt["status"]["0"] == "FAILED_PRESERVED"
        assert "Raw NONE control action SHA-256 mismatch" in bad_inst_rcpt["errors"]["0"]["error"]
    finally:
        parent_inner_rcpt.write_bytes(orig_parent_rcpt_bytes)

    # 5. Tampered stream bank on disk BEFORE freeze is caught
    s0_npz = out / runner.stream_relpath("inner", "C", 201)
    orig_s0_bytes = s0_npz.read_bytes()
    try:
        s0_npz.write_bytes(orig_s0_bytes + b"corrupt")
        with pytest.raises(ValueError, match="Stream bank SHA-256 mismatch"):
            runner.run_freeze_stage(cfg, out, protocol_path=protocol_path, root=root)
    finally:
        s0_npz.write_bytes(orig_s0_bytes)
        for f_rm in (out / "shards/freeze/failure.json", out / "shards/freeze/state.json"):
            if f_rm.exists():
                f_rm.unlink()

    # 6. Run clean freeze stage
    freeze = runner.run_freeze_stage(cfg, out, protocol_path=protocol_path, root=root)
    assert len(freeze["all_streams"]) == 30
    assert len(freeze["all_history_policy_shas"]) == 15
    assert len(freeze["all_instance_receipts"]) == 30
    outer_sel = json.loads((out / "outer_selection.json").read_text(encoding="utf-8"))
    assert outer_sel["qualification_did_not_filter_instances"] is True
    assert set(outer_sel["roles"].keys()) == {"C", "P", "Z"}
    for arm in ("C", "P", "Z"):
        assert 0 <= outer_sel["roles"][arm]["minimum_C_id"] < 96
        assert 0 <= outer_sel["roles"][arm]["minimum_maxV_id"] < 96

    # 7. Second freeze attempt must fail BEFORE ANY write
    freeze_files = [
        out / "FINAL_FREEZE.json",
        out / "EVALUATION_OPEN.json",
        out / "shards" / "freeze" / "state.json",
        out / "protocol_original.json",
        out / "protocol.json",
        out / "source_versions.json",
    ]
    before_bytes = {p: p.read_bytes() for p in freeze_files}
    with pytest.raises(FileExistsError):
        runner.run_freeze_stage(cfg, out, protocol_path=protocol_path, root=root)
    for p, raw in before_bytes.items():
        assert p.read_bytes() == raw
    assert not (out / "shards" / "freeze" / "failure.json").exists()

    # 8. Inject single-recipe failure on shard 0 evaluate for recipe 95 (ACI_1008 on M023) to verify failure isolation
    real_calibrate = runner._calibrate_single_recipe_stream

    def faulty_calibrate(recipe, raw_stream, shortfall, mask, anchors):
        if int(recipe["id"]) == 95:
            raise FloatingPointError("synthetic calibration failure on MC095")
        return real_calibrate(recipe, raw_stream, shortfall, mask, anchors)

    monkeypatch.setattr(runner, "_calibrate_single_recipe_stream", faulty_calibrate)
    runner.run_evaluate_shard(cfg, out, 0, protocol_path=protocol_path, root=root)
    monkeypatch.setattr(runner, "_calibrate_single_recipe_stream", real_calibrate)

    for shard in range(1, 15):
        runner.run_evaluate_shard(cfg, out, shard, protocol_path=protocol_path, root=root)

    # Verify saved stream NPZ files across inner, outer, and evaluate preserve masked NaN target/mask bytes and 24 raw SHAs
    for phase_check in ("inner", "outer", "evaluate"):
        s_npz = np.load(out / runner.stream_relpath(phase_check, "C", 201))
        orig_bank = bank_store[(phase_check, 201, "C")]
        assert s_npz["shortfall"].tobytes() == orig_bank["shortfall"].tobytes()
        assert s_npz["mask"].tobytes() == orig_bank["mask"].tobytes()
        assert np.isnan(s_npz["shortfall"][1, 1]) and not s_npz["mask"][1, 1]
        s_meta = json.loads((out / runner.stream_metadata_relpath(phase_check, "C", 201)).read_text(encoding="utf-8"))
        assert s_meta["raw_action_sha256"] == orig_bank["metadata"]["raw_action_sha256"]

    r0_eval = json.loads((out / "instances/evaluate/C_seed201/receipt.json").read_text(encoding="utf-8"))
    d0_eval = np.load(out / "instances/evaluate/C_seed201/daily.npz")
    assert d0_eval["ledger"].shape == (96, 35, 4)
    assert r0_eval["status"]["95"] == "FAILED_PRESERVED"
    assert np.isnan(d0_eval["ledger"][95]).all()
    assert r0_eval["status"]["0"] == "COMPLETED"
    assert np.isfinite(d0_eval["ledger"][0]).all()

    # Verify full 96-recipe checkpoint JSONL files in history and evaluate shards
    hist_ckpt_lines = [
        json.loads(line)
        for line in (out / "shards/history/shard_00_C_seed201/recipe_checkpoints.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(hist_ckpt_lines) == 97
    assert hist_ckpt_lines[0]["record_type"] == "HEADER"
    assert hist_ckpt_lines[0]["stage"] == "history"
    assert hist_ckpt_lines[0]["protocol_sha256"] == sha(protocol_path)
    assert "source_versions" in hist_ckpt_lines[0] and "source_commit" in hist_ckpt_lines[0]
    assert [r["id"] for r in hist_ckpt_lines[1:]] == list(range(96))
    assert all(r["success"] is True and r["final_none_control_validated"] is False for r in hist_ckpt_lines[1:])

    eval_ckpt_lines = [
        json.loads(line)
        for line in (out / "shards/evaluate/shard_00_C_seed201/recipe_checkpoints.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(eval_ckpt_lines) == 97
    assert eval_ckpt_lines[0]["record_type"] == "HEADER"
    assert eval_ckpt_lines[0]["stage"] == "evaluate"
    assert [r["id"] for r in eval_ckpt_lines[1:]] == list(range(96))
    assert all(r["success"] is True for r in eval_ckpt_lines[1:96])
    assert eval_ckpt_lines[96]["id"] == 95
    assert eval_ckpt_lines[96]["success"] is False
    assert "synthetic calibration failure on MC095" in eval_ckpt_lines[96]["error"]
    assert eval_ckpt_lines[1]["action_sha256"] == r0_eval["action_sha256"]["0"]
    np.testing.assert_allclose(eval_ckpt_lines[1]["evaluate"]["means_CRUV"], r0_eval["metrics"]["0"])

    # 9. Retroactive history prefix tampering or bank tampering in evaluate is rejected
    out_tamper_eval = tmp_path / "out_tamper_eval"
    shutil.copytree(out / "streams/inner", out_tamper_eval / "streams/inner")
    shutil.copytree(out / "streams/outer", out_tamper_eval / "streams/outer")
    shutil.copytree(out / "instances/inner", out_tamper_eval / "instances/inner")
    shutil.copytree(out / "instances/outer", out_tamper_eval / "instances/outer")
    shutil.copyfile(out / "FINAL_FREEZE.json", out_tamper_eval / "FINAL_FREEZE.json")
    shutil.copyfile(out / "EVALUATION_OPEN.json", out_tamper_eval / "EVALUATION_OPEN.json")
    shutil.copyfile(out / "protocol_original.json", out_tamper_eval / "protocol_original.json")

    # Tamper frozen history policy sha in FINAL_FREEZE.json (and update EVALUATION_OPEN.json) -> evaluate recipe fails prefix check
    fz_mod = json.loads((out_tamper_eval / "FINAL_FREEZE.json").read_text(encoding="utf-8"))
    fz_mod["all_history_policy_shas"]["P_seed201"]["1"] = "0" * 64
    save(out_tamper_eval / "FINAL_FREEZE.json", fz_mod)
    save(
        out_tamper_eval / "EVALUATION_OPEN.json",
        dict(freeze_sha256=sha(out_tamper_eval / "FINAL_FREEZE.json"), protocol_sha256=fz_mod["protocol_sha256"]),
    )
    runner.run_evaluate_shard(cfg, out_tamper_eval, 1, protocol_path=protocol_path, root=root)
    r1_tampered = json.loads((out_tamper_eval / "instances/evaluate/P_seed201/receipt.json").read_text(encoding="utf-8"))
    assert r1_tampered["status"]["1"] == "FAILED_PRESERVED"
    assert "History prefix SHA-256 mismatch" in r1_tampered["errors"]["1"]["error"]

    # Tamper historical stream bank bytes on disk after freeze -> evaluate shard raises ValueError immediately
    target_npz = out_tamper_eval / runner.stream_relpath("inner", "Z", 201)
    target_npz.write_bytes(target_npz.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        runner.run_evaluate_shard(cfg, out_tamper_eval, 2, protocol_path=protocol_path, root=root)

    # 10. Aggregate stage: verify 680 + 288 = 968 policies, 2199 + 1440 = 3639 comparisons, 47038 coords, 72 NONE aliases
    completion = runner.run_aggregate_stage(cfg, out, protocol_path=protocol_path, root=root, n_boot_override=4)
    assert completion["status"] == "COMPLETED_WITH_PRESERVED_FAILURES"
    assert completion["planned_recipes"] == 96
    assert completion["planned_instances_per_phase"] == 1440
    assert completion["total_planned_instances"] == 4320
    assert completion["complete_per_phase"]["inner"] == 1440
    assert completion["complete_per_phase"]["outer"] == 1440
    assert completion["complete_per_phase"]["evaluate"] == 1439
    assert completion["failed_per_phase"]["evaluate"] == 1
    assert completion["new_models_fitted"] == 0
    assert completion["scientific_qualification_used_to_filter"] is False
    assert completion["thresholds_changed"] is False

    all_names = json.loads((out / "all_policy_names.json").read_text(encoding="utf-8"))
    assert all_names["parent_policy_count"] == 680
    assert all_names["new_policy_count"] == 288
    assert len(all_names["names"]) == 968
    assert all_names["parent_comparison_count"] == 2199
    assert all_names["total_comparison_count"] == 3639
    assert all_names["nominal_family_size"] == 47038
    assert len(all_names["new_none_aliases"]) == 72
    assert all_names["new_none_aliases"][0] == ["MC000_C", "MR000_C"]
    assert all_names["new_none_aliases"][-1] == ["MC092_Z", "MR023_Z"]
    assert all_names["names"][680:683] == ["MC000_C", "MC000_P", "MC000_Z"]
    assert all_names["names"][-3:] == ["MC095_C", "MC095_P", "MC095_Z"]
    assert all_names["available"][-3:] == [False, True, True]

    # Verify parent ledger slices are retained verbatim and all 72 NONE aliases match MR base arm bitwise
    parent_npz = np.load(Path(cfg["parent_results"]) / "all_daily_ledger.npz")
    child_npz = np.load(out / "all_daily_ledger.npz")
    np.testing.assert_array_equal(child_npz["ledger"][:, :680], parent_npz["ledger"])
    name_idx = {n: i for i, n in enumerate(all_names["names"])}
    for mc_name, mr_name in all_names["new_none_aliases"]:
        np.testing.assert_array_equal(child_npz["ledger"][:, name_idx[mc_name]], child_npz["ledger"][:, name_idx[mr_name]])

    for span in (3, 1, 7):
        assert (out / f"inference_span{span}.json").exists()

    # 11. Tampered NONE control ledger in evaluate daily.npz -> aggregate rejects before infer_campaign
    eval_c0_path = out / "instances/evaluate/C_seed201/daily.npz"
    orig_eval_c0 = eval_c0_path.read_bytes()
    d_c0 = np.load(eval_c0_path)
    led_mod = d_c0["ledger"].copy()
    led_mod[0, 0, 0] += 0.125  # Mutate MC000_C (NONE control)
    np.savez_compressed(eval_c0_path, ledger=led_mod, reference=d_c0["reference"], counts=d_c0["counts"], days=d_c0["days"])
    try:
        with pytest.raises(ValueError, match="NONE control alias MC000_C -> MR000_C does not have bitwise identical"):
            runner.run_aggregate_stage(cfg, out, protocol_path=protocol_path, root=root, n_boot_override=4)
    finally:
        eval_c0_path.write_bytes(orig_eval_c0)


    # 12. Per-recipe durable checkpoint preserves progress on deadline interrupt, final write failure, and zero counts
    zero_act = np.zeros((4, 2), dtype=np.float64)
    zero_sf = np.ones((4, 2), dtype=np.float64)
    zero_mask = np.zeros((4, 2), dtype=bool)
    zero_anchors = np.arange(28087, 28091, dtype=np.int64)
    z_metrics = runner._checkpoint_phase_metrics(zero_act, zero_sf, zero_mask, zero_anchors)
    assert z_metrics["shared_count"] == 0
    assert z_metrics["means_CRUV"] == [None, None, None, None]
    assert z_metrics["means"] == {"C": None, "R": None, "U": None, "V": None}
    assert z_metrics["totals_CRUV"] == [0.0, 0.0, 0.0, 0.0]

    dup_ckpt = tmp_path / "dup.jsonl"
    runner._init_checkpoint_jsonl(dup_ckpt, {"record_type": "HEADER"})
    with pytest.raises(FileExistsError):
        runner._init_checkpoint_jsonl(dup_ckpt, {"record_type": "HEADER"})

    out_hist_int = tmp_path / "out_hist_int"
    hist_calls = {"n": 0}

    def interrupt_after_two_history_recipes(dl):
        hist_calls["n"] += 1
        if hist_calls["n"] >= 6:
            raise TimeoutError("Hard walltime budget reached after recipe 1")

    monkeypatch.setattr(runner, "deadline_check", interrupt_after_two_history_recipes)
    with pytest.raises(TimeoutError, match="Hard walltime budget reached after recipe 1"):
        runner.run_history_shard(cfg, out_hist_int, 0, protocol_path=protocol_path, root=root)

    hist_shard_dir = out_hist_int / "shards/history/shard_00_C_seed201"
    assert (hist_shard_dir / "failure.json").exists()
    hist_state = json.loads((hist_shard_dir / "state.json").read_text(encoding="utf-8"))
    assert hist_state["status"] == "FAILED_PRESERVED"
    assert not (out_hist_int / "instances/inner/C_seed201/receipt.json").exists()
    hist_lines = [
        json.loads(line)
        for line in (hist_shard_dir / "recipe_checkpoints.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(hist_lines) == 3
    assert hist_lines[0]["record_type"] == "HEADER"
    assert hist_lines[0]["stage"] == "history"
    assert [r["id"] for r in hist_lines[1:]] == [0, 1]
    for r in hist_lines[1:]:
        assert r["success"] is True
        assert r["status"] == "ACTION_GENERATED_METRICS_COMPUTED_PENDING_POSTCHECK"
        assert r["final_none_control_validated"] is False
        assert isinstance(r["prefix_sha256"], str) and len(r["prefix_sha256"]) == 64
        assert r["inner"]["shared_count"] > 0
        assert r["outer"]["shared_count"] > 0
        assert all(isinstance(v, float) for v in r["inner"]["means_CRUV"])
        assert all(isinstance(v, float) for v in r["outer"]["means_CRUV"])

    out_eval_int = tmp_path / "out_eval_int"
    shutil.copytree(out / "streams/inner", out_eval_int / "streams/inner")
    shutil.copytree(out / "streams/outer", out_eval_int / "streams/outer")
    shutil.copytree(out / "instances/inner", out_eval_int / "instances/inner")
    shutil.copytree(out / "instances/outer", out_eval_int / "instances/outer")
    shutil.copyfile(out / "FINAL_FREEZE.json", out_eval_int / "FINAL_FREEZE.json")
    shutil.copyfile(out / "EVALUATION_OPEN.json", out_eval_int / "EVALUATION_OPEN.json")
    shutil.copyfile(out / "protocol_original.json", out_eval_int / "protocol_original.json")

    eval_calls = {"n": 0}

    def interrupt_after_two_eval_recipes(dl):
        eval_calls["n"] += 1
        if eval_calls["n"] >= 5:
            raise TimeoutError("Hard walltime budget reached on evaluate after recipe 1")

    monkeypatch.setattr(runner, "deadline_check", interrupt_after_two_eval_recipes)
    with pytest.raises(TimeoutError, match="Hard walltime budget reached on evaluate after recipe 1"):
        runner.run_evaluate_shard(cfg, out_eval_int, 0, protocol_path=protocol_path, root=root)

    eval_shard_dir = out_eval_int / "shards/evaluate/shard_00_C_seed201"
    eval_lines = [
        json.loads(line)
        for line in (eval_shard_dir / "recipe_checkpoints.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(eval_lines) == 3
    assert eval_lines[0]["record_type"] == "HEADER"
    assert eval_lines[0]["stage"] == "evaluate"
    assert [r["id"] for r in eval_lines[1:]] == [0, 1]
    for r in eval_lines[1:]:
        assert r["success"] is True
        assert r["final_none_control_validated"] is False
        assert r["evaluate"]["shared_count"] > 0
        assert len(r["action_sha256"]) == 64
        assert len(r["prefix_sha256"]) == 64

    monkeypatch.setattr(runner, "deadline_check", lambda dl: None)

    def crash_on_final_write(*args, **kwargs):
        raise OSError("Simulated disk failure during final phase instance write")

    monkeypatch.setattr(runner, "_write_phase_instance", crash_on_final_write)
    with pytest.raises(OSError, match="Simulated disk failure during final phase instance write"):
        runner.run_evaluate_shard(cfg, out_eval_int, 1, protocol_path=protocol_path, root=root)

    eval_s1_lines = [
        json.loads(line)
        for line in (out_eval_int / "shards/evaluate/shard_01_P_seed201/recipe_checkpoints.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(eval_s1_lines) == 97
    assert [r["id"] for r in eval_s1_lines[1:]] == list(range(96))
    assert all(r["success"] is True for r in eval_s1_lines[1:])


def test_budget_arithmetic_and_deadline_enforcement(tmp_path, monkeypatch):
    cfg, protocol_path, root, _ = _make_synthetic_parent_campaign(tmp_path)
    assert 15 * 600 + 15 * 900 + 60 + 1800 + 600 + 3840 == 28800
    assert len(runner.verify_budget_and_recipes(cfg)) == 96

    # V2 retry accounting: charged prior V1 CPU seconds (713) deducted from local retry reserve (3127), keeping 28800 unchanged
    v1_budget_path = Path(repository_root()) / "experiments/meta_calibration_20261025/V1_FAILURE_BUDGET.json"
    if v1_budget_path.exists():
        v1_budget = json.loads(v1_budget_path.read_text(encoding="utf-8"))
        assert v1_budget["charged_prior_cpu_seconds"] == 713
        assert v1_budget["local_reserve_remaining_after_failed_allocation"] == 3127
        assert v1_budget["original_stage_max_cpu_seconds"] == 28800
    cfg_v2 = dict(cfg, local_retry_reserve_seconds=3127, prior_accounted_cpu_seconds=713)
    assert 15 * 600 + 15 * 900 + 60 + 1800 + 600 + 3127 + 713 == 28800
    assert len(runner.verify_budget_and_recipes(cfg_v2)) == 96
    # Old v1 config (3840, prior=0 default or explicit) remains compatible
    assert len(runner.verify_budget_and_recipes(dict(cfg, prior_accounted_cpu_seconds=0))) == 96

    with pytest.raises(ValueError, match="96-candidate"):
        runner.verify_budget_and_recipes(dict(cfg, max_candidates=24))
    with pytest.raises(ValueError, match="history_wall_seconds"):
        runner.verify_budget_and_recipes(dict(cfg, history_wall_seconds=1200))
    with pytest.raises(ValueError, match="evaluation_wall_seconds"):
        runner.verify_budget_and_recipes(dict(cfg, evaluation_wall_seconds=240))
    with pytest.raises(ValueError, match="local_retry_reserve_seconds"):
        runner.verify_budget_and_recipes(dict(cfg, local_retry_reserve_seconds=4740))
    # Reject overbooking (3840 + 713 > 3840) and negative prior_accounted_cpu_seconds
    with pytest.raises(ValueError, match="local_retry_reserve_seconds \\+ prior_accounted_cpu_seconds must equal 3840"):
        runner.verify_budget_and_recipes(dict(cfg, local_retry_reserve_seconds=3840, prior_accounted_cpu_seconds=713))
    with pytest.raises(ValueError, match="local_retry_reserve_seconds \\+ prior_accounted_cpu_seconds must equal 3840"):
        runner.verify_budget_and_recipes(dict(cfg, local_retry_reserve_seconds=3200, prior_accounted_cpu_seconds=713))
    with pytest.raises(ValueError, match="prior_accounted_cpu_seconds must be nonnegative"):
        runner.verify_budget_and_recipes(dict(cfg, local_retry_reserve_seconds=3841, prior_accounted_cpu_seconds=-1))
    with pytest.raises(ValueError, match="local_retry_reserve_seconds \\+ prior_accounted_cpu_seconds must equal 3840"):
        runner.verify_budget_and_recipes(dict(cfg, local_retry_reserve_seconds=-10, prior_accounted_cpu_seconds=3850))
    with pytest.raises(ValueError, match="budget_reservation"):
        runner.verify_budget_and_recipes(
            dict(cfg, budget_reservation=dict(cfg["budget_reservation"], total_reserved_candidates=1382))
        )

    recorded_deadlines = []
    monkeypatch.setattr(runner, "deadline_check", lambda dl: recorded_deadlines.append(float(dl)))
    monkeypatch.setattr(runner.time, "time", lambda: 50000.0)

    out_dl = tmp_path / "out_dl"
    bad_cfg = dict(cfg, parent_freeze_sha256="0" * 64)
    bad_proto = tmp_path / "bad_proto.json"
    save(bad_proto, bad_cfg)

    recorded_deadlines.clear()
    with pytest.raises(ValueError):
        runner.run_history_shard(bad_cfg, out_dl, 0, protocol_path=bad_proto, root=root)
    assert recorded_deadlines[0] == 50000.0 + 600.0 - 30.0

    recorded_deadlines.clear()
    with pytest.raises(ValueError):
        runner.run_freeze_stage(bad_cfg, out_dl / "f", protocol_path=bad_proto, root=root)
    assert recorded_deadlines[0] == 50000.0 + 60.0 - 30.0

    recorded_deadlines.clear()
    with pytest.raises(ValueError):
        runner.run_evaluate_shard(cfg, out_dl / "e", 0, protocol_path=protocol_path, root=root)
    assert recorded_deadlines[0] == 50000.0 + 900.0 - 30.0

    recorded_deadlines.clear()
    with pytest.raises(ValueError):
        runner.run_aggregate_stage(cfg, out_dl / "a", protocol_path=protocol_path, root=root)
    assert recorded_deadlines[0] == 50000.0 + 1800.0 - 30.0

