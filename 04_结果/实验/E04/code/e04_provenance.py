"""Execution/output binding for the E04 selector.

A scheduler state or an output file's existence is not an execution receipt.
This module binds the declared inputs, output manifest, and process outcome in
one receipt that the selector verifies before reading policy arrays.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Iterable, Mapping, Sequence

SCHEMA_VERSION = "E04-receipt-v1"
PLAN_NAME = "e04_execution_plan.json"
MANIFEST_NAME = "e04_output_manifest.json"
RECEIPT_NAME = "e04_execution_receipt.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _write_json(path: Path, value: object) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(_json_bytes(value))
    temporary.replace(path)


def _record(path: Path, *, root: Path | None = None, role: str | None = None) -> dict:
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    record = {
        "path": path.relative_to(root).as_posix() if root is not None else str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    if role is not None:
        record["role"] = role
    return record


def _resolve_record_path(record: Mapping[str, object], root: Path) -> Path:
    value = Path(str(record["path"]))
    candidate = value if value.is_absolute() else root / value
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"Provenance path escapes bundle: {record['path']}")
    return resolved


def write_output_manifest(bundle_dir: Path, outputs: Iterable[Path], *, name: str = MANIFEST_NAME) -> Path:
    """Write a manifest for the complete declared output set.

    Every output must already exist and live under ``bundle_dir``. The manifest
    excludes itself and is written before the execution receipt.
    """
    bundle = Path(bundle_dir).resolve()
    bundle.mkdir(parents=True, exist_ok=True)
    records = []
    seen: set[str] = set()
    for output in outputs:
        path = Path(output).resolve()
        if not path.is_relative_to(bundle):
            raise ValueError(f"E04 output is outside bundle: {path}")
        rel = path.relative_to(bundle).as_posix()
        if rel in seen:
            raise ValueError(f"Duplicate E04 output: {rel}")
        seen.add(rel)
        records.append(_record(path, root=bundle))
    if not records:
        raise ValueError("E04 output manifest cannot be empty")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "bundle_root": ".",
        "files": sorted(records, key=lambda item: item["path"]),
    }
    path = bundle / name
    _write_json(path, manifest)
    return path


def _input_records(inputs: Sequence[tuple[str, Path]]) -> list[dict]:
    return [_record(path, role=role) for role, path in inputs]


def write_execution_plan(
    bundle_dir: Path,
    *,
    argv: Sequence[str],
    inputs: Sequence[tuple[str, Path]],
    output_names: Iterable[str],
    git_commit: str | None = None,
    working_dir: Path | None = None,
    metadata: Mapping[str, object] | None = None,
    name: str = PLAN_NAME,
) -> Path:
    """Freeze command, input bytes, and expected output names before execution."""
    bundle = Path(bundle_dir).resolve()
    plan = {
        "schema_version": SCHEMA_VERSION,
        "argv": [str(item) for item in argv],
        "git_commit": git_commit,
        "working_dir": str(Path(working_dir).resolve()) if working_dir is not None else None,
        "inputs": _input_records(inputs),
        "expected_outputs": sorted(str(item).replace("\\", "/") for item in output_names),
        "metadata": dict(metadata or {}),
    }
    path = bundle / name
    _write_json(path, plan)
    return path


def write_execution_receipt(
    bundle_dir: Path,
    *,
    argv: Sequence[str],
    inputs: Sequence[tuple[str, Path]],
    output_manifest: Path,
    exit_code: int = 0,
    status: str = "EXECUTED",
    git_commit: str | None = None,
    metadata: Mapping[str, object] | None = None,
    plan_path: Path | None = None,
    name: str = RECEIPT_NAME,
) -> Path:
    """Write the process receipt after a successful command has materialized outputs."""
    bundle = Path(bundle_dir).resolve()
    manifest = Path(output_manifest).resolve()
    if not manifest.is_file() or not manifest.is_relative_to(bundle):
        raise ValueError("Output manifest must be an existing file inside the E04 bundle")
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    if manifest_data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported E04 output manifest schema")
    outputs = manifest_data.get("files")
    if not isinstance(outputs, list) or not outputs:
        raise ValueError("E04 output manifest has no files")
    if status == "EXECUTED" and exit_code != 0:
        raise ValueError("EXECUTED receipt requires exit_code=0")
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "exit_code": int(exit_code),
        "argv": [str(item) for item in argv],
        "git_commit": git_commit,
        "pid": os.getpid(),
        "inputs": _input_records(inputs),
        "output_manifest": _record(manifest, root=bundle),
        "outputs": outputs,
        "metadata": dict(metadata or {}),
    }
    if plan_path is not None:
        plan = Path(plan_path).resolve()
        if not plan.is_file() or not plan.is_relative_to(bundle):
            raise ValueError("Execution plan must be an existing file inside the E04 bundle")
        receipt["execution_plan"] = _record(plan, root=bundle)
    path = bundle / name
    _write_json(path, receipt)
    return path


def _verify_file_record(record: Mapping[str, object], *, root: Path, allow_external: bool = False) -> Path:
    value = Path(str(record["path"]))
    path = value if value.is_absolute() else root / value
    path = path.resolve()
    if not allow_external and not path.is_relative_to(root.resolve()):
        raise ValueError(f"Provenance path escapes bundle: {record['path']}")
    if not path.is_file():
        raise ValueError(f"Evidence missing: {path}")
    if path.stat().st_size != int(record["bytes"]) or sha256_file(path) != record["sha256"]:
        raise ValueError(f"Evidence hash mismatch: {path}")
    return path


def verify_e04_receipt(
    receipt_path: Path,
    *,
    preregistration: Path | None = None,
    expected_output_names: Iterable[str] | None = None,
) -> dict:
    """Verify process status, input binding, manifest binding, and all outputs."""
    receipt_path = Path(receipt_path).resolve()
    if not receipt_path.is_file():
        raise ValueError(f"E04 execution receipt missing: {receipt_path}")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported E04 execution receipt schema")
    if receipt.get("status") != "EXECUTED" or receipt.get("exit_code") != 0:
        raise ValueError("E04 receipt is not a successful execution receipt")
    bundle = receipt_path.parent

    plan_record = receipt.get("execution_plan")
    if not isinstance(plan_record, dict):
        raise ValueError("E04 receipt has no immutable execution plan")
    plan_path = _verify_file_record(plan_record, root=bundle)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported E04 execution plan schema")
    if plan.get("argv") != receipt.get("argv") or plan.get("inputs") != receipt.get("inputs"):
        raise ValueError("Receipt command/input binding differs from the pre-execution plan")
    expected_plan_outputs = sorted(str(item).replace("\\", "/") for item in plan.get("expected_outputs", []))
    if not expected_plan_outputs:
        raise ValueError("Execution plan has no expected outputs")

    input_records = receipt.get("inputs")
    if not isinstance(input_records, list) or not input_records:
        raise ValueError("E04 receipt has no input records")
    prereg_records = [item for item in input_records if item.get("role") == "preregistration"]
    if preregistration is not None:
        if len(prereg_records) != 1:
            raise ValueError("E04 receipt must contain exactly one preregistration input")
        expected = _record(Path(preregistration))
        actual = prereg_records[0]
        if actual["bytes"] != expected["bytes"] or actual["sha256"] != expected["sha256"]:
            raise ValueError("Preregistration hash does not match the execution receipt")
    for record in input_records:
        _verify_file_record(record, root=bundle, allow_external=True)

    manifest_record = receipt.get("output_manifest")
    if not isinstance(manifest_record, dict):
        raise ValueError("E04 receipt has no output manifest record")
    manifest_path = _verify_file_record(manifest_record, root=bundle)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported E04 output manifest schema")
    manifest_files = manifest.get("files")
    receipt_outputs = receipt.get("outputs")
    if not isinstance(manifest_files, list) or not isinstance(receipt_outputs, list):
        raise ValueError("E04 receipt/manifest output records are malformed")
    if manifest_files != receipt_outputs:
        raise ValueError("Receipt outputs differ from the bound output manifest")
    for record in manifest_files:
        _verify_file_record(record, root=bundle)

    actual = sorted(str(record["path"]) for record in manifest_files)
    if actual != expected_plan_outputs:
        raise ValueError(f"E04 output set differs from pre-execution plan: expected {expected_plan_outputs}, got {actual}")
    if expected_output_names is not None:
        expected = sorted(str(name).replace("\\", "/") for name in expected_output_names)
        if actual != expected:
            raise ValueError(f"E04 output set mismatch: expected {expected}, got {actual}")

    return {
        "receipt": receipt,
        "bundle_root": str(bundle),
        "receipt_path": str(receipt_path),
        "receipt_sha256": sha256_file(receipt_path),
        "execution_plan_path": str(plan_path),
        "execution_plan_sha256": sha256_file(plan_path),
        "output_manifest_path": str(manifest_path),
        "output_manifest_sha256": sha256_file(manifest_path),
        "outputs": manifest_files,
    }


def provenance_for_selector(verified: Mapping[str, object], selector_script: Path) -> dict:
    """Create a compact provenance block for the selector result JSON."""
    return {
        "execution_receipt": {
            "path": str(verified["receipt_path"]),
            "sha256": str(verified["receipt_sha256"]),
        },
        "execution_plan": {
            "path": str(verified["execution_plan_path"]),
            "sha256": str(verified["execution_plan_sha256"]),
        },
        "output_manifest": {
            "path": str(verified["output_manifest_path"]),
            "sha256": str(verified["output_manifest_sha256"]),
        },
        "selector_script": {
            "path": str(Path(selector_script).resolve()),
            "sha256": sha256_file(Path(selector_script)),
        },
        "binding": "selector input arrays are accepted only after receipt and manifest verification",
    }
