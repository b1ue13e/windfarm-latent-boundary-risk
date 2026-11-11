"""Distributed multi-stage runner for the 96-recipe causally calibrated Meta-head campaign."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from repo_paths import Path, repository_root
import platform
import shutil
import sys
import time
import traceback
from typing import Any

ROOT = Path(repository_root())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import scipy
from threadpoolctl import threadpool_limits

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
from windfarm_moe.delayed_calibration_baselines import (
    DelayedCalibrationConfig,
    run_delayed_calibration,
)
from windfarm_moe.meta_action_stream import (
    build_phase_bank,
    join_banks,
    load_bank,
    prefix_sha256,
    save_bank,
)
from windfarm_moe.residual_meta import META_ARMS, build_meta_recipes

POLICY_PREFIX = "MC"
PARENT_POLICY_PREFIX = "MR"

CALIBRATION_SPECS: tuple[tuple[int, str, DelayedCalibrationConfig], ...] = (
    (0, "NONE", DelayedCalibrationConfig()),
    (1, "TRACKER_003", DelayedCalibrationConfig(method="tracker", target_event_rate=0.05, step_size=0.03)),
    (2, "TRACKER_010", DelayedCalibrationConfig(method="tracker", target_event_rate=0.05, step_size=0.10)),
    (3, "ACI_1008", DelayedCalibrationConfig(method="aci", window_steps=1008, target_event_rate=0.05, gamma=0.0003)),
)


def build_calibration_recipes() -> list[dict[str, Any]]:
    """Deterministic 96-recipe grid: 24 base Meta heads (0..23) x 4 calibration modes (0..3)."""
    base_recipes = build_meta_recipes()
    recipes: list[dict[str, Any]] = []
    for base in base_recipes:
        base_id = int(base["id"])
        for cal_id, cal_mode, cal_cfg in CALIBRATION_SPECS:
            rid = 4 * base_id + int(cal_id)
            assert rid == len(recipes)
            recipes.append(
                dict(
                    id=rid,
                    base_meta_id=base_id,
                    calibration_id=int(cal_id),
                    calibration_mode=str(cal_mode),
                    q=float(base["q"]),
                    leaves=int(base["leaves"]),
                    l2=float(base["l2"]),
                    base_config=dict(base["config"]),
                    calibration_config=asdict(cal_cfg),
                )
            )
    assert len(recipes) == 96
    return recipes


def stream_relpath(phase: str, arm: str, seed: int) -> Path:
    return Path("streams") / phase / f"{arm}_seed{seed}.npz"


def stream_metadata_relpath(phase: str, arm: str, seed: int) -> Path:
    return Path("streams") / phase / f"{arm}_seed{seed}_metadata.json"


CHECKPOINT_FILENAME = "recipe_checkpoints.jsonl"


def _init_checkpoint_jsonl(path: Path, header: dict[str, Any]) -> Path:
    path = Path(path)
    line = json.dumps(header, sort_keys=True, allow_nan=False) + "\n"
    with path.open("x", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())
    return path


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Checkpoint file does not exist: {path}")
    line = json.dumps(record, sort_keys=True, allow_nan=False) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())


def _checkpoint_phase_metrics(
    actions: np.ndarray,
    shortfall: np.ndarray,
    mask: np.ndarray,
    anchors: np.ndarray,
) -> dict[str, Any]:
    ledger, counts, _ = score_actions(actions, shortfall, mask, anchors)
    shared_count = int(counts.sum())
    totals_arr = ledger.sum(axis=0)
    totals = [float(x) for x in totals_arr.tolist()]
    if shared_count > 0:
        means: list[float | None] = [float(x / shared_count) for x in totals_arr.tolist()]
    else:
        means = [None, None, None, None]
    return dict(
        shared_count=shared_count,
        totals=dict(C=totals[0], R=totals[1], U=totals[2], V=totals[3]),
        means=dict(C=means[0], R=means[1], U=means[2], V=means[3]),
        totals_CRUV=totals,
        means_CRUV=means,
    )



def _state_envelope(stage: str, shard: int | None = None, seed: int | None = None, arm: str | None = None) -> dict[str, Any]:
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
        started_utc=datetime.now(timezone.utc).isoformat(),
        clock="source_issue+7<decision_issue",
        new_head_training=False,
        independent_confirmation=False,
    )


def _phase_wall_seconds(cfg: dict[str, Any], key: str) -> float:
    return float(_strict_int(cfg.get(key), key))


def _exact_value_match(actual_val: Any, exp_val: Any) -> bool:
    if exp_val is None:
        return actual_val is None
    if isinstance(exp_val, bool):
        return isinstance(actual_val, bool) and (actual_val is exp_val)
    if isinstance(exp_val, int):
        return (
            not isinstance(actual_val, (bool, np.bool_))
            and isinstance(actual_val, (int, np.integer))
            and int(actual_val) == exp_val
        )
    if isinstance(exp_val, float):
        return (
            not isinstance(actual_val, (bool, np.bool_))
            and isinstance(actual_val, (int, float, np.number))
            and float(actual_val) == exp_val
        )
    return actual_val == exp_val


def verify_budget_and_recipes(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    if _strict_int(cfg.get("max_candidates"), "max_candidates") != 96 or _strict_int(
        cfg.get("max_cpu_seconds"), "max_cpu_seconds"
    ) != 28800:
        raise ValueError("Authorized 96-candidate / 28800-CPU-second budget differs")

    hist_wall = _strict_int(cfg.get("history_wall_seconds"), "history_wall_seconds")
    eval_wall = _strict_int(cfg.get("evaluation_wall_seconds"), "evaluation_wall_seconds")
    freeze_wall = _strict_int(cfg.get("freeze_wall_seconds"), "freeze_wall_seconds")
    agg_wall = _strict_int(cfg.get("aggregate_wall_seconds"), "aggregate_wall_seconds")
    audit_wall = _strict_int(cfg.get("independent_audit_wall_seconds"), "independent_audit_wall_seconds")
    reserve_wall = _strict_int(cfg.get("local_retry_reserve_seconds"), "local_retry_reserve_seconds")
    prior_cpu = _strict_int(cfg.get("prior_accounted_cpu_seconds", 0), "prior_accounted_cpu_seconds")
    max_jobs = _strict_int(cfg.get("maximum_science_parallel_jobs", 15), "maximum_science_parallel_jobs")

    if hist_wall != 600:
        raise ValueError("Protocol history_wall_seconds must equal 600")
    if eval_wall != 900:
        raise ValueError("Protocol evaluation_wall_seconds must equal 900")
    if freeze_wall != 60:
        raise ValueError("Protocol freeze_wall_seconds must equal 60")
    if agg_wall != 1800:
        raise ValueError("Protocol aggregate_wall_seconds must equal 1800")
    if audit_wall != 600:
        raise ValueError("Protocol independent_audit_wall_seconds must equal 600")
    if prior_cpu < 0:
        raise ValueError("Protocol prior_accounted_cpu_seconds must be nonnegative")
    if reserve_wall < 0 or reserve_wall + prior_cpu != 3840:
        raise ValueError("Protocol local_retry_reserve_seconds + prior_accounted_cpu_seconds must equal 3840")
    if max_jobs != 15:
        raise ValueError("Protocol maximum_science_parallel_jobs must equal 15")

    total_phase_cpu = 15 * hist_wall + 15 * eval_wall + freeze_wall + agg_wall + audit_wall + reserve_wall + prior_cpu
    if total_phase_cpu != 28800 or total_phase_cpu != int(cfg["max_cpu_seconds"]):
        raise ValueError(f"Phase CPU budget sum {total_phase_cpu} != 28800")

    if "budget_reservation" in cfg:
        br = cfg["budget_reservation"]
        if not isinstance(br, dict):
            raise ValueError("Protocol budget_reservation must be a dict")
        if (
            _strict_int(br.get("new_candidates"), "budget_reservation.new_candidates") != 96
            or _strict_int(br.get("cpu_seconds"), "budget_reservation.cpu_seconds") != 28800
            or _strict_int(br.get("total_reserved_candidates"), "budget_reservation.total_reserved_candidates") != 1478
            or _strict_int(
                br.get("total_accounted_plus_open_reservations_cpu"),
                "budget_reservation.total_accounted_plus_open_reservations_cpu",
            )
            != 61287
            or _strict_int(br.get("global_cpu_limit_unchanged"), "budget_reservation.global_cpu_limit_unchanged")
            != 86400
            or not (61287 < 86400)
        ):
            raise ValueError("Protocol budget_reservation settlement values differ from authorized 61287/86400/1478")

    expected = build_calibration_recipes()
    recipes = cfg.get("recipes")
    if not isinstance(recipes, list) or len(recipes) != 96:
        raise ValueError("Protocol must declare exactly 96 recipes")

    top_keys = set(expected[0].keys())
    for idx, (rec, exp) in enumerate(zip(recipes, expected)):
        if not isinstance(rec, dict) or set(rec.keys()) != top_keys:
            raise ValueError(f"Recipe {idx} keys do not match exact deterministic 96-recipe schema")
        for k in ("id", "base_meta_id", "calibration_id", "calibration_mode", "q", "leaves", "l2"):
            if not _exact_value_match(rec[k], exp[k]):
                raise ValueError(f"Recipe {idx} field {k}={rec[k]!r} differs from {exp[k]!r}")
        for sub_name in ("base_config", "calibration_config"):
            sub_actual = rec.get(sub_name)
            sub_exp = exp[sub_name]
            if not isinstance(sub_actual, dict) or set(sub_actual.keys()) != set(sub_exp.keys()):
                raise ValueError(f"Recipe {idx} {sub_name} keys do not match exact deterministic schema")
            for k, exp_v in sub_exp.items():
                if not _exact_value_match(sub_actual[k], exp_v):
                    raise ValueError(f"Recipe {idx} {sub_name}.{k}={sub_actual[k]!r} differs from {exp_v!r}")
    return [
        dict(
            r,
            base_config=dict(r["base_config"]),
            calibration_config=dict(r["calibration_config"]),
        )
        for r in recipes
    ]


def verify_parent_bindings(cfg: dict[str, Any], *, require_ledger: bool = False) -> Path:
    if "parent_results" not in cfg:
        raise ValueError("Protocol missing parent_results")
    parent_dir = Path(cfg["parent_results"])
    freeze_path = parent_dir / "FINAL_FREEZE.json"
    exp_freeze_sha = cfg.get("parent_freeze_sha256")
    if not isinstance(exp_freeze_sha, str) or not exp_freeze_sha:
        raise ValueError("Protocol missing parent_freeze_sha256")
    if not freeze_path.exists() or sha(freeze_path) != exp_freeze_sha:
        raise ValueError("Parent FINAL_FREEZE.json missing or SHA-256 mismatch")

    exp_ledger_sha = cfg.get("parent_ledger_sha256")
    exp_span3_sha = cfg.get("parent_span3_sha256")
    if not isinstance(exp_ledger_sha, str) or not exp_ledger_sha:
        raise ValueError("Protocol missing parent_ledger_sha256")
    if not isinstance(exp_span3_sha, str) or not exp_span3_sha:
        raise ValueError("Protocol missing parent_span3_sha256")

    ledger_path = parent_dir / "all_daily_ledger.npz"
    span3_path = parent_dir / "inference_span3.json"
    if require_ledger or ledger_path.exists():
        if not ledger_path.exists() or sha(ledger_path) != exp_ledger_sha:
            raise ValueError("Parent all_daily_ledger.npz missing or SHA-256 mismatch")
    if require_ledger or span3_path.exists():
        if not span3_path.exists() or sha(span3_path) != exp_span3_sha:
            raise ValueError("Parent inference_span3.json missing or SHA-256 mismatch")
    return parent_dir


def verify_none_control_matches_parent(
    parent_dir: Path,
    phase: str,
    seed: int,
    arm: str,
    base_meta_id: int,
    actions: np.ndarray,
    ledger: np.ndarray,
) -> str:
    act_sha = prefix_sha256(actions)
    p_inst = parent_dir / "instances" / phase / f"{arm}_seed{seed}"
    p_rcpt = json.loads((p_inst / "receipt.json").read_text(encoding="utf-8"))
    p_daily = np.load(p_inst / "daily.npz")
    exp_act_sha = (p_rcpt.get("action_sha256") or {}).get(str(base_meta_id))
    if act_sha != exp_act_sha:
        raise ValueError(
            f"Raw NONE control action SHA-256 mismatch against parent {PARENT_POLICY_PREFIX}{base_meta_id:03d}_{arm} "
            f"in {phase}/{arm}_seed{seed}: {act_sha} != {exp_act_sha}"
        )
    if not np.array_equal(ledger, p_daily["ledger"][base_meta_id]):
        raise ValueError(
            f"Raw NONE control daily ledger mismatch against parent {PARENT_POLICY_PREFIX}{base_meta_id:03d}_{arm} "
            f"in {phase}/{arm}_seed{seed}"
        )
    return act_sha


def _write_phase_instance(
    out: Path,
    phase: str,
    seed: int,
    arm: str,
    recipes: list[dict[str, Any]],
    bank: dict[str, Any],
    actions_by_rid: dict[int, np.ndarray],
    meta_by_rid: dict[int, dict[str, Any]],
    errors_by_rid: dict[int, dict[str, str]],
    parent_dir: Path,
    extra_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    destination = out / "instances" / phase / f"{arm}_seed{seed}"
    destination.mkdir(parents=True, exist_ok=False)

    aa = bank["anchors"]
    yy = bank["shortfall"]
    mm = bank["mask"]
    ref_arr = bank["reference"]

    ref_led, counts, days = score_actions(ref_arr, yy, mm, aa)
    ids = [int(r["id"]) for r in recipes]
    array = np.full((len(ids), len(days), 4), np.nan, dtype=np.float64)

    status: dict[str, str] = {}
    point: dict[str, list[float]] = {}
    hashes: dict[str, str] = {}
    metadata: dict[str, dict[str, Any]] = {}
    errors: dict[str, dict[str, str]] = {}

    for i, recipe in enumerate(recipes):
        rid = int(recipe["id"])
        key = str(rid)
        if rid in errors_by_rid:
            status[key] = "FAILED_PRESERVED"
            errors[key] = dict(errors_by_rid[rid])
            continue
        if rid not in actions_by_rid:
            status[key] = "NOT_EVALUATED_PRESERVED"
            continue
        try:
            act = np.ascontiguousarray(actions_by_rid[rid], dtype=np.float64)
            ledger, counts_local, days_local = score_actions(act, yy, mm, aa)
            if ledger.shape != (len(days_local), 4) or not np.isfinite(ledger).all():
                raise ValueError("Invalid candidate ledger")
            if int(recipe["calibration_id"]) == 0:
                verify_none_control_matches_parent(
                    parent_dir, phase, seed, arm, int(recipe["base_meta_id"]), act, ledger
                )
            array[i] = ledger
            point[key] = (ledger.sum(axis=0) / counts_local.sum()).tolist()
            status[key] = "COMPLETED"
            hashes[key] = prefix_sha256(act)
            metadata[key] = dict(meta_by_rid.get(rid) or {})
        except Exception as exc:
            status[key] = "FAILED_PRESERVED"
            errors[key] = dict(error=repr(exc), traceback=traceback.format_exc())

    np.savez_compressed(destination / "daily.npz", ledger=array, reference=ref_led, counts=counts, days=days)
    b_meta = bank["metadata"]
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
        source_manifest_sha256=b_meta.get("source_manifest_sha256"),
        parent_profile_sha256=b_meta.get("parent_profile_sha256"),
        bank_npz_sha256=b_meta.get("npz_sha256"),
        bank_raw_actions_sha256=b_meta.get("raw_actions_sha256"),
        complete_expected=len(recipes),
        completed=sum(v == "COMPLETED" for v in status.values()),
        scientific_qualification_used_to_filter=False,
    )
    if extra_receipt:
        receipt.update(extra_receipt)
    save(destination / "receipt.json", receipt)
    return dict(
        phase=phase,
        seed=seed,
        arm=arm,
        completed=receipt["completed"],
        expected=len(recipes),
    )


def _calibrate_single_recipe_stream(
    recipe: dict[str, Any],
    raw_stream: np.ndarray,
    shortfall: np.ndarray,
    mask: np.ndarray,
    anchors: np.ndarray,
) -> tuple[np.ndarray, DelayedCalibrationConfig, dict[str, Any]]:
    cal_id = int(recipe["calibration_id"])
    cal_cfg = DelayedCalibrationConfig(**recipe["calibration_config"])
    if cal_id == 0:
        actions = np.ascontiguousarray(raw_stream, dtype=np.float64)
        actions.setflags(write=False)
        info = dict(
            method="NONE",
            processed_feedback_issues=0,
            observed_feedback_issues=0,
            observed_feedback_cells=0,
        )
        return actions, cal_cfg, info

    res = run_delayed_calibration(
        raw_stream,
        shortfall,
        mask,
        anchors,
        cal_cfg,
        save_trace=False,
    )
    first_check = min(8, len(anchors))
    if first_check > 0 and len(anchors) >= 8 and int(anchors[7]) <= int(anchors[0]) + 7:
        if not np.array_equal(res.actions[:first_check], raw_stream[:first_check]):
            raise ValueError("First 8 cold-start steps differ from uncalibrated raw Meta actions")
    elif len(anchors) > 0 and not np.array_equal(res.actions[:1], raw_stream[:1]):
        raise ValueError("Initial cold-start step differs from uncalibrated raw Meta action")
    info = dict(
        method=res.method,
        processed_feedback_issues=int(res.processed_feedback_issues),
        observed_feedback_issues=int(res.observed_feedback_issues),
        observed_feedback_cells=int(res.observed_feedback_cells),
    )
    return res.actions, cal_cfg, info


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

        parent_dir = verify_parent_bindings(cfg, require_ledger=False)

        deadline_check(deadline)
        inner_raw_bank = build_phase_bank(parent_dir, "inner", seed, arm, root=root)
        inner_npz_rel = stream_relpath("inner", arm, seed)
        inner_manifest = save_bank(out / inner_npz_rel, inner_raw_bank)
        inner_bank = load_bank(out / inner_npz_rel, expected_npz_sha256=inner_manifest["npz_sha256"])

        deadline_check(deadline)
        outer_raw_bank = build_phase_bank(parent_dir, "outer", seed, arm, root=root)
        outer_npz_rel = stream_relpath("outer", arm, seed)
        outer_manifest = save_bank(out / outer_npz_rel, outer_raw_bank)
        outer_bank = load_bank(out / outer_npz_rel, expected_npz_sha256=outer_manifest["npz_sha256"])

        hist_bank = join_banks([inner_bank, outer_bank])
        n_inner = len(inner_bank["anchors"])
        n_outer = len(outer_bank["anchors"])
        assert len(hist_bank["anchors"]) == n_inner + n_outer
        if int(outer_bank["anchors"][0]) - int(inner_bank["anchors"][-1]) <= 7:
            raise ValueError("Joined history bank did not preserve the 7-step causal gap between inner and outer")

        expected_hist_grid = cfg.get("expected_historical_grid", True)
        if expected_hist_grid and n_inner == 850 and n_outer == 1289:
            if int(inner_bank["anchors"][0]) != 28087 or int(inner_bank["anchors"][-1]) != 28936:
                raise ValueError("Inner anchor boundaries differ from 28087..28936")
            if int(outer_bank["anchors"][0]) != 28944 or int(outer_bank["anchors"][-1]) != 30232:
                raise ValueError("Outer anchor boundaries differ from 28944..30232")

        inner_actions: dict[int, np.ndarray] = {}
        outer_actions: dict[int, np.ndarray] = {}
        inner_meta: dict[int, dict[str, Any]] = {}
        outer_meta: dict[int, dict[str, Any]] = {}
        inner_errors: dict[int, dict[str, str]] = {}
        outer_errors: dict[int, dict[str, str]] = {}
        history_policy_shas: dict[str, str] = {}

        checkpoint_path = _init_checkpoint_jsonl(
            shard_dir / CHECKPOINT_FILENAME,
            dict(
                record_type="HEADER",
                schema="meta-calibration-recipe-checkpoint-v1",
                stage="history",
                shard=shard,
                seed=seed,
                arm=arm,
                study_id=cfg.get("study_id"),
                protocol_sha256=protocol_sha,
                source_commit=state["source_commit"],
                source_versions=source_versions,
                parent_freeze_sha256=cfg["parent_freeze_sha256"],
                inner_npz_sha256=inner_manifest["npz_sha256"],
                outer_npz_sha256=outer_manifest["npz_sha256"],
                recipes_expected=len(recipes),
            ),
        )

        for recipe in recipes:
            deadline_check(deadline)
            rid = int(recipe["id"])
            base_id = int(recipe["base_meta_id"])
            key = str(rid)
            try:
                full_act, _, cal_info = _calibrate_single_recipe_stream(
                    recipe,
                    hist_bank["raw_actions"][base_id],
                    hist_bank["shortfall"],
                    hist_bank["mask"],
                    hist_bank["anchors"],
                )
                act_in = full_act[:n_inner]
                act_out = full_act[n_inner:]
                if int(recipe["calibration_id"]) == 0:
                    if not np.array_equal(act_in, inner_bank["raw_actions"][base_id]) or not np.array_equal(
                        act_out, outer_bank["raw_actions"][base_id]
                    ):
                        raise ValueError(f"NONE recipe {rid} trajectory differs from raw Meta actions")
                full_sha = prefix_sha256(full_act)
                in_sha = prefix_sha256(act_in)
                out_sha = prefix_sha256(act_out)
                in_metrics = _checkpoint_phase_metrics(
                    act_in,
                    inner_bank["shortfall"],
                    inner_bank["mask"],
                    inner_bank["anchors"],
                )
                out_metrics = _checkpoint_phase_metrics(
                    act_out,
                    outer_bank["shortfall"],
                    outer_bank["mask"],
                    outer_bank["anchors"],
                )
                history_policy_shas[key] = full_sha
                inner_actions[rid] = act_in
                outer_actions[rid] = act_out
                common_meta = dict(
                    base_meta_id=base_id,
                    calibration_id=int(recipe["calibration_id"]),
                    calibration_mode=str(recipe["calibration_mode"]),
                    q=float(recipe["q"]),
                    leaves=int(recipe["leaves"]),
                    l2=float(recipe["l2"]),
                    base_config=dict(recipe["base_config"]),
                    calibration_config=dict(recipe["calibration_config"]),
                    history_full_action_sha256=full_sha,
                    calibration_trace_summary=cal_info,
                )
                inner_meta[rid] = dict(
                    common_meta,
                    raw_action_sha256=inner_bank["metadata"]["raw_action_sha256"][str(base_id)],
                    model_sha256=inner_bank["metadata"]["model_sha256"][str(base_id)],
                )
                outer_meta[rid] = dict(
                    common_meta,
                    raw_action_sha256=outer_bank["metadata"]["raw_action_sha256"][str(base_id)],
                    model_sha256=outer_bank["metadata"]["model_sha256"][str(base_id)],
                )
                append_jsonl(
                    checkpoint_path,
                    dict(
                        record_type="RECIPE",
                        stage="history",
                        shard=shard,
                        seed=seed,
                        arm=arm,
                        id=rid,
                        base_meta_id=base_id,
                        calibration_id=int(recipe["calibration_id"]),
                        calibration_mode=str(recipe["calibration_mode"]),
                        success=True,
                        status="ACTION_GENERATED_METRICS_COMPUTED_PENDING_POSTCHECK",
                        final_none_control_validated=False,
                        error=None,
                        action_sha256=dict(inner=in_sha, outer=out_sha),
                        prefix_sha256=full_sha,
                        history_full_action_sha256=full_sha,
                        inner=in_metrics,
                        outer=out_metrics,
                        evaluate=None,
                    ),
                )
            except Exception as exc:
                err_dict = dict(error=repr(exc), traceback=traceback.format_exc())
                inner_errors[rid] = err_dict
                outer_errors[rid] = err_dict
                append_jsonl(
                    checkpoint_path,
                    dict(
                        record_type="RECIPE",
                        stage="history",
                        shard=shard,
                        seed=seed,
                        arm=arm,
                        id=rid,
                        base_meta_id=base_id,
                        calibration_id=int(recipe["calibration_id"]),
                        calibration_mode=str(recipe["calibration_mode"]),
                        success=False,
                        status="RECIPE_FAILED",
                        final_none_control_validated=False,
                        error=repr(exc),
                        action_sha256=None,
                        prefix_sha256=None,
                        history_full_action_sha256=None,
                        inner=None,
                        outer=None,
                        evaluate=None,
                    ),
                )

        extra_hist = dict(history_full_action_sha256=history_policy_shas)
        sum_inner = _write_phase_instance(
            out,
            "inner",
            seed,
            arm,
            recipes,
            inner_bank,
            inner_actions,
            inner_meta,
            inner_errors,
            parent_dir,
            extra_receipt=extra_hist,
        )
        sum_outer = _write_phase_instance(
            out,
            "outer",
            seed,
            arm,
            recipes,
            outer_bank,
            outer_actions,
            outer_meta,
            outer_errors,
            parent_dir,
            extra_receipt=extra_hist,
        )
        phase_summaries = [sum_inner, sum_outer]

        streams_recorded = {
            str(inner_npz_rel).replace("\\", "/"): dict(
                phase="inner",
                seed=seed,
                arm=arm,
                npz_sha256=inner_manifest["npz_sha256"],
                metadata_path=str(stream_metadata_relpath("inner", arm, seed)).replace("\\", "/"),
                metadata_sha256=inner_manifest["metadata_sha256"],
                raw_actions_sha256=inner_manifest["raw_actions_sha256"],
                raw_action_sha256=inner_bank["metadata"]["raw_action_sha256"],
            ),
            str(outer_npz_rel).replace("\\", "/"): dict(
                phase="outer",
                seed=seed,
                arm=arm,
                npz_sha256=outer_manifest["npz_sha256"],
                metadata_path=str(stream_metadata_relpath("outer", arm, seed)).replace("\\", "/"),
                metadata_sha256=outer_manifest["metadata_sha256"],
                raw_actions_sha256=outer_manifest["raw_actions_sha256"],
                raw_action_sha256=outer_bank["metadata"]["raw_action_sha256"],
            ),
        }

        shard_receipt = dict(
            status="COMPLETED",
            stage="history",
            shard=shard,
            seed=seed,
            arm=arm,
            protocol_sha256=protocol_sha,
            source_versions=source_versions,
            parent_freeze_sha256=cfg["parent_freeze_sha256"],
            streams=streams_recorded,
            joined_history_raw_action_sha256=hist_bank["metadata"]["raw_action_sha256"],
            joined_history_raw_actions_sha256=hist_bank["metadata"]["raw_actions_sha256"],
            history_full_action_sha256=history_policy_shas,
            recipes_completed=len(history_policy_shas),
            recipes_expected=len(recipes),
            phase_summaries=phase_summaries,
            new_models_fitted=0,
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


def history_summary(points: np.ndarray, recipes: list[dict[str, Any]]) -> dict[str, Any]:
    complete = np.isfinite(points).all(axis=(1, 2, 3))
    roles: dict[str, dict[str, Any]] = {}
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
        selection_scope="Historical outer minimum_C/minimum_maxV per arm (C/P/Z) without qualification filter; all 96 recipes still scored in evaluation",
    )


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
            deadline = start + _phase_wall_seconds(cfg, "freeze_wall_seconds") - 30.0
        deadline_check(deadline)

        verify_parent_bindings(cfg, require_ledger=False)
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
        all_history_policy_shas: dict[str, dict[str, str]] = {}
        all_instance_receipts: dict[str, str] = {}

        for shard in range(15):
            seed, arm = shard_assignment(shard)
            shard_key = f"{arm}_seed{seed}"
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
            if r_data.get("parent_freeze_sha256") != cfg["parent_freeze_sha256"]:
                raise ValueError(f"History shard {shard} parent_freeze_sha256 differs from current protocol")

            streams = r_data.get("streams") or {}
            if len(streams) != 2:
                raise ValueError(f"History shard {shard} receipt must bind inner and outer stream banks")
            for phase in ("inner", "outer"):
                s_rel = str(stream_relpath(phase, arm, seed)).replace("\\", "/")
                m_rel = str(stream_metadata_relpath(phase, arm, seed)).replace("\\", "/")
                if s_rel not in streams:
                    raise ValueError(f"Missing stream {s_rel} in history shard {shard} receipt")
                s_entry = streams[s_rel]
                s_full = out / s_rel
                m_full = out / m_rel
                if not s_full.exists() or not m_full.exists():
                    raise ValueError(f"Missing stream bank file or metadata on disk: {s_full}")
                if sha(s_full) != s_entry.get("npz_sha256") or sha(m_full) != s_entry.get("metadata_sha256"):
                    raise ValueError(f"Stream bank SHA-256 mismatch against history shard {shard} receipt for {s_rel}")
                loaded = load_bank(
                    s_full,
                    expected_npz_sha256=s_entry["npz_sha256"],
                    expected_metadata_sha256=s_entry["metadata_sha256"],
                )
                if loaded["metadata"].get("raw_action_sha256") != s_entry.get("raw_action_sha256") or len(
                    s_entry.get("raw_action_sha256") or {}
                ) != 24:
                    raise ValueError(f"Stream bank 24 raw action SHA-256 mismatch for {s_rel}")
                all_streams[s_rel] = dict(s_entry)

                inst_rcpt_rel = f"instances/{phase}/{arm}_seed{seed}/receipt.json"
                inst_rcpt_full = out / inst_rcpt_rel
                if not inst_rcpt_full.exists():
                    raise ValueError(f"Missing history instance receipt: {inst_rcpt_full}")
                all_instance_receipts[inst_rcpt_rel] = sha(inst_rcpt_full)

            hist_shas = r_data.get("history_full_action_sha256") or {}
            if not isinstance(hist_shas, dict):
                raise ValueError(f"Invalid history_full_action_sha256 in shard {shard}")
            all_history_policy_shas[shard_key] = {str(k): str(v) for k, v in hist_shas.items()}
            shard_receipts.append(r_data)

        assert len(all_streams) == 30
        assert len(all_history_policy_shas) == 15
        assert len(all_instance_receipts) == 30

        for phase in ("inner", "outer"):
            points, _ = collect(out, phase, recipes)
            np.save(out / f"{phase}_points.npy", points, allow_pickle=False)
            save(out / f"{phase}_selection.json", history_summary(points, recipes))

        if (out / "FINAL_FREEZE.json").exists() or (out / "EVALUATION_OPEN.json").exists():
            raise FileExistsError("FINAL_FREEZE.json or EVALUATION_OPEN.json already exists")
        freeze_payload = dict(
            time_utc=datetime.now(timezone.utc).isoformat(),
            study_id=cfg.get("study_id", "meta_calibration_20261025_v1"),
            source_commit=os.environ.get("CAMPAIGN_RELEASE", "LOCAL_SYNTHETIC"),
            protocol_sha256=protocol_sha,
            source_versions=source_versions,
            parent_freeze_sha256=cfg["parent_freeze_sha256"],
            parent_ledger_sha256=cfg["parent_ledger_sha256"],
            parent_span3_sha256=cfg["parent_span3_sha256"],
            recipes=recipes,
            historical_roles=json.loads((out / "outer_selection.json").read_text(encoding="utf-8")),
            all_streams=all_streams,
            all_history_policy_shas=all_history_policy_shas,
            all_instance_receipts=all_instance_receipts,
            history_shard_count=len(shard_receipts),
            selection_scope="Historical outer minimum_C/minimum_maxV per arm (C/P/Z); no qualification filter; all 96 evaluated",
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


def verify_freeze_barrier(cfg: dict[str, Any], out: Path, *, protocol_path: Path | None = None, root: Path = ROOT) -> dict[str, Any]:
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
    shard_key = f"{arm}_seed{seed}"
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
        parent_dir = verify_parent_bindings(cfg, require_ledger=False)

        all_streams = freeze.get("all_streams") or {}
        all_inst_rcpts = freeze.get("all_instance_receipts") or {}
        frozen_hist_shas = (freeze.get("all_history_policy_shas") or {}).get(shard_key)
        if not isinstance(frozen_hist_shas, dict):
            raise ValueError(f"Missing frozen history policy SHAs for {shard_key} in FINAL_FREEZE.json")

        loaded_hist_banks: list[dict[str, Any]] = []
        for phase in ("inner", "outer"):
            s_rel = str(stream_relpath(phase, arm, seed)).replace("\\", "/")
            if s_rel not in all_streams:
                raise ValueError(f"Frozen stream entry missing in FINAL_FREEZE: {s_rel}")
            s_entry = all_streams[s_rel]
            b_loaded = load_bank(
                out / s_rel,
                expected_npz_sha256=s_entry["npz_sha256"],
                expected_metadata_sha256=s_entry["metadata_sha256"],
            )
            if b_loaded["metadata"].get("raw_action_sha256") != s_entry.get("raw_action_sha256"):
                raise ValueError(f"Frozen historical bank raw_action_sha256 mismatch for {s_rel}")
            inst_rel = f"instances/{phase}/{arm}_seed{seed}/receipt.json"
            if inst_rel not in all_inst_rcpts or sha(out / inst_rel) != all_inst_rcpts[inst_rel]:
                raise ValueError(f"Historical instance receipt missing or modified since freeze: {inst_rel}")
            loaded_hist_banks.append(b_loaded)

        hist_bank = join_banks(loaded_hist_banks)
        n_hist = len(hist_bank["anchors"])

        deadline_check(deadline)
        eval_raw_bank = build_phase_bank(parent_dir, "evaluate", seed, arm, root=root)
        eval_npz_rel = stream_relpath("evaluate", arm, seed)
        eval_manifest = save_bank(out / eval_npz_rel, eval_raw_bank)
        eval_bank = load_bank(out / eval_npz_rel, expected_npz_sha256=eval_manifest["npz_sha256"])

        expected_len = int(cfg.get("expected_evaluation_anchors", 5033))
        expected_valid = int(cfg.get("expected_evaluation_valid_cells", 672939))
        if len(eval_bank["anchors"]) != expected_len or int(eval_bank["mask"].sum()) != expected_valid:
            raise ValueError("Evaluation population differs from expected counts")

        combined_bank = join_banks([hist_bank, eval_bank])
        if int(eval_bank["anchors"][0]) - int(hist_bank["anchors"][-1]) <= 7:
            raise ValueError("Combined history+evaluate bank did not preserve the 7-step causal gap")

        eval_actions: dict[int, np.ndarray] = {}
        eval_meta: dict[int, dict[str, Any]] = {}
        eval_errors: dict[int, dict[str, str]] = {}
        verified_prefix_shas: dict[str, str] = {}

        checkpoint_path = _init_checkpoint_jsonl(
            shard_dir / CHECKPOINT_FILENAME,
            dict(
                record_type="HEADER",
                schema="meta-calibration-recipe-checkpoint-v1",
                stage="evaluate",
                shard=shard,
                seed=seed,
                arm=arm,
                study_id=cfg.get("study_id"),
                protocol_sha256=freeze.get("protocol_sha256"),
                freeze_sha256=sha(out / "FINAL_FREEZE.json"),
                source_commit=state["source_commit"],
                source_versions=freeze.get("source_versions"),
                parent_freeze_sha256=cfg["parent_freeze_sha256"],
                evaluate_npz_sha256=eval_manifest["npz_sha256"],
                recipes_expected=len(recipes),
            ),
        )

        for recipe in recipes:
            deadline_check(deadline)
            rid = int(recipe["id"])
            base_id = int(recipe["base_meta_id"])
            key = str(rid)
            prefix_digest: str | None = None
            eval_sha: str | None = None
            try:
                if key not in frozen_hist_shas:
                    raise ValueError(f"Recipe {rid} missing frozen history prefix SHA-256")
                full_act, _, cal_info = _calibrate_single_recipe_stream(
                    recipe,
                    combined_bank["raw_actions"][base_id],
                    combined_bank["shortfall"],
                    combined_bank["mask"],
                    combined_bank["anchors"],
                )
                hist_prefix = full_act[:n_hist]
                prefix_digest = prefix_sha256(hist_prefix)
                if prefix_digest != frozen_hist_shas[key]:
                    raise ValueError(
                        f"History prefix SHA-256 mismatch for recipe {rid} on {shard_key}: "
                        f"{prefix_digest} != {frozen_hist_shas[key]}"
                    )
                verified_prefix_shas[key] = prefix_digest
                act_eval = full_act[n_hist:]
                eval_sha = prefix_sha256(act_eval)
                if int(recipe["calibration_id"]) == 0 and not np.array_equal(
                    act_eval, eval_bank["raw_actions"][base_id]
                ):
                    raise ValueError(f"NONE recipe {rid} evaluate trajectory differs from raw Meta actions")
                eval_metrics = _checkpoint_phase_metrics(
                    act_eval,
                    eval_bank["shortfall"],
                    eval_bank["mask"],
                    eval_bank["anchors"],
                )
                eval_actions[rid] = act_eval
                eval_meta[rid] = dict(
                    base_meta_id=base_id,
                    calibration_id=int(recipe["calibration_id"]),
                    calibration_mode=str(recipe["calibration_mode"]),
                    q=float(recipe["q"]),
                    leaves=int(recipe["leaves"]),
                    l2=float(recipe["l2"]),
                    base_config=dict(recipe["base_config"]),
                    calibration_config=dict(recipe["calibration_config"]),
                    raw_action_sha256=eval_bank["metadata"]["raw_action_sha256"][str(base_id)],
                    model_sha256=eval_bank["metadata"]["model_sha256"][str(base_id)],
                    verified_history_prefix_sha256=prefix_digest,
                    calibration_trace_summary=cal_info,
                )
                append_jsonl(
                    checkpoint_path,
                    dict(
                        record_type="RECIPE",
                        stage="evaluate",
                        shard=shard,
                        seed=seed,
                        arm=arm,
                        id=rid,
                        base_meta_id=base_id,
                        calibration_id=int(recipe["calibration_id"]),
                        calibration_mode=str(recipe["calibration_mode"]),
                        success=True,
                        status="ACTION_GENERATED_METRICS_COMPUTED_PENDING_POSTCHECK",
                        final_none_control_validated=False,
                        error=None,
                        action_sha256=eval_sha,
                        prefix_sha256=prefix_digest,
                        verified_history_prefix_sha256=prefix_digest,
                        inner=None,
                        outer=None,
                        evaluate=eval_metrics,
                    ),
                )
            except Exception as exc:
                eval_errors[rid] = dict(error=repr(exc), traceback=traceback.format_exc())
                append_jsonl(
                    checkpoint_path,
                    dict(
                        record_type="RECIPE",
                        stage="evaluate",
                        shard=shard,
                        seed=seed,
                        arm=arm,
                        id=rid,
                        base_meta_id=base_id,
                        calibration_id=int(recipe["calibration_id"]),
                        calibration_mode=str(recipe["calibration_mode"]),
                        success=False,
                        status="RECIPE_FAILED",
                        final_none_control_validated=False,
                        error=repr(exc),
                        action_sha256=eval_sha,
                        prefix_sha256=prefix_digest,
                        verified_history_prefix_sha256=None,
                        inner=None,
                        outer=None,
                        evaluate=None,
                    ),
                )

        summary = _write_phase_instance(
            out,
            "evaluate",
            seed,
            arm,
            recipes,
            eval_bank,
            eval_actions,
            eval_meta,
            eval_errors,
            parent_dir,
            extra_receipt=dict(verified_history_prefix_sha256=verified_prefix_shas),
        )

        eval_stream_record = dict(
            phase="evaluate",
            seed=seed,
            arm=arm,
            npz_path=str(eval_npz_rel).replace("\\", "/"),
            npz_sha256=eval_manifest["npz_sha256"],
            metadata_path=str(stream_metadata_relpath("evaluate", arm, seed)).replace("\\", "/"),
            metadata_sha256=eval_manifest["metadata_sha256"],
            raw_actions_sha256=eval_manifest["raw_actions_sha256"],
            raw_action_sha256=eval_bank["metadata"]["raw_action_sha256"],
        )

        shard_receipt = dict(
            status="COMPLETED",
            stage="evaluate",
            shard=shard,
            seed=seed,
            arm=arm,
            freeze_sha256=sha(out / "FINAL_FREEZE.json"),
            parent_freeze_sha256=cfg["parent_freeze_sha256"],
            evaluation_manifest_sha256=eval_bank["metadata"].get("source_manifest_sha256"),
            parent_profile_sha256=eval_bank["metadata"].get("parent_profile_sha256"),
            evaluate_stream=eval_stream_record,
            verified_history_prefix_count=len(verified_prefix_shas),
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
    *,
    expected_parent_policies: int = 680,
    expected_parent_comparisons: int = 2199,
) -> tuple[list[str], list[bool], list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str]]]:
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

    for required_parent in ("REF", "R0182_P", "GUARDED_FIXED_P"):
        if required_parent not in parent_names:
            raise ValueError(f"Parent family missing required comparator policy {required_parent!r}")
    for base_id in range(24):
        for arm in META_ARMS:
            mr_name = f"{PARENT_POLICY_PREFIX}{base_id:03d}_{arm}"
            if mr_name not in parent_names:
                raise ValueError(f"Parent family missing required raw Meta policy {mr_name!r}")

    raw_comps = fd.get("comparisons")
    if not isinstance(raw_comps, list) or not raw_comps:
        raise ValueError("Parent family_definition missing comparisons")
    if len(raw_comps) != int(expected_parent_comparisons):
        raise ValueError(f"Expected {int(expected_parent_comparisons)} parent comparisons, got {len(raw_comps)}")

    def map_pair(pair: list[Any] | tuple[Any, Any]) -> tuple[str, str]:
        l, r = pair
        ln = parent_names[int(l)] if isinstance(l, int) else str(l)
        rn = parent_names[int(r)] if isinstance(r, int) else str(r)
        return (ln, rn)

    comparisons: list[tuple[str, str]] = [map_pair(p) for p in raw_comps]
    aliases: list[tuple[str, str]] = [map_pair(p) for p in (fd.get("frozen_aliases") or [])]

    names = list(parent_names)
    new_aliases: list[tuple[str, str]] = []
    for r in recipes:
        rid = int(r["id"])
        base_id = int(r["base_meta_id"])
        cal_id = int(r["calibration_id"])
        for arm in META_ARMS:
            mc_name = f"{POLICY_PREFIX}{rid:03d}_{arm}"
            names.append(mc_name)
            if cal_id == 0:
                new_aliases.append((mc_name, f"{PARENT_POLICY_PREFIX}{base_id:03d}_{arm}"))

    assert len(new_aliases) == 72
    aliases.extend(new_aliases)

    new_pairs: list[tuple[str, str]] = []
    for r in recipes:
        rid = int(r["id"])
        base_id = int(r["base_meta_id"])
        for arm in META_ARMS:
            policy = f"{POLICY_PREFIX}{rid:03d}_{arm}"
            parent_mr = f"{PARENT_POLICY_PREFIX}{base_id:03d}_{arm}"
            for comparator in ("REF", "R0182_P", "GUARDED_FIXED_P", parent_mr):
                new_pairs.append((policy, comparator))
        # Within-config representation pairs: P vs C, Z vs C, Z vs P
        new_pairs.append((f"{POLICY_PREFIX}{rid:03d}_P", f"{POLICY_PREFIX}{rid:03d}_C"))
        new_pairs.append((f"{POLICY_PREFIX}{rid:03d}_Z", f"{POLICY_PREFIX}{rid:03d}_C"))
        new_pairs.append((f"{POLICY_PREFIX}{rid:03d}_Z", f"{POLICY_PREFIX}{rid:03d}_P"))

    assert len(new_pairs) == 1440
    seen = set(comparisons)
    if len(seen) != len(comparisons):
        raise ValueError("Parent comparisons contain unexpected duplicates")
    for pair in new_pairs:
        if pair in seen:
            raise ValueError(f"Duplicate comparison pair encountered: {pair}")
        comparisons.append(pair)
        seen.add(pair)

    return names, parent_avail, aliases, comparisons, new_aliases


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
            deadline = start + _phase_wall_seconds(cfg, "aggregate_wall_seconds") - 30.0
        deadline_check(deadline)

        freeze = verify_freeze_barrier(cfg, out, protocol_path=protocol_path, root=root)
        freeze_sha = sha(out / "FINAL_FREEZE.json")
        parent_dir = verify_parent_bindings(cfg, require_ledger=True)

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
            if r_data.get("parent_freeze_sha256") != cfg["parent_freeze_sha256"]:
                raise ValueError(f"Evaluate shard {shard} parent_freeze_sha256 mismatch")

            eval_s = r_data.get("evaluate_stream") or {}
            s_rel = str(stream_relpath("evaluate", arm, seed)).replace("\\", "/")
            if eval_s.get("npz_path") != s_rel:
                raise ValueError(f"Evaluate shard {shard} stream path mismatch: {eval_s.get('npz_path')} != {s_rel}")
            load_bank(
                out / s_rel,
                expected_npz_sha256=eval_s.get("npz_sha256"),
                expected_metadata_sha256=eval_s.get("metadata_sha256"),
            )

            inst_r_path = out / "instances" / "evaluate" / f"{arm}_seed{seed}" / "receipt.json"
            if not inst_r_path.exists():
                raise ValueError(f"Missing evaluate instance receipt: {inst_r_path}")
            inst_r = json.loads(inst_r_path.read_text(encoding="utf-8"))
            if (
                inst_r.get("phase") != "evaluate"
                or inst_r.get("seed") != seed
                or inst_r.get("arm") != arm
                or inst_r.get("bank_npz_sha256") != eval_s.get("npz_sha256")
            ):
                raise ValueError(f"Evaluate instance receipt binding mismatch for {arm}_seed{seed}")

        parent_ledger_path = parent_dir / "all_daily_ledger.npz"
        parent_span3_path = parent_dir / "inference_span3.json"
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

        names, parent_avail, aliases, comparisons, new_aliases = build_extended_family(
            parent_span3,
            recipes,
            expected_parent_policies=int(cfg.get("expected_parent_policies", 680)),
            expected_parent_comparisons=int(cfg.get("expected_parent_comparisons", 2199)),
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
        assert new_policy_count == 288
        assert total_policy_count == int(cfg.get("expected_parent_policies", 680)) + 288
        assert all_ledger.shape == (5, total_policy_count, 35, 4)
        assert len(names) == total_policy_count and len(available) == total_policy_count
        assert np.array_equal(all_ledger[:, :parent_policy_count], old_ledger)

        # Verify whole 5-fit daily ledger bitwise equality for all 72 new NONE control aliases BEFORE infer_campaign
        name_to_idx = {n: i for i, n in enumerate(names)}
        for left_name, right_name in new_aliases:
            li = name_to_idx[left_name]
            ri = name_to_idx[right_name]
            if available[li] and available[ri]:
                if not np.array_equal(all_ledger[:, li], all_ledger[:, ri]):
                    raise ValueError(
                        f"NONE control alias {left_name} -> {right_name} does not have bitwise identical 5-fit daily ledger"
                    )

        nominal_coords = 11 * len(names) + 10 * len(comparisons)
        if len(names) == 968 and len(comparisons) == 3639:
            assert nominal_coords == 47038

        np.savez_compressed(out / "all_daily_ledger.npz", ledger=all_ledger, counts=old_counts, day_ids=old_days)
        save(
            out / "all_policy_names.json",
            dict(
                names=names,
                available=available,
                aliases=[list(p) for p in aliases],
                new_none_aliases=[list(p) for p in new_aliases],
                comparisons=[list(p) for p in comparisons],
                parent_policy_count=parent_policy_count,
                new_policy_count=new_policy_count,
                parent_comparison_count=parent_comparison_count,
                total_comparison_count=len(comparisons),
                nominal_family_size=nominal_coords,
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
        verify_parent_bindings(cfg, require_ledger=True)

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
        assert expected_per_phase == 1440
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
