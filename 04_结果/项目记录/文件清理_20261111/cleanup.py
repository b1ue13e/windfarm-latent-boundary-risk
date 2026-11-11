"""Remove superseded writing artifacts, retaining scientific data and audit bytes."""
from pathlib import Path
from collections import Counter
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
import os
import zipfile

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CURRENT = ROOT / "03_论文交付/当前稿件_TSTE"
EVIDENCE = ROOT / "99_历史归档/保留证据"
actions = {}


def rel(p):
    return p.relative_to(ROOT).as_posix()


@lru_cache(maxsize=None)
def checked_parent(p):
    Path(str(p.resolve()).removeprefix("\\\\?\\")).relative_to(ROOT)


def checked(p):
    checked_parent(p.parent)
    p.absolute().relative_to(ROOT)
    assert p != ROOT and not p.is_symlink(), p
    return p


def files(p):
    if p.is_file():
        yield p
    elif p.is_dir():
        for base, dirs, names in os.walk(p):
            for name in dirs:
                assert not (Path(base) / name).is_symlink()
            for name in names:
                yield checked(Path(base) / name)


def schedule(p, reason, destination=None):
    for f in files(checked(p)):
        dest = destination / f.relative_to(p) if destination and p.is_dir() else destination
        actions[rel(f)] = dict(path=rel(f), action="move" if dest else "delete",
                              destination=rel(dest) if dest else None,
                              reason=reason, bytes=f.stat().st_size)


def sha(p):
    return hashlib.file_digest(p.open("rb"), "sha256").hexdigest()


def plan():
    # Scientific experiment directories, raw data, weights and frozen records are
    # deliberately outside these mutation roots.
    for p in CURRENT.iterdir():
        if p.is_file() and (p.name.startswith("manuscript_") or
                            (p.suffix == ".zip" and p.name != "tste_figures_v14.zip") or
                            (p.name.endswith("_README_CN.md") and p.name != "FIGURES_V14_README_CN.md")):
            if "layout_pages" in p.name and "v14" in p.name:
                schedule(p, "现行排版检查图移至审计记录", EVIDENCE / "TSTE排版检查" / p.name)
            else:
                schedule(p, "已被现行稿件替代的版本或重复导出")
    for p in (CURRENT / "figures").iterdir():
        if p.name != "v14":
            schedule(p, "旧图形版本")
    for p in (CURRENT / "figure_code").iterdir():
        if p.name not in {"figures_v14.py", "audit_panel_alignment.py", "requirements_figures.txt"}:
            if p.name == "export_visual_data_v2.py":
                schedule(p, "保留数据导出来源代码", EVIDENCE / "TSTE数据来源代码" / p.name)
            else:
                schedule(p, "旧绘图程序或Python字节码")
    schedule(CURRENT / "docs", "被v14替代的旧图")
    for p in (CURRENT / "sections").iterdir():
        if p.suffix == ".md" or p.name == "related_work_body.tex":
            schedule(p, "已被现行TeX及便读导出替代的草稿")
    schedule(CURRENT / "supplementary_methods.md", "已被现行补充材料TeX替代的草稿")
    for name in ["sources", "writing_notes"]:
        schedule(CURRENT / name, "写作记录集中保存", EVIDENCE / "TSTE写作记录" / name)
    for name in ["AUTHOR_NOTES_CN.md", "WRITING_BRIEF_CN.md"]:
        schedule(CURRENT / name, "写作记录集中保存", EVIDENCE / "TSTE写作记录" / name)
    schedule(CURRENT / "corpus", "文献及核验元数据集中保存", ROOT / "02_公共资源/文献/TSTE当前稿件")
    # Keep active checks and their byte-identity receipts at their original paths.
    active_qa = {"build_pdfs.py", "export_reading_copy.py", "verify_draft.py", "figure_rebuild_v14"}
    for p in (CURRENT / "qa").iterdir():
        if p.name in active_qa:
            continue
        if p.name == "__pycache__" or p.name == "io_probe.txt":
            schedule(p, "无用缓存或IO探针")
        elif p.name == "visual_redesign_20261027":
            for q in p.iterdir():
                if q.name != "DATA_RECEIPT.json":
                    schedule(q, "保留历史审计", EVIDENCE / "TSTE历史审计/visual_redesign_20261027" / q.name)
        else:
            schedule(p, "保留历史审计", EVIDENCE / "TSTE历史审计" / p.name)
    v14 = CURRENT / "qa/figure_rebuild_v14"
    for name in ["before", "rendered", "legacy_numbers"]:
        schedule(v14 / name, "保留v14历史检查及改稿前快照", EVIDENCE / "TSTE历史审计/figure_rebuild_v14" / name)
    schedule(v14 / "__pycache__", "Python字节码")
    # The frozen submission notice is evidence; the superseded submission payload is not.
    for p in files(CURRENT / "submission"):
        if p.suffix in {".pdf", ".zip"}:
            schedule(p, "旧投稿准备包，未投稿")
        else:
            schedule(p, "保留交付说明", EVIDENCE / "TSTE历史交付说明" / p.relative_to(CURRENT / "submission"))
    # Retain the current build PDFs/bibliography because the active checker and
    # quick build use them; preserve compilation logs as audit evidence.
    for p in (CURRENT / "build").iterdir():
        if p.suffix in {".log", ".blg"}:
            schedule(p, "保留原编译日志", EVIDENCE / "TSTE历史审计/build" / p.name)
        elif p.suffix not in {".pdf", ".bbl"}:
            schedule(p, "可重建编译缓存")

    for version in (ROOT / "99_历史归档/历史稿件").iterdir():
        if not version.is_dir():
            continue
        if version.name == "早期根目录稿件":
            gate_files = {"paper_tste_ieee.md", "paper_tste_supplementary.md", "cover_letter_tste.md"}
            for p in files(version):
                if p.name in gate_files:
                    schedule(p, "历史门禁必需输入，不是现行稿件", EVIDENCE / "历史门禁输入" / p.name)
                elif any(x in p.name for x in ["REPRODUCIBILITY", "REBUTTAL", "CHANGELOG"]):
                    schedule(p, "保留历史科学说明", EVIDENCE / "早期稿件审计" / p.relative_to(version))
                else:
                    schedule(p, "旧稿件及旧排版产物")
            continue
        keep_dirs = {"qa", "source_data", "supplement_data", "review_package", "revision_evidence",
                     "author_working", "literature", "interface_review", "public_review_package", "scripts", "tests", "tables"}
        for p in version.iterdir():
            if p.is_dir() and p.name in keep_dirs:
                schedule(p, "保留历史数据、来源代码和审计", EVIDENCE / "历史稿件证据" / version.name / p.name)
            elif p.is_file() and (p.suffix in {".json", ".csv", ".log", ".bib"} or
                any(x in p.name.upper() for x in ["AUDIT", "CONTRACT", "REVIEW", "PROVENANCE", "GAPS", "DECISION", "RESPONSE", "AUTHOR_ITEMS", "FOUR_QUESTIONS"]) or
                p.name.startswith("export_supplement") or p.name.startswith("test_")):
                schedule(p, "保留历史元数据、科学说明和检验代码", EVIDENCE / "历史稿件证据" / version.name / p.name)
            else:
                schedule(p, "已废弃的整套稿件、图形及发布包")
        # Compiler logs are historical audit records even inside a build folder.
        for p in files(version / "build"):
            if p.suffix in {".log", ".blg"}:
                schedule(p, "保留历史编译日志", EVIDENCE / "历史稿件证据" / version.name / "build" / p.relative_to(version / "build"))
    for p in files(ROOT / "99_历史归档/历史交付包"):
        if p.suffix in {".log", ".bib"}:
            schedule(p, "保留历史交付编译记录和引用", EVIDENCE / "早期交付记录" / p.relative_to(ROOT / "99_历史归档/历史交付包"))
        else:
            schedule(p, "被替代的历史交付文件")
    old = ROOT / "99_历史归档/旧工作目录"
    schedule(old / "$root", "错误工作目录中的旧编译产物")
    schedule(old / "archives/paper_drafts_202603", "更早的稿件排版试验")
    # These contain actual evidence despite the old 'cache' location.
    schedule(ROOT / "02_公共资源/运行缓存/tmp", "登记表修复及调查记录，不作缓存删除", EVIDENCE / "登记表修复及临时审计")
    for p in list(files(ROOT / "02_公共资源/运行缓存/build")):
        if p.suffix == ".log":
            schedule(p, "保留历史编译日志", EVIDENCE / "旧编译记录" / p.name)
        else:
            schedule(p, "旧稿件编译缓存及排版试验")
    schedule(ROOT / "02_公共资源/运行缓存/pagecheck", "可重建旧稿件预览缓存")
    schedule(ROOT / "02_公共资源/运行缓存/__pycache__", "Python字节码")
    schedule(ROOT / ".pytest_cache", "pytest缓存")
    # Only runtime bytecode in maintained engineering, not frozen experiment bundles.
    for base, dirs, _ in os.walk(ROOT / "02_公共资源/工程"):
        if "__pycache__" in dirs:
            schedule(Path(base) / "__pycache__", "Python字节码")
            dirs.remove("__pycache__")
    # Isolated historical build/review bundles sometimes embed data. Their
    # scientific members are protected regardless of the parent's folder name.
    for row in list(actions.values()):
        p = ROOT / row["path"]
        if row["action"] != "delete":
            continue
        scientific = p.suffix.lower() in {".json", ".csv", ".npz", ".npy", ".pt", ".pth", ".pkl",
                                         ".h5", ".hdf5", ".nc", ".parquet", ".log", ".blg", ".xml"}
        scientific |= p.name.endswith(".tar.gz")
        nested_record = bool(set(p.parts) & {"qa", "code_and_provenance", "code_versions", "protocol"})
        if scientific or (nested_record and p.suffix in {".md", ".txt", ".py", ".bib"}):
            schedule(p, "保留旧构建目录内的数据、日志及来源材料", EVIDENCE / "旧目录嵌套证据" / row["path"])


def salvage_archives(rows):
    """Keep unique data/audit members before deleting old document packages."""
    pool = {}
    for row in rows:
        if row["action"] == "move":
            pool.setdefault(row["sha256"], row["destination"])
    for p in files(CURRENT / "source_data"):
        pool.setdefault(sha(p), rel(p))
    evidence_parts = {"qa", "source_data", "supplement_data", "review_package", "revision_evidence",
                      "code_versions", "code_and_provenance", "literature", "corpus", "protocol",
                      "data", "csv", "figure_data", "source_static", "author_working", "guards"}
    receipts = []
    for row in rows:
        p = ROOT / row["path"]
        if row["action"] != "delete" or p.suffix != ".zip":
            continue
        with zipfile.ZipFile(p) as z:
            for member in z.infolist():
                q = Path(member.filename.replace("\\", "/"))
                if member.is_dir():
                    continue
                is_evidence = bool(set(q.parts) & evidence_parts) or q.suffix.lower() in {".json", ".csv", ".npz", ".npy", ".pt", ".pth", ".log", ".bib"}
                if not is_evidence:
                    continue
                assert not q.is_absolute() and ".." not in q.parts, member.filename
                data = z.read(member)
                digest = hashlib.sha256(data).hexdigest()
                canonical = pool.get(digest)
                saved = canonical is None
                if saved:
                    dest = checked(EVIDENCE / "旧压缩包唯一证据" / p.stem / q)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if dest.exists():
                        assert sha(dest) == digest
                    else:
                        dest.write_bytes(data)
                    canonical = rel(dest)
                    pool[digest] = canonical
                receipts.append(dict(archive=row["path"], member=member.filename, sha256=digest,
                                     retained=canonical, extracted=saved, bytes=len(data)))
    (OUT / "archive_evidence.json").write_text(json.dumps(receipts, ensure_ascii=False, indent=2), encoding="utf-8")
    return receipts


def apply():
    receipt = OUT / "operations.json"
    rows = json.loads((receipt if receipt.exists() else OUT / "plan.json").read_text(encoding="utf-8"))
    # A single digest per affected file binds both the removal record and all moves.
    def bind(row):
        if "sha256" not in row:
            row["sha256"] = sha(checked(ROOT / row["path"]))
        return row
    with ThreadPoolExecutor(max_workers=8) as executor:
        for i, row in enumerate(executor.map(bind, rows)):
            if i % 500 == 0:
                print("Hashing", i, row["path"], flush=True)
    (OUT / "operations.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    archive_receipt = OUT / "archive_evidence.json"
    salvage = json.loads(archive_receipt.read_text(encoding="utf-8")) if archive_receipt.exists() else salvage_archives(rows)
    def execute(row):
        p = checked(ROOT / row["path"])
        if not p.exists():
            if row["action"] == "move":
                assert (ROOT / row["destination"]).is_file()
            return
        if row["action"] == "move":
            dest = checked(ROOT / row["destination"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            assert not dest.exists(), dest
            p.rename(dest)
        else:
            p.unlink()
    with ThreadPoolExecutor(max_workers=8) as executor:
        for i, _ in enumerate(executor.map(execute, rows)):
            if i % 500 == 0:
                print("Organizing", i, flush=True)
    # Remove only empty directories inside the explicit cleanup roots.
    for root in [CURRENT, ROOT / "99_历史归档/历史稿件", ROOT / "99_历史归档/历史交付包",
                 ROOT / "02_公共资源/运行缓存", ROOT / ".pytest_cache", ROOT / "99_历史归档/旧工作目录/$root"]:
        for base, _, _ in os.walk(root, topdown=False):
            p = checked(Path(base))
            if not any(p.iterdir()):
                p.rmdir()
    # Preserve alias resolution for each moved evidence file, including callers
    # that use the pre-migration legacy prefix.
    mapfile = ROOT / "02_公共资源/项目管理/目录迁移/path_map.json"
    mapping = json.loads(mapfile.read_text(encoding="utf-8"))
    original = dict(mapping)
    for row in rows:
        if row["action"] != "move":
            continue
        src, dst = row["path"], row["destination"]
        mapping[src] = dst
        for alias, target in original.items():
            if src == target or src.startswith(target + "/"):
                mapping[alias + src[len(target):]] = dst
    mapfile.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    def mismatch(r):
        return r["destination"] if r["action"] == "move" and sha(ROOT / r["destination"]) != r["sha256"] else None
    with ThreadPoolExecutor(max_workers=8) as executor:
        mismatches = list(filter(None, executor.map(mismatch, rows)))
    assert not mismatches, mismatches
    summary = dict(operations=len(rows), counts=dict(Counter(r["action"] for r in rows)),
                   deleted_bytes=sum(r["bytes"] for r in rows if r["action"] == "delete"),
                   extracted_unique_bytes=sum(r["bytes"] for r in salvage if r["extracted"]),
                   move_hash_mismatches=mismatches, worker_task="45c64b4c541c4a2d83e02add465c775d",
                   worker_model="group/gemini-executor (specific serving model not disclosed)")
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.apply:
        apply()
    else:
        plan()
        rows = sorted(actions.values(), key=lambda x: x["path"])
        (OUT / "plan.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"operations": len(rows), "counts": dict(Counter(r["action"] for r in rows)),
                          "MiB": {a: round(sum(r["bytes"] for r in rows if r["action"] == a) / 2**20, 2) for a in ["delete", "move"]}}, ensure_ascii=False))
