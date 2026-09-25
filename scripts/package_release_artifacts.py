#!/usr/bin/env python3
"""Package Category B release artifacts into windfarm_derived_artifacts_v1.0.zip."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import zipfile
from pathlib import Path

REPO_ROOT = Path(os.environ.get("WINDFARM_REPO_ROOT", Path(__file__).resolve().parents[1]))


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Package Category B large artifacts for external release.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=REPO_ROOT / "artifacts" / "ARTIFACT_MANIFEST.json",
        help="Path to ARTIFACT_MANIFEST.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "archives",
        help="Directory to save release zip archive",
    )
    parser.add_argument(
        "--archive-name",
        type=str,
        default="windfarm_derived_artifacts_v1.0.zip",
        help="Name of the archive bundle",
    )
    args = parser.parse_args()

    if not args.manifest.exists():
        print(f"Error: Manifest not found: {args.manifest}")
        return 1

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    category_b = [item for item in manifest if item.get("category") == "B"]

    print(f"Found {len(category_b)} Category B artifacts in manifest:")
    for item in category_b:
        print(f"  - {item['filename']} ({item['size_bytes']:,} bytes)")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = args.output_dir / args.archive_name
    sha256_path = args.output_dir / f"{args.archive_name}.sha256"

    print(f"\nBuilding release archive: {archive_path}")
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for item in category_b:
            rel_path = item["filename"]
            src_file = REPO_ROOT / rel_path
            if not src_file.exists():
                print(f"Error: required file missing on disk: {src_file}")
                return 1

            actual_sha = compute_sha256(src_file)
            if actual_sha != item["sha256"]:
                print(f"Error: SHA256 mismatch for {rel_path}!")
                print(f"  Expected: {item['sha256']}")
                print(f"  Got:      {actual_sha}")
                return 1

            print(f"  Adding {rel_path} (verified SHA256 {actual_sha[:12]}...)")
            zf.write(src_file, arcname=rel_path)

    archive_size = archive_path.stat().st_size
    archive_sha = compute_sha256(archive_path)
    sha256_path.write_text(f"{archive_sha} *{args.archive_name}\n", encoding="utf-8")

    print(f"\nSuccessfully created release bundle:")
    print(f"  Archive: {archive_path} ({archive_size:,} bytes, {archive_size/1024/1024:.2f} MB)")
    print(f"  SHA256:  {archive_sha}")
    print(f"  Checksum written to: {sha256_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
