"""Record checks and bundle only the author's revised artwork and plotting data."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
import hashlib
import json
import zipfile

Q=Path(__file__).resolve().parent;B=Q.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks=json.loads((Q/"FINAL_CHECKS.json").read_text())
draft=json.loads((B/"qa/FINAL_CHECKS.json").read_text())
assert checks["status"]==draft["status"]=="PASS"
report=dict(status="FIG1_NATURE_V8_RENDERED_AND_VERIFIED",pages=7,main_figures=4,
    checks=f"{sum(c['passed'] for c in checks['checks'])}/{len(checks['checks'])} source, data and scene checks; {sum(c['passed'] for c in draft['checks'])}/{len(draft['checks'])} manuscript checks",
    artifacts={n:sha(B/n) for n in ["manuscript_fig1_nature_v8.pdf",
        "manuscript_fig1_nature_v8_page2.pdf","manuscript.pdf","figures/v8/fig1_overview.pdf"]},
    visual_review="All seven article pages inspected; final Figure 1 page checked after correcting top label margin.",
    structure="Continuous illustrated field scene, open method annotations and attached quantitative plots; no screen enclosures or three-card lower row",
    data_preservation="Original physical/action records and 45 prior result sources unchanged; Figures 2-4 byte-identical",
    new_fits=0,new_inference=0,new_calibrations=0,new_resampling=0,
    static_preflight_note="Only warning: no TIFF; main deliverables are vector PDF/SVG with embedded high-resolution illustration and a 600 dpi PNG preview",
    illustration="Generated conceptual artwork; all text, quantitative data and arrows are independently drawn vector objects",
    git_snapshot="See qa/fig1_nature_v8/GIT_SAVE.json")
(B/"qa/ACCEPTANCE.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
paths=[B/"FIG1_NATURE_V8_README_CN.md",B/"figure_code/overview_v8.py",B/"figure_code/overview_v3.py"]
paths += [B/"figures/v8"/f"fig1_overview.{ext}" for ext in ["pdf","svg","png"]]
paths += [B/"figures/v8/assets/illustrated_windfarm_open.png"]
paths += [B/n for n in ["source_data/v3/scada_example.csv","source_data/v3/decision_example.csv",
    "source_data/v4/historical_offsets.csv","source_data/v4/request_example.json"]]
paths += [Q/n for n in ["IMAGE_PROVENANCE.json","GENERATION_PROMPT.txt","EDIT_PROMPT.txt"]]
with zipfile.ZipFile(B/"tste_fig1_nature_v8.zip","w",compression=zipfile.ZIP_DEFLATED) as z:
    for p in paths:z.write(p,p.relative_to(B).as_posix())
print("Figure bundle ready:",len(paths),"files; third-party reference images excluded.")
