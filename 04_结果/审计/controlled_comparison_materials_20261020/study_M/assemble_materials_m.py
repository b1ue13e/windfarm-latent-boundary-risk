"""Inventory and copy existing evidence only; no scientific modules are imported."""
from pathlib import Path
import ast
import csv
import hashlib
import json
import shutil
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASES = [ROOT / "experiments/state_measurement_pilot_20261020",
         ROOT / "experiments/state_calibration_controls_20261020"]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rows(name, records):
    fields = list(dict.fromkeys(k for r in records for k in r))
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


copies, inventory, checks, headers, remote = [], [], [], [], []
for base in BASES:
    tag = "pilot" if "pilot" in base.name else "controls"
    export = json.loads((base / "export_manifest.json").read_text(encoding="utf-8"))
    for relative, expected in export["files"].items():
        f = base / "evidence" / relative
        actual = dict(bytes=f.stat().st_size, sha256=sha(f)) if f.is_file() else None
        checks.append(dict(study=tag, source=f.relative_to(ROOT).as_posix(),
                           expected=expected, actual=actual, matches=actual == expected))
    with tarfile.open(base / "compact_evidence.tar.gz", "r:gz") as archive:
        member_names = {m.name for m in archive.getmembers() if m.isfile()}
        for relative, expected in export["files"].items():
            h = archive.extractfile(relative)
            actual = dict(bytes=archive.getmember(relative).size,
                          sha256=hashlib.sha256(h.read()).hexdigest()) if h else None
            checks.append(dict(study=tag, source="compact_evidence.tar.gz::" + relative,
                               expected=expected, actual=actual, matches=actual == expected))
        checks.append(dict(study=tag, check="archive member names",
                           matches=member_names == set(export["files"]) | {"export_manifest.json"}))
    select = {f for f in base.iterdir() if f.is_file() and
              (f.suffix in (".json", ".csv", ".md", ".py", ".pbs", ".txt") or
               f.name == "compact_evidence.tar.gz")}
    for sub in ("prepared", "selection", "aggregate", "freeze", "action_audit", "audit"):
        d = base / "evidence/results" / sub
        if d.exists():
            select.update(f for f in d.iterdir() if f.is_file() and f.suffix in (".json", ".npz"))
    for f in sorted(select):
        dst = OUT / "copies" / tag / f.relative_to(base)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and sha(dst) != sha(f):
            raise ValueError("Refuse to overwrite a different copy: " + str(dst))
        shutil.copy2(f, dst)
        copies.append(dict(source=f.relative_to(ROOT).as_posix(),
                           copy=dst.relative_to(OUT).as_posix(), bytes=f.stat().st_size,
                           sha256=sha(f), copy_sha256=sha(dst)))
    exported = {("evidence/" + k): k for k in export["files"]}
    for f in sorted(base.rglob("*")):
        if not f.is_file() or "__pycache__" in f.parts:
            continue
        relative = f.relative_to(base).as_posix()
        copy = next((r["copy"] for r in copies if r["source"] == f.relative_to(ROOT).as_posix()), "")
        member = exported.get(relative, "")
        inventory.append(dict(study=tag, category="LOCAL_BYTES_HASHED", source=f.relative_to(ROOT).as_posix(),
                              bytes=f.stat().st_size, sha256=sha(f), organized_copy=copy,
                              compact_member=member, remote_path="", boundary="No model or measurement loaded"))
        if f.suffix == ".npz":
            arrays = []
            with zipfile.ZipFile(f) as archive:
                for n in archive.namelist():
                    with archive.open(n) as item:
                        magic = item.read(8)
                        length = int.from_bytes(item.read(2 if magic[6] == 1 else 4), "little")
                        header = ast.literal_eval(item.read(length).decode("latin1").strip())
                        arrays.append(dict(member=n, **header))
            headers.append(dict(source=f.relative_to(ROOT).as_posix(), arrays=arrays,
                                inspection="NPY header only; no array values loaded"))
    for manifest in sorted((base / "evidence/results").rglob("manifest.json")):
        obj = json.loads(manifest.read_text(encoding="utf-8"))
        for name, expected in obj.items():
            if name.startswith("source/") or not isinstance(expected, dict) or "sha256" not in expected:
                continue
            f = manifest.parent / name
            if f.exists():
                continue
            rel = f.relative_to(base / "evidence").as_posix()
            remote_path = export["remote_root"] + "/" + rel
            rec = dict(study=tag, category="HISTORICAL_MANIFEST_ONLY_REMOTE_UNCHECKED",
                       source=manifest.relative_to(ROOT).as_posix() + "::" + name,
                       bytes=expected.get("bytes", ""), sha256=expected["sha256"], organized_copy="",
                       compact_member="", remote_path=remote_path,
                       boundary="Historical hash is not current remote byte verification")
            remote.append(rec)
            inventory.append(rec)

# Preserve the exact execution source versions from local bytes and record their binding.
source_checks = []
for base in BASES:
    tag = "pilot" if "pilot" in base.name else "controls"
    manifest_name = "deployment_manifest_v2.json" if tag == "pilot" else "deployment_manifest.json"
    deployment = json.loads((base / manifest_name).read_text(encoding="utf-8"))
    for relative, expected in deployment["files"].items():
        f = ROOT / relative
        actual = dict(bytes=f.stat().st_size, sha256=sha(f)) if f.exists() else None
        record = dict(study=tag, source=relative, expected=expected,
                      actual=actual, matches=actual == expected)
        source_checks.append(record)
        if actual == expected:
            dst = OUT / "copies" / "source" / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
            if not any(r["copy"] == dst.relative_to(OUT).as_posix() for r in copies):
                copies.append(dict(source=relative, copy=dst.relative_to(OUT).as_posix(),
                                   bytes=f.stat().st_size, sha256=sha(f), copy_sha256=sha(dst)))
        else:
            packet = base / ("packet_v2.tar.gz" if tag == "pilot" else "packet.tar.gz")
            with tarfile.open(packet, "r:gz") as archive:
                blob = archive.extractfile(relative).read()
            old = dict(bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest())
            record["packet_recovery_source"] = packet.relative_to(ROOT).as_posix()
            record["packet_recovery_identity"] = old
            record["packet_recovery_matches"] = old == expected
            if record["packet_recovery_matches"]:
                dst = OUT / "copies/source" / relative
                dst.parent.mkdir(parents=True, exist_ok=True)
                if dst.exists() and sha(dst) != old["sha256"]:
                    raise ValueError("Different archived source copy")
                dst.write_bytes(blob)
                if not any(r["copy"] == dst.relative_to(OUT).as_posix() for r in copies):
                    copies.append(dict(source=packet.relative_to(ROOT).as_posix() + "::" + relative,
                                       copy=dst.relative_to(OUT).as_posix(), **old, copy_sha256=sha(dst)))

claims = []
pilot = json.loads((BASES[0] / "summary.json").read_text(encoding="utf-8"))
control = json.loads((BASES[1] / "summary.json").read_text(encoding="utf-8"))
claim_names = ["fresh_state", "old_state", "old_power", "P_premium_vs_Z", "residual_state"]
for tag, data, field, family in [("pilot", pilot, "registered_intervals", 154),
                                  ("controls", control, "interval", 596)]:
    source = BASES[0 if tag == "pilot" else 1].relative_to(ROOT).as_posix() + "/summary.json"
    for key, val in data[field].items():
        if "|cost|" not in key or not any(name + "|" in key for name in claim_names):
            continue
        claims.append(dict(id="M-" + str(len(claims) + 1).zfill(3), source=source,
                           pointer=field + "." + key, family=family, block_days=3,
                           point=val["point"], lower=val["lower"], upper=val["upper"],
                           unit="fraction, G=(C_A-C_B)/C_A; D=(C_A-C_B)/C_B",
                           epistemic="VERIFIED_STORED", figure="M-Fig measurement-cost contrasts",
                           allowed_claim="Finite fixed-program cost contrast; not safe substitution or pure information value"))
for key, val in control["interval"].items():
    if not any(name + "|" in key for name in ("residual_state", "allocation_residual_state")):
        continue
    if not (key.endswith("|mean_U") or key.endswith("|mean_R")):
        continue
    claims.append(dict(id="M-" + str(len(claims) + 1).zfill(3),
                       source=BASES[1].relative_to(ROOT).as_posix() + "/summary.json",
                       pointer="interval." + key, family=596, block_days=3,
                       point=val["point"], lower=val["lower"], upper=val["upper"],
                       unit="10*(U_B-U_A)/Cstar" if key.endswith("|mean_U") else "(R_B-R_A)/Cstar",
                       epistemic="VERIFIED_STORED", figure="M-Fig reserve/shortfall accounting",
                       allowed_claim="Signed normalized difference; never label as relative-U-percent CI"))
for i, label in enumerate(control["labels"]):
    for metric in ("C", "R", "U", "V"):
        claims.append(dict(id="M-" + str(len(claims) + 1).zfill(3),
                           source=BASES[1].relative_to(ROOT).as_posix() + "/summary.json",
                           pointer=f"mean_metrics.{metric}[{i}]", family="596 point field, no implicit interval",
                           block_days="", point=control["mean_metrics"][metric][i], lower="", upper="",
                           unit="fraction" if metric == "V" else "kWh-equivalent/valid turbine interval" if metric == "C" else "kWh/valid turbine interval",
                           epistemic="VERIFIED_STORED", figure="M-Table cost/procurement/uncovered/event decomposition",
                           allowed_claim=label + "; point only unless exact paired interval is separately bound"))
for key, routes in control["corrected_routes"].items():
    claims.append(dict(id="M-" + str(len(claims) + 1).zfill(3),
                       source=BASES[1].relative_to(ROOT).as_posix() + "/summary.json",
                       pointer="corrected_routes." + key, family=596, block_days=3,
                       point=json.dumps(routes), lower="", upper="", unit="logical conjunction",
                       epistemic="VERIFIED_STORED", figure="M-Table original acceptance routes",
                       allowed_claim="A/B/C not certified; false conjunction does not erase individual favorable contrasts"))

assert all(r["matches"] for r in checks), "Export/archive identity mismatch"
save("COPY_MANIFEST_M.json", copies)
save("EXPORT_CHECKS_M.json", checks)
save("SOURCE_BINDING_M.json", source_checks)
save("NPZ_HEADERS_M.json", headers)
rows("ASSETS_M.csv", inventory)
rows("REMOTE_MATERIALS_M.csv", remote)
rows("CLAIMS_M.csv", claims)
save("COUNTS_M.json", dict(copied_files=len(copies), copied_bytes=sum(r["bytes"] for r in copies),
                           local_files=sum(r["category"] == "LOCAL_BYTES_HASHED" for r in inventory),
                           historical_remote_entries=len(remote), exported_members_checked=len(checks),
                           archive_and_export_checks_pass=all(r["matches"] for r in checks),
                           source_checks=len(source_checks), source_matches=sum(r["matches"] for r in source_checks),
                           packet_recovered_bindings=sum(r.get("packet_recovery_matches", False) for r in source_checks),
                           npz_headers_inspected=len(headers), claim_fields=len(claims),
                           current_remote_bytes_verified=0, arrays_loaded=0, new_measurements=0,
                           model_operations=0, statistical_resampling=0))
print((OUT / "COUNTS_M.json").read_text(encoding="utf-8"))
