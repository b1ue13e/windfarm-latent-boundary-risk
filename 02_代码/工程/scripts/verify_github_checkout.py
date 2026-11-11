"""Check publication and frozen evidence without private data or weights.

An archived queue is valid here; this does not relabel the research complete.
The historical scientific and completion gates remain unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path as NativePath
import subprocess

from repo_paths import Path, repository_root

ROOT = Path(repository_root())


def forbidden_upload(name: str) -> bool:
    p = NativePath(name)
    if name.startswith("03_数据/") and name != "03_数据/README.md":
        return True
    if set(p.parts) & {"__pycache__", ".pytest_cache", "运行缓存", "复现运行"}:
        return True
    return name.endswith((".zip", ".tar.gz", ".tgz", ".7z", ".pt", ".pth", ".ckpt",
                          ".safetensors", ".joblib", ".pkl", ".onnx", ".h5", ".aux", ".pyc"))


def valid_research_state(state: dict) -> bool:
    if state.get("status") == "stopped":
        return state.get("active_task") is None and state.get("phase") == "archived_no_additional_investment"
    return state.get("status") == "complete"


def verify(root=ROOT) -> dict:
    root = Path(root)
    checks = []

    def record(name, passed, **details):
        checks.append(dict(name=name, passed=bool(passed), **details))

    required = ["AGENTS.md", "PROJECT.md", "project.py", "复现说明.md", "GITHUB_UPLOAD.md",
                "01_当前论文/TSTE/manuscript.tex", "01_当前论文/TSTE/supplementary.tex",
                "02_代码/工程/requirements-ci.txt", "03_数据/README.md", "04_结果/README.md",
                "04_结果/项目记录/docs/SCIENTIFIC_CONTRACT.md", ".github/workflows/verify.yml"]
    record("Current layout", all((root / p).is_file() for p in required), required=required)
    state = json.loads((root / ".agent_state/RUN_STATE.json").read_text(encoding="utf-8-sig"))
    record("Research state preserved", valid_research_state(state), status=state.get("status"),
           phase=state.get("phase"), active_task=state.get("active_task"))
    raw = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout
    forbidden = [p for p in raw.decode("utf-8").split("\0") if p and forbidden_upload(p)]
    record("No private data, weights, packed bundles or runtime cache tracked", not forbidden, forbidden=forbidden)
    receipt = json.loads((root / "01_当前论文/TSTE/qa/visual_redesign_20261027/DATA_RECEIPT.json").read_text(encoding="utf-8"))
    differences = []
    for name, expected in receipt["source_hashes"].items():
        p = root / name
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            differences.append(name)
    record("All stored scientific source fingerprints", not differences,
           files=len(receipt["source_hashes"]), differences=differences)
    return dict(status="PASS" if all(c["passed"] for c in checks) else "FAIL", checks=checks,
                scope="Published sources and stored evidence only; no raw-data, training, inference or deployment certification.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=NativePath)
    args = parser.parse_args()
    report = verify()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
