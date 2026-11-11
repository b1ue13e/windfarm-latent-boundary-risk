"""Independently reconstruct block accounting from archived float64 actions."""
from __future__ import annotations

import argparse
import hashlib
import json
from repo_paths import Path, repository_root
import sys

import numpy as np

ROOT = Path(repository_root())
sys.path.insert(0, str(ROOT))
from scripts.run_decision_information_development import digest, verify_bundle
from windfarm_moe.decision_information import block_totals


def audit_run(path: Path, protocol_path: Path) -> dict:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    seed, condition = int(path.parent.name[4:]), path.name
    verify_bundle(path, digest(protocol_path), "run", seed, condition)
    protected = {p.name: digest(p) for p in path.iterdir() if p.is_file()}
    checked = 0
    with np.load(path / "evaluation_coordinates.npz") as coordinates, np.load(path / "evaluation_actions.npz") as actions, np.load(path / "block_totals.npz") as stored:
        for variant in protocol["variants"]:
            for version, suffix in (("raw", "_raw"), ("calibrated", "")):
                action = actions[variant + suffix]
                if action.dtype != np.float64:
                    raise ValueError("Stored action precision changed")
                totals = block_totals(coordinates["shortfall"], action, coordinates["mask"], coordinates["anchors"])
                for name, values in totals.items():
                    if not np.array_equal(values, stored[f"{variant}__{version}__{name}"]):
                        raise ValueError(f"Exact accounting failed: {variant}/{version}/{name}")
                    checked += 1
        if not np.array_equal(coordinates["target_indices"], coordinates["anchors"] + protocol["task"]["horizon_steps"]):
            raise ValueError("Target coordinates differ from protocol")
        if not np.array_equal(coordinates["publication_indices"], coordinates["anchors"] - protocol["task"]["commitment_age_steps"]):
            raise ValueError("Commitment publication coordinates differ from protocol")
    for name, expected in protected.items():
        if digest(path / name) != expected:
            raise ValueError("Protected output changed during audit")
    return {"seed": seed, "condition": condition, "exact_block_array_checks": checked,
            "status": "EXACT_ARCHIVED_ACTION_ACCOUNTING_PASS", "protected_sha256": protected,
            "scope": "Reconstructs the archived actions only; not model-quality or deployment certification"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    rows = [audit_run(args.runs / f"seed{seed}" / condition, args.protocol)
            for seed in protocol["seeds"] for condition in protocol["conditions"]]
    report = {"status": "ALL_ARCHIVED_ACTIONS_EXACT", "runs": rows,
              "audit_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(report["status"], len(rows))


if __name__ == "__main__":
    main()
