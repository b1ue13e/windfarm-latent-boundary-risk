#!/usr/bin/env python3
"""Fetch and unpack Category B release artifacts with cryptographic validation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(os.environ.get("WINDFARM_REPO_ROOT", Path(__file__).resolve().parents[1]))
DEFAULT_RELEASE_URL = (
    "https://github.com/b1ue13e/windfarm-latent-boundary-risk/releases/download/v1.0/windfarm_derived_artifacts_v1.0.zip"
)
ALT_RELEASE_URL = (
    "https://github.com/b1ue13e/windfarm-latent-boundary-risk/releases/download/v1.0.0/windfarm_derived_artifacts_v1.0.zip"
)
DEFAULT_ARCHIVE_NAME = "windfarm_derived_artifacts_v1.0.zip"


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def check_existing_category_b(manifest_entries: list[dict], root: Path) -> tuple[bool, list[str]]:
    all_valid = True
    missing_or_invalid = []
    for item in manifest_entries:
        if item.get("category") != "B":
            continue
        rel = item["filename"]
        fp = root / rel
        if not fp.exists():
            all_valid = False
            missing_or_invalid.append(f"{rel} (missing)")
        else:
            actual_sha = compute_sha256(fp)
            if actual_sha != item["sha256"]:
                all_valid = False
                missing_or_invalid.append(f"{rel} (checksum mismatch)")
    return all_valid, missing_or_invalid


def download_with_progress(url: str, dest_path: Path):
    print(f"Downloading from {url} ...")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "windfarm-reproducibility-fetcher/1.0"},
        )
        with urllib.request.urlopen(req) as resp, dest_path.open("wb") as out_file:
            total_size = int(resp.getheader("Content-Length", 0))
            downloaded = 0
            block_size = 1024 * 1024  # 1 MB
            while chunk := resp.read(block_size):
                out_file.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    pct = downloaded / total_size * 100
                    mb = downloaded / (1024 * 1024)
                    tot_mb = total_size / (1024 * 1024)
                    print(f"\r  [{pct:5.1f}%] {mb:6.1f} / {tot_mb:6.1f} MB", end="", flush=True)
                else:
                    mb = downloaded / (1024 * 1024)
                    print(f"\r  {mb:6.1f} MB downloaded", end="", flush=True)
            print()
    except Exception as e:
        if dest_path.exists():
            dest_path.unlink()
        raise RuntimeError(f"Download failed from {url}: {e}") from e


def main():
    parser = argparse.ArgumentParser(description="Fetch and verify released Category B derived artifacts.")
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root directory",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Path to ARTIFACT_MANIFEST.json",
    )
    parser.add_argument(
        "--local-archive",
        type=Path,
        default=None,
        help="Path to local windfarm_derived_artifacts_v1.0.zip bundle (or dir containing it)",
    )
    parser.add_argument(
        "--archive-url",
        type=str,
        default=os.environ.get("WINDFARM_RELEASE_URL", DEFAULT_RELEASE_URL),
        help="Public URL for released artifacts zip bundle",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Directory to store downloaded archive",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check whether Category B artifacts are present and valid",
    )
    args = parser.parse_args()

    manifest_path = args.manifest or (args.root / "artifacts" / "ARTIFACT_MANIFEST.json")
    cache_dir = args.cache_dir or Path(os.environ.get("WINDFARM_CACHE_DIR", args.root / "archives"))

    if not manifest_path.exists():
        print(f"Error: Manifest not found: {manifest_path}")
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    category_b = [item for item in manifest if item.get("category") == "B"]
    manifest_by_rel = {item["filename"]: item for item in category_b}

    print(f"=== Category B Artifact Fetcher ({len(category_b)} release artifacts) ===")

    # Check if already present and valid
    valid, issues = check_existing_category_b(category_b, args.root)
    if valid:
        print("[PASS] All Category B artifacts already exist with valid SHA256 checksums:")
        for item in category_b:
            print(f"  [OK] {item['filename']} ({item['size_bytes']:,} bytes)")
        return 0

    if args.check_only:
        print("[FAIL] Category B artifacts missing or invalid:")
        for iss in issues:
            print(f"  - {iss}")
        return 1

    # Locate archive source:
    # 1. CLI --local-archive
    # 2. $env:WINDFARM_ARTIFACTS_ARCHIVE
    # 3. Cache directory file
    # 4. Download from --archive-url
    archive_file: Path | None = None
    env_local = os.environ.get("WINDFARM_ARTIFACTS_ARCHIVE")

    candidates = []
    if args.local_archive:
        candidates.append(args.local_archive)
    if env_local:
        candidates.append(Path(env_local))
    candidates.append(cache_dir / DEFAULT_ARCHIVE_NAME)

    for cand in candidates:
        if cand.is_file() and cand.exists():
            archive_file = cand
            break
        elif cand.is_dir() and (cand / DEFAULT_ARCHIVE_NAME).exists():
            archive_file = cand / DEFAULT_ARCHIVE_NAME
            break

    if archive_file:
        print(f"Using local release archive: {archive_file}")
    else:
        cache_dir.mkdir(parents=True, exist_ok=True)
        target_dl = cache_dir / DEFAULT_ARCHIVE_NAME
        print(f"No local archive found. Attempting download from public URL:")
        print(f"  URL: {args.archive_url}")
        print(f"  Destination: {target_dl}")
        download_success = False
        urls_to_try = [args.archive_url]
        if args.archive_url == DEFAULT_RELEASE_URL and ALT_RELEASE_URL not in urls_to_try:
            urls_to_try.append(ALT_RELEASE_URL)

        last_err = None
        for u in urls_to_try:
            try:
                download_with_progress(u, target_dl)
                archive_file = target_dl
                download_success = True
                break
            except Exception as e:
                last_err = e
                print(f"  Attempt with {u} failed: {e}")

        if not download_success:
            print(f"\n[ERROR] Unable to download release archive automatically:")
            print(f"  {last_err}\n")
            print("For isolated / offline / clean-clone testing, provide the release bundle via either:")
            print(f"  1. python scripts/fetch_artifacts.py --local-archive <path-to-{DEFAULT_ARCHIVE_NAME}>")
            print(f"  2. set WINDFARM_ARTIFACTS_ARCHIVE=<path-to-{DEFAULT_ARCHIVE_NAME}>")
            print(f"  3. place {DEFAULT_ARCHIVE_NAME} in {cache_dir}\n")
            return 1

    # Unpack archive into args.root
    print(f"\nUnpacking release archive: {archive_file}")
    with zipfile.ZipFile(archive_file, "r") as zf:
        namelist = zf.namelist()
        for item in category_b:
            rel = item["filename"]
            norm_rel = rel.replace("\\", "/")
            matching_names = [n for n in namelist if n.replace("\\", "/") == norm_rel]
            if not matching_names:
                print(f"[FAIL] Archive does not contain required artifact: {rel}")
                return 1

            arc_member = matching_names[0]
            dest_file = args.root / rel
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            print(f"  Extracting {rel} ...")
            with zf.open(arc_member) as src, dest_file.open("wb") as dst:
                shutil.copyfileobj(src, dst)

            actual_sha = compute_sha256(dest_file)
            if actual_sha != item["sha256"]:
                print(f"  [FAIL] SHA256 mismatch for extracted {rel}!")
                print(f"    Expected: {item['sha256']}")
                print(f"    Got:      {actual_sha}")
                return 1
            print(f"  [PASS] {rel} verified (SHA256: {actual_sha[:12]}...)")

    print("\n=======================================================")
    print("SUCCESS: ALL CATEGORY B ARTIFACTS FETCHED AND VERIFIED")
    print("=======================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
