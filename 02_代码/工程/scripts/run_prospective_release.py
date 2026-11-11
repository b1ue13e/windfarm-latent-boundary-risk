"""Distributed multi-stage causal runner for the 24-recipe prospective release campaign.

Implements S0 source/clock/support verification, 4-snapshot (A/B/C/D) causal historical
fitting and 3-window forward validation, exclusive pre-evaluation freeze barrier,
post-freeze 35-day evaluation with canonical endpoint daily-ledger alias preservation,
and full 1256-policy / 5697-comparison / 70786-coordinate stable contrast inference.
"""
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
from typing import Any, Mapping, Sequence

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
)
from scripts.run_residual_meta import _strict_int, shard_assignment
from windfarm_moe.meta_action_stream import prefix_sha256
from windfarm_moe.release_bank import (
    COST_RECIPE_ID,
    RELEASE_LAG_STEPS,
    SAFE_RECIPE_ID,
    _nan_exact_sha256,
    build_release_bank,
    load_release_bank,
    save_release_bank,
    verify_parent_campaign_freeze,
)
from windfarm_moe.release_gate import (
    MIN_SAMPLES_LEAF,
    RELEASE_GATE_SCHEMA,
    actual_cell_loss,
    build_recipes,
    build_release_gate_recipes,
    coerce_recipe,
    fit_rule,
    load_release_gate_model,
    predict_rule,
    save_release_gate_model,
)
from windfarm_moe.residual_meta import META_ARMS
from windfarm_moe.stable_contrast_inference import (
    CSTAR,
    THRESHOLDS,
    infer_stable_campaign as infer_campaign,
)

POLICY_PREFIX = "GR"
PARENT_POLICY_PREFIX = "NR"

SNAPSHOTS: dict[str, tuple[int, int]] = {
    "A": (28519, 28526),
    "B": (28937, 28944),
    "C": (29376, 29384),
    "D": (30233, 30240),
}
SNAPSHOT_ORDER: tuple[str, ...] = ("A", "B", "C", "D")
VALIDATION_WINDOWS: dict[str, tuple[int, int]] = {
    "A": (28526, 28937),
    "B": (28944, 29376),
    "C": (29384, 30233),
}

STATIC_RECIPE_IDS: tuple[int, ...] = tuple(range(0, 7))
LEARNED_RECIPE_IDS: tuple[int, ...] = tuple(range(7, 24))
GLOBAL_FIT_RECIPE_ID: int = 7
GATE_RECIPE_IDS: tuple[int, ...] = tuple(range(8, 20))
CURRENT_GATE_RECIPE_IDS: tuple[int, ...] = tuple(range(8, 14))
FEEDBACK_GATE_RECIPE_IDS: tuple[int, ...] = tuple(range(14, 20))
CALIBRATION_RECIPE_IDS: tuple[int, ...] = tuple(range(20, 24))
PRIMARY_CAL_RECIPE_ID: int = 22

EXPECTED_HIST_STEPS: int = 2139
EXPECTED_INNER_STEPS: int = 850
EXPECTED_OUTER_STEPS: int = 1289
EXPECTED_EVAL_STEPS: int = 5033
EXPECTED_FULL_STEPS: int = 7172
EXPECTED_S0_PREFIX_ISSUES: int = 432
EXPECTED_S0_MIN_VALID_ROWS: int = MIN_SAMPLES_LEAF
EXPECTED_EVAL_VALID_CELLS: int = 672939
EXPECTED_EVAL_DAYS: int = 35
ENDPOINT_RAWSCORE_TOL: float = 1e-8

EXPECTED_PARENT_POLICIES: int = 1184
EXPECTED_PARENT_COMPARISONS: int = 5163
EXPECTED_PARENT_ALIASES: int = 142
EXPECTED_NEW_POLICIES: int = 72
EXPECTED_NEW_COMPARISONS: int = 534
EXPECTED_NEW_ALIASES: int = 6
EXPECTED_TOTAL_POLICIES: int = 1256
EXPECTED_TOTAL_COMPARISONS: int = 5697
EXPECTED_NOMINAL_COORDINATES: int = 70786


def s0_shard_assignment(shard: int) -> tuple[int, str]:
    s = _strict_int(shard, "shard")
    if not 0 <= s < 3:
        raise ValueError("S0 shard index must be an integer in 0..2 (seed 201 across arms C/P/Z)")
    return 201, META_ARMS[s]


def bank_relpath(kind: str, arm: str, seed: int) -> Path:
    return Path("banks") / kind / f"{arm}_seed{int(seed)}" / "release_bank.npz"


def bank_meta_relpath(kind: str, arm: str, seed: int) -> Path:
    return Path("banks") / kind / f"{arm}_seed{int(seed)}" / "release_bank_metadata.json"


def model_relpath(snapshot: str, arm: str, seed: int, recipe_id: int) -> Path:
    return Path("models") / str(snapshot) / f"{arm}_seed{int(seed)}" / f"{POLICY_PREFIX}{int(recipe_id):03d}.joblib"


def model_receipt_relpath(snapshot: str, arm: str, seed: int, recipe_id: int) -> Path:
    return Path("models") / str(snapshot) / f"{arm}_seed{int(seed)}" / f"{POLICY_PREFIX}{int(recipe_id):03d}_receipt.json"


def _append_jsonl(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        dict(record),
        sort_keys=True,
        allow_nan=False,
        default=lambda x: x.tolist() if isinstance(x, np.ndarray) else str(x),
    ) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())


def _env_meta() -> dict[str, Any]:
    return dict(
        time_utc=datetime.now(timezone.utc).isoformat(),
        hostname=platform.node(),
        platform=platform.platform(),
        python=sys.version.split()[0],
        numpy=np.__version__,
        scipy=scipy.__version__,
        sklearn=sklearn.__version__,
        joblib=joblib.__version__,
        pbs_jobid=os.environ.get("PBS_JOBID"),
        campaign_release=os.environ.get("CAMPAIGN_RELEASE"),
    )


def verify_source_hashes(cfg: Mapping[str, Any], root: Path = ROOT) -> dict[str, str]:
    expected = cfg.get("source_hashes") or {}
    if not isinstance(expected, Mapping) or not expected:
        raise ValueError("Protocol missing source_hashes")
    actual: dict[str, str] = {}
    for rel, exp_sha in expected.items():
        p = Path(rel)
        if not p.is_absolute():
            p = Path(root) / p
        if not p.exists():
            raise ValueError(f"Required source file missing: {p}")
        digest = sha(p)
        if digest != exp_sha:
            raise ValueError(f"Source hash mismatch for {rel}: {digest} != {exp_sha}")
        actual[str(rel)] = digest
    return actual


def verify_budget_and_recipes(cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    if _strict_int(cfg.get("max_candidates"), "max_candidates") != 24 or _strict_int(
        cfg.get("max_cpu_seconds"), "max_cpu_seconds"
    ) != 14400:
        raise ValueError("Authorized 24-candidate / 14400-CPU-second budget differs")

    s0_wall = _strict_int(cfg.get("s0_wall_seconds", 120), "s0_wall_seconds")
    hist_wall = _strict_int(cfg.get("history_wall_seconds", cfg.get("shard_wall_seconds", 600)), "history_wall_seconds")
    eval_wall = _strict_int(cfg.get("evaluation_wall_seconds", 120), "evaluation_wall_seconds")
    freeze_wall = _strict_int(cfg.get("freeze_wall_seconds", 60), "freeze_wall_seconds")
    agg_wall = _strict_int(cfg.get("aggregate_wall_seconds", 1200), "aggregate_wall_seconds")
    audit_wall = _strict_int(cfg.get("independent_audit_wall_seconds", 300), "independent_audit_wall_seconds")
    reserve_wall = _strict_int(cfg.get("local_retry_reserve_seconds", 1680), "local_retry_reserve_seconds")
    prior_cpu = _strict_int(cfg.get("prior_accounted_cpu_seconds", 0), "prior_accounted_cpu_seconds")
    max_jobs = _strict_int(cfg.get("maximum_science_parallel_jobs", 15), "maximum_science_parallel_jobs")
    per_job_ncpus = _strict_int(cfg.get("per_job_ncpus", 1), "per_job_ncpus")
    agg_mem = _strict_int(cfg.get("aggregate_mem_gb", 96), "aggregate_mem_gb")

    if s0_wall != 120 or hist_wall != 600 or eval_wall != 120 or freeze_wall != 60 or agg_wall != 1200 or audit_wall != 300:
        raise ValueError("Stage wall seconds must equal S0=120, history=600, evaluate=120, freeze=60, aggregate=1200, audit=300")
    if prior_cpu < 0 or reserve_wall < 0 or reserve_wall + prior_cpu != 1680:
        raise ValueError("local_retry_reserve_seconds + prior_accounted_cpu_seconds must equal 1680")
    if max_jobs != 15 or per_job_ncpus != 1 or agg_mem != 96:
        raise ValueError("Resource limits must equal maximum_science_parallel_jobs=15, per_job_ncpus=1, aggregate_mem_gb=96")

    total_cpu = 3 * s0_wall + 15 * hist_wall + 15 * eval_wall + freeze_wall + agg_wall + audit_wall + reserve_wall + prior_cpu
    if total_cpu != 14400:
        raise ValueError(f"Stage CPU budget sum {total_cpu} != 14400")

    if "budget_reservation" in cfg:
        br = cfg["budget_reservation"]
        if not isinstance(br, Mapping):
            raise ValueError("budget_reservation must be a mapping")
        new_cand = _strict_int(br.get("new_candidates"), "budget_reservation.new_candidates")
        cpu_sec = _strict_int(br.get("cpu_seconds"), "budget_reservation.cpu_seconds")
        tot_cand = _strict_int(br.get("total_reserved_candidates"), "budget_reservation.total_reserved_candidates")
        tot_cpu = _strict_int(
            br.get("total_accounted_plus_open_reservations_cpu"),
            "budget_reservation.total_accounted_plus_open_reservations_cpu",
        )
        glob_cpu = _strict_int(br.get("global_cpu_limit_unchanged", 86400), "budget_reservation.global_cpu_limit_unchanged")
        glob_cand = _strict_int(br.get("candidate_limit_unchanged", 2000), "budget_reservation.candidate_limit_unchanged")
        if (
            new_cand != 24
            or cpu_sec != 14400
            or tot_cand != 1574
            or tot_cpu != 71276
            or glob_cpu != 86400
            or glob_cand != 2000
            or not (tot_cand <= glob_cand and tot_cpu <= glob_cpu)
        ):
            raise ValueError("budget_reservation values differ from authorized 24/14400 and global 1574<=2000 / 71276<=86400")

    expected = build_release_gate_recipes()
    recipes = cfg.get("recipes")
    if not isinstance(recipes, list) or len(recipes) != 24:
        raise ValueError("Protocol must declare all 24 release gate recipes")
    canonical_list: list[dict[str, Any]] = []
    for idx, (rec, exp) in enumerate(zip(recipes, expected)):
        coerced = coerce_recipe(rec)
        if coerced != exp or int(coerced["id"]) != idx:
            raise ValueError(f"Protocol recipe {idx} differs from canonical release gate recipe: {rec!r} != {exp!r}")
        canonical_list.append(coerced)
    return canonical_list


def verify_direct_parent_provenance(
    cfg: Mapping[str, Any], *, require_ledger: bool = False
) -> tuple[Path, dict[str, Any], Path, dict[str, Any], Path, dict[str, Any]]:
    parent_dir, parent_freeze, _ = verify_parent_campaign_freeze(
        cfg["parent_results"],
        str(cfg["parent_freeze_sha256"]),
        input_protocol_path=cfg.get("parent_input_protocol"),
        label="Direct parent NR",
    )
    mc_dir, mc_freeze, _ = verify_parent_campaign_freeze(
        cfg["stream_parent_results"],
        str(cfg["stream_parent_freeze_sha256"]),
        input_protocol_path=cfg.get("stream_parent_input_protocol"),
        label="Stream parent MCV2",
    )
    safe_dir, safe_freeze, _ = verify_parent_campaign_freeze(
        cfg["safe_parent_results"],
        str(cfg["safe_parent_freeze_sha256"]),
        input_protocol_path=cfg.get("safe_parent_input_protocol"),
        label="Safe parent BR",
    )
    if require_ledger:
        ledger_path = parent_dir / "all_daily_ledger.npz"
        if not ledger_path.exists():
            raise ValueError(f"Direct parent all_daily_ledger.npz missing: {ledger_path}")
        if cfg.get("parent_ledger_sha256") and sha(ledger_path) != str(cfg["parent_ledger_sha256"]):
            raise ValueError("Direct parent all_daily_ledger.npz SHA-256 mismatch")
        span3_path = parent_dir / "inference_span3.json"
        if cfg.get("parent_span3_sha256"):
            if not span3_path.exists() or sha(span3_path) != str(cfg["parent_span3_sha256"]):
                raise ValueError("Direct parent inference_span3.json missing or SHA-256 mismatch")
    return parent_dir, parent_freeze, mc_dir, mc_freeze, safe_dir, safe_freeze


def _save_protocol_copies(cfg: Mapping[str, Any], out: Path, protocol_path: Path | None) -> str:
    out.mkdir(parents=True, exist_ok=True)
    orig_dst = out / "protocol_original.json"
    res_dst = out / "protocol.json"
    raw_bytes = Path(protocol_path).read_bytes() if protocol_path is not None else (json.dumps(dict(cfg),indent=2,allow_nan=False)+'\n').encode()
    resolved_bytes = (json.dumps(dict(cfg),indent=2,allow_nan=False)+'\n').encode()
    for target, payload in ((orig_dst, raw_bytes), (res_dst, resolved_bytes)):
        tmp = out / f'.{target.name}.{os.getpid()}.{time.time_ns()}.tmp'
        try:
            tmp.write_bytes(payload)
            try:
                os.link(tmp, target)
            except (FileExistsError, PermissionError):
                # Windows can report ERROR_ACCESS_DENIED instead of EEXIST
                # when another reader has the destination hard link open.
                # Accept only an already-published complete, identical file.
                if not target.exists():
                    raise
                for retry in range(20):
                    try:
                        existing = target.read_bytes()
                        break
                    except PermissionError:
                        if os.name != "nt" or retry == 19:
                            raise
                        time.sleep(.005)
                if existing != payload:
                    raise ValueError(f"Existing {target.name} differs from input --protocol bytes")
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except PermissionError:
                # Windows may hold another reader's shared hard-link handle.
                # The fully written temporary copy is harmless and retained.
                if os.name != "nt":
                    raise
    return sha(orig_dst)


def _verify_historical_bank_contract(
    bank: Mapping[str, Any],
    *,
    expected_inner_steps: int = EXPECTED_INNER_STEPS,
    expected_outer_steps: int = EXPECTED_OUTER_STEPS,
    expected_s0_prefix_issues: int = EXPECTED_S0_PREFIX_ISSUES,
    expected_s0_min_valid_rows: int = EXPECTED_S0_MIN_VALID_ROWS,
) -> dict[str, Any]:
    anchors = np.asarray(bank["anchors"], dtype=np.int64)
    mask = np.asarray(bank["mask"], dtype=bool)
    shortfall = np.asarray(bank["shortfall"], dtype=np.float64)
    meta = dict(bank.get("metadata") or {})
    if bool(meta.get("include_evaluation", False)) or bool(meta.get("evaluation_touched", False)):
        raise ValueError("Historical bank must not include or touch evaluation data")
    if list(meta.get("phases") or []) != ["inner", "outer"]:
        raise ValueError(f"Historical bank phases must be ['inner', 'outer'], got {meta.get('phases')}")

    inner_begin, inner_end, _ = PHASES["inner"]
    outer_begin, outer_end, _ = PHASES["outer"]
    in_sel = (anchors >= inner_begin) & (anchors < inner_end)
    out_sel = (anchors >= outer_begin) & (anchors < outer_end)
    n_in = int(np.count_nonzero(in_sel))
    n_out = int(np.count_nonzero(out_sel))
    n_tot = int(anchors.size)
    if n_in != int(expected_inner_steps) or n_out != int(expected_outer_steps) or n_tot != int(expected_inner_steps + expected_outer_steps):
        raise ValueError(
            f"Historical bank issue counts (inner={n_in}, outer={n_out}, total={n_tot}) != "
            f"({expected_inner_steps}, {expected_outer_steps}, {expected_inner_steps + expected_outer_steps})"
        )
    if not np.array_equal(np.flatnonzero(in_sel), np.arange(0, n_in)) or not np.array_equal(
        np.flatnonzero(out_sel), np.arange(n_in, n_tot)
    ):
        raise ValueError("Historical bank inner/outer slices must be contiguous partitions")
    gap = int(anchors[n_in]) - int(anchors[n_in - 1])
    if gap <= RELEASE_LAG_STEPS:
        raise ValueError(f"Inner-to-outer boundary gap {gap} must exceed {RELEASE_LAG_STEPS}")

    cut_a, start_a = SNAPSHOTS["A"]
    sel_a = anchors < cut_a
    n_issues_a = int(np.count_nonzero(sel_a))
    if n_issues_a != int(expected_s0_prefix_issues):
        raise ValueError(f"Snapshot A prefix issue count {n_issues_a} != {expected_s0_prefix_issues}")
    if int(anchors[sel_a][-1]) + RELEASE_LAG_STEPS >= start_a:
        raise ValueError("Snapshot A last anchor violates +7 < start_a")
    valid_rows_a = int(np.count_nonzero(mask[sel_a]))
    if valid_rows_a < int(expected_s0_min_valid_rows):
        raise ValueError(f"Snapshot A valid rows {valid_rows_a} < {expected_s0_min_valid_rows}")

    trace = np.asarray(meta.get("feedback_release_trace", []), dtype=np.int64)
    if trace.shape != anchors.shape or np.any(trace >= anchors):
        raise ValueError("Historical bank feedback_release_trace violated strict maturity < decision_anchor")

    return dict(
        n_steps=n_tot,
        n_inner_steps=n_in,
        n_outer_steps=n_out,
        inner_outer_gap=gap,
        s0_prefix_issues=n_issues_a,
        s0_prefix_valid_rows=valid_rows_a,
        total_valid_cells=int(mask.sum()),
        shortfall_raw_sha256=_nan_exact_sha256(shortfall),
    )


def _score_canonical_or_raw_phase(
    *,
    recipe_id: int,
    arm: str,
    seed: int,
    phase: str,
    actions: np.ndarray,
    shortfall: np.ndarray,
    mask: np.ndarray,
    anchors: np.ndarray,
    cfg: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, str, dict[str, Any]]:
    act_arr = np.ascontiguousarray(actions, dtype=np.float64)
    act_sha = prefix_sha256(act_arr)
    raw_daily, raw_counts, raw_days = score_actions(act_arr, shortfall, mask, anchors)

    if recipe_id not in (0, 1):
        return (
            raw_daily,
            raw_counts,
            raw_days,
            act_sha,
            dict(
                canonical_endpoint_ledger=False,
                rawscore_max_abs_error=0.0,
                canonical_source=None,
            ),
        )

    if recipe_id == 0:
        parent_root = Path(cfg["safe_parent_results"])
        inst_dir = parent_root / "instances" / phase / f"P_seed{int(seed)}"
        parent_rec_key = str(SAFE_RECIPE_ID)
        parent_slot_idx = int(SAFE_RECIPE_ID)
    else:
        parent_root = Path(cfg["stream_parent_results"])
        inst_dir = parent_root / "instances" / phase / f"{arm}_seed{int(seed)}"
        parent_rec_key = str(COST_RECIPE_ID)
        parent_slot_idx = int(COST_RECIPE_ID)

    rcpt_path = inst_dir / "receipt.json"
    daily_path = inst_dir / "daily.npz"
    if not rcpt_path.exists() or not daily_path.exists():
        raise ValueError(f"Canonical parent endpoint receipt or daily.npz missing: {inst_dir}")
    rcpt = json.loads(rcpt_path.read_text(encoding="utf-8"))
    exp_act_sha = (rcpt.get("action_sha256") or {}).get(parent_rec_key)
    if rcpt.get("status", {}).get(parent_rec_key) != "COMPLETED" or exp_act_sha != act_sha:
        raise ValueError(
            f"Canonical endpoint {recipe_id} ({arm}_seed{seed} {phase}) action SHA mismatch: {act_sha} != {exp_act_sha}"
        )

    with np.load(daily_path) as d_npz:
        p_daily_all = np.asarray(d_npz["ledger"], dtype=np.float64)
        p_counts = np.asarray(d_npz["counts"], dtype=np.int64)
        p_days = np.asarray(d_npz["days"], dtype=np.int64)

    if p_daily_all.ndim != 3 or not (0 <= parent_slot_idx < p_daily_all.shape[0]):
        raise ValueError(f"Invalid canonical parent daily.npz shape {p_daily_all.shape} at {daily_path}")
    can_daily = np.ascontiguousarray(p_daily_all[parent_slot_idx], dtype=np.float64)

    if can_daily.shape != raw_daily.shape:
        raise ValueError(f"Canonical daily shape {can_daily.shape} != raw daily shape {raw_daily.shape}")
    if not np.array_equal(p_counts, np.asarray(raw_counts, dtype=np.int64)):
        raise ValueError("Canonical endpoint daily counts do not match raw score_actions counts")
    if not np.array_equal(p_days, np.asarray(raw_days, dtype=np.int64)):
        raise ValueError("Canonical endpoint daily day indices do not match raw score_actions days")
    if not np.array_equal(can_daily[:, 3], raw_daily[:, 3]):
        raise ValueError("Canonical endpoint daily strict event count V differs from raw score_actions")

    max_err = float(np.max(np.abs(can_daily - raw_daily))) if can_daily.size > 0 else 0.0
    if not np.isfinite(max_err) or max_err > ENDPOINT_RAWSCORE_TOL:
        raise ValueError(
            f"Canonical endpoint {recipe_id} rawscore guard exceeded {ENDPOINT_RAWSCORE_TOL}: max_abs_error={max_err}"
        )

    return (
        can_daily,
        p_counts,
        p_days,
        act_sha,
        dict(
            canonical_endpoint_ledger=True,
            rawscore_max_abs_error=max_err,
            canonical_source=str(daily_path),
            parent_receipt_path=str(rcpt_path),
            parent_recipe_id=int(parent_slot_idx),
            action_sha256_verified=act_sha,
        ),
    )


def _mean_metrics_from_daily(daily: np.ndarray, counts: np.ndarray) -> list[float]:
    tot_n = float(np.sum(counts))
    if tot_n <= 0.0:
        raise ValueError("Zero total valid cells in daily metrics")
    sums = np.sum(np.asarray(daily, dtype=np.float64), axis=0)
    return [float(sums[i] / tot_n) for i in range(4)]


def _window_cell_metrics(
    actions: np.ndarray, shortfall: np.ndarray, mask: np.ndarray
) -> dict[str, float]:
    valid = np.asarray(mask, dtype=bool)
    n_val = int(np.count_nonzero(valid))
    if n_val <= 0:
        raise ValueError("Empty valid cells in validation window")
    r = np.asarray(actions, dtype=np.float64)[valid]
    s = np.asarray(shortfall, dtype=np.float64)[valid]
    c, u, v = actual_cell_loss(r, s)
    return dict(
        C=float(np.mean(c)),
        R=float(np.mean(r / 6.0)),
        U=float(np.mean(u)),
        V=float(np.mean(v)),
        valid_cells=n_val,
    )


def _summarize_prediction_diagnostics(
    model: Mapping[str, Any],
    pred_meta: Mapping[str, Any],
    safe_slice: np.ndarray,
    cost_slice: np.ndarray,
) -> dict[str, Any]:
    kind = str(model.get("kind", "SAFE"))
    alpha_grid = pred_meta.get("alpha_grid")
    if alpha_grid is not None:
        ag = np.asarray(alpha_grid, dtype=np.float64)
        mean_a = float(np.mean(ag))
        min_a = float(np.min(ag))
        max_a = float(np.max(ag))
        g_enabled_frac = float(np.mean(ag > 0.0))
    else:
        mean_a = pred_meta.get("mean_alpha")
        min_a = pred_meta.get("min_alpha")
        max_a = pred_meta.get("max_alpha")
        g_enabled_frac = 1.0 if kind == "CONDITIONAL_CALIBRATION" and not pred_meta.get("fallback_to_safe") else 0.0

    leaf_stats = model.get("leaf_stats") or {}
    leaf_cf_summary: dict[str, Any] = {}
    for lk, lv in leaf_stats.items():
        if isinstance(lv, Mapping) and "safe_C_kwh" in lv and "actual_C_kwh" in lv:
            dc = float(lv["actual_C_kwh"]) - float(lv["safe_C_kwh"])
            d10u = 10.0 * (float(lv["actual_U_kwh"]) - float(lv["safe_U_kwh"]))
            leaf_cf_summary[str(lk)] = dict(
                alpha=float(lv.get("alpha", 0.0)),
                mean_counterfactual_delta_C_kwh=dc,
                mean_counterfactual_delta_10U_kwh=d10u,
                n_cells=int(lv.get("n_cells", 0)),
            )
        elif isinstance(lv, Mapping):
            leaf_cf_summary[str(lk)] = dict(lv)

    return dict(
        kind=kind,
        status=str(model.get("status", "UNKNOWN")),
        fallback_to_safe=bool(pred_meta.get("fallback_to_safe", False)),
        mean_alpha=mean_a,
        min_alpha=min_a,
        max_alpha=max_a,
        g_enabled_fraction=g_enabled_frac,
        mean_shift_kw=pred_meta.get("mean_shift_kw"),
        leaf_support={str(k): int(v) for k, v in (pred_meta.get("leaf_support") or {}).items()},
        leaf_counterfactual_stats=leaf_cf_summary,
        zero_clamp_count=int(pred_meta.get("zero_clamp_count", 0)),
        mean_cost_minus_safe_kw=float(np.mean(np.asarray(cost_slice, dtype=np.float64) - np.asarray(safe_slice, dtype=np.float64))),
    )


def run_s0_shard(
    cfg: Mapping[str, Any],
    out: Path | str,
    shard: int,
    *,
    protocol_path: Path | None = None,
    deadline: float | None = None,
    root: Path = ROOT,
    expected_inner_steps: int = EXPECTED_INNER_STEPS,
    expected_outer_steps: int = EXPECTED_OUTER_STEPS,
    expected_s0_prefix_issues: int = EXPECTED_S0_PREFIX_ISSUES,
    expected_s0_min_valid_rows: int = EXPECTED_S0_MIN_VALID_ROWS,
) -> dict[str, Any]:
    out_dir = Path(out)
    start = time.time()
    wall = float(_strict_int(cfg.get("s0_wall_seconds", 120), "s0_wall_seconds"))
    if deadline is None:
        deadline = start + wall
    seed, arm = s0_shard_assignment(shard)
    stage_dir = out_dir / "shards" / "s0" / f"shard_{int(shard):02d}_{arm}_seed{seed}"
    state = dict(
        stage="s0",
        shard=int(shard),
        seed=seed,
        arm=arm,
        status="RUNNING",
        env=_env_meta(),
    )
    save(stage_dir / "state.json", state)

    try:
        deadline_check(deadline)
        source_shas = verify_source_hashes(cfg, root=root)
        verify_budget_and_recipes(cfg)
        verify_direct_parent_provenance(cfg, require_ledger=False)
        proto_sha = _save_protocol_copies(cfg, out_dir, protocol_path)

        bank_npz = out_dir / bank_relpath("history", arm, seed)
        bank_meta = out_dir / bank_meta_relpath("history", arm, seed)
        if bank_npz.exists() or bank_meta.exists():
            bank = load_release_bank(bank_npz)
            manifest = dict(
                npz_path=str(bank_npz),
                metadata_path=str(bank_meta),
                npz_sha256=sha(bank_npz),
                metadata_sha256=sha(bank_meta),
                reused_existing=True,
            )
        else:
            bank = build_release_bank(dict(cfg), seed=seed, arm=arm, include_evaluation=False, root=root)
            manifest = save_release_bank(bank_npz, bank)
            manifest["reused_existing"] = False

        checks = _verify_historical_bank_contract(
            bank,
            expected_inner_steps=expected_inner_steps,
            expected_outer_steps=expected_outer_steps,
            expected_s0_prefix_issues=expected_s0_prefix_issues,
            expected_s0_min_valid_rows=expected_s0_min_valid_rows,
        )
        deadline_check(deadline)

        receipt = dict(
            schema="prospective-release-s0-v1",
            status="COMPLETED",
            shard=int(shard),
            seed=seed,
            arm=arm,
            protocol_sha256=proto_sha,
            source_hashes=source_shas,
            bank_manifest=manifest,
            bank_checks=checks,
            learner_fits_executed=0,
            evaluation_touched=False,
            elapsed_seconds=time.time() - start,
        )
        rcpt_path = out_dir / "s0" / f"{arm}_seed{seed}_receipt.json"
        save(rcpt_path, receipt)
        state.update(status="COMPLETED", receipt_path=str(rcpt_path), elapsed_seconds=time.time() - start)
        save(stage_dir / "state.json", state)
        return receipt
    except BaseException as exc:
        err = dict(stage="s0", shard=int(shard), seed=seed, arm=arm, error=repr(exc), traceback=traceback.format_exc())
        save(stage_dir / "failure.json", err)
        save(out_dir / "s0" / f"{arm}_seed{seed}_failure.json", err)
        state.update(status="FAILED_PRESERVED", error=repr(exc), elapsed_seconds=time.time() - start)
        save(stage_dir / "state.json", state)
        raise


def prediction_view(bank):
    """Expose only arrived covariates to the action function."""
    return {k: bank[k] for k in ("safe", "cost", "current_features", "feedback_features")}


def scheduled_actions(bank, models, recipe_id):
    """Four fixed causal snapshots; learned rules use SAFE before snapshot A."""
    a = bank["anchors"]
    actions = bank["safe"].copy()
    diagnostics = {}
    for j, key in enumerate(SNAPSHOT_ORDER):
        start = SNAPSHOTS[key][1]
        stop = SNAPSHOTS[SNAPSHOT_ORDER[j + 1]][1] if j < 3 else np.iinfo(np.int64).max
        sel = (a >= start) & (a < stop)
        if recipe_id in STATIC_RECIPE_IDS and j == 0:
            sel = a < stop
        if not np.any(sel):
            continue
        pred, meta = predict_rule(models[key, recipe_id], prediction_view(bank), sel)
        actions[sel] = pred
        diagnostics[key] = _summarize_prediction_diagnostics(
            models[key, recipe_id], meta, bank["safe"][sel], bank["cost"][sel])
    return actions, diagnostics


def verify_prefix(history, full):
    n = len(history["anchors"])
    for k in ("anchors", "shortfall", "mask", "reference", "safe", "cost",
              "current_features", "feedback_features"):
        left, right = np.ascontiguousarray(history[k]), np.ascontiguousarray(full[k][:n])
        if left.dtype != right.dtype or left.shape != right.shape or left.tobytes() != right.tobytes():
            raise ValueError(f"History/full bank prefix mismatch: {k}")
    return n


def _history_receipt_path(out, shard):
    seed, arm = shard_assignment(shard)
    return Path(out) / "shards" / "history" / f"shard_{shard:02d}_{arm}_seed{seed}" / "receipt.json"


def _record_phase(cfg, out, bank, models, phase, seed, arm, deadline):
    begin, end, _ = PHASES[phase]
    sel = (bank["anchors"] >= begin) & (bank["anchors"] < end)
    if not sel.any():
        raise ValueError(f"Empty phase {phase}")
    y, mask, anchors = bank["shortfall"][sel], bank["mask"][sel], bank["anchors"][sel]
    ledgers, receipts, point = [], {}, []
    for rid in range(24):
        deadline_check(deadline)
        act, diag = scheduled_actions(bank, models, rid)
        daily, counts, days, act_sha, canonical = _score_canonical_or_raw_phase(
            recipe_id=rid, arm=arm, seed=seed, phase=phase, actions=act[sel],
            shortfall=y, mask=mask, anchors=anchors, cfg=cfg)
        ledgers.append(daily)
        point.append(_mean_metrics_from_daily(daily, counts))
        windows = {}
        if phase != "evaluate":
            for key, (lo, hi) in VALIDATION_WINDOWS.items():
                win = (bank["anchors"] >= lo) & (bank["anchors"] < hi) & sel
                if win.any():
                    windows[key] = _window_cell_metrics(act[win], bank["shortfall"][win], bank["mask"][win])
        receipts[str(rid)] = dict(status="COMPLETED", action_sha256=act_sha,
                                  canonical=canonical, diagnostics=diag, validation_windows=windows)
    ref, ref_n, ref_days = score_actions(bank["reference"][sel], y, mask, anchors)
    if not np.array_equal(counts, ref_n) or not np.array_equal(days, ref_days):
        raise ValueError("Phase population differs between common reference and policies")
    folder = Path(out) / "instances" / phase / f"{arm}_seed{seed}"
    folder.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(folder / "daily.npz", ledger=np.stack(ledgers), counts=counts, days=days, reference=ref)
    receipt = dict(phase=phase, seed=seed, arm=arm, policies=receipts,
                   points=point, daily_sha256=sha(folder / "daily.npz"), valid_cells=int(mask.sum()),
                   target_sha256=_nan_exact_sha256(y), mask_sha256=hashlib.sha256(mask.tobytes()).hexdigest())
    save(folder / "receipt.json", receipt)
    return dict(path=str((folder / "receipt.json").relative_to(out)).replace("\\", "/"),
                sha256=sha(folder / "receipt.json"), daily_sha256=receipt["daily_sha256"])


def _load_models(out, records):
    models = {}
    for item in records:
        p = Path(out) / item["path"]
        r = Path(out) / item["receipt_path"]
        if sha(p) != item["sha256"] or sha(r) != item["receipt_sha256"]:
            raise ValueError("Frozen model or model receipt hash mismatch")
        models[item["snapshot"], item["recipe_id"]] = load_release_gate_model(p)
    if len(models) != 96:
        raise ValueError("All 24 models at all four snapshots are mandatory")
    return models


def run_history_shard(cfg, out, shard, *, protocol_path=None, deadline=None, root=ROOT):
    start = time.time()
    deadline = deadline or start + cfg["history_wall_seconds"]
    out = Path(out)
    seed, arm = shard_assignment(shard)
    recpath = _history_receipt_path(out, shard)
    if recpath.exists():
        raise FileExistsError("Refusing to replace completed historical shard")
    stage = recpath.parent
    save(stage / "state.json", dict(status="RUNNING", env=_env_meta(), shard=shard, seed=seed, arm=arm))
    try:
        source_shas = verify_source_hashes(cfg, root)
        recipes = verify_budget_and_recipes(cfg)
        verify_direct_parent_provenance(cfg)
        proto_sha = _save_protocol_copies(cfg, out, protocol_path)
        for a in META_ARMS:
            s0 = json.loads((out / "s0" / f"{a}_seed201_receipt.json").read_text())
            if s0["status"] != "COMPLETED" or s0["protocol_sha256"] != proto_sha:
                raise ValueError("S0 barrier not satisfied")
        bankpath = out / bank_relpath("history", arm, seed)
        if bankpath.exists():
            bank = load_release_bank(bankpath)
            manifest = dict(npz_sha256=sha(bankpath), metadata_sha256=sha(out / bank_meta_relpath("history", arm, seed)))
        else:
            bank = build_release_bank(cfg, seed, arm, include_evaluation=False, root=root)
            manifest = save_release_bank(bankpath, bank)
        checks = _verify_historical_bank_contract(bank)
        models, records = {}, []
        for key in SNAPSHOT_ORDER:
            cut, enabled = SNAPSHOTS[key]
            sel = bank["anchors"] < cut
            for recipe in recipes:
                deadline_check(deadline)
                rid = recipe["id"]
                model, receipt = fit_rule(bank, recipe, seed=seed, fit_selector=sel, episode_start=enabled)
                p, rp = out / model_relpath(key, arm, seed, rid), out / model_receipt_relpath(key, arm, seed, rid)
                if p.exists() or rp.exists():
                    raise FileExistsError("Refusing to overwrite partial model; inspect before retry")
                save_release_gate_model(p, model)
                save(rp, receipt)
                records.append(dict(snapshot=key, recipe_id=rid, path=str(p.relative_to(out)).replace("\\", "/"),
                    sha256=sha(p), receipt_path=str(rp.relative_to(out)).replace("\\", "/"), receipt_sha256=sha(rp),
                    status=model["status"], fallback=bool(model.get("fallback_to_safe")),
                    tree_fit=model.get("tree") is not None, global_alpha_fit=model["kind"] == "GLOBAL_FIT" and model["status"] == "FITTED_OK"))
                models[key, rid] = model
                _append_jsonl(stage / "progress.jsonl", records[-1])
        phases = {p: _record_phase(cfg, out, bank, models, p, seed, arm, deadline) for p in ("inner", "outer")}
        receipt = dict(status="COMPLETED", shard=shard, seed=seed, arm=arm, protocol_sha256=proto_sha,
            source_hashes=source_shas, bank_manifest=manifest, bank_checks=checks, models=records, phases=phases,
            evaluation_touched=False, selection_filters_evaluation=False, elapsed_seconds=time.time()-start,
            actual_tree_fits=sum(x["tree_fit"] for x in records),
            actual_global_alpha_fits=sum(x["global_alpha_fit"] for x in records))
        save(recpath, receipt)
        save(stage / "state.json", dict(status="COMPLETED", elapsed_seconds=time.time()-start))
        return receipt
    except BaseException as exc:
        save(stage / "failure.json", dict(error=repr(exc), traceback=traceback.format_exc(), elapsed_seconds=time.time()-start))
        raise


def _read_bound_phase(out, phase, seed, arm, expected=None):
    folder = Path(out) / "instances" / phase / f"{arm}_seed{seed}"
    rp = folder / "receipt.json"
    if expected is not None and sha(rp) != expected["sha256"]:
        raise ValueError("Phase receipt hash mismatch")
    r = json.loads(rp.read_text())
    if r["phase"] != phase or r["seed"] != seed or r["arm"] != arm or len(r["policies"]) != 24:
        raise ValueError("Phase identity or policy count mismatch")
    if sha(folder / "daily.npz") != r["daily_sha256"]:
        raise ValueError("Daily ledger hash mismatch")
    with np.load(folder / "daily.npz") as z:
        arrays = {k: z[k].copy() for k in z.files}
    return r, arrays


def historical_summary(out):
    summary, point = {}, np.zeros((5, 3, 24, 4))
    for si, seed in enumerate(SEEDS):
        for ai, arm in enumerate(META_ARMS):
            r, _ = _read_bound_phase(out, "outer", seed, arm)
            point[si, ai] = r["points"]
    for ai, arm in enumerate(META_ARMS):
        mean = point[:, ai].mean(axis=0)
        summary[arm] = dict(minimum_C_id=int(np.argmin(mean[:, 0])),
            minimum_maxV_id=int(np.argmin(point[:, ai, :, 3].max(axis=0))), outer_mean_points=mean.tolist())
    return dict(arms=summary, scope="Historical outer roles only; no qualification filtering or independent confirmation")


def run_freeze_stage(cfg, out, *, protocol_path=None, deadline=None, root=ROOT):
    out = Path(out)
    deadline = deadline or time.time() + cfg["freeze_wall_seconds"]
    freeze_path = out / "FINAL_FREEZE.json"
    if freeze_path.exists() or (out / "EVALUATION_OPEN.json").exists():
        raise FileExistsError("Exclusive freeze already exists")
    sources = verify_source_hashes(cfg, root)
    verify_budget_and_recipes(cfg)
    proto_sha = _save_protocol_copies(cfg, out, protocol_path)
    histories = []
    for shard in range(15):
        deadline_check(deadline)
        seed, arm = shard_assignment(shard)
        p = _history_receipt_path(out, shard)
        r = json.loads(p.read_text())
        if r["status"] != "COMPLETED" or r["protocol_sha256"] != proto_sha or r["source_hashes"] != sources:
            raise ValueError("History not complete or source/protocol changed")
        if (r["seed"], r["arm"], r["shard"]) != (seed, arm, shard) or r["evaluation_touched"]:
            raise ValueError("History identity or evaluation exclusion violated")
        # Verify bytes without deserializing models during the short freeze job.
        if len(r["models"]) != 96 or {(x["snapshot"], x["recipe_id"]) for x in r["models"]} != {(s, j) for s in SNAPSHOT_ORDER for j in range(24)}:
            raise ValueError("Incomplete model family")
        for item in r["models"]:
            if sha(out / item["path"]) != item["sha256"] or sha(out / item["receipt_path"]) != item["receipt_sha256"]:
                raise ValueError("Model hash changed before freeze")
        manifest = r["bank_manifest"]
        if sha(out / bank_relpath("history", arm, seed)) != manifest["npz_sha256"] or sha(out / bank_meta_relpath("history", arm, seed)) != manifest["metadata_sha256"]:
            raise ValueError("History bank changed before freeze")
        for phase in ("inner", "outer"):
            _read_bound_phase(out, phase, seed, arm, r["phases"][phase])
        histories.append(dict(path=str(p.relative_to(out)).replace("\\", "/"), sha256=sha(p), models=r["models"], bank_manifest=manifest))
    selection = historical_summary(out)
    save(out / "HISTORY_SELECTION.json", selection)
    freeze = dict(schema="prospective-release-freeze-v1", status="FROZEN", protocol_sha256=proto_sha,
        source_hashes=sources, histories=histories, recipes=cfg["recipes"], snapshots=SNAPSHOTS,
        selection_sha256=sha(out / "HISTORY_SELECTION.json"), environment=_env_meta(),
        evaluation_touched=False, independent_confirmation=False,
        model_records=1440, actual_tree_fits=sum(json.loads((out / h["path"]).read_text())["actual_tree_fits"] for h in histories),
        actual_global_alpha_fits=sum(json.loads((out / h["path"]).read_text())["actual_global_alpha_fits"] for h in histories))
    with freeze_path.open("x", encoding="utf-8") as f:
        json.dump(freeze, f, indent=2, allow_nan=False)
    save(out / "EVALUATION_OPEN.json", dict(freeze_sha256=sha(freeze_path), protocol_sha256=proto_sha))
    return freeze


def verified_freeze(cfg, out, protocol_path, root):
    freeze = json.loads((out / "FINAL_FREEZE.json").read_text())
    opened = json.loads((out / "EVALUATION_OPEN.json").read_text())
    if sha(out / "FINAL_FREEZE.json") != opened["freeze_sha256"] or _save_protocol_copies(cfg, out, protocol_path) != freeze["protocol_sha256"]:
        raise ValueError("Evaluation barrier hash mismatch")
    if verify_source_hashes(cfg, root) != freeze["source_hashes"] or sha(out / "HISTORY_SELECTION.json") != freeze["selection_sha256"]:
        raise ValueError("Source/selection changed after freeze")
    return freeze, opened["freeze_sha256"]


def run_evaluate_shard(cfg, out, shard, *, protocol_path=None, deadline=None, root=ROOT):
    out = Path(out)
    start = time.time()
    deadline = deadline or start + cfg["evaluation_wall_seconds"]
    seed, arm = shard_assignment(shard)
    stage = out / "shards" / "evaluate" / f"shard_{shard:02d}_{arm}_seed{seed}"
    if (stage / "receipt.json").exists():
        raise FileExistsError("Evaluation already completed")
    save(stage / "state.json", dict(status="RUNNING", env=_env_meta(), seed=seed, arm=arm))
    try:
        freeze, freeze_sha = verified_freeze(cfg, out, protocol_path, root)
        h = freeze["histories"][shard]
        if sha(out / h["path"]) != h["sha256"]:
            raise ValueError("Historical receipt changed after freeze")
        history = load_release_bank(out / bank_relpath("history", arm, seed),
            h["bank_manifest"]["npz_sha256"], h["bank_manifest"]["metadata_sha256"])
        models = _load_models(out, h["models"])
        full = build_release_bank(cfg, seed, arm, include_evaluation=True, root=root)
        verify_prefix(history, full)
        if len(full["anchors"]) != EXPECTED_FULL_STEPS:
            raise ValueError("Full issue count differs")
        ev = full["anchors"] >= PHASES["evaluate"][0]
        if int(full["mask"][ev].sum()) != EXPECTED_EVAL_VALID_CELLS:
            raise ValueError("Evaluation population differs")
        # Save only the manifest identity of the large reconstructed bank.
        save(stage / "full_bank_metadata.json", full["metadata"])
        phase = _record_phase(cfg, out, full, models, "evaluate", seed, arm, deadline)
        receipt = dict(status="COMPLETED", shard=shard, seed=seed, arm=arm, freeze_sha256=freeze_sha,
            phase=phase, full_bank_metadata_sha256=sha(stage / "full_bank_metadata.json"),
            evaluated_recipe_ids=list(range(24)), selection_did_not_filter=True, elapsed_seconds=time.time()-start)
        save(stage / "receipt.json", receipt)
        save(stage / "state.json", dict(status="COMPLETED", elapsed_seconds=time.time()-start))
        return receipt
    except BaseException as exc:
        save(stage / "failure.json", dict(error=repr(exc), traceback=traceback.format_exc(), elapsed_seconds=time.time()-start))
        raise


def build_extended_family(parent):
    fd = parent["family_definition"]
    old = parent["policy_names"]
    if len(old) != EXPECTED_PARENT_POLICIES or len(fd["comparisons"]) != EXPECTED_PARENT_COMPARISONS:
        raise ValueError("Parent family dimensions differ")
    def names_pair(pair):
        return tuple(old[int(x)] if isinstance(x, int) else str(x) for x in pair)
    comparisons = [names_pair(p) for p in fd["comparisons"]]
    aliases = [names_pair(p) for p in fd["frozen_aliases"]]
    if len(aliases) != EXPECTED_PARENT_ALIASES:
        raise ValueError("Parent alias count differs")
    names = old + [f"GR{rid:03d}_{arm}" for rid in range(24) for arm in META_ARMS]
    for rid in range(24):
        for arm in META_ARMS:
            l = f"GR{rid:03d}_{arm}"
            comparisons.extend((l, r) for r in ("REF", "R0182_P", "BR009_P", "BR009_Z", f"MC049_{arm}"))
        comparisons.extend([(f"GR{rid:03d}_P", f"GR{rid:03d}_C"), (f"GR{rid:03d}_Z", f"GR{rid:03d}_C"), (f"GR{rid:03d}_Z", f"GR{rid:03d}_P")])
    for rid in (*GATE_RECIPE_IDS, *CALIBRATION_RECIPE_IDS):
        comparisons.extend((f"GR{rid:03d}_{arm}", f"GR007_{arm}") for arm in META_ARMS)
    for rid in FEEDBACK_GATE_RECIPE_IDS:
        comparisons.extend((f"GR{rid:03d}_{arm}", f"GR{rid-6:03d}_{arm}") for arm in META_ARMS)
    for rid in GATE_RECIPE_IDS:
        comparisons.extend((f"GR{rid:03d}_{arm}", f"GR022_{arm}") for arm in META_ARMS)
    for arm in META_ARMS:
        aliases.extend([(f"GR000_{arm}", "BR009_P"), (f"GR001_{arm}", f"MC049_{arm}")])
    if len(comparisons) != EXPECTED_TOTAL_COMPARISONS or len(set(comparisons)) != len(comparisons) or len(names) != EXPECTED_TOTAL_POLICIES:
        raise ValueError("New family incomplete or duplicate comparisons")
    if 11 * len(names) + 10 * len(comparisons) != EXPECTED_NOMINAL_COORDINATES:
        raise ValueError("Nominal family size differs")
    return names, list(parent["available"]), comparisons, aliases


def run_aggregate_stage(cfg, out, *, protocol_path=None, deadline=None, root=ROOT, n_boot_override=None):
    out = Path(out)
    deadline = deadline or time.time() + cfg["aggregate_wall_seconds"]
    if (out / "completion.json").exists():
        raise FileExistsError("Aggregate already completed")
    freeze, freeze_sha = verified_freeze(cfg, out, protocol_path, root)
    parent_dir, *_ = verify_direct_parent_provenance(cfg, require_ledger=True)
    parent = json.loads((parent_dir / "inference_span3.json").read_text())
    names, avail, pairs, aliases = build_extended_family(parent)
    with np.load(parent_dir / "all_daily_ledger.npz") as z:
        old, counts, days = z["ledger"].copy(), z["counts"].copy(), z["day_ids"].copy()
    if old.shape != (5, EXPECTED_PARENT_POLICIES, 35, 4):
        raise ValueError("Parent ledger shape differs")
    ledger = np.empty((5, EXPECTED_TOTAL_POLICIES, 35, 4))
    ledger[:, :len(avail)] = old
    shard_bindings = []
    for shard in range(15):
        deadline_check(deadline)
        seed, arm = shard_assignment(shard)
        path = out / "shards" / "evaluate" / f"shard_{shard:02d}_{arm}_seed{seed}" / "receipt.json"
        er = json.loads(path.read_text())
        if er["status"] != "COMPLETED" or er["freeze_sha256"] != freeze_sha or er["evaluated_recipe_ids"] != list(range(24)) or (er["seed"], er["arm"]) != (seed, arm):
            raise ValueError("Incomplete or unbound evaluation")
        r, z = _read_bound_phase(out, "evaluate", seed, arm, er["phase"])
        si = SEEDS.index(seed)
        if not np.array_equal(z["counts"], counts) or not np.array_equal(z["days"], days) or not np.allclose(z["reference"], old[si, 0], rtol=0, atol=1e-8):
            raise ValueError("Reference/target population bridge changed")
        if z["ledger"].shape != (24, 35, 4) or not np.isfinite(z["ledger"]).all():
            raise ValueError("Nonfinite/missing mandatory policy evaluation")
        for rid in range(24):
            ledger[si, names.index(f"GR{rid:03d}_{arm}")] = z["ledger"][rid]
        shard_bindings.append(dict(path=str(path.relative_to(out)), sha256=sha(path)))
    avail.extend([True] * 72)
    for l, r in aliases:
        if not np.array_equal(ledger[:, names.index(l)], ledger[:, names.index(r)], equal_nan=True):
            raise ValueError(f"Alias ledger mismatch: {l}/{r}")
    np.savez_compressed(out / "all_daily_ledger.npz", ledger=ledger, counts=counts, day_ids=days)
    save(out / "all_policy_names.json", dict(names=names, available=avail, comparisons=pairs, aliases=aliases,
        new_policy_count=72, new_comparison_count=534, nominal_family_size=EXPECTED_NOMINAL_COORDINATES))
    save(out / "HISTORY_VALIDATION.json", {
        f"{arm}_seed{seed}": {phase: _read_bound_phase(out, phase, seed, arm)[0] for phase in ("inner", "outer")}
        for seed in SEEDS for arm in META_ARMS})
    for span in (1, 3, 7):
        deadline_check(deadline)
        result = infer_campaign(ledger, counts, names, pairs, span=span, seed=20261022,
            n_boot=20000 if n_boot_override is None else n_boot_override, available=avail, aliases=aliases)
        save(out / f"inference_span{span}.json", result)
    result = dict(status="COMPLETED", freeze_sha256=freeze_sha, environment=_env_meta(),
        model_records=freeze["model_records"], actual_tree_fits=freeze["actual_tree_fits"],
        actual_global_alpha_fits=freeze["actual_global_alpha_fits"],
        scored_instances=1080, all_recipe_ids_evaluated=True, qualification_used_to_filter=False,
        independent_confirmation=False, parent_prefix_exact=np.array_equal(ledger[:, :old.shape[1]], old, equal_nan=True),
        ledger_sha256=sha(out / "all_daily_ledger.npz"), evaluation_bindings=shard_bindings,
        inference_sha256={str(s): sha(out / f"inference_span{s}.json") for s in (1,3,7)})
    save(out / "completion.json", result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--protocol", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--stage", choices=("s0", "history", "freeze", "evaluate", "aggregate"), required=True)
    p.add_argument("--shard", type=int, default=0)
    a = p.parse_args()
    if not os.environ.get("PBS_JOBID") or not os.environ.get("CAMPAIGN_RELEASE"):
        raise RuntimeError("Metis PBS allocation and exact source release required")
    cfg = json.loads(a.protocol.read_text(encoding="utf-8"))
    with threadpool_limits(limits=1):
        func = globals()[f"run_{a.stage}_shard" if a.stage in ("s0", "history", "evaluate") else f"run_{a.stage}_stage"]
        kwargs = dict(protocol_path=a.protocol)
        if a.stage in ("s0", "history", "evaluate"):
            kwargs["shard"] = a.shard
        func(cfg, a.output, **kwargs)


if __name__ == "__main__":
    main()


