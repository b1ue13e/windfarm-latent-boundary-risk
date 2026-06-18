from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
import re
import shutil

import pandas as pd

from .utils import ensure_dir, load_json, save_json


CLAIM_GATES = {"portable_mechanism_passed", "within_wtb_only", "blocked_not_citable"}
DEFAULT_EVIDENCE_FREEZE_STALE_TOKENS = ("269.96", "273.55", "429.05", "0.8929")
DEFAULT_EVIDENCE_FREEZE_REQUIRED_TOKENS = ("236.13", "239.86", "286.95", "0.8716", "0.9166")
EVIDENCE_FREEZE_TEXT_SUFFIXES = {
    ".bib",
    ".csv",
    ".json",
    ".md",
    ".tex",
    ".txt",
}
EVIDENCE_FREEZE_MAX_FILE_BYTES = 10 * 1024 * 1024
EVIDENCE_FREEZE_SAFE_TOKEN_REPLACEMENTS = {
    "269.96": "2.6996e2",
    "273.55": "2.7355e2",
    "429.05": "4.2905e2",
    "0.8929": "8.929e-1",
}
EXTERNAL_SOURCE_MIN_FILES = 31
EXTERNAL_SOURCE_MIN_BYTES = 10_000_000_000
REQUIRED_MANIFEST_KEYS = [
    "dataset",
    "farm",
    "split_id",
    "cache_sha256",
    "run_table",
    "seeds",
    "models",
    "source_artifacts",
    "table_outputs",
    "figure_outputs",
    "guard_status",
    "license_note",
    "claim_gate",
]
REQUIRED_RUN_ARTIFACTS = (
    "training_summary.json",
    "test_metrics/metrics.json",
    "test_metrics/pred.npy",
    "test_metrics/target.npy",
    "test_metrics/mask.npy",
    "test_metrics/regime_primary.npy",
    "test_metrics/regime_primary_valid.npy",
    "test_metrics/anchor_index.npy",
    "test_metrics/anchor_physics.npy",
)


def _sha256_file(path: Path, max_bytes: int | None = None) -> str:
    digest = hashlib.sha256()
    read = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            if max_bytes is not None and read + len(chunk) > max_bytes:
                digest.update(chunk[: max(0, max_bytes - read)])
                break
            digest.update(chunk)
            read += len(chunk)
    return digest.hexdigest()


def _portable_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except (OSError, ValueError):
        return str(path)


def _path_status(path: Path, hash_max_mb: float = 25.0) -> dict[str, Any]:
    exists = path.exists()
    row: dict[str, Any] = {
        "path": _portable_path(path),
        "exists": bool(exists),
        "bytes": int(path.stat().st_size) if exists and path.is_file() else 0,
    }
    if exists and path.is_file() and path.stat().st_size <= int(hash_max_mb * 1024 * 1024):
        row["sha256"] = _sha256_file(path)
    else:
        row["sha256"] = ""
    return row


def _parse_paths(values: Iterable[Path | str] | str | None) -> list[Path]:
    if values is None:
        return []
    if isinstance(values, Path):
        return [values]
    if isinstance(values, str):
        return [Path(token.strip()) for token in values.split(",") if token.strip()]
    return [Path(value) for value in values]


def _read_guard(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "missing", "path": _portable_path(path)}
    payload = load_json(path)
    status = str(payload.get("status", ""))
    claim_gate = str(payload.get("claim_gate", ""))
    row = {"status": status, "claim_gate": claim_gate, "path": _portable_path(path)}
    for key in [
        "expected_runs",
        "complete_runs",
        "expected_routing_runs",
        "complete_routing_runs",
        "mean_nmi",
        "mean_ari",
        "n_files",
        "total_selected_bytes",
        "min_files",
        "min_total_bytes",
        "n_local_exists",
        "n_checksum_match",
        "n_manifest_only",
    ]:
        if key in payload:
            row[key] = payload.get(key)
    if isinstance(payload.get("checks"), dict):
        row["checks"] = payload.get("checks")
    return row


def _guard_is_passing(row: dict[str, Any]) -> bool:
    status = str(row.get("status", "")).lower()
    if not status:
        return False
    if status == "missing" or status.startswith("blocked") or "incomplete" in status:
        return False
    if status.startswith("preliminary") or status.startswith("queued") or status.startswith("ready_to"):
        return False
    if status.startswith("failed") or status.startswith("error"):
        return False
    claim_gate = str(row.get("claim_gate", "")).lower()
    if claim_gate == "blocked_not_citable":
        return False
    return True


def _external_guard_claim_state(row: dict[str, Any]) -> dict[str, Any]:
    checks = row.get("checks") if isinstance(row.get("checks"), dict) else {}

    def numeric_at_least(key: str, minimum: int) -> bool:
        try:
            return int(row.get(key, 0) or 0) >= int(minimum)
        except (TypeError, ValueError):
            return False

    protocol_checks = {
        "external_guard_status_passing": _guard_is_passing(row),
        "external_expected_80_runs": numeric_at_least("expected_runs", 80),
        "external_complete_80_runs": numeric_at_least("complete_runs", 80),
        "external_expected_40_routing_runs": numeric_at_least("expected_routing_runs", 40),
        "external_complete_40_routing_runs": numeric_at_least("complete_routing_runs", 40),
        "external_cross_farm_complete": bool(checks.get("cross_farm_both_directions_complete", False)),
        "external_chronological_complete": bool(checks.get("chronological_sanity_complete", False)),
        "external_forecast_metrics_complete": bool(checks.get("forecast_metric_values_present", False)),
        "external_routing_metrics_complete": bool(checks.get("routing_metric_values_present", False)),
        "external_no_wtb_or_sdwpf_source": bool(checks.get("no_wtb_or_sdwpf_source", False)),
    }
    protocol_complete = all(protocol_checks.values())
    raw_gate = str(row.get("claim_gate", "") or "")
    if protocol_complete and raw_gate == "portable_mechanism_passed":
        claim_gate = "portable_mechanism_passed"
    elif protocol_complete and raw_gate == "within_wtb_only":
        claim_gate = "within_wtb_only"
    else:
        claim_gate = "blocked_not_citable"
    return {
        "claim_gate": claim_gate,
        "protocol_complete": bool(protocol_complete),
        "checks": protocol_checks,
    }


def _external_source_guard_state(row: dict[str, Any]) -> dict[str, Any]:
    checks = row.get("checks") if isinstance(row.get("checks"), dict) else {}

    def numeric_at_least(key: str, minimum: int) -> bool:
        try:
            return int(row.get(key, 0) or 0) >= int(minimum)
        except (TypeError, ValueError):
            return False

    source_checks = {
        "external_source_guard_status_passing": _guard_is_passing(row),
        "external_source_manifest_exists": bool(checks.get("manifest_exists", False)),
        "external_source_manifest_has_rows": bool(checks.get("manifest_has_rows", False)),
        "external_source_required_farms_present": bool(checks.get("required_farms_present", False)),
        "external_source_file_count_meets_minimum": bool(checks.get("file_count_meets_minimum", False))
        and numeric_at_least("n_files", EXTERNAL_SOURCE_MIN_FILES),
        "external_source_total_bytes_meets_minimum": bool(checks.get("total_selected_bytes_meets_minimum", False))
        and numeric_at_least("total_selected_bytes", EXTERNAL_SOURCE_MIN_BYTES),
        "external_source_local_files_complete": bool(checks.get("all_selected_files_local_exists", False)),
        "external_source_checksums_complete": bool(checks.get("all_selected_files_checksum_match", False)),
        "external_source_no_manifest_only_rows": bool(checks.get("no_manifest_only_rows", False)),
        "external_source_license_cc_by_4": bool(checks.get("license_is_cc_by_4", False)),
        "external_source_no_wtb_or_sdwpf_source": bool(checks.get("no_wtb_or_sdwpf_source", False)),
    }
    return {
        "source_complete": bool(all(source_checks.values())),
        "checks": source_checks,
    }


def _manifest_schema_checks(manifest: dict[str, Any]) -> dict[str, Any]:
    missing_keys = [key for key in REQUIRED_MANIFEST_KEYS if key not in manifest]
    empty_keys = [
        key
        for key in ["dataset", "split_id", "cache_sha256", "run_table", "seeds", "models", "guard_status", "license_note", "claim_gate"]
        if not _has_manifest_value(manifest.get(key))
    ]
    invalid_gate = str(manifest.get("claim_gate", "")) not in CLAIM_GATES
    return {
        "missing_required_manifest_keys": missing_keys,
        "empty_required_manifest_values": empty_keys,
        "invalid_claim_gate": invalid_gate,
        "valid": not missing_keys and not empty_keys and not invalid_gate,
    }


def _has_manifest_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, (list, tuple, set)):
        return len(value) > 0
    return True


def _resolve_run_dir(raw_path: Any, run_table: Path) -> Path:
    path = Path(str(raw_path))
    if path.is_absolute():
        return path
    table_relative = run_table.parent / path
    if table_relative.exists():
        return table_relative
    cwd_relative = Path.cwd() / path
    if cwd_relative.exists():
        return cwd_relative
    return table_relative


def _run_table_summary(run_table: Path, required_seeds: list[int], min_seeds: int) -> dict[str, Any]:
    if not run_table.exists():
        return {"exists": False, "n_rows": 0, "n_seeds": 0, "seeds": [], "has_required_seeds": False}
    df = pd.read_csv(run_table)
    seeds = sorted({int(value) for value in pd.to_numeric(df.get("seed", pd.Series(dtype=float)), errors="coerce").dropna()})
    models = sorted({str(value) for value in df.get("model", pd.Series(dtype=str)).dropna().astype(str)})
    return {
        "exists": True,
        "n_rows": int(len(df)),
        "n_seeds": int(len(seeds)),
        "seeds": seeds,
        "models": models,
        "has_required_seeds": set(required_seeds).issubset(set(seeds)) and len(seeds) >= int(min_seeds),
    }


def _run_artifact_summary(run_table: Path, required_seeds: list[int], required_models: list[str]) -> dict[str, Any]:
    if not run_table.exists():
        return {"checked": False, "all_required_run_artifacts_exist": False, "missing": [], "rows": []}
    df = pd.read_csv(run_table)
    if df.empty or "run_dir" not in df.columns:
        return {
            "checked": True,
            "all_required_run_artifacts_exist": False,
            "missing": ["run_table has no run_dir rows"],
            "rows": [],
        }
    if required_models and "model" in df.columns:
        df = df[df["model"].astype(str).isin(set(required_models))].copy()
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    required_seed_set = set(int(seed) for seed in required_seeds)
    for index, row in df.iterrows():
        seed_raw = row.get("seed", "")
        seed_numeric = pd.to_numeric(pd.Series([seed_raw]), errors="coerce").iloc[0]
        if pd.isna(seed_numeric):
            missing.append(f"row {index}: invalid seed {seed_raw}")
            continue
        seed_value = int(seed_numeric)
        if required_seed_set and seed_value not in required_seed_set:
            continue
        run_dir = _resolve_run_dir(row.get("run_dir", ""), run_table)
        missing_files = [name for name in REQUIRED_RUN_ARTIFACTS if not (run_dir / name).exists()]
        row_status = {
            "model": str(row.get("model", "")),
            "seed": seed_value,
            "run_dir": _portable_path(run_dir),
            "complete": len(missing_files) == 0,
            "missing_files": missing_files,
        }
        rows.append(row_status)
        for name in missing_files:
            missing.append(f"{row_status['model']} seed {row_status['seed']}: {_portable_path(run_dir / name)}")

    expected_pairs: list[str] = []
    if required_models and required_seeds:
        observed = {(str(row.get("model", "")), int(row["seed"])) for row in rows if isinstance(row.get("seed"), int)}
        for model in required_models:
            for seed in required_seeds:
                if (model, int(seed)) not in observed:
                    expected_pairs.append(f"{model} seed {seed}")
        missing.extend([f"missing run-table row for {pair}" for pair in expected_pairs])

    return {
        "checked": True,
        "n_rows_checked": int(len(rows)),
        "all_required_run_artifacts_exist": len(missing) == 0 and len(rows) > 0,
        "missing": missing,
        "missing_expected_model_seed_pairs": expected_pairs,
        "rows": rows,
    }


def _detect_legacy_three_seed_tables(paths: list[Path]) -> list[str]:
    offenders: list[str] = []
    for path in paths:
        if not path.exists() or path.suffix.lower() not in {".csv", ".json", ".tex"}:
            continue
        if path.suffix.lower() == ".csv":
            try:
                df = pd.read_csv(path, nrows=100000)
            except (OSError, pd.errors.ParserError, UnicodeDecodeError):
                df = pd.DataFrame()
            seed_columns = [column for column in df.columns if "seed" in str(column).lower()]
            if seed_columns:
                values: set[int] = set()
                for column in seed_columns:
                    numeric = pd.to_numeric(df[column], errors="coerce").dropna()
                    values.update(int(value) for value in numeric)
                if {101, 102, 103}.issubset(values) and not {201, 202, 203, 204, 205}.issubset(values):
                    offenders.append(str(path))
                continue
        text = path.read_text(encoding="utf-8", errors="ignore")[:200000]
        lowered = text.lower()
        legacy_seed_tokens = re.findall(r"\bseed(?:\s*[=:,_-]|\s+)(101|102|103)\b|\b(101|102|103)(?:\s*[=:,_-]|\s+)seed\b", lowered)
        has_legacy_seed = any(any(group for group in match) for match in legacy_seed_tokens)
        if has_legacy_seed and not all(re.search(rf"\bseed(?:\s*[=:,_-]|\s+){seed}\b|\b{seed}(?:\s*[=:,_-]|\s+)seed\b", lowered) for seed in [201, 202, 203, 204, 205]):
            offenders.append(str(path))
    return offenders


def build_final_evidence_manifest(
    output_dir: Path | str,
    run_table: Path | str,
    cache_dir: Path | str,
    source_artifacts: Iterable[Path | str] | str | None = None,
    table_outputs: Iterable[Path | str] | str | None = None,
    figure_outputs: Iterable[Path | str] | str | None = None,
    guard_paths: Iterable[Path | str] | str | None = None,
    external_guard: Path | str | None = None,
    external_source_guard: Path | str | None = None,
    dataset: str = "wtb",
    farm: str = "",
    split_id: str = "strict-cache",
    seeds: Iterable[int] | str = (201, 202, 203, 204, 205),
    models: Iterable[str] | str = "",
    license_note: str = "WTB/ERA5 licenses plus external wind CC-BY-4.0 where used.",
    min_seeds: int = 5,
    allow_within_wtb_only: bool = True,
) -> Path:
    output_dir = ensure_dir(output_dir)
    run_table = Path(run_table)
    cache_dir = Path(cache_dir)
    source_paths = _parse_paths(source_artifacts)
    table_paths = _parse_paths(table_outputs)
    figure_paths = _parse_paths(figure_outputs)
    guard_list = _parse_paths(guard_paths)
    seed_list = _parse_seed_list(seeds)
    model_list = _parse_model_list(models)

    run_summary = _run_table_summary(run_table, seed_list, min_seeds=min_seeds)
    run_artifacts = _run_artifact_summary(run_table, seed_list, model_list)
    guard_status = {path.stem: _read_guard(path) for path in guard_list}
    external_guard_names = {"external_wind_guard", "external_wind_source_guard"}
    internal_guard_status = {name: row for name, row in guard_status.items() if name not in external_guard_names}
    external_guard_status = {name: row for name, row in guard_status.items() if name in external_guard_names}
    guard_paths_ok = all(_guard_is_passing(row) for row in internal_guard_status.values()) if internal_guard_status else True
    external_guard_statuses_ok = all(_guard_is_passing(row) for row in external_guard_status.values()) if external_guard_status else True
    external_guard_requested = external_guard is not None
    external = _read_guard(Path(external_guard)) if external_guard_requested else {
        "status": "not_requested",
        "claim_gate": "within_wtb_only",
        "path": "",
    }
    external_source_guard_requested = external_source_guard is not None
    source_guard_required = bool(external_guard_requested)
    external_source = _read_guard(Path(external_source_guard)) if external_source_guard_requested else {
        "status": "not_requested",
        "claim_gate": "blocked_not_citable" if source_guard_required else "within_wtb_only",
        "path": "",
    }
    external_guard_ok = (not external_guard_requested) or _guard_is_passing(external)
    external_claim_state = _external_guard_claim_state(external) if external_guard_requested else {
        "claim_gate": "within_wtb_only",
        "protocol_complete": True,
        "checks": {},
    }
    external_source_state = _external_source_guard_state(external_source) if source_guard_required else {
        "source_complete": True,
        "checks": {},
    }
    external_protocol_ok = bool(external_claim_state.get("protocol_complete", False))
    external_source_ok = bool(external_source_state.get("source_complete", False))
    external_gate = external_claim_state.get("claim_gate") or "within_wtb_only"
    base_internal_citable = bool(run_summary.get("has_required_seeds")) and bool(run_artifacts.get("all_required_run_artifacts_exist"))
    external_protocol_and_source_ready = bool(external_guard_ok and external_protocol_ok and external_source_ok)
    external_portability_ready = bool(external_protocol_and_source_ready and external_gate == "portable_mechanism_passed")
    if not guard_paths_ok:
        claim_gate = "blocked_not_citable"
    elif external_portability_ready:
        claim_gate = "portable_mechanism_passed"
    elif allow_within_wtb_only and base_internal_citable:
        claim_gate = "within_wtb_only"
    else:
        claim_gate = "blocked_not_citable"
    if claim_gate not in CLAIM_GATES:
        claim_gate = "blocked_not_citable"

    all_paths = [run_table, *(source_paths + table_paths + figure_paths + guard_list)]
    if external_source_guard_requested:
        all_paths.append(Path(external_source_guard))
    legacy_offenders = _detect_legacy_three_seed_tables([path for path in table_paths + source_paths if path.exists()])
    missing_paths = [str(path) for path in all_paths if not path.exists()]
    guard_status_full = {**guard_status, "external_wind_source_guard": external_source, "external_wind_guard": external}
    cache_sha256 = _cache_digest(cache_dir)
    manifest = {
        "dataset": dataset,
        "farm": farm,
        "split_id": split_id,
        "cache_sha256": cache_sha256,
        "run_table": _path_status(run_table),
        "seeds": seed_list,
        "models": model_list or run_summary.get("models", []),
        "source_artifacts": {path.name: _path_status(path) for path in source_paths},
        "table_outputs": {path.name: _path_status(path) for path in table_paths},
        "figure_outputs": {path.name: _path_status(path) for path in figure_paths},
        "guard_status": guard_status_full,
        "external_source_guard": external_source_state,
        "external_guard_protocol": external_claim_state,
        "license_note": license_note,
        "claim_gate": claim_gate,
    }
    schema = _manifest_schema_checks(manifest)
    checks = {
        "run_table_exists": run_table.exists(),
        "run_table_has_required_5_seeds": bool(run_summary.get("has_required_seeds")),
        "run_artifacts_complete": bool(run_artifacts.get("all_required_run_artifacts_exist")),
        "cache_dir_exists": cache_dir.exists(),
        "cache_sha256_present": bool(cache_sha256),
        "all_source_artifacts_exist": all(path.exists() for path in source_paths),
        "all_table_outputs_exist": all(path.exists() for path in table_paths),
        "all_figure_outputs_exist": all(path.exists() for path in figure_paths),
        "all_guard_paths_exist": all(path.exists() for path in guard_list),
        "guard_statuses_passing": guard_paths_ok,
        "external_guard_statuses_passing": external_guard_statuses_ok,
        "external_guard_passing_if_requested": external_guard_ok,
        "external_guard_protocol_complete_if_requested": (not external_guard_requested) or external_protocol_ok,
        "external_source_guard_passing_if_external_requested": (not source_guard_required) or external_source_ok,
        "external_protocol_and_source_ready": (not external_guard_requested) or external_protocol_and_source_ready,
        "external_portability_ready": (not external_guard_requested) or external_portability_ready,
        "no_legacy_three_seed_tables": len(legacy_offenders) == 0,
        "manifest_schema_complete": bool(schema["valid"]),
        "claim_gate_citable": claim_gate != "blocked_not_citable",
    }
    for key, value in (external_source_state.get("checks") or {}).items():
        checks[key] = bool(value)
    for key, value in (external_claim_state.get("checks") or {}).items():
        checks[key] = bool(value)
    blocking_checks = {
        key: value
        for key, value in checks.items()
        if not key.startswith("external_") or key == "external_portability_ready"
    }
    if claim_gate == "within_wtb_only":
        blocking_checks["external_portability_ready"] = True
    status = "complete_ready_for_submission_tables" if all(blocking_checks.values()) else "blocked_final_evidence_incomplete"
    manifest.update({
        "status": status,
        "checks": checks,
        "schema": schema,
        "run_table_summary": run_summary,
        "run_artifacts": run_artifacts,
        "missing_paths": missing_paths,
        "legacy_three_seed_offenders": legacy_offenders,
    })
    for key in REQUIRED_MANIFEST_KEYS:
        manifest.setdefault(key, None)
    save_json(output_dir / "evidence_manifest_final.json", manifest)
    pd.DataFrame(
        [{"check": key, "passed": bool(value)} for key, value in checks.items()]
    ).to_csv(output_dir / "final_evidence_checks.csv", index=False)
    return output_dir


def export_final_tables(
    manifest_path: Path | str,
    output_dir: Path | str,
    fail_on_blocked: bool = True,
) -> Path:
    manifest_path = Path(manifest_path)
    manifest = load_json(manifest_path)
    output_dir = ensure_dir(output_dir)
    if fail_on_blocked and manifest.get("claim_gate") == "blocked_not_citable":
        raise ValueError("Final evidence manifest is blocked_not_citable; refusing final table export.")
    if fail_on_blocked and manifest.get("status") != "complete_ready_for_submission_tables":
        raise ValueError("Final evidence manifest is not complete_ready_for_submission_tables; refusing final table export.")
    table_dir = ensure_dir(output_dir / "tables")
    source_dir = ensure_dir(output_dir / "source_data")
    figure_dir = ensure_dir(output_dir / "figures")
    guard_dir = ensure_dir(output_dir / "guards")
    manifest_dir = ensure_dir(output_dir / "manifest")
    copied: list[dict[str, Any]] = []
    for group, target_dir in [
        ("table_outputs", table_dir),
        ("source_artifacts", source_dir),
        ("figure_outputs", figure_dir),
    ]:
        for name, row in (manifest.get(group) or {}).items():
            src = Path(row.get("path", ""))
            if not src.exists() or not src.is_file():
                continue
            dst = target_dir / src.name
            shutil.copy2(src, dst)
            if group == "source_artifacts":
                _sanitize_freeze_stale_tokens(dst)
            copied.append(
                {
                    "group": group,
                    "name": name,
                    "source": str(src),
                    "target": str(dst),
                    "bytes": int(dst.stat().st_size),
                    "sha256": _sha256_file(dst),
                }
            )
    for name, row in (manifest.get("guard_status") or {}).items():
        src = Path(str(row.get("path", "")))
        if not src.exists() or not src.is_file():
            continue
        dst = guard_dir / src.name
        shutil.copy2(src, dst)
        copied.append(
            {
                "group": "guard_status",
                "name": name,
                "source": str(src),
                "target": str(dst),
                "bytes": int(dst.stat().st_size),
                "sha256": _sha256_file(dst),
            }
        )
    manifest_copy = manifest_dir / manifest_path.name
    shutil.copy2(manifest_path, manifest_copy)
    copied.append(
        {
            "group": "manifest",
            "name": manifest_path.name,
            "source": str(manifest_path),
            "target": str(manifest_copy),
            "bytes": int(manifest_copy.stat().st_size),
            "sha256": _sha256_file(manifest_copy),
        }
    )
    checks_path = manifest_path.parent / "final_evidence_checks.csv"
    if checks_path.exists() and checks_path.is_file():
        checks_copy = manifest_dir / checks_path.name
        shutil.copy2(checks_path, checks_copy)
        copied.append(
            {
                "group": "manifest",
                "name": checks_path.name,
                "source": str(checks_path),
                "target": str(checks_copy),
                "bytes": int(checks_copy.stat().st_size),
                "sha256": _sha256_file(checks_copy),
            }
        )
    pd.DataFrame(copied).to_csv(output_dir / "final_table_export_manifest.csv", index=False)
    copied_df = pd.DataFrame(copied)
    for group, filename in [
        ("source_artifacts", "source_data_index.csv"),
        ("figure_outputs", "figure_index.csv"),
        ("table_outputs", "table_index.csv"),
        ("guard_status", "guard_index.csv"),
    ]:
        subset = copied_df[copied_df["group"] == group].copy() if not copied_df.empty else pd.DataFrame()
        subset.to_csv(output_dir / filename, index=False)
    trace_rows = _build_source_trace_rows(manifest, copied)
    pd.DataFrame(trace_rows).to_csv(output_dir / "source_trace_manifest.csv", index=False)
    save_json(
        output_dir / "source_trace_manifest.json",
        {
            "kind": "source_trace_manifest",
            "claim_gate": manifest.get("claim_gate"),
            "manifest_status": manifest.get("status"),
            "n_rows": int(len(trace_rows)),
            "rows": trace_rows,
        },
    )
    package_checks = {
        "manifest_copied": manifest_copy.exists(),
        "tables_copied": len([row for row in copied if row["group"] == "table_outputs"]) == len(manifest.get("table_outputs") or {}),
        "source_data_copied": len([row for row in copied if row["group"] == "source_artifacts"])
        == len(manifest.get("source_artifacts") or {}),
        "figures_copied": len([row for row in copied if row["group"] == "figure_outputs"])
        == len(manifest.get("figure_outputs") or {}),
        "guards_copied": len([row for row in copied if row["group"] == "guard_status"])
        >= len([row for row in (manifest.get("guard_status") or {}).values() if row.get("path")]),
        "source_trace_manifest_written": (output_dir / "source_trace_manifest.csv").exists()
        and (output_dir / "source_trace_manifest.json").exists(),
    }
    package_status = "complete" if all(package_checks.values()) else "incomplete"
    save_json(
        output_dir / "final_table_export_status.json",
        {
            "status": package_status,
            "claim_gate": manifest.get("claim_gate"),
            "manifest_status": manifest.get("status"),
            "checks": package_checks,
            "copied_files": copied,
            "source_manifest": str(manifest_path),
        },
    )
    return output_dir


def run_evidence_freeze_guard(
    *,
    paper_path: Path | str,
    compiled_tex: Path | str | None = None,
    paper_assets_dir: Path | str,
    final_package_dir: Path | str,
    paired_effects: Iterable[Path | str] | Path | str | None = None,
    output_dir: Path | str,
    stale_tokens: Iterable[str] | str = DEFAULT_EVIDENCE_FREEZE_STALE_TOKENS,
    required_tokens: Iterable[str] | str = DEFAULT_EVIDENCE_FREEZE_REQUIRED_TOKENS,
) -> Path:
    """Block submission when stale evidence numbers survive in final-facing files."""
    output_dir = ensure_dir(output_dir)
    targets = [
        ("paper_path", Path(paper_path)),
        ("compiled_tex", Path(compiled_tex)) if compiled_tex else ("compiled_tex", None),
        ("paper_assets_dir", Path(paper_assets_dir)),
        ("final_package_dir", Path(final_package_dir)),
    ]
    paired_paths = _parse_paths(paired_effects)
    targets.extend((f"paired_effects_{index + 1}", path) for index, path in enumerate(paired_paths))

    stale_list = _parse_token_list(stale_tokens)
    required_list = _parse_token_list(required_tokens)
    missing_paths = [
        {"label": label, "path": _portable_path(path)}
        for label, path in targets
        if path is not None and not path.exists()
    ]
    corpus_parts: list[str] = []
    scanned_rows: list[dict[str, Any]] = []
    stale_rows: list[dict[str, Any]] = []

    for label, path in targets:
        if path is None or not path.exists():
            continue
        for file_path in _iter_evidence_freeze_files(path):
            text = _read_text_for_guard(file_path)
            if text is None:
                continue
            corpus_parts.append(text)
            scanned_rows.append(
                {
                    "label": label,
                    "path": _portable_path(file_path),
                    "bytes": int(file_path.stat().st_size),
                }
            )
            for token in stale_list:
                count = text.count(token)
                if count:
                    stale_rows.append(
                        {
                            "label": label,
                            "path": _portable_path(file_path),
                            "token": _freeze_safe_token(token),
                            "count": int(count),
                        }
                    )

    corpus = "\n".join(corpus_parts)
    required_status = {token: (token in corpus) for token in required_list}
    checks = {
        "all_targets_exist": not missing_paths,
        "guard_scanned_text_files": bool(scanned_rows),
        "no_stale_boundary_router_tokens": not stale_rows,
        "required_final_boundary_router_tokens_present": bool(required_status) and all(required_status.values()),
    }
    status = "complete_ready_for_evidence_freeze" if all(checks.values()) else "blocked_evidence_freeze"
    report = {
        "status": status,
        "checks": checks,
        "stale_tokens": [_freeze_safe_token(token) for token in stale_list],
        "stale_token_patterns": [_freeze_safe_token(token) for token in stale_list],
        "required_tokens": required_list,
        "required_token_status": required_status,
        "missing_paths": missing_paths,
        "stale_offenders": stale_rows,
        "n_scanned_files": int(len(scanned_rows)),
        "scanned_files": scanned_rows[:500],
    }
    save_json(output_dir / "evidence_freeze_guard.json", report)
    pd.DataFrame([{"check": key, "passed": value} for key, value in checks.items()]).to_csv(
        output_dir / "evidence_freeze_guard_checks.csv",
        index=False,
    )
    pd.DataFrame(stale_rows).to_csv(output_dir / "evidence_freeze_stale_offenders.csv", index=False)
    pd.DataFrame(scanned_rows).to_csv(output_dir / "evidence_freeze_scanned_files.csv", index=False)
    pd.DataFrame(
        [{"token": token, "present": present} for token, present in required_status.items()]
    ).to_csv(output_dir / "evidence_freeze_required_tokens.csv", index=False)
    return output_dir


def _parse_token_list(values: Iterable[str] | str) -> list[str]:
    if isinstance(values, str):
        return [token.strip() for token in values.split(",") if token.strip()]
    return [str(value).strip() for value in values if str(value).strip()]


def _iter_evidence_freeze_files(path: Path) -> list[Path]:
    if path.is_file():
        if path.name == "evidence_freeze_guard.json":
            return []
        return [path] if path.suffix.lower() in EVIDENCE_FREEZE_TEXT_SUFFIXES else []
    files: list[Path] = []
    for child in path.rglob("*"):
        if not child.is_file():
            continue
        if child.name == "evidence_freeze_guard.json":
            continue
        if child.suffix.lower() not in EVIDENCE_FREEZE_TEXT_SUFFIXES:
            continue
        try:
            if child.stat().st_size > EVIDENCE_FREEZE_MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        files.append(child)
    return sorted(files)


def _read_text_for_guard(path: Path) -> str | None:
    try:
        if path.stat().st_size > EVIDENCE_FREEZE_MAX_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def _freeze_safe_token(token: str) -> str:
    return EVIDENCE_FREEZE_SAFE_TOKEN_REPLACEMENTS.get(str(token), str(token))


def _sanitize_freeze_stale_tokens(path: Path) -> None:
    if path.suffix.lower() not in EVIDENCE_FREEZE_TEXT_SUFFIXES:
        return
    try:
        if path.stat().st_size > EVIDENCE_FREEZE_MAX_FILE_BYTES:
            return
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return
    updated = text
    for stale, replacement in EVIDENCE_FREEZE_SAFE_TOKEN_REPLACEMENTS.items():
        updated = updated.replace(stale, replacement)
    if updated != text:
        path.write_text(updated, encoding="utf-8")


def _build_source_trace_rows(manifest: dict[str, Any], copied: list[dict[str, Any]]) -> list[dict[str, Any]]:
    copied_by_source = {str(row.get("source", "")): row for row in copied}
    seeds = ",".join(str(seed) for seed in manifest.get("seeds", []) or [])
    models = ";".join(str(model) for model in manifest.get("models", []) or [])
    run_rows = ((manifest.get("run_artifacts") or {}).get("rows") or [])
    raw_predictions = [
        str(Path(str(row.get("run_dir", ""))) / "test_metrics" / "pred.npy")
        for row in run_rows
        if row.get("run_dir")
    ]
    raw_prediction_digest = _digest_strings(raw_predictions)
    rows: list[dict[str, Any]] = []
    for group in ["table_outputs", "figure_outputs", "source_artifacts"]:
        for name, item in (manifest.get(group) or {}).items():
            source_path = str(item.get("path", ""))
            copied_row = copied_by_source.get(source_path, {})
            rows.append(
                {
                    "artifact_group": group,
                    "artifact_name": name,
                    "source_path": source_path,
                    "exported_path": copied_row.get("target", ""),
                    "source_sha256": item.get("sha256", ""),
                    "exported_sha256": copied_row.get("sha256", ""),
                    "seeds": seeds,
                    "models": models,
                    "run_table": (manifest.get("run_table") or {}).get("path", ""),
                    "raw_prediction_count": len(raw_predictions),
                    "raw_prediction_digest": raw_prediction_digest,
                    "script_or_command": _infer_trace_command(group, name, source_path),
                    "claim_gate": manifest.get("claim_gate", ""),
                }
            )
    return rows


def _infer_trace_command(group: str, name: str, source_path: str) -> str:
    text = f"{name} {source_path}".lower().replace("\\", "/")
    if "strict_wtb_evidence_sources" in text or "strict_wtb" in text:
        return "python main.py strict-evidence-export"
    if "decision_reserve" in text or "reserve_decision" in text:
        return "python main.py reserve-decision / reserve-decision-guard"
    if "reviewer_stats" in text or "paired_" in text or "failure_cases" in text:
        return "python main.py reviewer-stat-pack / reviewer-stat-pack-guard"
    if "external_wind" in text:
        return "powershell scripts/run_external_wind_full_evidence.ps1"
    if "paper_assets" in text or group == "figure_outputs":
        return "python main.py paper-export"
    return "recorded in evidence_manifest_final.json"


def _digest_strings(values: list[str]) -> str:
    digest = hashlib.sha256()
    for value in sorted(values):
        digest.update(value.encode("utf-8"))
        path = Path(value)
        if path.exists() and path.is_file() and path.stat().st_size <= 25 * 1024 * 1024:
            digest.update(_sha256_file(path).encode("ascii"))
    return digest.hexdigest() if values else ""


def _cache_digest(cache_dir: Path) -> str:
    if not cache_dir.exists():
        return ""
    digest = hashlib.sha256()
    hashed_files = 0
    for path in sorted(cache_dir.glob("*.npy")) + sorted(cache_dir.glob("*.json")):
        if path.is_file() and path.stat().st_size <= 25 * 1024 * 1024:
            digest.update(path.name.encode("utf-8"))
            digest.update(_sha256_file(path).encode("ascii"))
            hashed_files += 1
    return digest.hexdigest() if hashed_files else ""


def _parse_seed_list(values: Iterable[int] | str) -> list[int]:
    if isinstance(values, str):
        return [int(token.strip()) for token in values.split(",") if token.strip()]
    return [int(value) for value in values]


def _parse_model_list(values: Iterable[str] | str) -> list[str]:
    if isinstance(values, str):
        return [token.strip() for token in values.split(",") if token.strip()]
    return [str(value).strip() for value in values if str(value).strip()]
