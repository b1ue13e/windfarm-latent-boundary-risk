"""Package bounded derived evidence; full actions/models stay on Metis."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    root = args.root.resolve()
    if not root.name.startswith("state_measurement_pilot_20261020") or args.output.exists():
        raise ValueError("Fresh archive required in the named pilot workspace")
    required = ["results/aggregate/manifest.json", "results/action_audit/audit.json",
                "results/prepared/manifest.json", "results/selection/manifest.json"]
    if not all((root / f).is_file() for f in required):
        raise ValueError("Incomplete pilot evidence")
    files = [root / "deployment_manifest.json", root / "check.pbs", root / "audit.pbs"]
    files += list((root / "logs").glob("*.log"))
    for name in ("prepared", "selection", "aggregate", "action_audit"):
        files += [f for f in (root / "results" / name).iterdir()
                  if f.is_file() and (f.suffix == ".json" or name == "aggregate")]
    for i in range(70):
        for phase, names in (("fits", ("manifest.json", "receipt.json", "offsets.json", "selection_blocks.npz", "training_trace.json")),
                ("evaluation", ("manifest.json", "receipt.json", "metrics.json", "action_audit.json", "blocks.npz"))):
            directory = root / "results" / phase / str(i)
            if not (directory / "manifest.json").is_file():
                raise ValueError("Missing completed task: " + str(directory))
            files.extend(directory / name for name in names if (directory / name).is_file())
    files = sorted(set(files))
    manifest = {str(f.relative_to(root)): dict(bytes=f.stat().st_size, sha256=sha(f)) for f in files}
    meta = dict(remote_root=str(root), files=manifest,
        scope="Partial derived evidence, not full raw/model/action replay. Original measurements, fitted models, fit indices, raw predictions and full action archives remain on Metis; upstream hashes included.")
    blob = json.dumps(meta, indent=2).encode()
    with tarfile.open(args.output, "w:gz") as tar:
        for f in files:
            tar.add(f, arcname=str(f.relative_to(root)), recursive=False)
        info = tarfile.TarInfo("export_manifest.json")
        info.size = len(blob)
        tar.addfile(info, io.BytesIO(blob))
    print(json.dumps(dict(files=len(files), bytes=args.output.stat().st_size, sha256=sha(args.output))))


if __name__ == "__main__":
    main()
