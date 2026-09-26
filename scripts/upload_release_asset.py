#!/usr/bin/env python3
"""Upload release asset to GitHub Release using GitHub REST API."""
from __future__ import annotations
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

TAG_NAME = "tste-submission-v1.0"
ASSET_NAME = "windfarm_derived_artifacts_v1.0.zip"
LOCAL_PATH = Path("C:/Users/Public/Downloads/windfarm_release") / ASSET_NAME
if not LOCAL_PATH.exists():
    LOCAL_PATH = Path(__file__).resolve().parents[1] / "archives" / ASSET_NAME

if not LOCAL_PATH.exists():
    print(f"Error: Asset file not found: {LOCAL_PATH}")
    sys.exit(1)

token = os.environ.get("GITHUB_TOKEN")
if not token:
    try:
        token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except Exception as e:
        print(f"Error obtaining GitHub token: {e}")
        sys.exit(1)

rel_req = urllib.request.Request(
    f"https://api.github.com/repos/b1ue13e/windfarm-latent-boundary-risk/releases/tags/{TAG_NAME}",
    headers={"Authorization": f"Bearer {token}", "User-Agent": "windfarm-release-uploader/1.0"},
)
with urllib.request.urlopen(rel_req) as resp:
    rel_info = json.loads(resp.read().decode("utf-8"))
    release_id = rel_info["id"]

file_size = LOCAL_PATH.stat().st_size
upload_url = f"https://uploads.github.com/repos/b1ue13e/windfarm-latent-boundary-risk/releases/{release_id}/assets?name={ASSET_NAME}"

print(f"Uploading {LOCAL_PATH} ({file_size:,} bytes) to {upload_url} ...")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/zip",
    "Content-Length": str(file_size),
    "User-Agent": "windfarm-release-uploader/1.0",
}

data = LOCAL_PATH.read_bytes()
req = urllib.request.Request(upload_url, data=data, headers=headers, method="POST")
try:
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode("utf-8", errors="ignore")
        print(f"Upload completed with HTTP {resp.status}!")
        print(body[:300])
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code} {e.reason}")
    print(e.read().decode("utf-8", errors="ignore"))
    sys.exit(1)
