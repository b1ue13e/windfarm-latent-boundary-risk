"""Acquire registered opaque year archives without opening their measurement contents.

Network streaming and cryptographic byte checks only; no ZIP reader or scientific
data library is imported. Failures retain their own partial files and receipts.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import urllib.request
from urllib.parse import urlparse


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_binding(binding: dict) -> None:
    expected = [(2023, "train"), (2024, "calibration"), (2025, "locked_test")]
    if binding["record_id"] != 22662930 or binding["measurement_access_allowed"] is not False:
        raise ValueError("Only the frozen metadata-only source acquisition is supported")
    if [(r["year"], r["role"]) for r in binding["archives"]] != expected:
        raise ValueError("Year/role binding changed")
    for record in binding["archives"]:
        year = record["year"]
        if record["name"] != f"{year}.zip" or record["bytes"] < 1:
            raise ValueError("Invalid archive name or size")
        parsed = urlparse(record["url"])
        if parsed.scheme != "https" or parsed.netloc != "zenodo.org" or parsed.path != f"/api/records/22662930/files/{year}.zip/content":
            raise ValueError("Archive URL is not the registered official record")
        checksum = record["official_md5"]
        if len(checksum) != 32 or any(c not in "0123456789abcdef" for c in checksum):
            raise ValueError("Invalid official MD5")


def acquire_one(record: dict, destination: Path, opener=urllib.request.urlopen) -> dict:
    """Write a new opaque file, verify bytes, and seal it read-only on success."""
    partial = destination.with_suffix(".zip.part")
    md5, sha = hashlib.md5(), hashlib.sha256()
    size = 0
    req = urllib.request.Request(record["url"], headers={"User-Agent": "Research-opaque-acquisition/1.0"})
    with partial.open("xb") as handle:
        with opener(req, timeout=120) as response:
            while chunk := response.read(4 * 1024 * 1024):
                size += len(chunk)
                if size > record["bytes"]:
                    raise ValueError("Response exceeds registered size")
                handle.write(chunk)
                md5.update(chunk)
                sha.update(chunk)
        handle.flush()
        os.fsync(handle.fileno())
    if size != record["bytes"] or md5.hexdigest() != record["official_md5"]:
        raise ValueError("Downloaded size or official MD5 mismatch; partial retained")
    # No existing sealed file can be replaced, including by a resumed command.
    with destination.open("xb") as marker:
        pass
    try:
        os.replace(partial, destination)
    except BaseException:
        destination.unlink()
        raise
    destination.chmod(0o400)
    return {"year": record["year"], "role": record["role"], "file": str(destination),
            "bytes": size, "official_md5": md5.hexdigest(), "sha256": sha.hexdigest(),
            "status": "OPAQUE_ARCHIVE_MD5_VERIFIED_CONTENT_UNOPENED", "finished_utc": now()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--binding-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sha256(args.binding) != args.binding_sha256:
        raise ValueError("Pre-acquisition binding hash mismatch")
    binding = json.loads(args.binding.read_text(encoding="utf-8"))
    validate_binding(binding)
    if sha256(Path(__file__)) != binding["acquisition_script_sha256"]:
        raise ValueError("Acquisition implementation differs from frozen binding")
    required = sum(r["bytes"] for r in binding["archives"]) + 2 * 1024**3
    args.output.parent.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(args.output.parent).free
    if free < required:
        raise ValueError("Insufficient space for archives plus 2 GiB headroom")
    args.output.mkdir(exist_ok=False)
    receipt = {"started_utc": now(), "binding_sha256": args.binding_sha256,
               "script_sha256": sha256(Path(__file__)), "argv": sys.argv,
               "host": platform.node(), "python": sys.version, "platform": platform.platform(),
               "free_bytes_before": free, "required_bytes_with_headroom": required,
               "execution_scope": "Login-node network streaming and byte hashing only; no measurement parser, ZIP listing, inference or model selection",
               "measurement_contents_opened": False, "archives": []}
    with (args.output / "start_receipt.json").open("x", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    for record in binding["archives"]:
        try:
            result = acquire_one(record, args.output / record["name"])
        except BaseException as exc:
            failure = {"year": record["year"], "failed_utc": now(), "type": type(exc).__name__,
                       "error": str(exc), "partial_files_preserved": True}
            with (args.output / f"failure_{record['year']}.json").open("x", encoding="utf-8") as f:
                json.dump(failure, f, indent=2)
            raise
        receipt["archives"].append(result)
        with (args.output / f"receipt_{record['year']}.json").open("x", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(json.dumps(result), flush=True)
    receipt["finished_utc"] = now()
    receipt["status"] = "ALL_THREE_OPAQUE_ARCHIVES_VERIFIED_NOT_PARSED"
    with (args.output / "completion_receipt.json").open("x", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)


if __name__ == "__main__":
    main()
