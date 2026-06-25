from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import json

import pandas as pd

from .config import DataConfig
from .strict_anchor import strict_anchor_mask_report
from .utils import ensure_dir, load_json, save_json

DEFAULT_FUTURE_HOLDOUT_SEEDS = (301, 302, 303, 304, 305)
DEFAULT_FUTURE_HOLDOUT_VARIANT = "bal_align_force"
DEFAULT_FUTURE_HOLDOUT_LABEL = "MoE + L_bal + L_align + L_force"
DEFAULT_FUTURE_HOLDOUT_MODE = "moe_full_no_aux"
DEFAULT_FUTURE_HOLDOUT_GROUP = "ablation"

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


def _day_range(start_step: int, end_step: int, slots_per_day: int) -> tuple[int, int]:
    if end_step <= start_step:
        return 0, 0
    start_day = int(start_step // slots_per_day) + 1
    end_day = int((end_step - 1) // slots_per_day) + 1
    return start_day, end_day


def _anchor_range(start_step: int, end_step: int, hist_len: int, pred_len: int) -> tuple[int | None, int | None, int]:
    anchor_start = int(start_step) + int(hist_len) - 1
    anchor_end = int(end_step) - int(pred_len) - 1
    if anchor_end < anchor_start:
        return None, None, 0
    return anchor_start, anchor_end, int(anchor_end - anchor_start + 1)


def _split_rows(config: DataConfig) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split, bounds in config.split_bounds().items():
        start, end = int(bounds[0]), int(bounds[1])
        day_start, day_end = _day_range(start, end, config.slots_per_day)
        anchor_start, anchor_end, n_anchors = _anchor_range(start, end, config.hist_len, config.pred_len)
        rows.append(
            {
                "split": split,
                "step_start": start,
                "step_end_exclusive": end,
                "day_start": day_start,
                "day_end": day_end,
                "n_days": max(day_end - day_start + 1, 0) if day_start else 0,
                "anchor_start": anchor_start,
                "anchor_end": anchor_end,
                "n_anchor_windows": n_anchors,
            }
        )
    return rows


def _command_lines(config: DataConfig, output_root: Path, seeds: list[int]) -> list[str]:
    cache_root = Path(config.cache_root)
    cache_dir = Path(config.root_dir) / cache_root / f"wtb_{config.max_days or config.total_days()}d"
    common = (
        f"--dataset wtb --root-dir {config.root_dir} --cache-root {config.cache_root} "
        f"--train-days {config.train_days} --val-days {config.val_days} --test-days {config.test_days} "
        f"--holdout-days {config.holdout_days} --hist-len {config.hist_len} --pred-len {config.pred_len}"
    )
    lines = [
        "python main.py future-holdout-guard "
        f"{common} --protocol-dir artifacts/future_holdout_protocol_wtb_strictmask_20260609 "
        "--output-dir artifacts/future_holdout_protocol_wtb_strictmask_20260609/guard",
        f"python main.py preprocess {common}",
        "python main.py paper-batch "
        f"{common} --output-dir {output_root} --groups ablation --variant-keys bal_align_force "
        f"--seeds {','.join(str(seed) for seed in seeds)} --epochs 20 --batch-size 16 --hidden-dim 64 --skip-visuals",
    ]
    lines.append(
        "python main.py mechanism-gate "
        f"--dataset wtb --root-dir {config.root_dir} --suite-dir {output_root} --cache-dir {cache_dir} "
        "--output-dir artifacts/future_holdout_wtb_strictmask_mechanism_gate "
        '--models "MoE + L_bal + L_align + L_force" --variant-keys bal_align_force --experiment-groups ablation '
        "--split holdout"
    )
    lines.append(
        "python main.py routing-placebo "
        f"--dataset wtb --root-dir {config.root_dir} --run-table "
        "artifacts/future_holdout_wtb_strictmask_mechanism_gate/mechanism_gate_run_table.csv "
        "--output-dir artifacts/future_holdout_wtb_strictmask_placebo --split holdout "
        '--models "MoE + L_bal + L_align + L_force"'
    )
    lines.append(
        "python main.py boundary-slice-audit "
        f"--dataset wtb --root-dir {config.root_dir} --run-table "
        "artifacts/future_holdout_wtb_strictmask_mechanism_gate/mechanism_gate_run_table.csv "
        f"--cache-dir {cache_dir} --output-dir artifacts/future_holdout_wtb_strictmask_boundary_slice "
        "--split holdout "
        '--models "MoE + L_bal + L_align + L_force"'
    )
    lines.append(
        "python main.py reviewer-stat-pack "
        f"--dataset wtb --root-dir {config.root_dir} --suite-dir {output_root} --cache-dir {cache_dir} "
        "--output-dir artifacts/future_holdout_wtb_strictmask_reviewer_stats --split holdout "
        '--models "MoE + L_bal + L_align + L_force" '
        '--reference-model "MoE + L_bal + L_align + L_force" '
        "--bootstrap-samples 1000 --permutation-samples 1000 --max-paired-examples 100000 --top-k-failures 24"
    )
    lines.append(
        "python main.py future-holdout-evidence-guard "
        "--protocol-dir artifacts/future_holdout_protocol_wtb_strictmask_20260609 "
        f"--suite-dir {output_root} --cache-dir {cache_dir} "
        "--mechanism-dir artifacts/future_holdout_wtb_strictmask_mechanism_gate "
        "--placebo-dir artifacts/future_holdout_wtb_strictmask_placebo "
        "--boundary-slice-dir artifacts/future_holdout_wtb_strictmask_boundary_slice "
        "--reviewer-pack-dir artifacts/future_holdout_wtb_strictmask_reviewer_stats "
        "--output-dir artifacts/future_holdout_evidence_guard_wtb_strictmask "
        f"--seeds {','.join(str(seed) for seed in seeds)}"
    )
    return lines


def _jsonable_bounds(bounds: dict[str, tuple[int, int]] | dict[str, list[int]]) -> dict[str, list[int]]:
    return {str(key): [int(value[0]), int(value[1])] for key, value in bounds.items()}


def _parse_seeds(values: Iterable[int] | str | None, fallback: Iterable[int] | None = None) -> list[int]:
    if values is None:
        return [int(seed) for seed in (fallback or DEFAULT_FUTURE_HOLDOUT_SEEDS)]
    if isinstance(values, str):
        return [int(token.strip()) for token in values.split(",") if token.strip()]
    return [int(seed) for seed in values]


def _path_status(label: str, path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "label": label,
        "path": str(path),
        "exists": bool(exists),
        "nonempty": bool(exists and path.is_file() and path.stat().st_size > 0),
    }


def _future_run_complete_status(
    run_dir: Path,
    variant_key: str,
    seed: int,
    model_mode: str,
    experiment_group: str,
    split: str = "holdout",
    require_gate_alignment: bool = True,
) -> dict[str, Any]:
    summary_path = run_dir / "training_summary.json"
    metrics_path = run_dir / f"{split}_metrics" / "metrics.json"
    checkpoint_path = run_dir / "best_model.pt"
    summary = load_json(summary_path) if summary_path.exists() else {}
    metrics = load_json(metrics_path) if metrics_path.exists() else {}
    gate_alignment = metrics.get("gate_alignment", {}) if isinstance(metrics, dict) else {}
    checks = {
        "summary_exists": summary_path.exists(),
        "best_model_exists": checkpoint_path.exists(),
        "metrics_exists": metrics_path.exists(),
        "seed_matches": int(summary.get("seed", -1)) == int(seed) if summary else False,
        "variant_key_matches": str(summary.get("variant_key", "")) == str(variant_key) if summary else False,
        "experiment_group_matches": str(summary.get("experiment_group", "")) == str(experiment_group) if summary else False,
        "model_mode_matches": str(summary.get("model_mode", "")) == str(model_mode) if summary else False,
        f"{split}_summary_present": f"{split}_summary" in summary if summary else False,
        "overall_rmse_present": "overall" in metrics and "rmse" in metrics.get("overall", {}),
        "switch_rmse_present": "switch_window" in metrics and "rmse" in metrics.get("switch_window", {}),
        "gate_nmi_present": (not require_gate_alignment) or "nmi" in gate_alignment,
        "gate_ari_present": (not require_gate_alignment) or "ari" in gate_alignment,
    }
    complete = all(checks.values())
    return {
        "variant_key": variant_key,
        "label": DEFAULT_FUTURE_HOLDOUT_LABEL,
        "mode": model_mode,
        "experiment_group": experiment_group,
        "split": split,
        "seed": int(seed),
        "run_dir": str(run_dir),
        "complete": bool(complete),
        "checks": checks,
        "overall_rmse": metrics.get("overall", {}).get("rmse") if isinstance(metrics, dict) else None,
        "switch_rmse": metrics.get("switch_window", {}).get("rmse") if isinstance(metrics, dict) else None,
        "nmi": gate_alignment.get("nmi") if isinstance(gate_alignment, dict) else None,
        "ari": gate_alignment.get("ari") if isinstance(gate_alignment, dict) else None,
    }


def run_future_holdout_guard(
    protocol_dir: Path | str,
    output_dir: Path | str,
    root_dir: Path | str = ".",
    cache_root: str = "artifacts/cache_strictmask_future",
    train_days: int = 160,
    val_days: int = 25,
    test_days: int = 25,
    holdout_days: int = 35,
    hist_len: int = 36,
    pred_len: int = 24,
    location_file: str = "sdwpf_baidukddcup2022_turb_location.CSV",
    dynamic_file: str = "wtbdata_245days.csv",
) -> Path:
    protocol_dir = Path(protocol_dir)
    output_dir = ensure_dir(output_dir)
    config = DataConfig(
        dataset="wtb",
        root_dir=Path(root_dir),
        cache_root=cache_root,
        train_days=int(train_days),
        val_days=int(val_days),
        test_days=int(test_days),
        holdout_days=int(holdout_days),
        hist_len=int(hist_len),
        pred_len=int(pred_len),
        location_file=location_file,
        dynamic_file=dynamic_file,
    )
    expected_bounds = _jsonable_bounds(config.split_bounds())
    protocol_path = protocol_dir / "future_holdout_protocol.json"
    protocol = load_json(protocol_path) if protocol_path.exists() else {}
    protocol_bounds = _jsonable_bounds(protocol.get("split_policy", {}).get("bounds", {})) if protocol else {}
    raw_dynamic = Path(root_dir) / dynamic_file
    raw_location = Path(root_dir) / location_file
    cache_dir = config.cache_dir()
    cache_metadata_path = cache_dir / "metadata.json"
    cache_metadata = load_json(cache_metadata_path) if cache_metadata_path.exists() else {}
    cache_bounds = _jsonable_bounds(cache_metadata.get("split_bounds", {})) if cache_metadata else {}
    anchor_report = strict_anchor_mask_report(cache_dir, cache_metadata) if cache_metadata else {"can_check": False}
    checks = {
        "protocol_json_exists": protocol_path.exists(),
        "protocol_status_is_not_executed": protocol.get("status") == "protocol_only_not_executed",
        "protocol_bounds_match_requested": protocol_bounds == expected_bounds,
        "raw_dynamic_exists": raw_dynamic.exists(),
        "raw_location_exists": raw_location.exists(),
        "cache_exists": cache_metadata_path.exists(),
        "cache_bounds_match_requested": cache_bounds == expected_bounds,
        "cache_train_days_match": int(cache_metadata.get("train_days", -1)) == int(train_days) if cache_metadata else False,
        "cache_holdout_days_match": int(cache_metadata.get("holdout_days", -1)) == int(holdout_days) if cache_metadata else False,
        "cache_has_strict_anchor_patch_marker": bool(cache_metadata.get("strict_anchor_mask_patch")),
        "cache_strict_anchor_check_ran": bool(anchor_report.get("can_check")),
        "cache_strict_anchor_violations_zero": anchor_report.get("strict_anchor_violations") == 0,
    }
    if not checks["protocol_json_exists"] or not checks["protocol_bounds_match_requested"]:
        status = "blocked_protocol_mismatch"
    elif not checks["raw_dynamic_exists"] or not checks["raw_location_exists"]:
        status = "blocked_missing_raw_data"
    elif not checks["cache_exists"]:
        status = "ready_to_preprocess"
    elif not checks["cache_bounds_match_requested"] or not checks["cache_holdout_days_match"]:
        status = "blocked_cache_split_mismatch"
    elif (
        not checks["cache_has_strict_anchor_patch_marker"]
        or not checks["cache_strict_anchor_check_ran"]
        or not checks["cache_strict_anchor_violations_zero"]
    ):
        status = "blocked_cache_not_strict_anchor_masked"
    else:
        status = "ready_to_execute_training"
    report = {
        "status": status,
        "checks": checks,
        "expected_bounds": expected_bounds,
        "protocol_bounds": protocol_bounds,
        "cache_bounds": cache_bounds,
        "strict_anchor_mask_report": anchor_report,
        "paths": {
            "protocol_json": str(protocol_path),
            "raw_dynamic": str(raw_dynamic),
            "raw_location": str(raw_location),
            "cache_metadata": str(cache_metadata_path),
        },
    }
    save_json(output_dir / "future_holdout_guard.json", report)
    lines = [
        "# Future-holdout execution guard",
        "",
        f"Status: `{status}`",
        "",
        "This guard prevents using an old cache or missing raw files as if they were a pre-specified future holdout rerun.",
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
            "## Expected split bounds",
            "",
            "```json",
            json.dumps(expected_bounds, indent=2),
            "```",
            "",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return output_dir


def run_future_holdout_evidence_guard(
    protocol_dir: Path | str,
    output_dir: Path | str,
    suite_dir: Path | str = "artifacts/future_holdout_wtb_strictmask_runs",
    cache_dir: Path | str = "artifacts/cache_strictmask_future/wtb_245d",
    mechanism_dir: Path | str | None = None,
    placebo_dir: Path | str | None = None,
    boundary_slice_dir: Path | str | None = None,
    reviewer_pack_dir: Path | str | None = None,
    seeds: Iterable[int] | str | None = None,
    variant_key: str = DEFAULT_FUTURE_HOLDOUT_VARIANT,
    model_mode: str = DEFAULT_FUTURE_HOLDOUT_MODE,
    experiment_group: str = DEFAULT_FUTURE_HOLDOUT_GROUP,
    split: str = "holdout",
    require_gate_alignment: bool = True,
) -> Path:
    protocol_dir = Path(protocol_dir)
    output_dir = ensure_dir(output_dir)
    suite_dir = Path(suite_dir)
    cache_dir = Path(cache_dir)
    base_dir = protocol_dir.parent
    mechanism_dir = Path(mechanism_dir) if mechanism_dir is not None else base_dir / "mechanism"
    placebo_dir = Path(placebo_dir) if placebo_dir is not None else base_dir / "placebo"
    boundary_slice_dir = Path(boundary_slice_dir) if boundary_slice_dir is not None else base_dir / "boundary"
    reviewer_pack_dir = Path(reviewer_pack_dir) if reviewer_pack_dir is not None else base_dir / "reviewer"

    protocol_path = protocol_dir / "future_holdout_protocol.json"
    protocol = load_json(protocol_path) if protocol_path.exists() else {}
    protocol_seeds = protocol.get("seeds") if isinstance(protocol.get("seeds"), list) else None
    seed_list = _parse_seeds(seeds, fallback=protocol_seeds)
    protocol_outputs = protocol.get("outputs", {}) if protocol else {}
    protocol_commands = Path(str(protocol_outputs.get("commands_ps1", ""))) if protocol_outputs else None
    metadata_path = cache_dir / "metadata.json"
    metadata = load_json(metadata_path) if metadata_path.exists() else {}
    anchor_report = strict_anchor_mask_report(cache_dir, metadata) if metadata else {"can_check": False}

    run_status = [
        _future_run_complete_status(
            suite_dir / f"wtb_{variant_key}_seed{seed}",
            variant_key=variant_key,
            seed=seed,
            model_mode=model_mode,
            experiment_group=experiment_group,
            split=split,
            require_gate_alignment=require_gate_alignment,
        )
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
                "experiment_group": row["experiment_group"],
                "split": row["split"],
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
    ).to_csv(output_dir / "future_holdout_run_status.csv", index=False)

    mechanism_config_path = mechanism_dir / "mechanism_evidence_gate_config.json"
    mechanism_config = load_json(mechanism_config_path) if mechanism_config_path.exists() else {}
    mechanism_gate_status = str(mechanism_config.get("gate_status", "")) if mechanism_config else ""
    audit_files = [
        _path_status(
            "protocol_commands_ps1",
            protocol_commands if protocol_commands else protocol_dir / "future_holdout_commands.ps1",
        ),
        _path_status("mechanism_evidence_gate_config", mechanism_config_path),
        _path_status("mechanism_gate_run_table", mechanism_dir / "mechanism_gate_run_table.csv"),
        _path_status("checkpoint_replay_audit", mechanism_dir / "checkpoint_replay" / "checkpoint_replay_audit.csv"),
        _path_status("checkpoint_replay_summary", mechanism_dir / "checkpoint_replay" / "checkpoint_replay_summary.csv"),
        _path_status(
            "mechanism_intervention_effects",
            mechanism_dir / "mechanism_intervention" / "mechanism_intervention_effects.csv",
        ),
        _path_status("routing_placebo_summary", placebo_dir / "routing_placebo_summary.csv"),
        _path_status("routing_placebo_effects", placebo_dir / "routing_placebo_effects.csv"),
        _path_status("boundary_slice_summary", boundary_slice_dir / "boundary_slice_summary.csv"),
        _path_status("boundary_slice_effects", boundary_slice_dir / "boundary_slice_effects.csv"),
    ]
    for filename in REVIEWER_STAT_REQUIRED_FILES:
        audit_files.append(_path_status(f"reviewer_stat_pack/{filename}", reviewer_pack_dir / filename))
    pd.DataFrame(audit_files).to_csv(output_dir / "future_holdout_audit_file_status.csv", index=False)

    checks = {
        "protocol_json_exists": protocol_path.exists(),
        "protocol_status_is_not_executed": protocol.get("status") == "protocol_only_not_executed",
        "protocol_seeds_match_requested": [int(seed) for seed in protocol_seeds or seed_list] == seed_list,
        "cache_metadata_exists": metadata_path.exists(),
        "cache_has_strict_anchor_patch_marker": bool(metadata.get("strict_anchor_mask_patch")) if metadata else False,
        "cache_strict_anchor_check_ran": bool(anchor_report.get("can_check")),
        "cache_strict_anchor_violations_zero": anchor_report.get("strict_anchor_violations") == 0,
        "all_expected_runs_complete": complete_runs == expected_runs and expected_runs > 0,
        "all_required_audit_files_present": all(row["exists"] and row["nonempty"] for row in audit_files),
        "mechanism_gate_status_passed": mechanism_gate_status == "passed",
    }
    if not checks["protocol_json_exists"]:
        status = "blocked_protocol_missing"
    elif not checks["cache_metadata_exists"]:
        status = "blocked_cache_missing"
    elif not checks["cache_has_strict_anchor_patch_marker"] or not checks["cache_strict_anchor_violations_zero"]:
        status = "blocked_cache_not_strict_anchor_masked"
    elif missing_runs > 0:
        status = "queued_or_in_progress" if complete_runs > 0 else "ready_to_execute_training"
    elif not checks["all_required_audit_files_present"]:
        status = "blocked_missing_holdout_audits"
    elif not checks["mechanism_gate_status_passed"]:
        status = "blocked_holdout_mechanism_gate_not_passed"
    else:
        status = "complete_ready_for_future_holdout_evidence"

    report = {
        "status": status,
        "checks": checks,
        "expected_runs": expected_runs,
        "complete_runs": complete_runs,
        "missing_runs": missing_runs,
        "variant_key": variant_key,
        "model_mode": model_mode,
        "experiment_group": experiment_group,
        "split": split,
        "seeds": seed_list,
        "mechanism_gate_status": mechanism_gate_status,
        "strict_anchor_mask_report": anchor_report,
        "paths": {
            "protocol_json": str(protocol_path),
            "cache_metadata": str(metadata_path),
            "suite_dir": str(suite_dir),
            "run_status_csv": str(output_dir / "future_holdout_run_status.csv"),
            "audit_file_status_csv": str(output_dir / "future_holdout_audit_file_status.csv"),
            "mechanism_dir": str(mechanism_dir),
            "placebo_dir": str(placebo_dir),
            "boundary_slice_dir": str(boundary_slice_dir),
            "reviewer_pack_dir": str(reviewer_pack_dir),
        },
    }
    save_json(output_dir / "future_holdout_evidence_guard.json", report)
    lines = [
        "# Future-holdout evidence guard",
        "",
        f"Status: `{status}`",
        "",
        "This guard distinguishes a prepared chronological holdout from completed, citable holdout evidence.",
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
            "",
            "## Strict-anchor mask report",
            "",
            "```json",
            json.dumps(anchor_report, indent=2),
            "```",
            "",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return output_dir


def write_future_holdout_protocol(
    output_dir: Path | str,
    root_dir: Path | str = ".",
    cache_root: str = "artifacts/cache_strictmask_future",
    train_days: int = 160,
    val_days: int = 25,
    test_days: int = 25,
    holdout_days: int = 35,
    hist_len: int = 36,
    pred_len: int = 24,
    seeds: list[int] | None = None,
) -> Path:
    output_dir = ensure_dir(output_dir)
    seeds = seeds or [301, 302, 303, 304, 305]
    config = DataConfig(
        dataset="wtb",
        root_dir=Path(root_dir),
        cache_root=cache_root,
        train_days=int(train_days),
        val_days=int(val_days),
        test_days=int(test_days),
        holdout_days=int(holdout_days),
        hist_len=int(hist_len),
        pred_len=int(pred_len),
    )
    rows = _split_rows(config)
    split_df = pd.DataFrame(rows)
    split_df.to_csv(output_dir / "future_holdout_split.csv", index=False)
    commands = _command_lines(config, output_root=Path("artifacts/future_holdout_wtb_strictmask_runs"), seeds=seeds)
    (output_dir / "future_holdout_commands.ps1").write_text("\n".join(commands) + "\n", encoding="utf-8")
    protocol = {
        "status": "protocol_only_not_executed",
        "dataset": "wtb",
        "purpose": "Pre-specified future-period holdout protocol for strict-mask WTB rerun.",
        "claim_supported_after_execution": "future-period routing-semantics and forecasting stress evidence",
        "claim_not_supported_until_execution": "broad deployment robustness or external generalization",
        "split_policy": {
            "train_days": int(train_days),
            "val_days": int(val_days),
            "test_days": int(test_days),
            "holdout_days": int(holdout_days),
            "total_days": int(config.total_days()),
            "slots_per_day": int(config.slots_per_day),
            "hist_len": int(hist_len),
            "pred_len": int(pred_len),
            "bounds": config.split_bounds(),
        },
        "primary_decision_rule": {
            "primary_model": "MoE + L_bal + L_align + L_force",
            "primary_metric": "holdout gate-regime NMI/ARI",
            "secondary_metrics": ["holdout overall RMSE", "holdout switch-window RMSE", "holdout boundary-band RMSE"],
            "minimum_report": "per-seed holdout metrics, replay gate status, mechanism intervention, placebo controls",
            "no_go_condition": "Do not claim deployment robustness if holdout RMSE degrades materially or routing agreement collapses.",
        },
        "seeds": [int(seed) for seed in seeds],
        "outputs": {
            "split_csv": str(output_dir / "future_holdout_split.csv"),
            "commands_ps1": str(output_dir / "future_holdout_commands.ps1"),
        },
    }
    save_json(output_dir / "future_holdout_protocol.json", protocol)
    lines = [
        "# Future-period holdout protocol",
        "",
        "Status: `protocol_only_not_executed`.",
        "",
        "This artifact pre-specifies a chronological WTB rerun with a held-out future period. It is not evidence that the holdout has passed.",
        "",
        "## Split",
        "",
    ]
    for row in rows:
        lines.append(
            f"- {row['split']}: days {row['day_start']}--{row['day_end']}, "
            f"steps {row['step_start']}--{row['step_end_exclusive'] - 1}, "
            f"anchor windows {row['n_anchor_windows']}."
        )
    lines.extend(
        [
            "",
            "## Decision Rule",
            "",
            "- Primary metric: holdout gate-regime NMI/ARI for the strict corrected router.",
            "- Secondary metrics: holdout overall RMSE, switch-window RMSE, and boundary-band RMSE.",
            "- Required reporting: per-seed holdout metrics, replay gate status, mechanism intervention, and placebo controls.",
            "- No-Go: do not claim deployment robustness if holdout RMSE degrades materially or routing agreement collapses.",
            "",
            "## Commands",
            "",
            "```powershell",
            *commands,
            "```",
            "",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return output_dir
