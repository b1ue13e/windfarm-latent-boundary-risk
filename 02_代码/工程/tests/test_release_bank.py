from __future__ import annotations

import hashlib
import json
from repo_paths import Path, repository_root
from typing import Any

import numpy as np
import pytest

import windfarm_moe.release_bank as rb
from windfarm_moe.delayed_calibration_baselines import run_delayed_calibration
from windfarm_moe.meta_action_stream import prefix_sha256


def _make_shortfall_with_payload(valid_vals: np.ndarray, mask: np.ndarray, payload_bits: int = 0x7FF8000000123456) -> np.ndarray:
    y = np.asarray(valid_vals, dtype=np.float64).copy()
    nan_val = np.array([payload_bits], dtype=np.uint64).view(np.float64)[0]
    y[~mask] = nan_val
    return y


def _manual_feedback_6(
    safe: np.ndarray, cost: np.ndarray, shortfall: np.ndarray, mask: np.ndarray, anchors: np.ndarray,
    window_steps: int = 144, lag_steps: int = 7,
) -> tuple[np.ndarray, np.ndarray]:
    t_steps, n_nodes = safe.shape
    out = np.zeros((t_steps, n_nodes, 6), dtype=np.float64)
    trace = np.full(t_steps, -1, dtype=np.int64)
    for i in range(t_steps):
        now = int(anchors[i])
        matured_idx = [j for j in range(i) if int(anchors[j]) + lag_steps < now]
        trace[i] = max((int(anchors[j]) + lag_steps for j in matured_idx), default=-1)
        win_idx = [j for j in matured_idx if int(anchors[j]) >= now - window_steps]
        c_diffs, u_diffs, v_diffs, s_norms = [], [], [], []
        for j in win_idx:
            valid = mask[j]
            if np.any(valid):
                s = shortfall[j, valid]
                b = safe[j, valid]
                c = cost[j, valid]
                u_c = np.maximum(s - c, 0.0) / 6.0
                u_b = np.maximum(s - b, 0.0) / 6.0
                c_c = c / 6.0 + 10.0 * u_c
                c_b = b / 6.0 + 10.0 * u_b
                c_diffs.append((c_c - c_b) / 100.0)
                u_diffs.append(10.0 * (u_c - u_b) / 100.0)
                v_diffs.append((s > c).astype(np.float64) - (s > b).astype(np.float64))
                s_norms.append(s / 100.0)
        if s_norms:
            s_cat = np.concatenate(s_norms)
            row = np.array([
                float(np.mean(np.concatenate(c_diffs))),
                float(np.mean(np.concatenate(u_diffs))),
                float(np.mean(np.concatenate(v_diffs))),
                float(np.mean(s_cat)),
                float(np.quantile(s_cat, 0.95, method="higher")),
                min(float(s_cat.size) / float(window_steps * n_nodes), 1.0),
            ], dtype=np.float64)
            out[i, :, :] = row[None, :]
    return out, trace


def test_feature_names_and_compute_current_features_width_and_validation() -> None:
    assert len(rb.CURRENT_FEATURE_NAMES) == 5
    assert len(rb.FEEDBACK_ONLY_FEATURE_NAMES) == 6
    assert len(rb.FEEDBACK_FEATURE_NAMES) == 11
    assert rb.FEEDBACK_FEATURE_NAMES == rb.CURRENT_FEATURE_NAMES + rb.FEEDBACK_ONLY_FEATURE_NAMES
    assert rb.ALL_FEATURE_NAMES == rb.FEEDBACK_FEATURE_NAMES
    assert rb.WIDTH_LOW_META_ID == 0
    assert rb.WIDTH_HIGH_META_ID == 18

    ref = np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float64)
    safe = np.array([[12.0, 25.0], [31.0, 42.0]], dtype=np.float64)
    cost = np.array([[11.0, 22.0], [35.0, 40.0]], dtype=np.float64)
    m0 = np.array([[8.0, 19.0], [28.0, 38.0]], dtype=np.float64)
    m18 = np.array([[15.0, 17.0], [25.0, 45.0]], dtype=np.float64)  # 2 negative crossings

    cur, neg_cross = rb.compute_current_features(ref, safe, cost, m0, m18)
    assert cur.shape == (2, 2, 5)
    assert not cur.flags.writeable
    assert np.isfinite(cur).all()
    assert neg_cross == 2
    np.testing.assert_allclose(cur[:, :, 0], ref)
    np.testing.assert_allclose(cur[:, :, 1], safe)
    np.testing.assert_allclose(cur[:, :, 2], cost)
    np.testing.assert_allclose(cur[:, :, 3], cost - safe)
    np.testing.assert_allclose(cur[:, :, 4], np.array([[7.0, 0.0], [0.0, 7.0]]))

    for bad_idx in range(5):
        args = [ref.copy(), safe.copy(), cost.copy(), m0.copy(), m18.copy()]
        args[bad_idx][0, 0] = np.nan
        with pytest.raises(ValueError, match="finite and nonnegative"):
            rb.compute_current_features(*args)
        args[bad_idx][0, 0] = -0.1
        with pytest.raises(ValueError, match="finite and nonnegative"):
            rb.compute_current_features(*args)


def test_feedback_maturity_t0_at_t8_and_rolling_expiry_with_gap() -> None:
    anchors = np.arange(12, dtype=np.int64)
    n_nodes = 2
    safe = np.full((12, n_nodes), 10.0, dtype=np.float64)
    cost = np.full((12, n_nodes), 8.0, dtype=np.float64)
    mask = np.ones((12, n_nodes), dtype=bool)
    mask[0, 1] = False  # at t=0 only 1 valid turbine out of 2 -> support = 1 / (window * 2)
    valid_s = np.full((12, n_nodes), 20.0, dtype=np.float64)
    valid_s[1:, :] = 5.0
    shortfall = _make_shortfall_with_payload(valid_s, mask)

    fb6, trace = rb.compute_feedback_features(safe, cost, shortfall, mask, anchors, window_steps=10, lag_steps=7)
    exp_fb6, exp_trace = _manual_feedback_6(safe, cost, shortfall, mask, anchors, window_steps=10, lag_steps=7)
    assert fb6.shape == (12, n_nodes, 6)
    assert not fb6.flags.writeable
    assert np.isfinite(fb6).all()
    np.testing.assert_array_equal(trace, exp_trace)
    np.testing.assert_allclose(fb6, exp_fb6, rtol=0.0, atol=1e-15)

    # Strict clock: source_anchor + 7 < decision_anchor => t=0 (anchor 0) matures only at anchor 8 (t=8)
    assert np.all(trace[:8] == -1)
    assert np.all(fb6[:8] == 0.0)
    assert trace[8] == 7
    assert np.isclose(fb6[8, 0, 5], 1.0 / float(10 * n_nodes))
    assert np.all(trace < anchors)

    # Rolling expiry by issue clock with a gap: anchors [0, 1, 8, 9, 144, 145, 160]
    gap_anchors = np.array([0, 1, 8, 9, 144, 145, 160], dtype=np.int64)
    g_safe = np.full((7, 2), 10.0, dtype=np.float64)
    g_cost = np.full((7, 2), 5.0, dtype=np.float64)
    g_mask = np.ones((7, 2), dtype=bool)
    g_y = np.array([
        [30.0, 30.0],  # anchor 0
        [12.0, 12.0],  # anchor 1
        [4.0, 4.0],    # anchor 8
        [4.0, 4.0],    # anchor 9
        [50.0, 50.0],  # anchor 144
        [50.0, 50.0],  # anchor 145
        [50.0, 50.0],  # anchor 160
    ], dtype=np.float64)
    g_fb, g_trace = rb.compute_feedback_features(g_safe, g_cost, g_y, g_mask, gap_anchors, window_steps=144, lag_steps=7)
    g_exp, g_exp_trace = _manual_feedback_6(g_safe, g_cost, g_y, g_mask, gap_anchors, window_steps=144, lag_steps=7)
    np.testing.assert_array_equal(g_trace, g_exp_trace)
    np.testing.assert_allclose(g_fb, g_exp, rtol=0.0, atol=1e-15)
    # At anchor 144: cutoff = 0, so anchors 0, 1, 8, 9 are all in window (4 issues * 2 = 8 cells)
    assert np.isclose(g_fb[4, 0, 5], 8.0 / 288.0)
    # At anchor 145: cutoff = 1, so anchor 0 expires! Only anchors 1, 8, 9 remain (6 cells)
    assert np.isclose(g_fb[5, 0, 5], 6.0 / 288.0)
    # At anchor 160: cutoff = 16, anchors 0, 1, 8, 9 all expired, anchors 144 and 145 matured (4 cells)
    assert np.isclose(g_fb[6, 0, 5], 4.0 / 288.0)


def test_causality_invariance_current_mask_and_future_shortfall() -> None:
    rng = np.random.default_rng(123)
    t_steps, n_nodes = 20, 3
    anchors = np.arange(t_steps, dtype=np.int64)
    ref = rng.uniform(5.0, 15.0, size=(t_steps, n_nodes))
    safe = rng.uniform(8.0, 20.0, size=(t_steps, n_nodes))
    cost = rng.uniform(6.0, 18.0, size=(t_steps, n_nodes))
    m0 = rng.uniform(4.0, 12.0, size=(t_steps, n_nodes))
    m18 = rng.uniform(10.0, 25.0, size=(t_steps, n_nodes))
    mask1 = rng.uniform(0.0, 1.0, size=(t_steps, n_nodes)) > 0.25
    valid_s1 = rng.uniform(0.0, 30.0, size=(t_steps, n_nodes))
    y1 = _make_shortfall_with_payload(valid_s1, mask1)

    cur1, _ = rb.compute_current_features(ref, safe, cost, m0, m18)
    fb1, tr1 = rb.compute_feedback_features(safe, cost, y1, mask1, anchors)

    # 1. Changing mask/shortfall at step k has zero impact on current_features anywhere and on feedback_features at steps <= k + 7
    k = 6
    mask2 = mask1.copy()
    mask2[k, :] = ~mask2[k, :]
    valid_s2 = valid_s1.copy()
    valid_s2[k, :] = 999.0
    y2 = _make_shortfall_with_payload(valid_s2, mask2)
    cur2, _ = rb.compute_current_features(ref, safe, cost, m0, m18)
    fb2, tr2 = rb.compute_feedback_features(safe, cost, y2, mask2, anchors)
    np.testing.assert_array_equal(cur1, cur2)
    np.testing.assert_array_equal(fb1[: k + 8], fb2[: k + 8])
    np.testing.assert_array_equal(tr1[: k + 8], tr2[: k + 8])

    # 2. Changing future S and mask after step k (> k) leaves all history features up to k+8 completely unchanged
    mask3 = mask1.copy()
    mask3[k + 1 :, :] = True
    valid_s3 = valid_s1.copy()
    valid_s3[k + 1 :, :] = 777.0
    y3 = _make_shortfall_with_payload(valid_s3, mask3)
    fb3, tr3 = rb.compute_feedback_features(safe, cost, y3, mask3, anchors)
    np.testing.assert_array_equal(fb1[: k + 9], fb3[: k + 9])
    np.testing.assert_array_equal(tr1[: k + 9], tr3[: k + 9])


def test_nan_validation_and_save_load_roundtrip_tamper_and_overwrite(tmp_path: Path) -> None:
    anchors = np.array([0, 1, 2, 9, 10], dtype=np.int64)
    mask = np.array([[True, False], [True, True], [False, False], [True, False], [True, True]], dtype=bool)
    valid_s = np.array([[5.0, 0.0], [10.0, 12.0], [0.0, 0.0], [8.0, 0.0], [4.0, 6.0]], dtype=np.float64)
    y = _make_shortfall_with_payload(valid_s, mask, payload_bits=0x7FF8000000ABCDEF)

    ref = np.full((5, 2), 6.0, dtype=np.float64)
    safe = np.full((5, 2), 9.0, dtype=np.float64)
    cost = np.full((5, 2), 7.0, dtype=np.float64)
    m0 = np.full((5, 2), 5.0, dtype=np.float64)
    m18 = np.full((5, 2), 11.0, dtype=np.float64)

    cur, _ = rb.compute_current_features(ref, safe, cost, m0, m18)
    fb6, trace = rb.compute_feedback_features(safe, cost, y, mask, anchors)
    fb11 = np.concatenate([cur, fb6], axis=-1)

    bank = dict(
        anchors=anchors, shortfall=y, mask=mask, reference=ref, safe=safe, cost=cost,
        current_features=cur, feedback_only_features=fb6, feedback_features=fb11,
        metadata=dict(feedback_release_trace=trace.tolist(), custom_tag="unit"),
    )

    # Validation checks: valid NaN rejected, finite outside mask rejected, nonfinite ref/safe/cost rejected, 6-col fb rejected
    bad_valid_nan = y.copy()
    bad_valid_nan[0, 0] = np.nan
    with pytest.raises(ValueError, match="Valid masked shortfall cells must be finite"):
        rb._validate_release_bank({**bank, "shortfall": bad_valid_nan})

    bad_outside_finite = y.copy()
    bad_outside_finite[0, 1] = 0.0
    validated = rb._validate_release_bank({**bank, "shortfall": bad_outside_finite})
    np.testing.assert_array_equal(validated[1], bad_outside_finite)

    for field in ("reference", "safe", "cost"):
        bad_arr = bank[field].copy()
        bad_arr[0, 1] = np.nan
        with pytest.raises(ValueError, match="finite and nonnegative"):
            rb._validate_release_bank({**bank, field: bad_arr})

    with pytest.raises(ValueError, match=r"feedback_features \[T, N, 11\]"):
        rb._validate_release_bank({**bank, "feedback_features": fb6})

    # Save and load roundtrip preserves exact NaN payload bytes and mask
    out_dir = tmp_path / "bank_art"
    receipt = rb.save_release_bank(out_dir, bank)
    loaded = rb.load_release_bank(out_dir, expected_sha256=receipt["npz_sha256"], expected_metadata_sha256=receipt["metadata_sha256"])

    assert loaded["current_features"].shape == (5, 2, 5)
    assert loaded["feedback_only_features"].shape == (5, 2, 6)
    assert loaded["feedback_features"].shape == (5, 2, 11)
    assert not loaded["feedback_features"].flags.writeable
    assert np.asarray(loaded["shortfall"], dtype="<f8").tobytes() == np.asarray(y, dtype="<f8").tobytes()
    np.testing.assert_array_equal(loaded["mask"], mask)

    # Refuse overwrite
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        rb.save_release_bank(out_dir, bank)

    # Bad SHA detection
    with pytest.raises(ValueError, match="NPZ file SHA-256 mismatch"):
        rb.load_release_bank(out_dir, expected_sha256="0" * 64)
    with pytest.raises(ValueError, match="metadata JSON SHA-256 mismatch"):
        rb.load_release_bank(out_dir, expected_metadata_sha256="0" * 64)


def _build_tiny_fixture_env(tmp_path: Path) -> dict[str, Any]:
    phase_anchors = {
        "inner": np.arange(0, 10, dtype=np.int64),
        "outer": np.arange(18, 28, dtype=np.int64),
        "evaluate": np.arange(36, 46, dtype=np.int64),
    }
    n_nodes = 2
    rng = np.random.default_rng(20261025)

    def _make_cache(kind: str, anchors_all: np.ndarray) -> tuple[Path, str, np.ndarray, np.ndarray, np.ndarray, dict[str, np.ndarray], np.ndarray, Path, str]:
        cdir = tmp_path / f"cache_{kind}"
        cdir.mkdir(parents=True, exist_ok=True)
        t_len = anchors_all.shape[0]
        mask = rng.uniform(0.0, 1.0, size=(t_len, n_nodes)) > 0.2
        mask[:, 0] = True
        valid_s = rng.uniform(2.0, 28.0, size=(t_len, n_nodes))
        shortfall = _make_shortfall_with_payload(valid_s, mask, payload_bits=0x7FF800000055AA11)
        ref0 = rng.uniform(6.0, 16.0, size=(t_len, n_nodes))
        x_arms: dict[str, np.ndarray] = {}
        for arm_idx, arm in enumerate(("C", "P", "Z")):
            x = rng.uniform(5.0, 25.0, size=(t_len, n_nodes, 9)).astype(np.float64)
            x[:, :, 0] = ref0  # common expert 0 across P and Z
            if arm == "Z":
                x[:, :, 1:] += 50.0  # make Z drastically different from P on experts 1..8
            np.save(cdir / f"{arm}_seed7.npy", x)
            x_arms[arm] = x
        np.save(cdir / "anchors.npy", anchors_all)
        np.save(cdir / "shortfall.npy", shortfall)
        np.save(cdir / "mask.npy", mask)

        files_meta = {}
        for f in sorted(cdir.glob("*.npy")):
            files_meta[f.name] = {"sha256": rb.sha(f), "bytes": f.stat().st_size}
        manifest_path = cdir / "manifest.json"
        rb.save(manifest_path, {"files": files_meta})
        manifest_sha = rb.sha(manifest_path)

        prof = rng.uniform(8.0, 18.0, size=(t_len, n_nodes)).astype(np.float64)
        prof_path = tmp_path / "profiles" / f"{kind}_seed7.npy"
        prof_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(prof_path, prof)
        return cdir, manifest_sha, anchors_all, shortfall, mask, x_arms, prof, prof_path, rb.sha(prof_path)

    hist_anchors = np.concatenate([phase_anchors["inner"], phase_anchors["outer"]])
    eval_anchors = phase_anchors["evaluate"]
    h_dir, h_msha, _, h_y, h_m, h_x, h_prof, h_ppath, h_psha = _make_cache("historical", hist_anchors)
    e_dir, e_msha, _, e_y, e_m, e_x, e_prof, e_ppath, e_psha = _make_cache("evaluate", eval_anchors)

    safe_dir = tmp_path / "safe_parent"
    mc_dir = tmp_path / "mc_parent"
    safe_dir.mkdir(parents=True, exist_ok=True)
    mc_dir.mkdir(parents=True, exist_ok=True)

    w0 = np.full(10, 0.1, dtype=np.float64)
    all_initializers: dict[str, str] = {}
    safe_inst_receipts: dict[str, str] = {}
    expected_safe_by_phase: dict[str, np.ndarray] = {}

    for phase in ("inner", "outer", "evaluate"):
        pa = phase_anchors[phase]
        is_eval = phase == "evaluate"
        a_src = eval_anchors if is_eval else hist_anchors
        idx = np.searchsorted(a_src, pa)
        y_slc = (e_y if is_eval else h_y)[idx]
        m_slc = (e_m if is_eval else h_m)[idx]
        b_slc = (e_prof if is_eval else h_prof)[idx]
        xp_slc = (e_x["P"] if is_eval else h_x["P"])[idx]

        init_rel = f"initializers/{phase}/P_seed7/COST_d0p01.json"
        init_path = safe_dir / init_rel
        rb.save(init_path, {
            "phase": phase, "seed": 7, "arm": "P", "relief": rb.SAFE_RELIEF,
            "goal": rb.SAFE_GOAL, "last_label_release": int(pa[0]) - 1,
            "canonical_initial": w0.tolist(),
        })
        all_initializers[init_rel] = rb.sha(init_path)

        delta = rb.signed_experts(xp_slc, b_slc, relief=rb.SAFE_RELIEF)
        res = rb.run_signed(
            delta, b_slc, y_slc, m_slc, pa, rb.SAFE_REPLAY_CONFIGS, w0,
            relief=rb.SAFE_RELIEF, score=False, return_actions=True,
        )
        act = np.ascontiguousarray(res["actions"][0], dtype=np.float64)
        expected_safe_by_phase[phase] = act
        rcpt_rel = f"instances/{phase}/P_seed7/receipt.json"
        rcpt_path = safe_dir / rcpt_rel
        rb.save(rcpt_path, {
            "status": {str(rb.SAFE_RECIPE_ID): "COMPLETED"},
            "action_sha256": {str(rb.SAFE_RECIPE_ID): prefix_sha256(act)},
        })
        if not is_eval:
            safe_inst_receipts[rcpt_rel] = rb.sha(rcpt_path)

    proto_payload = {"campaign": "tiny_fixture"}
    for cdir in (safe_dir, mc_dir):
        rb.save(cdir / "protocol_original.json", proto_payload)
        rb.save(cdir / "protocol.json", proto_payload)
    proto_sha = rb.sha(safe_dir / "protocol_original.json")

    safe_freeze_payload = {
        "protocol_sha256": proto_sha,
        "all_initializers": all_initializers,
        "all_instance_receipts": safe_inst_receipts,
    }
    rb.save(safe_dir / "FINAL_FREEZE.json", safe_freeze_payload)
    safe_freeze_sha = rb.sha(safe_dir / "FINAL_FREEZE.json")
    rb.save(safe_dir / "EVALUATION_OPEN.json", {"freeze_sha256": safe_freeze_sha, "protocol_sha256": proto_sha})

    # Stream banks (24 raw experts) and MCV2 receipts for C, P, Z
    stream_banks: dict[tuple[str, int, str], dict[str, Any]] = {}
    all_history_policy_shas: dict[str, dict[str, str]] = {}
    mc_inst_receipts: dict[str, str] = {}
    expected_cost_by_arm: dict[str, dict[str, np.ndarray]] = {}
    expected_width_by_arm: dict[str, dict[str, tuple[np.ndarray, np.ndarray]]] = {}

    for arm_idx, arm in enumerate(("C", "P", "Z")):
        raw_phases = {}
        for phase in ("inner", "outer", "evaluate"):
            pa = phase_anchors[phase]
            is_eval = phase == "evaluate"
            a_src = eval_anchors if is_eval else hist_anchors
            idx = np.searchsorted(a_src, pa)
            y_slc = (e_y if is_eval else h_y)[idx].copy()
            m_slc = (e_m if is_eval else h_m)[idx].copy()
            ref_slc = (e_x["P"] if is_eval else h_x["P"])[idx, :, 0].copy()

            raw_24 = rng.uniform(4.0, 24.0, size=(24, pa.shape[0], n_nodes)).astype(np.float64)
            raw_24[12] += float(arm_idx + 1) * 3.5  # distinct Meta 12 per arm
            # Force some negative crossings between Meta 18 and Meta 0
            raw_24[0, 0, 0] = 15.0
            raw_24[18, 0, 0] = 12.0
            bank_dict = {
                "anchors": pa.copy(),
                "shortfall": y_slc,
                "mask": m_slc,
                "reference": ref_slc,
                "raw_actions": raw_24,
                "metadata": {"phase": phase, "seed": 7, "arm": arm},
            }
            stream_banks[(phase, 7, arm)] = bank_dict
            raw_phases[phase] = bank_dict

        # Independently compute expected DelayedCalibration tracker on joined raw_actions[12]
        joined_hist = rb.join_banks([raw_phases["inner"], raw_phases["outer"]])
        joined_all = rb.join_banks([raw_phases["inner"], raw_phases["outer"], raw_phases["evaluate"]])
        cal_hist = run_delayed_calibration(
            joined_hist["raw_actions"][12], joined_hist["shortfall"], joined_hist["mask"], joined_hist["anchors"],
            rb.COST_CALIBRATION_CONFIG, save_trace=True,
        ).actions
        cal_all = run_delayed_calibration(
            joined_all["raw_actions"][12], joined_all["shortfall"], joined_all["mask"], joined_all["anchors"],
            rb.COST_CALIBRATION_CONFIG, save_trace=True,
        ).actions
        np.testing.assert_array_equal(cal_hist, cal_all[:20])
        expected_cost_by_arm[arm] = {"hist": cal_hist, "all": cal_all}
        expected_width_by_arm[arm] = {
            "hist": (joined_hist["raw_actions"][0], joined_hist["raw_actions"][18]),
            "all": (joined_all["raw_actions"][0], joined_all["raw_actions"][18]),
        }

        shard_key = f"{arm}_seed7"
        key = str(rb.COST_RECIPE_ID)
        hist_sha = prefix_sha256(cal_hist)
        all_history_policy_shas[shard_key] = {key: hist_sha}

        slices = {"inner": cal_all[:10], "outer": cal_all[10:20], "evaluate": cal_all[20:30]}
        for phase, slc in slices.items():
            rcpt_rel = f"instances/{phase}/{shard_key}/receipt.json"
            rcpt_path = mc_dir / rcpt_rel
            payload: dict[str, Any] = {
                "status": {key: "COMPLETED"},
                "action_sha256": {key: prefix_sha256(slc)},
            }
            if phase == "evaluate":
                payload["verified_history_prefix_sha256"] = {key: hist_sha}
            rb.save(rcpt_path, payload)
            if phase in ("inner", "outer"):
                mc_inst_receipts[rcpt_rel] = rb.sha(rcpt_path)

    mc_freeze_payload = {
        "protocol_sha256": proto_sha,
        "all_history_policy_shas": all_history_policy_shas,
        "all_instance_receipts": mc_inst_receipts,
    }
    rb.save(mc_dir / "FINAL_FREEZE.json", mc_freeze_payload)
    mc_freeze_sha = rb.sha(mc_dir / "FINAL_FREEZE.json")
    rb.save(mc_dir / "EVALUATION_OPEN.json", {"freeze_sha256": mc_freeze_sha, "protocol_sha256": proto_sha})

    cfg = {
        "historical_cache": str(h_dir),
        "historical_manifest_sha256": h_msha,
        "evaluation_cache": str(e_dir),
        "evaluation_manifest_sha256": e_msha,
        "parent_profiles": {
            "profiles/historical_seed7.npy": {"path": str(h_ppath), "sha256": h_psha, "bytes": h_ppath.stat().st_size},
            "profiles/evaluate_seed7.npy": {"path": str(e_ppath), "sha256": e_psha, "bytes": e_ppath.stat().st_size},
        },
        "stream_parent_results": str(mc_dir),
        "stream_parent_freeze_sha256": mc_freeze_sha,
        "stream_parent_input_protocol": str(mc_dir / "protocol_original.json"),
        "safe_parent_results": str(safe_dir),
        "safe_parent_freeze_sha256": safe_freeze_sha,
        "safe_parent_input_protocol": str(safe_dir / "protocol_original.json"),
    }
    return {
        "cfg": cfg,
        "stream_banks": stream_banks,
        "expected_safe_by_phase": expected_safe_by_phase,
        "expected_cost_by_arm": expected_cost_by_arm,
        "expected_width_by_arm": expected_width_by_arm,
    }


def test_build_release_bank_composition_shared_safe_and_no_eval_touch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = _build_tiny_fixture_env(tmp_path)
    cfg = env["cfg"]
    stream_banks = env["stream_banks"]
    called_phases: list[tuple[str, int, str]] = []

    def _fake_load_stream_bank(mc_dir: Path, mc_freeze: dict[str, Any], phase: str, seed: int, arm: str) -> tuple[dict[str, Any], dict[str, Any]]:
        called_phases.append((phase, seed, arm))
        b = stream_banks[(phase, seed, arm)]
        return b, {"phase": phase, "seed": seed, "arm": arm, "bank_sha256": prefix_sha256(b["raw_actions"])}

    monkeypatch.setattr(rb, "SEEDS", (7,))
    monkeypatch.setattr(rb, "load_verified_parent_stream_bank", _fake_load_stream_bank)

    orig_verify_cache = rb.verify_cache
    eval_cache_calls: list[Path] = []

    def _spy_verify_cache(cache_dir: Path, manifest_sha: str) -> None:
        if Path(cache_dir) == Path(cfg["evaluation_cache"]):
            eval_cache_calls.append(Path(cache_dir))
        orig_verify_cache(cache_dir, manifest_sha)

    monkeypatch.setattr(rb, "verify_cache", _spy_verify_cache)

    # 1. Build history-only banks across all 3 arms C, P, Z and verify no evaluation calls occur
    banks_hist = {}
    for arm in ("C", "P", "Z"):
        b = rb.build_release_bank(cfg, seed=7, arm=arm, include_evaluation=False)
        banks_hist[arm] = b
        assert b["anchors"].shape == (20,)
        assert b["current_features"].shape == (20, 2, 5)
        assert b["feedback_only_features"].shape == (20, 2, 6)
        assert b["feedback_features"].shape == (20, 2, 11)
        assert b["metadata"]["feedback_feature_names"] == list(rb.ALL_FEATURE_NAMES)
        assert len(b["metadata"]["feedback_feature_names"]) == 11
        assert b["metadata"]["evaluation_touched"] is False
        # All endpoints clock original[0] + 7 < now after first maturity (index >= 8)
        trace = np.asarray(b["metadata"]["feedback_release_trace"], dtype=np.int64)
        assert np.all(trace < b["anchors"])
        assert int(b["anchors"][0]) + 7 < int(b["anchors"][8])
        assert np.all(trace[8:] >= int(b["anchors"][0]) + 7)

        # Verify COST matches independent DelayedCalibration tracker on raw_actions[12] and first 8 cold-start steps match raw Meta 12
        exp_cost = env["expected_cost_by_arm"][arm]["hist"]
        np.testing.assert_allclose(b["cost"], exp_cost, rtol=0.0, atol=1e-15)
        raw12_inner = stream_banks[("inner", 7, arm)]["raw_actions"][12]
        np.testing.assert_array_equal(b["cost"][:8], raw12_inner[:8])
        # Independently hand-verify tracker update at first maturity (step 8, anchor 8, where step 0 matured: 0 + 7 < 8)
        m0_valid = stream_banks[("inner", 7, arm)]["mask"][0]
        y0_valid = stream_banks[("inner", 7, arm)]["shortfall"][0, m0_valid]
        a0_valid = raw12_inner[0, m0_valid]
        rate0 = float(np.mean(y0_valid > a0_valid))
        shift_step8 = 0.03 * (rate0 - 0.05)
        np.testing.assert_allclose(b["cost"][8], np.maximum(raw12_inner[8] + shift_step8, 0.0), rtol=0.0, atol=1e-15)
        m0, m18 = env["expected_width_by_arm"][arm]["hist"]
        np.testing.assert_allclose(b["current_features"][:, :, 4], np.maximum(m18 - m0, 0.0))
        np.testing.assert_array_equal(b["feedback_features"][:, :, :5], b["current_features"])
        np.testing.assert_array_equal(b["feedback_features"][:, :, 5:], b["feedback_only_features"])

    assert len(eval_cache_calls) == 0
    assert all(p != "evaluate" for p, _, _ in called_phases)

    # 2. Assert shared SAFE (BR009_P) across all 3 arms C, P, Z even though Z input varies in cache
    exp_safe_hist = np.concatenate([env["expected_safe_by_phase"]["inner"], env["expected_safe_by_phase"]["outer"]], axis=0)
    for arm in ("C", "P", "Z"):
        np.testing.assert_array_equal(banks_hist[arm]["safe"], exp_safe_hist)
        assert banks_hist[arm]["metadata"]["safe_sha256"] == banks_hist["P"]["metadata"]["safe_sha256"]

    # 3. Build with include_evaluation=True and verify history prefix is identical to history-only build
    b_eval = rb.build_release_bank(cfg, seed=7, arm="P", include_evaluation=True)
    assert len(eval_cache_calls) == 1
    assert b_eval["anchors"].shape == (30,)
    assert b_eval["feedback_features"].shape == (30, 2, 11)
    assert b_eval["metadata"]["evaluation_touched"] is True
    np.testing.assert_array_equal(b_eval["safe"][:20], banks_hist["P"]["safe"])
    np.testing.assert_array_equal(b_eval["cost"][:20], banks_hist["P"]["cost"])
    np.testing.assert_array_equal(b_eval["current_features"][:20], banks_hist["P"]["current_features"])
    np.testing.assert_array_equal(b_eval["feedback_features"][:20], banks_hist["P"]["feedback_features"])
