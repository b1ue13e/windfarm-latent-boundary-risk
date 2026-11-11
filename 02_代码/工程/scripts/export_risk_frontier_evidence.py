"""Export finite-grid sufficient statistics and receipts, not large raw arrays."""
import argparse
import json
from repo_paths import Path, repository_root
import sys
import tarfile

ROOT = Path(repository_root())
sys.path.insert(0, str(ROOT))
from scripts.run_risk_cost_frontier import sha, verify


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    pp = root / "experiments/risk_cost_frontier_development_20261018/protocol.json"
    protocol = json.loads(pp.read_text())
    verify(root / "results/aggregate", sha(pp), "aggregate")
    members = [p for folder in ("results/aggregate", "results/choose") for p in (root / folder).rglob("*") if p.is_file()]
    checks = 0
    for stage in ("historical", "evaluate"):
        for condition in protocol["conditions"]:
            for seed in protocol["seeds"]:
                folder = root / f"results/{stage}/seed{seed}/{condition}"
                verify(folder, sha(pp), stage, seed, condition)
                names = ("receipt.json", "manifest.json", "resources.json", "historical_grid.npz") if stage == "historical" else ("receipt.json", "manifest.json", "resources.json", "evaluation_grid.npz", "grid_metrics.json")
                members.extend(folder / name for name in names)
                if stage == "evaluate":
                    checks += json.loads((folder / "grid_metrics.json").read_text())["exact_selected_action_array_checks"]
    if checks != len(protocol["conditions"]) * len(protocol["seeds"]) * len(protocol["variants"]) * 6:
        raise ValueError("Incomplete selected-action accounting checks")
    members.extend(p for p in (root / "logs").iterdir() if p.is_file())
    members.extend(root / name for name in ("launch.py", "run_lf.pbs", "smoke_submission.json", "graph_submission.json"))
    members.extend(p for p in (root / "experiments/risk_cost_frontier_development_20261018").rglob("*") if p.is_file())
    members.extend(root / name for name in ("scripts/run_risk_cost_frontier.py", "windfarm_moe/risk_frontier.py", "windfarm_moe/decision_information.py"))
    mapping = {str(p.relative_to(root)): {"bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(set(members))}
    manifest = root / "compact_manifest.json"
    with manifest.open("x") as f:
        json.dump({"members": mapping, "exact_selected_action_array_checks": checks,
                   "producer_root": str(root), "scope": "metadata/statistics export; full calibration and selected actions retained on producer"}, f, indent=2)
    output = root / "compact_evidence.tar.gz"
    with tarfile.open(output, "x:gz") as archive:
        for name in mapping:
            archive.add(root / name, arcname=name, recursive=False)
        archive.add(manifest, arcname=manifest.name)
    print(json.dumps({"output": str(output), "sha256": sha(output), "members": len(mapping), "exact_checks": checks}))


if __name__ == "__main__":
    main()
