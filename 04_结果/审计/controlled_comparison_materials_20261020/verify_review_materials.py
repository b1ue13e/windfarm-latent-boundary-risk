"""Validate packaged file identities only; no research imports, network or statistics."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def validate(base, include_arrays=False):
    manifest = json.loads((base / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
    failures = []
    checked = 0
    groups = [manifest["core_files"]]
    if include_arrays:
        groups.append(manifest["existing_array_files"])
    for files in groups:
        for relative, expected in files.items():
            rel = PurePosixPath(relative)
            if rel.is_absolute() or ".." in rel.parts:
                failures.append({"file": relative, "reason": "UNSAFE_RELATIVE_PATH"})
                continue
            path = base / Path(*rel.parts)
            if not path.resolve().is_relative_to(base.resolve()):
                failures.append({"file": relative, "reason": "OUTSIDE_PACKAGE"})
            elif not path.is_file():
                failures.append({"file": relative, "reason": "MISSING"})
            elif path.stat().st_size != expected["bytes"] or sha(path) != expected["sha256"]:
                failures.append({"file": relative, "reason": "IDENTITY_MISMATCH"})
            checked += 1
    return {"status": "FAIL" if failures else "PASS_MATERIAL_IDENTITIES_ONLY",
            "checked_files": checked, "arrays_included": include_arrays,
            "failures": failures, "research_executed": False,
            "coverage_or_retraining_certification": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--include-arrays", action="store_true")
    args = parser.parse_args()
    result = validate(args.root.resolve(), args.include_arrays)
    print(json.dumps(result, indent=2))
    if result["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
