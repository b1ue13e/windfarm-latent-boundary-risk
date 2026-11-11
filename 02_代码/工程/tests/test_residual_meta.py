import hashlib
import json
import os
from repo_paths import Path, repository_root
import shutil

import numpy as np
import pytest

import scripts.run_residual_meta as runner
from scripts.run_mixture_closed_loop import save, score_actions, sha
from windfarm_moe.residual_meta import (
    META_ARMS,
    build_meta_features,
    build_meta_recipes,
    extract_valid_fit_rows,
    fit_residual_meta_head,
    flatten_row_major,
    load_meta_model,
    make_hgbr_estimator,
    predict_residual_meta_actions,
    save_meta_model,
    verify_common_ref_expert0,
)


def _write_cache_with_manifest(
    cache_dir: Path,
    anchors: np.ndarray,
    y: np.ndarray,
    m: np.ndarray,
    seeds=(201, 202, 203, 204, 205),
):
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(cache_dir / "anchors.npy", anchors)
    np.save(cache_dir / "shortfall.npy", y)
    np.save(cache_dir / "mask.npy", m)
    rng = np.random.default_rng(20261024)
    for seed in seeds:
        ref0 = rng.uniform(2.0, 9.0, y.shape)
        for arm in ("P", "Z"):
            x = rng.uniform(1.0, 15.0, (*y.shape, 9))
            x[:, :, 0] = ref0
            np.save(cache_dir / f"{arm}_seed{seed}.npy", x)

    files = {}
    for p in sorted(cache_dir.glob("*.npy")):
        files[p.name] = dict(bytes=p.stat().st_size, sha256=sha(p))
    save(cache_dir / "manifest.json", dict(files=files))
    return sha(cache_dir / "manifest.json")


def _build_synthetic_meta_fixture(tmp_path: Path, monkeypatch, *, n_parent_policies=608, n_parent_comps=1911):
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

    parent_names = ["REF"]
    for i in range(1, n_parent_policies):
        if i == 365:
            parent_names.append("R0182_P")
        elif i == 373:
            parent_names.append("R0186_P")
        elif i == 374:
            parent_names.append("R0186_Z")
        elif i == 412:
            parent_names.append("GUARDED_FIXED_P")
        elif i == 413:
            parent_names.append("GUARDED_FIXED_Z")
        else:
            parent_names.append(f"PARENT_{i:04d}")
    assert len(parent_names) == n_parent_policies

    parent_comps = []
    seen_p = set()
    for idx in range(1, n_parent_policies):
        parent_comps.append([idx, 0])
        seen_p.add((idx, 0))
    step = 1
    while len(parent_comps) < n_parent_comps:
        for idx in range(1, n_parent_policies):
            right = ((idx + step - 1) % (n_parent_policies - 1)) + 1
            if right != idx and (idx, right) not in seen_p:
                parent_comps.append([idx, right])
                seen_p.add((idx, right))
                if len(parent_comps) == n_parent_comps:
                    break
        step += 1
    assert len(parent_comps) == n_parent_comps

    parent_ledger = np.ones((5, n_parent_policies, 35, 4), dtype=np.float64)
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
        available=[True] * n_parent_policies,
        family_definition=dict(
            policy_names=parent_names,
            comparisons=parent_comps,
            frozen_aliases=[[2, 1]],
        ),
    )
    save(parent_dir / "inference_span3.json", parent_span3)

    src_file = tmp_path / "dummy_source.py"
    src_file.write_text("# synthetic meta source\n", encoding="utf-8")

    cfg = dict(
        study_id="meta_relief_synthetic_test",
        max_candidates=24,
        max_cpu_seconds=28800,
        history_wall_seconds=1200,
        evaluation_wall_seconds=240,
        shard_wall_seconds=1200,
        freeze_wall_seconds=60,
        aggregate_wall_seconds=1800,
        independent_audit_wall_seconds=600,
        local_retry_reserve_seconds=4740,
        maximum_science_parallel_jobs=15,
        budget_reservation=dict(
            new_candidates=24,
            cpu_seconds=28800,
            total_reserved_candidates=1382,
            total_accounted_plus_open_reservations_cpu=66219,
            global_cpu_limit_unchanged=86400,
        ),
        min_fit_rows=2,
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
        recipes=build_meta_recipes(),
        source_hashes={"dummy_source.py": sha(src_file)},
        inference=dict(spans=[3, 1, 7], n_boot=4, seed=20261022),
    )
    protocol_path = tmp_path / "protocol.json"
    save(protocol_path, cfg)
    return cfg, protocol_path, tmp_path


def test_24_recipe_grid_and_15_shard_mapping_deterministic():
    recipes = build_meta_recipes()
    assert len(recipes) == 24
    assert [r["id"] for r in recipes] == list(range(24))
    assert recipes[0] == dict(
        id=0,
        q=0.90,
        leaves=7,
        l2=1.0,
        config=dict(
            q=0.90,
            leaves=7,
            l2=1.0,
            loss="quantile",
            max_iter=128,
            max_bins=127,
            learning_rate=0.05,
            min_samples_leaf=64,
            early_stopping=False,
        ),
    )
    assert recipes[23] == dict(
        id=23,
        q=0.975,
        leaves=31,
        l2=10.0,
        config=dict(
            q=0.975,
            leaves=31,
            l2=10.0,
            loss="quantile",
            max_iter=128,
            max_bins=127,
            learning_rate=0.05,
            min_samples_leaf=64,
            early_stopping=False,
        ),
    )
    est = make_hgbr_estimator(0.95, 15, 10.0, 203)
    assert est.loss == "quantile"
    assert est.quantile == 0.95
    assert est.max_iter == 128
    assert est.max_leaf_nodes == 15
    assert est.max_bins == 127
    assert est.learning_rate == 0.05
    assert est.min_samples_leaf == 64
    assert est.l2_regularization == 10.0
    assert est.early_stopping is False
    assert est.random_state == 203

    mapped = [runner.shard_assignment(s) for s in range(15)]
    expected = [
        (201, "C"), (201, "P"), (201, "Z"),
        (202, "C"), (202, "P"), (202, "Z"),
        (203, "C"), (203, "P"), (203, "Z"),
        (204, "C"), (204, "P"), (204, "Z"),
        (205, "C"), (205, "P"), (205, "Z"),
    ]
    assert mapped == expected
    with pytest.raises(ValueError):
        runner.shard_assignment(15)
    with pytest.raises(ValueError):
        runner.shard_assignment(-1)
    with pytest.raises(ValueError):
        runner.shard_assignment(True)


def test_independent_manual_feature_oracle_and_no_future_or_mask_dependence():
    # Manual oracle for T=3 anchors: [144*10 + 0, 144*10 + 36, 144*10 + 72] -> slots 0, 36 (pi/2), 72 (pi)
    # N=3 turbines: node indices 0, 1, 2 -> normalized 0/134, 1/134, 2/134
    anchors = np.array([1440, 1476, 1512], dtype=np.int64)
    b = np.array(
        [
            [5.0, 6.0, 7.0],
            [8.0, 9.0, 10.0],
            [11.0, 12.0, 13.0],
        ],
        dtype=np.float64,
    )
    rng = np.random.default_rng(123)
    x_p = rng.uniform(1.0, 20.0, (3, 3, 9))
    x_z = rng.uniform(1.0, 20.0, (3, 3, 9))
    # Bitwise common REF expert 0
    x_z[:, :, 0] = x_p[:, :, 0]
    ref0 = verify_common_ref_expert0(x_p, x_z)
    np.testing.assert_array_equal(ref0, x_p[:, :, 0])

    feat_c = build_meta_features(b, x_p, anchors, "C")
    feat_p = build_meta_features(b, x_p, anchors, "P")
    feat_z = build_meta_features(b, x_z, anchors, "Z")

    assert feat_c.shape == (3, 3, 5)
    assert feat_p.shape == (3, 3, 13)
    assert feat_z.shape == (3, 3, 13)

    # First 5 common features in P and Z must be bitwise identical to C (expert 0 not duplicated)
    np.testing.assert_array_equal(feat_p[:, :, :5], feat_c)
    np.testing.assert_array_equal(feat_z[:, :, :5], feat_c)
    # Additional 8 features in P and Z are raw experts 1..8
    np.testing.assert_array_equal(feat_p[:, :, 5:], x_p[:, :, 1:9])
    np.testing.assert_array_equal(feat_z[:, :, 5:], x_z[:, :, 1:9])

    # Manual check of slot 0 (sin=0, cos=1), slot 36 (sin=1, cos=0), slot 72 (sin=0, cos=-1)
    np.testing.assert_allclose(feat_c[0, :, 2], 0.0, atol=1e-15)
    np.testing.assert_allclose(feat_c[0, :, 3], 1.0, atol=1e-15)
    np.testing.assert_allclose(feat_c[1, :, 2], 1.0, atol=1e-15)
    np.testing.assert_allclose(feat_c[1, :, 3], 0.0, atol=1e-15)
    np.testing.assert_allclose(feat_c[2, :, 2], 0.0, atol=1e-15)
    np.testing.assert_allclose(feat_c[2, :, 3], -1.0, atol=1e-15)
    np.testing.assert_allclose(feat_c[:, 0, 4], 0.0 / 134.0, atol=1e-15)
    np.testing.assert_allclose(feat_c[:, 1, 4], 1.0 / 134.0, atol=1e-15)
    np.testing.assert_allclose(feat_c[:, 2, 4], 2.0 / 134.0, atol=1e-15)

    # Row-major stack check: row t*N + n matches feat_p[t, n]
    flat_p = flatten_row_major(feat_p)
    assert flat_p.shape == (9, 13)
    for t in range(3):
        for n in range(3):
            np.testing.assert_array_equal(flat_p[t * 3 + n], feat_p[t, n])

    # Verify tampering REF expert 0 between P and Z is rejected
    x_z_bad = x_z.copy()
    x_z_bad[1, 2, 0] += 1e-12
    with pytest.raises(ValueError, match="REF expert 0 is not bitwise identical"):
        verify_common_ref_expert0(x_p, x_z_bad)


def test_real_hgbr_smoke_negative_residual_clamp_and_exact_serialization(tmp_path):
    # Real HistGradientBoostingRegressor smoke test where baseline b=20 > target y=4
    # so signed residual y - b = -16 < 0, and predicted action clamps at 0 if b + pred < 0.
    rng = np.random.default_rng(2026)
    t_steps, n_nodes = 40, 4  # 160 rows >= min_samples_leaf=64
    anchors = np.arange(27648, 27648 + t_steps, dtype=np.int64)
    b = np.full((t_steps, n_nodes), 20.0, dtype=np.float64)
    # Set y=4 on most rows, and y=0 with small b on test prediction rows to trigger zero clamp
    y = np.full((t_steps, n_nodes), 4.0, dtype=np.float64)
    mask = np.ones((t_steps, n_nodes), dtype=bool)
    mask[0, 1] = False
    x = rng.uniform(2.0, 10.0, (t_steps, n_nodes, 9))

    feat = build_meta_features(b, x, anchors, "P")
    x_valid, res_target, b_valid, y_valid, idx_sha = extract_valid_fit_rows(feat, b, y, mask)
    assert x_valid.shape == (t_steps * n_nodes - 1, 13)
    assert np.all(res_target < 0.0)
    assert len(idx_sha) == 64

    bundle, info = fit_residual_meta_head(
        x_valid,
        b_valid,
        y_valid,
        q=0.90,
        leaves=7,
        l2=1.0,
        seed=201,
        arm="P",
        min_rows=64,
    )
    assert info["status"] == "FITTED_OK"
    assert not info["fallback_to_anchor"]
    assert info["fit_success"] is True
    assert info["optimality_certified"] is False
    assert "optimal" not in info
    assert bundle["fit_success"] is True
    assert bundle["optimality_certified"] is False
    assert "optimal" not in bundle
    expected_params_all = make_hgbr_estimator(0.90, 7, 1.0, 201).get_params(deep=False)
    assert info["params_all"] == expected_params_all
    assert bundle["params_all"] == expected_params_all
    assert info["negative_residual_fraction"] == 1.0
    assert info["predicted_negative_offset_fraction"] == 1.0

    # Save and reload via joblib and verify bitwise identical predictions
    model_path = tmp_path / "M000.joblib"
    save_meta_model(model_path, bundle)
    loaded = load_meta_model(model_path)
    assert loaded["params_all"] == expected_params_all
    assert loaded["fit_success"] is True
    assert loaded["optimality_certified"] is False
    assert "optimal" not in loaded

    # Predict on a test grid where b is small (e.g. 1.0 kW) while predicted residual is ~ -16 kW -> clamped to 0.0
    b_eval = np.full((6, n_nodes), 1.0, dtype=np.float64)
    x_eval = rng.uniform(2.0, 10.0, (6, n_nodes, 9))
    a_eval = np.arange(30240, 30246, dtype=np.int64)
    feat_eval = build_meta_features(b_eval, x_eval, a_eval, "P")

    act1, pinfo1 = predict_residual_meta_actions(bundle, feat_eval, b_eval)
    act2, pinfo2 = predict_residual_meta_actions(loaded, feat_eval, b_eval)
    np.testing.assert_array_equal(act1, act2)
    assert pinfo1 == pinfo2
    assert np.all(act1 == 0.0)
    assert pinfo1["zero_clamp_count"] == 6 * n_nodes
    assert pinfo1["negative_offset_count"] == 6 * n_nodes

    # Verify future labels / current mask do not enter prediction
    y_eval_a = np.full((6, n_nodes), 5.0)
    y_eval_b = np.full((6, n_nodes), 999.0)
    m_eval = np.ones((6, n_nodes), dtype=bool)
    led_a, _, _ = score_actions(act1, y_eval_a, m_eval, a_eval)
    led_b, _, _ = score_actions(act1, y_eval_b, m_eval, a_eval)
    # Actions are identical; score_actions scores against raw shortfall y_eval
    assert led_b[0, 2] > led_a[0, 2]


def test_empty_or_failed_fit_declares_anchor_fallback_without_dropping():
    x_empty = np.empty((0, 5), dtype=np.float64)
    b_empty = np.empty((0,), dtype=np.float64)
    y_empty = np.empty((0,), dtype=np.float64)
    bundle, info = fit_residual_meta_head(
        x_empty,
        b_empty,
        y_empty,
        q=0.95,
        leaves=15,
        l2=10.0,
        seed=202,
        arm="C",
        min_rows=64,
    )
    assert bundle["fallback_to_anchor"] is True
    assert bundle["status"] == "FIT_ERROR_DECLARED_ANCHOR_FALLBACK"
    assert bundle["fit_success"] is False
    assert bundle["optimality_certified"] is False
    assert bundle["params_all"] is None
    assert "optimal" not in bundle
    assert info["status"] == "FIT_ERROR_DECLARED_ANCHOR_FALLBACK"
    assert info["fit_success"] is False
    assert info["optimality_certified"] is False
    assert info["params_all"] is None
    assert "optimal" not in info
    assert info["fit_qualified"] is False

    b_test = np.array([[4.5, 7.2], [3.1, 8.9]], dtype=np.float64)
    x_test = np.ones((2, 2, 9), dtype=np.float64)
    a_test = np.array([30240, 30241], dtype=np.int64)
    feat_test = build_meta_features(b_test, x_test, a_test, "C")
    act, pred_info = predict_residual_meta_actions(bundle, feat_test, b_test)
    np.testing.assert_array_equal(act, b_test)
    assert pred_info["fallback_to_anchor"] is True


_DUMMY_CALL_COUNTER = {"count": 0}


class FastDummyHGBR:
    def __init__(self, q, leaves, l2, seed):
        self.q = float(q)
        self.leaves = int(leaves)
        self.l2 = float(l2)
        self.seed = int(seed)
        self.offset_ = 0.0

    def get_params(self, deep=False):
        return make_hgbr_estimator(self.q, self.leaves, self.l2, self.seed).get_params(deep=deep)

    def fit(self, X, y):
        _DUMMY_CALL_COUNTER["count"] += 1
        if _DUMMY_CALL_COUNTER["count"] == 1:
            raise RuntimeError("synthetic estimator failure on first head")
        self.offset_ = float(np.quantile(y, self.q)) + 0.01 * (self.leaves / 31.0) - 0.001 * self.l2
        return self

    def predict(self, X):
        return np.full(X.shape[0], self.offset_, dtype=np.float64)


def test_full_distributed_pipeline_1080_models_72_roles_288_comparisons_and_barriers(tmp_path, monkeypatch):
    cfg, protocol_path, root = _build_synthetic_meta_fixture(
        tmp_path, monkeypatch, n_parent_policies=608, n_parent_comps=1911
    )
    out = tmp_path / "out"

    import windfarm_moe.residual_meta as rm_mod

    _DUMMY_CALL_COUNTER["count"] = 0
    monkeypatch.setattr(rm_mod, "make_hgbr_estimator", lambda q, leaves, l2, seed: FastDummyHGBR(q, leaves, l2, seed))

    # Barrier check: freeze before history -> rejected
    with pytest.raises(ValueError, match="Missing history shard receipt"):
        runner.run_freeze_stage(cfg, tmp_path / "out_pre_freeze", protocol_path=protocol_path, root=root)

    # Barrier check: evaluate before freeze -> rejected
    with pytest.raises(ValueError, match="FINAL_FREEZE.json"):
        runner.run_evaluate_shard(cfg, tmp_path / "out_pre_eval", 0, protocol_path=protocol_path, root=root)

    # Guard evaluation_cache during history stage
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
    for shard in range(15):
        rec = runner.run_history_shard(cfg, out, shard, protocol_path=protocol_path, root=root)
        assert rec["models_fitted"] == 72
        assert not rec["evaluation_cache_read"]
        assert not rec["scientific_qualification_used_to_filter"]
    monkeypatch.setattr(np, "load", real_np_load)
    monkeypatch.setattr(runner, "verify_cache", real_verify_cache)

    # Verify fallback head on shard 0 (C_seed201, inner, M000) was saved and evaluated without dropping
    fb_rcpt = json.loads((out / runner.model_receipt_relpath("inner", "C", 201, 0)).read_text(encoding="utf-8"))
    assert fb_rcpt["status"] == "FIT_ERROR_DECLARED_ANCHOR_FALLBACK"
    assert fb_rcpt["fallback_to_anchor"] is True
    assert fb_rcpt["fit_success"] is False
    assert fb_rcpt["optimality_certified"] is False
    assert fb_rcpt["params_all"] is None
    assert "optimal" not in fb_rcpt
    assert fb_rcpt["last_label_release"] < fb_rcpt["episode_start"]

    ok_rcpt = json.loads((out / runner.model_receipt_relpath("inner", "C", 201, 1)).read_text(encoding="utf-8"))
    assert ok_rcpt["status"] == "FITTED_OK"
    assert ok_rcpt["fit_success"] is True
    assert ok_rcpt["optimality_certified"] is False
    assert isinstance(ok_rcpt["params_all"], dict)
    assert ok_rcpt["params_all"]["max_iter"] == 128
    assert "optimal" not in ok_rcpt

    # Freeze stage hashes all 1080 models and 1080 model receipts
    freeze = runner.run_freeze_stage(cfg, out, protocol_path=protocol_path, root=root)
    assert len(freeze["all_models"]) == 1080
    assert len(freeze["all_model_receipts"]) == 1080
    assert (out / "EVALUATION_OPEN.json").exists()
    outer_sel = json.loads((out / "outer_selection.json").read_text(encoding="utf-8"))
    assert outer_sel["qualification_did_not_filter_instances"] is True
    assert set(outer_sel["roles"].keys()) == {"C", "P", "Z"}
    for arm in ("C", "P", "Z"):
        assert 0 <= outer_sel["roles"][arm]["minimum_C_id"] < 24
        assert 0 <= outer_sel["roles"][arm]["minimum_maxV_id"] < 24

    # Second freeze attempt must fail BEFORE ANY write
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

    # Inject a prediction failure on shard 0 evaluate for recipe 23 to verify preserved failure slots
    real_predict = runner.predict_residual_meta_actions

    def faulty_predict(bundle, features_3d, b):
        if bundle.get("recipe_id") == 23 and bundle.get("arm") == "C" and bundle.get("seed") == 201:
            raise FloatingPointError("synthetic prediction error on M023 C_seed201")
        return real_predict(bundle, features_3d, b)

    monkeypatch.setattr(runner, "predict_residual_meta_actions", faulty_predict)
    runner.run_evaluate_shard(cfg, out, 0, protocol_path=protocol_path, root=root)
    monkeypatch.setattr(runner, "predict_residual_meta_actions", real_predict)

    for shard in range(1, 15):
        runner.run_evaluate_shard(cfg, out, shard, protocol_path=protocol_path, root=root)

    # Check shard 0 evaluate receipt: recipe 23 is FAILED_PRESERVED with NaN ledger, others COMPLETED
    r0 = json.loads((out / "instances/evaluate/C_seed201/receipt.json").read_text(encoding="utf-8"))
    d0 = np.load(out / "instances/evaluate/C_seed201/daily.npz")
    assert d0["ledger"].shape == (24, 35, 4)
    assert r0["status"]["23"] == "FAILED_PRESERVED"
    assert np.isnan(d0["ledger"][23]).all()
    assert r0["status"]["0"] == "COMPLETED"
    assert np.isfinite(d0["ledger"][0]).all()

    # Tampered model weight rejection test on a lightweight copy (only shard 1 models)
    out_tampered = tmp_path / "out_tampered"
    shutil.copytree(out / "models/evaluate/P_seed201", out_tampered / "models/evaluate/P_seed201")
    shutil.copyfile(out / "FINAL_FREEZE.json", out_tampered / "FINAL_FREEZE.json")
    shutil.copyfile(out / "EVALUATION_OPEN.json", out_tampered / "EVALUATION_OPEN.json")
    shutil.copyfile(out / "protocol_original.json", out_tampered / "protocol_original.json")
    target_model = out_tampered / runner.model_relpath("evaluate", "P", 201, 0)
    target_model.write_bytes(target_model.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="Evaluate model missing or modified since freeze"):
        runner.run_evaluate_shard(cfg, out_tampered, 1, protocol_path=protocol_path, root=root)

    # Mutating cfg while keeping original protocol_path is rejected at protocol semantic barrier
    bad_cfg = dict(cfg, expected_evaluation_valid_cells=999999)
    with pytest.raises(ValueError, match="Supplied cfg differs from parsed original protocol"):
        runner.run_evaluate_shard(bad_cfg, out_tampered, 2, protocol_path=protocol_path, root=root)

    # Tampered model weight on disk BEFORE freeze is caught against history shard receipt sha256
    target_hist_model = out / runner.model_relpath("inner", "Z", 202, 5)
    orig_hist_model_bytes = target_hist_model.read_bytes()
    for f_rm in (out / "FINAL_FREEZE.json", out / "EVALUATION_OPEN.json", out / "shards/freeze/state.json"):
        f_rm.unlink()
    try:
        target_hist_model.write_bytes(orig_hist_model_bytes + b"tampered")
        with pytest.raises(ValueError, match="sha256 mismatch against history shard 5 receipt"):
            runner.run_freeze_stage(cfg, out, protocol_path=protocol_path, root=root)
    finally:
        target_hist_model.write_bytes(orig_hist_model_bytes)
        for f_rm in (out / "shards/freeze/failure.json", out / "shards/freeze/state.json"):
            if f_rm.exists():
                f_rm.unlink()
    # Re-run clean freeze after restoring model bytes
    runner.run_freeze_stage(cfg, out, protocol_path=protocol_path, root=root)
    # Update evaluate shard receipts with new freeze_sha256 so aggregate succeeds
    new_freeze_sha = sha(out / "FINAL_FREEZE.json")
    for s_idx in range(15):
        sd, am = runner.shard_assignment(s_idx)
        er_path = out / "shards/evaluate" / f"shard_{s_idx:02d}_{am}_seed{sd}" / "receipt.json"
        er_data = json.loads(er_path.read_text(encoding="utf-8"))
        er_data["freeze_sha256"] = new_freeze_sha
        save(er_path, er_data)

    # Aggregate stage
    completion = runner.run_aggregate_stage(cfg, out, protocol_path=protocol_path, root=root, n_boot_override=4)
    assert completion["status"] == "COMPLETED_WITH_PRESERVED_FAILURES"
    assert completion["planned_recipes"] == 24
    assert completion["planned_instances_per_phase"] == 360
    assert completion["total_planned_instances"] == 1080
    assert completion["complete_per_phase"]["inner"] == 360
    assert completion["complete_per_phase"]["outer"] == 360
    assert completion["complete_per_phase"]["evaluate"] == 359
    assert completion["failed_per_phase"]["inner"] == 0
    assert completion["failed_per_phase"]["outer"] == 0
    assert completion["failed_per_phase"]["evaluate"] == 1
    assert completion["all_planned_instances_retained"] is True
    assert completion["scientific_qualification_used_to_filter"] is False
    assert completion["thresholds_changed"] is False

    all_names = json.loads((out / "all_policy_names.json").read_text(encoding="utf-8"))
    assert all_names["parent_policy_count"] == 608
    assert all_names["new_policy_count"] == 72
    assert len(all_names["names"]) == 680
    assert all_names["parent_comparison_count"] == 1911
    assert all_names["total_comparison_count"] == 1911 + 288
    assert all_names["names"][608:611] == ["MR000_C", "MR000_P", "MR000_Z"]
    assert all_names["names"][-3:] == ["MR023_C", "MR023_P", "MR023_Z"]
    # MR023_C failed on seed 201 -> available=False; MR023_P and MR023_Z -> available=True
    assert all_names["available"][-3:] == [False, True, True]

    # Verify parent ledger slices are retained verbatim
    parent_npz = np.load(Path(cfg["parent_results"]) / "all_daily_ledger.npz")
    child_npz = np.load(out / "all_daily_ledger.npz")
    np.testing.assert_array_equal(child_npz["ledger"][:, :608], parent_npz["ledger"])

    for span in (3, 1, 7):
        assert (out / f"inference_span{span}.json").exists()

    # Check phase-specific default deadlines (history=1200s vs evaluate=240s, freeze=60s, aggregate=1800s)
    recorded_deadlines = []

    def spy_deadline_check(dl):
        recorded_deadlines.append(float(dl))

    monkeypatch.setattr(runner, "deadline_check", spy_deadline_check)
    monkeypatch.setattr(runner.time, "time", lambda: 10000.0)

    # Evaluate deadline must use evaluation_wall_seconds (240 - 30 = 210), NOT history_wall_seconds / shard_wall_seconds (1200)
    recorded_deadlines.clear()
    out_dl = tmp_path / "out_dl"
    out_dl.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(out / "FINAL_FREEZE.json", out_dl / "FINAL_FREEZE.json")
    shutil.copyfile(out / "EVALUATION_OPEN.json", out_dl / "EVALUATION_OPEN.json")
    shutil.copyfile(out / "protocol_original.json", out_dl / "protocol_original.json")
    with pytest.raises(ValueError, match="Evaluate model missing"):
        runner.run_evaluate_shard(cfg, out_dl, 0, protocol_path=protocol_path, root=root)
    assert recorded_deadlines[0] == 10000.0 + 240.0 - 30.0

    # History deadline must use history_wall_seconds (1200 - 30 = 1170)
    recorded_deadlines.clear()
    bad_hist_cfg = dict(cfg, historical_manifest_sha256="0" * 64)
    bad_hist_proto = tmp_path / "bad_hist_proto.json"
    save(bad_hist_proto, bad_hist_cfg)
    with pytest.raises(ValueError):
        runner.run_history_shard(bad_hist_cfg, out_dl, 0, protocol_path=bad_hist_proto, root=root)
    assert recorded_deadlines[0] == 10000.0 + 1200.0 - 30.0

    # Aggregate deadline must use aggregate_wall_seconds (1800 - 30 = 1770)
    recorded_deadlines.clear()
    with pytest.raises(ValueError, match="Missing evaluate shard receipt"):
        runner.run_aggregate_stage(cfg, out_dl, protocol_path=protocol_path, root=root)
    assert recorded_deadlines[0] == 10000.0 + 1800.0 - 30.0

    # Freeze deadline must use freeze_wall_seconds (60 - 30 = 30)
    recorded_deadlines.clear()
    out_dl_freeze = tmp_path / "out_dl_freeze"
    with pytest.raises(ValueError, match="Missing history shard receipt"):
        runner.run_freeze_stage(cfg, out_dl_freeze, protocol_path=protocol_path, root=root)
    assert recorded_deadlines[0] == 10000.0 + 60.0 - 30.0

    # Budget arithmetic and strict recipe schema validation checks
    assert 15 * 1200 + 15 * 240 + 60 + 1800 + 600 + 4740 == 28800
    verified_recipes = runner.verify_budget_and_recipes(cfg)
    assert verified_recipes == build_meta_recipes()

    # Reject old 14400 / 720 budget or mismatched phase arithmetic
    with pytest.raises(ValueError, match="28800"):
        runner.verify_budget_and_recipes(dict(cfg, max_cpu_seconds=14400))
    with pytest.raises(ValueError, match="history_wall_seconds"):
        runner.verify_budget_and_recipes(dict(cfg, history_wall_seconds=720))
    with pytest.raises(ValueError, match="evaluation_wall_seconds"):
        runner.verify_budget_and_recipes(dict(cfg, evaluation_wall_seconds=720))
    with pytest.raises(ValueError, match="freeze_wall_seconds"):
        runner.verify_budget_and_recipes(dict(cfg, freeze_wall_seconds=120))
    with pytest.raises(ValueError, match="aggregate_wall_seconds"):
        runner.verify_budget_and_recipes(dict(cfg, aggregate_wall_seconds=1200))
    with pytest.raises(ValueError, match="independent_audit_wall_seconds"):
        runner.verify_budget_and_recipes(dict(cfg, independent_audit_wall_seconds=300))
    with pytest.raises(ValueError, match="local_retry_reserve_seconds"):
        runner.verify_budget_and_recipes(dict(cfg, local_retry_reserve_seconds=4000))
    with pytest.raises(ValueError, match="budget_reservation"):
        runner.verify_budget_and_recipes(
            dict(
                cfg,
                budget_reservation=dict(
                    cfg["budget_reservation"],
                    total_accounted_plus_open_reservations_cpu=90000,
                ),
            )
        )

    # Reject missing fixed keys, extra unknown keys, or tampered values in recipes
    rec_missing_fixed = [dict(r, config=dict(r["config"])) for r in build_meta_recipes()]
    del rec_missing_fixed[3]["config"]["max_iter"]
    with pytest.raises(ValueError, match="Recipe 3 config keys"):
        runner.verify_budget_and_recipes(dict(cfg, recipes=rec_missing_fixed))

    rec_extra_cfg_key = [dict(r, config=dict(r["config"])) for r in build_meta_recipes()]
    rec_extra_cfg_key[5]["config"]["unknown_param"] = 123
    with pytest.raises(ValueError, match="Recipe 5 config keys"):
        runner.verify_budget_and_recipes(dict(cfg, recipes=rec_extra_cfg_key))

    rec_extra_top_key = [dict(r, config=dict(r["config"])) for r in build_meta_recipes()]
    rec_extra_top_key[2]["extra_top"] = "bad"
    with pytest.raises(ValueError, match="Recipe 2 keys"):
        runner.verify_budget_and_recipes(dict(cfg, recipes=rec_extra_top_key))

    rec_tampered_fixed = [dict(r, config=dict(r["config"])) for r in build_meta_recipes()]
    rec_tampered_fixed[7]["config"]["early_stopping"] = True
    with pytest.raises(ValueError, match="early_stopping"):
        runner.verify_budget_and_recipes(dict(cfg, recipes=rec_tampered_fixed))

