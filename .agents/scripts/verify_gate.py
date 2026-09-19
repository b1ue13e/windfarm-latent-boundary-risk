#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
STATE = ROOT / ".agent_state"
MANIFEST = ROOT / ".agents" / "verification_manifest.json"

TASK_RE = re.compile(r"^- \[(?P<mark>[ x!\-])\]\s+(?P<id>T[A-Za-z0-9_-]+)\s+(?P<state>TODO|DOING|VERIFIED|BLOCKED)\b", re.M)


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def run_command(cmd: str, cwd: Path):
    cp = subprocess.run(cmd, cwd=cwd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return cp.returncode, cp.stdout


def main() -> int:
    p = argparse.ArgumentParser(description="Fail closed when a long task lacks completion evidence.")
    p.add_argument("--no-run-commands", action="store_true", help="validate state only")
    args = p.parse_args()

    failures = []
    notes = []
    required_state = ["TASK_LEDGER.md", "EVIDENCE_LEDGER.md", "DECISION_LOG.md", "RUN_STATE.json"]
    for name in required_state:
        if not (STATE / name).exists():
            failures.append(f"missing state file: .agent_state/{name}")

    if failures:
        print("VERIFICATION_GATE: FAIL")
        for x in failures:
            print(f"- {x}")
        return 2

    manifest = load_json(MANIFEST, {})
    task_text = (STATE / "TASK_LEDGER.md").read_text(encoding="utf-8-sig")
    evidence = (STATE / "EVIDENCE_LEDGER.md").read_text(encoding="utf-8-sig")
    tasks = list(TASK_RE.finditer(task_text))
    if not tasks:
        failures.append("no parseable tasks found in TASK_LEDGER.md")

    if manifest.get("require_all_nonblocked_tasks_verified", True):
        for m in tasks:
            state = m.group("state")
            tid = m.group("id")
            if state in {"TODO", "DOING"}:
                failures.append(f"open task: {tid} is {state}")

    if manifest.get("require_evidence_for_verified_tasks", True):
        for m in tasks:
            if m.group("state") == "VERIFIED":
                tid = m.group("id")
                if f"Task-ID: {tid}" not in evidence:
                    failures.append(f"verified task lacks evidence entry: {tid}")

    if manifest.get("require_independent_review", True):
        review = STATE / "REVIEW_REPORT.md"
        if not review.exists():
            failures.append("independent review missing: .agent_state/REVIEW_REPORT.md")
        else:
            rt = review.read_text(encoding="utf-8-sig")
            if not re.search(r"\b(PASS|PASS_WITH_BLOCKERS)\b", rt):
                failures.append("independent review has no PASS/PASS_WITH_BLOCKERS verdict")

    if manifest.get("require_verification_report", False):
        vr = STATE / "VERIFICATION_REPORT.md"
        if not vr.exists() or not re.search(r"\bPASS\b", vr.read_text(encoding="utf-8-sig")):
            failures.append("required verification report missing or not PASS")

    for rel in manifest.get("required_files", []):
        if not (ROOT / rel).exists():
            failures.append(f"required file missing: {rel}")

    for item in manifest.get("forbidden_patterns", []):
        pattern = item.get("pattern", "")
        paths = item.get("paths", ["."])
        if not pattern:
            continue
        rx = re.compile(pattern)
        for rel in paths:
            pth = ROOT / rel
            candidates = [pth] if pth.is_file() else [p for p in pth.rglob("*") if p.is_file() and ".git" not in p.parts and ".agent_state" not in p.parts]
            for fp in candidates:
                try:
                    txt = fp.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                if rx.search(txt):
                    failures.append(f"forbidden pattern {pattern!r} found in {fp.relative_to(ROOT)}")
                    break

    command_results = []
    if not args.no_run_commands:
        for spec in manifest.get("commands", []):
            if not spec.get("enabled", True):
                continue
            name = spec.get("name", spec.get("command", "command"))
            cmd = spec.get("command", "")
            required = spec.get("required", True)
            cwd = ROOT / spec.get("cwd", ".")
            if not cmd:
                continue
            code, out = run_command(cmd, cwd)
            command_results.append((name, cmd, code, out[-5000:]))
            if required and code != 0:
                failures.append(f"verification command failed: {name} (exit {code})")

    report = STATE / "GATE_REPORT.md"
    lines = [f"# Verification Gate Report\n", f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}\n"]
    for name, cmd, code, out in command_results:
        lines += [f"## Command: {name}", f"`{cmd}`", f"Exit: {code}", "```", out, "```", ""]
    if failures:
        lines += ["## Verdict", "FAIL", "", "## Failures"] + [f"- {x}" for x in failures]
    else:
        lines += ["## Verdict", "PASS"]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if failures:
        print("VERIFICATION_GATE: FAIL")
        for x in failures:
            print(f"- {x}")
        return 1

    print("VERIFICATION_GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
