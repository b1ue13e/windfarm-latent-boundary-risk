"""Check exact recorded examples, vector exports and the revised manuscript."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
import hashlib
import json
import re
import fitz
import numpy as np
import pandas as pd

Q=Path(__file__).resolve().parent;B=Q.parents[1];ROOT = Path(repository_root())
checks=[]
def check(name,ok,**extra): checks.append(dict(name=name,passed=bool(ok),**extra))
binding=json.loads((Q/"DATA_BINDING.json").read_text())
check("recorded example sources unchanged",all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in binding["source_hashes"].items()))
old=json.loads((B/"qa/visual_redesign_20261027/DATA_RECEIPT.json").read_text())
check("45 prior result sources unchanged",all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in old["source_hashes"].items()))
a=np.load(ROOT/"artifacts/raw_replay_20261015_v2/cache_wtb/physics.npy",mmap_mode="r")[30240:30277,0,:]
s=pd.read_csv(B/"source_data/v3/scada_example.csv")
check("exact unscaled recorded SCADA",len(s)==37 and np.allclose(s.power_kw,a[:,3],rtol=0,atol=1e-10) and np.allclose(s.pitch_deg,a[:,1],rtol=0,atol=1e-12))
z=np.load(ROOT/"experiments/mainline_supplement_20261026/p1/recovered/results/evaluate/8/raw_actions.npz")
sel=(z["anchors"]>=157824)&(z["anchors"]<157968)
d=pd.read_csv(B/"source_data/v3/decision_example.csv")
request=np.maximum(z["raw"][sel,0]+z["offsets"][2],0)
check("all first-day decisions, no interval selection",len(d)==144 and bool(z["mask"][sel,0].all()))
check("existing reserve actions and offset",np.allclose(d.reserve_kw,request,rtol=0,atol=1e-10))
check("exact later shortfalls",np.allclose(d.shortfall_kw,z["shortfall"][sel,0],rtol=0,atol=1e-10))
check("uncovered area uses the correct gap",np.allclose(d.uncovered_kw,np.maximum(d.shortfall_kw-d.reserve_kw,0),rtol=0,atol=1e-10))
check("one-hour decision to target",((pd.to_datetime(d.target_utc)-pd.to_datetime(d.decision_utc)).dt.total_seconds()==3600).all())
for name in ["collisions","alignment","svg_audit"]:
    r=json.loads((Q/(name+".json")).read_text(encoding="utf-8-sig"))
    check(name,r["verdict"]=="PASS")
f=fitz.open(B/"figures/v3/fig1_overview.pdf")
spans=[s for b in f[0].get_text("dict")["blocks"] for l in b.get("lines",[]) for s in l.get("spans",[]) if s["text"].strip()]
check("actual final-size text minimum",min(s["size"] for s in spans)>=7)
check("no cropped vector text",all(s["bbox"][0]>=0 and s["bbox"][1]>=0 and s["bbox"][2]<=f[0].rect.width and s["bbox"][3]<=f[0].rect.height for s in spans))
check("no formula boxes",not re.search(r"max\(|C =|F −|bq",f[0].get_text()))
check("vector width",abs(f[0].rect.width-515.52)<.01)
svg=(B/"figures/v3/fig1_overview.svg").read_text(encoding="utf-8")
check("SVG has editable text","<text" in svg)
check("all formats exported",all((B/"figures/v3"/("fig1_overview."+ext)).exists() for ext in ["pdf","svg","png"]))
main=fitz.open(B/"manuscript.pdf"); texts=[p.get_text() for p in main]
check("four figures in main paper",all(any(f"Fig. {n}." in t for t in texts) for n in range(1,5)))
check("new Fig1 compiled",any("What the reserve request covers" in t for t in texts))
check("old formula graphic removed",not any("Reserve-layer input comparisons" in t for t in texts))
check("within page limit",len(main)<=10,pages=len(main))
log=(B/"build/manuscript.log").read_text(encoding="utf-8",errors="replace")
check("no overflow or missing references",not re.search(r"Overfull|LaTeX Warning: (?:Citation|Reference).*undefined",log))
check("no new fitting or inference",all(binding[k]==0 for k in ["new_fits","new_calibrations","new_resampling"]))
result=dict(status="PASS" if all(c["passed"] for c in checks) else "FAIL",checks=checks)
(Q/"FINAL_CHECKS.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(result["status"],sum(c["passed"] for c in checks),"/",len(checks))
for c in checks:
    if not c["passed"]:print(c)
raise SystemExit(0 if result["status"]=="PASS" else 1)
