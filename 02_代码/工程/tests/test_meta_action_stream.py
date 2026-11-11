import json
from repo_paths import Path, repository_root
import shutil

import numpy as np
import pytest

from scripts.run_mixture_closed_loop import save, score_actions, sha
import windfarm_moe.meta_action_stream as mas
from windfarm_moe.meta_action_stream import (
    build_phase_bank,
    join_banks,
    load_bank,
    prefix_sha256,
    save_bank,
)
from windfarm_moe.residual_meta import (
    build_meta_features,
    build_meta_recipes,
    feature_names_for_arm,
    fit_residual_meta_head,
    predict_residual_meta_actions,
    save_meta_model,
)


class LinearOffsetFakeModel:
    """Tiny deterministic model with .predict(X) independent of labels/masks."""

    def __init__(self, recipe_id: int, weight0: float = 0.05):
        self.recipe_id = int(recipe_id)
        self.weight0 = float(weight0)

    def predict(self, X: np.ndarray) -> np.ndarray:
        arr = np.asarray(X, dtype=np.float64)
        return self.weight0 * arr[:, 1] + 0.1 * float(self.recipe_id) - 0.5


def _write_cache(cache_dir: Path, anchors: np.ndarray, y: np.ndarray, m: np.ndarray, seed: int = 201) -> str:
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(cache_dir / "anchors.npy", anchors)
    np.save(cache_dir / "shortfall.npy", y)
    np.save(cache_dir / "mask.npy", m)
    rng = np.random.default_rng(seed + int(anchors[0]))
    ref0 = rng.uniform(3.0, 8.0, y.shape)
    for arm in ("P", "Z"):
        x = rng.uniform(1.0, 12.0, (*y.shape, 9))
        x[:, :, 0] = ref0
        np.save(cache_dir / f"{arm}_seed{seed}.npy", x)
    files = {p.name: dict(bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(cache_dir.glob("*.npy"))}
    save(cache_dir / "manifest.json", dict(files=files))
    return sha(cache_dir / "manifest.json")


def _build_tiny_parent_fixture(tmp_path: Path, monkeypatch, *, seed: int = 201) -> tuple[Path, Path, dict]:
    """Build synthetic parent campaign results with 7-step causal gaps across inner, outer, and evaluate."""
    # Preserve 7-step gaps:
    # fit [27648, 27650) -> max=27649, release=27656 < inner begin=28087
    # inner: [28087, 28090) -> 28087, 28088, 28089; gap to outer begin=28097 is 8 steps (28097 - 28089 = 8 > 7)
    # outer: [28097, 28100) -> 28097, 28098, 28099; gap to evaluate begin=30240
    monkeypatch.setitem(mas.PHASES, "inner", (28087, 28090, 27650))
    monkeypatch.setitem(mas.PHASES, "outer", (28097, 28100, 28090))
    monkeypatch.setitem(mas.PHASES, "evaluate", (30240, 30244, 28100))

    hist_cache = tmp_path / "hist_cache"
    eval_cache = tmp_path / "eval_cache"
    parent_res = tmp_path / "parent_campaign"
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)

    ha = np.concatenate([
        np.arange(27648, 27650, dtype=np.int64),
        np.arange(28087, 28090, dtype=np.int64),
        np.arange(28097, 28100, dtype=np.int64),
    ])
    hy = np.full((len(ha), 2), 6.0, dtype=np.float64)
    hy[1::2, 1] = 10.0
    hm = np.ones_like(hy, dtype=bool)
    hm[3, 1] = False
    hm[6, 0] = False
    hy[3, 1] = np.nan
    hy[6, 0] = np.nan
    hist_manifest_sha = _write_cache(hist_cache, ha, hy, hm, seed=seed)

    ea = np.arange(30240, 30244, dtype=np.int64)
    ey = np.full((len(ea), 2), 7.5, dtype=np.float64)
    em = np.ones_like(ey, dtype=bool)
    em[1, 0] = False
    ey[1, 0] = np.nan
    eval_manifest_sha = _write_cache(eval_cache, ea, ey, em, seed=seed)

    b_hist = np.full_like(hy, 4.0)
    b_eval = np.full_like(ey, 5.0)
    p_hist = profiles_dir / f"historical_seed{seed}.npy"
    p_eval = profiles_dir / f"evaluate_seed{seed}.npy"
    np.save(p_hist, b_hist)
    np.save(p_eval, b_eval)

    src_file = tmp_path / "known_source.py"
    src_file.write_text("KNOWN_CONSTANT = 42\n", encoding="utf-8")
    source_hashes = {"known_source.py": sha(src_file)}

    cfg = dict(
        study_id="meta_relief_20261024_v1",
        historical_cache=str(hist_cache),
        historical_manifest_sha256=hist_manifest_sha,
        evaluation_cache=str(eval_cache),
        evaluation_manifest_sha256=eval_manifest_sha,
        expected_evaluation_anchors=len(ea),
        expected_evaluation_valid_cells=int(em.sum()),
        parent_profiles={
            f"profiles/historical_seed{seed}.npy": dict(path=str(p_hist), sha256=sha(p_hist), bytes=p_hist.stat().st_size),
            f"profiles/evaluate_seed{seed}.npy": dict(path=str(p_eval), sha256=sha(p_eval), bytes=p_eval.stat().st_size),
        },
        recipes=build_meta_recipes(),
        source_hashes=source_hashes,
    )

    parent_res.mkdir(parents=True, exist_ok=True)
    # Write protocol_original.json with CRLF and protocol.json with LF (semantically identical)
    raw_json_lf = json.dumps(cfg, indent=2) + "\n"
    raw_json_crlf = raw_json_lf.replace("\n", "\r\n")
    (parent_res / "protocol_original.json").write_bytes(raw_json_crlf.encode("utf-8"))
    (parent_res / "protocol.json").write_bytes(raw_json_lf.encode("utf-8"))
    save(parent_res / "source_versions.json", source_hashes)
    proto_sha = sha(parent_res / "protocol_original.json")
    assert proto_sha != sha(parent_res / "protocol.json")

    recipes = build_meta_recipes()
    all_models = {}
    all_rcpts = {}

    for phase in ("inner", "outer", "evaluate"):
        is_eval = phase == "evaluate"
        c_dir = eval_cache if is_eval else hist_cache
        m_sha_expected = eval_manifest_sha if is_eval else hist_manifest_sha
        b_full = b_eval if is_eval else b_hist
        p_sha = sha(p_eval if is_eval else p_hist)
        a_full = np.load(c_dir / "anchors.npy")
        y_full = np.load(c_dir / "shortfall.npy")
        m_full = np.load(c_dir / "mask.npy")
        xp_full = np.load(c_dir / f"P_seed{seed}.npy")
        xz_full = np.load(c_dir / f"Z_seed{seed}.npy")

        begin, end, cut = mas.PHASES[phase]
        use = (a_full >= begin) & (a_full < end)
        aa, yy, mm, bb = a_full[use], y_full[use], m_full[use], b_full[use]

        for arm in ("C", "P", "Z"):
            xx = xz_full[use] if arm == "Z" else xp_full[use]
            feat_3d = build_meta_features(bb, xx, aa, arm)
            ref_led, counts, days = score_actions(xp_full[use][:, :, 0], yy, mm, aa)
            ledgers = np.zeros((24, len(days), 4), dtype=np.float64)
            act_hashes = {}
            status = {}

            for r in recipes:
                rid = int(r["id"])
                m_rel = f"models/{phase}/{arm}_seed{seed}/M{rid:03d}.joblib"
                r_rel = f"models/{phase}/{arm}_seed{seed}/M{rid:03d}_receipt.json"
                bundle = dict(
                    schema="residual-meta-head-v1",
                    kind="hgbr_quantile",
                    fallback_to_anchor=(rid == 23),
                    status="FIT_ERROR_DECLARED_ANCHOR_FALLBACK" if rid == 23 else "FITTED_OK",
                    fit_success=(rid != 23),
                    optimality_certified=False,
                    arm=arm,
                    seed=seed,
                    recipe_id=rid,
                    phase=phase,
                    fit_window=[27648, int(cut)],
                    episode_start=int(begin),
                    last_label_release=int(cut) - 1 + 7,
                    source_manifest_sha256=hist_manifest_sha,
                    parent_profile_sha256=sha(p_hist),
                    feature_names=list(feature_names_for_arm(arm)),
                    n_features=len(feature_names_for_arm(arm)),
                    estimator=None if rid == 23 else LinearOffsetFakeModel(rid),
                )
                save_meta_model(parent_res / m_rel, bundle)
                m_digest = sha(parent_res / m_rel)
                rcpt_payload = dict(
                    recipe_id=rid,
                    phase=phase,
                    seed=seed,
                    arm=arm,
                    status=bundle["status"],
                    fit_success=bundle["fit_success"],
                    optimality_certified=False,
                    fallback_to_anchor=bundle["fallback_to_anchor"],
                    fit_window=[27648, int(cut)],
                    episode_start=int(begin),
                    last_label_release=int(cut) - 1 + 7,
                    model_path=m_rel,
                    model_sha256=m_digest,
                    source_manifest_sha256=hist_manifest_sha,
                    parent_profile_sha256=sha(p_hist),
                )
                save(parent_res / r_rel, rcpt_payload)
                all_models[m_rel] = m_digest
                all_rcpts[r_rel] = sha(parent_res / r_rel)

                act, _ = predict_residual_meta_actions(bundle, feat_3d, bb)
                led, _, _ = score_actions(act, yy, mm, aa)
                ledgers[rid] = led
                act_hashes[str(rid)] = prefix_sha256(act)
                status[str(rid)] = "COMPLETED"

            inst_dir = parent_res / "instances" / phase / f"{arm}_seed{seed}"
            inst_dir.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(inst_dir / "daily.npz", ledger=ledgers, reference=ref_led, counts=counts, days=days)
            save(
                inst_dir / "receipt.json",
                dict(
                    phase=phase,
                    seed=seed,
                    arm=arm,
                    ids=list(range(24)),
                    status=status,
                    action_sha256=act_hashes,
                    source_manifest_sha256=m_sha_expected,
                    parent_profile_sha256=p_sha,
                    complete_expected=24,
                    completed=24,
                ),
            )

    freeze_payload = dict(
        study_id="residual_meta_20261024_v1",
        protocol_sha256=proto_sha,
        source_versions=source_hashes,
        historical_manifest_sha256=hist_manifest_sha,
        evaluation_manifest_sha256=eval_manifest_sha,
        recipes=recipes,
        all_models=all_models,
        all_model_receipts=all_rcpts,
    )
    save(parent_res / "FINAL_FREEZE.json", freeze_payload)
    save(
        parent_res / "EVALUATION_OPEN.json",
        dict(freeze_sha256=sha(parent_res / "FINAL_FREEZE.json"), protocol_sha256=proto_sha),
    )
    return parent_res, tmp_path, cfg


def test_build_phase_bank_all_arms_24_hashes_and_eval_cache_isolation(tmp_path, monkeypatch):
    parent_res, root, cfg = _build_tiny_parent_fixture(tmp_path, monkeypatch)

    # Guard evaluation cache during inner and outer phase bank construction
    eval_cache_dir = Path(cfg["evaluation_cache"]).resolve()
    real_np_load = np.load

    def guarded_load(file, *args, **kwargs):
        p = Path(file).resolve()
        if p == eval_cache_dir or eval_cache_dir in p.parents:
            raise AssertionError(f"Future evaluation cache accessed during historical phase: {p}")
        return real_np_load(file, *args, **kwargs)

    monkeypatch.setattr(np, "load", guarded_load)
    bank_inner_c = build_phase_bank(parent_res, "inner", 201, "C", root=root)
    bank_inner_p = build_phase_bank(parent_res, "inner", 201, "P", root=root)
    bank_outer_p = build_phase_bank(parent_res, "outer", 201, "P", root=root)
    monkeypatch.setattr(np, "load", real_np_load)

    bank_eval_z = build_phase_bank(parent_res, "evaluate", 201, "Z", root=root)

    assert bank_inner_c["raw_actions"].shape == (24, 3, 2)
    assert bank_eval_z["raw_actions"].shape == (24, 4, 2)
    assert not bank_inner_p["raw_actions"].flags.writeable
    assert not bank_inner_p["anchors"].flags.writeable

    # Verify all 24 rebuilt raw action SHA-256 digests match parent receipt
    inst_rcpt = json.loads((parent_res / "instances/inner/P_seed201/receipt.json").read_text(encoding="utf-8"))
    for rid in range(24):
        key = str(rid)
        assert prefix_sha256(bank_inner_p["raw_actions"][rid]) == inst_rcpt["action_sha256"][key]
        assert bank_inner_p["metadata"]["raw_action_sha256"][key] == inst_rcpt["action_sha256"][key]

    # Recipe 23 is anchor fallback -> equals causal baseline b (4.0 on historical)
    np.testing.assert_array_equal(bank_inner_p["raw_actions"][23], 4.0)
    # Common REF expert 0 is identical between C and P
    np.testing.assert_array_equal(bank_inner_c["reference"], bank_inner_p["reference"])


def test_future_labels_and_masks_do_not_enter_features_or_actions(tmp_path, monkeypatch):
    parent_res, root, cfg = _build_tiny_parent_fixture(tmp_path, monkeypatch)
    seen_features = []
    real_predict = mas.predict_residual_meta_actions

    def spy_predict(bundle, features_3d, b):
        seen_features.append(np.array(features_3d, copy=True))
        return real_predict(bundle, features_3d, b)

    monkeypatch.setattr(mas, "predict_residual_meta_actions", spy_predict)
    bank1 = build_phase_bank(parent_res, "inner", 201, "C", root=root)
    assert len(seen_features) == 24
    assert seen_features[0].shape == (3, 2, 5)

    # Mutate shortfall labels and masks in historical cache and update cache manifest + daily.npz reference
    hist_cache = Path(cfg["historical_cache"])
    y_mod = np.nan_to_num(np.load(hist_cache / "shortfall.npy"), nan=0.0) + 500.0
    m_mod = np.ones_like(y_mod, dtype=bool)
    np.save(hist_cache / "shortfall.npy", y_mod)
    np.save(hist_cache / "mask.npy", m_mod)
    files = {p.name: dict(bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(hist_cache.glob("*.npy"))}
    save(hist_cache / "manifest.json", dict(files=files))
    new_hist_sha = sha(hist_cache / "manifest.json")

    # Update manifest sha in protocol/freeze/receipts and daily reference to isolate feature/action invariance
    cfg["historical_manifest_sha256"] = new_hist_sha
    raw_lf = json.dumps(cfg, indent=2) + "\n"
    (parent_res / "protocol_original.json").write_bytes(raw_lf.replace("\n", "\r\n").encode("utf-8"))
    (parent_res / "protocol.json").write_bytes(raw_lf.encode("utf-8"))
    p_sha = sha(parent_res / "protocol_original.json")

    ha = np.load(hist_cache / "anchors.npy")
    xp = np.load(hist_cache / "P_seed201.npy")
    use = (ha >= 28087) & (ha < 28090)
    ref_led, counts, days = score_actions(xp[use][:, :, 0], y_mod[use], m_mod[use], ha[use])
    d_path = parent_res / "instances/inner/C_seed201/daily.npz"
    old_d = np.load(d_path)
    np.savez_compressed(d_path, ledger=old_d["ledger"], reference=ref_led, counts=counts, days=days)

    ir_path = parent_res / "instances/inner/C_seed201/receipt.json"
    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    ir["source_manifest_sha256"] = new_hist_sha
    save(ir_path, ir)

    freeze = json.loads((parent_res / "FINAL_FREEZE.json").read_text(encoding="utf-8"))
    freeze["protocol_sha256"] = p_sha
    freeze["historical_manifest_sha256"] = new_hist_sha
    for rid in range(24):
        m_rel = f"models/inner/C_seed201/M{rid:03d}.joblib"
        r_rel = f"models/inner/C_seed201/M{rid:03d}_receipt.json"
        b_mod = mas.load_meta_model(parent_res / m_rel)
        b_mod["source_manifest_sha256"] = new_hist_sha
        save_meta_model(parent_res / m_rel, b_mod)
        r_mod = json.loads((parent_res / r_rel).read_text(encoding="utf-8"))
        r_mod["source_manifest_sha256"] = new_hist_sha
        r_mod["model_sha256"] = sha(parent_res / m_rel)
        save(parent_res / r_rel, r_mod)
        freeze["all_models"][m_rel] = sha(parent_res / m_rel)
        freeze["all_model_receipts"][r_rel] = sha(parent_res / r_rel)
    save(parent_res / "FINAL_FREEZE.json", freeze)
    save(parent_res / "EVALUATION_OPEN.json", dict(freeze_sha256=sha(parent_res / "FINAL_FREEZE.json"), protocol_sha256=p_sha))

    seen_features.clear()
    bank2 = build_phase_bank(parent_res, "inner", 201, "C", root=root)
    np.testing.assert_array_equal(bank1["raw_actions"], bank2["raw_actions"])


def test_tampered_protocol_bytes_or_action_hash_or_wrong_model_time_fails(tmp_path, monkeypatch):
    parent_res, root, _ = _build_tiny_parent_fixture(tmp_path, monkeypatch)

    # 1. Tamper protocol_original.json bytes (convert CRLF -> LF so JSON semantics match but byte SHA differs)
    orig_bytes = (parent_res / "protocol_original.json").read_bytes()
    (parent_res / "protocol_original.json").write_bytes((parent_res / "protocol.json").read_bytes())
    with pytest.raises(ValueError, match="protocol_original.json byte SHA-256 differs"):
        build_phase_bank(parent_res, "inner", 201, "P", root=root)
    (parent_res / "protocol_original.json").write_bytes(orig_bytes)

    # 2. Tamper parent receipt action_sha256 -> fails verification
    rcpt_path = parent_res / "instances/inner/P_seed201/receipt.json"
    orig_rcpt = rcpt_path.read_bytes()
    rcpt_data = json.loads(orig_rcpt.decode("utf-8"))
    rcpt_data["action_sha256"]["17"] = "0" * 64
    save(rcpt_path, rcpt_data)
    with pytest.raises(ValueError, match="Rebuilt raw action SHA-256 mismatch for recipe 17"):
        build_phase_bank(parent_res, "inner", 201, "P", root=root)
    rcpt_path.write_bytes(orig_rcpt)

    # 3. Wrong model maturity time (last_label_release >= episode_start) fails even if freeze hashes match
    r0_path = parent_res / "models/inner/P_seed201/M000_receipt.json"
    orig_r0 = r0_path.read_bytes()
    r0_data = json.loads(orig_r0.decode("utf-8"))
    r0_data["last_label_release"] = 28087  # == episode_start (violates strict <)
    save(r0_path, r0_data)
    freeze_path = parent_res / "FINAL_FREEZE.json"
    open_path = parent_res / "EVALUATION_OPEN.json"
    orig_freeze = freeze_path.read_bytes()
    orig_open = open_path.read_bytes()
    freeze_data = json.loads(orig_freeze.decode("utf-8"))
    freeze_data["all_model_receipts"]["models/inner/P_seed201/M000_receipt.json"] = sha(r0_path)
    save(freeze_path, freeze_data)
    save(open_path, dict(freeze_sha256=sha(freeze_path), protocol_sha256=freeze_data["protocol_sha256"]))
    with pytest.raises(ValueError, match="Model maturity clock violation"):
        build_phase_bank(parent_res, "inner", 201, "P", root=root)
    r0_path.write_bytes(orig_r0)
    freeze_path.write_bytes(orig_freeze)
    open_path.write_bytes(orig_open)


def test_join_banks_preserves_7_step_gaps_rejects_overlap_and_save_load_identity(tmp_path, monkeypatch):
    parent_res, root, cfg = _build_tiny_parent_fixture(tmp_path, monkeypatch)
    hist_cache = Path(cfg["historical_cache"])
    eval_cache = Path(cfg["evaluation_cache"])
    orig_hist_y = np.load(hist_cache / "shortfall.npy")
    orig_eval_y = np.load(eval_cache / "shortfall.npy")

    b_inner = build_phase_bank(parent_res, "inner", 201, "P", root=root)
    b_outer = build_phase_bank(parent_res, "outer", 201, "P", root=root)
    b_eval = build_phase_bank(parent_res, "evaluate", 201, "P", root=root)

    assert np.isnan(b_inner["shortfall"][1, 1]) and not b_inner["mask"][1, 1]
    assert np.isnan(b_outer["shortfall"][1, 0]) and not b_outer["mask"][1, 0]
    assert np.isnan(b_eval["shortfall"][1, 0]) and not b_eval["mask"][1, 0]
    assert b_inner["shortfall"].tobytes() == np.ascontiguousarray(orig_hist_y[2:5], dtype=np.float64).tobytes()
    assert b_outer["shortfall"].tobytes() == np.ascontiguousarray(orig_hist_y[5:8], dtype=np.float64).tobytes()
    assert b_eval["shortfall"].tobytes() == np.ascontiguousarray(orig_eval_y, dtype=np.float64).tobytes()

    # First inner issue is 28087; gap between inner end (28089) and outer start (28097) is preserved!
    b_hist = join_banks([b_inner, b_outer])
    assert int(b_hist["anchors"][0]) == 28087
    np.testing.assert_array_equal(b_hist["anchors"], np.array([28087, 28088, 28089, 28097, 28098, 28099]))
    assert b_hist["raw_actions"].shape == (24, 6, 2)

    b_full = join_banks([b_hist, b_eval])
    assert b_full["raw_actions"].shape == (24, 10, 2)
    assert int(b_full["anchors"][5]) == 28099 and int(b_full["anchors"][6]) == 30240

    # Reject out-of-order or duplicate/overlapping banks (join_banks never sorts or reindexes)
    with pytest.raises(ValueError, match="Non-increasing or overlapping bank boundary"):
        join_banks([b_outer, b_inner])
    with pytest.raises(ValueError, match="Non-increasing or overlapping bank boundary"):
        join_banks([b_inner, b_inner])

    # Reject internal duplicate anchors
    bad_bank = dict(b_inner, anchors=np.array([28087, 28087, 28089], dtype=np.int64))
    with pytest.raises(ValueError, match="strictly increasing"):
        join_banks([bad_bank])

    # Save and load identity + refuse overwrite + preserve exact masked NaN target/mask bytes and 24 raw SHAs
    bank_dir = tmp_path / "saved_bank"
    manifest = save_bank(bank_dir, b_hist)
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        save_bank(bank_dir, b_hist)

    loaded = load_bank(bank_dir, expected_npz_sha256=manifest["npz_sha256"])
    np.testing.assert_array_equal(loaded["anchors"], b_hist["anchors"])
    np.testing.assert_array_equal(loaded["raw_actions"], b_hist["raw_actions"])
    np.testing.assert_array_equal(loaded["reference"], b_hist["reference"])
    np.testing.assert_array_equal(loaded["shortfall"], b_hist["shortfall"])
    np.testing.assert_array_equal(loaded["mask"], b_hist["mask"])
    assert loaded["shortfall"].tobytes() == b_hist["shortfall"].tobytes()
    assert loaded["mask"].tobytes() == b_hist["mask"].tobytes()
    assert np.isnan(loaded["shortfall"][~loaded["mask"]]).all()
    assert len(loaded["metadata"]["raw_action_sha256"]) == 24

    # Arbitrary invalid masked target values (-999, +inf, -inf, NaN) preserve 24 raw SHAs and NONE control scores
    for alt_val in (-999.0, np.inf, -np.inf, np.nan):
        y_alt = b_inner["shortfall"].copy()
        y_alt[~b_inner["mask"]] = alt_val
        alt_dir = tmp_path / f"alt_{str(alt_val).replace('-', 'neg')}"
        m_alt = save_bank(alt_dir, dict(b_inner, shortfall=y_alt))
        l_alt = load_bank(alt_dir, expected_npz_sha256=m_alt["npz_sha256"])
        assert l_alt["shortfall"].tobytes() == np.ascontiguousarray(y_alt, dtype=np.float64).tobytes()
        assert l_alt["metadata"]["raw_action_sha256"] == b_inner["metadata"]["raw_action_sha256"]
        assert l_alt["metadata"]["raw_actions_sha256"] == b_inner["metadata"]["raw_actions_sha256"]
        led_orig, cnt_orig, days_orig = score_actions(
            b_inner["raw_actions"][0], b_inner["shortfall"], b_inner["mask"], b_inner["anchors"]
        )
        led_alt, cnt_alt, days_alt = score_actions(
            l_alt["raw_actions"][0], l_alt["shortfall"], l_alt["mask"], l_alt["anchors"]
        )
        np.testing.assert_array_equal(led_alt, led_orig)
        np.testing.assert_array_equal(cnt_alt, cnt_orig)
        np.testing.assert_array_equal(days_alt, days_orig)

    # Valid-target NaN or negative at mask=True must still reject
    y_bad_valid_nan = b_inner["shortfall"].copy()
    y_bad_valid_nan[0, 0] = np.nan
    with pytest.raises(ValueError, match="Bank arrays must be finite"):
        save_bank(tmp_path / "bad_valid_nan.npz", dict(b_inner, shortfall=y_bad_valid_nan))
    with pytest.raises(ValueError, match="Bank arrays must be finite"):
        join_banks([dict(b_inner, shortfall=y_bad_valid_nan)])

    y_bad_valid_neg = b_inner["shortfall"].copy()
    y_bad_valid_neg[0, 0] = -0.1
    with pytest.raises(ValueError, match="must be nonnegative"):
        save_bank(tmp_path / "bad_valid_neg.npz", dict(b_inner, shortfall=y_bad_valid_neg))

    # Nonfinite or negative reference / raw_actions at mask=False must ALWAYS reject
    ref_bad_masked_nan = b_inner["reference"].copy()
    ref_bad_masked_nan[1, 1] = np.nan
    with pytest.raises(ValueError, match="Bank arrays must be finite"):
        save_bank(tmp_path / "bad_ref_nan.npz", dict(b_inner, reference=ref_bad_masked_nan))

    ref_bad_masked_neg = b_inner["reference"].copy()
    ref_bad_masked_neg[1, 1] = -1.0
    with pytest.raises(ValueError, match="must be nonnegative"):
        save_bank(tmp_path / "bad_ref_neg.npz", dict(b_inner, reference=ref_bad_masked_neg))

    raw_bad_masked_nan = b_inner["raw_actions"].copy()
    raw_bad_masked_nan[5, 1, 1] = np.nan
    with pytest.raises(ValueError, match="Bank arrays must be finite"):
        save_bank(tmp_path / "bad_raw_nan.npz", dict(b_inner, raw_actions=raw_bad_masked_nan))

    raw_bad_masked_neg = b_inner["raw_actions"].copy()
    raw_bad_masked_neg[5, 1, 1] = -0.01
    with pytest.raises(ValueError, match="must be nonnegative"):
        save_bank(tmp_path / "bad_raw_neg.npz", dict(b_inner, raw_actions=raw_bad_masked_neg))

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        load_bank(bank_dir, expected_npz_sha256="f" * 64)


def test_real_hgbr_parent_model_smoke_in_phase_bank(tmp_path, monkeypatch):
    """Smoke test using a real fitted HistGradientBoostingRegressor saved as M000 in parent models."""
    parent_res, root, _ = _build_tiny_parent_fixture(tmp_path, monkeypatch)
    rng = np.random.default_rng(20261025)
    x_train = rng.uniform(0.0, 10.0, (80, 5))
    b_train = rng.uniform(2.0, 6.0, 80)
    y_train = rng.uniform(1.0, 12.0, 80)
    bundle, _ = fit_residual_meta_head(x_train, b_train, y_train, q=0.90, leaves=7, l2=1.0, seed=201, arm="C", min_rows=64)

    m0_rel = "models/inner/C_seed201/M000.joblib"
    r0_rel = "models/inner/C_seed201/M000_receipt.json"
    old_bundle = mas.load_meta_model(parent_res / m0_rel)
    bundle.update({k: old_bundle[k] for k in ("recipe_id", "phase", "fit_window", "episode_start", "last_label_release", "source_manifest_sha256", "parent_profile_sha256")})
    save_meta_model(parent_res / m0_rel, bundle)
    m0_sha = sha(parent_res / m0_rel)

    r0 = json.loads((parent_res / r0_rel).read_text(encoding="utf-8"))
    r0["model_sha256"] = m0_sha
    save(parent_res / r0_rel, r0)

    # Recompute expected M000 action hash on inner C_seed201
    hist_cache = Path(json.loads((parent_res / "protocol.json").read_text(encoding="utf-8"))["historical_cache"])
    ha = np.load(hist_cache / "anchors.npy")
    xp = np.load(hist_cache / "P_seed201.npy")
    use = (ha >= 28087) & (ha < 28090)
    feat = build_meta_features(np.full((3, 2), 4.0), xp[use], ha[use], "C")
    act0, _ = predict_residual_meta_actions(bundle, feat, np.full((3, 2), 4.0))

    inst_r_path = parent_res / "instances/inner/C_seed201/receipt.json"
    inst_r = json.loads(inst_r_path.read_text(encoding="utf-8"))
    inst_r["action_sha256"]["0"] = prefix_sha256(act0)
    save(inst_r_path, inst_r)

    freeze = json.loads((parent_res / "FINAL_FREEZE.json").read_text(encoding="utf-8"))
    freeze["all_models"][m0_rel] = m0_sha
    freeze["all_model_receipts"][r0_rel] = sha(parent_res / r0_rel)
    save(parent_res / "FINAL_FREEZE.json", freeze)
    save(parent_res / "EVALUATION_OPEN.json", dict(freeze_sha256=sha(parent_res / "FINAL_FREEZE.json"), protocol_sha256=freeze["protocol_sha256"]))

    bank = build_phase_bank(parent_res, "inner", 201, "C", root=root)
    np.testing.assert_allclose(bank["raw_actions"][0], act0, rtol=0.0, atol=0.0)
