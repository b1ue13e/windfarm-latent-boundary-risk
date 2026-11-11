"""Verify scene data against immutable physical records and recorded actions."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
import json
import hashlib
import re
import zipfile
import numpy as np
import pandas as pd
import fitz

Q=Path(__file__).resolve().parent
B=Q.parents[1]
ROOT = Path(repository_root())
checks=[]
def check(name, ok, **info):
    checks.append(dict(name=name,passed=bool(ok),**info))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

binding=json.loads((B/"qa/fig1_redesign_v3/DATA_BINDING.json").read_text())
old=json.loads((B/"qa/visual_redesign_20261027/DATA_RECEIPT.json").read_text())
check("original physical and action records unchanged",all(sha(ROOT/p)==v for p,v in binding["source_hashes"].items()))
check("45 prior numerical result sources unchanged",all(sha(ROOT/p)==v for p,v in old["source_hashes"].items()))
physical=np.load(ROOT/"artifacts/raw_replay_20261015_v2/cache_wtb/physics.npy",mmap_mode="r")[30240:30277,0,:]
s=pd.read_csv(B/"source_data/v3/scada_example.csv")
check("all 37 unscaled physical records",len(s)==37 and np.allclose(s.power_kw,physical[:,3],rtol=0,atol=1e-10) and np.allclose(s.pitch_deg,physical[:,1],rtol=0,atol=1e-12))
z=np.load(ROOT/"experiments/mainline_supplement_20261026/p1/recovered/results/evaluate/8/raw_actions.npz")
sel=(z["anchors"]>=157824)&(z["anchors"]<157968)
d=pd.read_csv(B/"source_data/v3/decision_example.csv")
request=np.maximum(z["raw"][sel,0]+z["offsets"][2],0)
check("all 144 first-day actions remain eligible",len(d)==144 and bool(z["mask"][sel,0].all()))
check("requests equal the recorded fit plus frozen offset",np.allclose(d.reserve_kw,request,rtol=0,atol=1e-10))
check("shortfalls equal the recorded future labels",np.allclose(d.shortfall_kw,z["shortfall"][sel,0],rtol=0,atol=1e-10))
check("orange deficit uses the actual positive gap",np.allclose(d.uncovered_kw,np.maximum(d.shortfall_kw-d.reserve_kw,0),rtol=0,atol=1e-10))
check("target is one hour after every decision",((pd.to_datetime(d.target_utc)-pd.to_datetime(d.decision_utc)).dt.total_seconds()==3600).all())
e=json.loads((B/"source_data/v4/request_example.json").read_text())
check("first action matches the displayed request",e["raw_kw"]==float(z["raw"][sel,0][0]) and e["offset_kw"]==float(z["offsets"][2]) and e["reserve_kw"]==float(request[0]))
manifest=json.loads((Q/"DRAWING_MANIFEST.json").read_text())
for key,values in dict(power_kw=s.power_kw,pitch_deg=s.pitch_deg,reserve_kw=d.reserve_kw,shortfall_kw=d.shortfall_kw).items():
    check("rendered sequence uses every recorded value: "+key,np.array_equal(np.asarray(manifest["plot_series"][key]),values.to_numpy()))
check("plotted values fit inside physical axes",s.power_kw.between(0,1600).all() and s.pitch_deg.between(-1,7).all() and d.reserve_kw.between(0,1100).all() and d.shortfall_kw.between(0,1100).all())
check("no model or statistical rerun",all(manifest[k] for k in ["no_new_fits","no_new_calibrations","no_new_resampling"]))
with zipfile.ZipFile(B/"tste_fig1_method_v5.zip") as oldzip:
    names=[n for n in oldzip.namelist() if re.match(r"figures/v2/fig[234]_",n)]
    check("quantitative Figures 2 to 4 unchanged",len(names)==9 and all((B/n).read_bytes()==oldzip.read(n) for n in names))
for name in ["alignment","collisions","svg_audit"]:
    report=json.loads((Q/(name+".json")).read_text(encoding="utf-8-sig"))
    check(name,report["verdict"]=="PASS")
check("each actual sequence is plotted once",all(v==1 for v in manifest["plot_appearances"].values()) and len(manifest["plot_appearances"])==5)
check("all five historical offsets remain unchanged",np.allclose(manifest["plot_series"]["offset_kw"],z["offsets"],rtol=0,atol=1e-12) and np.array_equal(manifest["plot_series"]["calibration_q"],[.9,.925,.95,.975,.99]))
f=fitz.open(B/"figures/v9/fig1_overview.pdf");p=f[0]
spans=[s for block in p.get_text("dict")["blocks"] for line in block.get("lines",[]) for s in line.get("spans",[]) if s["text"].strip()]
check("final-size font floor",min(s["size"] for s in spans)>=7,minimum=min(s["size"] for s in spans))
check("all vector text stays on canvas",all(s["bbox"][0]>=0 and s["bbox"][1]>=0 and s["bbox"][2]<=p.rect.width+.01 and s["bbox"][3]<=p.rect.height+.01 for s in spans))
check("IEEE double-column width",abs(p.rect.width-515.52)<.01)
check("illustration is separate from quantitative vectors",len(p.get_images(full=True))==1 and isinstance(manifest["generated_artwork"],str))
svg=(B/"figures/v9/fig1_overview.svg").read_text(encoding="utf-8")
check("live SVG labels and embedded illustration","<text" in svg and "<image" in svg and "data:image/png;base64" in svg)
check("essential estimator, calibration and request labels",all(t in p.get_text() for t in ["HGB / MLP","q = 0.95","258.0 kW","234.9 kW","+23.0 kW","Clip at 0"]))
main=fitz.open(B/"manuscript.pdf");texts=[" ".join(pg.get_text().split()) for pg in main]
check("scene method and actual plots enter the article",any("Estimate and correct" in t and "Historical calibration" in t and "Reserve request" in t for t in texts))
check("training and clipping details retained in caption",any("0.90 pinball loss" in t and "raw estimate clipped at zero" in t and "fixed before evaluation" in t for t in texts))
check("separate examples and target alignment explained",any("different datasets" in t and "one hour after" in t for t in texts))
check("conceptual scene and generation assistance disclosed",any("conceptual wind-farm scene" in t for t in texts) and any("image-generation tool" in t for t in texts))
check("all four captions in the main paper",all(any(f"Fig. {n}." in t for t in texts) for n in range(1,5)))
check("main manuscript within page limit",len(main)<=10,pages=len(main))
log=(B/"build/manuscript.log").read_text(encoding="utf-8",errors="replace")
check("no overflow or undefined references",not re.search(r"Overfull|LaTeX Warning: (?:Citation|Reference).*undefined",log))
r=dict(status="PASS" if all(c["passed"] for c in checks) else "FAIL",checks=checks)
(Q/"FINAL_CHECKS.json").write_text(json.dumps(r,indent=2),encoding="utf-8")
print(r["status"],sum(c["passed"] for c in checks),"/",len(checks))
for c in checks:
    if not c["passed"]:print(c)
raise SystemExit(0 if r["status"]=="PASS" else 1)
