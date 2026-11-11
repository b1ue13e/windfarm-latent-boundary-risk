"""Export only compact derived no-refit evidence, never raw measurements."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    root = args.root.resolve()
    if not root.name.startswith("state_calibration_controls_20261020") or args.output.exists():
        raise ValueError("Fresh archive in the named control workspace required")
    for name in ("aggregate", "audit", "freeze"):
        if not (root / "results" / name / "manifest.json").is_file():
            raise ValueError("Incomplete results")
    files = [root / "deployment_manifest.json", root / "check.pbs", root / "audit.pbs"]
    files += list((root / "logs").glob("*.log"))
    for f in (root / "results").rglob("*"):
        relative = f.relative_to(root / "results")
        if f.is_file() and "source" not in relative.parts and f.name != "actions.npz":
            if f.suffix in (".json", ".npz"):
                files.append(f)
    files = sorted(set(files))
    meta = dict(scope="Partial derived evidence; full controls actions and old weights/predictions stay on Metis",
        remote_root=str(root), files={str(f.relative_to(root)): dict(bytes=f.stat().st_size, sha256=sha(f)) for f in files})
    blob = json.dumps(meta, indent=2).encode()
    with tarfile.open(args.output, "w:gz") as tar:
        for f in files:
            tar.add(f, arcname=str(f.relative_to(root)), recursive=False)
        info = tarfile.TarInfo("export_manifest.json"); info.size = len(blob)
        tar.addfile(info, io.BytesIO(blob))
    print(json.dumps(dict(files=len(files), bytes=args.output.stat().st_size, sha256=sha(args.output))))


if __name__ == "__main__":
    main()
