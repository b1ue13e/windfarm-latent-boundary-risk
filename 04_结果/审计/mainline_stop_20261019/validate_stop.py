"""Validate archival state and unchanged evidence; never run research workloads."""
from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    before = json.loads((OUT / "before.json").read_text(encoding="utf-8"))
    modified = [p for p, h in before["protected_sha256"].items() if sha(ROOT / p) != h]
    assert not modified, modified
    for p, h in before["authorized_state_files"].items():
        assert sha(OUT / "historical_state" / p) == h, p

    state = yaml.safe_load((ROOT / "research_state.yaml").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "research-manifest.json").read_text(encoding="utf-8"))
    run = json.loads((ROOT / ".agent_state/RUN_STATE.json").read_text(encoding="utf-8"))
    stop = state["stop_decision"]
    assert stop == manifest["stopDecision"] == manifest["project"]["stopDecision"] == run["stop_decision"]
    assert stop["decision"] == "STOP_ADDITIONAL_INVESTMENT"
    assert stop["scientific_completion"] is False and stop["submission_ready"] is False
    assert stop["automatic_resume"] is False
    assert state["project"]["status"] == manifest["project"]["status"] == run["status"] == "stopped"
    assert not state["next_actions"] and not manifest["nextActions"] and not run["next_actions"]
    assert not manifest["loop"]["nextActions"] and run["active_task"] is None
    assert run["metis_followup"]["status"] == "PAUSED"
    assert not run["metis_followup"]["next_actions"]
    assert all(m["executionAuthorized"] is False for m in manifest["methods"])
    assert all(e["executionStatus"] == "archived_no_additional_execution" for e in manifest["experiments"])
    assert state["progress"]["current_gate"] == "STOP"
    for item in state["research"]["verified_conclusions"]:
        assert (ROOT / item["evidence"].split("#")[0]).exists(), item
    for key in ["resource_loss_review", "novelty_review", "scientific_contract", "historical_records"]:
        assert (ROOT / state["evidence"][key]).exists(), key
    for p in before["authorized_state_files"]:
        if p.startswith(".agent_state/") and p.endswith(".md"):
            old = (OUT / "historical_state" / p).read_text(encoding="utf-8")
            current = (ROOT / p).read_text(encoding="utf-8")
            assert old.split("\n", 1)[1] in current, p
            assert "STOP_ADDITIONAL_INVESTMENT" in current[:1000], p
    project = (ROOT / "PROJECT.md").read_text(encoding="utf-8")
    assert "**当前状态**：`STOP_ADDITIONAL_INVESTMENT`" in project
    assert "**VERIFIED**: 在变桨过渡区，边界感知能够集中产生 48.4%" not in project
    record = ROOT / stop["record"]
    for doc in [record, OUT / "README.md"]:
        for target in re.findall(r"\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
            if not target.startswith(("https://", "http://", "#")):
                assert (doc.parent / target.split("#")[0]).exists(), (str(doc), target)
    automation = before["automation_observation"]
    assert sha(Path(automation["path"])) == automation["sha256"]
    assert 'status = "PAUSED"' in Path(automation["path"]).read_text(encoding="utf-8")

    verification = OUT / "verification"
    verification.mkdir(exist_ok=True)
    commands = []
    specs = [
        ("scientific_claim_gate", [sys.executable, "scripts/verify_scientific_claim_gate.py"]),
        ("number_gate", [sys.executable, "scripts/verify_tste_number_consistency.py", "--output-dir", str(verification / "numbers")]),
        ("independent_confirmation_gate", [sys.executable, "scripts/verify_independent_confirmation_gate.py", "--output", str(verification / "confirmation_gate.json")]),
    ]
    for name, argv in specs:
        result = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (verification / (name + ".log")).write_bytes(result.stdout)
        commands.append({"name": name, "argv": argv, "exit_code": result.returncode})
        assert result.returncode == 0, (name, result.stdout.decode("utf-8", errors="replace")[-1500:])
    assert all(sha(ROOT / p) == h for p, h in before["protected_sha256"].items())
    receipt = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_STOP_STATE_AND_BOUNDED_PRESERVATION",
        "python": sys.version,
        "platform": platform.platform(),
        "protected_paths_rechecked": len(before["protected_sha256"]),
        "protected_changes": [],
        "historical_state_snapshots_verified": 8,
        "execution_queue": [],
        "automatic_resume": False,
        "metis_automation_observed": "PAUSED_UNCHANGED_LOCAL_CONFIG",
        "remote_access": False,
        "training_inference_calibration_resampling_data_acquisition": False,
        "commands": commands,
        "scientific_completion": False,
        "scope": before["coverage"],
        "state_sha256": {p: sha(ROOT / p) for p in before["authorized_state_files"]},
        "decision_record_sha256": sha(record),
        "script_sha256": sha(Path(__file__)),
    }
    (OUT / "validation_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "protected_paths": receipt["protected_paths_rechecked"], "gate_exits": [c["exit_code"] for c in commands]}))


if __name__ == "__main__":
    main()
