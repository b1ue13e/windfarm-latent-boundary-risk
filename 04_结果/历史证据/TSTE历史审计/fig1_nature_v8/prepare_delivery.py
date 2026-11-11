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
assert "Fig. 1." in doc[1].get_text() and "Earlier residuals" in doc[1].get_text()
shutil.copy2(B/"manuscript.pdf",B/"manuscript_fig1_nature_v8.pdf")
page=fitz.open();page.insert_pdf(doc,from_page=1,to_page=1)
target=B/"manuscript_fig1_nature_v8_page2.pdf"
if target.exists():target.unlink()
page.save(target)
(Q/"pages").mkdir(exist_ok=True)
for i,p in enumerate(doc):
    p.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(Q/"pages"/f"page_{i+1}.png")
fig=fitz.open(B/"figures/v8/fig1_overview.pdf")
fig[0].get_pixmap(matrix=fitz.Matrix(2,2)).save(Q/"preview_144.png")

provenance=dict(date="2026-10-27",tool="OpenAI built-in image_gen.imagegen",
    model_version="Not exposed by the tool; no version inferred",
    purpose="Conceptual wind-farm illustration only; all labels, arrows and measured plots are vector overlays",
    asset="figures/v8/assets/illustrated_windfarm_open.png",
    asset_sha256=sha(B/"figures/v8/assets/illustrated_windfarm_open.png"),
    reference="Earlier generated wind-farm artwork; no third-party figure pixels supplied to the generator",
    generator_inputs="Visual brief and generated scene only; no manuscript or measurements",
    corrections="Terrain cleared around annotations; exact text, arrows and all plotted values drawn separately",
    evidence_boundary="Conceptual site, not a field deployment or map; SDWPF and Towie are different examples",
    final_prompt_files=["GENERATION_PROMPT.txt","EDIT_PROMPT.txt"],
    policy_checked="2026-10-27",
    policy_url="https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/",
    disclosure="Figure caption states conceptual setting; Acknowledgment identifies image generation and vector assistance")
(Q/"IMAGE_PROVENANCE.json").write_text(json.dumps(provenance,indent=2),encoding="utf-8")
print(f"Delivery PDF copied; {len(doc)} pages rendered and Figure 1 extracted.")
