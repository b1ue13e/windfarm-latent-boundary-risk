"""Consolidate byte-identical evidence copies and finish the cleanup index."""
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
B = ROOT / "03_论文交付/当前稿件_TSTE"
assert (OUT / "SUMMARY.json").is_file(), "Main cleanup must finish first"
rows = json.loads((OUT / "operations.json").read_text(encoding="utf-8"))
mf = ROOT / "02_公共资源/项目管理/目录迁移/path_map.json"
mapping = json.loads(mf.read_text(encoding="utf-8"))
groups = defaultdict(list)
eligible_dirs = {"source_data", "supplement_data", "literature", "code_versions", "code_and_provenance"}
for r in rows:
    if r["action"] != "move":
        continue
    p = Path(r["destination"])
    if "历史稿件证据" in p.parts and "qa" not in p.parts and set(p.parts) & eligible_dirs:
        groups[r["sha256"]].append(r)
duplicates = []
redirects = {}
for digest, copies in groups.items():
    copies.sort(key=lambda r: (len(r["destination"]), r["destination"]))
    canonical = copies[0]["destination"]
    for r in copies[1:]:
        p = ROOT / r["destination"]
        p.absolute().relative_to(ROOT / "99_历史归档/保留证据")
        assert (ROOT / canonical).is_file()
        if p.exists():
            assert p.stat().st_size == r["bytes"]
            p.unlink()
        redirects[r["destination"]] = canonical
        duplicates.append(dict(path=r["destination"], retained=canonical, sha256=digest, bytes=r["bytes"]))
for key, target in list(mapping.items()):
    if target in redirects:
        mapping[key] = redirects[target]
mapping.update(redirects)

# Active tools must write new check outputs at their current location; historical
# checks remain separate, byte-for-byte snapshots instead of being overwritten.
mutable_names = {"FINAL_CHECKS.json", "BUILD_RECEIPT.json", "BUILD_MANUSCRIPT.json", "BUILD_SUPPLEMENTARY.json",
                 "manuscript_extracted.txt", "supplementary_extracted.txt"}
for name in mutable_names:
    local = B / "qa" / name
    current = local.relative_to(ROOT).as_posix()
    target = mapping.get(current)
    if name.startswith("BUILD_") and target:
        shutil.copy2(ROOT / target, local)
    for alias in (current, "manuscripts/tste_telemetry_20261026/qa/" + name):
        mapping.pop(alias, None)
for key in list(mapping):
    if key.startswith(("03_论文交付/当前稿件_TSTE/qa/", "manuscripts/tste_telemetry_20261026/qa/")):
        p = Path(key)
        if p.parent.name == "qa" and (p.name.startswith(("manuscript_pass", "manuscript_quick", "supplementary_pass", "supplementary_quick"))):
            mapping.pop(key)

# A deleted manuscript/cache no longer has a live path alias. Its former identity
# remains in the original directory-migration records and this cleanup manifest.
retired = {k: v for k, v in mapping.items() if not (ROOT / v).exists()}
mapping = {k: v for k, v in mapping.items() if k not in retired}
mf.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(OUT / "deduplicated.json").write_text(json.dumps(duplicates, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "retired_aliases.json").write_text(json.dumps(retired, ensure_ascii=False, indent=2), encoding="utf-8")
summary = json.loads((OUT / "SUMMARY.json").read_text(encoding="utf-8"))
summary.update(duplicate_copies_deleted=len(duplicates), duplicate_bytes=sum(r["bytes"] for r in duplicates),
               retired_aliases=len(retired), live_aliases=len(mapping))
summary["net_reclaimed_bytes"] = summary["deleted_bytes"] + summary["duplicate_bytes"] - summary["extracted_unique_bytes"]
(OUT / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
