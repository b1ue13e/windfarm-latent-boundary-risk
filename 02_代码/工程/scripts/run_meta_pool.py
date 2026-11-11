"""Distributed multi-stage runner for the 24-recipe OOF constrained Meta-head pool campaign."""
from __future__ import annotations

import argparse
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
    verify_cache,
)
from scripts.run_residual_meta import (
    _strict_int,
    collect,
    shard_assignment,
    verify_protocol_cfg,
    verify_source_hashes,
)
from windfarm_moe.actual_mixture_update import MixtureConfig
from windfarm_moe.autonomous_campaign_inference import CSTAR, THRESHOLDS, infer_campaign
from windfarm_moe.bounded_relief import (
    fit_signed,
    run_signed,
    signed_action,
    signed_experts,
)
from windfarm_moe.meta_action_stream import (
    join_banks,
    load_bank,
    prefix_sha256,
)
from windfarm_moe.residual_meta import META_ARMS

POLICY_PREFIX = "MP"
PARENT_POLICY_PREFIX = "MC"

RELIEF_GRID: tuple[float, ...] = (0.0, 0.01, 0.03, 0.1, 0.3, 1.0)
GOALS: tuple[str, ...] = ("COST", "CAP")
POOL_MODES: tuple[tuple[int, str, dict[str, float]], ...] = (
    (
        0,
        "FIXED",
        dict(
            eta=0.0,
            schedule_power=0.5,
            severity_step=0.0,
            cost_scale=100.0,
            proximity_strength=0.0,
        ),
    ),
    (
        1,
        "ONLINE",
        dict(
            eta=0.3,
            schedule_power=0.5,
            severity_step=10.0,
            cost_scale=100.0,
            proximity_strength=0.0,
        ),
    ),
)

CHECKPOINT_FILENAME = "recipe_checkpoints.jsonl"
INITIALIZER_CHECKPOINT_FILENAME = "initializer_checkpoints.jsonl"


def build_pool_recipes() -> list[dict[str, Any]]:
    """Deterministic 24-recipe grid: 6 relief d x 2 goal (COST/CAP) x 2 mode (FIXED/ONLINE)."""
    recipes: list[dict[str, Any]] = []
    for relief in RELIEF_GRID:
        for goal in GOALS:
            for mode_id, mode, cfg in POOL_MODES:
                rid = len(recipes)
                recipes.append(
                    dict(
                        id=rid,
                        relief=float(relief),
                        goal=str(goal),
                        mode=str(mode),
                        config=dict(cfg),
                    )
                )
    assert len(recipes) == 24
    return recipes


build_recipes = build_pool_recipes


def relief_tag(relief: float) -> str:
    return f"d{float(relief):.2f}".replace(".", "p")


def initializer_relpath(phase: str, arm: str, seed: int, goal: str, relief: float) -> Path:
    return Path("initializers") / phase / f"{arm}_seed{seed}" / f"{goal}_{relief_tag(relief)}.json"


def stream_relpath(phase: str, arm: str, seed: int) -> Path:
    return Path("streams") / phase / f"{arm}_seed{seed}.npz"


def stream_metadata_relpath(phase: str, arm: str, seed: int) -> Path:
    return Path("streams") / phase / f"{arm}_seed{seed}_metadata.json"


def _init_checkpoint_jsonl(path: Path, header: dict[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
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


def _state_envelope(
    stage: str,
    shard: int | None = None,
    seed: int | None = None,
    arm: str | None = None,
) -> dict[str, Any]:
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


def _phase_wall_seconds(cfg: dict[str, Any], key: str, default: int) -> float:
    return float(_strict_int(cfg.get(key, default), key))


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
    if _strict_int(cfg.get("max_candidates"), "max_candidates") != 24 or _strict_int(
        cfg.get("max_cpu_seconds"), "max_cpu_seconds"
    ) != 14400:
        raise ValueError("Authorized 24-candidate / 14400-CPU-second budget differs")

    hist_wall = _strict_int(cfg.get("history_wall_seconds", 300), "history_wall_seconds")
    eval_wall = _strict_int(cfg.get("evaluation_wall_seconds", 300), "evaluation_wall_seconds")
    freeze_wall = _strict_int(cfg.get("freeze_wall_seconds", 60), "freeze_wall_seconds")
    agg_wall = _strict_int(cfg.get("aggregate_wall_seconds", 1200), "aggregate_wall_seconds")
    audit_wall = _strict_int(
        cfg.get("independent_audit_wall_seconds", 300), "independent_audit_wall_seconds"
    )
    reserve_wall = _strict_int(
        cfg.get("local_retry_reserve_seconds", 3840), "local_retry_reserve_seconds"
    )
    prior_cpu = _strict_int(cfg.get("prior_accounted_cpu_seconds", 0), "prior_accounted_cpu_seconds")
    max_jobs = _strict_int(
        cfg.get("maximum_science_parallel_jobs", 15), "maximum_science_parallel_jobs"
    )
    per_job_ncpus = _strict_int(cfg.get("per_job_ncpus", 1), "per_job_ncpus")
    agg_mem = _strict_int(cfg.get("aggregate_mem_gb", 96), "aggregate_mem_gb")

    if hist_wall != 300:
        raise ValueError("Protocol history_wall_seconds must equal 300")
    if eval_wall != 300:
        raise ValueError("Protocol evaluation_wall_seconds must equal 300")
    if freeze_wall != 60:
        raise ValueError("Protocol freeze_wall_seconds must equal 60")
    if agg_wall != 1200:
        raise ValueError("Protocol aggregate_wall_seconds must equal 1200")
    if audit_wall != 300:
        raise ValueError("Protocol independent_audit_wall_seconds must equal 300")
    if prior_cpu < 0:
        raise ValueError("Protocol prior_accounted_cpu_seconds must be nonnegative")
    if reserve_wall < 0 or reserve_wall + prior_cpu != 3840:
        raise ValueError(
            "Protocol local_retry_reserve_seconds + prior_accounted_cpu_seconds must equal 3840"
        )
    if max_jobs != 15:
        raise ValueError("Protocol maximum_science_parallel_jobs must equal 15")
    if per_job_ncpus != 1:
        raise ValueError("Protocol per_job_ncpus must equal 1")
    if agg_mem != 96:
        raise ValueError("Protocol aggregate_mem_gb must equal 96")

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
            != 1502
            or _strict_int(
                br.get("total_accounted_plus_open_reservations_cpu"),
                "budget_reservation.total_accounted_plus_open_reservations_cpu",
            )
            != 75687
            or _strict_int(
                br.get("global_cpu_limit_unchanged"),
                "budget_reservation.global_cpu_limit_unchanged",
            )
            != 86400
            or not (75687 < 86400)
        ):
            raise ValueError(
                "Protocol budget_reservation settlement values differ from authorized 75687/86400/1502"
            )

    expected = build_pool_recipes()
    recipes = cfg.get("recipes")
    if not isinstance(recipes, list) or len(recipes) != 24:
        raise ValueError("Protocol must declare exactly 24 recipes")

    top_keys = {"id", "relief", "goal", "mode", "config"}
    for idx, (rec, exp) in enumerate(zip(recipes, expected)):
        if not isinstance(rec, dict) or set(rec.keys()) != top_keys:
            raise ValueError(f"Recipe {idx} keys do not match exact deterministic 24-recipe schema")
        for k in ("id", "relief", "goal", "mode"):
            if not _exact_value_match(rec[k], exp[k]):
                raise ValueError(f"Recipe {idx} field {k}={rec[k]!r} differs from {exp[k]!r}")
        sub_actual = rec.get("config")
        sub_exp = exp["config"]
        if not isinstance(sub_actual, dict) or set(sub_actual.keys()) != set(sub_exp.keys()):
            raise ValueError(f"Recipe {idx} config keys do not match exact deterministic schema")
        for k, exp_v in sub_exp.items():
            if not _exact_value_match(sub_actual[k], exp_v):
                raise ValueError(f"Recipe {idx} config.{k}={sub_actual[k]!r} differs from {exp_v!r}")
    return [dict(r, config=dict(r["config"])) for r in recipes]


def verify_parent_bindings(
    cfg: dict[str, Any], *, require_ledger: bool = False
) -> tuple[Path, dict[str, Any], str]:
    if "parent_results" not in cfg:
        raise ValueError("Protocol missing parent_results")
    parent_dir = Path(cfg["parent_results"])
    freeze_path = parent_dir / "FINAL_FREEZE.json"
    open_path = parent_dir / "EVALUATION_OPEN.json"
    exp_freeze_sha = cfg.get("parent_freeze_sha256")
    if not isinstance(exp_freeze_sha, str) or not exp_freeze_sha:
        raise ValueError("Protocol missing parent_freeze_sha256")
    if not freeze_path.exists() or sha(freeze_path) != exp_freeze_sha:
        raise ValueError("Parent FINAL_FREEZE.json missing or SHA-256 mismatch")
    parent_freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if open_path.exists():
        open_data = json.loads(open_path.read_text(encoding="utf-8"))
        if open_data.get("freeze_sha256") != exp_freeze_sha:
            raise ValueError("Parent EVALUATION_OPEN.json freeze_sha256 mismatch")

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
    return parent_dir, parent_freeze, exp_freeze_sha


def resolve_meta_source_protocol(
    cfg: dict[str, Any],
    parent_mc_dir: Path,
    parent_mc_freeze: dict[str, Any],
) -> tuple[dict[str, Any], Path | None]:
    """Resolve original Meta protocol (profiles + cache timestamps) from parent MC -> Meta chain."""
    mc_proto_path = parent_mc_dir / "protocol_original.json"
    if not mc_proto_path.exists():
        mc_proto_path = parent_mc_dir / "protocol.json"
    mc_cfg: dict[str, Any] = {}
    if mc_proto_path.exists():
        if "protocol_sha256" in parent_mc_freeze and (parent_mc_dir / "protocol_original.json").exists():
            if sha(parent_mc_dir / "protocol_original.json") != parent_mc_freeze["protocol_sha256"]:
                raise ValueError("Parent MC protocol_original.json SHA-256 mismatch against parent FINAL_FREEZE")
        mc_cfg = json.loads(mc_proto_path.read_text(encoding="utf-8"))

    meta_dir: Path | None = None
    for candidate_key in ("meta_results", "grandparent_results"):
        if candidate_key in cfg and cfg[candidate_key]:
            meta_dir = Path(cfg[candidate_key])
            break
    if meta_dir is None and "parent_results" in mc_cfg and mc_cfg["parent_results"]:
        cand = Path(mc_cfg["parent_results"])
        if cand.exists():
            meta_dir = cand

    meta_cfg: dict[str, Any] = {}
    if meta_dir is not None and (meta_dir / "protocol_original.json").exists():
        meta_orig = meta_dir / "protocol_original.json"
        if (meta_dir / "FINAL_FREEZE.json").exists():
            meta_freeze = json.loads((meta_dir / "FINAL_FREEZE.json").read_text(encoding="utf-8"))
            if "protocol_sha256" in meta_freeze and sha(meta_orig) != meta_freeze["protocol_sha256"]:
                raise ValueError("Meta protocol_original.json SHA-256 mismatch against Meta FINAL_FREEZE")
        meta_cfg = json.loads(meta_orig.read_text(encoding="utf-8"))
    elif meta_dir is not None and (meta_dir / "protocol.json").exists():
        meta_cfg = json.loads((meta_dir / "protocol.json").read_text(encoding="utf-8"))

    merged: dict[str, Any] = {}
    for src in (meta_cfg, mc_cfg, cfg):
        for k in (
            "historical_cache",
            "historical_manifest_sha256",
            "evaluation_cache",
            "evaluation_manifest_sha256",
            "parent_profiles",
        ):
            if k in src and src[k]:
                if k in merged and merged[k] != src[k]:
                    raise ValueError(f"Conflicting source binding for {k} across Meta/MC/Pool protocols")
                merged[k] = src[k]

    for req in (
        "historical_cache",
        "historical_manifest_sha256",
        "evaluation_cache",
        "evaluation_manifest_sha256",
        "parent_profiles",
    ):
        if req not in merged:
            raise ValueError(f"Missing required source binding {req!r} in protocol chain")
    return merged, meta_dir


def load_verified_causal_profile_and_anchors(
    source_cfg: dict[str, Any],
    kind: str,
    seed: int,
    *,
    meta_dir: Path | None = None,
    parent_mc_dir: Path | None = None,
) -> tuple[np.ndarray, np.ndarray, str, str]:
    """Load verified original cache anchors.npy and causal R186 profile for kind in {'historical', 'evaluate'}."""
    if kind not in ("historical", "evaluate"):
        raise ValueError(f"Unsupported profile kind: {kind!r}")
    is_eval = kind == "evaluate"
    cache_dir = Path(source_cfg["evaluation_cache"] if is_eval else source_cfg["historical_cache"])
    manifest_sha = str(
        source_cfg["evaluation_manifest_sha256"]
        if is_eval
        else source_cfg["historical_manifest_sha256"]
    )
    verify_cache(cache_dir, manifest_sha)
    a_full = np.asarray(np.load(cache_dir / "anchors.npy"), dtype=np.int64)
    y_full = np.load(cache_dir / "shortfall.npy", mmap_mode="r")
    if a_full.ndim != 1 or a_full.size == 0 or np.any(np.diff(a_full) <= 0):
        raise ValueError(f"Cache {kind} anchors must be 1D, non-empty, and strictly increasing")

    profiles = source_cfg.get("parent_profiles") or {}
    key1 = f"profiles/{kind}_seed{seed}.npy"
    key2 = f"{kind}_seed{seed}"
    key3 = f"{kind}_seed{seed}.npy"
    entry = profiles.get(key1) or profiles.get(key2) or profiles.get(key3)
    if not isinstance(entry, dict):
        raise ValueError(f"Missing parent profile manifest entry for {key1}")

    candidates = [Path(entry["path"])]
    for base in (meta_dir, parent_mc_dir):
        if base is not None:
            candidates.append(Path(base) / key1)
    resolved = next((p for p in candidates if p.exists()), candidates[0])
    if not resolved.exists():
        raise ValueError(f"Causal anchor profile missing: {resolved}")
    if "bytes" in entry and resolved.stat().st_size != int(entry["bytes"]):
        raise ValueError(f"Causal anchor profile byte size mismatch for {resolved}")
    profile_sha = sha(resolved)
    if profile_sha != entry["sha256"]:
        raise ValueError(f"Causal anchor profile SHA-256 mismatch for {resolved}")

    b_full = np.asarray(np.load(resolved), dtype=np.float64)
    if b_full.shape != y_full.shape or not np.isfinite(b_full).all() or np.any(b_full < 0.0):
        raise ValueError(f"Invalid causal baseline profile shape or values in {resolved}")
    return a_full, b_full, profile_sha, manifest_sha


def select_exact_anchor_slice(
    cache_anchors: np.ndarray,
    profile_full: np.ndarray,
    bank_anchors: np.ndarray,
) -> np.ndarray:
    """Select exact causal anchor rows matching bank_anchors via searchsorted with exact timestamp match."""
    ca = np.asarray(cache_anchors, dtype=np.int64)
    ba = np.asarray(bank_anchors, dtype=np.int64)
    if ca.ndim != 1 or ca.size == 0 or np.any(np.diff(ca) <= 0):
        raise ValueError("Cache anchors must be 1D strictly increasing")
    if ba.ndim != 1 or ba.size == 0 or np.any(np.diff(ba) <= 0):
        raise ValueError("Bank anchors must be 1D strictly increasing")
    idx = np.searchsorted(ca, ba)
    if np.any(idx < 0) or np.any(idx >= ca.size) or not np.array_equal(ca[idx], ba):
        raise ValueError("Bank anchors do not match exact timestamps in original cache anchors")
    out = np.ascontiguousarray(profile_full[idx], dtype=np.float64)
    if out.shape != (ba.size, profile_full.shape[1]) or not np.isfinite(out).all() or np.any(out < 0.0):
        raise ValueError("Selected causal anchor slice is invalid")
    out.flags.writeable = False
    return out


def raw_experts_from_bank(bank: dict[str, Any]) -> np.ndarray:
    """Convert bank['raw_actions'] of shape (24, T, N) to contiguous raw experts (T, N, 24)."""
    raw = np.asarray(bank["raw_actions"], dtype=np.float64)
    if raw.ndim != 3 or raw.shape[0] != 24:
        raise ValueError(f"Expected bank raw_actions shape (24, T, N), got {raw.shape}")
    x = np.ascontiguousarray(np.moveaxis(raw, 0, -1), dtype=np.float64)
    assert x.shape == (raw.shape[1], raw.shape[2], 24)
    if not np.isfinite(x).all() or np.any(x < 0.0):
        raise ValueError("Raw 24 Meta experts must be finite and nonnegative")
    x.flags.writeable = False
    return x


def load_verified_parent_stream_bank(
    parent_mc_dir: Path,
    parent_mc_freeze: dict[str, Any],
    phase: str,
    seed: int,
    arm: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load cached stream bank from parent MC campaign and verify hashes against parent freeze/receipts."""
    s_rel = str(stream_relpath(phase, arm, seed)).replace("\\", "/")
    m_rel = str(stream_metadata_relpath(phase, arm, seed)).replace("\\", "/")
    s_path = parent_mc_dir / s_rel
    m_path = parent_mc_dir / m_rel

    if phase in ("inner", "outer"):
        all_streams = parent_mc_freeze.get("all_streams") or {}
        if s_rel not in all_streams:
            raise ValueError(f"Missing stream {s_rel} in parent FINAL_FREEZE.all_streams")
        s_entry = dict(all_streams[s_rel])
        exp_npz_sha = s_entry.get("npz_sha256")
        exp_meta_sha = s_entry.get("metadata_sha256")
        exp_raw_shas = s_entry.get("raw_action_sha256")
    elif phase == "evaluate":
        shard_idx = (int(seed) - 201) * 3 + META_ARMS.index(arm)
        eval_shard_rcpt_path = (
            parent_mc_dir / "shards" / "evaluate" / f"shard_{shard_idx:02d}_{arm}_seed{seed}" / "receipt.json"
        )
        inst_rcpt_path = parent_mc_dir / "instances" / "evaluate" / f"{arm}_seed{seed}" / "receipt.json"
        if not eval_shard_rcpt_path.exists() or not inst_rcpt_path.exists():
            raise ValueError(f"Missing parent evaluate shard or instance receipt for {arm}_seed{seed}")
        eval_shard_rcpt = json.loads(eval_shard_rcpt_path.read_text(encoding="utf-8"))
        inst_rcpt = json.loads(inst_rcpt_path.read_text(encoding="utf-8"))
        if eval_shard_rcpt.get("status") != "COMPLETED":
            raise ValueError(f"Parent evaluate shard {shard_idx} is not COMPLETED")
        s_entry = dict(eval_shard_rcpt.get("evaluate_stream") or {})
        exp_npz_sha = s_entry.get("npz_sha256") or inst_rcpt.get("bank_npz_sha256")
        exp_meta_sha = s_entry.get("metadata_sha256")
        exp_raw_shas = s_entry.get("raw_action_sha256")
        if inst_rcpt.get("bank_npz_sha256") and inst_rcpt.get("bank_npz_sha256") != exp_npz_sha:
            raise ValueError(f"Parent evaluate instance receipt bank_npz_sha256 mismatch for {arm}_seed{seed}")
    else:
        raise ValueError(f"Unsupported phase: {phase!r}")

    if not isinstance(exp_npz_sha, str) or not exp_npz_sha:
        raise ValueError(f"Missing expected NPZ SHA-256 for parent stream {s_rel}")
    bank = load_bank(
        s_path,
        expected_npz_sha256=exp_npz_sha,
        expected_metadata_sha256=exp_meta_sha,
    )
    meta = bank["metadata"]
    if meta.get("seed") != seed or meta.get("arm") != arm or meta.get("phase") != phase:
        raise ValueError(f"Loaded stream bank identity mismatch for {s_rel}")
    if exp_raw_shas is not None and meta.get("raw_action_sha256") != exp_raw_shas:
        raise ValueError(f"Loaded stream bank 24 raw_action_sha256 mismatch for {s_rel}")
    if s_entry.get("raw_actions_sha256") and meta.get("raw_actions_sha256") != s_entry.get("raw_actions_sha256"):
        raise ValueError(f"Loaded stream bank raw_actions_sha256 mismatch for {s_rel}")

    stream_record = dict(
        phase=phase,
        seed=seed,
        arm=arm,
        npz_path=s_rel,
        npz_sha256=exp_npz_sha,
        metadata_path=m_rel,
        metadata_sha256=sha(m_path),
        raw_actions_sha256=meta.get("raw_actions_sha256"),
        raw_action_sha256=meta.get("raw_action_sha256"),
    )
    return bank, stream_record


def _build_inner_no_prior_oof_record(
    *,
    seed: int,
    arm: str,
    relief: float,
    goal: str,
    episode_start: int,
    source_manifest_sha256: str,
    parent_profile_sha256: str,
) -> dict[str, Any]:
    """Declare pure anchor e0 25-weight initializer for inner phase (no prior OOF Meta stream exists)."""
    w0 = np.zeros(25, dtype=np.float64)
    w0[0] = 1.0
    w_list = w0.tolist()
    return dict(
        phase="inner",
        seed=int(seed),
        arm=str(arm),
        relief=float(relief),
        goal=str(goal),
        status="NO_PRIOR_OOF_ANCHOR",
        bundle_status="NO_PRIOR_OOF_ANCHOR",
        optimal=False,
        bundle_optimal=False,
        numerical_fitted=False,
        weights=w_list,
        raw_bundle_weights=w_list,
        canonical_initial=w_list,
        objective=None,
        bundle_objective=None,
        lower_bound=None,
        gap=None,
        mean_uncovered_power=None,
        bundle_mean_uncovered_power=None,
        uncovered_cap=None,
        anchor_mean_uncovered_power=None,
        anchor_objective=None,
        raw_actual_affine_feasible=True,
        actual_affine_feasible=True,
        repaired_to_anchor=False,
        repair_alpha=0.0,
        boundary_guard_count=0,
        max_boundary_violation=0.0,
        support_smoothing=0.0,
        fit_window=[],
        fit_anchor_start=None,
        fit_anchor_end=None,
        fit_issue_count=0,
        valid_fit_cells=0,
        episode_start=int(episode_start),
        last_label_release=None,
        n_raw_experts=24,
        n_experts=25,
        source_manifest_sha256=str(source_manifest_sha256),
        parent_profile_sha256=str(parent_profile_sha256),
        oof_source_phases=[],
        numerical_failure=None,
        elapsed_seconds=0.0,
    )


def fit_oof_pool_initializer(
    *,
    phase: str,
    seed: int,
    arm: str,
    relief: float,
    goal: str,
    oof_bank: dict[str, Any],
    b_oof: np.ndarray,
    episode_start: int,
    source_manifest_sha256: str,
    parent_profile_sha256: str,
    time_limit: float = 10.0,
) -> dict[str, Any]:
    """Fit 25-simplex weights on valid masked OOF Meta rows only, enforcing causal maturity."""
    fit_start = time.monotonic()
    a_oof = np.asarray(oof_bank["anchors"], dtype=np.int64)
    y_oof = np.asarray(oof_bank["shortfall"], dtype=np.float64)
    m_oof = np.asarray(oof_bank["mask"], dtype=bool)
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
    if y_oof.shape != b_arr.shape or m_oof.shape != b_arr.shape or x_oof.shape != (*b_arr.shape, 24):
        raise ValueError("OOF fit arrays shape mismatch")

    valid_cells = int(m_oof.sum())
    if valid_cells < 1:
        raise ValueError(f"No valid masked OOF cells available for {phase}/{arm}_seed{seed}")

    x_valid = np.ascontiguousarray(x_oof[m_oof], dtype=np.float64)
    b_valid = np.ascontiguousarray(b_arr[m_oof], dtype=np.float64)
    y_valid = np.ascontiguousarray(y_oof[m_oof], dtype=np.float64)
    if not np.isfinite(y_valid).all() or np.any(y_valid < 0.0):
        raise ValueError("Valid masked OOF shortfall contains NaN, Inf, or negative values")

    try:
        with threadpool_limits(limits=1):
            record = fit_signed(
                x_valid,
                b_valid,
                y_valid,
                relief=float(relief),
                goal=str(goal),
                time_limit=float(time_limit),
            )
    except Exception as exc:
        w_fb = np.zeros(25, dtype=np.float64)
        w_fb[0] = 1.0
        u_fb = float(np.maximum(y_valid - b_valid, 0.0).mean()) if np.isfinite(b_valid).all() else 0.0
        c_fb = (
            float((b_valid + 10.0 * np.maximum(y_valid - b_valid, 0.0)).mean() / 6.0)
            if np.isfinite(b_valid).all()
            else 0.0
        )
        record = dict(
            weights=w_fb.tolist(),
            raw_bundle_weights=w_fb.tolist(),
            canonical_initial=w_fb.tolist(),
            status="INITIALIZER_ERROR_DECLARED_ANCHOR_FALLBACK",
            bundle_status="ERROR",
            optimal=False,
            bundle_optimal=False,
            objective=c_fb,
            bundle_objective=c_fb,
            lower_bound=0.0,
            gap=c_fb,
            mean_uncovered_power=u_fb,
            bundle_mean_uncovered_power=u_fb,
            uncovered_cap=(u_fb if goal == "CAP" else None),
            anchor_mean_uncovered_power=u_fb,
            anchor_objective=c_fb,
            raw_actual_affine_feasible=True,
            actual_affine_feasible=True,
            repaired_to_anchor=True,
            repair_alpha=1.0,
            boundary_guard_count=0,
            max_boundary_violation=0.0,
            relief=float(relief),
            goal=str(goal),
            time_limit=float(min(float(time_limit), 10.0)),
            support_smoothing=0.0,
            numerical_failure=repr(exc),
            error=repr(exc),
            traceback=traceback.format_exc(),
        )

    w_arr = np.asarray(record["weights"], dtype=np.float64)
    w_canon = np.asarray(record["canonical_initial"], dtype=np.float64)
    if (
        w_arr.shape != (25,)
        or w_canon.shape != (25,)
        or not np.array_equal(w_arr, w_canon)
        or not np.isfinite(w_arr).all()
        or np.any(w_arr < 0.0)
        or not np.isclose(w_arr.sum(), 1.0, atol=1e-12, rtol=0.0)
    ):
        raise ValueError("Fitted OOF pool weights must be a 25-element probability simplex vector without smoothing")

    oof_phases = list(oof_bank["metadata"].get("phases") or [oof_bank["metadata"].get("phase")])
    record.update(
        phase=str(phase),
        seed=int(seed),
        arm=str(arm),
        relief=float(relief),
        goal=str(goal),
        numerical_fitted=True,
        weights=w_arr.tolist(),
        raw_bundle_weights=np.asarray(record["raw_bundle_weights"], dtype=np.float64).tolist(),
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


def _score_phase_pool_recipes(
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

    def record_success(
        recipe: dict[str, Any],
        actions: np.ndarray,
        ledger: np.ndarray | None,
        info: dict[str, Any],
    ) -> None:
        rid = int(recipe["id"])
        key = str(rid)
        act = np.ascontiguousarray(actions, dtype=np.float64)
        check_ledger, counts_local, days_local = score_actions(act, yy, mm, aa)
        if ledger is None:
            ledger = check_ledger
        else:
            if not np.allclose(ledger, check_ledger, rtol=0.0, atol=1e-8) or not np.array_equal(
                ledger[:, 3], check_ledger[:, 3]
            ):
                raise ValueError(f"Candidate {rid} ledger diverges from original-S score_actions")
        if ledger.shape != (len(days_local), 4) or not np.isfinite(ledger).all():
            raise ValueError(f"Invalid candidate ledger for recipe {rid}")
        idx_pos = ids.index(rid)
        array[idx_pos] = ledger
        means_list = (ledger.sum(axis=0) / counts_local.sum()).tolist()
        point[key] = [float(v) for v in means_list]
        status[key] = "COMPLETED"
        act_sha = prefix_sha256(act)
        hashes[key] = act_sha
        metadata[key] = dict(info)
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
                    relief=float(recipe["relief"]),
                    goal=str(recipe["goal"]),
                    mode=str(recipe["mode"]),
                    success=True,
                    status="COMPLETED",
                    error=None,
                    action_sha256=act_sha,
                    metrics=_checkpoint_phase_metrics(act, yy, mm, aa),
                ),
            )

    def record_failure(recipe: dict[str, Any], exc: BaseException) -> None:
        rid = int(recipe["id"])
        key = str(rid)
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
                    relief=float(recipe["relief"]),
                    goal=str(recipe["goal"]),
                    mode=str(recipe["mode"]),
                    success=False,
                    status="FAILED_PRESERVED",
                    error=repr(exc),
                    action_sha256=None,
                    metrics=None,
                ),
            )

    for relief in RELIEF_GRID:
        for goal in GOALS:
            group = [
                r
                for r in recipes
                if float(r["relief"]) == float(relief) and str(r["goal"]) == str(goal)
            ]
            if not group:
                continue
            init_rel = initializer_relpath(phase, arm, seed, goal, relief)
            init_path = out / init_rel
            try:
                init_rec = json.loads(init_path.read_text(encoding="utf-8"))
                init_sha = sha(init_path)
                w0 = np.asarray(init_rec["canonical_initial"], dtype=np.float64)
                w_raw = np.asarray(init_rec["weights"], dtype=np.float64)
                if w0.shape != (25,) or not np.array_equal(w0, w_raw):
                    raise ValueError(f"Initializer {init_rel} weights must be 25-simplex with zero smoothing")
                delta = signed_experts(xx, bb, relief=float(relief))
            except Exception as init_exc:
                for r in group:
                    record_failure(r, init_exc)
                continue

            fixed_recipes = [r for r in group if r["mode"] == "FIXED"]
            online_recipes = [r for r in group if r["mode"] != "FIXED"]

            static_action: np.ndarray | None = None
            for r in fixed_recipes:
                deadline_check(deadline)
                try:
                    with threadpool_limits(limits=1):
                        act, guard_info = signed_action(bb, delta, w0, relief=float(relief), return_info=True)
                    static_action = act
                    record_success(
                        r,
                        actions=act,
                        ledger=None,
                        info=dict(
                            relief=float(relief),
                            goal=str(goal),
                            mode=str(r["mode"]),
                            initializer_path=str(init_rel).replace("\\", "/"),
                            initializer_sha256=init_sha,
                            initializer_status=init_rec["status"],
                            initializer_optimal=bool(init_rec["optimal"]),
                            numerical_fitted=bool(init_rec.get("numerical_fitted", phase != "inner")),
                            repaired_to_anchor=bool(init_rec.get("repaired_to_anchor", False)),
                            boundary_guard_count=int(guard_info["boundary_guard_count"]),
                            max_boundary_violation=float(guard_info["max_boundary_violation"]),
                            parent_profile_sha256=profile_sha,
                            episode_restart=True,
                        ),
                    )
                except Exception as exc:
                    record_failure(r, exc)

            if static_action is None:
                try:
                    with threadpool_limits(limits=1):
                        static_action = signed_action(bb, delta, w0, relief=float(relief))
                except Exception:
                    static_action = None

            if online_recipes:
                configs = [MixtureConfig(**r["config"]) for r in online_recipes]
                try:
                    deadline_check(deadline)
                    with threadpool_limits(limits=1):
                        # Pass RAW 24 Meta experts xx (shape [T, N, 24]) directly to run_signed!
                        res = run_signed(
                            xx,
                            bb,
                            yy,
                            mm,
                            aa,
                            configs,
                            w0,
                            relief=float(relief),
                            score=True,
                            return_actions=True,
                        )
                    if static_action is None:
                        raise ValueError("Static action unavailable for warm-start equality check")
                    n_pre = min(8, len(aa))
                    if n_pre > 0 and (len(aa) < 8 or int(aa[n_pre - 1]) <= int(aa[0]) + 7):
                        expected_pre = np.broadcast_to(
                            static_action[:n_pre], (len(online_recipes), n_pre, bb.shape[1])
                        )
                        if not np.array_equal(res["actions"][:, :n_pre], expected_pre):
                            raise ValueError(
                                "Online Meta-pool update does not share exact first 8 actions with FIXED"
                            )
                    elif len(aa) > 0:
                        expected_first = np.broadcast_to(
                            static_action[:1], (len(online_recipes), 1, bb.shape[1])
                        )
                        if not np.array_equal(res["actions"][:, :1], expected_first):
                            raise ValueError(
                                "Online Meta-pool initial action differs from FIXED"
                            )
                    for idx, r in enumerate(online_recipes):
                        rec_info = dict(
                            relief=float(relief),
                            goal=str(goal),
                            mode=str(r["mode"]),
                            initializer_path=str(init_rel).replace("\\", "/"),
                            initializer_sha256=init_sha,
                            initializer_status=init_rec["status"],
                            initializer_optimal=bool(init_rec["optimal"]),
                            numerical_fitted=bool(init_rec.get("numerical_fitted", phase != "inner")),
                            repaired_to_anchor=bool(init_rec.get("repaired_to_anchor", False)),
                            final_weights=res["metadata"]["final_weights"][idx],
                            final_lambda_u=res["metadata"]["final_lambda_u"][idx],
                            maximum_lambda_u=res["metadata"]["maximum_lambda_u"][idx],
                            boundary_guard_count=int(res["metadata"]["boundary_guard_counts"][idx]),
                            max_boundary_violation=float(res["metadata"]["max_boundary_violation"]),
                            feedback_updates=int(res["metadata"]["feedback_updates"]),
                            parent_profile_sha256=profile_sha,
                            feedback_rule="source_anchor+7<decision_anchor",
                            episode_restart=True,
                        )
                        record_success(
                            r,
                            actions=res["actions"][idx],
                            ledger=res["ledger"][idx],
                            info=rec_info,
                        )
                except Exception as batch_exc:
                    save(
                        destination / f"{goal}_{relief_tag(relief)}_batch_failure.json",
                        dict(error=repr(batch_exc), traceback=traceback.format_exc()),
                    )
                    for r in online_recipes:
                        try:
                            deadline_check(deadline)
                            with threadpool_limits(limits=1):
                                single = run_signed(
                                    xx,
                                    bb,
                                    yy,
                                    mm,
                                    aa,
                                    [MixtureConfig(**r["config"])],
                                    w0,
                                    relief=float(relief),
                                    score=True,
                                    return_actions=True,
                                )
                            if static_action is None:
                                raise ValueError("Static action unavailable for warm-start equality check")
                            n_pre = min(8, len(aa))
                            if n_pre > 0 and (len(aa) < 8 or int(aa[n_pre - 1]) <= int(aa[0]) + 7):
                                if not np.array_equal(single["actions"][0, :n_pre], static_action[:n_pre]):
                                    raise ValueError(
                                        "Online Meta-pool update does not share exact first 8 actions with FIXED"
                                    )
                            elif len(aa) > 0 and not np.array_equal(
                                single["actions"][0, :1], static_action[:1]
                            ):
                                raise ValueError("Online Meta-pool initial action differs from FIXED")
                            single_info = dict(
                                relief=float(relief),
                                goal=str(goal),
                                mode=str(r["mode"]),
                                initializer_path=str(init_rel).replace("\\", "/"),
                                initializer_sha256=init_sha,
                                initializer_status=init_rec["status"],
                                initializer_optimal=bool(init_rec["optimal"]),
                                numerical_fitted=bool(init_rec.get("numerical_fitted", phase != "inner")),
                                repaired_to_anchor=bool(init_rec.get("repaired_to_anchor", False)),
                                final_weights=single["metadata"]["final_weights"][0],
                                final_lambda_u=single["metadata"]["final_lambda_u"][0],
                                maximum_lambda_u=single["metadata"]["maximum_lambda_u"][0],
                                boundary_guard_count=int(single["metadata"]["boundary_guard_counts"][0]),
                                max_boundary_violation=float(single["metadata"]["max_boundary_violation"]),
                                feedback_updates=int(single["metadata"]["feedback_updates"]),
                                parent_profile_sha256=profile_sha,
                                feedback_rule="source_anchor+7<decision_anchor",
                                episode_restart=True,
                            )
                            record_success(
                                r,
                                actions=single["actions"][0],
                                ledger=single["ledger"][0],
                                info=single_info,
                            )
                        except Exception as exc:
                            record_failure(r, exc)

    for rid in ids:
        if str(rid) not in status:
            status[str(rid)] = "NOT_EVALUATED_PRESERVED"

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
            deadline = start + _phase_wall_seconds(cfg, "history_wall_seconds", 300) - 20.0
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

        parent_mc_dir, parent_mc_freeze, parent_freeze_sha = verify_parent_bindings(
            cfg, require_ledger=False
        )
        source_cfg, meta_dir = resolve_meta_source_protocol(cfg, parent_mc_dir, parent_mc_freeze)

        # Load ONLY historical cache anchors and historical causal R186 profile (never touch evaluation cache or eval stream!)
        hist_cache_anchors, b_hist_full, hist_profile_sha, hist_manifest_sha = (
            load_verified_causal_profile_and_anchors(
                source_cfg,
                "historical",
                seed,
                meta_dir=meta_dir,
                parent_mc_dir=parent_mc_dir,
            )
        )

        deadline_check(deadline)
        inner_bank, inner_stream_rec = load_verified_parent_stream_bank(
            parent_mc_dir, parent_mc_freeze, "inner", seed, arm
        )
        outer_bank, outer_stream_rec = load_verified_parent_stream_bank(
            parent_mc_dir, parent_mc_freeze, "outer", seed, arm
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
                schema="meta-pool-initializer-checkpoint-v1",
                stage="history",
                shard=shard,
                seed=seed,
                arm=arm,
                study_id=cfg.get("study_id"),
                protocol_sha256=protocol_sha,
                source_commit=state["source_commit"],
                source_versions=source_versions,
                parent_freeze_sha256=parent_freeze_sha,
                initializers_expected=36,
            ),
        )

        init_records: list[dict[str, Any]] = []
        fit_time_limit = float(cfg.get("fit_time_limit_seconds", 10.0))

        # 1. Prepare all 36 initializers (inner: 12 declared anchor e0; outer: 12 fitted on inner OOF; evaluate: 12 fitted on inner+outer OOF)
        for phase in ("inner", "outer", "evaluate"):
            begin, _, _ = PHASES[phase]
            if phase != "inner":
                oof_bank = inner_bank if phase == "outer" else hist_joined_bank
                b_oof = b_inner if phase == "outer" else b_joined
                # Ensure episode_start respects actual bank start or PHASES[phase][0]
                actual_begin = (
                    int(outer_bank["anchors"][0]) if phase == "outer" else int(begin)
                )
            else:
                oof_bank = None
                b_oof = None
                actual_begin = int(inner_bank["anchors"][0])

            for relief in RELIEF_GRID:
                for goal in GOALS:
                    deadline_check(deadline)
                    if phase == "inner":
                        rec = _build_inner_no_prior_oof_record(
                            seed=seed,
                            arm=arm,
                            relief=relief,
                            goal=goal,
                            episode_start=actual_begin,
                            source_manifest_sha256=hist_manifest_sha,
                            parent_profile_sha256=hist_profile_sha,
                        )
                    else:
                        assert oof_bank is not None and b_oof is not None
                        rec = fit_oof_pool_initializer(
                            phase=phase,
                            seed=seed,
                            arm=arm,
                            relief=relief,
                            goal=goal,
                            oof_bank=oof_bank,
                            b_oof=b_oof,
                            episode_start=actual_begin,
                            source_manifest_sha256=hist_manifest_sha,
                            parent_profile_sha256=hist_profile_sha,
                            time_limit=fit_time_limit,
                        )
                    rel_init = initializer_relpath(phase, arm, seed, goal, relief)
                    init_path = out / rel_init
                    save(init_path, rec)
                    rec_sha = sha(init_path)
                    entry = dict(
                        phase=phase,
                        seed=int(seed),
                        arm=str(arm),
                        goal=str(goal),
                        relief=float(relief),
                        path=str(rel_init).replace("\\", "/"),
                        sha256=rec_sha,
                        status=rec["status"],
                        optimal=bool(rec["optimal"]),
                        numerical_fitted=bool(rec["numerical_fitted"]),
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

        assert len(init_records) == 36
        num_fitted = sum(1 for r in init_records if r["numerical_fitted"])
        num_anchor = sum(1 for r in init_records if not r["numerical_fitted"])
        assert num_fitted == 24 and num_anchor == 12

        recipe_ckpt_path = _init_checkpoint_jsonl(
            shard_dir / CHECKPOINT_FILENAME,
            dict(
                record_type="HEADER",
                schema="meta-pool-recipe-checkpoint-v1",
                stage="history",
                shard=shard,
                seed=seed,
                arm=arm,
                study_id=cfg.get("study_id"),
                protocol_sha256=protocol_sha,
                source_commit=state["source_commit"],
                source_versions=source_versions,
                parent_freeze_sha256=parent_freeze_sha,
                inner_npz_sha256=inner_stream_rec["npz_sha256"],
                outer_npz_sha256=outer_stream_rec["npz_sha256"],
                recipes_expected=len(recipes),
            ),
        )

        # 2. Score all 24 recipes on inner and outer
        sum_inner = _score_phase_pool_recipes(
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
        sum_outer = _score_phase_pool_recipes(
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


def history_summary(points: np.ndarray, recipes: list[dict[str, Any]]) -> dict[str, Any]:
    """Select historical minimum_C and minimum_maxV across all 24 pool recipes per arm without qualification filter."""
    complete = np.isfinite(points).all(axis=(1, 2, 3))
    roles: dict[str, dict[str, Any]] = {}
    by_goal_roles: dict[str, dict[str, Any]] = {}
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
        for goal in GOALS:
            g_pool = [j for j in pool if recipes[j]["goal"] == goal]
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
                by_goal_roles[f"{goal}_{arm}"] = dict(
                    minimum_C_id=int(recipes[g_c]["id"]),
                    minimum_maxV_id=int(recipes[g_v]["id"]),
                )
    return dict(
        roles=roles,
        by_goal_roles=by_goal_roles,
        complete_recipe_count=int(complete.sum()),
        all_recipes_retained=True,
        qualification_did_not_filter_instances=True,
        selection_scope="Historical outer minimum_C/minimum_maxV per arm (C/P/Z) across all 24 pool recipes without qualification filter; all 24 recipes still scored in evaluation",
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
            deadline = start + _phase_wall_seconds(cfg, "freeze_wall_seconds", 60) - 20.0
        deadline_check(deadline)

        parent_mc_dir, parent_mc_freeze, parent_freeze_sha = verify_parent_bindings(
            cfg, require_ledger=False
        )
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
            if r_data.get("parent_freeze_sha256") != parent_freeze_sha:
                raise ValueError(f"History shard {shard} parent_freeze_sha256 differs from current protocol")
            if (
                r_data.get("initializers_prepared") != 36
                or r_data.get("initializers_numerical_fitted") != 24
                or r_data.get("initializers_anchor_declared") != 12
                or r_data.get("new_models_fitted") != 0
            ):
                raise ValueError(f"History shard {shard} initializer accounting mismatch")

            total_numerical_fits += int(r_data["initializers_numerical_fitted"])
            total_anchor_records += int(r_data["initializers_anchor_declared"])

            inits = r_data.get("initializers")
            if not isinstance(inits, list) or len(inits) != 36:
                raise ValueError(f"History shard {shard} receipt must record 36 initializers")
            for item in inits:
                rel_key = str(item.get("path", "")).replace("\\", "/")
                rec_sha = item.get("sha256")
                if not rel_key or not isinstance(rec_sha, str):
                    raise ValueError(f"History shard {shard} receipt has invalid initializer entry")
                full_init = out / rel_key
                if not full_init.exists():
                    raise ValueError(f"Missing required initializer on disk: {full_init}")
                actual_sha = sha(full_init)
                if actual_sha != rec_sha:
                    raise ValueError(
                        f"Initializer {rel_key} SHA-256 mismatch against history shard {shard} receipt"
                    )
                recorded_initializers[rel_key] = actual_sha

            streams = r_data.get("streams") or {}
            if len(streams) != 2:
                raise ValueError(f"History shard {shard} receipt must bind inner and outer stream banks")
            for phase in ("inner", "outer"):
                s_rel = str(stream_relpath(phase, arm, seed)).replace("\\", "/")
                if s_rel not in streams:
                    raise ValueError(f"Missing stream {s_rel} in history shard {shard} receipt")
                s_entry = streams[s_rel]
                _, verified_stream = load_verified_parent_stream_bank(
                    parent_mc_dir, parent_mc_freeze, phase, seed, arm
                )
                if (
                    s_entry.get("npz_sha256") != verified_stream["npz_sha256"]
                    or s_entry.get("metadata_sha256") != verified_stream["metadata_sha256"]
                    or s_entry.get("raw_actions_sha256") != verified_stream["raw_actions_sha256"]
                ):
                    raise ValueError(f"Stream bank SHA-256 mismatch against parent freeze for {s_rel}")
                all_streams[s_rel] = dict(verified_stream)

                inst_rcpt_rel = f"instances/{phase}/{arm}_seed{seed}/receipt.json"
                inst_rcpt_full = out / inst_rcpt_rel
                if not inst_rcpt_full.exists():
                    raise ValueError(f"Missing history instance receipt: {inst_rcpt_full}")
                all_instance_receipts[inst_rcpt_rel] = sha(inst_rcpt_full)

            shard_receipts.append(r_data)

        all_initializers: dict[str, str] = {}
        for phase in ("inner", "outer", "evaluate"):
            for seed in SEEDS:
                for arm in META_ARMS:
                    for relief in RELIEF_GRID:
                        for goal in GOALS:
                            rel = initializer_relpath(phase, arm, seed, goal, relief)
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

        assert len(all_initializers) == 540
        assert total_numerical_fits == 360
        assert total_anchor_records == 180
        assert len(all_streams) == 30
        assert len(all_instance_receipts) == 30

        for phase in ("inner", "outer"):
            points, _ = collect(out, phase, recipes)
            np.save(out / f"{phase}_points.npy", points, allow_pickle=False)
            save(out / f"{phase}_selection.json", history_summary(points, recipes))

        if (out / "FINAL_FREEZE.json").exists() or (out / "EVALUATION_OPEN.json").exists():
            raise FileExistsError("FINAL_FREEZE.json or EVALUATION_OPEN.json already exists")
        freeze_payload = dict(
            time_utc=datetime.now(timezone.utc).isoformat(),
            study_id=cfg.get("study_id", "meta_pool_20261025_v1"),
            source_commit=os.environ.get("CAMPAIGN_RELEASE", "LOCAL_SYNTHETIC"),
            protocol_sha256=protocol_sha,
            source_versions=source_versions,
            parent_freeze_sha256=parent_freeze_sha,
            parent_ledger_sha256=cfg["parent_ledger_sha256"],
            parent_span3_sha256=cfg["parent_span3_sha256"],
            recipes=recipes,
            historical_roles=json.loads((out / "outer_selection.json").read_text(encoding="utf-8")),
            parent_historical_roles=parent_mc_freeze.get("historical_roles"),
            all_initializers=all_initializers,
            all_streams=all_streams,
            all_instance_receipts=all_instance_receipts,
            total_initializers=len(all_initializers),
            numerical_fits=total_numerical_fits,
            anchor_declarations=total_anchor_records,
            new_models_fitted=0,
            history_shard_count=len(shard_receipts),
            selection_scope="Historical outer minimum_C/minimum_maxV per arm (C/P/Z) across all 24 pool recipes without qualification filter; all 24 evaluated",
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
            deadline = start + _phase_wall_seconds(cfg, "evaluation_wall_seconds", 300) - 20.0
        deadline_check(deadline)

        freeze = verify_freeze_barrier(cfg, out, protocol_path=protocol_path, root=root)
        parent_mc_dir, parent_mc_freeze, parent_freeze_sha = verify_parent_bindings(
            cfg, require_ledger=False
        )
        source_cfg, meta_dir = resolve_meta_source_protocol(cfg, parent_mc_dir, parent_mc_freeze)

        all_inits = freeze.get("all_initializers") or {}
        if len(all_inits) != 540:
            raise ValueError("FINAL_FREEZE.json must bind all 540 initializers")
        for phase_check in ("inner", "outer", "evaluate"):
            for relief in RELIEF_GRID:
                for goal in GOALS:
                    rel = str(initializer_relpath(phase_check, arm, seed, goal, relief)).replace("\\", "/")
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
                parent_mc_dir, parent_mc_freeze, phase_check, seed, arm
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
                parent_mc_dir=parent_mc_dir,
            )
        )
        eval_bank, eval_stream_rec = load_verified_parent_stream_bank(
            parent_mc_dir, parent_mc_freeze, "evaluate", seed, arm
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
                schema="meta-pool-recipe-checkpoint-v1",
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
                evaluate_npz_sha256=eval_stream_rec["npz_sha256"],
                recipes_expected=len(recipes),
            ),
        )

        summary = _score_phase_pool_recipes(
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


def resolve_parent_mc_historical_comparators(
    parent_mc_freeze: dict[str, Any],
    parent_names: list[str],
) -> dict[str, tuple[str, str]]:
    """Extract frozen historical minimum_C and minimum_maxV MC policy names per arm from parent FINAL_FREEZE."""
    hist_roles = parent_mc_freeze.get("historical_roles") or {}
    roles = hist_roles.get("roles") if "roles" in hist_roles else hist_roles
    if not isinstance(roles, dict):
        raise ValueError("Parent FINAL_FREEZE missing historical_roles.roles")
    parent_set = set(parent_names)
    resolved: dict[str, tuple[str, str]] = {}
    for arm in META_ARMS:
        entry = roles.get(arm)
        if not isinstance(entry, dict):
            raise ValueError(f"Parent FINAL_FREEZE historical_roles missing arm {arm!r}")
        if "minimum_C_id" not in entry or "minimum_maxV_id" not in entry:
            raise ValueError(f"Parent FINAL_FREEZE historical_roles[{arm!r}] missing minimum_C_id or minimum_maxV_id")
        min_c_id = _strict_int(entry["minimum_C_id"], f"historical_roles.{arm}.minimum_C_id")
        min_v_id = _strict_int(entry["minimum_maxV_id"], f"historical_roles.{arm}.minimum_maxV_id")
        mc_c = f"{PARENT_POLICY_PREFIX}{min_c_id:03d}_{arm}"
        mc_v = f"{PARENT_POLICY_PREFIX}{min_v_id:03d}_{arm}"
        if mc_c not in parent_set or mc_v not in parent_set:
            raise ValueError(f"Parent family missing historical MC comparator {mc_c!r} or {mc_v!r}")
        resolved[arm] = (mc_c, mc_v)
    return resolved


def build_extended_family(
    parent_span3: dict[str, Any],
    recipes: list[dict[str, Any]],
    parent_mc_freeze: dict[str, Any],
    *,
    expected_parent_policies: int = 968,
    expected_parent_comparisons: int = 3639,
) -> tuple[list[str], list[bool], list[tuple[str, str]], list[tuple[str, str]], dict[str, dict[str, str]]]:
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

    mc_hist_comparators = resolve_parent_mc_historical_comparators(parent_mc_freeze, parent_names)

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

    fixed_lookup = {
        (float(r["relief"]), str(r["goal"])): int(r["id"])
        for r in recipes
        if r["mode"] == "FIXED"
    }
    assert len(fixed_lookup) == 12

    new_pairs_raw: list[tuple[str, str]] = []
    for r in recipes:
        rid = int(r["id"])
        d_val = float(r["relief"])
        goal = str(r["goal"])
        for arm in META_ARMS:
            policy = f"{POLICY_PREFIX}{rid:03d}_{arm}"
            mc_min_c, mc_min_v = mc_hist_comparators[arm]
            for comparator in ("REF", "R0182_P", "GUARDED_FIXED_P", mc_min_c, mc_min_v):
                new_pairs_raw.append((policy, comparator))
            if r["mode"] != "FIXED":
                fixed_id = fixed_lookup[(d_val, goal)]
                new_pairs_raw.append((policy, f"{POLICY_PREFIX}{fixed_id:03d}_{arm}"))
        # Within-recipe representation pairs: P vs C, Z vs C, Z vs P (3 * 24 = 72 pairs)
        new_pairs_raw.append((f"{POLICY_PREFIX}{rid:03d}_P", f"{POLICY_PREFIX}{rid:03d}_C"))
        new_pairs_raw.append((f"{POLICY_PREFIX}{rid:03d}_Z", f"{POLICY_PREFIX}{rid:03d}_C"))
        new_pairs_raw.append((f"{POLICY_PREFIX}{rid:03d}_Z", f"{POLICY_PREFIX}{rid:03d}_P"))

    # Nominal count before deduplication: 360 base + 36 online-vs-fixed + 72 rep = 468
    assert len(new_pairs_raw) == 468
    seen = set(comparisons)
    if len(seen) != len(comparisons):
        raise ValueError("Parent comparisons contain unexpected duplicates")
    for pair in new_pairs_raw:
        if pair not in seen:
            comparisons.append(pair)
            seen.add(pair)

    comparator_summary = {
        arm: dict(minimum_C=pair[0], minimum_maxV=pair[1])
        for arm, pair in mc_hist_comparators.items()
    }
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
        parent_mc_dir, parent_mc_freeze, parent_freeze_sha = verify_parent_bindings(
            cfg, require_ledger=True
        )

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
                raise ValueError(
                    f"Evaluate shard {shard} freeze_sha256 does not match current FINAL_FREEZE.json"
                )
            if r_data.get("parent_freeze_sha256") != parent_freeze_sha:
                raise ValueError(f"Evaluate shard {shard} parent_freeze_sha256 mismatch")

            eval_s = r_data.get("evaluate_stream") or {}
            _, verified_eval_s = load_verified_parent_stream_bank(
                parent_mc_dir, parent_mc_freeze, "evaluate", seed, arm
            )
            if (
                eval_s.get("npz_sha256") != verified_eval_s["npz_sha256"]
                or eval_s.get("metadata_sha256") != verified_eval_s["metadata_sha256"]
            ):
                raise ValueError(f"Evaluate shard {shard} stream SHA-256 mismatch against parent")

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

        parent_ledger_path = parent_mc_dir / "all_daily_ledger.npz"
        parent_span3_path = parent_mc_dir / "inference_span3.json"
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

        names, parent_avail, aliases, comparisons, mc_hist_comparators = build_extended_family(
            parent_span3,
            recipes,
            parent_mc_freeze,
            expected_parent_policies=int(cfg.get("expected_parent_policies", 968)),
            expected_parent_comparisons=int(cfg.get("expected_parent_comparisons", 3639)),
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
        assert total_policy_count == int(cfg.get("expected_parent_policies", 968)) + 72
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
                parent_mc_historical_comparators=mc_hist_comparators,
                parent_policy_count=parent_policy_count,
                new_policy_count=new_policy_count,
                parent_comparison_count=parent_comparison_count,
                new_comparison_count=len(comparisons) - parent_comparison_count,
                total_comparison_count=len(comparisons),
                nominal_family_size=nominal_coords,
            ),
        )

        # Save consolidated 540-entry weights summary JSON (no giant action cache)
        weights_summary: dict[str, Any] = {}
        for phase in ("inner", "outer", "evaluate"):
            for seed in SEEDS:
                for arm in META_ARMS:
                    for relief in RELIEF_GRID:
                        for goal in GOALS:
                            rel = initializer_relpath(phase, arm, seed, goal, relief)
                            rel_key = str(rel).replace("\\", "/")
                            init_data = json.loads((out / rel).read_text(encoding="utf-8"))
                            weights_summary[rel_key] = dict(
                                phase=phase,
                                seed=int(seed),
                                arm=str(arm),
                                relief=float(relief),
                                goal=str(goal),
                                status=init_data["status"],
                                optimal=bool(init_data["optimal"]),
                                numerical_fitted=bool(init_data["numerical_fitted"]),
                                fit_window=init_data["fit_window"],
                                fit_issue_count=int(init_data["fit_issue_count"]),
                                valid_fit_cells=int(init_data["valid_fit_cells"]),
                                last_label_release=init_data["last_label_release"],
                                episode_start=int(init_data["episode_start"]),
                                weights=init_data["weights"],
                                canonical_initial=init_data["canonical_initial"],
                                sha256=sha(out / rel),
                            )
        assert len(weights_summary) == 540
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
        verify_parent_bindings(cfg, require_ledger=True)

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
            total_initializers=540,
            numerical_fits=360,
            anchor_declarations=180,
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
