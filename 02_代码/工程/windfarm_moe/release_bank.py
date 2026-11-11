"""Causal endpoint and feature bank for the prospective release test.

Reconstructs SAFE (BR009_P, common to all arms C/P/Z) and COST (MC049_{arm}),
5 current features [common_ref, safe, cost, cost - safe, width] and 6 rolling
144-issue delayed feedback features without touching evaluation data during history build.
"""
from __future__ import annotations

from collections import deque
import hashlib
import json
from repo_paths import Path, repository_root
from typing import Any, Sequence

import numpy as np

from scripts.run_meta_pool import load_verified_parent_stream_bank, select_exact_anchor_slice
from scripts.run_mixture_closed_loop import PHASES, SEEDS, save, sha, verify_cache
from windfarm_moe.actual_mixture_update import MixtureConfig
from windfarm_moe.bounded_relief import run_signed, signed_action, signed_experts
from windfarm_moe.delayed_calibration_baselines import DelayedCalibrationConfig, run_delayed_calibration
from windfarm_moe.meta_action_stream import _readonly, join_banks, prefix_sha256
from windfarm_moe.residual_meta import META_ARMS, verify_common_ref_expert0

ROOT = Path(__file__).resolve().parents[1]
RELEASE_LAG_STEPS = 7
FEEDBACK_WINDOW_STEPS = 144
SAFE_RECIPE_ID = 9
SAFE_RELIEF = 0.01
SAFE_GOAL = "COST"
SAFE_MIXTURE_CONFIG = MixtureConfig(eta=0.03, schedule_power=0.5, severity_step=1.0, cost_scale=100.0, proximity_strength=0.0)
SAFE_REPLAY_CONFIGS = (
    SAFE_MIXTURE_CONFIG,
    MixtureConfig(eta=0.3, schedule_power=0.5, severity_step=1.0, cost_scale=100.0),
    MixtureConfig(eta=0.3, schedule_power=0.5, severity_step=10.0, cost_scale=100.0),
)
COST_RECIPE_ID = 49
COST_BASE_META_ID = 12
COST_CALIBRATION_CONFIG = DelayedCalibrationConfig(method="tracker", target_event_rate=0.05, step_size=0.03)
WIDTH_LOW_META_ID = 0
WIDTH_HIGH_META_ID = 18

CURRENT_FEATURE_NAMES: tuple[str, ...] = ("common_ref", "safe", "cost", "cost_minus_safe", "width")
FEEDBACK_ONLY_FEATURE_NAMES: tuple[str, ...] = (
    "mean_c_diff_norm", "mean_10u_diff_norm", "mean_v_diff", "mean_s_norm", "q95_s_norm", "history_support_fraction",
)
FEEDBACK_FEATURE_NAMES: tuple[str, ...] = CURRENT_FEATURE_NAMES + FEEDBACK_ONLY_FEATURE_NAMES
ALL_FEATURE_NAMES: tuple[str, ...] = FEEDBACK_FEATURE_NAMES


def _nan_exact_sha256(arr: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(arr, dtype="<f8").tobytes()).hexdigest()


def _verify_nan_outside_mask_and_finite_valid(
    y: np.ndarray, mask: np.ndarray, ref_y: np.ndarray | None = None, ref_mask: np.ndarray | None = None
) -> None:
    y_arr, m_arr = np.asarray(y, dtype=np.float64), np.asarray(mask, dtype=bool)
    if y_arr.ndim != 2 or m_arr.shape != y_arr.shape:
        raise ValueError("Shortfall and mask must have matching 2D shape [T, N]")
    if not np.isfinite(y_arr[m_arr]).all() or np.any(y_arr[m_arr] < 0.0):
        raise ValueError("Valid masked shortfall cells must be finite and nonnegative")
    if ref_mask is not None and not np.array_equal(m_arr, np.asarray(ref_mask, dtype=bool)):
        raise ValueError("Mask array does not match reference mask")
    if ref_y is not None:
        ry, ay = np.asarray(ref_y, dtype="<f8"), np.asarray(y_arr, dtype="<f8")
        if ay.shape != ry.shape or ay.tobytes() != ry.tobytes():
            raise ValueError("Shortfall bytes (including NaN payload outside mask) do not match reference")


def verify_parent_campaign_freeze(
    camp_dir: Path | str, expected_freeze_sha256: str, *, input_protocol_path: Path | str | None = None, label: str = "Parent"
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    """Verify campaign FINAL_FREEZE.json, EVALUATION_OPEN.json, and semantic/byte protocol."""
    cdir = Path(camp_dir)
    if not isinstance(expected_freeze_sha256, str) or not expected_freeze_sha256:
        raise ValueError(f"{label} expected_freeze_sha256 must be a non-empty string")
    freeze_path, open_path = cdir / "FINAL_FREEZE.json", cdir / "EVALUATION_OPEN.json"
    if not freeze_path.exists() or sha(freeze_path) != expected_freeze_sha256:
        raise ValueError(f"{label} FINAL_FREEZE.json missing or SHA-256 mismatch: {freeze_path}")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if open_path.exists():
        open_data = json.loads(open_path.read_text(encoding="utf-8"))
        if open_data.get("freeze_sha256") != expected_freeze_sha256:
            raise ValueError(f"{label} EVALUATION_OPEN.json freeze_sha256 mismatch")
        if "protocol_sha256" in freeze and open_data.get("protocol_sha256") != freeze["protocol_sha256"]:
            raise ValueError(f"{label} EVALUATION_OPEN.json protocol_sha256 mismatch")

    orig_path, res_path = cdir / "protocol_original.json", cdir / "protocol.json"
    if not orig_path.exists() and not res_path.exists():
        raise ValueError(f"{label} missing protocol_original.json and protocol.json in {cdir}")
    proto_sha = freeze.get("protocol_sha256")
    if orig_path.exists() and isinstance(proto_sha, str) and proto_sha and sha(orig_path) != proto_sha:
        raise ValueError(f"{label} protocol_original.json byte SHA-256 mismatch against FINAL_FREEZE")
    if input_protocol_path is not None:
        in_p = Path(input_protocol_path)
        if not in_p.exists():
            raise ValueError(f"{label} input_protocol_path missing: {in_p}")
        if isinstance(proto_sha, str) and proto_sha and sha(in_p) != proto_sha:
            raise ValueError(f"{label} input_protocol_path byte SHA-256 mismatch against FINAL_FREEZE")
    proto_cfg = json.loads((orig_path if orig_path.exists() else res_path).read_text(encoding="utf-8"))
    if orig_path.exists() and res_path.exists() and json.loads(res_path.read_text(encoding="utf-8")) != proto_cfg:
        raise ValueError(f"{label} protocol.json semantic mismatch against protocol_original.json")
    if input_protocol_path is not None and json.loads(Path(input_protocol_path).read_text(encoding="utf-8")) != proto_cfg:
        raise ValueError(f"{label} input_protocol_path semantic mismatch against campaign protocol")
    return cdir, freeze, proto_cfg


def _load_verified_causal_profile(cfg: dict[str, Any], kind: str, seed: int) -> tuple[np.ndarray, str]:
    profiles = cfg.get("parent_profiles") or {}
    key = f"profiles/{kind}_seed{seed}.npy"
    entry = profiles.get(key) or profiles.get(f"{kind}_seed{seed}") or profiles.get(f"{kind}_seed{seed}.npy")
    if not isinstance(entry, dict):
        raise ValueError(f"Missing parent_profiles entry for {key}")
    p = Path(entry["path"])
    if not p.exists():
        raise ValueError(f"Causal parent profile missing: {p}")
    if "bytes" in entry and p.stat().st_size != int(entry["bytes"]):
        raise ValueError(f"Causal parent profile byte size mismatch: {p}")
    digest = sha(p)
    if digest != entry["sha256"]:
        raise ValueError(f"Causal parent profile SHA-256 mismatch: {p}")
    arr = np.asarray(np.load(p), dtype=np.float64)
    if arr.ndim != 2 or not np.isfinite(arr).all() or np.any(arr < 0.0):
        raise ValueError(f"Invalid causal baseline profile array in {p}")
    return arr, digest


def reconstruct_safe_phase_actions(
    cfg: dict[str, Any], safe_dir: Path, safe_freeze: dict[str, Any], phase: str, seed: int,
    bank_anchors: np.ndarray, bank_shortfall: np.ndarray, bank_mask: np.ndarray, bank_reference: np.ndarray,
    *, cache_state: dict[str, Any] | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Reconstruct common SAFE (BR009_P) actions for a single phase and verify receipt SHA."""
    is_eval = phase == "evaluate"
    kind = "evaluate" if is_eval else "historical"
    if cache_state is None or kind not in cache_state:
        cache_dir = Path(cfg["evaluation_cache"] if is_eval else cfg["historical_cache"])
        manifest_sha = str(cfg["evaluation_manifest_sha256"] if is_eval else cfg["historical_manifest_sha256"])
        verify_cache(cache_dir, manifest_sha)
        a_full = np.asarray(np.load(cache_dir / "anchors.npy"), dtype=np.int64)
        y_full = np.asarray(np.load(cache_dir / "shortfall.npy"), dtype=np.float64)
        m_full = np.asarray(np.load(cache_dir / "mask.npy"), dtype=bool)
        x_p_full = np.load(cache_dir / f"P_seed{seed}.npy", mmap_mode="r")
        x_z_full = np.load(cache_dir / f"Z_seed{seed}.npy", mmap_mode="r")
        ref0_full = verify_common_ref_expert0(x_p_full, x_z_full)
        b_full, profile_sha = _load_verified_causal_profile(cfg, kind, seed)
        if b_full.shape != y_full.shape:
            raise ValueError(f"Profile shape {b_full.shape} differs from shortfall shape {y_full.shape}")
        state = dict(
            manifest_sha=manifest_sha, profile_sha=profile_sha, a_full=a_full, y_full=y_full,
            m_full=m_full, x_p_full=x_p_full, ref0_full=ref0_full, b_full=b_full,
        )
        if cache_state is not None:
            cache_state[kind] = state
    else:
        state = cache_state[kind]

    a_full, ba = state["a_full"], np.asarray(bank_anchors, dtype=np.int64)
    idx = np.searchsorted(a_full, ba)
    if np.any(idx < 0) or np.any(idx >= a_full.size) or not np.array_equal(a_full[idx], ba):
        raise ValueError(f"Phase {phase} bank anchors do not match cache anchors")

    y_slice = np.ascontiguousarray(state["y_full"][idx], dtype=np.float64)
    m_slice = np.ascontiguousarray(state["m_full"][idx], dtype=bool)
    ref_slice = np.ascontiguousarray(state["ref0_full"][idx], dtype=np.float64)
    _verify_nan_outside_mask_and_finite_valid(bank_shortfall, bank_mask, ref_y=y_slice, ref_mask=m_slice)
    if not np.array_equal(np.asarray(bank_reference, dtype=np.float64), ref_slice):
        raise ValueError(f"Phase {phase} bank reference does not match verified common REF expert 0")

    b_slice = select_exact_anchor_slice(a_full, state["b_full"], ba)
    x_p_slice = np.ascontiguousarray(state["x_p_full"][idx], dtype=np.float64)

    init_rel = f"initializers/{phase}/P_seed{seed}/COST_d0p01.json"
    all_inits = safe_freeze.get("all_initializers") or {}
    if init_rel not in all_inits:
        raise ValueError(f"Missing {init_rel} in safe parent FINAL_FREEZE.all_initializers")
    exp_init_sha = str(all_inits[init_rel])
    init_path = safe_dir / init_rel
    if not init_path.exists() or sha(init_path) != exp_init_sha:
        raise ValueError(f"Safe initializer {init_rel} missing or SHA-256 mismatch")
    init_rec = json.loads(init_path.read_text(encoding="utf-8"))
    if (
        init_rec.get("phase") != phase or int(init_rec.get("seed", -1)) != int(seed) or init_rec.get("arm") != "P"
        or float(init_rec.get("relief", -1.0)) != SAFE_RELIEF or init_rec.get("goal") != SAFE_GOAL
        or int(init_rec.get("last_label_release", ba[0])) >= int(ba[0])
    ):
        raise ValueError(f"Safe initializer {init_rel} metadata/maturity binding mismatch")
    w0 = np.asarray(init_rec["canonical_initial"], dtype=np.float64)

    delta = signed_experts(x_p_slice, b_slice, relief=SAFE_RELIEF)
    static_act = signed_action(b_slice, delta, w0, relief=SAFE_RELIEF)
    res = run_signed(
        delta, b_slice, y_slice, m_slice, ba, SAFE_REPLAY_CONFIGS, w0,
        relief=SAFE_RELIEF, score=False, return_actions=True,
    )
    safe_act = np.ascontiguousarray(res["actions"][0], dtype=np.float64)
    n_pre = min(8, len(ba))
    if n_pre > 0 and len(ba) >= 8 and int(ba[7]) <= int(ba[0]) + RELEASE_LAG_STEPS:
        if not np.array_equal(safe_act[:n_pre], static_act[:n_pre]):
            raise ValueError(f"SAFE phase {phase} cold-start first 8 steps differ from static signed_action")

    act_sha = prefix_sha256(safe_act)
    inst_rcpt_path = safe_dir / "instances" / phase / f"P_seed{seed}" / "receipt.json"
    if not inst_rcpt_path.exists():
        raise ValueError(f"Missing safe parent instance receipt: {inst_rcpt_path}")
    inst_rcpt = json.loads(inst_rcpt_path.read_text(encoding="utf-8"))
    exp_act_sha = (inst_rcpt.get("action_sha256") or {}).get(str(SAFE_RECIPE_ID))
    if inst_rcpt.get("status", {}).get(str(SAFE_RECIPE_ID)) != "COMPLETED" or act_sha != exp_act_sha:
        raise ValueError(f"SAFE BR009_P action SHA-256 mismatch in {phase}/P_seed{seed}: {act_sha} != {exp_act_sha}")
    if phase in ("inner", "outer"):
        all_inst = safe_freeze.get("all_instance_receipts") or {}
        rel_rcpt = f"instances/{phase}/P_seed{seed}/receipt.json"
        if rel_rcpt in all_inst and sha(inst_rcpt_path) != all_inst[rel_rcpt]:
            raise ValueError(f"Safe parent historical instance receipt SHA mismatch: {rel_rcpt}")

    safe_act.flags.writeable = False
    return safe_act, dict(
        phase=phase, seed=int(seed), policy="BR009_P", recipe_id=SAFE_RECIPE_ID,
        initializer_path=init_rel, initializer_sha256=exp_init_sha, action_sha256=act_sha,
        source_manifest_sha256=state["manifest_sha"], parent_profile_sha256=state["profile_sha"],
        feedback_updates=int(res["metadata"]["feedback_updates"]),
        original_batch_shape_preserved=True,
    )


def reconstruct_cost_actions_from_banks(
    mc_dir: Path, mc_freeze: dict[str, Any], phase_banks: Sequence[dict[str, Any]], seed: int, arm: str
) -> tuple[np.ndarray, dict[str, Any]]:
    """Reconstruct COST (MC049_{arm}) continuous cold-start calibrated actions across phase_banks."""
    if not phase_banks:
        raise ValueError("At least one phase bank is required")
    phases = [str(b["metadata"]["phase"]) for b in phase_banks]
    if phases not in (["inner", "outer"], ["inner", "outer", "evaluate"]):
        raise ValueError(f"Unsupported phase sequence for COST reconstruction: {phases}")
    for idx in range(1, len(phase_banks)):
        prev_end, curr_start = int(phase_banks[idx - 1]["anchors"][-1]), int(phase_banks[idx]["anchors"][0])
        if curr_start - prev_end <= RELEASE_LAG_STEPS:
            raise ValueError(f"Joined phase banks must preserve >7 step causal gap: {prev_end} -> {curr_start}")

    joined = join_banks(phase_banks)
    raw_12 = np.asarray(joined["raw_actions"][COST_BASE_META_ID], dtype=np.float64)
    cal_res = run_delayed_calibration(
        raw_12, joined["shortfall"], joined["mask"], joined["anchors"], COST_CALIBRATION_CONFIG, save_trace=True
    )
    cost_full = np.ascontiguousarray(cal_res.actions, dtype=np.float64)
    anchors = joined["anchors"]
    first_check = min(8, len(anchors))
    if first_check > 0 and len(anchors) >= 8 and int(anchors[7]) <= int(anchors[0]) + RELEASE_LAG_STEPS:
        if not np.array_equal(cost_full[:first_check], raw_12[:first_check]):
            raise ValueError("COST MC049 cold-start first 8 steps differ from uncalibrated raw Meta 12")

    shard_key, key = f"{arm}_seed{seed}", str(COST_RECIPE_ID)
    frozen_hist_shas = ((mc_freeze.get("all_history_policy_shas") or {}).get(shard_key)) or {}
    if key not in frozen_hist_shas:
        raise ValueError(f"Missing MC049 history prefix SHA in MCV2 FINAL_FREEZE for {shard_key}")

    n_inner, n_outer = len(phase_banks[0]["anchors"]), len(phase_banks[1]["anchors"])
    n_hist = n_inner + n_outer
    hist_prefix_sha = prefix_sha256(cost_full[:n_hist])
    if hist_prefix_sha != frozen_hist_shas[key]:
        raise ValueError(f"COST MC049_{arm} history prefix SHA mismatch for {shard_key}: {hist_prefix_sha} != {frozen_hist_shas[key]}")

    phase_slices = {"inner": cost_full[:n_inner], "outer": cost_full[n_inner:n_hist]}
    if len(phase_banks) == 3:
        phase_slices["evaluate"] = cost_full[n_hist:]

    phase_action_shas: dict[str, str] = {}
    all_inst_rcpts = mc_freeze.get("all_instance_receipts") or {}
    for phase, slc in phase_slices.items():
        rcpt_rel = f"instances/{phase}/{arm}_seed{seed}/receipt.json"
        rcpt_path = mc_dir / rcpt_rel
        if not rcpt_path.exists():
            raise ValueError(f"Missing MCV2 instance receipt: {rcpt_path}")
        if phase in ("inner", "outer") and rcpt_rel in all_inst_rcpts and sha(rcpt_path) != all_inst_rcpts[rcpt_rel]:
            raise ValueError(f"MCV2 historical instance receipt SHA mismatch: {rcpt_rel}")
        rcpt = json.loads(rcpt_path.read_text(encoding="utf-8"))
        exp_sha, act_sha = (rcpt.get("action_sha256") or {}).get(key), prefix_sha256(slc)
        if rcpt.get("status", {}).get(key) != "COMPLETED" or act_sha != exp_sha:
            raise ValueError(f"COST MC049_{arm} phase {phase} action SHA mismatch for {shard_key}: {act_sha} != {exp_sha}")
        if phase == "evaluate":
            ver_pref = (rcpt.get("verified_history_prefix_sha256") or {}).get(key)
            if ver_pref and ver_pref != hist_prefix_sha:
                raise ValueError(f"MCV2 evaluate receipt verified_history_prefix_sha256 mismatch for {shard_key}")
        phase_action_shas[phase] = act_sha

    cost_full.flags.writeable = False
    return cost_full, dict(
        policy=f"MC049_{arm}", recipe_id=COST_RECIPE_ID, base_meta_id=COST_BASE_META_ID,
        calibration_config=COST_CALIBRATION_CONFIG.__dict__.copy(), history_prefix_sha256=hist_prefix_sha,
        phase_action_sha256=phase_action_shas, processed_feedback_issues=int(cal_res.processed_feedback_issues),
        observed_feedback_issues=int(cal_res.observed_feedback_issues), observed_feedback_cells=int(cal_res.observed_feedback_cells),
    )


def compute_current_features(
    reference: np.ndarray, safe: np.ndarray, cost: np.ndarray, raw_meta_0: np.ndarray, raw_meta_18: np.ndarray
) -> tuple[np.ndarray, int]:
    """Build 5 current features [common_ref, safe, cost, cost - safe, width] on the full grid."""
    ref_arr, safe_arr, cost_arr = np.asarray(reference, dtype=np.float64), np.asarray(safe, dtype=np.float64), np.asarray(cost, dtype=np.float64)
    m0_arr, m18_arr = np.asarray(raw_meta_0, dtype=np.float64), np.asarray(raw_meta_18, dtype=np.float64)
    if ref_arr.ndim != 2 or any(a.shape != ref_arr.shape for a in (safe_arr, cost_arr, m0_arr, m18_arr)):
        raise ValueError("All current feature input arrays must share identical 2D shape [T, N]")
    for name, arr in (("reference", ref_arr), ("safe", safe_arr), ("cost", cost_arr), ("raw_meta_0", m0_arr), ("raw_meta_18", m18_arr)):
        if not np.isfinite(arr).all() or np.any(arr < 0.0):
            raise ValueError(f"Current feature input {name} must be finite and nonnegative on the whole grid")
    raw_diff = m18_arr - m0_arr
    negative_crossings = int(np.count_nonzero(raw_diff < 0.0))
    width = np.maximum(raw_diff, 0.0)
    features = np.stack([ref_arr, safe_arr, cost_arr, cost_arr - safe_arr, width], axis=-1)
    if not np.isfinite(features).all():
        raise ValueError("Current features contain non-finite values")
    return _readonly(features, np.float64), negative_crossings


def compute_feedback_features(
    safe: np.ndarray, cost: np.ndarray, shortfall: np.ndarray, mask: np.ndarray, anchors: np.ndarray,
    *, window_steps: int = FEEDBACK_WINDOW_STEPS, lag_steps: int = RELEASE_LAG_STEPS,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute 6 causal delayed feedback features [T, N, 6] and feedback_release_trace [T]."""
    safe_arr, cost_arr = np.asarray(safe, dtype=np.float64), np.asarray(cost, dtype=np.float64)
    y_arr, m_arr, a_arr = np.asarray(shortfall, dtype=np.float64), np.asarray(mask, dtype=bool), np.asarray(anchors)
    if (
        safe_arr.ndim != 2 or safe_arr.shape[0] < 1 or safe_arr.shape[1] < 1
        or any(x.shape != safe_arr.shape for x in (cost_arr, y_arr, m_arr))
        or a_arr.shape != (safe_arr.shape[0],) or a_arr.dtype.kind not in "iu"
    ):
        raise ValueError("Invalid shapes or dtypes for feedback feature computation")
    a_int = np.asarray(a_arr, dtype=np.int64)
    if np.any(a_int < 0) or np.any(np.diff(a_int) <= 0):
        raise ValueError("Anchors must be nonnegative and strictly increasing")
    if not np.isfinite(safe_arr).all() or np.any(safe_arr < 0.0) or not np.isfinite(cost_arr).all() or np.any(cost_arr < 0.0):
        raise ValueError("SAFE and COST actions must be finite and nonnegative")
    _verify_nan_outside_mask_and_finite_valid(y_arr, m_arr)
    if isinstance(window_steps, (bool, np.bool_)) or int(window_steps) < 1 or isinstance(lag_steps, (bool, np.bool_)) or int(lag_steps) < 1:
        raise ValueError("window_steps and lag_steps must be positive integers")
    win, lag = int(window_steps), int(lag_steps)

    t_steps, n_nodes = safe_arr.shape
    denom_support = float(win * n_nodes)
    row_feats = np.zeros((t_steps, 6), dtype=np.float64)
    release_trace = np.full(t_steps, -1, dtype=np.int64)
    active: deque[tuple[int, int, float, float, float, float, np.ndarray]] = deque()
    cursor, last_release, total_valid = 0, -1, 0

    for i in range(t_steps):
        now = int(a_int[i])
        while cursor < i and int(a_int[cursor]) + lag < now:
            src_anchor = int(a_int[cursor])
            last_release = src_anchor + lag
            valid = m_arr[cursor]
            cnt = int(np.count_nonzero(valid))
            if cnt > 0:
                s_val, b_val, c_val = y_arr[cursor, valid], safe_arr[cursor, valid], cost_arr[cursor, valid]
                u_c, u_b = np.maximum(s_val - c_val, 0.0) / 6.0, np.maximum(s_val - b_val, 0.0) / 6.0
                c_c, c_b = c_val / 6.0 + 10.0 * u_c, b_val / 6.0 + 10.0 * u_b
                v_diff = (s_val > c_val).astype(np.float64) - (s_val > b_val).astype(np.float64)
                s_norm = np.ascontiguousarray(s_val / 100.0, dtype=np.float64)
                active.append((
                    src_anchor, cnt, float(np.sum((c_c - c_b) / 100.0)), float(np.sum(10.0 * (u_c - u_b) / 100.0)),
                    float(np.sum(v_diff)), float(np.sum(s_norm)), s_norm,
                ))
                total_valid += cnt
            cursor += 1

        cutoff = now - win
        while active and active[0][0] < cutoff:
            total_valid -= active.popleft()[1]
        if last_release >= now:
            raise AssertionError(f"Causality violation: last_release={last_release} >= now={now}")
        release_trace[i] = last_release

        if total_valid > 0:
            inv_n = 1.0 / float(total_valid)
            s_pool = np.concatenate([item[6] for item in active])
            row_feats[i, 0] = sum(item[2] for item in active) * inv_n
            row_feats[i, 1] = sum(item[3] for item in active) * inv_n
            row_feats[i, 2] = sum(item[4] for item in active) * inv_n
            row_feats[i, 3] = sum(item[5] for item in active) * inv_n
            row_feats[i, 4] = float(np.quantile(s_pool, 0.95, method="higher"))
            row_feats[i, 5] = min(float(total_valid) / denom_support, 1.0)

    feedback_3d = np.broadcast_to(row_feats[:, None, :], (t_steps, n_nodes, 6)).copy()
    if not np.isfinite(feedback_3d).all():
        raise ValueError("Feedback features contain non-finite values")
    return _readonly(feedback_3d, np.float64), _readonly(release_trace, np.int64)


def build_release_bank(
    cfg: dict[str, Any], seed: int, arm: str, include_evaluation: bool = False, root: Path = ROOT
) -> dict[str, Any]:
    """Build causal release endpoint + feature bank for history (2139) or history+evaluate (7172)."""
    if isinstance(seed, (bool, np.bool_)) or int(seed) not in SEEDS:
        raise ValueError(f"Unsupported seed: {seed!r}")
    seed = int(seed)
    if arm not in META_ARMS:
        raise ValueError(f"Unsupported arm: {arm!r}")

    mc_dir, mc_freeze, _ = verify_parent_campaign_freeze(
        cfg["stream_parent_results"], cfg["stream_parent_freeze_sha256"],
        input_protocol_path=cfg.get("stream_parent_input_protocol"), label="Stream parent MCV2",
    )
    safe_dir, safe_freeze, _ = verify_parent_campaign_freeze(
        cfg["safe_parent_results"], cfg["safe_parent_freeze_sha256"],
        input_protocol_path=cfg.get("safe_parent_input_protocol"), label="Safe parent BR",
    )

    phases = ("inner", "outer", "evaluate") if include_evaluation else ("inner", "outer")
    phase_banks: list[dict[str, Any]] = []
    stream_records: dict[str, dict[str, Any]] = {}
    safe_slices: list[np.ndarray] = []
    safe_records: dict[str, dict[str, Any]] = {}
    cache_state: dict[str, Any] = {}

    for phase in phases:
        bank, s_rec = load_verified_parent_stream_bank(mc_dir, mc_freeze, phase, seed, arm)
        phase_banks.append(bank)
        stream_records[phase] = s_rec
        safe_act, safe_info = reconstruct_safe_phase_actions(
            cfg, safe_dir, safe_freeze, phase, seed,
            bank["anchors"], bank["shortfall"], bank["mask"], bank["reference"], cache_state=cache_state,
        )
        safe_slices.append(safe_act)
        safe_records[phase] = safe_info

    if not include_evaluation and "evaluate" in cache_state:
        raise AssertionError("History build must never touch evaluation cache")

    joined = join_banks(phase_banks)
    anchors, shortfall, mask, reference = joined["anchors"], joined["shortfall"], joined["mask"], joined["reference"]
    _verify_nan_outside_mask_and_finite_valid(shortfall, mask)

    safe_full = _readonly(np.concatenate(safe_slices, axis=0), np.float64)
    cost_full, cost_info = reconstruct_cost_actions_from_banks(mc_dir, mc_freeze, phase_banks, seed, arm)
    current_features, neg_crossings = compute_current_features(
        reference, safe_full, cost_full, joined["raw_actions"][WIDTH_LOW_META_ID], joined["raw_actions"][WIDTH_HIGH_META_ID]
    )
    feedback_only_features, release_trace = compute_feedback_features(safe_full, cost_full, shortfall, mask, anchors)
    if np.any(release_trace >= anchors):
        raise AssertionError("Feedback release trace violated strict maturity < decision_anchor")
    feedback_features = _readonly(np.concatenate([current_features, feedback_only_features], axis=-1), np.float64)

    metadata = dict(
        schema="prospective-release-bank-v1", seed=seed, arm=arm, include_evaluation=bool(include_evaluation),
        phases=list(phases), n_steps=int(anchors.shape[0]), n_turbines=int(shortfall.shape[1]),
        valid_cells=int(mask.sum()), anchor_start=int(anchors[0]), anchor_end=int(anchors[-1]),
        clock_rule="source_anchor+7<decision_anchor", feedback_window_steps=FEEDBACK_WINDOW_STEPS,
        current_feature_names=list(CURRENT_FEATURE_NAMES),
        feedback_only_feature_names=list(FEEDBACK_ONLY_FEATURE_NAMES),
        feedback_feature_names=list(FEEDBACK_FEATURE_NAMES),
        all_feature_names=list(ALL_FEATURE_NAMES), width_meta_indices=[WIDTH_LOW_META_ID, WIDTH_HIGH_META_ID],
        width_negative_crossings_count=int(neg_crossings), feedback_release_trace=release_trace.tolist(),
        safe_policy="BR009_P", cost_policy=f"MC049_{arm}",
        common_incumbent_note="All arms share SAFE (BR009_P) which contains strong current power; arm C is common-incumbent information, not power-free.",
        stream_parent_results=str(mc_dir), stream_parent_freeze_sha256=str(cfg["stream_parent_freeze_sha256"]),
        safe_parent_results=str(safe_dir), safe_parent_freeze_sha256=str(cfg["safe_parent_freeze_sha256"]),
        stream_records=stream_records, safe_records=safe_records, cost_record=cost_info,
        reference_sha256=prefix_sha256(reference), safe_sha256=prefix_sha256(safe_full),
        cost_sha256=prefix_sha256(cost_full), current_features_sha256=_nan_exact_sha256(current_features),
        feedback_only_features_sha256=_nan_exact_sha256(feedback_only_features),
        feedback_features_sha256=_nan_exact_sha256(feedback_features), shortfall_raw_sha256=_nan_exact_sha256(shortfall),
        mask_sha256=hashlib.sha256(np.ascontiguousarray(mask, dtype=np.uint8).tobytes()).hexdigest(),
        anchors_sha256=hashlib.sha256(np.ascontiguousarray(anchors, dtype="<i8").tobytes()).hexdigest(),
        evaluation_touched=bool(include_evaluation), new_head_training=False, independent_confirmation=False,
    )
    return dict(
        anchors=_readonly(anchors, np.int64), shortfall=_readonly(shortfall, np.float64),
        mask=_readonly(mask, bool), reference=_readonly(reference, np.float64),
        safe=safe_full, cost=cost_full, current_features=current_features,
        feedback_only_features=feedback_only_features,
        feedback_features=feedback_features, metadata=metadata,
    )


def _validate_release_bank(bank: dict[str, Any]) -> tuple[
    np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, Any]
]:
    a = np.asarray(bank["anchors"], dtype=np.int64)
    y = np.asarray(bank["shortfall"], dtype=np.float64)
    m = np.asarray(bank["mask"], dtype=bool)
    ref = np.asarray(bank["reference"], dtype=np.float64)
    safe = np.asarray(bank["safe"], dtype=np.float64)
    cost = np.asarray(bank["cost"], dtype=np.float64)
    cur = np.asarray(bank["current_features"], dtype=np.float64)
    fb = np.asarray(bank["feedback_features"], dtype=np.float64)
    meta = dict(bank.get("metadata") or {})

    if a.ndim != 1 or a.size == 0 or np.any(a < 0) or np.any(np.diff(a) <= 0):
        raise ValueError("Release bank anchors must be 1D, nonnegative, and strictly increasing")
    t_steps = a.shape[0]
    if y.ndim != 2 or y.shape[0] != t_steps or y.shape[1] < 1:
        raise ValueError("Release bank shortfall must have 2D shape [T, N]")
    n_nodes = y.shape[1]
    if any(x.shape != (t_steps, n_nodes) for x in (m, ref, safe, cost)):
        raise ValueError("Release bank mask, reference, safe, and cost must match [T, N]")
    if cur.shape != (t_steps, n_nodes, 5) or fb.shape != (t_steps, n_nodes, 11):
        raise ValueError(f"Expected current_features [T, N, 5] and feedback_features [T, N, 11], got {cur.shape} and {fb.shape}")
    if not np.array_equal(fb[:, :, :5], cur):
        raise ValueError("feedback_features first 5 columns must match current_features")
    if "feedback_only_features" in bank and bank["feedback_only_features"] is not None:
        fbo = np.asarray(bank["feedback_only_features"], dtype=np.float64)
        if fbo.shape != (t_steps, n_nodes, 6) or not np.array_equal(fb[:, :, 5:], fbo):
            raise ValueError("feedback_only_features must have shape [T, N, 6] and match feedback_features[:, :, 5:]")
    _verify_nan_outside_mask_and_finite_valid(y, m)
    for name, arr in (("reference", ref), ("safe", safe), ("cost", cost)):
        if not np.isfinite(arr).all() or np.any(arr < 0.0):
            raise ValueError(f"Release bank {name} must be finite and nonnegative on the full grid")
    if not np.isfinite(cur).all() or not np.isfinite(fb).all():
        raise ValueError("Release bank current_features and feedback_features must be finite on the full grid")
    if "feedback_release_trace" in meta:
        trace = np.asarray(meta["feedback_release_trace"], dtype=np.int64)
        if trace.shape != (t_steps,) or np.any(trace >= a):
            raise ValueError("Invalid feedback_release_trace in metadata")
    return a, y, m, ref, safe, cost, cur, fb, meta


def _resolve_release_bank_paths(path: Path | str) -> tuple[Path, Path]:
    p = Path(path)
    if p.suffix == ".npz":
        return p, p.with_name(p.stem + "_metadata.json")
    if p.suffix == ".json":
        return p.with_suffix(".npz"), p
    return p / "release_bank.npz", p / "release_bank_metadata.json"


def save_release_bank(path: Path | str, bank: dict[str, Any]) -> dict[str, Any]:
    """Save compact release bank arrays to compressed NPZ and metadata to JSON; refuse overwrite."""
    a, y, m, ref, safe, cost, cur, fb, meta = _validate_release_bank(bank)
    npz_path, meta_path = _resolve_release_bank_paths(path)
    if npz_path.exists() or meta_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing release bank artifact: {npz_path} or {meta_path}")
    npz_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        npz_path, anchors=a, shortfall=y, mask=m, reference=ref, safe=safe, cost=cost,
        current_features=cur, feedback_features=fb,
    )
    npz_sha, npz_bytes = sha(npz_path), int(npz_path.stat().st_size)
    manifest = dict(
        meta, npz_file=npz_path.name, npz_sha256=npz_sha, npz_bytes=npz_bytes,
        reference_sha256=prefix_sha256(ref), safe_sha256=prefix_sha256(safe), cost_sha256=prefix_sha256(cost),
        current_features_sha256=_nan_exact_sha256(cur), feedback_features_sha256=_nan_exact_sha256(fb),
        shortfall_raw_sha256=_nan_exact_sha256(y),
        mask_sha256=hashlib.sha256(np.ascontiguousarray(m, dtype=np.uint8).tobytes()).hexdigest(),
        anchors_sha256=hashlib.sha256(np.ascontiguousarray(a, dtype="<i8").tobytes()).hexdigest(),
    )
    save(meta_path, manifest)
    meta_sha = sha(meta_path)
    return dict(
        npz_path=str(npz_path), metadata_path=str(meta_path), npz_sha256=npz_sha, npz_bytes=npz_bytes,
        metadata_sha256=meta_sha, safe_sha256=manifest["safe_sha256"], cost_sha256=manifest["cost_sha256"],
        current_features_sha256=manifest["current_features_sha256"], feedback_features_sha256=manifest["feedback_features_sha256"],
    )


def load_release_bank(
    path: Path | str, expected_sha256: str | None = None, expected_metadata_sha256: str | None = None
) -> dict[str, Any]:
    """Load saved release bank, verify NPZ/metadata SHA-256 and exact NaN bytes, and return read-only arrays."""
    npz_path, meta_path = _resolve_release_bank_paths(path)
    if not npz_path.exists() or not meta_path.exists():
        raise FileNotFoundError(f"Missing release bank NPZ or metadata JSON: {npz_path}, {meta_path}")
    if expected_metadata_sha256 is not None and sha(meta_path) != expected_metadata_sha256:
        raise ValueError("Release bank metadata JSON SHA-256 mismatch")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    want_npz_sha = expected_sha256 or meta.get("npz_sha256")
    if want_npz_sha is not None and sha(npz_path) != want_npz_sha:
        raise ValueError("Release bank NPZ file SHA-256 mismatch")
    if "npz_bytes" in meta and npz_path.stat().st_size != int(meta["npz_bytes"]):
        raise ValueError("Release bank NPZ byte size mismatch")

    with np.load(npz_path) as data:
        if "raw_actions" in data.files:
            raise ValueError("Release bank NPZ must not serialize 24-expert raw_actions")
        cur_loaded = _readonly(data["current_features"], np.float64)
        fb_loaded = _readonly(data["feedback_features"], np.float64)
        bank = dict(
            anchors=_readonly(data["anchors"], np.int64), shortfall=_readonly(data["shortfall"], np.float64),
            mask=_readonly(data["mask"], bool), reference=_readonly(data["reference"], np.float64),
            safe=_readonly(data["safe"], np.float64), cost=_readonly(data["cost"], np.float64),
            current_features=cur_loaded,
            feedback_only_features=_readonly(fb_loaded[:, :, 5:], np.float64) if fb_loaded.ndim == 3 and fb_loaded.shape[2] == 11 else None,
            feedback_features=fb_loaded, metadata=meta,
        )
    a, y, m, ref, safe, cost, cur, fb, _ = _validate_release_bank(bank)
    if meta.get("reference_sha256") and prefix_sha256(ref) != meta["reference_sha256"]:
        raise ValueError("Loaded reference SHA-256 mismatch")
    if meta.get("safe_sha256") and prefix_sha256(safe) != meta["safe_sha256"]:
        raise ValueError("Loaded safe SHA-256 mismatch")
    if meta.get("cost_sha256") and prefix_sha256(cost) != meta["cost_sha256"]:
        raise ValueError("Loaded cost SHA-256 mismatch")
    if meta.get("current_features_sha256") and _nan_exact_sha256(cur) != meta["current_features_sha256"]:
        raise ValueError("Loaded current_features SHA-256 mismatch")
    if meta.get("feedback_features_sha256") and _nan_exact_sha256(fb) != meta["feedback_features_sha256"]:
        raise ValueError("Loaded feedback_features SHA-256 mismatch")
    if meta.get("shortfall_raw_sha256") and _nan_exact_sha256(y) != meta["shortfall_raw_sha256"]:
        raise ValueError("Loaded shortfall exact NaN byte SHA-256 mismatch")
    if meta.get("mask_sha256") and hashlib.sha256(np.ascontiguousarray(m, dtype=np.uint8).tobytes()).hexdigest() != meta["mask_sha256"]:
        raise ValueError("Loaded mask SHA-256 mismatch")
    if meta.get("anchors_sha256") and hashlib.sha256(np.ascontiguousarray(a, dtype="<i8").tobytes()).hexdigest() != meta["anchors_sha256"]:
        raise ValueError("Loaded anchors SHA-256 mismatch")
    return bank
