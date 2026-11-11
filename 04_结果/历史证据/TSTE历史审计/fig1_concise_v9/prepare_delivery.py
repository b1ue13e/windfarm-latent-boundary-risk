"""Package the revised figure and typeset reading page, without changing results."""
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

Q=Path(__file__).resolve().parent
B=Q.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
doc=fitz.open(B/"manuscript.pdf")
assert len(doc)==7
assert "Fig. 1." in doc[1].get_text() and "Historical calibration" in doc[1].get_text()
shutil.copy2(B/"manuscript.pdf",B/"manuscript_fig1_concise_v9.pdf")
page=fitz.open();page.insert_pdf(doc,from_page=1,to_page=1)
target=B/"manuscript_fig1_concise_v9_page2.pdf"
if target.exists():target.unlink()
page.save(target)
(Q/"pages").mkdir(exist_ok=True)
for i,p in enumerate(doc):
    p.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(Q/"pages"/f"page_{i+1}.png")
fig=fitz.open(B/"figures/v9/fig1_overview.pdf")
fig[0].get_pixmap(matrix=fitz.Matrix(2,2)).save(Q/"preview_144.png")

provenance=json.loads((B/"qa/fig1_nature_v8/IMAGE_PROVENANCE.json").read_text(encoding="utf-8"))
provenance["revision"]="Reused the same generated illustration; text reduced and estimation/correction redrawn as vector operations. No new generation."
provenance["original_prompt_directory"]="qa/fig1_nature_v8"
(Q/"IMAGE_PROVENANCE.json").write_text(json.dumps(provenance,indent=2),encoding="utf-8")
print(f"Delivery PDF copied; {len(doc)} pages rendered and Figure 1 extracted.")
