from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
import hashlib
import platform
import sys

import pandas as pd

from .utils import ensure_dir, load_json, save_json


DEFAULT_REPRODUCIBILITY_FILES: tuple[dict[str, Any], ...] = (
    {"category": "data", "label": "WTB dynamic raw data", "path": "wtbdata_245days.csv", "required": True},
    {
        "category": "data",
        "label": "WTB turbine-location raw data",
        "path": "sdwpf_baidukddcup2022_turb_location.CSV",
        "required": True,
    },
    {
        "category": "data",
        "label": "WTB strict-cache metadata",
        "path": "artifacts/cache_strictmask/wtb_245d/metadata.json",
        "required": True,
    },
    {
        "category": "evidence",
        "label": "Strict WTB evidence SHA256 manifest",
        "path": "artifacts/strict_wtb_evidence_sources_20260609/strict_wtb_evidence_manifest.json",
        "required": True,
    },
    {
        "category": "evidence",
        "label": "Final evidence manifest",
        "path": "artifacts/final_evidence_package/manifest/evidence_manifest_final.json",
        "required": True,
    },
    {
        "category": "evidence",
        "label": "Final evidence export status",
        "path": "artifacts/final_evidence_package/export/final_table_export_status.json",
        "required": True,
    },
    {
        "category": "evidence",
        "label": "Final evidence source-data index",
        "path": "artifacts/final_evidence_package/export/source_data_index.csv",
        "required": True,
    },
    {
        "category": "evidence",
        "label": "WTB operational engineering baseline summary",
        "path": "artifacts/operational_baselines_wtb_strictmask/wtb_operational_baselines.csv",
        "required": True,
    },
    {
        "category": "evidence",
        "label": "WTB operational engineering baseline LaTeX table",
        "path": "artifacts/operational_baselines_wtb_strictmask/table_wtb_operational_baselines.tex",
        "required": True,
    },
    {
        "category": "evidence",
        "label": "WTB transition-window reserve summary",
        "path": "artifacts/decision_reserve_wtb_operational_windows/reserve_decision_summary.csv",
        "required": True,
    },
    {
        "category": "evidence",
        "label": "WTB transition-window reserve operational windows",
        "path": "artifacts/decision_reserve_wtb_operational_windows/reserve_decision_operational_windows.csv",
        "required": True,
    },
    {
        "category": "guard",
        "label": "Strict strong-baseline guard",
        "path": "artifacts/strict_baseline_protocol_wtb_strictmask_20260609/guard_refresh/strict_baseline_guard.json",
        "required": True,
    },
    {
        "category": "guard",
        "label": "Future holdout guard",
        "path": "artifacts/future_holdout_protocol_wtb_strictmask_20260609/guard_refresh/future_holdout_guard.json",
        "required": True,
    },
    {
        "category": "guard",
        "label": "Future holdout evidence guard",
        "path": "artifacts/future_holdout_evidence_guard_wtb_strictmask/future_holdout_evidence_guard.json",
        "required": True,
    },
    {
        "category": "guard",
        "label": "Spatial holdout guard",
        "path": "artifacts/spatial_holdout_protocol_wtb_east_20260611/guard_refresh/spatial_holdout_guard.json",
        "required": True,
    },
    {
        "category": "guard",
        "label": "Spatial holdout evidence guard",
        "path": "artifacts/spatial_holdout_evidence_guard_wtb_east/spatial_holdout_evidence_guard.json",
        "required": True,
    },
    {
        "category": "guard",
        "label": "Strict ablation guard",
        "path": "artifacts/strict_ablation_guard_wtb_strictmask/strict_ablation_guard.json",
        "required": True,
    },
    {
        "category": "guard",
        "label": "Strict ablation evidence guard",
        "path": "artifacts/strict_ablation_evidence_guard_wtb_strictmask/strict_ablation_evidence_guard.json",
        "required": True,
    },
    {
        "category": "guard",
        "label": "Threshold controls guard",
        "path": "artifacts/strict_threshold_controls_guard_wtb_strictmask/threshold_controls_guard.json",
        "required": True,
    },
    {
        "category": "guard",
        "label": "Threshold controls evidence guard",
        "path": "artifacts/strict_threshold_controls_evidence_guard_wtb_strictmask/threshold_controls_evidence_guard.json",
        "required": True,
    },
    {
        "category": "guard",
        "label": "Boundary negative controls guard",
        "path": "artifacts/boundary_negative_controls_wtb/boundary_negative_controls_guard.json",
        "required": True,
    },
    {
        "category": "guard",
        "label": "Mechanism behavior pack guard",
        "path": "artifacts/mechanism_behavior_pack_wtb/mechanism_behavior_pack_guard.json",
        "required": True,
    },
    {
        "category": "guard",
        "label": "Transition-window reserve-decision guard",
        "path": "artifacts/decision_reserve_wtb_operational_windows_guard/reserve_decision_guard.json",
        "required": True,
    },
    {
        "category": "guard",
        "label": "External wind portability guard",
        "path": "artifacts/external_wind_guard/external_wind_guard.json",
        "required": True,
    },
    {
        "category": "guard",
        "label": "Preliminary reviewer statistics guard",
        "path": "artifacts/reviewer_stat_pack_guard_wtb_strictmask_available/reviewer_stat_pack_guard.json",
        "required": True,
    },
    {
        "category": "guard",
        "label": "Combined strict reviewer statistics guard",
        "path": "artifacts/strictmask_combined_reviewer_stats_guard/reviewer_stat_pack_guard.json",
        "required": True,
    },
    {
        "category": "readiness",
        "label": "Science readiness dashboard",
        "path": "artifacts/science_readiness_dashboard_20260611/science_readiness_status.json",
        "required": True,
    },
    {
        "category": "audit",
        "label": "Science-style experiment audit",
        "path": "artifacts/science_top_experiment_audit_20260609.md",
        "required": True,
    },
    {"category": "manuscript", "label": "Submission draft", "path": "paper_draft.md", "required": True},
    {
        "category": "script",
        "label": "Strict follow-up queue",
        "path": "artifacts/strict_followup_queue_20260611.ps1",
        "required": True,
    },
    {
        "category": "script",
        "label": "Strict extension queue",
        "path": "artifacts/strict_extension_queue_20260611.ps1",
        "required": True,
    },
    {
        "category": "script",
        "label": "Future holdout queue",
        "path": "artifacts/future_holdout_queue_20260611.ps1",
        "required": True,
    },
    {
        "category": "script",
        "label": "Post-queue finalization",
        "path": "artifacts/strict_postqueue_finalize_20260611.ps1",
        "required": True,
    },
    {
        "category": "script",
        "label": "Goal strict completion queue",
        "path": "artifacts/goal_strict_completion_queue_20260612.ps1",
        "required": True,
    },
    {
        "category": "reproduction",
        "label": "Science reproduction package index",
        "path": "artifacts/reproduction_package_20260611/reproduction_index.json",
        "required": True,
    },
    {
        "category": "reproduction",
        "label": "Guard-only reproduction entry point",
        "path": "artifacts/reproduction_package_20260611/refresh_guards_only.ps1",
        "required": True,
    },
    {
        "category": "reproduction",
        "label": "Active experiment queue entry point",
        "path": "artifacts/reproduction_package_20260611/run_active_experiment_queues.ps1",
        "required": True,
    },
    {
        "category": "reproduction",
        "label": "Submission artifact rebuild entry point",
        "path": "artifacts/reproduction_package_20260611/rebuild_submission_artifacts.ps1",
        "required": True,
    },
    {
        "category": "reproduction",
        "label": "Final evidence package rebuild entry point",
        "path": "artifacts/reproduction_package_20260611/rebuild_final_evidence_package.ps1",
        "required": True,
    },
    {
        "category": "reproduction",
        "label": "External wind protocol entry point",
        "path": "artifacts/reproduction_package_20260611/external_wind_protocol.ps1",
        "required": True,
    },
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _portable_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except (OSError, ValueError):
        return str(path)


def _environment() -> dict[str, Any]:
    env: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "python": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "machine": platform.machine(),
    }
    for module_name in ["numpy", "pandas", "torch", "sklearn", "matplotlib"]:
        try:
            module = __import__(module_name)
        except Exception as exc:  # pragma: no cover - defensive environment capture
            env[f"{module_name}_available"] = False
            env[f"{module_name}_error"] = repr(exc)
            continue
        env[f"{module_name}_available"] = True
        env[f"{module_name}_version"] = str(getattr(module, "__version__", "unknown"))
        if module_name == "torch":
            env["torch_cuda_available"] = bool(module.cuda.is_available())
            env["torch_cuda_version"] = str(getattr(module.version, "cuda", ""))
    return env


def _file_record(root_dir: Path, row: dict[str, Any], hash_max_bytes: int) -> dict[str, Any]:
    path = root_dir / Path(str(row["path"]))
    exists = path.exists()
    size = int(path.stat().st_size) if exists and path.is_file() else 0
    sha = ""
    if not exists:
        hash_status = "missing"
    elif not path.is_file():
        hash_status = "not_a_file"
    elif size > int(hash_max_bytes):
        hash_status = "skipped_large_file"
    else:
        sha = _sha256(path)
        hash_status = "hashed"
    return {
        "category": str(row.get("category", "")),
        "label": str(row.get("label", "")),
        "path": _portable_path(path),
        "required": bool(row.get("required", True)),
        "exists": bool(exists),
        "bytes": size,
        "hash_status": hash_status,
        "sha256": sha,
    }


def _strict_model_weight_records(root_dir: Path, hash_max_bytes: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted((root_dir / "artifacts/strictmask_validation_wtb_full").glob("wtb_bal_align_force_seed*/best_model.pt")):
        records.append(
            _file_record(
                root_dir,
                {
                    "category": "model_weights",
                    "label": f"Strict corrected-router checkpoint {path.parent.name}",
                    "path": str(path.relative_to(root_dir)) if path.is_relative_to(root_dir) else str(path),
                    "required": True,
                },
                hash_max_bytes,
            )
        )
    return records


def run_reproducibility_manifest(
    output_dir: Path | str,
    root_dir: Path | str = ".",
    hash_max_mb: float = 25.0,
    evidence_files: Iterable[dict[str, Any]] | None = None,
) -> Path:
    root_dir = Path(root_dir)
    output_dir = ensure_dir(output_dir)
    hash_max_bytes = int(float(hash_max_mb) * 1024 * 1024)
    rows = list(evidence_files) if evidence_files is not None else list(DEFAULT_REPRODUCIBILITY_FILES)
    file_records = [_file_record(root_dir, row, hash_max_bytes) for row in rows]
    file_records.extend(_strict_model_weight_records(root_dir, hash_max_bytes))
    file_df = pd.DataFrame(file_records)
    file_df.to_csv(output_dir / "reproducibility_file_manifest.csv", index=False)

    required = file_df[file_df["required"] == True] if not file_df.empty else file_df
    required_files_exist = bool(required["exists"].all()) if not required.empty else False
    strict_model_weight_count = int((file_df["category"] == "model_weights").sum()) if not file_df.empty else 0
    strict_model_weights_complete = strict_model_weight_count >= 5
    readiness_path = root_dir / "artifacts/science_readiness_dashboard_20260611/science_readiness_status.json"
    readiness = load_json(readiness_path) if readiness_path.exists() else {}
    complete_readiness_statuses = {
        "complete_candidate",
        "portable_submission_ready",
        "within_wtb_submission_ready",
        "within_wtb_submission_ready_external_nonportable",
        "within_wtb_submission_ready_external_not_citable",
    }
    active_gaps = str(readiness.get("overall_status", "")) not in {"", *complete_readiness_statuses}
    if not required_files_exist or not strict_model_weights_complete:
        status = "blocked_missing_reproducibility_inputs"
    elif active_gaps:
        status = "preliminary_active_experiment_gaps"
    else:
        status = "complete_ready_for_reproducibility_package"
    checks = {
        "required_files_exist": required_files_exist,
        "strict_model_weights_complete": strict_model_weights_complete,
        "environment_recorded": True,
        "strict_wtb_evidence_manifest_present": bool(
            (root_dir / "artifacts/strict_wtb_evidence_sources_20260609/strict_wtb_evidence_manifest.json").exists()
        ),
        "science_readiness_dashboard_present": bool(readiness_path.exists()),
        "active_experiment_gaps": active_gaps,
    }
    manifest = {
        "status": status,
        "checks": checks,
        "root_dir": str(root_dir),
        "hash_max_mb": float(hash_max_mb),
        "n_files": int(len(file_df)),
        "n_required_files": int(len(required)),
        "n_missing_required_files": int((~required["exists"]).sum()) if not required.empty else 0,
        "strict_model_weight_count": strict_model_weight_count,
        "environment": _environment(),
        "paths": {
            "file_manifest_csv": _portable_path(output_dir / "reproducibility_file_manifest.csv"),
            "readiness_dashboard": _portable_path(readiness_path),
        },
    }
    save_json(output_dir / "reproducibility_manifest.json", manifest)

    lines = [
        "# Reproducibility and compliance manifest",
        "",
        f"Status: `{status}`",
        "",
        "This manifest records the local evidence files, guards, queue scripts, model checkpoints, and execution environment needed for a reviewer-facing reproducibility package.",
        "",
        "## Checks",
        "",
    ]
    for key, value in checks.items():
        lines.append(f"- {key}: `{bool(value)}`")
    lines.extend(
        [
            "",
            "## Counts",
            "",
            f"- Files tracked: `{manifest['n_files']}`",
            f"- Required files: `{manifest['n_required_files']}`",
            f"- Missing required files: `{manifest['n_missing_required_files']}`",
            f"- Strict corrected-router checkpoints: `{strict_model_weight_count}` / `5`",
            "",
            "Large files may be recorded by size without SHA256 when they exceed the configured hash limit.",
            "",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return output_dir
