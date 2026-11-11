"""Check the writing artifacts against preserved results, without refitting."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_代码/工程"))
from repo_paths import Path, repository_root
import csv
import hashlib
import json
import re
import fitz

BASE = Path(__file__).resolve().parents[1]
ROOT = Path(repository_root())
import os
REPORT_DIR = Path(os.environ.get("REPRODUCTION_OUTPUT_DIR", str(BASE / "qa"))) / "draft"
if "REPRODUCTION_OUTPUT_DIR" not in os.environ:
    REPORT_DIR = BASE / "qa"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
checks = []

def record(name, passed, **evidence):
    checks.append(dict(name=name, passed=bool(passed), **evidence))

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8-sig")

bib = (BASE / "references.bib").read_text(encoding="utf-8")
keys = set(re.findall(r"@\w+\{([^,]+),", bib))
sources = [BASE / "manuscript.tex", BASE / "supplementary.tex"]
sources += list((BASE / "sections").glob("*_body.tex"))
sources += [BASE / "sections/supplementary_tables.tex"]
tex = "\n".join(p.read_text(encoding="utf-8") for p in sources)
used = {k.strip() for block in re.findall(r"\\cite\{([^}]+)\}", tex) for k in block.split(",")}
record("citation keys", used <= keys, missing=sorted(used-keys), cited_count=len(used))
record("conversion artifacts", "*** Add File:" not in tex and r"\n***" not in tex)
record("prose em dash", "\u2014" not in tex and "---" not in tex)
labels = re.findall(r"\\label\{([^}]+)\}", tex)
record("unique labels", len(labels)==len(set(labels)))
main = (BASE/"manuscript.tex").read_text(encoding="utf-8")
ab = main.split(r"\begin{abstract}",1)[1].split(r"\end{abstract}",1)[0]
record("abstract word range", 150<=len(ab.split())<=200, words=len(ab.split()))

original = list(csv.DictReader(read("analyses/praw_supplement_v3_execution_20261021/primary_comparisons.csv").splitlines()))
exported = list(csv.DictReader((BASE/"source_data/fig1_coordinates.csv").read_text(encoding="utf-8-sig").splitlines()))
record("measurement figure coordinates", all(any(all(o.get(k)==r.get(k) for k in r) for o in original) for r in exported), rows=len(exported))
old = json.loads(read("analyses/independent_confirmation_execution_20261019/derived/summary.json"))
new = json.loads(read("experiments/mainline_supplement_20261026/FINAL_RESULTS.json"))
fig2 = list(csv.DictReader((BASE/"source_data/fig2_coordinates.csv").read_text(encoding="utf-8-sig").splitlines()))
for row, source in zip(fig2, (old,new)):
    vals = [source["relative_cost_point"]*100] + [v*100 for v in source["relative_cost_interval"]]
    record("cross-year figure "+row["year"], all(abs(float(row[k])-v)<1e-10 for k,v in zip(("cost","low","high"), vals)))

for stem in ("manuscript", "supplementary"):
    pdf = BASE / f"{stem}.pdf"
    doc = fitz.open(pdf)
    text = "\n".join(page.get_text() for page in doc)
    (REPORT_DIR/f"{stem}_extracted.txt").write_text(text, encoding="utf-8")
    forbidden = [r"\b(?:audit|receipt|PBS|sha256|hash|gate)\b", r"[A-Z]:\\", r"\*\*\* Add File:", r"\[\?\]", r"AUTHOR_INPUT_NEEDED"]
    found = [p for p in forbidden if re.search(p,text,re.I)]
    record(stem+" clean reader text", not found, found=found)
    overflow=[]
    for i,page in enumerate(doc):
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines",[]):
                for span in line.get("spans",[]):
                    x0,y0,x1,y1=span["bbox"]
                    if span["text"].strip() and (x0<0 or y0<0 or x1>page.rect.width+1 or y1>page.rect.height+1):
                        overflow.append([i+1,span["text"]])
    record(stem+" page boundaries", not overflow, overflow=overflow)
    record(stem+" page count", stem!="manuscript" or len(doc)<=10, pages=len(doc))
    fonts=sorted({s["font"] for pg in doc for b in pg.get_text("dict")["blocks"] for l in b.get("lines",[]) for s in l.get("spans",[])})
    record(stem+" embedded body font", any("TimesNewRoman" in f for f in fonts), fonts=fonts)
    record(stem+" root PDF matches build", hashlib.sha256(pdf.read_bytes()).digest()==hashlib.sha256((BASE/"build"/f"{stem}.pdf").read_bytes()).digest())

# Verify the point accounting as typeset. Rounding tolerance is below one last reported digit per component.
for line in (BASE/"sections/results_body.tex").read_text(encoding="utf-8").splitlines():
    if " & " not in line: continue
    cells=[c.strip() for c in line.replace(r"\\","").split("&")]
    if len(cells) not in (6,7): continue
    try: c,r,u=map(float,cells[2:5])
    except ValueError: continue
    record("typeset accounting "+" / ".join(cells[:2]), abs(c-r-10*u)<0.001)

report=dict(status="PASS" if all(c["passed"] for c in checks) else "FAIL",checks=checks,
            scope="Writing consistency, source coordinates and PDF structure. No new statistical inference or venue certification.")
(REPORT_DIR/"FINAL_CHECKS.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(report["status"], f"{sum(c['passed'] for c in checks)}/{len(checks)} checks")
for c in checks:
    if not c["passed"]: print(c)
raise SystemExit(0 if report["status"]=="PASS" else 1)
