"""Distributed multi-stage adapter for the 24-recipe conditional pool numerical refinement campaign.

Uses an isolated private module instance of scripts/run_conditional_pool.py per process with explicit
dependency injection so shared imports and original source files remain untouched.
Note: On-disk initializer filenames within the new campaign directory remain CP{id:03d}.json as
produced by isolated base.initializer_relpath, while policy names use POLICY_PREFIX = "NR".
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
from repo_paths import Path, repository_root
import sys
from typing import Any

ROOT = Path(repository_root())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from threadpoolctl import threadpool_limits

from scripts.run_meta_pool import _exact_value_match
from scripts.run_mixture_closed_loop import save, sha
from scripts.run_residual_meta import _strict_int, shard_assignment
import windfarm_moe.conditional_convex_pool as kernel_mod
from windfarm_moe.residual_meta import META_ARMS

POLICY_PREFIX = "NR"
PARENT_POLICY_PREFIX = "CP"
DEFAULT_REFINED_RECIPE_IDS: tuple[int, ...] = (16, 19, 22, 23)
DEFAULT_UNCHANGED_RECIPE_IDS: tuple[int, ...] = tuple(
    rid for rid in range(24) if rid not in DEFAULT_REFINED_RECIPE_IDS
)
REFINEMENT_TIME_LIMIT: float = 60.0
REFINEMENT_TIME_BUDGET_CEILING: float = 60.0


def _load_isolated_base_module() -> Any:
    base_path = ROOT / "scripts" / "run_conditional_pool.py"
    spec = importlib.util.spec_from_file_location("_isolated_run_conditional_pool", base_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load isolated base module from {base_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.POLICY_PREFIX = POLICY_PREFIX
    mod.PARENT_POLICY_PREFIX = PARENT_POLICY_PREFIX
    return mod


_BASE = _load_isolated_base_module()
_ORIG_BASE_BUILD_EXTENDED_FAMILY = _BASE.build_extended_family
_ORIG_BASE_FIT_OOF_INITIALIZER = _BASE.fit_oof_conditional_pool_initializer
_ORIG_BASE_INFER_CAMPAIGN = _BASE.infer_campaign

GROUPS_GRID = _BASE.GROUPS_GRID
RELIEF_GRID = _BASE.RELIEF_GRID
CAP_MODES = _BASE.CAP_MODES
COMMON_COMPARATORS = _BASE.COMMON_COMPARATORS
build_conditional_pool_recipes = _BASE.build_conditional_pool_recipes
build_recipes = _BASE.build_conditional_pool_recipes
initializer_relpath = _BASE.initializer_relpath
history_summary = _BASE.history_summary
verify_freeze_barrier = _BASE.verify_freeze_barrier


def _verify_freeze_protocol(camp_dir: Path, exp_freeze_sha: str, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    freeze_path = camp_dir / "FINAL_FREEZE.json"
    if not freeze_path.exists() or sha(freeze_path) != exp_freeze_sha:
        raise ValueError(f"{label} FINAL_FREEZE.json missing or SHA-256 mismatch")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    open_path = camp_dir / "EVALUATION_OPEN.json"
    if open_path.exists():
        open_data = json.loads(open_path.read_text(encoding="utf-8"))
        if open_data.get("freeze_sha256") != exp_freeze_sha:
            raise ValueError(f"{label} EVALUATION_OPEN.json freeze_sha256 mismatch")
        if "protocol_sha256" in freeze and open_data.get("protocol_sha256") != freeze["protocol_sha256"]:
            raise ValueError(f"{label} EVALUATION_OPEN.json protocol_sha256 mismatch")
    orig_path = camp_dir / "protocol_original.json"
    res_path = camp_dir / "protocol.json"
    proto_path = orig_path if orig_path.exists() else res_path
    if not proto_path.exists():
        raise ValueError(f"{label} protocol_original.json / protocol.json missing")
    if "protocol_sha256" in freeze and orig_path.exists() and sha(orig_path) != freeze["protocol_sha256"]:
        raise ValueError(f"{label} protocol_original.json SHA-256 mismatch against FINAL_FREEZE")
    proto_cfg = json.loads(proto_path.read_text(encoding="utf-8"))
    if orig_path.exists() and res_path.exists():
        if json.loads(res_path.read_text(encoding="utf-8")) != proto_cfg:
            raise ValueError(f"{label} protocol.json semantic mismatch against protocol_original.json")
    return freeze, proto_cfg


def verify_parent_and_stream_bindings(
    cfg: dict[str, Any], *, require_ledger: bool = False
) -> tuple[Path, dict[str, Any], str, Path, dict[str, Any], str]:
    parent_cp_dir, _, parent_cp_freeze_sha = _BASE.verify_parent_bindings(cfg, require_ledger=require_ledger)
    parent_cp_freeze, cp_cfg = _verify_freeze_protocol(parent_cp_dir, parent_cp_freeze_sha, "Parent CP")
    if not cp_cfg.get("parent_results") or not cp_cfg.get("parent_freeze_sha256"):
        raise ValueError("Parent CP protocol missing parent_results or parent_freeze_sha256")

    cp_stream_str = cp_cfg.get("stream_parent_results")
    if not isinstance(cp_stream_str, str) or not cp_stream_str:
        raise ValueError("Parent CP protocol missing explicit stream_parent_results")
    stream_root_str = cfg.get("stream_parent_results") or cp_stream_str
    if not isinstance(stream_root_str, str) or not stream_root_str or Path(str(stream_root_str)) != Path(cp_stream_str):
        raise ValueError("Conflicting stream_parent_results between protocol and parent CP protocol")
    stream_mc_dir = Path(stream_root_str)

    cp_stream_sha = cp_cfg.get("stream_parent_freeze_sha256") or parent_cp_freeze.get("stream_parent_freeze_sha256")
    if not isinstance(cp_stream_sha, str) or not cp_stream_sha:
        raise ValueError("Parent CP missing explicit stream_parent_freeze_sha256")
    if (
        cp_cfg.get("stream_parent_freeze_sha256")
        and parent_cp_freeze.get("stream_parent_freeze_sha256")
        and cp_cfg["stream_parent_freeze_sha256"] != parent_cp_freeze["stream_parent_freeze_sha256"]
    ):
        raise ValueError("Parent CP protocol and FINAL_FREEZE stream_parent_freeze_sha256 mismatch")
    exp_stream_freeze_sha = cfg.get("stream_parent_freeze_sha256") or cp_stream_sha
    if not isinstance(exp_stream_freeze_sha, str) or exp_stream_freeze_sha != cp_stream_sha:
        raise ValueError("stream_parent_freeze_sha256 conflicts with parent CP stream_parent_freeze_sha256")

    stream_mc_freeze, mc_cfg = _verify_freeze_protocol(stream_mc_dir, exp_stream_freeze_sha, "Stream parent MCV2")
    if not mc_cfg.get("parent_results"):
        raise ValueError("Stream parent MCV2 protocol missing parent_results")
    return parent_cp_dir, parent_cp_freeze, parent_cp_freeze_sha, stream_mc_dir, stream_mc_freeze, exp_stream_freeze_sha


_BASE.verify_parent_and_stream_bindings = verify_parent_and_stream_bindings


def _resolve_refined_and_control_ids(cfg: dict[str, Any]) -> tuple[list[int], list[int]]:
    br = cfg.get("budget_reservation") if isinstance(cfg.get("budget_reservation"), dict) else {}
    raw_ref = cfg.get("refined_recipe_ids", br.get("refined_recipe_ids", list(DEFAULT_REFINED_RECIPE_IDS)))
    if not isinstance(raw_ref, list) or [_strict_int(x, "refined_recipe_ids") for x in raw_ref] != list(DEFAULT_REFINED_RECIPE_IDS):
        raise ValueError(f"refined_recipe_ids must equal {list(DEFAULT_REFINED_RECIPE_IDS)}")
    raw_ctrl = cfg.get("unchanged_control_recipe_ids", br.get("unchanged_control_recipe_ids", list(DEFAULT_UNCHANGED_RECIPE_IDS)))
    if not isinstance(raw_ctrl, list) or [_strict_int(x, "unchanged_control_recipe_ids") for x in raw_ctrl] != list(DEFAULT_UNCHANGED_RECIPE_IDS):
        raise ValueError(f"unchanged_control_recipe_ids must equal {list(DEFAULT_UNCHANGED_RECIPE_IDS)}")
    return [int(x) for x in raw_ref], [int(x) for x in raw_ctrl]


def verify_budget_and_recipes(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    if _strict_int(cfg.get("max_candidates"), "max_candidates") != 24 or _strict_int(cfg.get("max_cpu_seconds"), "max_cpu_seconds") != 14400:
        raise ValueError("Authorized 24-candidate / 14400-CPU-second budget differs")

    walls = (
        _strict_int(cfg.get("history_wall_seconds", 600), "history_wall_seconds"),
        _strict_int(cfg.get("evaluation_wall_seconds", 120), "evaluation_wall_seconds"),
        _strict_int(cfg.get("freeze_wall_seconds", 60), "freeze_wall_seconds"),
        _strict_int(cfg.get("aggregate_wall_seconds", 1200), "aggregate_wall_seconds"),
        _strict_int(cfg.get("independent_audit_wall_seconds", 300), "independent_audit_wall_seconds"),
        _strict_int(cfg.get("maximum_science_parallel_jobs", 15), "maximum_science_parallel_jobs"),
        _strict_int(cfg.get("per_job_ncpus", 1), "per_job_ncpus"),
        _strict_int(cfg.get("aggregate_mem_gb", 96), "aggregate_mem_gb"),
    )
    reserve_wall = _strict_int(cfg.get("local_retry_reserve_seconds", 2040), "local_retry_reserve_seconds")
    prior_cpu = _strict_int(cfg.get("prior_accounted_cpu_seconds", 0), "prior_accounted_cpu_seconds")
    if walls != (600, 120, 60, 1200, 300, 15, 1, 96) or prior_cpu < 0 or reserve_wall < 0 or reserve_wall + prior_cpu != 2040:
        raise ValueError("Protocol resource walls or job/thread/memory limits differ from authorized refinement spec")

    _resolve_refined_and_control_ids(cfg)
    if "budget_reservation" in cfg:
        br = cfg["budget_reservation"]
        if (
            not isinstance(br, dict)
            or _strict_int(br.get("new_candidates"), "budget_reservation.new_candidates") != 24
            or _strict_int(br.get("cpu_seconds"), "budget_reservation.cpu_seconds") != 14400
            or _strict_int(br.get("total_reserved_candidates"), "budget_reservation.total_reserved_candidates") != 1550
            or _strict_int(br.get("total_accounted_plus_open_reservations_cpu"), "budget_reservation.total_accounted_plus_open_reservations_cpu") != 65808
            or _strict_int(br.get("global_cpu_limit_unchanged"), "budget_reservation.global_cpu_limit_unchanged") != 86400
        ):
            raise ValueError("Protocol budget_reservation settlement values differ from authorized 65808/86400/1550")

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
    return [dict(id=int(r["id"]), groups=int(r["groups"]), relief=float(r["relief"]), cap_mode=str(r["cap_mode"])) for r in recipes]


def load_verified_parent_cp_initializer(
    *, parent_cp_dir: Path, parent_cp_freeze: dict[str, Any], phase: str, seed: int, arm: str,
    recipe: dict[str, Any], oof_bank: dict[str, Any], episode_start: int,
    source_manifest_sha256: str, parent_profile_sha256: str,
) -> tuple[dict[str, Any], str, str]:
    rid = int(recipe["id"])
    rel = initializer_relpath(phase, arm, seed, rid)
    rel_key = str(rel).replace("\\", "/")
    all_inits = parent_cp_freeze.get("all_initializers") or {}
    if rel_key not in all_inits:
        raise ValueError(f"Missing parent initializer {rel_key} in parent CP FINAL_FREEZE.all_initializers")
    exp_sha = str(all_inits[rel_key])
    full_path = Path(parent_cp_dir) / rel
    if not full_path.exists() or sha(full_path) != exp_sha:
        raise ValueError(f"Parent initializer {rel_key} missing or SHA-256 mismatch against parent FINAL_FREEZE")
    parent_rec = json.loads(full_path.read_text(encoding="utf-8"))

    a_oof = np.asarray(oof_bank["anchors"], dtype=np.int64)
    m_oof = np.asarray(oof_bank["mask"], dtype=bool)
    ref_oof = np.asarray(oof_bank["reference"], dtype=np.float64)
    if a_oof.ndim != 1 or a_oof.size == 0 or np.any(np.diff(a_oof) <= 0):
        raise ValueError(f"OOF fit anchors for {phase} must be 1D strictly increasing")
    last_release = int(a_oof[-1]) + 7
    if last_release >= int(episode_start):
        raise ValueError("OOF fit labels are not strictly mature before phase start")
    g, d, mode = int(recipe["groups"]), float(recipe["relief"]), str(recipe["cap_mode"])
    expected_cuts = _BASE.fit_context_cuts(ref_oof, g)
    oof_phases = list(oof_bank["metadata"].get("phases") or [oof_bank["metadata"].get("phase")])

    if (
        parent_rec.get("phase") != str(phase)
        or int(parent_rec.get("seed", -1)) != int(seed)
        or parent_rec.get("arm") != str(arm)
        or int(parent_rec.get("id", -1)) != rid
        or int(parent_rec.get("groups", -1)) != g
        or not _exact_value_match(parent_rec.get("relief"), d)
        or parent_rec.get("cap_mode") != mode
        or bool(parent_rec.get("numerical_fitted")) is not True
        or list(parent_rec.get("cuts", [])) != expected_cuts
        or list(parent_rec.get("fit_window", [])) != [int(a_oof[0]), int(a_oof[-1]) + 1]
        or int(parent_rec.get("fit_anchor_start", -1)) != int(a_oof[0])
        or int(parent_rec.get("fit_anchor_end", -1)) != int(a_oof[-1])
        or int(parent_rec.get("fit_issue_count", -1)) != int(a_oof.size)
        or int(parent_rec.get("valid_fit_cells", -1)) != int(m_oof.sum())
        or int(parent_rec.get("episode_start", -1)) != int(episode_start)
        or int(parent_rec.get("last_label_release", -1)) != int(last_release)
        or parent_rec.get("source_manifest_sha256") != str(source_manifest_sha256)
        or parent_rec.get("parent_profile_sha256") != str(parent_profile_sha256)
        or list(parent_rec.get("oof_source_phases", [])) != oof_phases
        or parent_rec.get("oof_raw_actions_sha256") != oof_bank["metadata"].get("raw_actions_sha256")
    ):
        raise ValueError(f"Parent initializer {rel_key} metadata/window/binding mismatch")

    w_arr = np.asarray(parent_rec.get("weights"), dtype=np.float64)
    w_canon = np.asarray(parent_rec.get("canonical_initial"), dtype=np.float64)
    if (
        w_arr.shape != (g, 25) or w_canon.shape != (g, 25) or not np.array_equal(w_arr, w_canon)
        or not np.isfinite(w_arr).all() or np.any(w_arr < 0.0) or not np.allclose(w_arr.sum(axis=1), 1.0, atol=1e-12, rtol=0.0)
    ):
        raise ValueError(f"Parent initializer {rel_key} weights invalid on ({g}, 25) simplex")
    return parent_rec, exp_sha, rel_key


def _make_initializer_hook(
    *, parent_cp_dir: Path, parent_cp_freeze: dict[str, Any], refined_ids: set[int],
    orig_fit_oof: Any = _ORIG_BASE_FIT_OOF_INITIALIZER, kernel_fn: Any = None,
):
    active_kernel = kernel_mod.fit_conditional_pool if kernel_fn is None else kernel_fn

    def hooked_fit_oof_conditional_pool_initializer(
        *, phase: str, seed: int, arm: str, recipe: dict[str, Any], oof_bank: dict[str, Any],
        b_oof: np.ndarray, episode_start: int, source_manifest_sha256: str, parent_profile_sha256: str,
        time_limit: float = 8.0, max_iter: int = 1200, tol: float = 1e-7,
    ) -> dict[str, Any]:
        parent_rec, parent_sha, parent_rel = load_verified_parent_cp_initializer(
            parent_cp_dir=parent_cp_dir, parent_cp_freeze=parent_cp_freeze, phase=phase, seed=seed,
            arm=arm, recipe=recipe, oof_bank=oof_bank, episode_start=episode_start,
            source_manifest_sha256=source_manifest_sha256, parent_profile_sha256=parent_profile_sha256,
        )
        rid = int(recipe["id"])
        is_refined = rid in refined_ids
        parent_weights = copy.deepcopy(parent_rec["weights"])
        parent_gap = float(parent_rec["gap"]) if parent_rec.get("gap") is not None else None
        parent_obj = float(parent_rec["objective"]) if parent_rec.get("objective") is not None else None
        parent_status = str(parent_rec.get("status"))

        def injected_backend(x, b, y, mask, anchors, reference, *, groups=3, relief=0.0, cap_mode="COST", time_limit=8.0, max_iter=1200, tol=1e-7, **kwargs):
            if not is_refined:
                return copy.deepcopy(parent_rec)
            return active_kernel(
                x, b, y, mask, anchors, reference,
                groups=groups, relief=relief, cap_mode=cap_mode,
                time_limit=REFINEMENT_TIME_LIMIT, time_budget_ceiling=REFINEMENT_TIME_BUDGET_CEILING,
                warm_start_weights=np.asarray(parent_weights, dtype=np.float64).copy(),
                max_iter=int(max_iter), tol=float(tol), **kwargs,
            )

        prev_fit = _BASE.fit_conditional_pool
        _BASE.fit_conditional_pool = injected_backend
        try:
            rec = orig_fit_oof(
                phase=phase, seed=seed, arm=arm, recipe=recipe, oof_bank=oof_bank, b_oof=b_oof,
                episode_start=episode_start, source_manifest_sha256=source_manifest_sha256,
                parent_profile_sha256=parent_profile_sha256, time_limit=time_limit, max_iter=max_iter, tol=tol,
            )
        finally:
            _BASE.fit_conditional_pool = prev_fit

        if not is_refined:
            if rec["weights"] != parent_weights or rec["canonical_initial"] != parent_weights:
                raise ValueError(f"Unchanged control recipe {rid} weights mutated from parent")
        elif (
            parent_obj is not None and bool(parent_rec.get("actual_feasible", True))
            and rec.get("numerical_failure") is None
            and not str(rec.get("status", "")).startswith(("INITIALIZER_ERROR", "NUMERICAL_FAILURE", "BOUND_CONTRADICTION"))
        ):
            if float(rec["objective"]) > parent_obj + 1e-12 * max(1.0, abs(parent_obj)):
                raise ValueError(f"Refined recipe {rid} objective {rec['objective']} exceeded feasible parent incumbent {parent_obj}")

        rec.update(
            newly_solved=bool(is_refined), reused_from_parent=bool(not is_refined),
            parent_initializer_path=parent_rel, parent_initializer_sha256=parent_sha,
            parent_gap=parent_gap, parent_objective=parent_obj, parent_status=parent_status,
        )
        return rec

    return hooked_fit_oof_conditional_pool_initializer


def build_extended_family(
    parent_span3: dict[str, Any], recipes: list[dict[str, Any]], parent_cp_freeze: dict[str, Any] | None = None,
    *, expected_parent_policies: int = 1112, expected_parent_comparisons: int = 4599,
    refined_recipe_ids: list[int] | tuple[int, ...] = DEFAULT_REFINED_RECIPE_IDS,
) -> tuple[list[str], list[bool], list[tuple[str, str]], list[tuple[str, str]], dict[str, Any]]:
    names, parent_avail, aliases, comparisons, comparator_summary = _ORIG_BASE_BUILD_EXTENDED_FAMILY(
        parent_span3, recipes, parent_cp_freeze,
        expected_parent_policies=int(expected_parent_policies),
        expected_parent_comparisons=int(expected_parent_comparisons),
    )
    refined_set = {int(x) for x in refined_recipe_ids}
    seen, alias_set = set(comparisons), set(aliases)
    direct_pairs: list[tuple[str, str]] = []
    new_aliases: list[tuple[str, str]] = []
    for r in recipes:
        rid = int(r["id"])
        for arm in META_ARMS:
            nr_pol, cp_pol = f"{POLICY_PREFIX}{rid:03d}_{arm}", f"{PARENT_POLICY_PREFIX}{rid:03d}_{arm}"
            if cp_pol not in names:
                raise ValueError(f"Parent family missing expected CP policy {cp_pol!r}")
            pair = (nr_pol, cp_pol)
            if pair in seen:
                raise ValueError(f"Duplicate direct NR vs CP comparison: {pair}")
            comparisons.append(pair)
            seen.add(pair)
            direct_pairs.append(pair)
            if rid not in refined_set and pair not in alias_set:
                aliases.append(pair)
                alias_set.add(pair)
                new_aliases.append(pair)

    assert len(direct_pairs) == 72 and len(new_aliases) == 60
    breakdown = dict(comparator_summary.get("new_comparison_breakdown") or {})
    breakdown["direct_refinement_vs_parent_cp_pairs"] = len(direct_pairs)
    breakdown["total_new_comparisons"] = int(breakdown.get("total_new_comparisons", 492)) + len(direct_pairs)
    comparator_summary = dict(
        comparator_summary, new_comparison_breakdown=breakdown,
        refined_recipe_ids=sorted(refined_set),
        unchanged_control_recipe_ids=[int(r["id"]) for r in recipes if int(r["id"]) not in refined_set],
        parent_alias_count=len(aliases) - len(new_aliases),
        new_unchanged_control_alias_count=len(new_aliases), total_alias_count=len(aliases),
    )
    return names, parent_avail, aliases, comparisons, comparator_summary


def run_history_shard(cfg: dict[str, Any], out: Path, shard: int, *, protocol_path: Path | None = None, deadline: float | None = None, root: Path = ROOT) -> dict[str, Any]:
    out = Path(out)
    refined_ids, _ = _resolve_refined_and_control_ids(cfg)
    parent_cp_dir, parent_cp_freeze, _, _, _, _ = verify_parent_and_stream_bindings(cfg, require_ledger=False)
    _BASE.fit_oof_conditional_pool_initializer = _make_initializer_hook(
        parent_cp_dir=parent_cp_dir, parent_cp_freeze=parent_cp_freeze,
        refined_ids=set(refined_ids), orig_fit_oof=_ORIG_BASE_FIT_OOF_INITIALIZER,
    )
    try:
        shard_receipt = _BASE.run_history_shard(cfg, out, shard, protocol_path=protocol_path, deadline=deadline, root=root)
    finally:
        _BASE.fit_oof_conditional_pool_initializer = _ORIG_BASE_FIT_OOF_INITIALIZER

    seed, arm = shard_assignment(shard)
    shard_dir = out / "shards" / "history" / f"shard_{shard:02d}_{arm}_seed{seed}"
    new_solved = reused_num = 0
    for item in shard_receipt["initializers"]:
        rec_data = json.loads((out / item["path"]).read_text(encoding="utf-8"))
        item["newly_solved"] = bool(rec_data.get("newly_solved", False))
        item["reused_from_parent"] = bool(rec_data.get("reused_from_parent", False))
        item["parent_initializer_sha256"] = rec_data.get("parent_initializer_sha256")
        item["parent_gap"] = rec_data.get("parent_gap")
        if item["numerical_fitted"]:
            new_solved += int(item["newly_solved"])
            reused_num += int(item["reused_from_parent"])

    if new_solved != 8 or reused_num != 40 or shard_receipt["initializers_anchor_declared"] != 24:
        raise ValueError(f"History shard {shard} refinement accounting mismatch: new={new_solved}, reused={reused_num}")
    shard_receipt.update(
        initializers_newly_solved=new_solved, initializers_reused_from_parent=reused_num,
        actual_new_numerical_fits=new_solved, reused_parent_numerical_fits=reused_num,
    )
    save(shard_dir / "receipt.json", shard_receipt)
    return shard_receipt


def run_freeze_stage(cfg: dict[str, Any], out: Path, *, protocol_path: Path | None = None, deadline: float | None = None, root: Path = ROOT) -> dict[str, Any]:
    out = Path(out)
    refined_ids, control_ids = _resolve_refined_and_control_ids(cfg)
    freeze_payload = _BASE.run_freeze_stage(cfg, out, protocol_path=protocol_path, deadline=deadline, root=root)
    total_new = total_reused = 0
    for shard in range(15):
        seed, arm = shard_assignment(shard)
        r_data = json.loads((out / "shards" / "history" / f"shard_{shard:02d}_{arm}_seed{seed}" / "receipt.json").read_text(encoding="utf-8"))
        if (r_data.get("initializers_newly_solved"), r_data.get("initializers_reused_from_parent"), r_data.get("initializers_anchor_declared")) != (8, 40, 24):
            raise ValueError(f"History shard {shard} refinement counts invalid in freeze")
        total_new += int(r_data["initializers_newly_solved"])
        total_reused += int(r_data["initializers_reused_from_parent"])

    if total_new != 120 or total_reused != 600:
        raise ValueError(f"Freeze total new ({total_new}) / reused ({total_reused}) mismatch (expected 120 / 600)")
    freeze_payload.update(
        actual_new_numerical_fits=total_new, reused_parent_numerical_fits=total_reused,
        refined_recipe_ids=refined_ids, unchanged_control_recipe_ids=control_ids,
    )
    save(out / "FINAL_FREEZE.json", freeze_payload)
    freeze_sha = sha(out / "FINAL_FREEZE.json")
    open_data = json.loads((out / "EVALUATION_OPEN.json").read_text(encoding="utf-8"))
    open_data["freeze_sha256"] = freeze_sha
    save(out / "EVALUATION_OPEN.json", open_data)
    stage_state_path = out / "shards" / "freeze" / "state.json"
    if stage_state_path.exists():
        st = json.loads(stage_state_path.read_text(encoding="utf-8"))
        st["freeze_sha256"] = freeze_sha
        save(stage_state_path, st)
    return freeze_payload


def run_evaluate_shard(cfg: dict[str, Any], out: Path, shard: int, *, protocol_path: Path | None = None, deadline: float | None = None, root: Path = ROOT) -> dict[str, Any]:
    return _BASE.run_evaluate_shard(cfg, out, shard, protocol_path=protocol_path, deadline=deadline, root=root)


def run_aggregate_stage(cfg: dict[str, Any], out: Path, *, protocol_path: Path | None = None, deadline: float | None = None, root: Path = ROOT, n_boot_override: int | None = None) -> dict[str, Any]:
    out = Path(out)
    refined_ids, control_ids = _resolve_refined_and_control_ids(cfg)
    cfg_agg = dict(cfg)
    cfg_agg.setdefault("expected_parent_policies", 1112)
    cfg_agg.setdefault("expected_parent_comparisons", 4599)

    def wrapped_build_family(parent_span3, recipes, parent_mp_freeze=None, *, expected_parent_policies=1112, expected_parent_comparisons=4599):
        return build_extended_family(
            parent_span3, recipes, parent_mp_freeze,
            expected_parent_policies=expected_parent_policies,
            expected_parent_comparisons=expected_parent_comparisons,
            refined_recipe_ids=refined_ids,
        )

    def wrapped_infer_campaign(ledger, counts, policy_names, comparisons, *, span, seed=20261022, n_boot=20000, cstar=_BASE.CSTAR, available=None, aliases=()):
        avail = [True] * len(policy_names) if available is None else list(available)
        idx_map = {name: i for i, name in enumerate(policy_names)}
        alias_pairs_str = {(str(l), str(r)) for l, r in aliases}
        for rid in refined_ids:
            for arm in META_ARMS:
                nr_name, cp_name = f"{POLICY_PREFIX}{rid:03d}_{arm}", f"{PARENT_POLICY_PREFIX}{rid:03d}_{arm}"
                if (nr_name, cp_name) in alias_pairs_str or (cp_name, nr_name) in alias_pairs_str:
                    raise ValueError(f"Refined recipe {rid} must never be declared as a frozen alias")
        for rid in control_ids:
            for arm in META_ARMS:
                nr_name, cp_name = f"{POLICY_PREFIX}{rid:03d}_{arm}", f"{PARENT_POLICY_PREFIX}{rid:03d}_{arm}"
                if (nr_name, cp_name) not in alias_pairs_str:
                    raise ValueError(f"Missing unchanged control alias ({nr_name}, {cp_name})")
                li, ri = idx_map[nr_name], idx_map[cp_name]
                if avail[li] and avail[ri] and not np.array_equal(ledger[:, li], ledger[:, ri]):
                    raise ValueError(f"Unchanged control alias ({nr_name}, {cp_name}) 5-fit daily ledger mismatch")
        return _ORIG_BASE_INFER_CAMPAIGN(
            ledger, counts, policy_names, comparisons,
            span=span, seed=seed, n_boot=n_boot, cstar=cstar, available=available, aliases=aliases,
        )

    _BASE.build_extended_family = wrapped_build_family
    _BASE.infer_campaign = wrapped_infer_campaign
    try:
        completion = _BASE.run_aggregate_stage(cfg_agg, out, protocol_path=protocol_path, deadline=deadline, root=root, n_boot_override=n_boot_override)
    finally:
        _BASE.build_extended_family = _ORIG_BASE_BUILD_EXTENDED_FAMILY
        _BASE.infer_campaign = _ORIG_BASE_INFER_CAMPAIGN

    weights_path = out / "all_initializer_weights.json"
    weights_summary = json.loads(weights_path.read_text(encoding="utf-8"))
    new_cnt = reused_cnt = 0
    for rel_key, entry in weights_summary.items():
        init_data = json.loads((out / rel_key).read_text(encoding="utf-8"))
        entry["newly_solved"] = bool(init_data.get("newly_solved", False))
        entry["reused_from_parent"] = bool(init_data.get("reused_from_parent", False))
        entry["parent_initializer_sha256"] = init_data.get("parent_initializer_sha256")
        entry["parent_gap"] = init_data.get("parent_gap")
        entry["parent_objective"] = init_data.get("parent_objective")
        if entry["numerical_fitted"]:
            new_cnt += int(entry["newly_solved"])
            reused_cnt += int(entry["reused_from_parent"])
    if new_cnt != 120 or reused_cnt != 600:
        raise ValueError(f"Aggregate weights summary new ({new_cnt}) / reused ({reused_cnt}) != 120 / 600")
    save(weights_path, weights_summary)

    names_path = out / "all_policy_names.json"
    names_data = json.loads(names_path.read_text(encoding="utf-8"))
    names_data.update(
        parent_alias_count=len(names_data["aliases"]) - 60, new_unchanged_control_alias_count=60,
        total_alias_count=len(names_data["aliases"]), refined_recipe_ids=refined_ids, unchanged_control_recipe_ids=control_ids,
    )
    save(names_path, names_data)

    completion.update(
        actual_new_numerical_fits=120, reused_parent_numerical_fits=600,
        refined_recipe_ids=refined_ids, unchanged_control_recipe_ids=control_ids,
        initializer_filenames_note="Initializer files retain CP{id:03d}.json names inside the new campaign directory via isolated base.initializer_relpath; policy family names use NR{id:03d}_{arm}.",
    )
    save(out / "completion.json", completion)
    return completion


_BASE.verify_budget_and_recipes = verify_budget_and_recipes


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
