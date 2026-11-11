"""Immutable causal Meta action stream bank rebuilt from frozen parent models without new fits."""
from __future__ import annotations

import hashlib
import json
from repo_paths import Path, repository_root
from typing import Any, Sequence

import numpy as np

from scripts.run_mixture_closed_loop import PHASES, SEEDS, save, score_actions, sha, verify_cache
from windfarm_moe.residual_meta import (
    META_ARMS,
    build_meta_features,
    build_meta_recipes,
    load_meta_model,
    predict_residual_meta_actions,
    verify_common_ref_expert0,
)

ROOT = Path(__file__).resolve().parents[1]
VALID_PHASES = ("inner", "outer", "evaluate")


def prefix_sha256(actions: np.ndarray) -> str:
    """Compute canonical little-endian float64 SHA-256 digest of an action array."""
    arr = np.asarray(actions)
    if not np.isfinite(arr).all() or np.any(arr < 0.0):
        raise ValueError("Actions must be finite and nonnegative for hashing")
    return hashlib.sha256(np.ascontiguousarray(arr, dtype="<f8").tobytes()).hexdigest()


def _readonly(arr: np.ndarray, dtype: Any) -> np.ndarray:
    out = np.ascontiguousarray(arr, dtype=dtype)
    out.flags.writeable = False
    return out


def _verify_parent_freeze_and_protocol(parent_results: Path, root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    orig_path = parent_results / "protocol_original.json"
    res_path = parent_results / "protocol.json"
    freeze_path = parent_results / "FINAL_FREEZE.json"
    open_path = parent_results / "EVALUATION_OPEN.json"
    for p in (orig_path, res_path, freeze_path, open_path):
        if not p.exists():
            raise ValueError(f"Missing required parent artifact: {p}")

    orig_sha = sha(orig_path)
    freeze_sha = sha(freeze_path)
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    eval_open = json.loads(open_path.read_text(encoding="utf-8"))

    if orig_sha != freeze.get("protocol_sha256"):
        raise ValueError("Parent protocol_original.json byte SHA-256 differs from FINAL_FREEZE.protocol_sha256")
    if eval_open.get("freeze_sha256") != freeze_sha:
        raise ValueError("Parent EVALUATION_OPEN.json freeze_sha256 differs from FINAL_FREEZE.json byte SHA-256")
    if eval_open.get("protocol_sha256") != orig_sha:
        raise ValueError("Parent EVALUATION_OPEN.json protocol_sha256 differs from protocol_original.json byte SHA-256")

    cfg_orig = json.loads(orig_path.read_text(encoding="utf-8"))
    cfg_res = json.loads(res_path.read_text(encoding="utf-8"))
    if cfg_orig != cfg_res:
        raise ValueError("Parent protocol.json semantic content differs from protocol_original.json")

    expected_sources = cfg_orig.get("source_hashes") or {}
    if not expected_sources:
        raise ValueError("Parent protocol missing source_hashes")
    actual_sources: dict[str, str] = {}
    for rel, exp_sha in expected_sources.items():
        src_p = Path(rel) if Path(rel).is_absolute() else (root / rel)
        if not src_p.exists() or sha(src_p) != exp_sha:
            raise ValueError(f"Parent source hash mismatch for {rel}")
        actual_sources[str(rel)] = exp_sha
    if freeze.get("source_versions") != actual_sources:
        raise ValueError("Parent FINAL_FREEZE.source_versions differs from verified source_hashes")
    if (parent_results / "source_versions.json").exists():
        if json.loads((parent_results / "source_versions.json").read_text(encoding="utf-8")) != actual_sources:
            raise ValueError("Parent source_versions.json differs from verified source_hashes")
    if cfg_orig.get("recipes") != build_meta_recipes() or freeze.get("recipes") != build_meta_recipes():
        raise ValueError("Parent recipes differ from deterministic 24-recipe grid")
    return cfg_orig, freeze, actual_sources


def _load_parent_profile(cfg: dict[str, Any], kind: str, seed: int) -> tuple[np.ndarray, str, Path]:
    profiles = cfg.get("parent_profiles") or {}
    key = f"profiles/{kind}_seed{seed}.npy"
    entry = profiles.get(key) or profiles.get(f"{kind}_seed{seed}") or profiles.get(f"{kind}_seed{seed}.npy")
    if not isinstance(entry, dict):
        raise ValueError(f"Missing parent profile entry for {key}")
    candidates = [Path(entry["path"])]
    if "parent_results" in cfg:
        candidates.append(Path(cfg["parent_results"]) / key)
    resolved = next((p for p in candidates if p.exists()), candidates[0])
    if not resolved.exists():
        raise ValueError(f"Parent profile file missing: {resolved}")
    if "bytes" in entry and resolved.stat().st_size != int(entry["bytes"]):
        raise ValueError(f"Parent profile byte size mismatch for {resolved}")
    digest = sha(resolved)
    if digest != entry["sha256"]:
        raise ValueError(f"Parent profile SHA-256 mismatch for {resolved}")
    arr = np.load(resolved)
    if not np.isfinite(arr).all() or np.any(arr < 0.0):
        raise ValueError(f"Invalid causal baseline values in {resolved}")
    return arr, digest, resolved


def build_phase_bank(
    parent_results: Path | str,
    phase: str,
    seed: int,
    arm: str,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Rebuild immutable 24-action phase stream bank from frozen parent models without fitting."""
    parent_dir = Path(parent_results)
    if phase not in VALID_PHASES or phase not in PHASES:
        raise ValueError(f"Unsupported phase: {phase!r}")
    if isinstance(seed, (bool, np.bool_)) or int(seed) not in SEEDS:
        raise ValueError(f"Unsupported seed: {seed!r}")
    seed = int(seed)
    if arm not in META_ARMS:
        raise ValueError(f"Unsupported arm: {arm!r}")

    cfg, freeze, source_hashes = _verify_parent_freeze_and_protocol(parent_dir, root)
    is_eval = phase == "evaluate"
    cache_dir = Path(cfg["evaluation_cache"] if is_eval else cfg["historical_cache"])
    manifest_sha = str(cfg["evaluation_manifest_sha256"] if is_eval else cfg["historical_manifest_sha256"])
    verify_cache(cache_dir, manifest_sha)

    a_full = np.load(cache_dir / "anchors.npy")
    y_full = np.load(cache_dir / "shortfall.npy")
    m_full = np.load(cache_dir / "mask.npy")
    x_p = np.load(cache_dir / f"P_seed{seed}.npy", mmap_mode="r")
    x_z = np.load(cache_dir / f"Z_seed{seed}.npy", mmap_mode="r")
    ref0_full = verify_common_ref_expert0(x_p, x_z)
    x_full = x_z if arm == "Z" else x_p

    prof_kind = "evaluate" if is_eval else "historical"
    b_full, profile_sha, _ = _load_parent_profile(cfg, prof_kind, seed)
    if b_full.shape != y_full.shape:
        raise ValueError(f"Parent profile shape {b_full.shape} differs from target shape {y_full.shape}")

    begin, end, cut = PHASES[phase]
    use = (a_full >= begin) & (a_full < end)
    anchors = np.asarray(a_full[use], dtype=np.int64)
    shortfall = np.asarray(y_full[use], dtype=np.float64)
    mask = np.asarray(m_full[use], dtype=bool)
    reference = np.asarray(ref0_full[use], dtype=np.float64)
    b_slice = np.asarray(b_full[use], dtype=np.float64)
    x_slice = np.asarray(x_full[use], dtype=np.float64)

    if anchors.ndim != 1 or anchors.size == 0 or np.any(np.diff(anchors) <= 0):
        raise ValueError(f"Phase {phase} anchors must be non-empty and strictly increasing")
    if is_eval:
        exp_len = int(cfg.get("expected_evaluation_anchors", 5033))
        exp_valid = int(cfg.get("expected_evaluation_valid_cells", 672939))
        if len(anchors) != exp_len or int(mask.sum()) != exp_valid:
            raise ValueError("Evaluation population differs from expected counts")

    inst_dir = parent_dir / "instances" / phase / f"{arm}_seed{seed}"
    inst_rcpt = json.loads((inst_dir / "receipt.json").read_text(encoding="utf-8"))
    inst_daily = np.load(inst_dir / "daily.npz")
    if (
        inst_rcpt.get("phase") != phase
        or int(inst_rcpt.get("seed", -1)) != seed
        or inst_rcpt.get("arm") != arm
        or inst_rcpt.get("source_manifest_sha256") != manifest_sha
        or inst_rcpt.get("parent_profile_sha256") != profile_sha
    ):
        raise ValueError(f"Parent instance receipt identity mismatch for {phase}/{arm}_seed{seed}")

    ref_led, counts, days = score_actions(reference, shortfall, mask, anchors)
    if (
        not np.array_equal(counts, inst_daily["counts"])
        or not np.array_equal(days, inst_daily["days"])
        or not np.allclose(ref_led, inst_daily["reference"], rtol=0.0, atol=1e-8)
    ):
        raise ValueError(f"Reference/daily population mismatch against parent daily.npz for {phase}/{arm}_seed{seed}")

    features_3d = build_meta_features(b_slice, x_slice, anchors, arm)
    all_models = freeze.get("all_models") or {}
    all_rcpts = freeze.get("all_model_receipts") or {}
    recipes = build_meta_recipes()
    raw_actions = np.empty((24, anchors.shape[0], shortfall.shape[1]), dtype=np.float64)
    raw_action_shas: dict[str, str] = {}
    model_shas: dict[str, str] = {}
    model_receipt_shas: dict[str, str] = {}

    for recipe in recipes:
        rid = int(recipe["id"])
        key = str(rid)
        m_rel = f"models/{phase}/{arm}_seed{seed}/M{rid:03d}.joblib"
        r_rel = f"models/{phase}/{arm}_seed{seed}/M{rid:03d}_receipt.json"
        m_path = parent_dir / m_rel
        r_path = parent_dir / r_rel
        if not m_path.exists() or not r_path.exists():
            raise ValueError(f"Missing frozen parent model or receipt: {m_rel}")
        m_sha = sha(m_path)
        r_sha = sha(r_path)
        if all_models.get(m_rel) != m_sha or all_rcpts.get(r_rel) != r_sha:
            raise ValueError(f"Frozen model or receipt SHA mismatch against FINAL_FREEZE for {m_rel}")

        m_rcpt = json.loads(r_path.read_text(encoding="utf-8"))
        bundle = load_meta_model(m_path)
        for meta_obj in (m_rcpt, bundle):
            if (
                meta_obj.get("phase") != phase
                or int(meta_obj.get("seed", -1)) != seed
                or meta_obj.get("arm") != arm
                or int(meta_obj.get("recipe_id", -1)) != rid
                or meta_obj.get("source_manifest_sha256") != str(cfg["historical_manifest_sha256"])
            ):
                raise ValueError(f"Model metadata mismatch in {m_rel}")
            fit_win = meta_obj.get("fit_window")
            last_rel = int(meta_obj.get("last_label_release", begin))
            ep_start = int(meta_obj.get("episode_start", -1))
            if fit_win != [27648, int(cut)] or ep_start != int(begin) or last_rel >= int(begin) or last_rel != int(cut) - 1 + 7:
                raise ValueError(f"Model maturity clock violation in {m_rel}: last_release={last_rel}, begin={begin}, cut={cut}")
        if m_rcpt.get("model_sha256") != m_sha or m_rcpt.get("optimality_certified") is not False:
            raise ValueError(f"Invalid model receipt binding in {r_rel}")

        act, _ = predict_residual_meta_actions(bundle, features_3d, b_slice)
        act_sha = prefix_sha256(act)
        if inst_rcpt.get("status", {}).get(key) != "COMPLETED" or inst_rcpt.get("action_sha256", {}).get(key) != act_sha:
            raise ValueError(f"Rebuilt raw action SHA-256 mismatch for recipe {rid} in {phase}/{arm}_seed{seed}")
        raw_actions[rid] = act
        raw_action_shas[key] = act_sha
        model_shas[key] = m_sha
        model_receipt_shas[key] = r_sha

    metadata = dict(
        schema="meta-action-stream-bank-v1",
        phase=phase,
        phases=[phase],
        seed=seed,
        arm=arm,
        n_recipes=24,
        n_steps=int(anchors.shape[0]),
        n_turbines=int(shortfall.shape[1]),
        valid_cells=int(mask.sum()),
        anchor_start=int(anchors[0]),
        anchor_end=int(anchors[-1]),
        clock_rule="source_anchor+7<decision_anchor",
        parent_results=str(parent_dir),
        protocol_sha256=str(freeze["protocol_sha256"]),
        freeze_sha256=sha(parent_dir / "FINAL_FREEZE.json"),
        source_manifest_sha256=manifest_sha,
        historical_manifest_sha256=str(cfg["historical_manifest_sha256"]),
        parent_profile_sha256=profile_sha,
        source_hashes=source_hashes,
        model_sha256=model_shas,
        model_receipt_sha256=model_receipt_shas,
        raw_action_sha256=raw_action_shas,
        raw_actions_sha256=prefix_sha256(raw_actions),
        reference_sha256=prefix_sha256(reference),
        independent_confirmation=False,
    )
    return dict(
        anchors=_readonly(anchors, np.int64),
        shortfall=_readonly(shortfall, np.float64),
        mask=_readonly(mask, bool),
        reference=_readonly(reference, np.float64),
        raw_actions=_readonly(raw_actions, np.float64),
        metadata=metadata,
    )


def _validate_bank(bank: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    a = np.asarray(bank["anchors"], dtype=np.int64)
    y = np.asarray(bank["shortfall"], dtype=np.float64)
    m = np.asarray(bank["mask"], dtype=bool)
    ref = np.asarray(bank["reference"], dtype=np.float64)
    raw = np.asarray(bank["raw_actions"], dtype=np.float64)
    meta = dict(bank.get("metadata") or {})
    if a.ndim != 1 or a.size == 0 or np.any(np.diff(a) <= 0):
        raise ValueError("Bank anchors must be 1D, non-empty, and strictly increasing without duplicates")
    t_steps = a.shape[0]
    if y.ndim != 2 or y.shape[0] != t_steps or m.shape != y.shape or ref.shape != y.shape:
        raise ValueError("Bank shortfall, mask, and reference shapes must match [T, N]")
    if raw.shape != (24, t_steps, y.shape[1]):
        raise ValueError(f"Bank raw_actions shape {raw.shape} does not match (24, {t_steps}, {y.shape[1]})")
    if not (np.isfinite(ref).all() and np.isfinite(raw).all()):
        raise ValueError("Bank arrays must be finite")
    if np.any(ref < 0.0) or np.any(raw < 0.0):
        raise ValueError("Bank shortfall, reference, and raw_actions must be nonnegative")
    if not np.isfinite(y[m]).all():
        raise ValueError("Bank arrays must be finite")
    if np.any(y[m] < 0.0):
        raise ValueError("Bank shortfall, reference, and raw_actions must be nonnegative")
    return a, y, m, ref, raw, meta


def join_banks(banks: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Concatenate causal phase banks along T without sorting, reindexing, or compressing gaps."""
    if not banks:
        raise ValueError("join_banks requires at least one bank")
    validated = [_validate_bank(b) for b in banks]
    a0, y0, _, _, _, meta0 = validated[0]
    n_nodes = y0.shape[1]
    seed = meta0.get("seed")
    arm = meta0.get("arm")
    phases: list[str] = []
    segment_Boundaries: list[dict[str, Any]] = []

    for idx, (a, y, m, ref, raw, meta) in enumerate(validated):
        if y.shape[1] != n_nodes or raw.shape[0] != 24:
            raise ValueError("All joined banks must share identical (24, N) dimensions")
        if meta.get("seed") != seed or meta.get("arm") != arm:
            raise ValueError("All joined banks must share identical seed and arm")
        if idx > 0:
            prev_a = validated[idx - 1][0]
            if int(a[0]) <= int(prev_a[-1]):
                raise ValueError(f"Non-increasing or overlapping bank boundary: {int(prev_a[-1])} -> {int(a[0])}")
        phases.extend(meta.get("phases") or ([meta["phase"]] if "phase" in meta else [f"part_{idx}"]))
        segment_Boundaries.append(
            dict(
                phase=meta.get("phase", f"part_{idx}"),
                n_steps=int(a.shape[0]),
                anchor_start=int(a[0]),
                anchor_end=int(a[-1]),
                raw_action_sha256=meta.get("raw_action_sha256"),
                model_sha256=meta.get("model_sha256"),
            )
        )

    anchors = np.concatenate([v[0] for v in validated], axis=0)
    shortfall = np.concatenate([v[1] for v in validated], axis=0)
    mask = np.concatenate([v[2] for v in validated], axis=0)
    reference = np.concatenate([v[3] for v in validated], axis=0)
    raw_actions = np.concatenate([v[4] for v in validated], axis=1)
    if np.any(np.diff(anchors) <= 0):
        raise ValueError("Joined anchors are not strictly increasing")

    joined_shas = {str(rid): prefix_sha256(raw_actions[rid]) for rid in range(24)}
    metadata = dict(
        schema="meta-action-stream-bank-v1",
        phase="+".join(phases),
        phases=phases,
        seed=seed,
        arm=arm,
        n_recipes=24,
        n_steps=int(anchors.shape[0]),
        n_turbines=int(n_nodes),
        valid_cells=int(mask.sum()),
        anchor_start=int(anchors[0]),
        anchor_end=int(anchors[-1]),
        clock_rule="source_anchor+7<decision_anchor",
        segments=segment_Boundaries,
        protocol_sha256=meta0.get("protocol_sha256"),
        freeze_sha256=meta0.get("freeze_sha256"),
        source_hashes=meta0.get("source_hashes"),
        raw_action_sha256=joined_shas,
        raw_actions_sha256=prefix_sha256(raw_actions),
        reference_sha256=prefix_sha256(reference),
        independent_confirmation=False,
    )
    return dict(
        anchors=_readonly(anchors, np.int64),
        shortfall=_readonly(shortfall, np.float64),
        mask=_readonly(mask, bool),
        reference=_readonly(reference, np.float64),
        raw_actions=_readonly(raw_actions, np.float64),
        metadata=metadata,
    )


def _resolve_bank_paths(path: Path | str) -> tuple[Path, Path]:
    p = Path(path)
    if p.suffix == ".npz":
        return p, p.with_name(p.stem + "_metadata.json")
    if p.suffix == ".json":
        return p.with_suffix(".npz"), p
    return p / "bank.npz", p / "metadata.json"


def save_bank(path: Path | str, bank: dict[str, Any]) -> dict[str, Any]:
    """Save bank arrays to compressed NPZ and metadata to separate JSON; refuse overwrite."""
    a, y, m, ref, raw, meta = _validate_bank(bank)
    npz_path, meta_path = _resolve_bank_paths(path)
    if npz_path.exists() or meta_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing bank artifact: {npz_path} or {meta_path}")
    npz_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(npz_path, anchors=a, shortfall=y, mask=m, reference=ref, raw_actions=raw)
    npz_sha = sha(npz_path)
    npz_bytes = int(npz_path.stat().st_size)

    raw_shas = {str(rid): prefix_sha256(raw[rid]) for rid in range(24)}
    manifest = dict(
        meta,
        npz_file=npz_path.name,
        npz_sha256=npz_sha,
        npz_bytes=npz_bytes,
        raw_action_sha256=raw_shas,
        raw_actions_sha256=prefix_sha256(raw),
        reference_sha256=prefix_sha256(ref),
    )
    save(meta_path, manifest)
    meta_sha = sha(meta_path)
    return dict(
        npz_path=str(npz_path),
        metadata_path=str(meta_path),
        npz_sha256=npz_sha,
        npz_bytes=npz_bytes,
        metadata_sha256=meta_sha,
        raw_actions_sha256=manifest["raw_actions_sha256"],
    )


def load_bank(path: Path | str, *, expected_npz_sha256: str | None = None, expected_metadata_sha256: str | None = None) -> dict[str, Any]:
    """Load saved bank and verify NPZ/metadata SHA-256 and 24 raw action digests."""
    npz_path, meta_path = _resolve_bank_paths(path)
    if not npz_path.exists() or not meta_path.exists():
        raise FileNotFoundError(f"Missing bank NPZ or metadata JSON: {npz_path}, {meta_path}")
    if expected_metadata_sha256 is not None and sha(meta_path) != expected_metadata_sha256:
        raise ValueError("Bank metadata JSON SHA-256 mismatch")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    want_npz_sha = expected_npz_sha256 or meta.get("npz_sha256")
    if want_npz_sha is not None and sha(npz_path) != want_npz_sha:
        raise ValueError("Bank NPZ file SHA-256 mismatch")
    if "npz_bytes" in meta and npz_path.stat().st_size != int(meta["npz_bytes"]):
        raise ValueError("Bank NPZ byte size mismatch")

    with np.load(npz_path) as data:
        bank = dict(
            anchors=_readonly(data["anchors"], np.int64),
            shortfall=_readonly(data["shortfall"], np.float64),
            mask=_readonly(data["mask"], bool),
            reference=_readonly(data["reference"], np.float64),
            raw_actions=_readonly(data["raw_actions"], np.float64),
            metadata=meta,
        )
    a, y, m, ref, raw, _ = _validate_bank(bank)
    if meta.get("raw_actions_sha256") and prefix_sha256(raw) != meta["raw_actions_sha256"]:
        raise ValueError("Loaded raw_actions tensor SHA-256 mismatch")
    if meta.get("reference_sha256") and prefix_sha256(ref) != meta["reference_sha256"]:
        raise ValueError("Loaded reference array SHA-256 mismatch")
    rec_shas = meta.get("raw_action_sha256") or {}
    for rid in range(24):
        key = str(rid)
        if key in rec_shas and prefix_sha256(raw[rid]) != rec_shas[key]:
            raise ValueError(f"Loaded raw action SHA-256 mismatch for recipe {rid}")
    return bank
