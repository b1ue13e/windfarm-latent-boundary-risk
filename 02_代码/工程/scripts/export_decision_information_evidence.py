"""Export compact verified evidence; full actions/models remain at the producer."""
from __future__ import annotations

import argparse
import hashlib
import json
from repo_paths import Path, repository_root
import tarfile


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    audit = json.loads((root / "results/all_actions_audit.json").read_text())
    if audit["status"] != "ALL_ARCHIVED_ACTIONS_EXACT" or len(audit["runs"]) != 30:
        raise ValueError("Complete exact action audit required")
    paths = [p for p in (root / "results/aggregate").rglob("*") if p.is_file()]
    for directory in (root / "results/runs").glob("seed*/*"):
        for name in ("metrics.csv", "execution_receipt.json", "output_manifest.json",
                     "models_and_diagnostics.json", "calibration_offsets.json", "wind_bins.json"):
            paths.append(directory / name)
    for name in ("execution_receipt.json", "output_manifest.json", "data_manifest.json"):
        paths.append(root / "results/prepared" / name)
    paths.extend(p for p in (root / "logs").iterdir() if p.is_file())
    paths.extend((root / "results/all_actions_audit.json", root / "results/smoke_action_audit.json"))
    paths.extend(p for p in root.glob("*submission.json"))
    paths.extend(root / name for name in ("launch_array.py", "array.pbs", "run_lf.pbs", "audit_smoke.pbs", "aggregate_audit.pbs"))
    paths.extend(root / name for name in ("scripts/run_decision_information_development.py",
                   "scripts/audit_decision_information_actions.py", "windfarm_moe/decision_information.py",
                   "experiments/decision_information_development_20261018/protocol.json"))
    members = {str(p.relative_to(root)): {"bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(set(paths))}
    manifest_path = root / "compact_evidence_manifest.json"
    with manifest_path.open("x", encoding="utf-8") as handle:
        json.dump({"status": "COMPACT_METADATA_EXPORT", "producer_root": str(root),
                   "members": members, "full_weights_and_actions": "Retained at producer; not duplicated into compact export"}, handle, indent=2)
    with tarfile.open(args.output, "x:gz") as archive:
        for name in members:
            archive.add(root / name, arcname=name, recursive=False)
        archive.add(manifest_path, arcname=manifest_path.name)
    print(json.dumps({"archive": str(args.output), "sha256": sha(args.output), "members": len(members)}))


if __name__ == "__main__":
    main()
