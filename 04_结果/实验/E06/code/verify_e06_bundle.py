"""Local verifier for the Metis E06 receipt-bound bundle.

The remote receipt keeps absolute Metis paths. This verifier validates the
pulled bundle directly, then maps the reproducibility inputs that exist in the
local workspace and reports unavailable local equivalents explicitly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def record(path: Path) -> dict:
    return {"bytes": path.stat().st_size, "sha256": sha256(path)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--local-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    local_root = args.local_root.resolve()
    prereg = bundle / "PREREGISTRATION_E04_V2.json"
    receipt = bundle / "e04_execution_receipt.json"
    plan_path = bundle / "e04_execution_plan.json"
    manifest_path = bundle / "e04_output_manifest.json"
    expected_outputs = [f"seed{seed}_full_policy_day_blocks.npz" for seed in range(201, 206)]
    receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
    plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if receipt_data.get("schema_version") != "E04-receipt-v1" or receipt_data.get("status") != "EXECUTED" or receipt_data.get("exit_code") != 0:
        raise ValueError("Remote receipt is not a successful E04 receipt")
    if receipt_data.get("execution_plan") != {"path": plan_path.name, **record(plan_path)}:
        raise ValueError("Receipt does not bind the pulled execution plan")
    if receipt_data.get("output_manifest") != {"path": manifest_path.name, **record(manifest_path)}:
        raise ValueError("Receipt does not bind the pulled output manifest")
    if receipt_data.get("outputs") != manifest_data.get("files"):
        raise ValueError("Receipt outputs differ from pulled output manifest")
    if sorted(item["path"] for item in manifest_data["files"]) != sorted(expected_outputs):
        raise ValueError("Pulled output manifest does not contain the five E04 policy arrays")
    for item in manifest_data["files"]:
        output = bundle / item["path"]
        if not output.is_file() or record(output) != {"bytes": item["bytes"], "sha256": item["sha256"]}:
            raise ValueError(f"Pulled output hash mismatch: {output}")
    if receipt_data.get("inputs") != plan_data.get("inputs") or receipt_data.get("argv") != plan_data.get("argv"):
        raise ValueError("Receipt command/input records differ from execution plan")
    remote_input_attestation = json.loads((bundle / "e06_remote_input_verification.json").read_text(encoding="utf-8"))
    if remote_input_attestation.get("status") != "INPUTS_UNCHANGED_AFTER_REPLAY" or not all(item.get("match") for item in remote_input_attestation.get("checks", [])):
        raise ValueError("Remote input attestation is incomplete or contains a mismatch")

    selector = bundle / "e04_selection.json"
    selector_manifest = bundle / "e04_selector_output_manifest.json"
    selection = json.loads(selector.read_text(encoding="utf-8"))
    selector_hashes = json.loads(selector_manifest.read_text(encoding="utf-8"))
    selector_checks = {
        "selector_result": selector_hashes["selector_result"] == {"path": selector.name, **record(selector)},
        "execution_receipt": selector_hashes["execution_receipt"] == {"path": receipt.name, **record(receipt)},
        "execution_plan": selector_hashes["execution_plan"] == {"path": "e04_execution_plan.json", **record(bundle / "e04_execution_plan.json")},
        "output_manifest": selector_hashes["output_manifest"] == {"path": "e04_output_manifest.json", **record(bundle / "e04_output_manifest.json")},
    }

    exact_inputs = local_root / "experiments" / "E06" / "remote_e06_inputs" / "e06_exact_inputs"
    local_candidates = {
        "preregistration": prereg,
        "residuals": exact_inputs / "fixed_forecast_residuals.npz",
        "cache_metadata": exact_inputs / "cache_metadata.json",
    }
    for seed in range(201, 206):
        local_candidates[f"checkpoint:{seed}"] = exact_inputs / "checkpoints" / f"seed{seed}_best_model.pt"
    cache = local_root / "artifacts" / "raw_replay_20261015_v2" / "cache_wtb"
    for path in sorted(cache.glob("*.npy")):
        local_candidates[f"cache_array:{path.name}"] = path

    remote_inputs = json.loads((bundle / "e04_execution_receipt.json").read_text(encoding="utf-8"))["inputs"]
    input_checks = []
    for remote in remote_inputs:
        role = str(remote.get("role"))
        if role == "cache_array":
            key = f"cache_array:{Path(str(remote['path'])).name}"
        elif role == "checkpoint":
            key = f"checkpoint:{Path(str(remote['path'])).parent.name.replace('seed', '')}"
        else:
            key = role
        local = local_candidates.get(key)
        row = {"role": role, "remote": remote, "local_path": str(local) if local else None}
        if local is None or not local.is_file():
            row["status"] = "LOCAL_EQUIVALENT_UNAVAILABLE"
        else:
            actual = record(local)
            row["actual"] = actual
            row["status"] = "MATCH" if actual == {k: remote[k] for k in ("bytes", "sha256")} else "MISMATCH"
        input_checks.append(row)

    result = {
        "schema_version": "E06-local-verification-v1",
        "status": "PASS_BUNDLE_LOCAL_INPUTS" if all(c["status"] == "MATCH" for c in input_checks) else ("PASS_BUNDLE_LOCAL_INPUTS_PARTIAL" if all(c["status"] != "MISMATCH" for c in input_checks) else "FAIL_INPUT_MISMATCH"),
        "bundle": str(bundle),
        "receipt": {"status": receipt_data["status"], "exit_code": receipt_data["exit_code"], **record(receipt)},
        "output_manifest": {"files": len(manifest_data["files"]), **record(bundle / "e04_output_manifest.json")},        
        "execution_plan": record(bundle / "e04_execution_plan.json"),
        "selector": {"selection_status": selection["selection"]["status"], **record(selector)},
        "selector_hash_checks": selector_checks,
        "remote_input_checks": input_checks,
        "remote_input_summary": {
            "total": len(input_checks),
            "match": sum(c["status"] == "MATCH" for c in input_checks),
            "unavailable": sum(c["status"] == "LOCAL_EQUIVALENT_UNAVAILABLE" for c in input_checks),
            "mismatch": sum(c["status"] == "MISMATCH" for c in input_checks),
        },
        "scientific_status": "not promoted; selector remains conditional on the remote receipt-bound replay and frozen inputs",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] in {"PASS_BUNDLE_LOCAL_INPUTS", "PASS_BUNDLE_LOCAL_INPUTS_PARTIAL"} and all(selector_checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
