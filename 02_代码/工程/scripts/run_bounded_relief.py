"""Distributed multi-stage runner for the 48-program bounded signed-relief campaign."""
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

import numpy as np
import scipy
from threadpoolctl import threadpool_limits

from scripts.run_mixture_closed_loop import (
    ARMS,
    PHASES,
    SEEDS,
    deadline_check,
    save,
    score_actions,
    sha,
    verify_cache,
)
from windfarm_moe.actual_mixture_update import MixtureConfig
from windfarm_moe.autonomous_campaign_inference import CSTAR, THRESHOLDS, infer_campaign
from windfarm_moe.bounded_relief import fit_signed, run_signed, signed_action, signed_experts

RELIEF_GRID = (0.0, 0.01, 0.03, 0.1, 0.3, 1.0)
GOALS = ("COST", "CAP")
MODES = (
    ("FIXED", 0.0, 0.0),
    ("ONLINE_A", 0.03, 1.0),
    ("ONLINE_B", 0.3, 1.0),
    ("ONLINE_C", 0.3, 10.0),
)
PROXIMAL_MODES = (
    ("FIXED", 0.0, 0.0, 0.0),
    ("PROX_A", 0.3, 10.0, 0.001),
    ("PROX_B", 0.3, 10.0, 0.01),
    ("PROX_C", 0.3, 10.0, 0.1),
)
DESIGN_SPECS = {
    "bounded_relief": ("BR", False),
    "proximal_relief": ("PR", True),
}


def build_recipes() -> list[dict]:
    """Deterministic 48-recipe grid: 6 relief d x 2 goal x 4 mode (IDs 0..47)."""
    recipes: list[dict] = []
    for relief in RELIEF_GRID:
        for goal in GOALS:
            for mode, eta, gamma in MODES:
                recipes.append(
                    dict(
                        id=len(recipes),
                        relief=float(relief),
                        goal=goal,
                        mode=mode,
                        config=dict(
                            eta=float(eta),
                            schedule_power=0.5,
                            severity_step=float(gamma),
                            cost_scale=100.0,
                        ),
                    )
                )
    assert len(recipes) == 48
    return recipes


def build_proximal_recipes() -> list[dict]:
    """Deterministic 48-recipe proximal grid: 6 relief d x 2 goal x 4 mode (IDs 0..47)."""
    recipes: list[dict] = []
    for relief in RELIEF_GRID:
        for goal in GOALS:
            for mode, eta, gamma, mu in PROXIMAL_MODES:
                recipes.append(
                    dict(
                        id=len(recipes),
                        relief=float(relief),
                        goal=goal,
                        mode=mode,
                        config=dict(
                            eta=float(eta),
                            schedule_power=0.5,
                            severity_step=float(gamma),
                            cost_scale=100.0,
                            proximity_strength=float(mu),
                        ),
                    )
                )
    assert len(recipes) == 48
    return recipes


def get_design(cfg: dict) -> str:
    design = cfg.get("design", "bounded_relief")
    if design not in DESIGN_SPECS:
        raise ValueError(f"Unsupported campaign design: {design!r}")
    return str(design)


def policy_prefix_for_design(design: str) -> str:
    if design not in DESIGN_SPECS:
        raise ValueError(f"Unsupported campaign design: {design!r}")
    return DESIGN_SPECS[design][0]


def relief_tag(relief: float) -> str:
    return f"d{float(relief):.2f}".replace(".", "p")


def initializer_relpath(phase: str, arm: str, seed: int, goal: str, relief: float) -> Path:
    return Path("initializers") / phase / f"{arm}_seed{seed}" / f"{goal}_{relief_tag(relief)}.json"


def shard_assignment(shard: int) -> tuple[int, str]:
    if isinstance(shard, (bool, np.bool_)) or not isinstance(shard, int) or not 0 <= shard < 10:
        raise ValueError("Shard index must be an integer in 0..9")
    return 201 + shard // 2, ARMS[shard % 2]


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


def verify_budget_and_recipes(cfg: dict) -> list[dict]:
    if cfg.get("max_candidates") != 48 or cfg.get("max_cpu_seconds") != 14400:
        raise ValueError("Authorized 48-candidate / 14400-CPU-second budget differs")
    design = get_design(cfg)
    expected = build_proximal_recipes() if design == "proximal_relief" else build_recipes()
    recipes = cfg.get("recipes")
    if not isinstance(recipes, list) or len(recipes) != 48:
        raise ValueError("Protocol must declare exactly 48 recipes")
    for idx, (rec, exp) in enumerate(zip(recipes, expected)):
        if (
            rec.get("id") != idx
            or float(rec.get("relief", -1.0)) != exp["relief"]
            or rec.get("goal") != exp["goal"]
            or rec.get("mode") != exp["mode"]
            or dict(rec.get("config", {})) != exp["config"]
        ):
            raise ValueError(f"Recipe {idx} does not match deterministic 48-recipe specification")
    return recipes


def load_verified_parent_freeze(cfg: dict) -> tuple[dict, str, Path]:
    if "parent_results" not in cfg:
        raise ValueError("Protocol missing parent_results for parent initializer reuse")
    exp_freeze_sha = cfg.get("parent_freeze_sha256")
    if not isinstance(exp_freeze_sha, str) or not exp_freeze_sha:
        raise ValueError("Protocol missing parent_freeze_sha256 for parent initializer reuse")
    parent_dir = Path(cfg["parent_results"])
    freeze_path = parent_dir / "FINAL_FREEZE.json"
    if not freeze_path.exists():
        raise ValueError(f"Parent FINAL_FREEZE.json missing: {freeze_path}")
    actual_sha = sha(freeze_path)
    if actual_sha != exp_freeze_sha:
        raise ValueError(
            f"Parent FINAL_FREEZE.json sha256 mismatch: {actual_sha} != {exp_freeze_sha}"
        )
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    all_inits = freeze.get("all_initializers")
    if not isinstance(all_inits, dict) or len(all_inits) != 360:
        raise ValueError("Parent FINAL_FREEZE.json must contain 360 all_initializers entries")
    return freeze, actual_sha, parent_dir


def load_verified_parent_profile(cfg: dict, kind: str, seed: int) -> tuple[np.ndarray, str, Path]:
    profiles = cfg.get("parent_profiles") or {}
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
        started_utc=datetime.now(timezone.utc).isoformat(),
        clock="source_issue+7<decision_issue",
        independent_confirmation=False,
    )


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
    x = np.load(cache / f"{arm}_seed{seed}.npy", mmap_mode="r")
    if b_full.shape != y.shape:
        raise ValueError(f"Parent profile shape {b_full.shape} differs from target shape {y.shape}")

    begin, end, _ = PHASES[phase]
    use = (a >= begin) & (a < end)
    aa = a[use]
    yy = y[use]
    mm = m[use]
    bb = np.asarray(b_full[use], dtype=np.float64)
    xx = np.asarray(x[use], dtype=np.float64)

    expected_len = cfg.get("expected_evaluation_anchors", 5033)
    expected_valid = cfg.get("expected_evaluation_valid_cells", 672939)
    if phase == "evaluate" and (len(aa) != expected_len or int(mm.sum()) != expected_valid):
        raise ValueError("Evaluation population differs")

    destination = out / "instances" / phase / f"{arm}_seed{seed}"
    destination.mkdir(parents=True, exist_ok=False)

    status: dict[str, str] = {}
    point: dict[str, list[float]] = {}
    ledgers: dict[int, np.ndarray] = {}
    hashes: dict[str, str] = {}
    metadata: dict[str, dict] = {}
    errors: dict[str, dict] = {}

    def record(recipe: dict, actions: np.ndarray, ledger: np.ndarray | None = None, info: dict | None = None) -> None:
        rid = int(recipe["id"])
        key = str(rid)
        if ledger is None:
            ledger, counts_local, days_local = score_actions(actions, yy, mm, aa)
        else:
            days_local = np.unique(aa // 144)
            counts_local = np.asarray([mm[aa // 144 == d].sum() for d in days_local])
            # Verify raw-S scoring consistency
            check_ledger, _, _ = score_actions(actions, yy, mm, aa)
            if not np.allclose(ledger, check_ledger, rtol=0.0, atol=1e-8) or not np.array_equal(
                ledger[:, 3], check_ledger[:, 3]
            ):
                raise ValueError("Candidate ledger diverges from original-S score_actions")
        if ledger.shape != (len(days_local), 4) or not np.isfinite(ledger).all():
            raise ValueError("Invalid candidate ledger")
        ledgers[rid] = ledger
        point[key] = (ledger.sum(axis=0) / counts_local.sum()).tolist()
        status[key] = "COMPLETED"
        metadata[key] = info or {}
        hashes[key] = hashlib.sha256(np.ascontiguousarray(actions, dtype="<f8").tobytes()).hexdigest()

    def failed(recipe: dict, exc: BaseException) -> None:
        key = str(int(recipe["id"]))
        status[key] = "FAILED_PRESERVED"
        errors[key] = dict(error=repr(exc), traceback=traceback.format_exc())

    for relief in RELIEF_GRID:
        for goal in GOALS:
            group = [
                r
                for r in recipes
                if float(r["relief"]) == float(relief) and r["goal"] == goal
            ]
            if not group:
                continue
            init_path = out / initializer_relpath(phase, arm, seed, goal, relief)
            try:
                init_rec = json.loads(init_path.read_text(encoding="utf-8"))
                w0 = np.asarray(init_rec["canonical_initial"], dtype=np.float64)
                delta = signed_experts(xx, bb, relief=relief)
            except Exception as init_exc:
                for r in group:
                    failed(r, init_exc)
                continue

            fixed_recipes = [r for r in group if r["mode"] == "FIXED"]
            online_recipes = [r for r in group if r["mode"] != "FIXED"]

            static_action: np.ndarray | None = None
            for r in fixed_recipes:
                deadline_check(deadline)
                try:
                    with threadpool_limits(limits=1):
                        act, guard_info = signed_action(bb, delta, w0, relief=relief, return_info=True)
                    static_action = act
                    record(
                        r,
                        actions=act,
                        info=dict(
                            relief=float(relief),
                            goal=goal,
                            mode=r["mode"],
                            initializer_status=init_rec["status"],
                            initializer_optimal=bool(init_rec["optimal"]),
                            repaired_to_anchor=bool(init_rec.get("repaired_to_anchor", False)),
                            boundary_guard_count=int(guard_info["boundary_guard_count"]),
                            max_boundary_violation=float(guard_info["max_boundary_violation"]),
                            parent_profile_sha256=profile_sha,
                        ),
                    )
                except Exception as exc:
                    failed(r, exc)

            if static_action is None:
                try:
                    with threadpool_limits(limits=1):
                        static_action = signed_action(bb, delta, w0, relief=relief)
                except Exception:
                    static_action = None

            if online_recipes:
                configs = [MixtureConfig(**r["config"]) for r in online_recipes]
                try:
                    deadline_check(deadline)
                    with threadpool_limits(limits=1):
                        res = run_signed(
                            delta,
                            bb,
                            yy,
                            mm,
                            aa,
                            configs,
                            w0,
                            relief=relief,
                            score=True,
                            return_actions=True,
                        )
                    if static_action is None:
                        raise ValueError("Static action unavailable for warm-start equality check")
                    n_pre = min(8, len(aa))
                    expected_pre = np.broadcast_to(static_action[:n_pre], (len(online_recipes), n_pre, bb.shape[1]))
                    if not np.array_equal(res["actions"][:, :n_pre], expected_pre):
                        raise ValueError("Online signed-relief update does not share exact first 8 actions with FIXED")
                    for idx, r in enumerate(online_recipes):
                        rec_info = dict(
                            relief=float(relief),
                            goal=goal,
                            mode=r["mode"],
                            final_weights=res["metadata"]["final_weights"][idx],
                            final_lambda_u=res["metadata"]["final_lambda_u"][idx],
                            maximum_lambda_u=res["metadata"]["maximum_lambda_u"][idx],
                            boundary_guard_count=int(res["metadata"]["boundary_guard_counts"][idx]),
                            max_boundary_violation=float(res["metadata"]["max_boundary_violation"]),
                            feedback_updates=int(res["metadata"]["feedback_updates"]),
                            initializer_status=init_rec["status"],
                            initializer_optimal=bool(init_rec["optimal"]),
                            repaired_to_anchor=bool(init_rec.get("repaired_to_anchor", False)),
                            parent_profile_sha256=profile_sha,
                            feedback_rule="source_anchor+7<decision_anchor",
                        )
                        if "proximity_strength" in r["config"]:
                            rec_info["proximity_strength"] = float(r["config"]["proximity_strength"])
                        record(
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
                                    delta,
                                    bb,
                                    yy,
                                    mm,
                                    aa,
                                    [MixtureConfig(**r["config"])],
                                    w0,
                                    relief=relief,
                                    score=True,
                                    return_actions=True,
                                )
                            if static_action is None:
                                raise ValueError("Static action unavailable for warm-start equality check")
                            n_pre = min(8, len(aa))
                            if not np.array_equal(single["actions"][0, :n_pre], static_action[:n_pre]):
                                raise ValueError("Online signed-relief update does not share exact first 8 actions with FIXED")
                            single_info = dict(
                                relief=float(relief),
                                goal=goal,
                                mode=r["mode"],
                                final_weights=single["metadata"]["final_weights"][0],
                                final_lambda_u=single["metadata"]["final_lambda_u"][0],
                                maximum_lambda_u=single["metadata"]["maximum_lambda_u"][0],
                                boundary_guard_count=int(single["metadata"]["boundary_guard_counts"][0]),
                                max_boundary_violation=float(single["metadata"]["max_boundary_violation"]),
                                feedback_updates=int(single["metadata"]["feedback_updates"]),
                                initializer_status=init_rec["status"],
                                initializer_optimal=bool(init_rec["optimal"]),
                                repaired_to_anchor=bool(init_rec.get("repaired_to_anchor", False)),
                                parent_profile_sha256=profile_sha,
                                feedback_rule="source_anchor+7<decision_anchor",
                            )
                            if "proximity_strength" in r["config"]:
                                single_info["proximity_strength"] = float(r["config"]["proximity_strength"])
                            record(
                                r,
                                actions=single["actions"][0],
                                ledger=single["ledger"][0],
                                info=single_info,
                            )
                        except Exception as exc:
                            failed(r, exc)

    ref, counts, days = score_actions(xx[:, :, 0], yy, mm, aa)
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


def verify_protocol_cfg(cfg: dict, protocol_path: Path | None) -> None:
    if protocol_path is not None and Path(protocol_path).exists():
        original = json.loads(Path(protocol_path).read_text(encoding="utf-8"))
        if cfg != original:
            raise ValueError("Supplied cfg differs from parsed original protocol")


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
    if deadline is None:
        deadline = start + float(cfg.get("shard_wall_seconds", 600)) - 30.0
    seed, arm = shard_assignment(shard)
    shard_dir = out / "shards" / "history" / f"shard_{shard:02d}_{arm}_seed{seed}"
    shard_dir.mkdir(parents=True, exist_ok=False)

    state = _state_envelope("history", shard=shard, seed=seed, arm=arm)
    save(shard_dir / "state.json", state)

    try:
        deadline_check(deadline)
        verify_protocol_cfg(cfg, protocol_path)
        recipes = verify_budget_and_recipes(cfg)
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

        x_mmap = np.load(hist_cache / f"{arm}_seed{seed}.npy", mmap_mode="r")
        init_records: list[dict] = []
        reuse_parent_inits = bool(cfg.get("reuse_parent_initializers", False))
        parent_freeze = None
        parent_freeze_sha = None
        parent_dir = None
        if reuse_parent_inits:
            parent_freeze, parent_freeze_sha, parent_dir = load_verified_parent_freeze(cfg)
            parent_all_inits = parent_freeze["all_initializers"]

        for phase in ("inner", "outer", "evaluate"):
            deadline_check(deadline)
            begin, end, cut = PHASES[phase]
            use = (a >= 27648) & (a < cut)
            if not np.any(use) or len(a[use]) != cut - 27648 or int(a[use].max()) + 7 >= begin:
                raise ValueError("Warm-start labels are not strictly mature")
            valid_mask = m[use]
            expected_last_release = int(a[use].max()) + 7
            expected_valid_cells = int(valid_mask.sum())
            expected_n_experts = int(x_mmap.shape[-1] + 1)

            if reuse_parent_inits:
                assert parent_dir is not None
                for relief in RELIEF_GRID:
                    for goal in GOALS:
                        deadline_check(deadline)
                        rel_init = initializer_relpath(phase, arm, seed, goal, relief)
                        rel_key = str(rel_init).replace("\\", "/")
                        exp_init_sha = parent_all_inits.get(rel_key)
                        if not isinstance(exp_init_sha, str) or not exp_init_sha:
                            raise ValueError(f"Parent FINAL_FREEZE.json missing initializer entry: {rel_key}")
                        src_init_path = parent_dir / rel_init
                        if not src_init_path.exists():
                            raise ValueError(f"Parent initializer file missing: {src_init_path}")
                        src_sha = sha(src_init_path)
                        if src_sha != exp_init_sha:
                            raise ValueError(
                                f"Parent initializer {rel_key} sha256 mismatch against parent FINAL_FREEZE.json: {src_sha} != {exp_init_sha}"
                            )
                        record = json.loads(src_init_path.read_text(encoding="utf-8"))
                        if (
                            record.get("phase") != phase
                            or int(record.get("seed", -1)) != seed
                            or record.get("arm") != arm
                            or float(record.get("relief", -1.0)) != float(relief)
                            or record.get("goal") != goal
                            or list(record.get("fit_window", [])) != [27648, int(cut)]
                            or int(record.get("episode_start", -1)) != int(begin)
                            or int(record.get("last_label_release", -1)) != expected_last_release
                            or int(record.get("last_label_release", begin)) >= int(begin)
                            or int(record.get("valid_fit_cells", -1)) != expected_valid_cells
                            or int(record.get("n_experts", -1)) != expected_n_experts
                            or record.get("source_manifest_sha256") != cfg["historical_manifest_sha256"]
                            or record.get("parent_profile_sha256") != profile_sha
                        ):
                            raise ValueError(f"Parent initializer metadata binding mismatch for {rel_key}")
                        w_canon = np.asarray(record.get("canonical_initial", []), dtype=np.float64)
                        if (
                            w_canon.shape != (expected_n_experts,)
                            or not np.isfinite(w_canon).all()
                            or np.any(w_canon < 0.0)
                            or not np.isclose(w_canon.sum(), 1.0, atol=1e-12, rtol=0.0)
                        ):
                            raise ValueError(f"Parent initializer canonical_initial invalid for {rel_key}")
                        init_path = out / rel_init
                        init_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(src_init_path, init_path)
                        copied_sha = sha(init_path)
                        if copied_sha != exp_init_sha:
                            raise ValueError(f"Copied initializer sha256 mismatch for {rel_key}")
                        init_records.append(
                            dict(
                                phase=phase,
                                seed=seed,
                                arm=arm,
                                goal=goal,
                                relief=float(relief),
                                path=rel_key,
                                sha256=copied_sha,
                                status=record["status"],
                                optimal=bool(record["optimal"]),
                                reused_from_parent=True,
                            )
                        )
            else:
                x_fit = np.asarray(x_mmap[use][valid_mask], dtype=np.float64)
                b_fit = np.asarray(b_hist[use][valid_mask], dtype=np.float64)
                y_fit = np.asarray(y[use][valid_mask], dtype=np.float64)

                for relief in RELIEF_GRID:
                    for goal in GOALS:
                        deadline_check(deadline)
                        fit_start = time.monotonic()
                        try:
                            with threadpool_limits(limits=1):
                                record = fit_signed(
                                    x_fit,
                                    b_fit,
                                    y_fit,
                                    relief=relief,
                                    goal=goal,
                                    time_limit=float(cfg.get("fit_time_limit_seconds", 10.0)),
                                )
                        except Exception as exc:
                            k = x_fit.shape[-1] + 1
                            w_fb = np.zeros(k, dtype=np.float64)
                            w_fb[0] = 1.0
                            u_fb = float(np.maximum(y_fit - b_fit, 0.0).mean())
                            c_fb = float((b_fit + 10.0 * np.maximum(y_fit - b_fit, 0.0)).mean() / 6.0)
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
                                actual_affine_feasible=True,
                                repaired_to_anchor=False,
                                repair_alpha=0.0,
                                boundary_guard_count=0,
                                max_boundary_violation=0.0,
                                relief=float(relief),
                                goal=goal,
                                support_smoothing=0.0,
                                error=repr(exc),
                                traceback=traceback.format_exc(),
                            )
                        record.update(
                            phase=phase,
                            seed=seed,
                            arm=arm,
                            relief=float(relief),
                            goal=goal,
                            fit_window=[27648, int(cut)],
                            episode_start=int(begin),
                            last_label_release=expected_last_release,
                            valid_fit_cells=expected_valid_cells,
                            n_experts=expected_n_experts,
                            source_manifest_sha256=cfg["historical_manifest_sha256"],
                            parent_profile_sha256=profile_sha,
                            elapsed_seconds=float(time.monotonic() - fit_start),
                        )
                        rel_init = initializer_relpath(phase, arm, seed, goal, relief)
                        init_path = out / rel_init
                        save(init_path, record)
                        init_records.append(
                            dict(
                                phase=phase,
                                seed=seed,
                                arm=arm,
                                goal=goal,
                                relief=float(relief),
                                path=str(rel_init).replace("\\", "/"),
                                sha256=sha(init_path),
                                status=record["status"],
                                optimal=bool(record["optimal"]),
                            )
                        )

        assert len(init_records) == 36
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
            initializers_prepared=len(init_records),
            initializers_fitted=(0 if reuse_parent_inits else len(init_records)),
            initializers_reused_from_parent=reuse_parent_inits,
            parent_freeze_sha256=parent_freeze_sha,
            initializers=init_records,
            phase_summaries=phase_summaries,
            evaluation_cache_read=False,
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
    points = np.full((len(recipes), len(SEEDS), len(ARMS), 4), np.nan, dtype=np.float64)
    ledgers: dict[tuple[int, str], np.ndarray] = {}
    for si, seed in enumerate(SEEDS):
        for ai, arm in enumerate(ARMS):
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
    for ai, arm in enumerate(ARMS):
        for goal in GOALS:
            pool = [j for j, r in enumerate(recipes) if r["goal"] == goal and complete[j]]
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
                roles[f"{goal}_{arm}"] = dict(
                    minimum_C_id=int(recipes[best_c]["id"]),
                    minimum_maxV_id=int(recipes[best_v]["id"]),
                )
    return dict(
        roles=roles,
        complete_recipe_count=int(complete.sum()),
        all_recipes_retained=True,
        qualification_did_not_filter_instances=True,
        selection_scope="Historical outer only; all 48 recipes still scored in evaluation",
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
    if deadline is None:
        deadline = start + float(cfg.get("freeze_wall_seconds", 60)) - 30.0
    stage_dir.mkdir(parents=True, exist_ok=True)
    state = _state_envelope("freeze")
    save(stage_dir / "state.json", state)

    try:
        deadline_check(deadline)
        verify_protocol_cfg(cfg, protocol_path)
        recipes = verify_budget_and_recipes(cfg)
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
        recorded_initializers: dict[str, str] = {}
        reuse_parent_inits = bool(cfg.get("reuse_parent_initializers", False))
        parent_freeze = None
        parent_freeze_sha = None
        if reuse_parent_inits:
            parent_freeze, parent_freeze_sha, _ = load_verified_parent_freeze(cfg)
        for shard in range(10):
            seed, arm = shard_assignment(shard)
            r_path = out / "shards" / "history" / f"shard_{shard:02d}_{arm}_seed{seed}" / "receipt.json"
            if not r_path.exists():
                raise ValueError(f"Missing history shard receipt: {r_path}")
            r_data = json.loads(r_path.read_text(encoding="utf-8"))
            prepared_count = r_data.get("initializers_prepared", r_data.get("initializers_fitted"))
            if r_data.get("status") != "COMPLETED" or prepared_count != 36:
                raise ValueError(f"History shard {shard} did not complete all 36 initializers")
            if reuse_parent_inits:
                if (
                    r_data.get("initializers_fitted") != 0
                    or not r_data.get("initializers_reused_from_parent")
                    or r_data.get("parent_freeze_sha256") != parent_freeze_sha
                ):
                    raise ValueError(f"History shard {shard} parent initializer reuse binding mismatch")
            elif r_data.get("initializers_fitted") != 36:
                raise ValueError(f"History shard {shard} did not fit all 36 initializers")
            if r_data.get("shard") != shard or r_data.get("seed") != seed or r_data.get("arm") != arm:
                raise ValueError(f"History shard {shard} receipt identity mismatch")
            if r_data.get("protocol_sha256") != protocol_sha:
                raise ValueError(f"History shard {shard} protocol_sha256 differs from current protocol")
            if r_data.get("source_versions") != source_versions:
                raise ValueError(f"History shard {shard} source_versions differ from current source")
            if r_data.get("historical_manifest_sha256") != cfg["historical_manifest_sha256"]:
                raise ValueError(f"History shard {shard} historical_manifest_sha256 differs from current protocol")
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
                    raise ValueError(f"Missing required initializer: {full_init}")
                actual_sha = sha(full_init)
                if actual_sha != rec_sha:
                    raise ValueError(
                        f"Initializer {rel_key} sha256 mismatch against history shard {shard} receipt: {actual_sha} != {rec_sha}"
                    )
                if reuse_parent_inits and parent_freeze is not None:
                    if parent_freeze["all_initializers"].get(rel_key) != actual_sha:
                        raise ValueError(
                            f"Initializer {rel_key} sha256 mismatch against parent FINAL_FREEZE.json"
                        )
                recorded_initializers[rel_key] = rec_sha
            shard_receipts.append(r_data)

        all_initializers: dict[str, str] = {}
        for phase in ("inner", "outer", "evaluate"):
            for seed in SEEDS:
                for arm in ARMS:
                    for relief in RELIEF_GRID:
                        for goal in GOALS:
                            rel = initializer_relpath(phase, arm, seed, goal, relief)
                            rel_key = str(rel).replace("\\", "/")
                            full = out / rel
                            if not full.exists():
                                raise ValueError(f"Missing required initializer: {full}")
                            digest = sha(full)
                            if rel_key not in recorded_initializers or recorded_initializers[rel_key] != digest:
                                raise ValueError(f"Initializer {rel_key} missing or mismatched in history shard receipts")
                            all_initializers[rel_key] = digest
        assert len(all_initializers) == 360

        for phase in ("inner", "outer"):
            points, _ = collect(out, phase, recipes)
            np.save(out / f"{phase}_points.npy", points, allow_pickle=False)
            save(out / f"{phase}_selection.json", history_summary(points, recipes))

        if (out / "FINAL_FREEZE.json").exists() or (out / "EVALUATION_OPEN.json").exists():
            raise FileExistsError("FINAL_FREEZE.json or EVALUATION_OPEN.json already exists")
        freeze_payload = dict(
            time_utc=datetime.now(timezone.utc).isoformat(),
            study_id=cfg.get("study_id", "bounded_relief_20261024_v1"),
            design=get_design(cfg),
            source_commit=os.environ.get("CAMPAIGN_RELEASE", "LOCAL_SYNTHETIC"),
            protocol_sha256=protocol_sha,
            source_versions=source_versions,
            historical_manifest_sha256=cfg["historical_manifest_sha256"],
            evaluation_manifest_sha256=cfg["evaluation_manifest_sha256"],
            recipes=recipes,
            historical_roles=json.loads((out / "outer_selection.json").read_text(encoding="utf-8")),
            all_initializers=all_initializers,
            initializers_reused_from_parent=reuse_parent_inits,
            parent_freeze_sha256=parent_freeze_sha,
            history_shard_count=len(shard_receipts),
            selection_scope="Historical outer minimum_C/minimum_maxV per goal per arm; no qualification filter; all 48 evaluated",
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
    if deadline is None:
        deadline = start + float(cfg.get("shard_wall_seconds", 600)) - 30.0
    seed, arm = shard_assignment(shard)
    shard_dir = out / "shards" / "evaluate" / f"shard_{shard:02d}_{arm}_seed{seed}"
    shard_dir.mkdir(parents=True, exist_ok=False)

    state = _state_envelope("evaluate", shard=shard, seed=seed, arm=arm)
    save(shard_dir / "state.json", state)

    try:
        deadline_check(deadline)
        recipes = verify_budget_and_recipes(cfg)
        freeze = verify_freeze_barrier(cfg, out, protocol_path=protocol_path, root=root)
        all_inits = freeze.get("all_initializers") or {}
        for relief in RELIEF_GRID:
            for goal in GOALS:
                rel = str(initializer_relpath("evaluate", arm, seed, goal, relief)).replace("\\", "/")
                full = out / rel
                if rel not in all_inits or not full.exists() or sha(full) != all_inits[rel]:
                    raise ValueError(f"Evaluate initializer missing or modified since freeze: {rel}")

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
    design: str = "bounded_relief",
    expected_parent_policies: int | None = None,
    expected_parent_comparisons: int | None = None,
) -> tuple[list[str], list[bool], list[tuple[str, str]], list[tuple[str, str]]]:
    if design not in DESIGN_SPECS:
        raise ValueError(f"Unsupported campaign design: {design!r}")
    prefix = policy_prefix_for_design(design)
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
        for arm in ARMS:
            names.append(f"{prefix}{rid:03d}_{arm}")

    fixed_lookup = {
        (float(r["relief"]), r["goal"]): int(r["id"])
        for r in recipes
        if r["mode"] == "FIXED"
    }

    relief_idx_map = {float(d): idx for idx, d in enumerate(RELIEF_GRID)}
    goal_idx_map = {g: idx for idx, g in enumerate(GOALS)}

    new_pairs: list[tuple[str, str]] = []
    for r in recipes:
        rid = int(r["id"])
        d_val = float(r["relief"])
        goal = str(r["goal"])
        new_pairs.append((f"{prefix}{rid:03d}_Z", f"{prefix}{rid:03d}_P"))
        for arm in ARMS:
            policy = f"{prefix}{rid:03d}_{arm}"
            for comparator in ("REF", "R0182_P", f"GUARDED_FIXED_{arm}", f"R0186_{arm}"):
                new_pairs.append((policy, comparator))
            if r["mode"] != "FIXED":
                fixed_id = fixed_lookup[(d_val, goal)]
                new_pairs.append((policy, f"{prefix}{fixed_id:03d}_{arm}"))
            if design == "proximal_relief":
                if r["mode"] == "FIXED":
                    old_fixed = f"BR{rid:03d}_{arm}"
                    if old_fixed not in parent_names:
                        raise ValueError(f"Missing parent FIXED control policy {old_fixed}")
                    new_pairs.append((policy, old_fixed))
                else:
                    d_idx = relief_idx_map[d_val]
                    g_idx = goal_idx_map[goal]
                    old_online_c_id = (d_idx * 8 + g_idx * 4) + 3
                    old_online_c = f"BR{old_online_c_id:03d}_{arm}"
                    if old_online_c not in parent_names:
                        raise ValueError(f"Missing parent ONLINE_C comparator policy {old_online_c}")
                    new_pairs.append((policy, old_online_c))

    seen = set(comparisons)
    if len(seen) != len(comparisons):
        raise ValueError("Parent comparisons contain unexpected duplicates")
    for pair in new_pairs:
        if pair not in seen:
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
    if deadline is None:
        deadline = start + float(cfg.get("aggregate_wall_seconds", 1200)) - 30.0
    stage_dir = out / "shards" / "aggregate"
    stage_dir.mkdir(parents=True, exist_ok=True)
    state = _state_envelope("aggregate")
    save(stage_dir / "state.json", state)

    try:
        deadline_check(deadline)
        recipes = verify_budget_and_recipes(cfg)
        freeze = verify_freeze_barrier(cfg, out, protocol_path=protocol_path, root=root)
        freeze_sha = sha(out / "FINAL_FREEZE.json")

        for shard in range(10):
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
        design = get_design(cfg)
        names, parent_avail, aliases, comparisons = build_extended_family(
            parent_span3,
            recipes,
            design=design,
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
            for arm in ARMS:
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
            for arm in ARMS:
                panel = np.stack([eval_ledgers[seed, arm][j] for seed in SEEDS], axis=0)
                all_ledger = np.concatenate([all_ledger, panel[:, None, :, :]], axis=1)
                available.append(bool(np.isfinite(panel).all()))

        new_policy_count = len(recipes) * len(ARMS)
        total_policy_count = parent_policy_count + new_policy_count
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
                for arm in ARMS:
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
                expected=len(recipes) * 10,
            )

        all_complete = all(v["completed"] == len(recipes) * 10 and v["failed"] == 0 for v in phase_counts.values())
        completion = dict(
            status="COMPLETED_ALL_PREDEFINED_INSTANCES" if all_complete else "COMPLETED_WITH_PRESERVED_FAILURES",
            planned_recipes=len(recipes),
            planned_instances_per_phase=len(recipes) * 10,
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
                raise ValueError("--shard 0..9 is required for --stage history")
            run_history_shard(cfg, args.output, args.shard, protocol_path=args.protocol)
        elif args.stage == "freeze":
            run_freeze_stage(cfg, args.output, protocol_path=args.protocol)
        elif args.stage == "evaluate":
            if args.shard is None:
                raise ValueError("--shard 0..9 is required for --stage evaluate")
            run_evaluate_shard(cfg, args.output, args.shard, protocol_path=args.protocol)
        elif args.stage == "aggregate":
            run_aggregate_stage(cfg, args.output, protocol_path=args.protocol)


if __name__ == "__main__":
    main()
