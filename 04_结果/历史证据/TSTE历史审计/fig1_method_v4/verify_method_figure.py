"""Validate stored calibration values, request arithmetic and the compiled method figure."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
import hashlib
import json
import re
import zipfile
import numpy as np
import pandas as pd
import fitz

Q=Path(__file__).resolve().parent;B=Q.parents[1];ROOT = Path(repository_root())
checks=[]
def check(name,ok,**extra):checks.append(dict(name=name,passed=bool(ok),**extra))
binding=json.loads((Q/"SOURCE_BINDING.json").read_text())
p=ROOT/binding["source"]
check("existing action archive unchanged",hashlib.sha256(p.read_bytes()).hexdigest()==binding["sha256"])
z=np.load(p)
profile=pd.read_csv(B/"source_data/v4/historical_offsets.csv")
check("exact stored residual quantiles",np.array_equal(profile.calibration_q,[.9,.925,.95,.975,.99]) and np.allclose(profile.offset_kw,z["offsets"],rtol=0,atol=1e-12))
e=json.loads((B/"source_data/v4/request_example.json").read_text())
check("same existing fitted instance",e["seed"]==201 and e["rule"]=="P1/HGB" and e["calibration_q"]==.95)
check("raw estimate copied exactly",e["raw_kw"]==float(z["raw"][0,0]))
check("chosen historical offset copied exactly",e["offset_kw"]==float(z["offsets"][2]))
check("request construction",e["reserve_kw"]==max(e["raw_kw"]+e["offset_kw"],0))
check("example timestamp and eligibility",int(z["anchors"][0])==157824 and bool(z["mask"][0,0]))
check("no fitting or recalibration",all(binding[k]==0 for k in ["new_fits","new_calibrations","new_resampling"]))
receipt=json.loads((B/"qa/visual_redesign_20261027/DATA_RECEIPT.json").read_text())
check("all prior result sources unchanged",all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in receipt["source_hashes"].items()),count=len(receipt["source_hashes"]))
with zipfile.ZipFile(B/"tste_fig1_v3.zip") as old:
    names=[n for n in old.namelist() if n.startswith("figures/v2/")]
    check("all three quantitative figures unchanged",len(names)==9 and all((B/n).read_bytes()==old.read(n) for n in names))
for name in ["alignment","collisions","svg_audit"]:
    r=json.loads((Q/(name+".json")).read_text(encoding="utf-8-sig"))
    check(name,r["verdict"]=="PASS")
fig=fitz.open(B/"figures/v4/fig1_overview.pdf")
spans=[s for b in fig[0].get_text("dict")["blocks"] for l in b.get("lines",[]) for s in l.get("spans",[]) if s["text"].strip()]
check("font floor at final physical size",min(s["size"] for s in spans)>=7,minimum=min(s["size"] for s in spans))
check("no cropped text",all(s["bbox"][0]>=0 and s["bbox"][1]>=0 and s["bbox"][2]<=fig[0].rect.width and s["bbox"][3]<=fig[0].rect.height for s in spans))
check("IEEE double-column width",abs(fig[0].rect.width-515.52)<.01)
svg=(B/"figures/v4/fig1_overview.svg").read_text(encoding="utf-8")
check("editable SVG text","<text" in svg)
main=fitz.open(B/"manuscript.pdf");texts=[p.get_text() for p in main]
check("new method illustration actually compiled",any("Residual-offset correction" in t and "258.0" in t for t in texts))
check("old opaque rule icon removed",not any("Reserve rule" in t for t in texts))
check("all four figure captions present",all(any(f"Fig. {n}." in t for t in texts) for n in range(1,5)))
fig_pages=[i for i,t in enumerate(texts) if any(f"Fig. {n}." in t for n in range(1,5))]
ref_page=next(i for i,t in enumerate(texts) if "REFERENCES" in t)
check("figures before references",max(fig_pages)<=ref_page)
check("page limit",len(main)<=10,pages=len(main))
log=(B/"build/manuscript.log").read_text(encoding="utf-8",errors="replace")
check("no overflow or missing references",not re.search(r"Overfull|LaTeX Warning: (?:Citation|Reference).*undefined",log))
result=dict(status="PASS" if all(c["passed"] for c in checks) else "FAIL",checks=checks)
(Q/"FINAL_CHECKS.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(result["status"],sum(c["passed"] for c in checks),"/",len(checks))
for c in checks:
    if not c["passed"]:print(c)
raise SystemExit(0 if result["status"]=="PASS" else 1)
