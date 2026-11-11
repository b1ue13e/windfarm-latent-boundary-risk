from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PREREG = ROOT / "experiments/E04/PREREGISTRATION_E04_V2.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def main() -> int:
    p = json.loads(PREREG.read_text(encoding="utf-8"))
    failures = []
    for key, rel in {
        "information_set_contract": "docs/INFORMATION_SET_CONTRACT.md",
        "fixed_target_contract": "docs/FIXED_TARGET_CONTRACT.md",
        "criterion_doc": "docs/MINIMUM_SUFFICIENT_DECISION_CRITERION.md",
        "selector_script": "experiments/E04/code/select_e04_v2.py",
        "provenance_module": "experiments/E04/code/e04_provenance.py",
        "receipt_wrapper": "experiments/E04/code/run_e04_bound.py",
        "preregistration_verifier": "experiments/E04/code/verify_preregistration.py",
    }.items():
        actual = sha256(ROOT / rel)
        expected = p["input_artifact_sha256"][key].upper()
        if actual != expected:
            failures.append(f"{key}: expected {expected}, got {actual}")
    if p["status"] != "PREREGISTERED_BEFORE_EXECUTION":
        failures.append("invalid preregistration status")
    if p["valid_outcomes"] != ["SELECTED", "NO FEASIBLE POLICY", "UNSTABLE SELECTION", "BLOCKED"]:
        failures.append("valid outcome set changed")
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception as exc:
        failures.append(f"cannot read git HEAD: {exc}")
        commit = None
    if failures:
        print("PREREGISTRATION_INVALID")
        print("\n".join(failures))
        return 1
    print(json.dumps({"status":"PREREGISTRATION_INPUT_HASHES_VALID","git_head":commit,"experiment_id":p["experiment_id"]}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
