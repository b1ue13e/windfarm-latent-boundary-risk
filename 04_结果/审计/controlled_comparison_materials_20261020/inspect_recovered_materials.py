"""Check existing-file hashes and array headers; never evaluate models or outcomes."""
import ast
import csv
import hashlib
import json
from pathlib import Path
import struct
import zipfile

BASE = Path(__file__).resolve().parent
WORKSPACE = BASE.parent.parent


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def header(handle):
    if handle.read(6) != b"\x93NUMPY":
        raise ValueError("Not an NPY array")
    version = handle.read(2)
    size = 2 if version[0] == 1 else 4
    count = struct.unpack("<H" if size == 2 else "<I", handle.read(size))[0]
    encoding = "utf-8" if version[0] == 3 else "latin1"
    return ast.literal_eval(handle.read(count).decode(encoding))


def main():
    plan = json.loads((BASE / "TRANSFER_PLAN.json").read_text())
    rows = []
    schemas = []
    missing = []
    for item in plan["files"]:
        path = BASE / "recovered" / item["group"] / item["relative"]
        if not path.is_file():
            missing.append(path.relative_to(BASE).as_posix())
            continue
        if path.stat().st_size != item["bytes"] or sha(path) != item["sha256"]:
            raise ValueError("Recovered bytes differ from historical manifest: " + str(path))
        row = dict(item, local=path.relative_to(BASE).as_posix(),
                   status="CURRENT_BYTES_EQUAL_HISTORICAL_MANIFEST")
        rows.append(row)
        if path.suffix == ".npz":
            with zipfile.ZipFile(path) as archive:
                for name in archive.namelist():
                    if not name.endswith(".npy"):
                        raise ValueError("Unexpected NPZ member")
                    with archive.open(name) as handle:
                        info = header(handle)
                    schemas.append({"file": row["local"], "key": name[:-4], **info})
        elif path.suffix == ".npy":
            with path.open("rb") as handle:
                info = header(handle)
            schemas.append({"file": row["local"], "key": "array", **info})
    extra = json.loads((BASE / "SUPPLEMENT_TRANSFER.json").read_text())
    extra_path = WORKSPACE / extra["file"]
    if extra_path.stat().st_size != extra["bytes"] or sha(extra_path) != extra["sha256"]:
        raise ValueError("Supplemental point-model bytes differ")
    rows.append({"group": "R", "relative": "results/prepared/point_forecaster.joblib",
                 "remote_root": "", "bytes": extra["bytes"], "sha256": extra["sha256"],
                 "historical_manifest": extra["historical_manifest"],
                 "historical_manifest_sha256": sha(WORKSPACE / extra["historical_manifest"]),
                 "local": extra_path.relative_to(BASE).as_posix(),
                 "status": "CURRENT_BYTES_EQUAL_HISTORICAL_MANIFEST"})
    physical = json.loads((BASE / "SUPPLEMENT_PHYSICAL.json").read_text())
    physical_path = WORKSPACE / physical["file"]
    if physical_path.stat().st_size != physical["bytes"] or sha(physical_path) != physical["sha256"]:
        raise ValueError("Existing shared physical-channel bytes differ")
    rows.append({"group": "shared", "relative": "physical_channels.npy", "remote_root": "",
                 "bytes": physical["bytes"], "sha256": physical["sha256"],
                 "historical_manifest": ";".join(physical["historical_manifests"]),
                 "historical_manifest_sha256": ";".join(sha(WORKSPACE / path) for path in physical["historical_manifests"]),
                 "local": physical_path.relative_to(BASE).as_posix(),
                 "status": "CURRENT_BYTES_EQUAL_BOTH_HISTORICAL_MANIFESTS"})
    with physical_path.open("rb") as handle:
        info = header(handle)
    schemas.append({"file": physical_path.relative_to(BASE).as_posix(), "key": "array", **info})
    if missing:
        raise ValueError("Selected existing files still missing: " + str(missing[:10]))
    fields = list(rows[0])
    with (BASE / "RECOVERED_FILES.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (BASE / "ARRAY_SCHEMA.json").write_text(json.dumps({
        "scope": "NPY/NPZ headers only; array payloads not evaluated; joblib not deserialized",
        "arrays": schemas
    }, indent=2) + "\n", encoding="utf-8")
    aliases = []
    by_hash = {row["sha256"]: row["local"] for row in rows}
    fits = WORKSPACE / "experiments/state_measurement_pilot_20261020/evidence/results/fits"
    for task in range(70):
        original = fits / str(task) / "manifest.json"
        meta = json.loads(original.read_text())["fit_indices.npy"]
        if meta["sha256"] not in by_hash:
            raise ValueError("No recovered representative training index")
        aliases.append({"task": task, "declared_file_sha256": meta["sha256"],
                        "available_identical_representative": by_hash[meta["sha256"]],
                        "individual_current_remote_file_hash_reread": False})
    with (BASE / "TRAINING_INDEX_ALIASES_M.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(aliases[0]))
        writer.writeheader()
        writer.writerows(aliases)
    result = {"status": "ALL_SELECTED_EXISTING_MATERIAL_BYTES_VERIFIED",
              "files": len(rows), "bytes": sum(row["bytes"] for row in rows),
              "groups": {key: {"files": sum(row["group"] == key for row in rows),
                                "bytes": sum(row["bytes"] for row in rows if row["group"] == key)}
                         for key in ["R", "M_pilot", "M_controls", "shared"]},
              "array_headers": len(schemas), "training_index_representatives": 5,
              "training_index_task_aliases": 70, "joblib_deserialized": False,
              "action_accounting_recomputed": False, "bootstrap_executed": False,
              "raw_SCADA_CSV_copied": False,
              "existing_derived_physical_channel_array_copied_once": True,
              "new_research_or_model_execution": False}
    (BASE / "CURRENT_AVAILABILITY.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
