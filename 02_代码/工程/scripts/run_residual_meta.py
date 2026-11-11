"""Distributed multi-stage runner for the 24-config direct residual quantile meta-head campaign."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from repo_paths import Path, repository_root
import platform
import shutil
import sys
import time
import traceback

ROOT = Path(repository_root())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
import scipy
import sklearn
from threadpoolctl import threadpool_limits

from scripts.run_mixture_closed_loop import (
    PHASES,
    SEEDS,
    deadline_check,
    save,
    score_actions,
    sha,
    verify_cache,
)
from windfarm_moe.autonomous_campaign_inference import CSTAR, THRESHOLDS, infer_campaign
from windfarm_moe.residual_meta import (
    META_ARMS,
    build_meta_features,
    build_meta_recipes,
    extract_valid_fit_rows,
    feature_names_for_arm,
    fit_residual_meta_head,
    load_meta_model,
    predict_residual_meta_actions,
    save_meta_model,
    verify_common_ref_expert0,
)

POLICY_PREFIX = "MR"


def shard_assignment(shard: int) -> tuple[int, str]:
    if isinstance(shard, (bool, np.bool_)) or not isinstance(shard, int) or not 0 <= shard < 15:
        raise ValueError("Shard index must be an integer in 0..14")
    return 201 + shard // 3, META_ARMS[shard % 3]


def model_relpath(phase: str, arm: str, seed: int, recipe_id: int) -> Path:
    return Path("models") / phase / f"{arm}_seed{seed}" / f"M{int(recipe_id):03d}.joblib"


def model_receipt_relpath(phase: str, arm: str, seed: int, recipe_id: int) -> Path:
    return Path("models") / phase / f"{arm}_seed{seed}" / f"M{int(recipe_id):03d}_receipt.json"


def verify_source_hashes(cfg: dict, root: Path = ROOT) -> dict[str, str]:
    expected = cfg.get("source_hashes") or {}
    if not expected:
        raise ValueError("Protocol missing source_hashes")
    actual: dict[str, str] = {}
    for rel, exp_sha in expected.items():
        p = Path(rel)
        if not p.is_absolute():
            p = root / p
        if not p.exists():
            raise ValueError(f"Required source file missing: {p}")
        digest = sha(p)
        if digest != exp_sha:
            raise ValueError(f"Source hash mismatch for {rel}: {digest} != {exp_sha}")
        actual[str(rel)] = digest
    return actual


def _strict_int(val: object, name: str) -> int:
    if isinstance(val, (bool, np.bool_)) or not isinstance(val, (int, np.integer)):
        raise ValueError(f"Protocol {name} must be an integer, got {val!r}")
    return int(val)


def verify_budget_and_recipes(cfg: dict) -> list[dict]:
    if _strict_int(cfg.get("max_candidates"), "max_candidates") != 24 or _strict_int(
        cfg.get("max_cpu_seconds"), "max_cpu_seconds"
    ) != 28800:
        raise ValueError("Authorized 24-candidate / 28800-CPU-second budget differs")

    hist_wall = _strict_int(cfg.get("history_wall_seconds"), "history_wall_seconds")
    eval_wall = _strict_int(cfg.get("evaluation_wall_seconds"), "evaluation_wall_seconds")
    freeze_wall = _strict_int(cfg.get("freeze_wall_seconds"), "freeze_wall_seconds")
    agg_wall = _strict_int(cfg.get("aggregate_wall_seconds"), "aggregate_wall_seconds")
    audit_wall = _strict_int(cfg.get("independent_audit_wall_seconds"), "independent_audit_wall_seconds")
    reserve_wall = _strict_int(cfg.get("local_retry_reserve_seconds"), "local_retry_reserve_seconds")
    shard_compat = _strict_int(cfg.get("shard_wall_seconds", 1200), "shard_wall_seconds")
    max_jobs = _strict_int(cfg.get("maximum_science_parallel_jobs", 15), "maximum_science_parallel_jobs")

    if hist_wall != 1200:
        raise ValueError("Protocol history_wall_seconds must equal 1200")
    if eval_wall != 240:
        raise ValueError("Protocol evaluation_wall_seconds must equal 240")
    if shard_compat != 1200:
        raise ValueError("Protocol shard_wall_seconds compatibility field must equal 1200")
    if freeze_wall != 60:
        raise ValueError("Protocol freeze_wall_seconds must equal 60")
    if agg_wall != 1800:
        raise ValueError("Protocol aggregate_wall_seconds must equal 1800")
    if audit_wall != 600:
        raise ValueError("Protocol independent_audit_wall_seconds must equal 600")
    if reserve_wall != 4740:
        raise ValueError("Protocol local_retry_reserve_seconds must equal 4740")
    if max_jobs != 15:
        raise ValueError("Protocol maximum_science_parallel_jobs must equal 15")

    total_phase_cpu = 15 * hist_wall + 15 * eval_wall + freeze_wall + agg_wall + audit_wall + reserve_wall
    if total_phase_cpu != 28800 or total_phase_cpu != int(cfg["max_cpu_seconds"]):
        raise ValueError(f"Phase CPU budget sum {total_phase_cpu} != 28800")

    if "budget_reservation" in cfg:
        br = cfg["budget_reservation"]
        if not isinstance(br, dict):
            raise ValueError("Protocol budget_reservation must be a dict")
        if (
            _strict_int(br.get("new_candidates"), "budget_reservation.new_candidates") != 24
            or _strict_int(br.get("cpu_seconds"), "budget_reservation.cpu_seconds") != 28800
            or _strict_int(br.get("total_reserved_candidates"), "budget_reservation.total_reserved_candidates") != 1382
            or _strict_int(
                br.get("total_accounted_plus_open_reservations_cpu"),
                "budget_reservation.total_accounted_plus_open_reservations_cpu",
            )
            != 66219
            or _strict_int(br.get("global_cpu_limit_unchanged"), "budget_reservation.global_cpu_limit_unchanged")
            != 86400
            or not (66219 < 86400)
        ):
            raise ValueError("Protocol budget_reservation settlement values differ from authorized 66219/86400/1382")

    expected = build_meta_recipes()
    recipes = cfg.get("recipes")
    if not isinstance(recipes, list) or len(recipes) != 24:
        raise ValueError("Protocol must declare exactly 24 recipes")

    top_keys = {"id", "q", "leaves", "l2", "config"}
    for idx, (rec, exp) in enumerate(zip(recipes, expected)):
        if not isinstance(rec, dict) or set(rec.keys()) != top_keys:
            raise ValueError(f"Recipe {idx} keys do not match exact deterministic recipe schema")
        rec_cfg = rec.get("config")
        exp_cfg = exp["config"]
        if not isinstance(rec_cfg, dict) or set(rec_cfg.keys()) != set(exp_cfg.keys()):
            raise ValueError(f"Recipe {idx} config keys do not match exact deterministic config schema")
        if (
            isinstance(rec["id"], (bool, np.bool_))
            or not isinstance(rec["id"], (int, np.integer))
            or int(rec["id"]) != idx
            or isinstance(rec["leaves"], (bool, np.bool_))
            or not isinstance(rec["leaves"], (int, np.integer))
            or int(rec["leaves"]) != exp["leaves"]
            or isinstance(rec["q"], (bool, np.bool_))
            or not isinstance(rec["q"], (int, float, np.number))
            or float(rec["q"]) != exp["q"]
            or isinstance(rec["l2"], (bool, np.bool_))
            or not isinstance(rec["l2"], (int, float, np.number))
            or float(rec["l2"]) != exp["l2"]
        ):
            raise ValueError(f"Recipe {idx} does not match deterministic 24-recipe specification")
        for k, exp_val in exp_cfg.items():
            actual_val = rec_cfg[k]
            if isinstance(exp_val, bool):
                if not isinstance(actual_val, bool) or actual_val is not exp_val:
                    raise ValueError(f"Recipe {idx} config field {k}={actual_val!r} differs from {exp_val!r}")
            elif isinstance(exp_val, int):
                if isinstance(actual_val, (bool, np.bool_)) or not isinstance(actual_val, (int, np.integer)) or int(actual_val) != exp_val:
                    raise ValueError(f"Recipe {idx} config field {k}={actual_val!r} differs from {exp_val!r}")
            elif isinstance(exp_val, float):
                if isinstance(actual_val, (bool, np.bool_)) or not isinstance(actual_val, (int, float, np.number)) or float(actual_val) != exp_val:
                    raise ValueError(f"Recipe {idx} config field {k}={actual_val!r} differs from {exp_val!r}")
            else:
                if actual_val != exp_val:
                    raise ValueError(f"Recipe {idx} config field {k}={actual_val!r} differs from {exp_val!r}")
    return [dict(r, config=dict(r["config"])) for r in recipes]


def load_verified_parent_profile(cfg: dict, kind: str, seed: int) -> tuple[np.ndarray, str, Path]:
    profiles = cfg.get("parent_profiles") or {}
    if len(profiles) != 10:
        raise ValueError(f"Protocol parent_profiles must bind all 10 profile files, got {len(profiles)}")
    key1 = f"profiles/{kind}_seed{seed}.npy"
    key2 = f"{kind}_seed{seed}"
    key3 = f"{kind}_seed{seed}.npy"
    entry = profiles.get(key1) or profiles.get(key2) or profiles.get(key3)
    if not isinstance(entry, dict):
        raise ValueError(f"Missing parent profile manifest entry for {key1}")
    raw_path = Path(entry["path"])
    candidates = [raw_path]
    if "parent_results" in cfg:
        candidates.append(Path(cfg["parent_results"]) / f"profiles/{kind}_seed{seed}.npy")
    resolved = next((p for p in candidates if p.exists()), raw_path)
    if not resolved.exists():
        raise ValueError(f"Parent profile missing: {resolved}")
    if "bytes" in entry and resolved.stat().st_size != int(entry["bytes"]):
        raise ValueError(f"Parent profile byte size mismatch for {resolved}")
    digest = sha(resolved)
    if digest != entry["sha256"]:
        raise ValueError(f"Parent profile sha256 mismatch for {resolved}")
    arr = np.load(resolved)
    if not np.isfinite(arr).all() or np.any(arr < 0.0):
        raise ValueError(f"Invalid causal baseline values in {resolved}")
    return arr, digest, resolved


def _state_envelope(stage: str, shard: int | None = None, seed: int | None = None, arm: str | None = None) -> dict:
    return dict(
        status="RUNNING",
        stage=stage,
        shard=shard,
        seed=seed,
        arm=arm,
        job_id=os.environ.get("PBS_JOBID", "LOCAL_SYNTHETIC"),
        source_commit=os.environ.get("CAMPAIGN_RELEASE", "LOCAL_SYNTHETIC"),
        host=platform.node(),
        python=sys.version,
        numpy=np.__version__,
        scipy=scipy.__version__,
        sklearn=sklearn.__version__,
        joblib=joblib.__version__,
        started_utc=datetime.now(timezone.utc).isoformat(),
        clock="source_issue+7<decision_issue",
        independent_confirmation=False,
    )


def verify_protocol_cfg(cfg: dict, protocol_path: Path | None) -> None:
    if protocol_path is not None and Path(protocol_path).exists():
        original = json.loads(Path(protocol_path).read_text(encoding="utf-8"))
        if cfg != original:
            raise ValueError("Supplied cfg differs from parsed original protocol")


def _load_arm_experts_and_verify_ref0(cache: Path, seed: int, arm: str) -> tuple[np.ndarray, np.ndarray]:
    x_p = np.load(cache / f"P_seed{seed}.npy", mmap_mode="r")
    x_z = np.load(cache / f"Z_seed{seed}.npy", mmap_mode="r")
    ref0 = verify_common_ref_expert0(x_p, x_z)
    if arm == "C":
        return x_p, ref0
    if arm == "P":
        return x_p, ref0
    if arm == "Z":
        return x_z, ref0
    raise ValueError(f"Unsupported arm {arm!r}")


def _score_shard_phase(
    cfg: dict,
    out: Path,
    phase: str,
    seed: int,
    arm: str,
    recipes: list[dict],
    b_full: np.ndarray,
    profile_sha: str,
    deadline: float,
) -> dict:
    deadline_check(deadline)
    if phase == "evaluate":
        cache = Path(cfg["evaluation_cache"])
        manifest_sha = cfg["evaluation_manifest_sha256"]
    else:
        cache = Path(cfg["historical_cache"])
        manifest_sha = cfg["historical_manifest_sha256"]

    a = np.load(cache / "anchors.npy")
    y = np.load(cache / "shortfall.npy")
    m = np.load(cache / "mask.npy")
    x_full, ref0_full = _load_arm_experts_and_verify_ref0(cache, seed, arm)
    if b_full.shape != y.shape:
        raise ValueError(f"Parent profile shape {b_full.shape} differs from target shape {y.shape}")

    begin, end, _ = PHASES[phase]
    use = (a >= begin) & (a < end)
    aa = a[use]
    yy = y[use]
    mm = m[use]
    bb = np.asarray(b_full[use], dtype=np.float64)
    xx = np.asarray(x_full[use], dtype=np.float64)
    ref0_slice = np.asarray(ref0_full[use], dtype=np.float64)

    expected_len = cfg.get("expected_evaluation_anchors", 5033)
    expected_valid = cfg.get("expected_evaluation_valid_cells", 672939)
    if phase == "evaluate" and (len(aa) != expected_len or int(mm.sum()) != expected_valid):
        raise ValueError("Evaluation population differs")

    destination = out / "instances" / phase / f"{arm}_seed{seed}"
    destination.mkdir(parents=True, exist_ok=False)

    features_3d = build_meta_features(bb, xx, aa, arm)

    status: dict[str, str] = {}
    point: dict[str, list[float]] = {}
    ledgers: dict[int, np.ndarray] = {}
    hashes: dict[str, str] = {}
    metadata: dict[str, dict] = {}
    errors: dict[str, dict] = {}

    for recipe in recipes:
        deadline_check(deadline)
        rid = int(recipe["id"])
        key = str(rid)
        m_rel = model_relpath(phase, arm, seed, rid)
        r_rel = model_receipt_relpath(phase, arm, seed, rid)
        try:
            bundle = load_meta_model(out / m_rel)
            model_rec = json.loads((out / r_rel).read_text(encoding="utf-8"))
            if sha(out / m_rel) != model_rec.get("model_sha256"):
                raise ValueError(f"Serialized model hash mismatch against model receipt for {m_rel}")
            actions, pred_info = predict_residual_meta_actions(bundle, features_3d, bb)
            ledger, counts_local, days_local = score_actions(actions, yy, mm, aa)
            if ledger.shape != (len(days_local), 4) or not np.isfinite(ledger).all():
                raise ValueError("Invalid candidate ledger")
            ledgers[rid] = ledger
            point[key] = (ledger.sum(axis=0) / counts_local.sum()).tolist()
            status[key] = "COMPLETED"
            hashes[key] = hashlib.sha256(np.ascontiguousarray(actions, dtype="<f8").tobytes()).hexdigest()
            metadata[key] = dict(
                q=float(recipe["q"]),
                leaves=int(recipe["leaves"]),
                l2=float(recipe["l2"]),
                model_path=str(m_rel).replace("\\", "/"),
                model_sha256=model_rec["model_sha256"],
                fit_status=model_rec["status"],
                fit_success=bool(model_rec["fit_success"]),
                optimality_certified=bool(model_rec["optimality_certified"]),
                fallback_to_anchor=bool(model_rec["fallback_to_anchor"]),
                fit_qualified=bool(model_rec["fit_qualified"]),
                fit_indices_sha256=model_rec["fit_indices_sha256"],
                zero_clamp_count=int(pred_info["zero_clamp_count"]),
                negative_offset_count=int(pred_info["negative_offset_count"]),
                mean_predicted_residual_kw=float(pred_info["mean_predicted_residual_kw"]),
                parent_profile_sha256=profile_sha,
            )
        except Exception as exc:
            status[key] = "FAILED_PRESERVED"
            errors[key] = dict(error=repr(exc), traceback=traceback.format_exc())

    ref, counts, days = score_actions(ref0_slice, yy, mm, aa)
    ids = [int(r["id"]) for r in recipes]
    array = np.full((len(ids), len(days), 4), np.nan, dtype=np.float64)
    for i, rid in enumerate(ids):
        if rid in ledgers:
            array[i] = ledgers[rid]
        if str(rid) not in status:
            status[str(rid)] = "NOT_EVALUATED_PRESERVED"

    np.savez_compressed(destination / "daily.npz", ledger=array, reference=ref, counts=counts, days=days)
    receipt = dict(
        phase=phase,
        seed=seed,
        arm=arm,
        ids=ids,
        status=status,
        metrics=point,
        action_sha256=hashes,
        metadata=metadata,
        errors=errors,
        source_manifest_sha256=manifest_sha,
        parent_profile_sha256=profile_sha,
        complete_expected=len(recipes),
        completed=sum(v == "COMPLETED" for v in status.values()),
        scientific_qualification_used_to_filter=False,
    )
    save(destination / "receipt.json", receipt)
    return dict(
        phase=phase,
        seed=seed,
        arm=arm,
        completed=receipt["completed"],
        expected=len(recipes),
    )


def _phase_wall_seconds(cfg: dict, key: str) -> float:
    return float(_strict_int(cfg.get(key), key))


def run_history_shard(
    cfg: dict,
    out: Path,
    shard: int,
    *,
    protocol_path: Path | None = None,
    deadline: float | None = None,
    root: Path = ROOT,
) -> dict:
    out = Path(out)
    start = time.time()
    seed, arm = shard_assignment(shard)
    shard_dir = out / "shards" / "history" / f"shard_{shard:02d}_{arm}_seed{seed}"
    shard_dir.mkdir(parents=True, exist_ok=False)

    state = _state_envelope("history", shard=shard, seed=seed, arm=arm)
    save(shard_dir / "state.json", state)

    try:
        verify_protocol_cfg(cfg, protocol_path)
        recipes = verify_budget_and_recipes(cfg)
        if deadline is None:
            deadline = start + _phase_wall_seconds(cfg, "history_wall_seconds") - 30.0
        deadline_check(deadline)
        source_versions = verify_source_hashes(cfg, root=root)
        save(shard_dir / "source_versions.json", source_versions)
        if protocol_path is not None and Path(protocol_path).exists():
            shutil.copyfile(protocol_path, shard_dir / "protocol_original.json")
            protocol_sha = sha(protocol_path)
        else:
            save(shard_dir / "protocol_original.json", cfg)
            protocol_sha = sha(shard_dir / "protocol_original.json")
        save(shard_dir / "protocol.json", cfg)

        verify_cache(cfg["historical_cache"], cfg["historical_manifest_sha256"])
        hist_cache = Path(cfg["historical_cache"])
        a = np.load(hist_cache / "anchors.npy")
        y = np.load(hist_cache / "shortfall.npy")
        m = np.load(hist_cache / "mask.npy")
        expected_hist_grid = cfg.get("expected_historical_grid", True)
        if expected_hist_grid and len(a) == 2585 and not np.array_equal(a, np.arange(27648, 30233)):
            raise ValueError("Historical grid changed")

        b_hist, profile_sha, _ = load_verified_parent_profile(cfg, "historical", seed)
        if b_hist.shape != y.shape:
            raise ValueError("Historical parent profile shape mismatch")

        x_mmap, _ = _load_arm_experts_and_verify_ref0(hist_cache, seed, arm)
        model_records: list[dict] = []
        min_fit_rows = int(cfg.get("min_fit_rows", 64))

        for phase in ("inner", "outer", "evaluate"):
            deadline_check(deadline)
            begin, end, cut = PHASES[phase]
            use = (a >= 27648) & (a < cut)
            if not np.any(use) or len(a[use]) != cut - 27648 or int(a[use].max()) + 7 >= begin:
                raise ValueError("Warm-start labels are not strictly mature")
            a_fit = a[use]
            b_slice = np.asarray(b_hist[use], dtype=np.float64)
            y_slice = np.asarray(y[use], dtype=np.float64)
            m_slice = np.asarray(m[use], dtype=bool)
            x_slice = np.asarray(x_mmap[use], dtype=np.float64)
            expected_last_release = int(a_fit.max()) + 7

            try:
                feat_3d = build_meta_features(b_slice, x_slice, a_fit, arm)
                x_valid, _, b_valid, y_valid, fit_indices_sha = extract_valid_fit_rows(
                    feat_3d, b_slice, y_slice, m_slice
                )
            except Exception as prep_exc:
                x_valid = np.empty((0, len(feature_names_for_arm(arm))), dtype=np.float64)
                b_valid = np.empty((0,), dtype=np.float64)
                y_valid = np.empty((0,), dtype=np.float64)
                fit_indices_sha = hashlib.sha256(b"").hexdigest()
                prep_error = repr(prep_exc)
            else:
                prep_error = None

            for recipe in recipes:
                deadline_check(deadline)
                rid = int(recipe["id"])
                fit_start = time.monotonic()
                if prep_error is not None:
                    # Force fallback via empty x_valid
                    bundle, info = fit_residual_meta_head(
                        x_valid,
                        b_valid,
                        y_valid,
                        q=float(recipe["q"]),
                        leaves=int(recipe["leaves"]),
                        l2=float(recipe["l2"]),
                        seed=seed,
                        arm=arm,
                        min_rows=min_fit_rows,
                    )
                    info["prep_error"] = prep_error
                else:
                    bundle, info = fit_residual_meta_head(
                        x_valid,
                        b_valid,
                        y_valid,
                        q=float(recipe["q"]),
                        leaves=int(recipe["leaves"]),
                        l2=float(recipe["l2"]),
                        seed=seed,
                        arm=arm,
                        min_rows=min_fit_rows,
                    )

                m_rel = model_relpath(phase, arm, seed, rid)
                r_rel = model_receipt_relpath(phase, arm, seed, rid)
                m_path = out / m_rel
                r_path = out / r_rel

                bundle.update(
                    recipe_id=rid,
                    phase=phase,
                    fit_window=[27648, int(cut)],
                    episode_start=int(begin),
                    last_label_release=expected_last_release,
                    fit_indices_sha256=fit_indices_sha,
                    source_manifest_sha256=cfg["historical_manifest_sha256"],
                    parent_profile_sha256=profile_sha,
                )
                save_meta_model(m_path, bundle)
                m_sha = sha(m_path)

                info.update(
                    recipe_id=rid,
                    phase=phase,
                    seed=seed,
                    arm=arm,
                    q=float(recipe["q"]),
                    leaves=int(recipe["leaves"]),
                    l2=float(recipe["l2"]),
                    fit_window=[27648, int(cut)],
                    episode_start=int(begin),
                    last_label_release=expected_last_release,
                    fit_indices_sha256=fit_indices_sha,
                    model_path=str(m_rel).replace("\\", "/"),
                    model_sha256=m_sha,
                    source_manifest_sha256=cfg["historical_manifest_sha256"],
                    parent_profile_sha256=profile_sha,
                    environment=dict(
                        python=sys.version,
                        numpy=np.__version__,
                        scipy=scipy.__version__,
                        sklearn=sklearn.__version__,
                        joblib=joblib.__version__,
                    ),
                    elapsed_seconds=float(time.monotonic() - fit_start),
                )
                save(r_path, info)
                r_sha = sha(r_path)

                model_records.append(
                    dict(
                        phase=phase,
                        seed=seed,
                        arm=arm,
                        recipe_id=rid,
                        q=float(recipe["q"]),
                        leaves=int(recipe["leaves"]),
                        l2=float(recipe["l2"]),
                        path=str(m_rel).replace("\\", "/"),
                        sha256=m_sha,
                        receipt_path=str(r_rel).replace("\\", "/"),
                        receipt_sha256=r_sha,
                        fit_indices_sha256=fit_indices_sha,
                        status=info["status"],
                        fit_success=bool(info["fit_success"]),
                        optimality_certified=bool(info["optimality_certified"]),
                        fallback_to_anchor=bool(info["fallback_to_anchor"]),
                        fit_qualified=bool(info["fit_qualified"]),
                    )
                )

        assert len(model_records) == 72
        phase_summaries = []
        for phase in ("inner", "outer"):
            summary = _score_shard_phase(cfg, out, phase, seed, arm, recipes, b_hist, profile_sha, deadline)
            phase_summaries.append(summary)

        shard_receipt = dict(
            status="COMPLETED",
            stage="history",
            shard=shard,
            seed=seed,
            arm=arm,
            protocol_sha256=protocol_sha,
            source_versions=source_versions,
            historical_manifest_sha256=cfg["historical_manifest_sha256"],
            parent_profile_sha256=profile_sha,
            models_prepared=len(model_records),
            models_fitted=len(model_records),
            models=model_records,
            phase_summaries=phase_summaries,
            evaluation_cache_read=False,
            scientific_qualification_used_to_filter=False,
            elapsed_seconds=time.time() - start,
        )
        save(shard_dir / "receipt.json", shard_receipt)
        state.update(status="COMPLETED", elapsed_seconds=time.time() - start, phase_summaries=phase_summaries)
        save(shard_dir / "state.json", state)
        return shard_receipt
    except BaseException as exc:
        save(shard_dir / "failure.json", dict(error=repr(exc), traceback=traceback.format_exc()))
        state.update(status="FAILED_PRESERVED", elapsed_seconds=time.time() - start, error=repr(exc))
        save(shard_dir / "state.json", state)
        raise


def collect(out: Path, phase: str, recipes: list[dict]) -> tuple[np.ndarray, dict[tuple[int, str], np.ndarray]]:
    out = Path(out)
    points = np.full((len(recipes), len(SEEDS), len(META_ARMS), 4), np.nan, dtype=np.float64)
    ledgers: dict[tuple[int, str], np.ndarray] = {}
    for si, seed in enumerate(SEEDS):
        for ai, arm in enumerate(META_ARMS):
            folder = out / "instances" / phase / f"{arm}_seed{seed}"
            if not (folder / "daily.npz").exists() or not (folder / "receipt.json").exists():
                raise ValueError(f"Missing {phase} instance artifacts for {arm}_seed{seed}")
            d = np.load(folder / "daily.npz")
            receipt = json.loads((folder / "receipt.json").read_text(encoding="utf-8"))
            for j, recipe in enumerate(recipes):
                key = str(recipe["id"])
                if key in receipt["metrics"]:
                    points[j, si, ai] = receipt["metrics"][key]
            ledgers[seed, arm] = d["ledger"]
    return points, ledgers


def history_summary(points: np.ndarray, recipes: list[dict]) -> dict:
    complete = np.isfinite(points).all(axis=(1, 2, 3))
    roles: dict[str, dict] = {}
    for ai, arm in enumerate(META_ARMS):
        arm_complete = np.isfinite(points[:, :, ai, :]).all(axis=(1, 2))
        pool = [j for j in range(len(recipes)) if arm_complete[j]]
        if pool:
            best_c = min(pool, key=lambda j: (float(points[j, :, ai, 0].mean()), int(recipes[j]["id"])))
            best_v = min(
                pool,
                key=lambda j: (
                    float(points[j, :, ai, 3].max()),
                    float(points[j, :, ai, 2].max()),
                    float(points[j, :, ai, 0].mean()),
                    int(recipes[j]["id"]),
                ),
            )
            roles[arm] = dict(
                minimum_C_id=int(recipes[best_c]["id"]),
                minimum_maxV_id=int(recipes[best_v]["id"]),
            )
    return dict(
        roles=roles,
        complete_recipe_count=int(complete.sum()),
        all_recipes_retained=True,
        qualification_did_not_filter_instances=True,
        selection_scope="Historical outer minimum_C/minimum_maxV per arm (C/P/Z) without qualification filter; all 24 recipes still scored in evaluation",
    )


def run_freeze_stage(
    cfg: dict,
    out: Path,
    *,
    protocol_path: Path | None = None,
    deadline: float | None = None,
    root: Path = ROOT,
) -> dict:
    out = Path(out)
    stage_dir = out / "shards" / "freeze"
    if (
        (out / "FINAL_FREEZE.json").exists()
        or (out / "EVALUATION_OPEN.json").exists()
        or (stage_dir / "state.json").exists()
    ):
        raise FileExistsError("FINAL_FREEZE.json or EVALUATION_OPEN.json already exists")
    start = time.time()
    stage_dir.mkdir(parents=True, exist_ok=True)
    state = _state_envelope("freeze")
    save(stage_dir / "state.json", state)

    try:
        verify_protocol_cfg(cfg, protocol_path)
        recipes = verify_budget_and_recipes(cfg)
        if deadline is None:
            deadline = start + _phase_wall_seconds(cfg, "freeze_wall_seconds") - 30.0
        deadline_check(deadline)
        source_versions = verify_source_hashes(cfg, root=root)
        save(out / "source_versions.json", source_versions)
        if protocol_path is not None and Path(protocol_path).exists():
            if not (out / "protocol_original.json").exists():
                shutil.copyfile(protocol_path, out / "protocol_original.json")
            protocol_sha = sha(protocol_path)
        else:
            save(out / "protocol_original.json", cfg)
            protocol_sha = sha(out / "protocol_original.json")
        save(out / "protocol.json", cfg)

        shard_receipts = []
        recorded_models: dict[str, str] = {}
        recorded_model_receipts: dict[str, str] = {}
        for shard in range(15):
            seed, arm = shard_assignment(shard)
            r_path = out / "shards" / "history" / f"shard_{shard:02d}_{arm}_seed{seed}" / "receipt.json"
            if not r_path.exists():
                raise ValueError(f"Missing history shard receipt: {r_path}")
            r_data = json.loads(r_path.read_text(encoding="utf-8"))
            if r_data.get("status") != "COMPLETED" or r_data.get("models_fitted") != 72:
                raise ValueError(f"History shard {shard} did not complete all 72 models")
            if r_data.get("shard") != shard or r_data.get("seed") != seed or r_data.get("arm") != arm:
                raise ValueError(f"History shard {shard} receipt identity mismatch")
            if r_data.get("protocol_sha256") != protocol_sha:
                raise ValueError(f"History shard {shard} protocol_sha256 differs from current protocol")
            if r_data.get("source_versions") != source_versions:
                raise ValueError(f"History shard {shard} source_versions differ from current source")
            if r_data.get("historical_manifest_sha256") != cfg["historical_manifest_sha256"]:
                raise ValueError(f"History shard {shard} historical_manifest_sha256 differs from current protocol")
            models_list = r_data.get("models")
            if not isinstance(models_list, list) or len(models_list) != 72:
                raise ValueError(f"History shard {shard} receipt must record 72 models")
            for item in models_list:
                rel_key = str(item.get("path", "")).replace("\\", "/")
                rec_sha = item.get("sha256")
                rcpt_key = str(item.get("receipt_path", "")).replace("\\", "/")
                rcpt_sha = item.get("receipt_sha256")
                if not rel_key or not isinstance(rec_sha, str) or not rcpt_key or not isinstance(rcpt_sha, str):
                    raise ValueError(f"History shard {shard} receipt has invalid model entry")
                full_model = out / rel_key
                full_rcpt = out / rcpt_key
                if not full_model.exists() or not full_rcpt.exists():
                    raise ValueError(f"Missing required model or receipt: {full_model}")
                actual_sha = sha(full_model)
                if actual_sha != rec_sha:
                    raise ValueError(
                        f"Model {rel_key} sha256 mismatch against history shard {shard} receipt: {actual_sha} != {rec_sha}"
                    )
                actual_rcpt_sha = sha(full_rcpt)
                if actual_rcpt_sha != rcpt_sha:
                    raise ValueError(
                        f"Model receipt {rcpt_key} sha256 mismatch against history shard {shard} receipt: {actual_rcpt_sha} != {rcpt_sha}"
                    )
                recorded_models[rel_key] = rec_sha
                recorded_model_receipts[rcpt_key] = rcpt_sha
            shard_receipts.append(r_data)

        all_models: dict[str, str] = {}
        all_model_receipts: dict[str, str] = {}
        for phase in ("inner", "outer", "evaluate"):
            for seed in SEEDS:
                for arm in META_ARMS:
                    for recipe in recipes:
                        rid = int(recipe["id"])
                        m_rel = str(model_relpath(phase, arm, seed, rid)).replace("\\", "/")
                        r_rel = str(model_receipt_relpath(phase, arm, seed, rid)).replace("\\", "/")
                        full_m = out / m_rel
                        full_r = out / r_rel
                        if not full_m.exists() or not full_r.exists():
                            raise ValueError(f"Missing required model or receipt: {full_m}")
                        m_digest = sha(full_m)
                        r_digest = sha(full_r)
                        if m_rel not in recorded_models or recorded_models[m_rel] != m_digest:
                            raise ValueError(f"Model {m_rel} missing or mismatched in history shard receipts")
                        if r_rel not in recorded_model_receipts or recorded_model_receipts[r_rel] != r_digest:
                            raise ValueError(f"Model receipt {r_rel} missing or mismatched in history shard receipts")
                        all_models[m_rel] = m_digest
                        all_model_receipts[r_rel] = r_digest
        assert len(all_models) == 1080
        assert len(all_model_receipts) == 1080

        for phase in ("inner", "outer"):
            points, _ = collect(out, phase, recipes)
            np.save(out / f"{phase}_points.npy", points, allow_pickle=False)
            save(out / f"{phase}_selection.json", history_summary(points, recipes))

        if (out / "FINAL_FREEZE.json").exists() or (out / "EVALUATION_OPEN.json").exists():
            raise FileExistsError("FINAL_FREEZE.json or EVALUATION_OPEN.json already exists")
        freeze_payload = dict(
            time_utc=datetime.now(timezone.utc).isoformat(),
            study_id=cfg.get("study_id", "meta_relief_20261024_v1"),
            source_commit=os.environ.get("CAMPAIGN_RELEASE", "LOCAL_SYNTHETIC"),
            protocol_sha256=protocol_sha,
            source_versions=source_versions,
            historical_manifest_sha256=cfg["historical_manifest_sha256"],
            evaluation_manifest_sha256=cfg["evaluation_manifest_sha256"],
            recipes=recipes,
            historical_roles=json.loads((out / "outer_selection.json").read_text(encoding="utf-8")),
            all_models=all_models,
            all_model_receipts=all_model_receipts,
            history_shard_count=len(shard_receipts),
            selection_scope="Historical outer minimum_C/minimum_maxV per arm (C/P/Z); no qualification filter; all 24 evaluated",
        )
        with (out / "FINAL_FREEZE.json").open("x", encoding="utf-8") as f:
            json.dump(freeze_payload, f, indent=2, allow_nan=False)
            f.write("\n")
        freeze_sha = sha(out / "FINAL_FREEZE.json")
        with (out / "EVALUATION_OPEN.json").open("x", encoding="utf-8") as f:
            json.dump(
                dict(
                    time_utc=datetime.now(timezone.utc).isoformat(),
                    freeze_sha256=freeze_sha,
                    protocol_sha256=protocol_sha,
                ),
                f,
                indent=2,
            )
            f.write("\n")

        state.update(status="COMPLETED", elapsed_seconds=time.time() - start, freeze_sha256=freeze_sha)
        save(stage_dir / "state.json", state)
        return freeze_payload
    except BaseException as exc:
        save(stage_dir / "failure.json", dict(error=repr(exc), traceback=traceback.format_exc()))
        state.update(status="FAILED_PRESERVED", elapsed_seconds=time.time() - start, error=repr(exc))
        save(stage_dir / "state.json", state)
        raise


def verify_freeze_barrier(cfg: dict, out: Path, *, protocol_path: Path | None = None, root: Path = ROOT) -> dict:
    freeze_path = out / "FINAL_FREEZE.json"
    open_path = out / "EVALUATION_OPEN.json"
    if not freeze_path.exists() or not open_path.exists():
        raise ValueError("Evaluation requires both FINAL_FREEZE.json and EVALUATION_OPEN.json")
    open_data = json.loads(open_path.read_text(encoding="utf-8"))
    if sha(freeze_path) != open_data.get("freeze_sha256"):
        raise ValueError("FINAL_FREEZE.json hash does not match EVALUATION_OPEN.json")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if open_data.get("protocol_sha256") != freeze.get("protocol_sha256"):
        raise ValueError("EVALUATION_OPEN.json protocol_sha256 does not match FINAL_FREEZE.json")
    source_versions = verify_source_hashes(cfg, root=root)
    if freeze.get("source_versions") != source_versions:
        raise ValueError("Source versions changed after FINAL_FREEZE")
    if protocol_path is not None and Path(protocol_path).exists():
        if sha(protocol_path) != freeze.get("protocol_sha256"):
            raise ValueError("Protocol SHA changed after FINAL_FREEZE")
        verify_protocol_cfg(cfg, protocol_path)
    if (out / "protocol_original.json").exists():
        if sha(out / "protocol_original.json") != freeze.get("protocol_sha256"):
            raise ValueError("Frozen protocol_original.json SHA does not match FINAL_FREEZE")
        if cfg != json.loads((out / "protocol_original.json").read_text(encoding="utf-8")):
            raise ValueError("Supplied cfg differs from frozen protocol_original.json")
    return freeze


def run_evaluate_shard(
    cfg: dict,
    out: Path,
    shard: int,
    *,
    protocol_path: Path | None = None,
    deadline: float | None = None,
    root: Path = ROOT,
) -> dict:
    out = Path(out)
    start = time.time()
    seed, arm = shard_assignment(shard)
    shard_dir = out / "shards" / "evaluate" / f"shard_{shard:02d}_{arm}_seed{seed}"
    shard_dir.mkdir(parents=True, exist_ok=False)

    state = _state_envelope("evaluate", shard=shard, seed=seed, arm=arm)
    save(shard_dir / "state.json", state)

    try:
        recipes = verify_budget_and_recipes(cfg)
        if deadline is None:
            deadline = start + _phase_wall_seconds(cfg, "evaluation_wall_seconds") - 30.0
        deadline_check(deadline)
        freeze = verify_freeze_barrier(cfg, out, protocol_path=protocol_path, root=root)
        all_models = freeze.get("all_models") or {}
        all_rcpts = freeze.get("all_model_receipts") or {}
        for recipe in recipes:
            rid = int(recipe["id"])
            m_rel = str(model_relpath("evaluate", arm, seed, rid)).replace("\\", "/")
            r_rel = str(model_receipt_relpath("evaluate", arm, seed, rid)).replace("\\", "/")
            full_m = out / m_rel
            full_r = out / r_rel
            if m_rel not in all_models or not full_m.exists() or sha(full_m) != all_models[m_rel]:
                raise ValueError(f"Evaluate model missing or modified since freeze: {m_rel}")
            if r_rel not in all_rcpts or not full_r.exists() or sha(full_r) != all_rcpts[r_rel]:
                raise ValueError(f"Evaluate model receipt missing or modified since freeze: {r_rel}")

        verify_cache(cfg["evaluation_cache"], cfg["evaluation_manifest_sha256"])
        b_eval, profile_sha, _ = load_verified_parent_profile(cfg, "evaluate", seed)

        summary = _score_shard_phase(cfg, out, "evaluate", seed, arm, recipes, b_eval, profile_sha, deadline)
        shard_receipt = dict(
            status="COMPLETED",
            stage="evaluate",
            shard=shard,
            seed=seed,
            arm=arm,
            freeze_sha256=sha(out / "FINAL_FREEZE.json"),
            evaluation_manifest_sha256=cfg["evaluation_manifest_sha256"],
            parent_profile_sha256=profile_sha,
            summary=summary,
            elapsed_seconds=time.time() - start,
        )
        save(shard_dir / "receipt.json", shard_receipt)
        state.update(status="COMPLETED", elapsed_seconds=time.time() - start, summary=summary)
        save(shard_dir / "state.json", state)
        return shard_receipt
    except BaseException as exc:
        save(shard_dir / "failure.json", dict(error=repr(exc), traceback=traceback.format_exc()))
        state.update(status="FAILED_PRESERVED", elapsed_seconds=time.time() - start, error=repr(exc))
        save(shard_dir / "state.json", state)
        raise


def build_extended_family(
    parent_span3: dict,
    recipes: list[dict],
    *,
    expected_parent_policies: int | None = None,
    expected_parent_comparisons: int | None = None,
) -> tuple[list[str], list[bool], list[tuple[str, str]], list[tuple[str, str]]]:
    fd = parent_span3.get("family_definition") or {}
    parent_names = list(parent_span3.get("policy_names") or fd.get("policy_names") or [])
    parent_avail = [bool(x) for x in (parent_span3.get("available") or [])]
    if not parent_names or len(parent_names) != len(parent_avail):
        raise ValueError(
            f"Parent policy_names ({len(parent_names)}) and available ({len(parent_avail)}) mismatch"
        )
    if fd.get("policy_names") is not None and list(fd.get("policy_names")) != parent_names:
        raise ValueError("Parent family_definition.policy_names differs from top-level policy_names")
    if parent_names[0] != "REF":
        raise ValueError("Parent policy index 0 must be REF")
    if expected_parent_policies is not None and len(parent_names) != int(expected_parent_policies):
        raise ValueError(f"Expected {int(expected_parent_policies)} parent policies, got {len(parent_names)}")

    for required_parent in ("REF", "R0182_P", "GUARDED_FIXED_P"):
        if required_parent not in parent_names:
            raise ValueError(f"Parent family missing required comparator policy {required_parent!r}")

    raw_comps = fd.get("comparisons")
    if not isinstance(raw_comps, list) or not raw_comps:
        raise ValueError("Parent family_definition missing comparisons")
    if expected_parent_comparisons is not None and len(raw_comps) != int(expected_parent_comparisons):
        raise ValueError(f"Expected {int(expected_parent_comparisons)} parent comparisons, got {len(raw_comps)}")

    def map_pair(pair: list | tuple) -> tuple[str, str]:
        l, r = pair
        ln = parent_names[int(l)] if isinstance(l, int) else str(l)
        rn = parent_names[int(r)] if isinstance(r, int) else str(r)
        return (ln, rn)

    comparisons: list[tuple[str, str]] = [map_pair(p) for p in raw_comps]
    aliases: list[tuple[str, str]] = [map_pair(p) for p in (fd.get("frozen_aliases") or [])]

    names = list(parent_names)
    for r in recipes:
        rid = int(r["id"])
        for arm in META_ARMS:
            names.append(f"{POLICY_PREFIX}{rid:03d}_{arm}")

    new_pairs: list[tuple[str, str]] = []
    for r in recipes:
        rid = int(r["id"])
        for arm in META_ARMS:
            policy = f"{POLICY_PREFIX}{rid:03d}_{arm}"
            for comparator in ("REF", "R0182_P", "GUARDED_FIXED_P"):
                new_pairs.append((policy, comparator))
        # Within-config representation pairs: P vs C, Z vs C, Z vs P
        new_pairs.append((f"{POLICY_PREFIX}{rid:03d}_P", f"{POLICY_PREFIX}{rid:03d}_C"))
        new_pairs.append((f"{POLICY_PREFIX}{rid:03d}_Z", f"{POLICY_PREFIX}{rid:03d}_C"))
        new_pairs.append((f"{POLICY_PREFIX}{rid:03d}_Z", f"{POLICY_PREFIX}{rid:03d}_P"))

    assert len(new_pairs) == 288
    seen = set(comparisons)
    if len(seen) != len(comparisons):
        raise ValueError("Parent comparisons contain unexpected duplicates")
    for pair in new_pairs:
        if pair in seen:
            raise ValueError(f"Duplicate comparison pair encountered: {pair}")
        comparisons.append(pair)
        seen.add(pair)

    return names, parent_avail, aliases, comparisons


def run_aggregate_stage(
    cfg: dict,
    out: Path,
    *,
    protocol_path: Path | None = None,
    deadline: float | None = None,
    root: Path = ROOT,
    n_boot_override: int | None = None,
) -> dict:
    out = Path(out)
    start = time.time()
    stage_dir = out / "shards" / "aggregate"
    stage_dir.mkdir(parents=True, exist_ok=True)
    state = _state_envelope("aggregate")
    save(stage_dir / "state.json", state)

    try:
        recipes = verify_budget_and_recipes(cfg)
        if deadline is None:
            deadline = start + _phase_wall_seconds(cfg, "aggregate_wall_seconds") - 30.0
        deadline_check(deadline)
        freeze = verify_freeze_barrier(cfg, out, protocol_path=protocol_path, root=root)
        freeze_sha = sha(out / "FINAL_FREEZE.json")

        for shard in range(15):
            seed, arm = shard_assignment(shard)
            r_path = out / "shards" / "evaluate" / f"shard_{shard:02d}_{arm}_seed{seed}" / "receipt.json"
            if not r_path.exists():
                raise ValueError(f"Missing evaluate shard receipt: {r_path}")
            r_data = json.loads(r_path.read_text(encoding="utf-8"))
            if r_data.get("status") != "COMPLETED":
                raise ValueError(f"Evaluate shard {shard} receipt status is not COMPLETED")
            if r_data.get("shard") != shard or r_data.get("seed") != seed or r_data.get("arm") != arm:
                raise ValueError(f"Evaluate shard {shard} receipt identity mismatch")
            if r_data.get("freeze_sha256") != freeze_sha:
                raise ValueError(f"Evaluate shard {shard} freeze_sha256 does not match current FINAL_FREEZE.json")
            if r_data.get("evaluation_manifest_sha256") != cfg["evaluation_manifest_sha256"]:
                raise ValueError(f"Evaluate shard {shard} evaluation_manifest_sha256 mismatch")
            _, expected_eval_prof_sha, _ = load_verified_parent_profile(cfg, "evaluate", seed)
            if r_data.get("parent_profile_sha256") != expected_eval_prof_sha:
                raise ValueError(f"Evaluate shard {shard} parent_profile_sha256 mismatch")
            inst_r_path = out / "instances" / "evaluate" / f"{arm}_seed{seed}" / "receipt.json"
            if not inst_r_path.exists():
                raise ValueError(f"Missing evaluate instance receipt: {inst_r_path}")
            inst_r = json.loads(inst_r_path.read_text(encoding="utf-8"))
            if (
                inst_r.get("phase") != "evaluate"
                or inst_r.get("seed") != seed
                or inst_r.get("arm") != arm
                or inst_r.get("source_manifest_sha256") != cfg["evaluation_manifest_sha256"]
                or inst_r.get("parent_profile_sha256") != expected_eval_prof_sha
            ):
                raise ValueError(f"Evaluate instance receipt binding mismatch for {arm}_seed{seed}")

        parent_dir = Path(cfg["parent_results"])
        parent_ledger_path = parent_dir / "all_daily_ledger.npz"
        parent_span3_path = parent_dir / "inference_span3.json"
        if not parent_ledger_path.exists() or sha(parent_ledger_path) != cfg["parent_ledger_sha256"]:
            raise ValueError("Parent all_daily_ledger.npz missing or SHA mismatch")
        if not parent_span3_path.exists() or sha(parent_span3_path) != cfg["parent_span3_sha256"]:
            raise ValueError("Parent inference_span3.json missing or SHA mismatch")

        old_npz = np.load(parent_ledger_path)
        old_ledger = np.asarray(old_npz["ledger"], dtype=np.float64)
        old_counts = np.asarray(old_npz["counts"])
        old_days = np.asarray(old_npz["day_ids"])
        if old_ledger.ndim != 4 or old_ledger.shape[0] != 5 or old_ledger.shape[2:] != (35, 4):
            raise ValueError(f"Unexpected parent ledger shape: {old_ledger.shape}")

        parent_span3 = json.loads(parent_span3_path.read_text(encoding="utf-8"))
        fd = parent_span3.get("family_definition") or {}
        parent_names = list(parent_span3.get("policy_names") or fd.get("policy_names") or [])
        parent_raw_comps = fd.get("comparisons") or []
        parent_policy_count = len(parent_names)
        parent_comparison_count = len(parent_raw_comps)
        if old_ledger.shape[1] != parent_policy_count:
            raise ValueError(
                f"Parent ledger policy axis {old_ledger.shape[1]} differs from parent inference policy count {parent_policy_count}"
            )

        names, parent_avail, aliases, comparisons = build_extended_family(
            parent_span3,
            recipes,
            expected_parent_policies=cfg.get("expected_parent_policies", parent_policy_count),
            expected_parent_comparisons=cfg.get("expected_parent_comparisons", parent_comparison_count),
        )

        for phase in ("inner", "outer", "evaluate"):
            points, _ = collect(out, phase, recipes)
            np.save(out / f"{phase}_points.npy", points, allow_pickle=False)
            if phase != "evaluate":
                save(out / f"{phase}_selection.json", history_summary(points, recipes))

        _, eval_ledgers = collect(out, "evaluate", recipes)
        for si, seed in enumerate(SEEDS):
            for arm in META_ARMS:
                d = np.load(out / "instances" / "evaluate" / f"{arm}_seed{seed}" / "daily.npz")
                if (
                    not np.array_equal(d["counts"], old_counts)
                    or not np.array_equal(d["days"], old_days)
                    or not np.allclose(d["reference"], old_ledger[si, 0], rtol=0.0, atol=1e-8)
                ):
                    raise ValueError("Reference/target population bridge changed")

        all_ledger = old_ledger.copy()
        available = list(parent_avail)
        for j, _ in enumerate(recipes):
            for arm in META_ARMS:
                panel = np.stack([eval_ledgers[seed, arm][j] for seed in SEEDS], axis=0)
                all_ledger = np.concatenate([all_ledger, panel[:, None, :, :]], axis=1)
                available.append(bool(np.isfinite(panel).all()))

        new_policy_count = len(recipes) * len(META_ARMS)
        total_policy_count = parent_policy_count + new_policy_count
        assert new_policy_count == 72
        assert all_ledger.shape == (5, total_policy_count, 35, 4)
        assert len(names) == total_policy_count and len(available) == total_policy_count
        assert np.array_equal(all_ledger[:, :parent_policy_count], old_ledger)

        np.savez_compressed(out / "all_daily_ledger.npz", ledger=all_ledger, counts=old_counts, day_ids=old_days)
        save(
            out / "all_policy_names.json",
            dict(
                names=names,
                available=available,
                aliases=[list(p) for p in aliases],
                comparisons=[list(p) for p in comparisons],
                parent_policy_count=parent_policy_count,
                new_policy_count=new_policy_count,
                parent_comparison_count=parent_comparison_count,
                total_comparison_count=len(comparisons),
                nominal_family_size=11 * len(names) + 10 * len(comparisons),
            ),
        )

        inf_cfg = cfg.get("inference") or {}
        spans = inf_cfg.get("spans", [3, 1, 7])
        n_boot = int(n_boot_override if n_boot_override is not None else inf_cfg.get("n_boot", 20000))
        boot_seed = int(inf_cfg.get("seed", 20261022))

        for span in spans:
            deadline_check(deadline)
            with threadpool_limits(limits=1):
                result = infer_campaign(
                    all_ledger,
                    old_counts,
                    names,
                    comparisons,
                    span=int(span),
                    seed=boot_seed,
                    n_boot=n_boot,
                    cstar=CSTAR,
                    available=available,
                    aliases=aliases,
                )
            save(out / f"inference_span{span}.json", result)

        verify_freeze_barrier(cfg, out, protocol_path=protocol_path, root=root)
        verify_cache(cfg["historical_cache"], cfg["historical_manifest_sha256"])
        verify_cache(cfg["evaluation_cache"], cfg["evaluation_manifest_sha256"])

        phase_counts: dict[str, dict[str, int]] = {}
        for phase in ("inner", "outer", "evaluate"):
            completed_total = 0
            failed_total = 0
            for seed in SEEDS:
                for arm in META_ARMS:
                    r_inst = json.loads(
                        (out / "instances" / phase / f"{arm}_seed{seed}" / "receipt.json").read_text(encoding="utf-8")
                    )
                    c_count = int(r_inst["completed"])
                    e_count = int(r_inst["complete_expected"])
                    completed_total += c_count
                    failed_total += e_count - c_count
            phase_counts[phase] = dict(
                completed=completed_total,
                failed=failed_total,
                expected=len(recipes) * len(SEEDS) * len(META_ARMS),
            )

        expected_per_phase = len(recipes) * len(SEEDS) * len(META_ARMS)
        assert expected_per_phase == 360
        all_complete = all(v["completed"] == expected_per_phase and v["failed"] == 0 for v in phase_counts.values())
        completion = dict(
            status="COMPLETED_ALL_PREDEFINED_INSTANCES" if all_complete else "COMPLETED_WITH_PRESERVED_FAILURES",
            planned_recipes=len(recipes),
            planned_instances_per_phase=expected_per_phase,
            total_planned_instances=expected_per_phase * 3,
            complete_per_phase={p: v["completed"] for p, v in phase_counts.items()},
            failed_per_phase={p: v["failed"] for p, v in phase_counts.items()},
            phase_instance_accounting=phase_counts,
            all_predefined_instances_scored=all_complete,
            all_planned_instances_retained=True,
            scientific_qualification_used_to_filter=False,
            thresholds=THRESHOLDS.copy(),
            thresholds_changed=False,
            old_results_written=False,
            independent_confirmation=False,
            selection_adjusted=False,
            coverage_certified=False,
            elapsed_seconds=time.time() - start,
        )
        save(out / "completion.json", completion)
        state.update(status=completion["status"], elapsed_seconds=time.time() - start)
        save(stage_dir / "state.json", state)
        return completion
    except BaseException as exc:
        save(out / "failure.json", dict(error=repr(exc), traceback=traceback.format_exc()))
        save(stage_dir / "failure.json", dict(error=repr(exc), traceback=traceback.format_exc()))
        state.update(status="FAILED_PRESERVED", elapsed_seconds=time.time() - start, error=repr(exc))
        save(stage_dir / "state.json", state)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=("history", "freeze", "evaluate", "aggregate"), required=True)
    parser.add_argument("--shard", type=int, default=None)
    args = parser.parse_args()

    if not os.environ.get("PBS_JOBID"):
        raise RuntimeError("Bounded Metis PBS allocation required")
    if not os.environ.get("CAMPAIGN_RELEASE"):
        raise RuntimeError("Missing exact source release identity")

    cfg = json.loads(args.protocol.read_text(encoding="utf-8"))
    with threadpool_limits(limits=1):
        if args.stage == "history":
            if args.shard is None:
                raise ValueError("--shard 0..14 is required for --stage history")
            run_history_shard(cfg, args.output, args.shard, protocol_path=args.protocol)
        elif args.stage == "freeze":
            run_freeze_stage(cfg, args.output, protocol_path=args.protocol)
        elif args.stage == "evaluate":
            if args.shard is None:
                raise ValueError("--shard 0..14 is required for --stage evaluate")
            run_evaluate_shard(cfg, args.output, args.shard, protocol_path=args.protocol)
        elif args.stage == "aggregate":
            run_aggregate_stage(cfg, args.output, protocol_path=args.protocol)


if __name__ == "__main__":
    main()
