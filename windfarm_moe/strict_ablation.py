from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import json

import pandas as pd

from .config import DataConfig
from .paper import paper_experiment_specs
from .strict_anchor import strict_anchor_mask_report
from .utils import ensure_dir, load_json, save_json


DEFAULT_STRICT_ABLATION_VARIANTS = (
    "dense",
    "unconstrained",
    "bal",
    "align",
    "bal_align",
    "bal_align_force",
    "bal_align_force_smooth",
    "context_align_force",
    "anchor_only",
    "full",
)
DEFAULT_STRICT_ABLATION_SEEDS = (201, 202, 203, 204, 205)
DEFAULT_ROUTING_CONTROL_GATE_VARIANTS = ("bal_align_force", "context_align_force", "anchor_only")


def _variant_specs(dataset: str = "wtb") -> dict[str, dict[str, str]]:
    specs: dict[str, dict[str, str]] = {}
    for spec in paper_experiment_specs(dataset):
        key = str(spec.get("key", ""))
        if key:
            specs[key] = {
                "label": str(spec.get("label", key)),
                "mode": str(spec.get("mode", "")),
            }
    return specs


def _parse_variant_keys(values: Iterable[str] | str | None, dataset: str = "wtb") -> list[str]:
    specs = _variant_specs(dataset)
    if values is None:
        tokens = list(DEFAULT_STRICT_ABLATION_VARIANTS)
    elif isinstance(values, str):
        tokens = [token.strip() for token in values.split(",") if token.strip()]
    else:
        tokens = [str(token).strip() for token in values if str(token).strip()]
    unknown = sorted(set(tokens).difference(specs))
    if unknown:
        available = ", ".join(sorted(specs))
        raise ValueError(f"Unknown strict ablation variant(s): {', '.join(unknown)}. Available: {available}")
    return tokens


def _parse_seeds(values: Iterable[int] | str | None) -> list[int]:
    if values is None:
        return [int(seed) for seed in DEFAULT_STRICT_ABLATION_SEEDS]
    if isinstance(values, str):
        return [int(token.strip()) for token in values.split(",") if token.strip()]
    return [int(seed) for seed in values]


def _jsonable_bounds(bounds: dict[str, tuple[int, int]] | dict[str, list[int]]) -> dict[str, list[int]]:
    return {str(key): [int(value[0]), int(value[1])] for key, value in bounds.items()}


def _path_status(label: str, path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "label": label,
        "path": str(path),
        "exists": bool(exists),
        "nonempty": bool(exists and path.is_file() and path.stat().st_size > 0),
    }


def _run_complete_status(run_dir: Path, variant_key: str, seed: int, specs: dict[str, dict[str, str]]) -> dict[str, Any]:
    summary_path = run_dir / "training_summary.json"
    metrics_path = run_dir / "test_metrics" / "metrics.json"
    summary = load_json(summary_path) if summary_path.exists() else {}
    metrics = load_json(metrics_path) if metrics_path.exists() else {}
    spec = specs[variant_key]
    checks = {
        "summary_exists": summary_path.exists(),
        "metrics_exists": metrics_path.exists(),
        "seed_matches": int(summary.get("seed", -1)) == int(seed) if summary else False,
        "variant_key_matches": str(summary.get("variant_key", "")) == variant_key if summary else False,
        "experiment_group_is_ablation": str(summary.get("experiment_group", "")) == "ablation" if summary else False,
        "model_mode_matches": str(summary.get("model_mode", "")) == spec["mode"] if summary else False,
        "overall_rmse_present": "overall" in metrics and "rmse" in metrics.get("overall", {}),
        "switch_rmse_present": "switch_window" in metrics and "rmse" in metrics.get("switch_window", {}),
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


def run_strict_ablation_guard(
    output_dir: Path | str,
    root_dir: Path | str = ".",
    cache_root: str = "artifacts/cache_strictmask",
    suite_dir: Path | str = "artifacts/strictmask_ablation_rerun_wtb_full",
    train_days: int = 180,
    val_days: int = 30,
    test_days: int = 35,
    hist_len: int = 36,
    pred_len: int = 24,
    variant_keys: Iterable[str] | str | None = None,
    seeds: Iterable[int] | str | None = None,
) -> Path:
    output_dir = ensure_dir(output_dir)
    suite_dir = Path(suite_dir)
    specs = _variant_specs("wtb")
    variant_key_list = _parse_variant_keys(variant_keys)
    seed_list = _parse_seeds(seeds)
    config = DataConfig(
        dataset="wtb",
        root_dir=Path(root_dir),
        cache_root=cache_root,
        train_days=int(train_days),
        val_days=int(val_days),
        test_days=int(test_days),
        hist_len=int(hist_len),
        pred_len=int(pred_len),
    )
    expected_bounds = _jsonable_bounds(config.split_bounds())
    cache_dir = config.cache_dir()
    metadata_path = cache_dir / "metadata.json"
    metadata = load_json(metadata_path) if metadata_path.exists() else {}
    cache_bounds = _jsonable_bounds(metadata.get("split_bounds", {})) if metadata else {}
    anchor_report = strict_anchor_mask_report(cache_dir, metadata) if metadata else {"can_check": False}
    run_status = [
        _run_complete_status(Path(suite_dir) / f"wtb_{variant_key}_seed{seed}", variant_key, seed, specs)
        for variant_key in variant_key_list
        for seed in seed_list
    ]
    complete_runs = int(sum(1 for row in run_status if row["complete"]))
    expected_runs = int(len(run_status))
    missing_runs = expected_runs - complete_runs
    run_df = pd.DataFrame(
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
    )
    run_df.to_csv(output_dir / "strict_ablation_run_status.csv", index=False)
    routing_controls = {"context_align_force", "anchor_only"}.issubset(set(variant_key_list))
    checks = {
        "cache_metadata_exists": metadata_path.exists(),
        "cache_bounds_match_requested": cache_bounds == expected_bounds,
        "cache_has_strict_anchor_patch_marker": bool(metadata.get("strict_anchor_mask_patch")),
        "cache_strict_anchor_check_ran": bool(anchor_report.get("can_check")),
        "cache_strict_anchor_violations_zero": anchor_report.get("strict_anchor_violations") == 0,
        "routing_control_variants_included": routing_controls,
        "all_expected_runs_complete": missing_runs == 0 and expected_runs > 0,
    }
    if not checks["cache_metadata_exists"]:
        status = "blocked_cache_missing"
    elif not checks["cache_bounds_match_requested"]:
        status = "blocked_cache_split_mismatch"
    elif not checks["cache_has_strict_anchor_patch_marker"] or not checks["cache_strict_anchor_violations_zero"]:
        status = "blocked_cache_not_strict_anchor_masked"
    elif not checks["routing_control_variants_included"]:
        status = "blocked_missing_routing_controls"
    elif missing_runs > 0:
        status = "ready_to_execute_training"
    else:
        status = "complete_ready_for_strict_ablation_table"
    report = {
        "status": status,
        "checks": checks,
        "expected_runs": expected_runs,
        "complete_runs": complete_runs,
        "missing_runs": missing_runs,
        "variants": variant_key_list,
        "seeds": seed_list,
        "expected_bounds": expected_bounds,
        "cache_bounds": cache_bounds,
        "anchor_mask_report": anchor_report,
        "paths": {
            "cache_metadata": str(metadata_path),
            "suite_dir": str(suite_dir),
            "run_status_csv": str(output_dir / "strict_ablation_run_status.csv"),
        },
    }
    save_json(output_dir / "strict_ablation_guard.json", report)
    lines = [
        "# Strict-cache ablation guard",
        "",
        f"Status: `{status}`",
        "",
        "This guard prevents legacy or incomplete ablation rows from being used as the strict-cache ablation table.",
        "",
        "## Checks",
        "",
    ]
    for key, value in checks.items():
        lines.append(f"- {key}: `{bool(value)}`")
    lines.extend(
        [
            "",
            "## Run Completion",
            "",
            f"- Expected runs: `{expected_runs}`",
            f"- Complete runs: `{complete_runs}`",
            f"- Missing or incomplete runs: `{missing_runs}`",
            "",
            "## Anchor-Mask Report",
            "",
            "```json",
            json.dumps(anchor_report, indent=2),
            "```",
            "",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return output_dir


def run_strict_ablation_evidence_guard(
    output_dir: Path | str,
    root_dir: Path | str = ".",
    cache_root: str = "artifacts/cache_strictmask",
    suite_dir: Path | str = "artifacts/strictmask_ablation_rerun_wtb_full",
    routing_gate_dir: Path | str = "artifacts/strictmask_ablation_routing_controls_gate",
    train_days: int = 180,
    val_days: int = 30,
    test_days: int = 35,
    hist_len: int = 36,
    pred_len: int = 24,
    variant_keys: Iterable[str] | str | None = None,
    seeds: Iterable[int] | str | None = None,
    gate_variant_keys: Iterable[str] | str | None = None,
) -> Path:
    output_dir = ensure_dir(output_dir)
    suite_dir = Path(suite_dir)
    routing_gate_dir = Path(routing_gate_dir)
    specs = _variant_specs("wtb")
    variant_key_list = _parse_variant_keys(variant_keys)
    seed_list = _parse_seeds(seeds)
    gate_variant_key_list = _parse_variant_keys(gate_variant_keys or ",".join(DEFAULT_ROUTING_CONTROL_GATE_VARIANTS))
    config = DataConfig(
        dataset="wtb",
        root_dir=Path(root_dir),
        cache_root=cache_root,
        train_days=int(train_days),
        val_days=int(val_days),
        test_days=int(test_days),
        hist_len=int(hist_len),
        pred_len=int(pred_len),
    )
    expected_bounds = _jsonable_bounds(config.split_bounds())
    cache_dir = config.cache_dir()
    metadata_path = cache_dir / "metadata.json"
    metadata = load_json(metadata_path) if metadata_path.exists() else {}
    cache_bounds = _jsonable_bounds(metadata.get("split_bounds", {})) if metadata else {}
    anchor_report = strict_anchor_mask_report(cache_dir, metadata) if metadata else {"can_check": False}
    run_status = [
        _run_complete_status(suite_dir / f"wtb_{variant_key}_seed{seed}", variant_key, seed, specs)
        for variant_key in variant_key_list
        for seed in seed_list
    ]
    complete_runs = int(sum(1 for row in run_status if row["complete"]))
    expected_runs = int(len(run_status))
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
    ).to_csv(output_dir / "strict_ablation_evidence_run_status.csv", index=False)

    gate_config_path = routing_gate_dir / "mechanism_evidence_gate_config.json"
    gate_config = load_json(gate_config_path) if gate_config_path.exists() else {}
    gate_status = str(gate_config.get("gate_status", "")) if gate_config else ""
    gate_audited_runs = int(gate_config.get("n_audited_runs", 0)) if gate_config else 0
    expected_gate_runs = int(len(gate_variant_key_list) * len(seed_list))
    audit_files = [
        _path_status("routing_gate_config", gate_config_path),
        _path_status("routing_gate_run_table", routing_gate_dir / "mechanism_gate_run_table.csv"),
        _path_status("checkpoint_replay_audit", routing_gate_dir / "checkpoint_replay" / "checkpoint_replay_audit.csv"),
        _path_status("checkpoint_replay_summary", routing_gate_dir / "checkpoint_replay" / "checkpoint_replay_summary.csv"),
        _path_status(
            "mechanism_intervention_effects",
            routing_gate_dir / "mechanism_intervention" / "mechanism_intervention_effects.csv",
        ),
    ]
    pd.DataFrame(audit_files).to_csv(output_dir / "strict_ablation_evidence_file_status.csv", index=False)
    routing_controls = {"context_align_force", "anchor_only"}.issubset(set(variant_key_list))
    gate_controls = set(DEFAULT_ROUTING_CONTROL_GATE_VARIANTS).issubset(set(gate_variant_key_list))
    checks = {
        "cache_metadata_exists": metadata_path.exists(),
        "cache_bounds_match_requested": cache_bounds == expected_bounds,
        "cache_has_strict_anchor_patch_marker": bool(metadata.get("strict_anchor_mask_patch")) if metadata else False,
        "cache_strict_anchor_check_ran": bool(anchor_report.get("can_check")),
        "cache_strict_anchor_violations_zero": anchor_report.get("strict_anchor_violations") == 0,
        "routing_control_variants_included": routing_controls,
        "routing_gate_variants_cover_controls": gate_controls,
        "all_expected_runs_complete": missing_runs == 0 and expected_runs > 0,
        "all_required_gate_files_present": all(row["exists"] and row["nonempty"] for row in audit_files),
        "routing_gate_status_passed": gate_status == "passed",
        "routing_gate_audited_runs_cover_expected": gate_audited_runs >= expected_gate_runs and expected_gate_runs > 0,
    }
    if not checks["cache_metadata_exists"]:
        status = "blocked_cache_missing"
    elif not checks["cache_bounds_match_requested"]:
        status = "blocked_cache_split_mismatch"
    elif not checks["cache_has_strict_anchor_patch_marker"] or not checks["cache_strict_anchor_violations_zero"]:
        status = "blocked_cache_not_strict_anchor_masked"
    elif not checks["routing_control_variants_included"] or not checks["routing_gate_variants_cover_controls"]:
        status = "blocked_missing_routing_controls"
    elif missing_runs > 0:
        status = "queued_or_in_progress" if complete_runs > 0 else "ready_to_execute_training"
    elif not checks["all_required_gate_files_present"]:
        status = "blocked_missing_routing_control_gate"
    elif not checks["routing_gate_status_passed"]:
        status = "blocked_routing_control_gate_not_passed"
    elif not checks["routing_gate_audited_runs_cover_expected"]:
        status = "blocked_routing_control_gate_incomplete"
    else:
        status = "complete_ready_for_strict_ablation_evidence"
    report = {
        "status": status,
        "checks": checks,
        "expected_runs": expected_runs,
        "complete_runs": complete_runs,
        "missing_runs": missing_runs,
        "expected_routing_gate_runs": expected_gate_runs,
        "routing_gate_audited_runs": gate_audited_runs,
        "routing_gate_status": gate_status,
        "variants": variant_key_list,
        "routing_gate_variants": gate_variant_key_list,
        "seeds": seed_list,
        "expected_bounds": expected_bounds,
        "cache_bounds": cache_bounds,
        "anchor_mask_report": anchor_report,
        "paths": {
            "cache_metadata": str(metadata_path),
            "suite_dir": str(suite_dir),
            "routing_gate_dir": str(routing_gate_dir),
            "run_status_csv": str(output_dir / "strict_ablation_evidence_run_status.csv"),
            "file_status_csv": str(output_dir / "strict_ablation_evidence_file_status.csv"),
        },
    }
    save_json(output_dir / "strict_ablation_evidence_guard.json", report)
    lines = [
        "# Strict-cache ablation evidence guard",
        "",
        f"Status: `{status}`",
        "",
        "This guard prevents citing strict-cache ablation or routing-control evidence until both the full run table and the routing-control replay/intervention gate are complete.",
        "",
        "## Run Completion",
        "",
        f"- Expected ablation runs: `{expected_runs}`",
        f"- Complete ablation runs: `{complete_runs}`",
        f"- Missing or incomplete runs: `{missing_runs}`",
        f"- Expected routing-gate runs: `{expected_gate_runs}`",
        f"- Audited routing-gate runs: `{gate_audited_runs}`",
        "",
        "## Checks",
        "",
    ]
    for key, value in checks.items():
        lines.append(f"- {key}: `{bool(value)}`")
    lines.extend(
        [
            "",
            "## Anchor-Mask Report",
            "",
            "```json",
            json.dumps(anchor_report, indent=2),
            "```",
            "",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return output_dir
