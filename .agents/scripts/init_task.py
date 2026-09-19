#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()
AGENTS = ROOT / ".agents"
TEMPLATE = AGENTS / "state-template"
STATE = ROOT / ".agent_state"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def render(text: str, title: str, created: str) -> str:
    return text.replace("{{TITLE}}", title).replace("{{CREATED}}", created)


def main() -> int:
    p = argparse.ArgumentParser(description="Initialize persistent reliability state for a long Antigravity task.")
    p.add_argument("--title", required=True)
    p.add_argument("--force", action="store_true", help="overwrite existing state files")
    args = p.parse_args()

    if not TEMPLATE.exists():
        raise SystemExit(f"Missing template directory: {TEMPLATE}")

    STATE.mkdir(exist_ok=True)
    created = now_iso()
    for name in ["TASK_LEDGER.md", "EVIDENCE_LEDGER.md", "DECISION_LOG.md", "RUN_STATE.json"]:
        src = TEMPLATE / name
        dst = STATE / name
        if dst.exists() and not args.force:
            continue
        dst.write_text(render(src.read_text(encoding="utf-8-sig"), args.title, created), encoding="utf-8")

    print(f"Initialized reliability state in {STATE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
