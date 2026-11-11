"""Package the revised manuscript and the original data required to redraw it."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_代码/工程"))
from repo_paths import Path, repository_root
import hashlib
import json
import shutil
import zipfile
import fitz

Q = Path(__file__).resolve().parent
B = Q.parents[1]
for p in [Q/"FINAL_CHECKS.json", B/"qa/FINAL_CHECKS.json"]:
    assert json.loads(p.read_text())["status"] == "PASS", p
files = {B/p for p in ["manuscript.tex", "manuscript.pdf", "manuscript.md", "supplementary.tex",
    "supplementary.pdf", "references.bib", "README.md", "FIGURES_V14_README_CN.md",
    "figure_code/figures_v14.py", "figure_code/audit_panel_alignment.py", "figure_code/requirements_figures.txt",
    "qa/build_pdfs.py", "qa/export_reading_copy.py", "qa/verify_draft.py",
    "qa/BUILD_MANUSCRIPT.json", "qa/FINAL_CHECKS.json"]}
for folder, pattern in [("sections", "*.tex"), ("figures/v14", "*"), ("source_data/v2", "*.csv"),
    ("source_data/v4", "*"), ("source_data/v10", "*"), ("qa/figure_rebuild_v14", "*.md"),
    ("qa/figure_rebuild_v14", "*.json"), ("qa/figure_rebuild_v14", "verify_v14.py")]:
    files.update(p for p in (B/folder).glob(pattern) if p.is_file())
archive = B/"tste_figures_v14.zip"
guide = """TSTE figure revision v14

Open manuscript.pdf. The supplementary PDF is unchanged.
All five main figures are available as editable SVG, vector PDF and600dpiPNG.

To redraw on another computer:
  pip install -r figure_code/requirements_figures.txt
  python figure_code/figures_v14.py
To compile from a clean directory with XeLaTeX/BibTeX and Times New Roman/Arial:
  python qa/build_pdfs.py --document manuscript
  python qa/export_reading_copy.py
Use --quick only after the bibliography has been built.

The full repository is needed for the scientific source-identity checks in qa.
Those checks use archived records outside this compact drawing package.
No downloaded reference images or full-text papers are redistributed.
"""
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(files):
        z.write(p, p.relative_to(B).as_posix())
    z.writestr("REBUILD.txt", guide)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    members = len(z.namelist())
receipt = dict(main_pdf="manuscript.pdf", pages=len(fitz.open(B/"manuscript.pdf")),
    main_sha256=hashlib.sha256((B/"manuscript.pdf").read_bytes()).hexdigest(),
    archive=archive.name, archive_bytes=archive.stat().st_size, members=members,
    figures=5, panels=16, no_new_experiments=True)
(Q/"DELIVERY.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps(receipt, indent=2))
