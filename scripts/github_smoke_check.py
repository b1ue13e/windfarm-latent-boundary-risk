"""Fast checks that make a fresh GitHub checkout self-describing.

The full evidence gate is intentionally separate because it requires locally
built PDFs and experiment artifacts that are not part of a clean source clone.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-artifacts", action="store_true")
    args = parser.parse_args()

    required = [
        ".github/workflows/verify.yml",
        ".github/pull_request_template.md",
        ".github/SECURITY.md",
        "docs/GITHUB_REPRODUCIBILITY_PLAN.md",
        ".agents/verification_manifest.json",
        ".agent_state/RUN_STATE.json",
        ".agent_state/TASK_LEDGER.md",
        ".agent_state/EVIDENCE_LEDGER.md",
        ".agent_state/REVIEW_REPORT.md",
    ]
    missing = [rel for rel in required if not (ROOT / rel).exists()]
    if missing:
        for rel in missing:
            print(f"MISSING: {rel}")
        return 1

    state = json.loads((ROOT / ".agent_state/RUN_STATE.json").read_text(encoding="utf-8-sig"))
    if state.get("status") != "complete":
        print(f"RUN_STATE status is not complete: {state.get('status')!r}")
        return 1

    task_text = (ROOT / ".agent_state/TASK_LEDGER.md").read_text(encoding="utf-8-sig")
    if "T43" not in task_text:
        print("T43 GitHub reproducibility task is not registered")
        return 1

    if args.require_artifacts:
        artifact_paths = [
            "build/paper_tste_ieee.pdf",
            "build/paper_tste_supplementary.pdf",
            "artifacts/direct_quantile_baselines_summary.csv",
            "artifacts/channel_consequence_ablations.csv",
        ]
        missing_artifacts = [rel for rel in artifact_paths if not (ROOT / rel).exists()]
        if missing_artifacts:
            for rel in missing_artifacts:
                print(f"MISSING_ARTIFACT: {rel}")
            return 2

    print("GITHUB_SMOKE_CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
