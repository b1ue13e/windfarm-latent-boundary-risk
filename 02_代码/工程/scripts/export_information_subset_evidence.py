"""Export completed compact evidence; full models/actions remain immutable remotely."""
import argparse
import hashlib
import importlib.util
import json
from repo_paths import Path, repository_root
import tarfile


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def export_members(members, output):
    manifest = {name: dict(bytes=path.stat().st_size, sha256=sha(path)) for name, path in members.items()}
    mp = output.with_suffix(".members.json")
    with mp.open("x", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    with tarfile.open(output, "x:gz") as t:
        for name, path in members.items():
            t.add(path, arcname=name)
        t.add(mp, arcname="export_manifest.json")
    with tarfile.open(output) as t:
        for name, record in manifest.items():
            data = t.extractfile(name).read()
            if len(data) != record["bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
                raise ValueError("Export member mismatch: " + name)
    return dict(archive_sha256=sha(output), bytes=output.stat().st_size, members=len(manifest),
                scope="Compact metadata/block evidence; raw forecast/actions/weights and fit indices remain on Metis")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study-root", type=Path, required=True)
    p.add_argument("--post-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    spec = importlib.util.spec_from_file_location("frozen_subset_export_producer", args.study_root / "scripts/run_information_subset_study.py")
    producer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(producer)
    protocol = args.study_root / "experiments/information_subset_development_20261019/protocol.json"
    cfg = json.loads(protocol.read_text(encoding="utf-8"))
    producer.verify(args.study_root / "results/aggregate", protocol, "aggregate")
    audit = json.loads((args.post_root / "audit/audit.json").read_text(encoding="utf-8"))
    tasks = producer.tasks(cfg)
    expected = sum(len(t["budgets"]) for t in tasks) * len(cfg["offset_quantiles"]) * 6
    if audit["status"] != "ALL_NEW_ACTION_ARRAYS_EXACT" or audit["array_checks"] != expected or audit["tasks"] != len(tasks):
        raise ValueError("Independent action audit incomplete")
    members = {}
    source = json.loads((args.study_root / "deployment_manifest.json").read_text())["files"]
    for name, expected_sha in source.items():
        path = args.study_root / name
        if sha(path) != expected_sha:
            raise ValueError("Source archive identity mismatch")
        members["study/" + name] = path
    for name in ("deployment_manifest.json", "deployment_lustre.json"):
        members["study/" + name] = args.study_root / name
    for stage in ("historical", "evaluate"):
        for index in range(len(tasks)):
            root = args.study_root / "results" / stage / str(index)
            for name in ("receipt.json", "manifest.json", "metadata.json", "historical_blocks.npz" if stage == "historical" else "evaluation_blocks.npz"):
                members["study/" + (root / name).relative_to(args.study_root).as_posix()] = root / name
    for stage in ("choose", "aggregate"):
        for path in (args.study_root / "results" / stage).rglob("*"):
            if path.is_file():
                members["study/" + path.relative_to(args.study_root).as_posix()] = path
    for stage in ("audit", "report"):
        for path in (args.post_root / stage).rglob("*"):
            if path.is_file():
                members["post/" + path.relative_to(args.post_root).as_posix()] = path
    receipt = export_members(members, args.output)
    receipt["exporter_sha256"] = sha(__file__)
    with (args.post_root / "archive_receipt.json").open("x", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
