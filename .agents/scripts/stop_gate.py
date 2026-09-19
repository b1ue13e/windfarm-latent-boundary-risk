#!/usr/bin/env python3
"""Optional Antigravity Stop hook.

It fails closed when verify_gate.py says the task is incomplete. Because Antigravity hook
behavior has had version/platform regressions, this is an extra guard rather than the
primary source of truth.
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    workspace_paths = payload.get("workspacePaths") or []
    root = Path(workspace_paths[0]) if workspace_paths else Path.cwd()
    script = root / ".agents" / "scripts" / "verify_gate.py"

    if not script.exists():
        # Do not deadlock an unrelated session if this hook is accidentally installed globally.
        print(json.dumps({}))
        return 0

    cp = subprocess.run([sys.executable, str(script), "--no-run-commands"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if cp.returncode == 0:
        print(json.dumps({}))
    else:
        reason = "Completion gate failed. Continue the task and repair the following:\n" + cp.stdout[-3500:]
        print(json.dumps({"decision": "continue", "reason": reason}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
