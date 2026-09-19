#!/usr/bin/env python3
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main() -> int:
    p = argparse.ArgumentParser(description="Append an evidence record tied to a task ID.")
    p.add_argument("--task", required=True, help="Task ID, e.g. T03")
    p.add_argument("--status", required=True, choices=["VERIFIED_REPO", "VERIFIED_COMMAND", "VERIFIED_SOURCE", "INFERRED", "UNKNOWN"])
    p.add_argument("--summary", required=True)
    p.add_argument("--source", default="")
    p.add_argument("--command", default="")
    p.add_argument("--exit-code", default="")
    p.add_argument("--output", default="")
    args = p.parse_args()

    state = Path.cwd() / ".agent_state"
    state.mkdir(exist_ok=True)
    ledger = state / "EVIDENCE_LEDGER.md"
    if not ledger.exists():
        ledger.write_text("# Evidence Ledger\n\n", encoding="utf-8")

    block = [
        f"## {args.task} — {now_iso()}",
        f"Task-ID: {args.task}",
        f"Status: {args.status}",
        f"Summary: {args.summary}",
    ]
    if args.source:
        block.append(f"Source: {args.source}")
    if args.command:
        block.append(f"Command: `{args.command}`")
    if args.exit_code:
        block.append(f"Exit-Code: {args.exit_code}")
    if args.output:
        block.extend(["Relevant-Output:", "```", args.output[:4000], "```"])
    block.append("")

    with ledger.open("a", encoding="utf-8") as f:
        f.write("\n".join(block) + "\n")
    print(f"Recorded evidence for {args.task}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
