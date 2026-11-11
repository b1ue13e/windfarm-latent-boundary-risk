"""Build a minimal, isolated submission copy without changing research assets."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
import hashlib
import json
import os
import re
import shutil
import subprocess
import zipfile
import fitz

Q = Path(__file__).resolve().parent
B = Q.parents[1]
DEST = B / "submission/TSTE_minimal_20261027"
STAGE = Q / "source_stage"
EXTRACT = Q / "source_rebuild"
for directory in (DEST, STAGE, EXTRACT):
    directory.mkdir(parents=True, exist_ok=False)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

entries = ["manuscript.tex", "supplementary.tex"]
sources = set(entries + ["references.bib"])
graphics = set()
for name in entries:
    text = (B / name).read_text(encoding="utf-8")
    sections = re.findall(r"\\input\{([^}]+)\}", text)
    for section in sections:
        filename = section + ".tex"
        sources.add(filename)
        text += "\n" + (B / filename).read_text(encoding="utf-8")
    graphics.update(re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text))
sources.update(graphics)
assert len(graphics) == 4
protected = {p: digest(B / p) for p in sources}
protected.update({p: digest(B / p) for p in ["manuscript.pdf", "supplementary.pdf"]})
for name in sorted(sources):
    target = STAGE / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(B / name, target)

main = STAGE / "manuscript.tex"
text = main.read_text(encoding="utf-8")
old = r"\markboth{Working Manuscript}{Li and Du: Incremental Telemetry for Wind Power Reserve Decisions}"
new = r"\markboth{Incremental Telemetry for Wind Power Reserve Decisions}{Li and Du: Incremental Telemetry for Wind Power Reserve Decisions}"
assert text.count(old) == 1
main.write_text(text.replace(old, new), encoding="utf-8")
for path in [Path("E:/MiKTeX/tex/latex/IEEEtran/IEEEtran.cls"),
             Path("E:/MiKTeX/bibtex/bst/IEEEtran/IEEEtran.bst")]:
    shutil.copy2(path, STAGE / path.name)
for stem in ("manuscript", "supplementary"):
    shutil.copy2(B / "build" / (stem + ".bbl"), STAGE / (stem + ".bbl"))
(STAGE / "BUILD_README.txt").write_text(
    "Compile with XeLaTeX and BibTeX from this directory.\n"
    "Main file: manuscript.tex. Supplementary file: supplementary.tex.\n"
    "Required installed fonts: Times New Roman and Arial.\n"
    "For each STEM (manuscript or supplementary), run:\n"
    "  xelatex -interaction=nonstopmode -halt-on-error STEM.tex\n"
    "  bibtex STEM\n"
    "  xelatex -interaction=nonstopmode -halt-on-error STEM.tex\n"
    "  xelatex -interaction=nonstopmode -halt-on-error STEM.tex\n"
    "The bundled .bbl files also allow two XeLaTeX passes without BibTeX.\n"
    "Figure PDFs are embedded quantitative/vector and illustration assets.\n"
    "IEEEtran class and bibliography style retain their original license headers.\n",
    encoding="utf-8")
source_zip = DEST / "03_LaTeX_source.zip"
with zipfile.ZipFile(source_zip, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(STAGE.rglob("*")):
        if path.is_file():
            archive.write(path, path.relative_to(STAGE).as_posix())
with zipfile.ZipFile(source_zip) as archive:
    assert archive.testzip() is None
    archive.extractall(EXTRACT)

env = os.environ.copy()
env["BIBINPUTS"] = str(EXTRACT) + os.pathsep
xe = "E:/MiKTeX/miktex/bin/x64/xelatex.exe"
bib = "E:/MiKTeX/miktex/bin/x64/bibtex.exe"
build_checks = []
for stem in ("manuscript", "supplementary"):
    commands = [[xe, "-interaction=nonstopmode", "-halt-on-error", stem + ".tex"],
                [bib, stem],
                [xe, "-interaction=nonstopmode", "-halt-on-error", stem + ".tex"],
                [xe, "-interaction=nonstopmode", "-halt-on-error", stem + ".tex"]]
    for n, command in enumerate(commands, 1):
        run = subprocess.run(command, cwd=EXTRACT, env=env, capture_output=True, timeout=120)
        (Q / (stem + f"_pass{n}.txt")).write_bytes(run.stdout + run.stderr)
        if run.returncode:
            raise RuntimeError((run.stdout + run.stderr).decode("utf-8", errors="replace")[-4000:])
    log = (EXTRACT / (stem + ".log")).read_text(encoding="utf-8", errors="replace")
    warnings = re.findall(r"Overfull[^\n]*|LaTeX Warning: (?:Citation|Reference)[^\n]*undefined|LaTeX Font Warning:[^\n]*", log)
    assert not warnings, warnings
    name = "01_Manuscript.pdf" if stem == "manuscript" else "02_Supplementary.pdf"
    shutil.copy2(EXTRACT / (stem + ".pdf"), DEST / name)
    original = fitz.open(B / (stem + ".pdf"))
    revised = fitz.open(DEST / name)
    assert len(original) == len(revised)
    before = " ".join(" ".join(p.get_text().split()) for p in original)
    after = " ".join(" ".join(p.get_text().split()) for p in revised)
    if stem == "manuscript":
        before = before.replace("WORKING MANUSCRIPT", "")
        after = after.replace("INCREMENTAL TELEMETRY FOR WIND POWER RESERVE DECISIONS", "")
    assert " ".join(before.split()) == " ".join(after.split()), stem + " reader text differs"
    build_checks.append(dict(document=stem, pages=len(revised), clean_compile=True, reader_text_preserved=True))
    print(stem, len(revised), "pages; isolated build and content comparison PASS", flush=True)

assert protected == {p: digest(B / p) for p in protected}
(DEST / "00_投稿说明.txt").write_text(
    "TSTE 最小投稿包 | 2026-10-27\n\n"
    "论文：Current Power as Incremental Telemetry for Wind Power Reserve Decisions\n\n"
    "01_Manuscript.pdf：正文，7页、4幅主图，上传为主论文。\n"
    "02_Supplementary.pdf：补充材料，单独上传为补充文件。\n"
    "03_LaTeX_source.zip：完整编译源包，按系统要求上传或留作后续使用。\n"
    "本说明供作者使用，不上传为论文附件。\n\n"
    "源包已在独立目录解压并重新编译，含全部引用分节、四幅图、参考文献、IEEEtran类文件及书目样式。\n"
    "投稿副本只去掉工作稿状态页眉；正文、图注、图形数据及补充材料内容保持。\n\n"
    "提交前由作者确认：姓名/顺序/单位/邮箱/ORCID；基金与利益冲突；全体作者同意及一稿一投；数据代码公开范围；现有AI辅助声明。包内未代填或代确认这些事实。\n\n"
    "投稿入口：https://ieee.atyponrex.com/journal/tste-pes\n"
    "官方要求：https://ieee-pes.org/publications/authors-kit/information-for-authors-of-ieee-power-energy-society-transactions-papers/\n"
    "官方上传说明：https://ieee-pes.org/publications/how-to-get-published/submit-a-transaction-or-journal/\n"
    "按2026-10-27核对的初投稿要求整理。未向期刊上传或提交。\n",
    encoding="utf-8-sig")
outer = DEST.parent / "TSTE_minimal_20261027.zip"
with zipfile.ZipFile(outer, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(DEST.iterdir()):
        archive.write(path, path.name)
with zipfile.ZipFile(outer) as archive:
    assert len(archive.namelist()) == 4 and archive.testzip() is None
report = dict(status="READY_WITH_AUTHOR_CHECKS", output=str(outer), megabytes=round(outer.stat().st_size/1024**2, 2),
              files=[p.name for p in sorted(DEST.iterdir())], source_files=len(list(STAGE.rglob("*"))),
              builds=build_checks, protected_sources_unchanged=True,
              graphic_assets_unchanged=all(digest(B / g) == digest(EXTRACT / g) for g in graphics),
              no_experiments=True, submitted=False)
(Q / "PACKAGE_CHECKS.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2), flush=True)
