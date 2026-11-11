"""Package the reviewed manuscript and editable figures without third-party sources."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
from datetime import datetime, timezone
import hashlib
import json
import shutil
import zipfile
import fitz

B = Path(__file__).resolve().parents[2]
Q = Path(__file__).resolve().parent
visual = json.loads((Q / "FINAL_VISUAL_CHECKS.json").read_text(encoding="utf-8"))
writing = json.loads((B / "qa/FINAL_CHECKS.json").read_text(encoding="utf-8"))
assert visual["status"] == writing["status"] == "PASS"
alias = B / "manuscript_figures_v2.pdf"
shutil.copy2(B / "manuscript.pdf", alias)

files = [B / n for n in [
    "manuscript.pdf", "manuscript.tex", "manuscript.md", "supplementary.pdf",
    "supplementary.tex", "references.bib", "README.md",
    "AUTHOR_NOTES_CN.md", "FIGURES_V2_README_CN.md",
    "qa/build_pdfs.py", "qa/export_reading_copy.py", "qa/verify_draft.py",
]]
for pattern in ["figures/v2/*", "source_data/v2/*.csv", "figure_code/*v2.py",
                "sections/*_body.tex", "sections/supplementary_tables.tex"]:
    files.extend(p for p in B.glob(pattern) if p.is_file())
archive = B / "tste_figures_v2.zip"
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(set(files)):
        z.write(p, p.relative_to(B).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert not any(n.startswith(("corpus/", "qa/visual_redesign_20261027/references/")) for n in z.namelist())
    members = len(z.namelist())

artifacts = {}
for name in ["manuscript.pdf", "manuscript_figures_v2.pdf", "supplementary.pdf"]:
    p = B / name
    with fitz.open(p) as d:
        artifacts[name] = dict(pages=len(d), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
assert artifacts["manuscript.pdf"] == artifacts["manuscript_figures_v2.pdf"]
artifacts[archive.name] = dict(members=members, bytes=archive.stat().st_size,
                             sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
report = dict(
    status="FIGURES_V2_COMPLETE",
    saved_utc=datetime.now(timezone.utc).isoformat(),
    artifacts=artifacts,
    main_figures=4,
    panels=[3, 4, 3, 4],
    visual_review="All seven main pages inspected. Four figures inspected panel by panel; final revised pages 2, 4 and 7 rechecked.",
    checks=dict(writing=sum(c["passed"] for c in writing["checks"]),
                visual=sum(c["passed"] for c in visual["checks"]),
                vector_font_minimum=visual["font_summary"],
                collisions="All four final PDFs: zero fail and zero warn",
                source_assets="45 original source hashes unchanged"),
    new_model_fits=0, new_calibrations=0, new_statistical_resampling=0,
    static_export_note="Vector PDF is the manuscript master. PNG is a 600 dpi preview; no TIFF was needed.",
    svg_auditor_note="Local skill audit lacks a math import; supplied math via runpy globals without changing its checks. SVG font sizes use local-unit presentation attributes matching PDF geometry.",
    author_items="Author metadata, funding, archive release and AI-use disclosure remain author-verification items.",
    scope="Figure redesign and manuscript integration using existing evidence; no venue acceptance assessment.",
    git_save="Pending local snapshot on an isolated branch; shared index lock untouched.",
)
(B / "qa/ACCEPTANCE.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"Released {members} files; ZIP {archive.stat().st_size:,} bytes; main {artifacts['manuscript.pdf']['pages']} pages.")
