"""Distributed multi-stage runner for the 24-recipe OOF static conditional pool campaign."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from repo_paths import Path, repository_root
import shutil
import sys
import time
import traceback
from typing import Any

ROOT = Path(repository_root())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from threadpoolctl import threadpool_limits

from scripts.run_meta_pool import (
    CHECKPOINT_FILENAME,
    INITIALIZER_CHECKPOINT_FILENAME,
    _checkpoint_phase_metrics,
    _exact_value_match,
    _init_checkpoint_jsonl,
    _phase_wall_seconds,
    _state_envelope,
    append_jsonl,
    load_verified_causal_profile_and_anchors,
    load_verified_parent_stream_bank,
    raw_experts_from_bank,
    resolve_meta_source_protocol,
    select_exact_anchor_slice,
    stream_metadata_relpath,
    stream_relpath,
    verify_parent_bindings,
)
from scripts.run_mixture_closed_loop import (
    PHASES,
    SEEDS,
    deadline_check,
    save,
    score_actions,
    sha,
)
from scripts.run_residual_meta import (
    _strict_int,
    collect,
    shard_assignment,
    verify_protocol_cfg,
    verify_source_hashes,
)
from windfarm_moe.autonomous_campaign_inference import CSTAR, THRESHOLDS, infer_campaign
from windfarm_moe.conditional_convex_pool import (
    ALLOWED_CAP_MODES,
    ALLOWED_GROUPS,
    fit_conditional_pool,
    fit_context_cuts,
    initialize_anchor_record,
    predict_conditional_pool,
)
from windfarm_moe.meta_action_stream import join_banks, prefix_sha256
from windfarm_moe.residual_meta import META_ARMS

POLICY_PREFIX = "CP"
PARENT_POLICY_PREFIX = "MP"

GROUPS_GRID: tuple[int, ...] = ALLOWED_GROUPS
RELIEF_GRID: tuple[float, ...] = (0.01, 0.03, 0.1, 1.0)
CAP_MODES: tuple[str, ...] = ALLOWED_CAP_MODES
COMMON_COMPARATORS: tuple[str, ...] = (
    "REF",
    "R0182_P",
    "GUARDED_FIXED_P",
    "BR009_Z",
    "MP010_Z",
)


def build_conditional_pool_recipes() -> list[dict[str, Any]]:
    """Deterministic 24-recipe grid: 2 groups (1, 3) x 4 relief (0.01, 0.03, 0.1, 1.0) x 3 cap_mode."""
    recipes: list[dict[str, Any]] = []
    for groups in GROUPS_GRID:
        for relief in RELIEF_GRID:
            for cap_mode in CAP_MODES:
                recipes.append(
                    dict(
                        id=len(recipes),
                        groups=int(groups),
                        relief=float(relief),
                        cap_mode=str(cap_mode),
                    )
                )
    assert len(recipes) == 24
    return recipes


build_recipes = build_conditional_pool_recipes


def initializer_relpath(phase: str, arm: str, seed: int, recipe_id: int) -> Path:
    return Path("initializers") / phase / f"{arm}_seed{seed}" / f"CP{int(recipe_id):03d}.json"


def verify_budget_and_recipes(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    if _strict_int(cfg.get("max_candidates"), "max_candidates") != 24 or _strict_int(
        cfg.get("max_cpu_seconds"), "max_cpu_seconds"
    ) != 14400:
        raise ValueError("Authorized 24-candidate / 14400-CPU-second budget differs")

    hist_wall = _strict_int(cfg.get("history_wall_seconds", 600), "history_wall_seconds")
    eval_wall = _strict_int(cfg.get("evaluation_wall_seconds", 120), "evaluation_wall_seconds")
    freeze_wall = _strict_int(cfg.get("freeze_wall_seconds", 60), "freeze_wall_seconds")
    agg_wall = _strict_int(cfg.get("aggregate_wall_seconds", 1200), "aggregate_wall_seconds")
    audit_wall = _strict_int(
        cfg.get("independent_audit_wall_seconds", 300), "independent_audit_wall_seconds"
    )
    reserve_wall = _strict_int(
        cfg.get("local_retry_reserve_seconds", 2040), "local_retry_reserve_seconds"
    )
    prior_cpu = _strict_int(cfg.get("prior_accounted_cpu_seconds", 0), "prior_accounted_cpu_seconds")
    max_jobs = _strict_int(
        cfg.get("maximum_science_parallel_jobs", 15), "maximum_science_parallel_jobs"
    )
    per_job_ncpus = _strict_int(cfg.get("per_job_ncpus", 1), "per_job_ncpus")
    agg_mem = _strict_int(cfg.get("aggregate_mem_gb", 96), "aggregate_mem_gb")

    if hist_wall != 600:
        raise ValueError("Protocol history_wall_seconds must equal 600")
    if eval_wall != 120:
        raise ValueError("Protocol evaluation_wall_seconds must equal 120")
    if freeze_wall != 60:
        raise ValueError("Protocol freeze_wall_seconds must equal 60")
    if agg_wall != 1200:
        raise ValueError("Protocol aggregate_wall_seconds must equal 1200")
    if audit_wall != 300:
        raise ValueError("Protocol independent_audit_wall_seconds must equal 300")
    if prior_cpu < 0 or reserve_wall < 0 or reserve_wall + prior_cpu != 2040:
        raise ValueError(
            "Protocol local_retry_reserve_seconds + prior_accounted_cpu_seconds must equal 2040"
        )
    if max_jobs != 15 or per_job_ncpus != 1 or agg_mem != 96:
        raise ValueError("Protocol job/thread/memory limits must equal 15 / 1 / 96GB")

    total_phase_cpu = (
        15 * hist_wall
        + 15 * eval_wall
        + freeze_wall
        + agg_wall
        + audit_wall
        + reserve_wall
        + prior_cpu
    )
    if total_phase_cpu != 14400 or total_phase_cpu != int(cfg["max_cpu_seconds"]):
        raise ValueError(f"Phase CPU budget sum {total_phase_cpu} != 14400")

    if "budget_reservation" in cfg:
        br = cfg["budget_reservation"]
        if not isinstance(br, dict):
            raise ValueError("Protocol budget_reservation must be a dict")
        if (
            _strict_int(br.get("new_candidates"), "budget_reservation.new_candidates") != 24
            or _strict_int(br.get("cpu_seconds"), "budget_reservation.cpu_seconds") != 14400
            or _strict_int(
                br.get("total_reserved_candidates"),
                "budget_reservation.total_reserved_candidates",
            )
            != 1526
            or _strict_int(
                br.get("total_accounted_plus_open_reservations_cpu"),
                "budget_reservation.total_accounted_plus_open_reservations_cpu",
            )
            != 60997
            or _strict_int(
                br.get("global_cpu_limit_unchanged"),
                "budget_reservation.global_cpu_limit_unchanged",
            )
            != 86400
            or not (60997 < 86400)
        ):
            raise ValueError(
                "Protocol budget_reservation settlement values differ from authorized 60997/86400/1526"
            )

    expected = build_conditional_pool_recipes()
    recipes = cfg.get("recipes")
    if not isinstance(recipes, list) or len(recipes) != 24:
        raise ValueError("Protocol must declare exactly 24 recipes")

    for idx, (rec, exp) in enumerate(zip(recipes, expected)):
        if not isinstance(rec, dict) or not {"id", "groups", "relief", "cap_mode"}.issubset(rec.keys()):
            raise ValueError(f"Recipe {idx} keys do not match deterministic 24-recipe schema")
        for k in ("id", "groups", "relief", "cap_mode"):
            if not _exact_value_match(rec[k], exp[k]):
                raise ValueError(f"Recipe {idx} field {k}={rec[k]!r} differs from {exp[k]!r}")
        if "mode" in rec and rec["mode"] != "STATIC":
            raise ValueError(f"Recipe {idx} mode must be STATIC if present")
    return [
        dict(
            id=int(r["id"]),
            groups=int(r["groups"]),
            relief=float(r["relief"]),
            cap_mode=str(r["cap_mode"]),
        )
        for r in recipes
    ]


def verify_parent_and_stream_bindings(
    cfg: dict[str, Any], *, require_ledger: bool = False
) -> tuple[Path, dict[str, Any], str, Path, dict[str, Any], str]:
    parent_mp_dir, parent_mp_freeze, parent_mp_freeze_sha = verify_parent_bindings(
        cfg, require_ledger=require_ledger
    )
    mp_proto_path = parent_mp_dir / "protocol_original.json"
    if not mp_proto_path.exists():
        mp_proto_path = parent_mp_dir / "protocol.json"
    mp_cfg: dict[str, Any] = {}
    if mp_proto_path.exists():
        if "protocol_sha256" in parent_mp_freeze and (parent_mp_dir / "protocol_original.json").exists():
            if sha(parent_mp_dir / "protocol_original.json") != parent_mp_freeze["protocol_sha256"]:
                raise ValueError("Parent MP protocol_original.json SHA-256 mismatch against MP FINAL_FREEZE")
        mp_cfg = json.loads(mp_proto_path.read_text(encoding="utf-8"))

    stream_root_str = cfg.get("stream_parent_results") or mp_cfg.get("parent_results")
    if not isinstance(stream_root_str, str) or not stream_root_str:
        raise ValueError("Protocol missing stream_parent_results (or parent_results in MP protocol)")
    if (
        cfg.get("stream_parent_results")
        and mp_cfg.get("parent_results")
        and Path(str(cfg["stream_parent_results"])) != Path(str(mp_cfg["parent_results"]))
    ):
        raise ValueError("Conflicting stream_parent_results between protocol and parent MP protocol")

    stream_mc_dir = Path(stream_root_str)
    exp_stream_freeze_sha = (
        cfg.get("stream_parent_freeze_sha256")
        or mp_cfg.get("parent_freeze_sha256")
        or parent_mp_freeze.get("parent_freeze_sha256")
    )
    if not isinstance(exp_stream_freeze_sha, str) or not exp_stream_freeze_sha:
        raise ValueError("Protocol missing stream_parent_freeze_sha256")
    if (
        cfg.get("stream_parent_freeze_sha256")
        and parent_mp_freeze.get("parent_freeze_sha256")
        and cfg["stream_parent_freeze_sha256"] != parent_mp_freeze["parent_freeze_sha256"]
    ):
        raise ValueError("stream_parent_freeze_sha256 conflicts with parent MP FINAL_FREEZE")

    mc_freeze_path = stream_mc_dir / "FINAL_FREEZE.json"
    mc_open_path = stream_mc_dir / "EVALUATION_OPEN.json"
    if not mc_freeze_path.exists() or sha(mc_freeze_path) != exp_stream_freeze_sha:
        raise ValueError("Stream parent MCV2 FINAL_FREEZE.json missing or SHA-256 mismatch")
    stream_mc_freeze = json.loads(mc_freeze_path.read_text(encoding="utf-8"))
    if mc_open_path.exists():
        mc_open = json.loads(mc_open_path.read_text(encoding="utf-8"))
        if mc_open.get("freeze_sha256") != exp_stream_freeze_sha:
            raise ValueError("Stream parent MCV2 EVALUATION_OPEN.json freeze_sha256 mismatch")

    return (
        parent_mp_dir,
        parent_mp_freeze,
        parent_mp_freeze_sha,
        stream_mc_dir,
        stream_mc_freeze,
        exp_stream_freeze_sha,
    )


def _build_inner_no_prior_oof_record(
    *,
    recipe: dict[str, Any],
    seed: int,
    arm: str,
    episode_start: int,
    source_manifest_sha256: str,
    parent_profile_sha256: str,
) -> dict[str, Any]:
    rec = initialize_anchor_record(
        groups=int(recipe["groups"]),
        relief=float(recipe["relief"]),
        cap_mode=str(recipe["cap_mode"]),
    )
    rec.update(
        id=int(recipe["id"]),
        phase="inner",
        seed=int(seed),
        arm=str(arm),
        fit_window=[],
        fit_anchor_start=None,
        fit_anchor_end=None,
        episode_start=int(episode_start),
        last_label_release=None,
        source_manifest_sha256=str(source_manifest_sha256),
        parent_profile_sha256=str(parent_profile_sha256),
        oof_source_phases=[],
        oof_raw_actions_sha256=None,
    )
    return rec


def fit_oof_conditional_pool_initializer(
    *,
    phase: str,
    seed: int,
    arm: str,
    recipe: dict[str, Any],
    oof_bank: dict[str, Any],
    b_oof: np.ndarray,
    episode_start: int,
    source_manifest_sha256: str,
    parent_profile_sha256: str,
    time_limit: float = 8.0,
    max_iter: int = 1200,
    tol: float = 1e-7,
) -> dict[str, Any]:
    """Fit context-conditional 25-simplex weights on mature OOF Meta rows with common REF cuts."""
    fit_start = time.monotonic()
    a_oof = np.asarray(oof_bank["anchors"], dtype=np.int64)
    y_oof = np.asarray(oof_bank["shortfall"], dtype=np.float64)
    m_oof = np.asarray(oof_bank["mask"], dtype=bool)
    ref_oof = np.asarray(oof_bank["reference"], dtype=np.float64)
    x_oof = raw_experts_from_bank(oof_bank)
    b_arr = np.asarray(b_oof, dtype=np.float64)

    if a_oof.ndim != 1 or a_oof.size == 0 or np.any(np.diff(a_oof) <= 0):
        raise ValueError(f"OOF fit anchors for {phase} must be 1D strictly increasing")
    if int(a_oof[0]) < 28087:
        raise ValueError(f"OOF Meta stream cannot contain anchors before 28087, got {int(a_oof[0])}")
    last_release = int(a_oof[-1]) + 7
    if last_release >= int(episode_start):
        raise ValueError(
            f"OOF fit labels are not strictly mature before {phase} start: "
            f"last_anchor={int(a_oof[-1])}, last_release={last_release} >= episode_start={int(episode_start)}"
        )
    if (
        y_oof.shape != b_arr.shape
        or m_oof.shape != b_arr.shape
        or ref_oof.shape != b_arr.shape
        or x_oof.shape != (*b_arr.shape, 24)
    ):
        raise ValueError("OOF fit arrays shape mismatch")
    if not np.isfinite(ref_oof).all() or np.any(ref_oof < 0.0):
        raise ValueError("OOF reference array must be finite and nonnegative")

    valid_cells = int(m_oof.sum())
    if valid_cells < 1:
        raise ValueError(f"No valid masked OOF cells available for {phase}/{arm}_seed{seed}")
    y_valid = np.asarray(y_oof[m_oof], dtype=np.float64)
    if not np.isfinite(y_valid).all() or np.any(y_valid < 0.0):
        raise ValueError("Valid masked OOF shortfall contains NaN, Inf, or negative values")

    g = int(recipe["groups"])
    d = float(recipe["relief"])
    mode = str(recipe["cap_mode"])
    cuts = fit_context_cuts(ref_oof, g)

    try:
        with threadpool_limits(limits=1):
            record = fit_conditional_pool(
                x_oof,
                b_arr,
                y_oof,
                m_oof,
                a_oof,
                ref_oof,
                groups=g,
                relief=d,
                cap_mode=mode,
                time_limit=float(min(float(time_limit), 8.0)),
                max_iter=int(max_iter),
                tol=float(tol),
            )
    except Exception as exc:
        w_fb = np.zeros((g, 25), dtype=np.float64)
        w_fb[:, 0] = 1.0
        b_valid = np.asarray(b_arr[m_oof], dtype=np.float64)
        z_fb = np.maximum(y_valid - b_valid, 0.0)
        u_fb = float(z_fb.mean())
        c_fb = float((b_valid + 10.0 * z_fb).mean() / 6.0)
        day_grid = np.broadcast_to((a_oof // 144)[:, None], b_arr.shape)
        day_valid = day_grid[m_oof]
        u_days = np.unique(day_valid)
        d_caps = [float(z_fb[day_valid == int(day)].mean()) for day in u_days] if mode == "DAY" else None
        record = initialize_anchor_record(groups=g, relief=d, cap_mode=mode)
        record.update(
            status="INITIALIZER_ERROR_DECLARED_ANCHOR_FALLBACK",
            optimal=False,
            numerical_fitted=True,
            cuts=cuts,
            cuts_source=("HISTORICAL_REFERENCE_GRID_QUANTILES" if g == 3 else "SINGLE_POOL_NO_CUTS"),
            weights=w_fb.tolist(),
            raw_weights=w_fb.tolist(),
            canonical_initial=w_fb.tolist(),
            objective=c_fb,
            lower_bound=0.0,
            gap=c_fb,
            mean_uncovered_power=u_fb,
            uncovered_cap=(u_fb if mode == "POOLED" else None),
            day_caps=d_caps,
            day_uncovered_power=(list(d_caps) if d_caps is not None else None),
            day_ids=[int(day) for day in u_days.tolist()],
            day_valid_counts=[int(np.count_nonzero(day_valid == int(day))) for day in u_days],
            max_cap_violation=0.0,
            anchor_objective=c_fb,
            anchor_mean_uncovered_power=u_fb,
            valid_fit_cells=valid_cells,
            total_cells=int(b_arr.size),
            fit_issue_count=int(a_oof.size),
            actual_feasible=True,
            raw_actual_feasible=False,
            repaired_to_anchor=True,
            repair_alpha=1.0,
            time_limit=float(min(float(time_limit), 8.0)),
            max_iter=int(max_iter),
            relative_tolerance=float(tol),
            numerical_failure=repr(exc),
            error=repr(exc),
            traceback=traceback.format_exc(),
        )

    w_arr = np.asarray(record["weights"], dtype=np.float64)
    w_canon = np.asarray(record["canonical_initial"], dtype=np.float64)
    if (
        w_arr.shape != (g, 25)
        or w_canon.shape != (g, 25)
        or not np.array_equal(w_arr, w_canon)
        or not np.isfinite(w_arr).all()
        or np.any(w_arr < 0.0)
        or not np.allclose(w_arr.sum(axis=1), 1.0, atol=1e-12, rtol=0.0)
    ):
        raise ValueError(f"Fitted conditional pool weights must have shape ({g}, 25) on probability simplex")
    if list(record.get("cuts", [])) != cuts:
        raise ValueError("Fitted conditional pool cuts differ from full historical reference grid quantiles")

    oof_phases = list(oof_bank["metadata"].get("phases") or [oof_bank["metadata"].get("phase")])
    record.update(
        id=int(recipe["id"]),
        phase=str(phase),
        seed=int(seed),
        arm=str(arm),
        groups=g,
        relief=d,
        cap_mode=mode,
        numerical_fitted=True,
        weights=w_arr.tolist(),
        raw_weights=np.asarray(record.get("raw_weights", w_arr), dtype=np.float64).tolist(),
        canonical_initial=w_canon.tolist(),
        fit_window=[int(a_oof[0]), int(a_oof[-1]) + 1],
        fit_anchor_start=int(a_oof[0]),
        fit_anchor_end=int(a_oof[-1]),
        fit_issue_count=int(a_oof.size),
        valid_fit_cells=int(valid_cells),
        episode_start=int(episode_start),
        last_label_release=int(last_release),
        n_raw_experts=24,
        n_experts=25,
        source_manifest_sha256=str(source_manifest_sha256),
        parent_profile_sha256=str(parent_profile_sha256),
        oof_source_phases=oof_phases,
        oof_raw_actions_sha256=oof_bank["metadata"].get("raw_actions_sha256"),
        elapsed_seconds=float(time.monotonic() - fit_start),
    )
    return record


def _score_phase_conditional_recipes(
    *,
    out: Path,
    phase: str,
    seed: int,
    arm: str,
    recipes: list[dict[str, Any]],
    bank: dict[str, Any],
    b_slice: np.ndarray,
    profile_sha: str,
    stream_record: dict[str, Any],
    checkpoint_path: Path | None,
    deadline: float,
) -> dict[str, Any]:
    destination = out / "instances" / phase / f"{arm}_seed{seed}"
    destination.mkdir(parents=True, exist_ok=False)

    aa = np.asarray(bank["anchors"], dtype=np.int64)
    yy = np.asarray(bank["shortfall"], dtype=np.float64)
    mm = np.asarray(bank["mask"], dtype=bool)
    ref_arr = np.asarray(bank["reference"], dtype=np.float64)
    xx = raw_experts_from_bank(bank)
    bb = np.asarray(b_slice, dtype=np.float64)

    ref_led, counts, days = score_actions(ref_arr, yy, mm, aa)
    ids = [int(r["id"]) for r in recipes]
    array = np.full((len(ids), len(days), 4), np.nan, dtype=np.float64)

    status: dict[str, str] = {}
    point: dict[str, list[float]] = {}
    hashes: dict[str, str] = {}
    metadata: dict[str, dict[str, Any]] = {}
    errors: dict[str, dict[str, str]] = {}

    for recipe in recipes:
        deadline_check(deadline)
        rid = int(recipe["id"])
        key = str(rid)
        init_rel = initializer_relpath(phase, arm, seed, rid)
        init_path = out / init_rel
        try:
            init_rec = json.loads(init_path.read_text(encoding="utf-8"))
            init_sha = sha(init_path)
            with threadpool_limits(limits=1):
                act, pred_meta = predict_conditional_pool(xx, bb, ref_arr, init_rec)
            act = np.ascontiguousarray(act, dtype=np.float64)
            ledger, counts_local, days_local = score_actions(act, yy, mm, aa)
            if ledger.shape != (len(days_local), 4) or not np.isfinite(ledger).all():
                raise ValueError(f"Invalid candidate ledger for recipe {rid}")
            idx_pos = ids.index(rid)
            array[idx_pos] = ledger
            means_list = (ledger.sum(axis=0) / counts_local.sum()).tolist()
            point[key] = [float(v) for v in means_list]
            status[key] = "COMPLETED"
            act_sha = prefix_sha256(act)
            hashes[key] = act_sha
            metadata[key] = dict(
                id=rid,
                groups=int(recipe["groups"]),
                relief=float(recipe["relief"]),
                cap_mode=str(recipe["cap_mode"]),
                cuts=list(init_rec.get("cuts", [])),
                initializer_path=str(init_rel).replace("\\", "/"),
                initializer_sha256=init_sha,
                initializer_status=init_rec["status"],
                initializer_optimal=bool(init_rec["optimal"]),
                numerical_fitted=bool(init_rec.get("numerical_fitted", phase != "inner")),
                actual_feasible=bool(init_rec.get("actual_feasible", True)),
                repaired_to_anchor=bool(init_rec.get("repaired_to_anchor", False)),
                boundary_guard_count=int(pred_meta["boundary_guard_count"]),
                max_boundary_violation=float(pred_meta["max_boundary_violation"]),
                group_cell_counts=list(pred_meta["group_cell_counts"]),
                recomputed_cuts_on_prediction=bool(pred_meta["recomputed_cuts_on_prediction"]),
                mask_gated_prediction=bool(pred_meta["mask_gated_prediction"]),
                parent_profile_sha256=profile_sha,
            )
            if checkpoint_path is not None:
                append_jsonl(
                    checkpoint_path,
                    dict(
                        record_type="RECIPE",
                        stage=("evaluate" if phase == "evaluate" else "history"),
                        phase=phase,
                        seed=int(seed),
                        arm=str(arm),
                        id=rid,
                        groups=int(recipe["groups"]),
                        relief=float(recipe["relief"]),
                        cap_mode=str(recipe["cap_mode"]),
                        success=True,
                        status="COMPLETED",
                        error=None,
                        action_sha256=act_sha,
                        metrics=_checkpoint_phase_metrics(act, yy, mm, aa),
                    ),
                )
        except Exception as exc:
            status[key] = "FAILED_PRESERVED"
            errors[key] = dict(error=repr(exc), traceback=traceback.format_exc())
            if checkpoint_path is not None:
                append_jsonl(
                    checkpoint_path,
                    dict(
                        record_type="RECIPE",
                        stage=("evaluate" if phase == "evaluate" else "history"),
                        phase=phase,
                        seed=int(seed),
                        arm=str(arm),
                        id=rid,
                        groups=int(recipe["groups"]),
                        relief=float(recipe["relief"]),
                        cap_mode=str(recipe["cap_mode"]),
                        success=False,
                        status="FAILED_PRESERVED",
                        error=repr(exc),
                        action_sha256=None,
                        metrics=None,
                    ),
                )

    np.savez_compressed(
        destination / "daily.npz",
        ledger=array,
        reference=ref_led,
        counts=counts,
        days=days,
    )
    b_meta = bank["metadata"]
    receipt = dict(
        phase=phase,
        seed=int(seed),
        arm=str(arm),
        ids=ids,
        status=status,
        metrics=point,
        action_sha256=hashes,
        metadata=metadata,
        errors=errors,
        source_manifest_sha256=b_meta.get("source_manifest_sha256"),
        parent_profile_sha256=profile_sha,
        bank_npz_sha256=stream_record.get("npz_sha256"),
        bank_metadata_sha256=stream_record.get("metadata_sha256"),
        bank_raw_actions_sha256=stream_record.get("raw_actions_sha256"),
        complete_expected=len(recipes),
        completed=sum(v == "COMPLETED" for v in status.values()),
        scientific_qualification_used_to_filter=False,
    )
    save(destination / "receipt.json", receipt)
    return dict(
        phase=phase,
        seed=int(seed),
        arm=str(arm),
        completed=receipt["completed"],
        expected=len(recipes),
    )


def history_summary(points: np.ndarray, recipes: list[dict[str, Any]]) -> dict[str, Any]:
    """Select historical minimum_C and minimum_maxV across all 24 conditional pool recipes per arm."""
    complete = np.isfinite(points).all(axis=(1, 2, 3))
    roles: dict[str, dict[str, Any]] = {}
    by_cap_mode_roles: dict[str, dict[str, Any]] = {}
    by_groups_roles: dict[str, dict[str, Any]] = {}
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
        for mode in CAP_MODES:
            m_pool = [j for j in pool if recipes[j]["cap_mode"] == mode]
            if m_pool:
                m_c = min(m_pool, key=lambda j: (float(points[j, :, ai, 0].mean()), int(recipes[j]["id"])))
                m_v = min(
                    m_pool,
                    key=lambda j: (
                        float(points[j, :, ai, 3].max()),
                        float(points[j, :, ai, 2].max()),
                        float(points[j, :, ai, 0].mean()),
                        int(recipes[j]["id"]),
                    ),
                )
                by_cap_mode_roles[f"{mode}_{arm}"] = dict(
                    minimum_C_id=int(recipes[m_c]["id"]),
                    minimum_maxV_id=int(recipes[m_v]["id"]),
                )
        for grp in GROUPS_GRID:
            g_pool = [j for j in pool if int(recipes[j]["groups"]) == int(grp)]
            if g_pool:
                g_c = min(g_pool, key=lambda j: (float(points[j, :, ai, 0].mean()), int(recipes[j]["id"])))
                g_v = min(
                    g_pool,
                    key=lambda j: (
                        float(points[j, :, ai, 3].max()),
                        float(points[j, :, ai, 2].max()),
                        float(points[j, :, ai, 0].mean()),
                        int(recipes[j]["id"]),
                    ),
                )
                by_groups_roles[f"G{grp}_{arm}"] = dict(
                    minimum_C_id=int(recipes[g_c]["id"]),
                    minimum_maxV_id=int(recipes[g_v]["id"]),
                )
    return dict(
        roles=roles,
        by_cap_mode_roles=by_cap_mode_roles,
        by_groups_roles=by_groups_roles,
        complete_recipe_count=int(complete.sum()),
        all_recipes_retained=True,
        qualification_did_not_filter_instances=True,
        selection_scope="Historical outer minimum_C/minimum_maxV per arm (C/P/Z) across all 24 conditional pool recipes without qualification filter; all 24 recipes still scored in evaluation",
    )


def run_history_shard(
    cfg: dict[str, Any],
    out: Path,
    shard: int,
    *,
    protocol_path: Path | None = None,
    deadline: float | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
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
            deadline = start + _phase_wall_seconds(cfg, "history_wall_seconds", 600) - 30.0
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

        (
            _,
            _,
            parent_freeze_sha,
            stream_mc_dir,
            stream_mc_freeze,
            stream_freeze_sha,
        ) = verify_parent_and_stream_bindings(cfg, require_ledger=False)
        source_cfg, meta_dir = resolve_meta_source_protocol(cfg, stream_mc_dir, stream_mc_freeze)

        hist_cache_anchors, b_hist_full, hist_profile_sha, hist_manifest_sha = (
            load_verified_causal_profile_and_anchors(
                source_cfg,
                "historical",
                seed,
                meta_dir=meta_dir,
                parent_mc_dir=stream_mc_dir,
            )
        )

        deadline_check(deadline)
        inner_bank, inner_stream_rec = load_verified_parent_stream_bank(
            stream_mc_dir, stream_mc_freeze, "inner", seed, arm
        )
        outer_bank, outer_stream_rec = load_verified_parent_stream_bank(
            stream_mc_dir, stream_mc_freeze, "outer", seed, arm
        )
        hist_joined_bank = join_banks([inner_bank, outer_bank])

        n_inner = len(inner_bank["anchors"])
        n_outer = len(outer_bank["anchors"])
        if int(outer_bank["anchors"][0]) - int(inner_bank["anchors"][-1]) <= 7:
            raise ValueError("Joined history bank did not preserve the 7-step causal gap between inner and outer")

        expected_hist_grid = cfg.get("expected_historical_grid", True)
        if expected_hist_grid and n_inner == 850 and n_outer == 1289:
            if int(inner_bank["anchors"][0]) != 28087 or int(inner_bank["anchors"][-1]) != 28936:
                raise ValueError("Inner anchor boundaries differ from 28087..28936")
            if int(outer_bank["anchors"][0]) != 28944 or int(outer_bank["anchors"][-1]) != 30232:
                raise ValueError("Outer anchor boundaries differ from 28944..30232")
            if len(hist_joined_bank["anchors"]) != 2139:
                raise ValueError("Joined history issue count differs from 2139")

        b_inner = select_exact_anchor_slice(hist_cache_anchors, b_hist_full, inner_bank["anchors"])
        b_outer = select_exact_anchor_slice(hist_cache_anchors, b_hist_full, outer_bank["anchors"])
        b_joined = select_exact_anchor_slice(
            hist_cache_anchors, b_hist_full, hist_joined_bank["anchors"]
        )

        init_ckpt_path = _init_checkpoint_jsonl(
            shard_dir / INITIALIZER_CHECKPOINT_FILENAME,
            dict(
                record_type="HEADER",
                schema="conditional-pool-initializer-checkpoint-v1",
                stage="history",
                shard=shard,
                seed=seed,
                arm=arm,
                study_id=cfg.get("study_id"),
                protocol_sha256=protocol_sha,
                source_commit=state["source_commit"],
                source_versions=source_versions,
                parent_freeze_sha256=parent_freeze_sha,
                stream_parent_freeze_sha256=stream_freeze_sha,
                initializers_expected=72,
            ),
        )

        init_records: list[dict[str, Any]] = []
        fit_time_limit = float(cfg.get("fit_time_limit_seconds", 8.0))
        fit_max_iter = int(cfg.get("fit_max_iter", 1200))
        fit_tol = float(cfg.get("fit_relative_tolerance", 1e-7))

        for phase in ("inner", "outer", "evaluate"):
            begin, _, _ = PHASES[phase]
            if phase != "inner":
                oof_bank = inner_bank if phase == "outer" else hist_joined_bank
                b_oof = b_inner if phase == "outer" else b_joined
                actual_begin = int(outer_bank["anchors"][0]) if phase == "outer" else int(begin)
            else:
                oof_bank = None
                b_oof = None
                actual_begin = int(inner_bank["anchors"][0])

            for recipe in recipes:
                deadline_check(deadline)
                rid = int(recipe["id"])
                if phase == "inner":
                    rec = _build_inner_no_prior_oof_record(
                        recipe=recipe,
                        seed=seed,
                        arm=arm,
                        episode_start=actual_begin,
                        source_manifest_sha256=hist_manifest_sha,
                        parent_profile_sha256=hist_profile_sha,
                    )
                else:
                    assert oof_bank is not None and b_oof is not None
                    rec = fit_oof_conditional_pool_initializer(
                        phase=phase,
                        seed=seed,
                        arm=arm,
                        recipe=recipe,
                        oof_bank=oof_bank,
                        b_oof=b_oof,
                        episode_start=actual_begin,
                        source_manifest_sha256=hist_manifest_sha,
                        parent_profile_sha256=hist_profile_sha,
                        time_limit=fit_time_limit,
                        max_iter=fit_max_iter,
                        tol=fit_tol,
                    )
                rel_init = initializer_relpath(phase, arm, seed, rid)
                init_path = out / rel_init
                save(init_path, rec)
                rec_sha = sha(init_path)
                entry = dict(
                    phase=phase,
                    seed=int(seed),
                    arm=str(arm),
                    id=rid,
                    groups=int(recipe["groups"]),
                    relief=float(recipe["relief"]),
                    cap_mode=str(recipe["cap_mode"]),
                    cuts=list(rec["cuts"]),
                    path=str(rel_init).replace("\\", "/"),
                    sha256=rec_sha,
                    status=rec["status"],
                    optimal=bool(rec["optimal"]),
                    numerical_fitted=bool(rec["numerical_fitted"]),
                    actual_feasible=bool(rec["actual_feasible"]),
                    fit_issue_count=int(rec["fit_issue_count"]),
                    valid_fit_cells=int(rec["valid_fit_cells"]),
                    last_label_release=rec["last_label_release"],
                    episode_start=int(rec["episode_start"]),
                )
                init_records.append(entry)
                append_jsonl(
                    init_ckpt_path,
                    dict(
                        record_type="INITIALIZER",
                        stage="history",
                        shard=shard,
                        **entry,
                    ),
                )

        assert len(init_records) == 72
        num_fitted = sum(1 for r in init_records if r["numerical_fitted"])
        num_anchor = sum(1 for r in init_records if not r["numerical_fitted"])
        assert num_fitted == 48 and num_anchor == 24

        recipe_ckpt_path = _init_checkpoint_jsonl(
            shard_dir / CHECKPOINT_FILENAME,
            dict(
                record_type="HEADER",
                schema="conditional-pool-recipe-checkpoint-v1",
                stage="history",
                shard=shard,
                seed=seed,
                arm=arm,
                study_id=cfg.get("study_id"),
                protocol_sha256=protocol_sha,
                source_commit=state["source_commit"],
                source_versions=source_versions,
                parent_freeze_sha256=parent_freeze_sha,
                stream_parent_freeze_sha256=stream_freeze_sha,
                inner_npz_sha256=inner_stream_rec["npz_sha256"],
                outer_npz_sha256=outer_stream_rec["npz_sha256"],
                recipes_expected=len(recipes),
            ),
        )

        sum_inner = _score_phase_conditional_recipes(
            out=out,
            phase="inner",
            seed=seed,
            arm=arm,
            recipes=recipes,
            bank=inner_bank,
            b_slice=b_inner,
            profile_sha=hist_profile_sha,
            stream_record=inner_stream_rec,
            checkpoint_path=recipe_ckpt_path,
            deadline=deadline,
        )
        sum_outer = _score_phase_conditional_recipes(
            out=out,
            phase="outer",
            seed=seed,
            arm=arm,
            recipes=recipes,
            bank=outer_bank,
            b_slice=b_outer,
            profile_sha=hist_profile_sha,
            stream_record=outer_stream_rec,
            checkpoint_path=recipe_ckpt_path,
            deadline=deadline,
        )
        phase_summaries = [sum_inner, sum_outer]
        streams_recorded = {
            inner_stream_rec["npz_path"]: inner_stream_rec,
            outer_stream_rec["npz_path"]: outer_stream_rec,
        }

        shard_receipt = dict(
            status="COMPLETED",
            stage="history",
            shard=shard,
            seed=seed,
            arm=arm,
            protocol_sha256=protocol_sha,
            source_versions=source_versions,
            parent_freeze_sha256=parent_freeze_sha,
            stream_parent_freeze_sha256=stream_freeze_sha,
            historical_manifest_sha256=hist_manifest_sha,
            parent_profile_sha256=hist_profile_sha,
            streams=streams_recorded,
            initializers_prepared=len(init_records),
            initializers_numerical_fitted=num_fitted,
            initializers_anchor_declared=num_anchor,
            initializers=init_records,
            phase_summaries=phase_summaries,
            new_models_fitted=0,
            evaluation_cache_read=False,
            scientific_qualification_used_to_filter=False,
            elapsed_seconds=time.time() - start,
        )
        save(shard_dir / "receipt.json", shard_receipt)
        state.update(
            status="COMPLETED",
            elapsed_seconds=time.time() - start,
            phase_summaries=phase_summaries,
        )
        save(shard_dir / "state.json", state)
        return shard_receipt
    except BaseException as exc:
        save(shard_dir / "failure.json", dict(error=repr(exc), traceback=traceback.format_exc()))
        state.update(status="FAILED_PRESERVED", elapsed_seconds=time.time() - start, error=repr(exc))
        save(shard_dir / "state.json", state)
        raise


def run_freeze_stage(
    cfg: dict[str, Any],
    out: Path,
    *,
    protocol_path: Path | None = None,
    deadline: float | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
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
            deadline = start + _phase_wall_seconds(cfg, "freeze_wall_seconds", 60) - 20.0
        deadline_check(deadline)

        (
            _,
            parent_mp_freeze,
            parent_freeze_sha,
            stream_mc_dir,
            stream_mc_freeze,
            stream_freeze_sha,
        ) = verify_parent_and_stream_bindings(cfg, require_ledger=False)
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

        shard_receipts: list[dict[str, Any]] = []
        all_streams: dict[str, dict[str, Any]] = {}
        recorded_initializers: dict[str, str] = {}
        all_instance_receipts: dict[str, str] = {}
        total_numerical_fits = 0
        total_anchor_records = 0

        for shard in range(15):
            seed, arm = shard_assignment(shard)
            r_path = out / "shards" / "history" / f"shard_{shard:02d}_{arm}_seed{seed}" / "receipt.json"
            if not r_path.exists():
                raise ValueError(f"Missing history shard receipt: {r_path}")
            r_data = json.loads(r_path.read_text(encoding="utf-8"))
            if r_data.get("status") != "COMPLETED":
                raise ValueError(f"History shard {shard} status is not COMPLETED")
            if r_data.get("shard") != shard or r_data.get("seed") != seed or r_data.get("arm") != arm:
                raise ValueError(f"History shard {shard} receipt identity mismatch")
            if r_data.get("protocol_sha256") != protocol_sha:
                raise ValueError(f"History shard {shard} protocol_sha256 differs from current protocol")
            if r_data.get("source_versions") != source_versions:
                raise ValueError(f"History shard {shard} source_versions differ from current source")
            if (
                r_data.get("parent_freeze_sha256") != parent_freeze_sha
                or r_data.get("stream_parent_freeze_sha256") != stream_freeze_sha
            ):
                raise ValueError(f"History shard {shard} parent or stream freeze SHA-256 mismatch")
            if (
                r_data.get("initializers_prepared") != 72
                or r_data.get("initializers_numerical_fitted") != 48
                or r_data.get("initializers_anchor_declared") != 24
                or r_data.get("new_models_fitted") != 0
            ):
                raise ValueError(f"History shard {shard} initializer accounting mismatch")

            total_numerical_fits += int(r_data["initializers_numerical_fitted"])
            total_anchor_records += int(r_data["initializers_anchor_declared"])

            inits = r_data.get("initializers")
            if not isinstance(inits, list) or len(inits) != 72:
                raise ValueError(f"History shard {shard} receipt must record 72 initializers")
            for item in inits:
                rel_key = str(item.get("path", "")).replace("\\", "/")
                rec_sha = item.get("sha256")
                if not rel_key or not isinstance(rec_sha, str):
                    raise ValueError(f"History shard {shard} receipt has invalid initializer entry")
                full_init = out / rel_key
                if not full_init.exists() or sha(full_init) != rec_sha:
                    raise ValueError(
                        f"Initializer {rel_key} missing or SHA-256 mismatch against history shard {shard} receipt"
                    )
                recorded_initializers[rel_key] = rec_sha

            streams = r_data.get("streams") or {}
            if len(streams) != 2:
                raise ValueError(f"History shard {shard} receipt must bind inner and outer stream banks")
            for phase in ("inner", "outer"):
                s_rel = str(stream_relpath(phase, arm, seed)).replace("\\", "/")
                if s_rel not in streams:
                    raise ValueError(f"Missing stream {s_rel} in history shard {shard} receipt")
                s_entry = streams[s_rel]
                _, verified_stream = load_verified_parent_stream_bank(
                    stream_mc_dir, stream_mc_freeze, phase, seed, arm
                )
                if (
                    s_entry.get("npz_sha256") != verified_stream["npz_sha256"]
                    or s_entry.get("metadata_sha256") != verified_stream["metadata_sha256"]
                    or s_entry.get("raw_actions_sha256") != verified_stream["raw_actions_sha256"]
                ):
                    raise ValueError(f"Stream bank SHA-256 mismatch against stream parent freeze for {s_rel}")
                all_streams[s_rel] = dict(verified_stream)

                inst_rcpt_rel = f"instances/{phase}/{arm}_seed{seed}/receipt.json"
                inst_rcpt_full = out / inst_rcpt_rel
                if not inst_rcpt_full.exists():
                    raise ValueError(f"Missing history instance receipt: {inst_rcpt_full}")
                all_instance_receipts[inst_rcpt_rel] = sha(inst_rcpt_full)

            shard_receipts.append(r_data)

        all_initializers: dict[str, str] = {}
        cuts_by_context: dict[tuple[str, int, int], list[float]] = {}
        for phase in ("inner", "outer", "evaluate"):
            for seed in SEEDS:
                for arm in META_ARMS:
                    for recipe in recipes:
                        rid = int(recipe["id"])
                        grp = int(recipe["groups"])
                        rel = initializer_relpath(phase, arm, seed, rid)
                        rel_key = str(rel).replace("\\", "/")
                        full = out / rel
                        if not full.exists():
                            raise ValueError(f"Missing required initializer: {full}")
                        digest = sha(full)
                        if rel_key not in recorded_initializers or recorded_initializers[rel_key] != digest:
                            raise ValueError(
                                f"Initializer {rel_key} missing or mismatched in history shard receipts"
                            )
                        all_initializers[rel_key] = digest
                        rec_json = json.loads(full.read_text(encoding="utf-8"))
                        cuts_val = [float(x) for x in rec_json.get("cuts", [])]
                        if phase == "inner":
                            exp_inner_cuts = [] if grp == 1 else [0.0, 0.0]
                            if cuts_val != exp_inner_cuts:
                                raise ValueError(
                                    f"Inner initializer {rel_key} cuts {cuts_val} differ from declared {exp_inner_cuts}"
                                )
                        key_ctx = (phase, int(seed), grp)
                        if key_ctx not in cuts_by_context:
                            cuts_by_context[key_ctx] = cuts_val
                        elif cuts_by_context[key_ctx] != cuts_val:
                            raise ValueError(
                                f"Context cuts mismatch across arms/recipes at phase={phase}, seed={seed}, groups={grp}: "
                                f"{cuts_val} != {cuts_by_context[key_ctx]}"
                            )

        assert len(all_initializers) == 1080
        assert total_numerical_fits == 720
        assert total_anchor_records == 360
        assert len(all_streams) == 30
        assert len(all_instance_receipts) == 30

        for phase in ("inner", "outer"):
            points, _ = collect(out, phase, recipes)
            np.save(out / f"{phase}_points.npy", points, allow_pickle=False)
            save(out / f"{phase}_selection.json", history_summary(points, recipes))

        freeze_payload = dict(
            time_utc=datetime.now(timezone.utc).isoformat(),
            study_id=cfg.get("study_id", "conditional_pool_20261025_v1"),
            source_commit=os.environ.get("CAMPAIGN_RELEASE", "LOCAL_SYNTHETIC"),
            protocol_sha256=protocol_sha,
            source_versions=source_versions,
            parent_freeze_sha256=parent_freeze_sha,
            stream_parent_freeze_sha256=stream_freeze_sha,
            parent_ledger_sha256=cfg["parent_ledger_sha256"],
            parent_span3_sha256=cfg["parent_span3_sha256"],
            recipes=recipes,
            historical_roles=json.loads((out / "outer_selection.json").read_text(encoding="utf-8")),
            parent_historical_roles=parent_mp_freeze.get("historical_roles"),
            cuts_consistent_across_arms=True,
            all_initializers=all_initializers,
            all_streams=all_streams,
            all_instance_receipts=all_instance_receipts,
            total_initializers=len(all_initializers),
            numerical_fits=total_numerical_fits,
            anchor_declarations=total_anchor_records,
            new_models_fitted=0,
            history_shard_count=len(shard_receipts),
            selection_scope="Historical outer minimum_C/minimum_maxV per arm (C/P/Z) across all 24 conditional pool recipes without qualification filter; all 24 evaluated",
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


def verify_freeze_barrier(
    cfg: dict[str, Any],
    out: Path,
    *,
    protocol_path: Path | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
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
    if freeze.get("parent_freeze_sha256") != cfg.get("parent_freeze_sha256"):
        raise ValueError("parent_freeze_sha256 changed after FINAL_FREEZE")
    if (
        cfg.get("stream_parent_freeze_sha256")
        and freeze.get("stream_parent_freeze_sha256") != cfg.get("stream_parent_freeze_sha256")
    ):
        raise ValueError("stream_parent_freeze_sha256 changed after FINAL_FREEZE")
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
    cfg: dict[str, Any],
    out: Path,
    shard: int,
    *,
    protocol_path: Path | None = None,
    deadline: float | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
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
            deadline = start + _phase_wall_seconds(cfg, "evaluation_wall_seconds", 120) - 30.0
        deadline_check(deadline)

        freeze = verify_freeze_barrier(cfg, out, protocol_path=protocol_path, root=root)
        (
            _,
            _,
            parent_freeze_sha,
            stream_mc_dir,
            stream_mc_freeze,
            stream_freeze_sha,
        ) = verify_parent_and_stream_bindings(cfg, require_ledger=False)
        source_cfg, meta_dir = resolve_meta_source_protocol(cfg, stream_mc_dir, stream_mc_freeze)

        all_inits = freeze.get("all_initializers") or {}
        if len(all_inits) != 1080:
            raise ValueError("FINAL_FREEZE.json must bind all 1080 initializers")
        for phase_check in ("inner", "outer", "evaluate"):
            for recipe in recipes:
                rel = str(initializer_relpath(phase_check, arm, seed, int(recipe["id"]))).replace("\\", "/")
                full = out / rel
                if rel not in all_inits or not full.exists() or sha(full) != all_inits[rel]:
                    raise ValueError(f"Initializer missing or modified since freeze: {rel}")

        all_streams = freeze.get("all_streams") or {}
        all_inst_rcpts = freeze.get("all_instance_receipts") or {}
        for phase_check in ("inner", "outer"):
            s_rel = str(stream_relpath(phase_check, arm, seed)).replace("\\", "/")
            if s_rel not in all_streams:
                raise ValueError(f"Frozen stream entry missing in FINAL_FREEZE: {s_rel}")
            s_entry = all_streams[s_rel]
            _, verified_s = load_verified_parent_stream_bank(
                stream_mc_dir, stream_mc_freeze, phase_check, seed, arm
            )
            if (
                verified_s["npz_sha256"] != s_entry.get("npz_sha256")
                or verified_s["metadata_sha256"] != s_entry.get("metadata_sha256")
            ):
                raise ValueError(f"Historical stream bank tampered since freeze: {s_rel}")
            inst_rel = f"instances/{phase_check}/{arm}_seed{seed}/receipt.json"
            if inst_rel not in all_inst_rcpts or sha(out / inst_rel) != all_inst_rcpts[inst_rel]:
                raise ValueError(f"Historical instance receipt missing or modified since freeze: {inst_rel}")

        eval_cache_anchors, b_eval_full, eval_profile_sha, eval_manifest_sha = (
            load_verified_causal_profile_and_anchors(
                source_cfg,
                "evaluate",
                seed,
                meta_dir=meta_dir,
                parent_mc_dir=stream_mc_dir,
            )
        )
        eval_bank, eval_stream_rec = load_verified_parent_stream_bank(
            stream_mc_dir, stream_mc_freeze, "evaluate", seed, arm
        )

        expected_len = int(cfg.get("expected_evaluation_anchors", 5033))
        expected_valid = int(cfg.get("expected_evaluation_valid_cells", 672939))
        if len(eval_bank["anchors"]) != expected_len or int(eval_bank["mask"].sum()) != expected_valid:
            raise ValueError("Evaluation population differs from expected counts")

        b_eval = select_exact_anchor_slice(eval_cache_anchors, b_eval_full, eval_bank["anchors"])

        checkpoint_path = _init_checkpoint_jsonl(
            shard_dir / CHECKPOINT_FILENAME,
            dict(
                record_type="HEADER",
                schema="conditional-pool-recipe-checkpoint-v1",
                stage="evaluate",
                shard=shard,
                seed=seed,
                arm=arm,
                study_id=cfg.get("study_id"),
                protocol_sha256=freeze.get("protocol_sha256"),
                freeze_sha256=sha(out / "FINAL_FREEZE.json"),
                source_commit=state["source_commit"],
                source_versions=freeze.get("source_versions"),
                parent_freeze_sha256=parent_freeze_sha,
                stream_parent_freeze_sha256=stream_freeze_sha,
                evaluate_npz_sha256=eval_stream_rec["npz_sha256"],
                recipes_expected=len(recipes),
            ),
        )

        summary = _score_phase_conditional_recipes(
            out=out,
            phase="evaluate",
            seed=seed,
            arm=arm,
            recipes=recipes,
            bank=eval_bank,
            b_slice=b_eval,
            profile_sha=eval_profile_sha,
            stream_record=eval_stream_rec,
            checkpoint_path=checkpoint_path,
            deadline=deadline,
        )

        shard_receipt = dict(
            status="COMPLETED",
            stage="evaluate",
            shard=shard,
            seed=seed,
            arm=arm,
            freeze_sha256=sha(out / "FINAL_FREEZE.json"),
            parent_freeze_sha256=parent_freeze_sha,
            stream_parent_freeze_sha256=stream_freeze_sha,
            evaluation_manifest_sha256=eval_manifest_sha,
            parent_profile_sha256=eval_profile_sha,
            evaluate_stream=eval_stream_rec,
            new_models_fitted=0,
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
    parent_span3: dict[str, Any],
    recipes: list[dict[str, Any]],
    parent_mp_freeze: dict[str, Any] | None = None,
    *,
    expected_parent_policies: int = 1040,
    expected_parent_comparisons: int = 4107,
) -> tuple[list[str], list[bool], list[tuple[str, str]], list[tuple[str, str]], dict[str, Any]]:
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
    if len(parent_names) != int(expected_parent_policies):
        raise ValueError(f"Expected {int(expected_parent_policies)} parent policies, got {len(parent_names)}")

    for required_parent in COMMON_COMPARATORS:
        if required_parent not in parent_names:
            raise ValueError(f"Parent family missing required comparator policy {required_parent!r}")

    raw_comps = fd.get("comparisons")
    if not isinstance(raw_comps, list) or not raw_comps:
        raise ValueError("Parent family_definition missing comparisons")
    if len(raw_comps) != int(expected_parent_comparisons):
        raise ValueError(
            f"Expected {int(expected_parent_comparisons)} parent comparisons, got {len(raw_comps)}"
        )

    def map_pair(pair: list[Any] | tuple[Any, Any]) -> tuple[str, str]:
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

    g1_lookup = {
        (float(r["relief"]), str(r["cap_mode"])): int(r["id"])
        for r in recipes
        if int(r["groups"]) == 1
    }
    pooled_lookup = {
        (int(r["groups"]), float(r["relief"])): int(r["id"])
        for r in recipes
        if str(r["cap_mode"]) == "POOLED"
    }
    assert len(g1_lookup) == 12 and len(pooled_lookup) == 8

    new_pairs_raw: list[tuple[str, str]] = []
    for r in recipes:
        rid = int(r["id"])
        grp = int(r["groups"])
        d_val = float(r["relief"])
        mode = str(r["cap_mode"])
        for arm in META_ARMS:
            policy = f"{POLICY_PREFIX}{rid:03d}_{arm}"
            for comparator in COMMON_COMPARATORS:
                new_pairs_raw.append((policy, comparator))
            if grp == 3:
                g1_id = g1_lookup[(d_val, mode)]
                new_pairs_raw.append((policy, f"{POLICY_PREFIX}{g1_id:03d}_{arm}"))
            if mode == "DAY":
                pooled_id = pooled_lookup[(grp, d_val)]
                new_pairs_raw.append((policy, f"{POLICY_PREFIX}{pooled_id:03d}_{arm}"))
        new_pairs_raw.append((f"{POLICY_PREFIX}{rid:03d}_P", f"{POLICY_PREFIX}{rid:03d}_C"))
        new_pairs_raw.append((f"{POLICY_PREFIX}{rid:03d}_Z", f"{POLICY_PREFIX}{rid:03d}_C"))
        new_pairs_raw.append((f"{POLICY_PREFIX}{rid:03d}_Z", f"{POLICY_PREFIX}{rid:03d}_P"))

    assert len(new_pairs_raw) == 492
    seen = set(comparisons)
    if len(seen) != len(comparisons):
        raise ValueError("Parent comparisons contain unexpected duplicates")
    for pair in new_pairs_raw:
        if pair in seen:
            raise ValueError(f"Duplicate comparison generated in conditional pool family: {pair}")
        comparisons.append(pair)
        seen.add(pair)

    comparator_summary = dict(
        common_comparators=list(COMMON_COMPARATORS),
        parent_mp_historical_roles=(parent_mp_freeze or {}).get("historical_roles"),
        new_comparison_breakdown=dict(
            common_comparator_pairs=360,
            within_recipe_representation_pairs=72,
            g3_vs_g1_context_pairs=36,
            day_vs_pooled_cap_pairs=24,
            total_new_comparisons=492,
        ),
    )
    return names, parent_avail, aliases, comparisons, comparator_summary


def run_aggregate_stage(
    cfg: dict[str, Any],
    out: Path,
    *,
    protocol_path: Path | None = None,
    deadline: float | None = None,
    root: Path = ROOT,
    n_boot_override: int | None = None,
) -> dict[str, Any]:
    out = Path(out)
    start = time.time()
    stage_dir = out / "shards" / "aggregate"
    stage_dir.mkdir(parents=True, exist_ok=True)
    state = _state_envelope("aggregate")
    save(stage_dir / "state.json", state)

    try:
        recipes = verify_budget_and_recipes(cfg)
        if deadline is None:
            deadline = start + _phase_wall_seconds(cfg, "aggregate_wall_seconds", 1200) - 30.0
        deadline_check(deadline)

        freeze = verify_freeze_barrier(cfg, out, protocol_path=protocol_path, root=root)
        freeze_sha = sha(out / "FINAL_FREEZE.json")
        (
            parent_mp_dir,
            parent_mp_freeze,
            parent_freeze_sha,
            stream_mc_dir,
            stream_mc_freeze,
            stream_freeze_sha,
        ) = verify_parent_and_stream_bindings(cfg, require_ledger=True)

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
            if (
                r_data.get("freeze_sha256") != freeze_sha
                or r_data.get("parent_freeze_sha256") != parent_freeze_sha
                or r_data.get("stream_parent_freeze_sha256") != stream_freeze_sha
            ):
                raise ValueError(f"Evaluate shard {shard} freeze SHA-256 mismatch")

            eval_s = r_data.get("evaluate_stream") or {}
            _, verified_eval_s = load_verified_parent_stream_bank(
                stream_mc_dir, stream_mc_freeze, "evaluate", seed, arm
            )
            if (
                eval_s.get("npz_sha256") != verified_eval_s["npz_sha256"]
                or eval_s.get("metadata_sha256") != verified_eval_s["metadata_sha256"]
            ):
                raise ValueError(f"Evaluate shard {shard} stream SHA-256 mismatch against stream parent")

            inst_r_path = out / "instances" / "evaluate" / f"{arm}_seed{seed}" / "receipt.json"
            if not inst_r_path.exists():
                raise ValueError(f"Missing evaluate instance receipt: {inst_r_path}")
            inst_r = json.loads(inst_r_path.read_text(encoding="utf-8"))
            if (
                inst_r.get("phase") != "evaluate"
                or inst_r.get("seed") != seed
                or inst_r.get("arm") != arm
                or inst_r.get("bank_npz_sha256") != verified_eval_s["npz_sha256"]
            ):
                raise ValueError(f"Evaluate instance receipt binding mismatch for {arm}_seed{seed}")

        parent_ledger_path = parent_mp_dir / "all_daily_ledger.npz"
        parent_span3_path = parent_mp_dir / "inference_span3.json"
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
                f"Parent ledger policy axis {old_ledger.shape[1]} differs from parent policy count {parent_policy_count}"
            )

        names, parent_avail, aliases, comparisons, comparator_summary = build_extended_family(
            parent_span3,
            recipes,
            parent_mp_freeze,
            expected_parent_policies=int(cfg.get("expected_parent_policies", 1040)),
            expected_parent_comparisons=int(cfg.get("expected_parent_comparisons", 4107)),
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
        assert total_policy_count == int(cfg.get("expected_parent_policies", 1040)) + 72
        assert all_ledger.shape == (5, total_policy_count, 35, 4)
        assert len(names) == total_policy_count and len(available) == total_policy_count
        assert np.array_equal(all_ledger[:, :parent_policy_count], old_ledger)

        nominal_coords = 11 * len(names) + 10 * len(comparisons)
        np.savez_compressed(
            out / "all_daily_ledger.npz",
            ledger=all_ledger,
            counts=old_counts,
            day_ids=old_days,
        )
        save(
            out / "all_policy_names.json",
            dict(
                names=names,
                available=available,
                aliases=[list(p) for p in aliases],
                comparisons=[list(p) for p in comparisons],
                comparator_summary=comparator_summary,
                parent_policy_count=parent_policy_count,
                new_policy_count=new_policy_count,
                parent_comparison_count=parent_comparison_count,
                new_comparison_count=len(comparisons) - parent_comparison_count,
                total_comparison_count=len(comparisons),
                nominal_family_size=nominal_coords,
            ),
        )

        weights_summary: dict[str, Any] = {}
        for phase in ("inner", "outer", "evaluate"):
            for seed in SEEDS:
                for arm in META_ARMS:
                    for recipe in recipes:
                        rid = int(recipe["id"])
                        rel = initializer_relpath(phase, arm, seed, rid)
                        rel_key = str(rel).replace("\\", "/")
                        init_data = json.loads((out / rel).read_text(encoding="utf-8"))
                        weights_summary[rel_key] = dict(
                            phase=phase,
                            seed=int(seed),
                            arm=str(arm),
                            id=rid,
                            groups=int(recipe["groups"]),
                            relief=float(recipe["relief"]),
                            cap_mode=str(recipe["cap_mode"]),
                            cuts=list(init_data["cuts"]),
                            status=init_data["status"],
                            optimal=bool(init_data["optimal"]),
                            numerical_fitted=bool(init_data["numerical_fitted"]),
                            actual_feasible=bool(init_data.get("actual_feasible", True)),
                            repaired_to_anchor=bool(init_data.get("repaired_to_anchor", False)),
                            fit_window=init_data["fit_window"],
                            fit_issue_count=int(init_data["fit_issue_count"]),
                            valid_fit_cells=int(init_data["valid_fit_cells"]),
                            last_label_release=init_data["last_label_release"],
                            episode_start=int(init_data["episode_start"]),
                            weights=init_data["weights"],
                            canonical_initial=init_data["canonical_initial"],
                            sha256=sha(out / rel),
                        )
        assert len(weights_summary) == 1080
        save(out / "all_initializer_weights.json", weights_summary)

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
        verify_parent_and_stream_bindings(cfg, require_ledger=True)

        phase_counts: dict[str, dict[str, int]] = {}
        for phase in ("inner", "outer", "evaluate"):
            completed_total = 0
            failed_total = 0
            for seed in SEEDS:
                for arm in META_ARMS:
                    r_inst = json.loads(
                        (out / "instances" / phase / f"{arm}_seed{seed}" / "receipt.json").read_text(
                            encoding="utf-8"
                        )
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
        all_complete = all(
            v["completed"] == expected_per_phase and v["failed"] == 0 for v in phase_counts.values()
        )
        completion = dict(
            status=(
                "COMPLETED_ALL_PREDEFINED_INSTANCES"
                if all_complete
                else "COMPLETED_WITH_PRESERVED_FAILURES"
            ),
            planned_recipes=len(recipes),
            planned_instances_per_phase=expected_per_phase,
            total_planned_instances=expected_per_phase * 3,
            complete_per_phase={p: v["completed"] for p, v in phase_counts.items()},
            failed_per_phase={p: v["failed"] for p, v in phase_counts.items()},
            phase_instance_accounting=phase_counts,
            total_initializers=1080,
            numerical_fits=720,
            anchor_declarations=360,
            all_predefined_instances_scored=all_complete,
            all_planned_instances_retained=True,
            scientific_qualification_used_to_filter=False,
            new_models_fitted=0,
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
    parser.add_argument(
        "--stage", choices=("history", "freeze", "evaluate", "aggregate"), required=True
    )
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
