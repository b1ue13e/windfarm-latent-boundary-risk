from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .utils import ensure_dir, load_json, save_json


DEFAULT_STRICT_BASELINE_DIR = Path("artifacts/strict_baseline_protocol_wtb_strictmask_20260609")
DEFAULT_FUTURE_HOLDOUT_DIR = Path("artifacts/future_holdout_protocol_wtb_strictmask_20260609")
DEFAULT_FUTURE_HOLDOUT_EVIDENCE_GUARD_DIR = Path("artifacts/future_holdout_evidence_guard_wtb_strictmask")
DEFAULT_SPATIAL_HOLDOUT_DIR = Path("artifacts/spatial_holdout_protocol_wtb_east_20260611")
DEFAULT_SPATIAL_HOLDOUT_EVIDENCE_GUARD_DIR = Path("artifacts/spatial_holdout_evidence_guard_wtb_east")
DEFAULT_STRICT_ABLATION_GUARD_DIR = Path("artifacts/strict_ablation_guard_wtb_strictmask")
DEFAULT_STRICT_ABLATION_EVIDENCE_GUARD_DIR = Path("artifacts/strict_ablation_evidence_guard_wtb_strictmask")
DEFAULT_THRESHOLD_CONTROLS_GUARD_DIR = Path("artifacts/strict_threshold_controls_guard_wtb_strictmask")
DEFAULT_THRESHOLD_CONTROLS_EVIDENCE_GUARD_DIR = Path("artifacts/strict_threshold_controls_evidence_guard_wtb_strictmask")
DEFAULT_REVIEWER_PACK_GUARD_DIR = Path("artifacts/strictmask_combined_reviewer_stats_guard")
DEFAULT_REPRODUCIBILITY_MANIFEST_DIR = Path("artifacts/reproducibility_manifest_final")
DEFAULT_REVIEWER_PACK = Path("artifacts/strictmask_combined_reviewer_stats/reviewer_stat_pack_config.json")
DEFAULT_AUDIT_DOC = Path("artifacts/science_top_experiment_audit_20260609.md")
DEFAULT_MANUSCRIPT_DOC = Path("paper_draft.md")
DEFAULT_ABLATION_SUITE = Path("artifacts/strictmask_ablation_rerun_wtb_full")
DEFAULT_EXTERNAL_WIND_GUARD_DIR = Path("artifacts/external_wind_guard")
DEFAULT_EXTERNAL_WIND_SOURCE_GUARD_DIR = Path("artifacts/external_wind_source_guard")
DEFAULT_EXTERNAL_WIND_ADAPTATION_GUARD = Path("artifacts/external_wind_small_calibration_adaptation/adaptation_guard.json")
DEFAULT_FINAL_EVIDENCE_MANIFEST = Path("artifacts/final_evidence_package/manifest/evidence_manifest_final.json")

ABLATION_VARIANTS = (
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
ABLATION_SEEDS = (201, 202, 203, 204, 205)


def _latest_file(root: Path, filename: str) -> Path | None:
    if root.is_file():
        return root
    if not root.exists():
        return None
    matches = [path for path in root.rglob(filename) if path.is_file()]
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_mtime)


def _safe_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return load_json(path)


def _status_from_guard(guard: dict[str, Any]) -> str:
    if not guard:
        return "missing"
    status = str(guard.get("status", ""))
    if status.startswith("blocked"):
        return "blocked"
    if status.startswith("complete"):
        return "complete"
    if status.startswith("ready"):
        return "ready"
    return status or "unknown"


def _external_wind_status(guard: dict[str, Any]) -> str:
    if not guard:
        return "missing"
    claim_gate = str(guard.get("claim_gate", ""))
    status = str(guard.get("status", ""))
    if claim_gate == "portable_mechanism_passed":
        return "complete"
    if claim_gate == "within_wtb_only" or status == "complete_but_within_wtb_only":
        return "complete_but_within_wtb_only"
    if claim_gate == "blocked_not_citable" or status.startswith("blocked"):
        return "blocked_not_citable"
    return status or "unknown"


def _final_evidence_status(manifest: dict[str, Any]) -> str:
    if not manifest:
        return "missing"
    status = str(manifest.get("status", ""))
    claim_gate = str(manifest.get("claim_gate", ""))
    if status == "complete_ready_for_submission_tables" and claim_gate == "portable_mechanism_passed":
        return "portable_ready"
    if status == "complete_ready_for_submission_tables" and claim_gate == "within_wtb_only":
        return "within_wtb_ready"
    if claim_gate == "blocked_not_citable" or status.startswith("blocked"):
        return "blocked"
    return status or "unknown"


def _overall_status(items: list[dict[str, Any]], final_manifest: dict[str, Any], external_guard: dict[str, Any]) -> str:
    final_status = _final_evidence_status(final_manifest)
    external_status = _external_wind_status(external_guard)
    if final_status == "portable_ready":
        return "portable_submission_ready"
    if final_status == "within_wtb_ready":
        if external_status == "complete_but_within_wtb_only":
            return "within_wtb_submission_ready_external_nonportable"
        if external_status in {"blocked_not_citable", "missing"}:
            return "within_wtb_submission_ready_external_not_citable"
        return "within_wtb_submission_ready"
    if final_status == "blocked":
        return "blocked_final_evidence_incomplete"
    ready_statuses = {
        "complete",
        "diagnostic_only",
        "pass",
        "available",
        "portable_ready",
        "within_wtb_ready",
        "complete_but_within_wtb_only",
    }
    return "active_incomplete" if any(row["status"] not in ready_statuses for row in items) else "complete_candidate"


def _run_complete(run_dir: Path, variant_key: str, seed: int) -> bool:
    summary_path = run_dir / "training_summary.json"
    metrics_path = run_dir / "test_metrics" / "metrics.json"
    if not summary_path.exists() or not metrics_path.exists():
        return False
    summary = load_json(summary_path)
    metrics = load_json(metrics_path)
    return (
        str(summary.get("variant_key", "")) == str(variant_key)
        and int(summary.get("seed", -1)) == int(seed)
        and "overall" in metrics
        and "rmse" in metrics.get("overall", {})
    )


def _count_suite_runs(suite_dir: Path, variant_keys: tuple[str, ...], seeds: tuple[int, ...]) -> dict[str, int]:
    expected = len(variant_keys) * len(seeds)
    complete = 0
    if suite_dir.exists():
        for variant_key in variant_keys:
            for seed in seeds:
                if _run_complete(suite_dir / f"wtb_{variant_key}_seed{seed}", variant_key, seed):
                    complete += 1
    return {"expected": expected, "complete": complete, "missing": expected - complete}


def _item(
    priority: str,
    requirement: str,
    status: str,
    evidence: str,
    next_action: str,
    expected: int | None = None,
    complete: int | None = None,
    missing: int | None = None,
) -> dict[str, Any]:
    return {
        "priority": priority,
        "requirement": requirement,
        "status": status,
        "expected": expected,
        "complete": complete,
        "missing": missing,
        "evidence": evidence,
        "next_action": next_action,
    }


def _write_refresh_script(output_dir: Path) -> Path:
    script_path = output_dir / "refresh_readiness.ps1"
    script_lines = [
        '$ErrorActionPreference = "Stop"',
        "",
        '$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\\..")',
        "Set-Location $repoRoot",
        "",
        "function Test-ActivePaperBatch {",
        "    $running = Get-CimInstance Win32_Process -Filter \"name = 'python.exe'\" | Where-Object {",
        '        $commandLine = $_.CommandLine -replace [char]34, ""',
        '        $commandLine -notlike "* -Command *" -and $commandLine -like "*main.py paper-batch*"',
        "    }",
        "    return [bool]$running",
        "}",
        "",
        "if (Test-ActivePaperBatch) {",
        '    Write-Host "Skipping readiness refresh while a paper-batch process is active; post-queue finalization will refresh it."',
        "    exit 0",
        "}",
        "",
        'python main.py strict-baseline-guard --protocol-dir artifacts/strict_baseline_protocol_wtb_strictmask_20260609 --output-dir artifacts/strict_baseline_protocol_wtb_strictmask_20260609/guard_refresh --root-dir . --cache-root artifacts/cache_strictmask --suite-dir artifacts/strictmask_baseline_rerun_wtb_full --train-days 180 --val-days 30 --test-days 35 --hist-len 36 --pred-len 24 --variant-keys graph_wavenet,graph_transformer,gat_gru,patchtst --seeds 201,202,203,204,205',
        'python main.py future-holdout-guard --protocol-dir artifacts/future_holdout_protocol_wtb_strictmask_20260609 --output-dir artifacts/future_holdout_protocol_wtb_strictmask_20260609/guard_refresh --root-dir . --cache-root artifacts/cache_strictmask_future --train-days 160 --val-days 25 --test-days 25 --holdout-days 35 --hist-len 36 --pred-len 24',
        'python main.py future-holdout-evidence-guard --protocol-dir artifacts/future_holdout_protocol_wtb_strictmask_20260609 --output-dir artifacts/future_holdout_evidence_guard_wtb_strictmask --suite-dir artifacts/future_holdout_wtb_strictmask_runs --cache-dir artifacts/cache_strictmask_future/wtb_245d --mechanism-dir artifacts/future_holdout_wtb_strictmask_mechanism_gate --placebo-dir artifacts/future_holdout_wtb_strictmask_placebo --boundary-slice-dir artifacts/future_holdout_wtb_strictmask_boundary_slice --reviewer-pack-dir artifacts/future_holdout_wtb_strictmask_reviewer_stats --seeds 301,302,303,304,305',
        'python main.py spatial-holdout-guard --protocol-dir artifacts/spatial_holdout_protocol_wtb_east_20260611 --output-dir artifacts/spatial_holdout_protocol_wtb_east_20260611/guard_refresh --source-cache-dir artifacts/cache_strictmask/wtb_245d --output-cache-root artifacts/cache_strictmask_spatial_east --suite-dir artifacts/spatial_holdout_wtb_east_runs --strategy east --fraction 0.2 --seeds 401,402,403,404,405 --variant-keys bal_align_force,context_align_force,anchor_only',
        'python main.py spatial-holdout-evidence-guard --protocol-dir artifacts/spatial_holdout_protocol_wtb_east_20260611 --output-dir artifacts/spatial_holdout_evidence_guard_wtb_east --suite-dir artifacts/spatial_holdout_wtb_east_runs --cache-dir artifacts/cache_strictmask_spatial_east/wtb_245d --mechanism-dir artifacts/spatial_holdout_wtb_east_mechanism_gate --reviewer-pack-dir artifacts/spatial_holdout_wtb_east_reviewer_stats --seeds 401,402,403,404,405 --variant-keys bal_align_force,context_align_force,anchor_only',
        'python main.py strict-ablation-guard --output-dir artifacts/strict_ablation_guard_wtb_strictmask --root-dir . --cache-root artifacts/cache_strictmask --suite-dir artifacts/strictmask_ablation_rerun_wtb_full --train-days 180 --val-days 30 --test-days 35 --hist-len 36 --pred-len 24 --variant-keys dense,unconstrained,bal,align,bal_align,bal_align_force,bal_align_force_smooth,context_align_force,anchor_only,full --seeds 201,202,203,204,205',
        'python main.py strict-ablation-evidence-guard --output-dir artifacts/strict_ablation_evidence_guard_wtb_strictmask --root-dir . --cache-root artifacts/cache_strictmask --suite-dir artifacts/strictmask_ablation_rerun_wtb_full --routing-gate-dir artifacts/strictmask_ablation_routing_controls_gate --train-days 180 --val-days 30 --test-days 35 --hist-len 36 --pred-len 24 --variant-keys dense,unconstrained,bal,align,bal_align,bal_align_force,bal_align_force_smooth,context_align_force,anchor_only,full --seeds 201,202,203,204,205 --gate-variant-keys bal_align_force,context_align_force,anchor_only',
        'python main.py threshold-controls-guard --output-dir artifacts/strict_threshold_controls_guard_wtb_strictmask --root-dir . --cache-root artifacts/cache_strictmask --suite-dir artifacts/strictmask_threshold_controls_wtb --train-days 180 --val-days 30 --test-days 35 --hist-len 36 --pred-len 24 --variant-keys sens_rated_7p0,sens_rated_13p0,sens_pitch_0p5,sens_pitch_20p0 --seeds 201,202,203,204,205',
        'python main.py paper-export --dataset wtb --root-dir . --cache-root artifacts/cache_strictmask --output-dir artifacts/strictmask_threshold_controls_mechanism_source --wtb-suite-dir artifacts/strictmask_threshold_controls_wtb',
        'python main.py mechanism-intervention --run-table artifacts/strictmask_threshold_controls_mechanism_source/tables/wtb_test_aggregated_runs.csv --cache-dir artifacts/cache_strictmask/wtb_245d --output-dir artifacts/strictmask_threshold_controls_mechanism --root-dir . --split test --models "Physics-Aligned MoE" --interventions actual,anchor_boundary_zero --batch-size 512',
        'python main.py threshold-controls-semantic-guard --output-dir artifacts/strict_threshold_controls_semantic_guard_wtb_strictmask --mechanism-dir artifacts/strictmask_threshold_controls_mechanism --positive-mechanism-dir artifacts/mechanism_gate_wtb_strictmask_full/mechanism_intervention --variant-keys sens_rated_7p0,sens_rated_13p0,sens_pitch_0p5,sens_pitch_20p0 --seeds 201,202,203,204,205',
        'python main.py threshold-controls-evidence-guard --output-dir artifacts/strict_threshold_controls_evidence_guard_wtb_strictmask --root-dir . --cache-root artifacts/cache_strictmask --suite-dir artifacts/strictmask_threshold_controls_wtb --reviewer-pack-dir artifacts/strictmask_threshold_controls_reviewer_stats --semantic-guard-dir artifacts/strict_threshold_controls_semantic_guard_wtb_strictmask --boundary-negative-guard-dir artifacts/boundary_negative_controls_wtb --train-days 180 --val-days 30 --test-days 35 --hist-len 36 --pred-len 24 --variant-keys sens_rated_7p0,sens_rated_13p0,sens_pitch_0p5,sens_pitch_20p0 --seeds 201,202,203,204,205',
        'python main.py threshold-label-validity-audit --dataset wtb --root-dir . --cache-dir artifacts/cache_strictmask/wtb_245d --run-table artifacts/strictmask_combined_reviewer_stats/reviewer_stat_pack_run_table.csv --output-dir artifacts/threshold_label_validity_audit_wtb_strictmask --models "MoE + L_bal + L_align + L_force" --rated-wind-grid 10.0,10.5,11.0 --pitch-threshold-grid 1.5,2.0,2.5 --seeds 201,202,203,204,205',
        'python main.py reviewer-stat-pack-guard --pack-dir artifacts/strictmask_combined_reviewer_stats --output-dir artifacts/strictmask_combined_reviewer_stats_guard --min-runs 35',
        'python main.py science-readiness-dashboard --output-dir artifacts/science_readiness_dashboard_20260611 --root-dir . --threshold-controls-evidence-guard artifacts/strict_threshold_controls_evidence_guard_wtb_strictmask/threshold_controls_evidence_guard.json --reviewer-pack-guard artifacts/strictmask_combined_reviewer_stats_guard/reviewer_stat_pack_guard.json --reviewer-pack-config artifacts/strictmask_combined_reviewer_stats/reviewer_stat_pack_config.json --external-wind-guard artifacts/external_wind_guard/external_wind_guard.json --external-wind-source-guard artifacts/external_wind_source_guard/external_wind_source_guard.json --final-evidence-manifest artifacts/final_evidence_package/manifest/evidence_manifest_final.json --reproducibility-manifest artifacts/reproducibility_manifest_final/reproducibility_manifest.json',
        'python main.py reproducibility-manifest --output-dir artifacts/reproducibility_manifest_final --root-dir . --hash-max-mb 25',
        'python main.py science-readiness-dashboard --output-dir artifacts/science_readiness_dashboard_20260611 --root-dir . --threshold-controls-evidence-guard artifacts/strict_threshold_controls_evidence_guard_wtb_strictmask/threshold_controls_evidence_guard.json --reviewer-pack-guard artifacts/strictmask_combined_reviewer_stats_guard/reviewer_stat_pack_guard.json --reviewer-pack-config artifacts/strictmask_combined_reviewer_stats/reviewer_stat_pack_config.json --external-wind-guard artifacts/external_wind_guard/external_wind_guard.json --external-wind-source-guard artifacts/external_wind_source_guard/external_wind_source_guard.json --final-evidence-manifest artifacts/final_evidence_package/manifest/evidence_manifest_final.json --reproducibility-manifest artifacts/reproducibility_manifest_final/reproducibility_manifest.json',
        "",
        "Get-Content artifacts\\science_readiness_dashboard_20260611\\README.md",
        "",
    ]
    script_path.write_text("\n".join(script_lines), encoding="utf-8")
    return script_path


def run_science_readiness_dashboard(
    output_dir: Path | str,
    root_dir: Path | str = ".",
    strict_baseline_guard: Path | str | None = None,
    future_holdout_guard: Path | str | None = None,
    future_holdout_evidence_guard: Path | str | None = None,
    spatial_holdout_guard: Path | str | None = None,
    spatial_holdout_evidence_guard: Path | str | None = None,
    strict_ablation_guard: Path | str | None = None,
    strict_ablation_evidence_guard: Path | str | None = None,
    threshold_controls_guard: Path | str | None = None,
    threshold_controls_evidence_guard: Path | str | None = None,
    reviewer_pack_guard: Path | str | None = None,
    reproducibility_manifest: Path | str | None = None,
    reviewer_pack_config: Path | str | None = None,
    external_wind_guard: Path | str | None = None,
    external_wind_source_guard: Path | str | None = None,
    external_wind_adaptation_guard: Path | str | None = None,
    final_evidence_manifest: Path | str | None = None,
    audit_doc: Path | str | None = None,
    manuscript_doc: Path | str | None = None,
    ablation_suite_dir: Path | str | None = None,
) -> Path:
    root_dir = Path(root_dir)
    output_dir = ensure_dir(output_dir)

    strict_path = Path(strict_baseline_guard) if strict_baseline_guard else _latest_file(root_dir / DEFAULT_STRICT_BASELINE_DIR, "strict_baseline_guard.json")
    future_path = Path(future_holdout_guard) if future_holdout_guard else _latest_file(root_dir / DEFAULT_FUTURE_HOLDOUT_DIR, "future_holdout_guard.json")
    future_evidence_path = (
        Path(future_holdout_evidence_guard)
        if future_holdout_evidence_guard
        else _latest_file(root_dir / DEFAULT_FUTURE_HOLDOUT_EVIDENCE_GUARD_DIR, "future_holdout_evidence_guard.json")
    )
    spatial_path = Path(spatial_holdout_guard) if spatial_holdout_guard else _latest_file(root_dir / DEFAULT_SPATIAL_HOLDOUT_DIR, "spatial_holdout_guard.json")
    spatial_evidence_path = (
        Path(spatial_holdout_evidence_guard)
        if spatial_holdout_evidence_guard
        else _latest_file(root_dir / DEFAULT_SPATIAL_HOLDOUT_EVIDENCE_GUARD_DIR, "spatial_holdout_evidence_guard.json")
    )
    ablation_guard_path = Path(strict_ablation_guard) if strict_ablation_guard else _latest_file(root_dir / DEFAULT_STRICT_ABLATION_GUARD_DIR, "strict_ablation_guard.json")
    ablation_evidence_path = (
        Path(strict_ablation_evidence_guard)
        if strict_ablation_evidence_guard
        else _latest_file(root_dir / DEFAULT_STRICT_ABLATION_EVIDENCE_GUARD_DIR, "strict_ablation_evidence_guard.json")
    )
    threshold_guard_path = Path(threshold_controls_guard) if threshold_controls_guard else _latest_file(root_dir / DEFAULT_THRESHOLD_CONTROLS_GUARD_DIR, "threshold_controls_guard.json")
    threshold_evidence_path = (
        Path(threshold_controls_evidence_guard)
        if threshold_controls_evidence_guard
        else _latest_file(root_dir / DEFAULT_THRESHOLD_CONTROLS_EVIDENCE_GUARD_DIR, "threshold_controls_evidence_guard.json")
    )
    reviewer_guard_path = Path(reviewer_pack_guard) if reviewer_pack_guard else _latest_file(root_dir / DEFAULT_REVIEWER_PACK_GUARD_DIR, "reviewer_stat_pack_guard.json")
    repro_path = Path(reproducibility_manifest) if reproducibility_manifest else _latest_file(root_dir / DEFAULT_REPRODUCIBILITY_MANIFEST_DIR, "reproducibility_manifest.json")
    reviewer_path = Path(reviewer_pack_config) if reviewer_pack_config else root_dir / DEFAULT_REVIEWER_PACK
    external_guard_path = Path(external_wind_guard) if external_wind_guard else _latest_file(root_dir / DEFAULT_EXTERNAL_WIND_GUARD_DIR, "external_wind_guard.json")
    external_source_guard_path = (
        Path(external_wind_source_guard)
        if external_wind_source_guard
        else _latest_file(root_dir / DEFAULT_EXTERNAL_WIND_SOURCE_GUARD_DIR, "external_wind_source_guard.json")
    )
    external_adaptation_guard_path = (
        Path(external_wind_adaptation_guard)
        if external_wind_adaptation_guard
        else root_dir / DEFAULT_EXTERNAL_WIND_ADAPTATION_GUARD
    )
    final_manifest_path = Path(final_evidence_manifest) if final_evidence_manifest else root_dir / DEFAULT_FINAL_EVIDENCE_MANIFEST
    audit_path = Path(audit_doc) if audit_doc else root_dir / DEFAULT_AUDIT_DOC
    manuscript_path = Path(manuscript_doc) if manuscript_doc else root_dir / DEFAULT_MANUSCRIPT_DOC
    ablation_suite = Path(ablation_suite_dir) if ablation_suite_dir else root_dir / DEFAULT_ABLATION_SUITE

    strict = _safe_json(strict_path)
    future = _safe_json(future_path)
    future_evidence = _safe_json(future_evidence_path)
    spatial = _safe_json(spatial_path)
    spatial_evidence = _safe_json(spatial_evidence_path)
    ablation_guard = _safe_json(ablation_guard_path)
    ablation_evidence_guard = _safe_json(ablation_evidence_path)
    threshold_guard = _safe_json(threshold_guard_path)
    threshold_evidence_guard = _safe_json(threshold_evidence_path)
    reviewer_guard = _safe_json(reviewer_guard_path)
    repro_manifest = _safe_json(repro_path)
    reviewer = _safe_json(reviewer_path)
    external_guard = _safe_json(external_guard_path)
    external_source_guard = _safe_json(external_source_guard_path)
    external_adaptation_guard = _safe_json(external_adaptation_guard_path)
    final_manifest = _safe_json(final_manifest_path)
    ablation_counts = _count_suite_runs(ablation_suite, ABLATION_VARIANTS, ABLATION_SEEDS)

    items: list[dict[str, Any]] = []
    strict_status = _status_from_guard(strict)
    if strict and not strict.get("checks", {}).get("all_expected_runs_complete", False):
        strict_status = "in_progress"
    items.append(
        _item(
            "fatal",
            "Strict-cache strong baselines: Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST",
            strict_status,
            str(strict_path) if strict_path else "",
            "Wait for remaining GAT-GRU/PatchTST runs and rerun strict-baseline-guard.",
            int(strict.get("expected_runs", 0)) if strict else None,
            int(strict.get("complete_runs", 0)) if strict else None,
            int(strict.get("missing_runs", 0)) if strict else None,
        )
    )

    if spatial_evidence:
        spatial_status = _status_from_guard(spatial_evidence)
        spatial_evidence_source = str(spatial_evidence_path)
        spatial_next_action = "Execute spatial holdout training, mechanism gate, and reviewer-stat pack."
        spatial_expected = int(spatial_evidence.get("expected_runs", 0))
        spatial_complete = int(spatial_evidence.get("complete_runs", 0))
        spatial_missing = int(spatial_evidence.get("missing_runs", 0))
    else:
        spatial_status = _status_from_guard(spatial)
        if spatial and not spatial.get("checks", {}).get("all_expected_runs_complete", False):
            spatial_status = "ready"
        spatial_evidence_source = str(spatial_path) if spatial_path else ""
        spatial_next_action = "Run spatial-holdout-evidence-guard after the cache/run guard, then execute held-out turbine audits."
        spatial_expected = int(spatial.get("expected_runs", 0)) if spatial else None
        spatial_complete = int(spatial.get("complete_runs", 0)) if spatial else None
        spatial_missing = int(spatial.get("missing_runs", 0)) if spatial else None
    items.append(
        _item(
            "fatal",
            "WTB east-cluster spatial turbine-group holdout",
            spatial_status,
            spatial_evidence_source,
            spatial_next_action,
            spatial_expected,
            spatial_complete,
            spatial_missing,
        )
    )

    if future_evidence:
        future_status = _status_from_guard(future_evidence)
        future_evidence_source = str(future_evidence_path)
        future_next_action = "Execute queued future holdout runs and holdout audits."
        future_expected = int(future_evidence.get("expected_runs", 0))
        future_complete = int(future_evidence.get("complete_runs", 0))
        future_missing = int(future_evidence.get("missing_runs", 0))
    else:
        future_status = _status_from_guard(future)
        future_evidence_source = str(future_path) if future_path else ""
        future_next_action = "Run future-holdout-evidence-guard after the protocol/cache guard, then execute queued holdout runs."
        future_expected = None
        future_complete = None
        future_missing = None
    items.append(
        _item(
            "high-priority",
            "Pre-specified future-period holdout",
            future_status,
            future_evidence_source,
            future_next_action,
            future_expected,
            future_complete,
            future_missing,
        )
    )

    if ablation_evidence_guard:
        ablation_status = _status_from_guard(ablation_evidence_guard)
        if ablation_evidence_guard and not ablation_evidence_guard.get("checks", {}).get("all_expected_runs_complete", False):
            ablation_status = "queued_or_in_progress"
        ablation_expected = int(ablation_evidence_guard.get("expected_runs", 0))
        ablation_complete = int(ablation_evidence_guard.get("complete_runs", 0))
        ablation_missing = int(ablation_evidence_guard.get("missing_runs", 0))
        ablation_evidence = str(ablation_evidence_path)
    elif ablation_guard:
        ablation_status = _status_from_guard(ablation_guard)
        if ablation_guard and not ablation_guard.get("checks", {}).get("all_expected_runs_complete", False):
            ablation_status = "queued_or_in_progress"
        ablation_expected = int(ablation_guard.get("expected_runs", 0))
        ablation_complete = int(ablation_guard.get("complete_runs", 0))
        ablation_missing = int(ablation_guard.get("missing_runs", 0))
        ablation_evidence = str(ablation_guard_path)
    else:
        ablation_status = "complete" if ablation_counts["complete"] == ablation_counts["expected"] else "queued_or_in_progress"
        ablation_expected = ablation_counts["expected"]
        ablation_complete = ablation_counts["complete"]
        ablation_missing = ablation_counts["missing"]
        ablation_evidence = str(ablation_suite)
    items.append(
        _item(
            "high-priority",
            "Strict-cache full ablation including simple routing controls",
            ablation_status,
            ablation_evidence,
            "Run strict ablation suite and mechanism-gate routing controls.",
            ablation_expected,
            ablation_complete,
            ablation_missing,
        )
    )

    threshold_source = threshold_evidence_path if threshold_evidence_guard else threshold_guard_path
    threshold_for_counts = threshold_evidence_guard if threshold_evidence_guard else threshold_guard
    threshold_status = _status_from_guard(threshold_for_counts)
    if threshold_for_counts and not threshold_for_counts.get("checks", {}).get("all_expected_runs_complete", False):
        threshold_status = "queued_or_in_progress"
    items.append(
        _item(
            "high-priority",
            "Strict-cache wrong-threshold mechanism negative controls",
            threshold_status,
            str(threshold_source) if threshold_source else "",
            "Run strict threshold-control sensitivity suite and reviewer-stat pack.",
            int(threshold_for_counts.get("expected_runs", 0)) if threshold_for_counts else None,
            int(threshold_for_counts.get("complete_runs", 0)) if threshold_for_counts else None,
            int(threshold_for_counts.get("missing_runs", 0)) if threshold_for_counts else None,
        )
    )

    reviewer_status = "missing"
    reviewer_complete = None
    reviewer_evidence = str(reviewer_path)
    if reviewer_guard:
        raw_status = str(reviewer_guard.get("status", ""))
        if raw_status.startswith("complete"):
            reviewer_status = "available"
        elif raw_status.startswith("preliminary"):
            reviewer_status = "preliminary"
        elif raw_status.startswith("blocked"):
            reviewer_status = "blocked"
        else:
            reviewer_status = raw_status or "unknown"
        reviewer_complete = int(reviewer_guard.get("n_runs", 0))
        reviewer_evidence = str(reviewer_guard_path)
    elif reviewer:
        reviewer_status = "preliminary" if int(reviewer.get("n_runs", 0)) < 20 else "available"
        reviewer_complete = int(reviewer.get("n_runs", 0))
    items.append(
        _item(
            "strengthening",
            "Reviewer statistics pack: per-example rows, paired tests, efficiency, failure cases",
            reviewer_status,
            reviewer_evidence,
            "Regenerate final combined reviewer-stat pack after all strict baselines and ablations finish.",
            None,
            reviewer_complete,
            None,
        )
    )

    external_status = _external_wind_status(external_guard)
    external_next_action = "Run scripts/run_external_wind_full_evidence.ps1 -RunTraining, then refresh final evidence before citing cross-farm portability."
    if external_status == "complete_but_within_wtb_only":
        external_next_action = "Keep the manuscript at WTB-only mechanism evidence; do not cite cross-farm portability."
    elif external_status == "complete":
        external_next_action = "Cross-farm portability may be cited after final evidence manifest is refreshed."
    items.append(
        _item(
            "fatal",
            "External Kelmarsh/Penmanshiel portability guard",
            external_status,
            str(external_guard_path) if external_guard_path else "",
            external_next_action,
            int(external_guard.get("expected_runs", 0)) if external_guard else None,
            int(external_guard.get("complete_runs", 0)) if external_guard else None,
            int(external_guard.get("expected_runs", 0)) - int(external_guard.get("complete_runs", 0))
            if external_guard and "expected_runs" in external_guard
            else None,
        )
    )

    source_status = _status_from_guard(external_source_guard)
    items.append(
        _item(
            "high-priority",
            "External wind source-data guard",
            source_status,
            str(external_source_guard_path) if external_source_guard_path else "",
            "Keep Kelmarsh/Penmanshiel source files, checksums, and CC-BY-4.0 manifest in the release bundle.",
            int(external_source_guard.get("min_files", 0)) if external_source_guard else None,
            int(external_source_guard.get("n_local_exists", 0)) if external_source_guard else None,
            int(external_source_guard.get("min_files", 0)) - int(external_source_guard.get("n_local_exists", 0))
            if external_source_guard and "min_files" in external_source_guard
            else None,
        )
    )

    adaptation_status = _status_from_guard(external_adaptation_guard)
    if external_adaptation_guard and str(external_adaptation_guard.get("status", "")).startswith("complete"):
        adaptation_status = (
            "diagnostic_only"
            if not bool(external_adaptation_guard.get("site_specific_adaptation_wording_allowed", False))
            else "complete"
        )
    items.append(
        _item(
            "high-priority",
            "Kelmarsh/Penmanshiel site-specific small-calibration adaptation",
            adaptation_status,
            str(external_adaptation_guard_path),
            "Report as a site-specific adaptation diagnostic; do not claim usable external routing unless the guard allows it.",
            int(external_adaptation_guard.get("n_routing_runs", 0)) if external_adaptation_guard else None,
            int(external_adaptation_guard.get("n_adapted_runs", 0)) if external_adaptation_guard else None,
            int(external_adaptation_guard.get("n_routing_runs", 0)) - int(external_adaptation_guard.get("n_adapted_runs", 0))
            if external_adaptation_guard and "n_routing_runs" in external_adaptation_guard
            else None,
        )
    )

    final_status = _final_evidence_status(final_manifest)
    final_next_action = "Refresh final evidence after any guard, reviewer pack, or manuscript claim-gate change."
    if final_status == "within_wtb_ready":
        final_next_action = "Submission tables are ready for the downgraded WTB-only claim; external portability remains uncited."
    elif final_status == "portable_ready":
        final_next_action = "Submission tables are ready for the portable-mechanism claim."
    items.append(
        _item(
            "fatal",
            "Final evidence manifest claim gate",
            final_status,
            str(final_manifest_path),
            final_next_action,
        )
    )

    repro_status = "missing"
    if repro_manifest:
        raw_status = str(repro_manifest.get("status", ""))
        if raw_status.startswith("complete"):
            repro_status = "available"
        elif raw_status.startswith("preliminary"):
            repro_status = "preliminary"
        elif raw_status.startswith("blocked"):
            repro_status = "blocked"
        else:
            repro_status = raw_status or "unknown"
    items.append(
        _item(
            "strengthening",
            "Reproducibility and compliance manifest",
            repro_status,
            str(repro_path) if repro_path else "",
            "Keep the manifest refreshed after each guard or evidence-package update.",
            int(repro_manifest.get("n_required_files", 0)) if repro_manifest else None,
            int(repro_manifest.get("n_required_files", 0)) - int(repro_manifest.get("n_missing_required_files", 0))
            if repro_manifest
            else None,
            int(repro_manifest.get("n_missing_required_files", 0)) if repro_manifest else None,
        )
    )

    audit_text = audit_path.read_text(encoding="utf-8").lower() if audit_path.exists() else ""
    manuscript_text = manuscript_path.read_text(encoding="utf-8").lower() if manuscript_path.exists() else ""
    era5_text = f"{audit_text}\n{manuscript_text}"
    era5_has_persistence_limit = any(
        phrase in era5_text
        for phrase in [
            "persistence wins headline rmse",
            "persistence is hard to beat",
            "last-value persistence",
        ]
    )
    era5_has_routing_calibration = any(
        phrase in era5_text
        for phrase in [
            "calibrates gate-regime agreement",
            "calibration around a visible thermodynamic",
            "routing calibrates",
            "visible-regime routing calibration",
        ]
    )
    era5_rejects_broad_forecast = any(
        phrase in era5_text
        for phrase in [
            "not broad deployment",
            "not prediction superiority",
            "not broad forecast repair",
            "without creating a better headline forecasting map",
        ]
    )
    era5_narrowed = era5_has_persistence_limit and era5_has_routing_calibration and era5_rejects_broad_forecast
    items.append(
        _item(
            "strengthening",
            "ERA5 claim narrowed away from forecasting advantage",
            "pass" if era5_narrowed else "needs_review",
            f"{audit_path}; {manuscript_path}",
            "Keep ERA5 framed as visible-regime routing calibration, not prediction superiority.",
        )
    )

    status_counts = pd.Series([row["status"] for row in items]).value_counts().to_dict()
    dashboard = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "overall_status": _overall_status(items, final_manifest, external_guard),
        "claim_gate": str(final_manifest.get("claim_gate", "")) if final_manifest else "",
        "final_evidence_status": str(final_manifest.get("status", "")) if final_manifest else "missing",
        "external_wind_claim_gate": str(external_guard.get("claim_gate", "")) if external_guard else "missing",
        "status_counts": {str(key): int(value) for key, value in status_counts.items()},
        "items": items,
        "source_paths": {
            "strict_baseline_guard": str(strict_path) if strict_path else "",
            "future_holdout_guard": str(future_path) if future_path else "",
            "future_holdout_evidence_guard": str(future_evidence_path) if future_evidence_path else "",
            "spatial_holdout_guard": str(spatial_path) if spatial_path else "",
            "spatial_holdout_evidence_guard": str(spatial_evidence_path) if spatial_evidence_path else "",
            "strict_ablation_guard": str(ablation_guard_path) if ablation_guard_path else "",
            "strict_ablation_evidence_guard": str(ablation_evidence_path) if ablation_evidence_path else "",
            "threshold_controls_guard": str(threshold_guard_path) if threshold_guard_path else "",
            "threshold_controls_evidence_guard": str(threshold_evidence_path) if threshold_evidence_path else "",
            "reviewer_pack_guard": str(reviewer_guard_path) if reviewer_guard_path else "",
            "reproducibility_manifest": str(repro_path) if repro_path else "",
            "reviewer_pack_config": str(reviewer_path),
            "external_wind_guard": str(external_guard_path) if external_guard_path else "",
            "external_wind_source_guard": str(external_source_guard_path) if external_source_guard_path else "",
            "external_wind_adaptation_guard": str(external_adaptation_guard_path),
            "final_evidence_manifest": str(final_manifest_path),
            "audit_doc": str(audit_path),
            "manuscript_doc": str(manuscript_path),
            "ablation_suite_dir": str(ablation_suite),
        },
    }
    save_json(output_dir / "science_readiness_status.json", dashboard)
    pd.DataFrame(items).to_csv(output_dir / "science_readiness_items.csv", index=False)
    refresh_script = _write_refresh_script(output_dir)

    lines = [
        "# Science readiness dashboard",
        "",
        f"Generated at: `{dashboard['generated_at']}`",
        f"Overall status: `{dashboard['overall_status']}`",
        "",
        "Refresh command:",
        "",
        "```powershell",
        str(refresh_script),
        "```",
        "",
        "## Items",
        "",
    ]
    for row in items:
        count_text = ""
        if row["expected"] is not None:
            count_text = f" ({row['complete']}/{row['expected']} complete)"
        lines.append(f"- {row['priority']} | {row['status']} | {row['requirement']}{count_text}")
        if row["next_action"]:
            lines.append(f"  Next: {row['next_action']}")
    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    dashboard["source_paths"]["refresh_script"] = str(refresh_script)
    save_json(output_dir / "science_readiness_status.json", dashboard)
    return output_dir
