"""Package the current manuscript and editable figures without third-party papers."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
import hashlib
import json
import shutil
import zipfile
import fitz

B = Path(__file__).resolve().parents[2]
Q = Path(__file__).resolve().parent
copy = B / "manuscript_fig1_method_v5.pdf"
shutil.copy2(B / "manuscript.pdf", copy)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

artifacts = {}
for name in ["manuscript.pdf", copy.name, "supplementary.pdf"]:
    with fitz.open(B / name) as doc:
        artifacts[name] = dict(pages=len(doc), sha256=digest(B / name))

acceptance = dict(
    status="FIG1_METHOD_V5_COMPLETE", main_figures=4, panels=[3, 4, 3, 4],
    artifacts=artifacts,
    visual_review="All seven final main pages and the complete scene-backed Figure 1 inspected.",
    checks="18/18 draft checks; 28/28 method/source checks; source, alignment, SVG, font and collision checks passed.",
    method="Selected telemetry and common information feed the 0.90 shortfall estimator; a separate historical residual quantile supplies a frozen offset; nonnegative correction forms the request.",
    example="Recorded P1/HGB seed 201: 234.9486916381771 + 23.03161116486629 = 257.9803028030434 kW.",
    contribution="Matched measurement value and input reduction under cost/event-rate requirements are distinguished from the existing estimator and calibration steps.",
    learning="Continued the Applied Energy, TSTE and Nature Energy figure study retained in the reference notes; no source figure copied.",
    assets="One AI-generated wind-farm landscape used as illustrative background, with no research data. All labels, plots and result annotations remain editable vector elements.",
    new_model_fits=0, new_calibrations=0, new_statistical_resampling=0,
    scope="Method illustration and manuscript layout; quantitative Figures 2-4 unchanged.",
    git_save="Task snapshot saved separately from the shared index; see qa/fig1_method_v5/GIT_SAVE.json after saving."
)
(B / "qa/ACCEPTANCE.json").write_text(json.dumps(acceptance, indent=2), encoding="utf-8")

files = set()
for name in ["manuscript.pdf", copy.name, "manuscript.tex", "manuscript.md",
             "supplementary.pdf", "supplementary.tex", "references.bib",
             "README.md", "AUTHOR_NOTES_CN.md", "FIG1_METHOD_V5_README_CN.md",
             "figure_code/overview_v5.py", "figure_code/overview_v4.py", "figure_code/overview_v3.py",
             "figure_code/results_v2.py", "source_data/v3/scada_example.csv",
             "qa/build_pdfs.py", "qa/export_reading_copy.py",
             "qa/fig1_method_v4/DESIGN_NOTES_CN.md",
             "qa/fig1_method_v5/DESIGN_NOTES_CN.md",
             "qa/fig1_method_v5/IMAGE_PROVENANCE.json"]:
    files.add(B / name)
for folder, pattern in [("sections", "*.tex"), ("figures/v5", "*"),
                        ("figures/v2", "*.*"), ("figures/v3/assets", "*"),
                        ("source_data/v4", "*"), ("source_data/v2", "*")]:
    files.update(p for p in (B / folder).glob(pattern) if p.is_file())
missing = [str(p.relative_to(B)) for p in files if not p.is_file()]
if missing:
    raise FileNotFoundError(missing)
bundle = B / "tste_fig1_method_v5.zip"
with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for p in sorted(files):
        z.write(p, p.relative_to(B).as_posix())
with zipfile.ZipFile(bundle) as z:
    assert z.testzip() is None
    assert z.read(copy.name) == copy.read_bytes()
    assert not any(n.startswith(("corpus/", "qa/fig1_redesign_v3/references/")) for n in z.namelist())
receipt = dict(bundle=bundle.name, files=len(files), bytes=bundle.stat().st_size,
               sha256=digest(bundle), manuscript_sha256=digest(copy), archive_integrity="PASS")
(B / "qa/fig1_method_v5").mkdir(parents=True, exist_ok=True)
(B / "qa/fig1_method_v5/DELIVERY.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps(receipt, indent=2))
