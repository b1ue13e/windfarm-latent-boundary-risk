from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import json
import os
import shutil

import numpy as np
import pandas as pd

from .strict_anchor import strict_anchor_mask_report
from .utils import ensure_dir, load_json, save_json


DEFAULT_SPATIAL_HOLDOUT_SEEDS = (401, 402, 403, 404, 405)
DEFAULT_SPATIAL_HOLDOUT_VARIANTS = ("bal_align_force", "context_align_force", "anchor_only")
SPATIAL_VARIANT_SPECS: dict[str, dict[str, str]] = {
    "bal_align_force": {"label": "MoE + L_bal + L_align + L_force", "mode": "moe_full_no_aux"},
    "context_align_force": {"label": "Context-supervised router", "mode": "moe_context_align"},
    "anchor_only": {"label": "Anchor-only router", "mode": "moe_anchor_only"},
}
REVIEWER_STAT_REQUIRED_FILES = (
    "reviewer_stat_pack_config.json",
    "reviewer_stat_pack_run_table.csv",
    "per_example_manifest.csv",
    "per_example_predictions.csv.gz",
    "paired_effects_raw.csv",
    "paired_effects_summary.csv",
    "efficiency_fairness_table.csv",
    "failure_cases_gate_correct_bad.csv",
    "failure_cases_gate_correct_bad.png",
    "failure_cases_boundary_gate_correct_bad.csv",
    "failure_cases_boundary_gate_correct_bad.png",
    "reviewer_stat_pack_report.md",
)


def _parse_seeds(values: Iterable[int] | str | None) -> list[int]:
    if values is None:
        return [int(seed) for seed in DEFAULT_SPATIAL_HOLDOUT_SEEDS]
    if isinstance(values, str):
        return [int(token.strip()) for token in values.split(",") if token.strip()]
    return [int(seed) for seed in values]


def _parse_variant_keys(values: Iterable[str] | str | None) -> list[str]:
    if values is None:
        return list(DEFAULT_SPATIAL_HOLDOUT_VARIANTS)
    tokens = values.split(",") if isinstance(values, str) else list(values)
    parsed = [str(token).strip() for token in tokens if str(token).strip()]
    unknown = sorted(set(parsed).difference(SPATIAL_VARIANT_SPECS))
    if unknown:
        available = ", ".join(SPATIAL_VARIANT_SPECS)
        raise ValueError(f"Unknown spatial holdout variant(s): {unknown}. Available: {available}")
    return parsed


def _path_status(label: str, path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "label": label,
        "path": str(path),
        "exists": bool(exists),
        "nonempty": bool(exists and path.is_file() and path.stat().st_size > 0),
    }


def _select_spatial_nodes(
    coords: np.ndarray,
    node_ids: np.ndarray,
    strategy: str = "east",
    fraction: float = 0.2,
) -> tuple[np.ndarray, np.ndarray]:
    coords = np.asarray(coords, dtype=np.float64)
    node_ids = np.asarray(node_ids)
    if coords.ndim != 2 or coords.shape[0] == 0:
        raise ValueError("coords.npy must be a non-empty 2D array")
    fraction = float(fraction)
    if not 0.0 < fraction < 1.0:
        raise ValueError("fraction must be between 0 and 1")
    n_nodes = int(coords.shape[0])
    n_holdout = max(1, int(round(n_nodes * fraction)))
    strategy = str(strategy).lower()
    if strategy in {"east", "right", "high_x"}:
        order = np.argsort(coords[:, 0], kind="mergesort")
        indices = order[-n_holdout:]
    elif strategy in {"west", "left", "low_x"}:
        order = np.argsort(coords[:, 0], kind="mergesort")
        indices = order[:n_holdout]
    elif strategy in {"north", "high_y"}:
        order = np.argsort(coords[:, 1], kind="mergesort")
        indices = order[-n_holdout:]
    elif strategy in {"south", "low_y"}:
        order = np.argsort(coords[:, 1], kind="mergesort")
        indices = order[:n_holdout]
    else:
        raise ValueError("strategy must be one of east, west, north, south")
    indices = np.sort(indices.astype(np.int64))
    return indices, node_ids[indices]


def _run_complete_status(run_dir: Path, variant_key: str, seed: int) -> dict[str, Any]:
    summary_path = run_dir / "training_summary.json"
    metrics_path = run_dir / "test_metrics" / "metrics.json"
    summary = load_json(summary_path) if summary_path.exists() else {}
    metrics = load_json(metrics_path) if metrics_path.exists() else {}
    spec = SPATIAL_VARIANT_SPECS[variant_key]
    checks = {
        "summary_exists": summary_path.exists(),
        "metrics_exists": metrics_path.exists(),
        "seed_matches": int(summary.get("seed", -1)) == int(seed) if summary else False,
        "variant_key_matches": str(summary.get("variant_key", "")) == variant_key if summary else False,
        "experiment_group_is_ablation": str(summary.get("experiment_group", "")) == "ablation" if summary else False,
        "model_mode_matches": str(summary.get("model_mode", "")) == spec["mode"] if summary else False,
        "overall_rmse_present": "overall" in metrics and "rmse" in metrics.get("overall", {}),
        "gate_alignment_present": "gate_alignment" in metrics,
    }
    complete = all(checks.values())
    return {
        "variant_key": variant_key,
        "label": spec["label"],
        "mode": spec["mode"],
        "seed": int(seed),
        "run_dir": str(run_dir),
        "complete": bool(complete),
        "checks": checks,
        "overall_rmse": metrics.get("overall", {}).get("rmse"),
        "switch_rmse": metrics.get("switch_window", {}).get("rmse"),
        "nmi": metrics.get("gate_alignment", {}).get("nmi"),
        "ari": metrics.get("gate_alignment", {}).get("ari"),
    }


def _link_or_copy(source: Path, destination: Path) -> None:
    if destination.exists():
        return
    ensure_dir(destination.parent)
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def _mask_for_spatial_holdout(
    base_mask: np.ndarray,
    split_bounds: dict[str, list[int] | tuple[int, int]],
    holdout_indices: np.ndarray,
) -> np.ndarray:
    mask = np.array(base_mask, copy=True)
    n_nodes = mask.shape[1]
    all_indices = np.arange(n_nodes)
    train_indices = np.setdiff1d(all_indices, holdout_indices, assume_unique=False)
    for split, bounds in split_bounds.items():
        start, end = int(bounds[0]), int(bounds[1])
        if split in {"train", "val"}:
            mask[start:end, holdout_indices] = 0
        elif split in {"test", "holdout"}:
            mask[start:end, train_indices] = 0
    return mask


def _spatial_mask_report(cache_dir: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    patch = metadata.get("spatial_holdout_patch", {})
    holdout = np.asarray(patch.get("holdout_node_indices", []), dtype=np.int64)
    split_bounds = metadata.get("split_bounds", {})
    target_path = cache_dir / "target_mask.npy"
    regime_path = cache_dir / "regime_primary_valid.npy"
    if holdout.size == 0:
        return {"can_check": False, "reason": "spatial_holdout_patch.holdout_node_indices is empty"}
    if not target_path.exists() or not regime_path.exists():
        return {"can_check": False, "reason": "target_mask.npy or regime_primary_valid.npy is missing"}
    target = np.load(target_path, mmap_mode="r")
    regime = np.load(regime_path, mmap_mode="r")
    if target.ndim != 2 or regime.shape != target.shape:
        return {"can_check": False, "reason": "target/regime masks must have matching [time, node] shape"}
    all_nodes = np.arange(target.shape[1], dtype=np.int64)
    train_nodes = np.setdiff1d(all_nodes, holdout, assume_unique=False)
    rows: list[dict[str, Any]] = []
    checks: dict[str, bool] = {}
    for split, bounds in split_bounds.items():
        start, end = int(bounds[0]), int(bounds[1])
        train_target_sum = float(np.asarray(target[start:end, train_nodes]).sum()) if train_nodes.size else 0.0
        holdout_target_sum = float(np.asarray(target[start:end, holdout]).sum())
        train_regime_sum = float(np.asarray(regime[start:end, train_nodes]).sum()) if train_nodes.size else 0.0
        holdout_regime_sum = float(np.asarray(regime[start:end, holdout]).sum())
        rows.append(
            {
                "split": split,
                "start": start,
                "end": end,
                "train_node_target_sum": train_target_sum,
                "holdout_node_target_sum": holdout_target_sum,
                "train_node_regime_valid_sum": train_regime_sum,
                "holdout_node_regime_valid_sum": holdout_regime_sum,
            }
        )
        if split in {"train", "val"}:
            checks[f"{split}_holdout_nodes_masked"] = holdout_target_sum == 0.0 and holdout_regime_sum == 0.0
            checks[f"{split}_train_nodes_available"] = train_target_sum > 0.0 and train_regime_sum > 0.0
        elif split in {"test", "holdout"}:
            checks[f"{split}_train_nodes_masked"] = train_target_sum == 0.0 and train_regime_sum == 0.0
            checks[f"{split}_holdout_nodes_available"] = holdout_target_sum > 0.0 and holdout_regime_sum > 0.0
    return {
        "can_check": True,
        "holdout_node_count": int(holdout.size),
        "total_node_count": int(target.shape[1]),
        "holdout_fraction_actual": float(holdout.size / max(target.shape[1], 1)),
        "checks": checks,
        "split_mask_sums": rows,
        "mask_policy_pass": bool(checks) and all(checks.values()),
    }


def build_spatial_holdout_cache(
    source_cache_dir: Path | str,
    output_cache_dir: Path | str,
    strategy: str = "east",
    fraction: float = 0.2,
) -> Path:
    source_cache_dir = Path(source_cache_dir)
    output_cache_dir = ensure_dir(output_cache_dir)
    metadata = load_json(source_cache_dir / "metadata.json")
    if metadata.get("dataset") != "wtb":
        raise ValueError("spatial holdout cache currently supports only WTB")
    coords = np.load(source_cache_dir / "coords.npy")
    node_ids = np.load(source_cache_dir / "node_ids.npy")
    holdout_indices, holdout_node_ids = _select_spatial_nodes(coords, node_ids, strategy=strategy, fraction=fraction)
    split_bounds = metadata.get("split_bounds", {})

    modified_names = {"target_mask.npy", "regime_primary_valid.npy", "regime_aux_valid.npy", "metadata.json"}
    for source in source_cache_dir.iterdir():
        if source.name in modified_names or not source.is_file():
            continue
        _link_or_copy(source, output_cache_dir / source.name)

    for name in ["target_mask.npy", "regime_primary_valid.npy", "regime_aux_valid.npy"]:
        source_path = source_cache_dir / name
        if source_path.exists():
            masked = _mask_for_spatial_holdout(np.load(source_path), split_bounds, holdout_indices)
            np.save(output_cache_dir / name, masked)

    metadata["spatial_holdout_patch"] = {
        "source_cache": str(source_cache_dir),
        "strategy": str(strategy),
        "fraction": float(fraction),
        "holdout_node_indices": holdout_indices.astype(int).tolist(),
        "holdout_node_ids": np.asarray(holdout_node_ids).astype(int).tolist(),
        "policy": "train/val supervision excludes held-out turbines; test/holdout metrics include held-out turbines only",
    }
    save_json(output_cache_dir / "metadata.json", metadata)
    return output_cache_dir


def write_spatial_holdout_protocol(
    output_dir: Path | str,
    source_cache_dir: Path | str = "artifacts/cache_strictmask/wtb_245d",
    output_cache_root: str = "artifacts/cache_strictmask_spatial_east",
    suite_dir: Path | str = "artifacts/spatial_holdout_wtb_east_runs",
    strategy: str = "east",
    fraction: float = 0.2,
    seeds: Iterable[int] | str | None = None,
) -> Path:
    output_dir = ensure_dir(output_dir)
    seeds = _parse_seeds(seeds)
    output_cache_dir = Path(output_cache_root) / "wtb_245d"
    seed_text = ",".join(str(seed) for seed in seeds)
    commands = [
        "python main.py spatial-holdout-cache "
        f"--source-cache-dir {source_cache_dir} --output-cache-root {output_cache_root} "
        f"--strategy {strategy} --fraction {float(fraction):g}",
        "python main.py spatial-holdout-guard "
        f"--protocol-dir {output_dir} --source-cache-dir {source_cache_dir} --output-cache-root {output_cache_root} "
        f"--suite-dir {suite_dir} --strategy {strategy} --fraction {float(fraction):g} "
        f"--seeds {seed_text} --variant-keys bal_align_force,context_align_force,anchor_only "
        f"--output-dir {output_dir / 'guard'}",
        "python main.py paper-batch --dataset wtb --root-dir . "
        f"--cache-root {output_cache_root} --output-dir {suite_dir} "
        "--groups ablation --variant-keys bal_align_force,context_align_force,anchor_only "
        f"--seeds {seed_text} --epochs 20 --batch-size 16 --hidden-dim 64 --skip-visuals",
        "python main.py mechanism-gate --dataset wtb --root-dir . "
        f"--suite-dir {suite_dir} --cache-dir {output_cache_dir} "
        "--output-dir artifacts/spatial_holdout_wtb_east_mechanism_gate "
        '--models "MoE + L_bal + L_align + L_force,Context-supervised router,Anchor-only router" '
        "--variant-keys bal_align_force,context_align_force,anchor_only --experiment-groups ablation --split test",
        "python main.py reviewer-stat-pack --dataset wtb --root-dir . "
        f"--suite-dir {suite_dir} --cache-dir {output_cache_dir} "
        "--output-dir artifacts/spatial_holdout_wtb_east_reviewer_stats "
        '--models "MoE + L_bal + L_align + L_force,Context-supervised router,Anchor-only router" '
        '--reference-model "MoE + L_bal + L_align + L_force" '
        '--baseline-models "Context-supervised router,Anchor-only router" '
        "--bootstrap-samples 1000 --permutation-samples 1000 --max-paired-examples 100000 --top-k-failures 24",
        "python main.py spatial-holdout-evidence-guard "
        f"--protocol-dir {output_dir} --suite-dir {suite_dir} --cache-dir {output_cache_dir} "
        "--mechanism-dir artifacts/spatial_holdout_wtb_east_mechanism_gate "
        "--reviewer-pack-dir artifacts/spatial_holdout_wtb_east_reviewer_stats "
        "--output-dir artifacts/spatial_holdout_evidence_guard_wtb_east "
        "--seeds "
        f"{seed_text} --variant-keys bal_align_force,context_align_force,anchor_only",
    ]
    (output_dir / "spatial_holdout_commands.ps1").write_text("\n".join(commands) + "\n", encoding="utf-8")
    protocol = {
        "status": "protocol_only_not_executed",
        "dataset": "wtb",
        "purpose": "Spatial turbine-group holdout derived from the strict-anchor-mask WTB cache.",
        "claim_supported_after_execution": "cross-turbine routing and forecasting generalization within WTB",
        "claim_not_supported_until_execution": "external wind-farm generalization",
        "source_cache_dir": str(source_cache_dir),
        "output_cache_root": str(output_cache_root),
        "output_cache_dir": str(output_cache_dir),
        "suite_dir": str(suite_dir),
        "strategy": str(strategy),
        "fraction": float(fraction),
        "seeds": seeds,
        "primary_decision_rule": {
            "primary_model": "MoE + L_bal + L_align + L_force",
            "routing_controls": ["Context-supervised router", "Anchor-only router"],
            "primary_metric": "held-out turbine gate-regime NMI/ARI",
            "secondary_metrics": ["held-out turbine overall RMSE", "held-out turbine switch-window RMSE"],
            "no_go_condition": "Do not claim cross-turbine generalization if held-out turbine routing agreement collapses or only anchor-only routing succeeds.",
        },
        "outputs": {
            "commands_ps1": str(output_dir / "spatial_holdout_commands.ps1"),
        },
    }
    save_json(output_dir / "spatial_holdout_protocol.json", protocol)
    pd.DataFrame(
        [
            {
                "strategy": strategy,
                "fraction": float(fraction),
                "source_cache_dir": str(source_cache_dir),
                "output_cache_dir": str(output_cache_dir),
                "suite_dir": str(suite_dir),
                "seeds": ",".join(str(seed) for seed in seeds),
            }
        ]
    ).to_csv(output_dir / "spatial_holdout_plan.csv", index=False)
    lines = [
        "# Spatial turbine-group holdout protocol",
        "",
        "Status: `protocol_only_not_executed`.",
        "",
        "This protocol creates a derived strict-cache WTB setting where a spatial turbine cluster is held out from train/val supervision and used for test metrics.",
        "",
        "## Commands",
        "",
        "```powershell",
        *commands,
        "```",
        "",
    ]
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return output_dir


def run_spatial_holdout_evidence_guard(
    protocol_dir: Path | str,
    output_dir: Path | str,
    suite_dir: Path | str = "artifacts/spatial_holdout_wtb_east_runs",
    cache_dir: Path | str = "artifacts/cache_strictmask_spatial_east/wtb_245d",
    mechanism_dir: Path | str | None = None,
    reviewer_pack_dir: Path | str | None = None,
    seeds: Iterable[int] | str | None = None,
    variant_keys: Iterable[str] | str | None = None,
) -> Path:
    protocol_dir = Path(protocol_dir)
    output_dir = ensure_dir(output_dir)
    suite_dir = Path(suite_dir)
    cache_dir = Path(cache_dir)
    base_dir = protocol_dir.parent
    mechanism_dir = Path(mechanism_dir) if mechanism_dir is not None else base_dir / "mechanism"
    reviewer_pack_dir = Path(reviewer_pack_dir) if reviewer_pack_dir is not None else base_dir / "reviewer"
    seed_list = _parse_seeds(seeds)
    variant_key_list = _parse_variant_keys(variant_keys)

    protocol_path = protocol_dir / "spatial_holdout_protocol.json"
    protocol = load_json(protocol_path) if protocol_path.exists() else {}
    metadata_path = cache_dir / "metadata.json"
    metadata = load_json(metadata_path) if metadata_path.exists() else {}
    anchor_report = strict_anchor_mask_report(cache_dir, metadata) if metadata else {"can_check": False}
    mask_report = _spatial_mask_report(cache_dir, metadata) if metadata else {"can_check": False}
    run_status = [
        _run_complete_status(suite_dir / f"wtb_{variant_key}_seed{seed}", variant_key, seed)
        for variant_key in variant_key_list
        for seed in seed_list
    ]
    expected_runs = int(len(run_status))
    complete_runs = int(sum(1 for row in run_status if row["complete"]))
    missing_runs = expected_runs - complete_runs
    pd.DataFrame(
        [
            {
                "variant_key": row["variant_key"],
                "label": row["label"],
                "mode": row["mode"],
                "seed": row["seed"],
                "run_dir": row["run_dir"],
                "complete": row["complete"],
                "overall_rmse": row["overall_rmse"],
                "switch_rmse": row["switch_rmse"],
                "nmi": row["nmi"],
                "ari": row["ari"],
                **{f"check_{key}": value for key, value in row["checks"].items()},
            }
            for row in run_status
        ]
    ).to_csv(output_dir / "spatial_holdout_evidence_run_status.csv", index=False)

    protocol_outputs = protocol.get("outputs", {}) if protocol else {}
    protocol_commands = Path(str(protocol_outputs.get("commands_ps1", ""))) if protocol_outputs else None
    mechanism_config_path = mechanism_dir / "mechanism_evidence_gate_config.json"
    mechanism_config = load_json(mechanism_config_path) if mechanism_config_path.exists() else {}
    mechanism_gate_status = str(mechanism_config.get("gate_status", "")) if mechanism_config else ""
    mechanism_audited_runs = int(mechanism_config.get("n_audited_runs", 0)) if mechanism_config else 0
    audit_files = [
        _path_status(
            "protocol_commands_ps1",
            protocol_commands if protocol_commands else protocol_dir / "spatial_holdout_commands.ps1",
        ),
        _path_status("mechanism_evidence_gate_config", mechanism_config_path),
        _path_status("mechanism_gate_run_table", mechanism_dir / "mechanism_gate_run_table.csv"),
        _path_status("checkpoint_replay_audit", mechanism_dir / "checkpoint_replay" / "checkpoint_replay_audit.csv"),
        _path_status("checkpoint_replay_summary", mechanism_dir / "checkpoint_replay" / "checkpoint_replay_summary.csv"),
        _path_status(
            "mechanism_intervention_effects",
            mechanism_dir / "mechanism_intervention" / "mechanism_intervention_effects.csv",
        ),
    ]
    for filename in REVIEWER_STAT_REQUIRED_FILES:
        audit_files.append(_path_status(f"reviewer_stat_pack/{filename}", reviewer_pack_dir / filename))
    pd.DataFrame(audit_files).to_csv(output_dir / "spatial_holdout_audit_file_status.csv", index=False)

    routing_controls_included = {"context_align_force", "anchor_only"}.issubset(set(variant_key_list))
    checks = {
        "protocol_json_exists": protocol_path.exists(),
        "protocol_status_is_not_executed": protocol.get("status") == "protocol_only_not_executed",
        "cache_metadata_exists": metadata_path.exists(),
        "cache_has_spatial_holdout_patch": bool(metadata.get("spatial_holdout_patch")) if metadata else False,
        "cache_has_strict_anchor_patch_marker": bool(metadata.get("strict_anchor_mask_patch")) if metadata else False,
        "cache_strict_anchor_check_ran": bool(anchor_report.get("can_check")),
        "cache_strict_anchor_violations_zero": anchor_report.get("strict_anchor_violations") == 0,
        "cache_spatial_mask_check_ran": bool(mask_report.get("can_check")),
        "cache_spatial_mask_policy_pass": bool(mask_report.get("mask_policy_pass")),
        "routing_control_variants_included": routing_controls_included,
        "all_expected_runs_complete": complete_runs == expected_runs and expected_runs > 0,
        "all_required_audit_files_present": all(row["exists"] and row["nonempty"] for row in audit_files),
        "mechanism_gate_status_passed": mechanism_gate_status == "passed",
        "mechanism_audited_runs_cover_expected": mechanism_audited_runs >= expected_runs and expected_runs > 0,
    }
    if not checks["protocol_json_exists"]:
        status = "blocked_protocol_missing"
    elif not checks["cache_metadata_exists"]:
        status = "blocked_cache_missing"
    elif not checks["cache_has_strict_anchor_patch_marker"] or not checks["cache_strict_anchor_violations_zero"]:
        status = "blocked_cache_not_strict_anchor_masked"
    elif not checks["cache_has_spatial_holdout_patch"] or not checks["cache_spatial_mask_policy_pass"]:
        status = "blocked_cache_not_spatial_holdout_masked"
    elif not checks["routing_control_variants_included"]:
        status = "blocked_missing_routing_controls"
    elif missing_runs > 0:
        status = "queued_or_in_progress" if complete_runs > 0 else "ready_to_execute_training"
    elif not checks["all_required_audit_files_present"]:
        status = "blocked_missing_spatial_audits"
    elif not checks["mechanism_gate_status_passed"]:
        status = "blocked_spatial_mechanism_gate_not_passed"
    elif not checks["mechanism_audited_runs_cover_expected"]:
        status = "blocked_spatial_mechanism_gate_incomplete"
    else:
        status = "complete_ready_for_spatial_holdout_evidence"

    report = {
        "status": status,
        "checks": checks,
        "expected_runs": expected_runs,
        "complete_runs": complete_runs,
        "missing_runs": missing_runs,
        "variant_keys": variant_key_list,
        "seeds": seed_list,
        "mechanism_gate_status": mechanism_gate_status,
        "mechanism_audited_runs": mechanism_audited_runs,
        "strict_anchor_mask_report": anchor_report,
        "spatial_mask_report": mask_report,
        "paths": {
            "protocol_json": str(protocol_path),
            "cache_metadata": str(metadata_path),
            "suite_dir": str(suite_dir),
            "run_status_csv": str(output_dir / "spatial_holdout_evidence_run_status.csv"),
            "audit_file_status_csv": str(output_dir / "spatial_holdout_audit_file_status.csv"),
            "mechanism_dir": str(mechanism_dir),
            "reviewer_pack_dir": str(reviewer_pack_dir),
        },
    }
    save_json(output_dir / "spatial_holdout_evidence_guard.json", report)
    lines = [
        "# Spatial holdout evidence guard",
        "",
        f"Status: `{status}`",
        "",
        "This guard distinguishes a prepared turbine-group holdout from completed, citable held-out-turbine evidence.",
        "",
        "## Run Completion",
        "",
        f"- Expected runs: `{expected_runs}`",
        f"- Complete runs: `{complete_runs}`",
        f"- Missing or incomplete runs: `{missing_runs}`",
        "",
        "## Checks",
        "",
    ]
    for key, value in checks.items():
        lines.append(f"- {key}: `{bool(value)}`")
    lines.extend(
        [
            "",
            "## Mechanism Gate",
            "",
            f"- gate_status: `{mechanism_gate_status or 'missing'}`",
            f"- audited_runs: `{mechanism_audited_runs}`",
            "",
            "## Spatial mask report",
            "",
            "```json",
            json.dumps(mask_report, indent=2),
            "```",
            "",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return output_dir


def run_spatial_holdout_guard(
    protocol_dir: Path | str,
    output_dir: Path | str,
    source_cache_dir: Path | str = "artifacts/cache_strictmask/wtb_245d",
    output_cache_root: str = "artifacts/cache_strictmask_spatial_east",
    suite_dir: Path | str = "artifacts/spatial_holdout_wtb_east_runs",
    strategy: str = "east",
    fraction: float = 0.2,
    seeds: Iterable[int] | str | None = None,
    variant_keys: Iterable[str] | str | None = None,
) -> Path:
    protocol_dir = Path(protocol_dir)
    output_dir = ensure_dir(output_dir)
    source_cache_dir = Path(source_cache_dir)
    cache_dir = Path(output_cache_root) / "wtb_245d"
    suite_dir = Path(suite_dir)
    seeds = _parse_seeds(seeds)
    variant_keys = _parse_variant_keys(variant_keys)
    protocol_path = protocol_dir / "spatial_holdout_protocol.json"
    protocol = load_json(protocol_path) if protocol_path.exists() else {}
    metadata_path = cache_dir / "metadata.json"
    metadata = load_json(metadata_path) if metadata_path.exists() else {}
    spatial_patch = metadata.get("spatial_holdout_patch", {}) if metadata else {}
    anchor_report = strict_anchor_mask_report(cache_dir, metadata) if metadata else {"can_check": False}
    mask_report = _spatial_mask_report(cache_dir, metadata) if metadata else {"can_check": False}
    run_status = [
        _run_complete_status(Path(suite_dir) / f"wtb_{variant_key}_seed{seed}", variant_key, seed)
        for variant_key in variant_keys
        for seed in seeds
    ]
    run_df = pd.DataFrame(run_status)
    run_df.to_csv(output_dir / "spatial_holdout_run_status.csv", index=False)
    expected_runs = int(len(run_status))
    complete_runs = int(sum(1 for row in run_status if row["complete"]))
    checks = {
        "protocol_json_exists": protocol_path.exists(),
        "protocol_status_is_not_executed": protocol.get("status") == "protocol_only_not_executed",
        "protocol_source_cache_matches_requested": Path(str(protocol.get("source_cache_dir", ""))) == source_cache_dir
        if protocol
        else False,
        "protocol_output_cache_root_matches_requested": str(protocol.get("output_cache_root", "")).replace("\\", "/")
        == str(output_cache_root).replace("\\", "/")
        if protocol
        else False,
        "protocol_output_cache_dir_matches_requested": str(protocol.get("output_cache_dir", "")).replace("\\", "/")
        == str(cache_dir).replace("\\", "/")
        if protocol
        else False,
        "cache_metadata_exists": metadata_path.exists(),
        "cache_has_spatial_holdout_patch": bool(spatial_patch),
        "cache_spatial_strategy_matches_requested": str(spatial_patch.get("strategy", "")).lower() == str(strategy).lower(),
        "cache_spatial_fraction_matches_requested": abs(float(spatial_patch.get("fraction", -1.0)) - float(fraction))
        < 1e-12,
        "cache_has_strict_anchor_patch_marker": bool(metadata.get("strict_anchor_mask_patch")) if metadata else False,
        "cache_strict_anchor_check_ran": bool(anchor_report.get("can_check")),
        "cache_strict_anchor_violations_zero": anchor_report.get("strict_anchor_violations") == 0,
        "cache_spatial_mask_check_ran": bool(mask_report.get("can_check")),
        "cache_spatial_mask_policy_pass": bool(mask_report.get("mask_policy_pass")),
        "all_expected_runs_complete": complete_runs == expected_runs and expected_runs > 0,
    }
    if not checks["protocol_json_exists"]:
        status = "blocked_protocol_missing"
    elif not checks["protocol_source_cache_matches_requested"] or not checks["protocol_output_cache_dir_matches_requested"]:
        status = "blocked_protocol_cache_mismatch"
    elif not checks["cache_metadata_exists"]:
        status = "ready_to_build_cache"
    elif not checks["cache_has_strict_anchor_patch_marker"] or not checks["cache_strict_anchor_violations_zero"]:
        status = "blocked_cache_not_strict_anchor_masked"
    elif not checks["cache_has_spatial_holdout_patch"] or not checks["cache_spatial_mask_policy_pass"]:
        status = "blocked_cache_not_spatial_holdout_masked"
    elif checks["all_expected_runs_complete"]:
        status = "complete_ready_for_spatial_holdout_comparison"
    else:
        status = "ready_to_execute_training"
    report = {
        "status": status,
        "checks": checks,
        "expected_runs": expected_runs,
        "complete_runs": complete_runs,
        "missing_runs": expected_runs - complete_runs,
        "variant_keys": variant_keys,
        "seeds": seeds,
        "strict_anchor_mask_report": anchor_report,
        "spatial_mask_report": mask_report,
        "paths": {
            "protocol_json": str(protocol_path),
            "source_cache_dir": str(source_cache_dir),
            "cache_metadata": str(metadata_path),
            "suite_dir": str(suite_dir),
            "run_status_csv": str(output_dir / "spatial_holdout_run_status.csv"),
        },
    }
    save_json(output_dir / "spatial_holdout_guard.json", report)
    lines = [
        "# Spatial holdout execution guard",
        "",
        f"Status: `{status}`",
        "",
        "This guard prevents treating a derived cache as spatial holdout evidence unless the strict-anchor mask and turbine-group masking policy both pass.",
        "",
        "## Checks",
        "",
    ]
    for key, value in checks.items():
        lines.append(f"- {key}: `{bool(value)}`")
    lines.extend(
        [
            "",
            "## Strict-anchor mask report",
            "",
            "```json",
            json.dumps(anchor_report, indent=2),
            "```",
            "",
            "## Spatial mask report",
            "",
            "```json",
            json.dumps(mask_report, indent=2),
            "```",
            "",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return output_dir
