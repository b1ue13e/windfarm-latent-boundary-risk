"""Verify figure data, vector exports and manuscript integration without statistical fitting."""
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

B=Path(__file__).resolve().parents[2]
ROOT = Path(repository_root())
Q=Path(__file__).resolve().parent
checks=[]
def check(name,ok,**details):
    checks.append(dict(name=name,passed=bool(ok),**details))

receipt=json.loads((Q/"DATA_RECEIPT.json").read_text(encoding="utf-8"))
bad=[p for p,h in receipt["source_hashes"].items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
check("original experiment assets unchanged",not bad,source_count=len(receipt["source_hashes"]),mismatches=bad)
check("no new model or interval fitting",all(receipt[x]==0 for x in ["new_fits","new_calibrations","new_bootstrap"]))
daily=pd.read_csv(B/"source_data/v2/cross_year_daily.csv")
check("all requested calendar slots",len(daily)==4850 and daily.groupby("year").date.nunique().to_dict()=={2025:365,2026:120})
z=daily[daily.N==0]
check("no synthetic values for target-free days",z.C.isna().all() and z.date.nunique()==12,dates=sorted(z.date.unique().tolist()))
summary=pd.read_csv(B/"source_data/v2/cross_year_summary.csv")
for (year,arm),g in daily.groupby(["year","arm"]):
    for metric in ["C","R","U","V"]:
        fit_mean=np.mean([np.nansum(x[metric]*x.N)/x.N.sum() for _,x in g.groupby("seed")])
        original=summary[(summary.year==year)&(summary.arm==arm)][metric].iloc[0]
        check(f"{year} {arm} pooled {metric}",abs(fit_mean-original)<1e-10)
fits=pd.read_csv(B/"source_data/v2/measurement_fit.csv")
check("all matched fixed fits",len(fits)==40 and set(fits.seed)==set(range(201,206)))
check("accounting identity preserved",np.allclose(fits.C,fits.R+10*fits.U,atol=1e-10,rtol=0))

stems=["fig1_overview","fig2_measurement","fig3_cross_year","fig4_temporal"]
font_summary={}
for stem in stems:
    folder=B/"figures/v2"
    check(stem+" export bundle",all((folder/(stem+"."+ext)).exists() for ext in ["pdf","svg","png"]))
    svg=(folder/(stem+".svg")).read_text(encoding="utf-8")
    check(stem+" live SVG text","<text" in svg)
    d=fitz.open(folder/(stem+".pdf"))
    spans=[s for p in d for b in p.get_text("dict")["blocks"] for l in b.get("lines",[]) for s in l.get("spans",[]) if s["text"].strip()]
    low=min(s["size"] for s in spans)
    check(stem+" actual font floor",low>=7,minimum_points=round(low,3))
    font_summary[stem]=round(low,3)
    check(stem+" IEEE double-column width",abs(d[0].rect.width/72-7.16)<.01)
    outside=[s["text"] for s in spans if s["bbox"][0]<-.5 or s["bbox"][1]<-.5 or s["bbox"][2]>d[0].rect.width+.5 or s["bbox"][3]>d[0].rect.height+.5]
    check(stem+" no clipped text",not outside,offenders=outside)
for n in [2,3,4]:
    c=json.loads((Q/f"fig{n}.collisions.json").read_text())
    check(f"Fig{n} collisions",c["summary"]["fail"]==0 and c["summary"]["warn"]==0)
    a=json.loads((Q/f"{stems[n-1]}.alignment.json").read_text())
    check(f"Fig{n} alignment",a.get("verdict")=="PASS",verdict=a.get("verdict"))
overview=json.loads((Q/"overview_collision_audit.json").read_text())
check("Fig1 collisions",overview["summary"]["fail"]==0 and overview["summary"]["warn"]==0,
      summary=overview["summary"])
geometry=json.loads((Q/"overview_geometry.json").read_text())
check("Fig1 label containment and nodes",geometry["label_containment"]=="PASS" and geometry["node_nonoverlap"]=="PASS")
svg_audit=json.loads((Q/"overview_svg_audit.json").read_text(encoding="utf-8-sig"))
check("Fig1 SVG schematic audit",svg_audit["verdict"]=="PASS",font_floor=svg_audit["minimum_found_pt"])

main=(B/"manuscript.tex").read_text(encoding="utf-8")
section_paths=re.findall(r"\\input\{([^}]+)\}",main)
tex="\n".join((B/(p+".tex")).read_text(encoding="utf-8") for p in section_paths)
files=re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}",tex)
check("four new main figures only",len(files)==4 and {Path(p).stem for p in files}==set(stems),paths=files)
doc=fitz.open(B/"manuscript.pdf")
pages=[p.get_text() for p in doc]
captions={f:next((i+1 for i,t in enumerate(pages) if f"Fig. {n}." in t),None) for n,f in enumerate(stems,1)}
check("all figures in compiled main paper",all(captions.values()),pages=captions)
reference_page=next(i+1 for i,t in enumerate(pages) if "REFERENCES" in t)
check("all figures before bibliography",max(captions.values())<=reference_page,reference_page=reference_page)
check("main page limit",len(doc)<=10,pages=len(doc))
log=(B/"build/manuscript.log").read_text(encoding="utf-8",errors="replace")
warnings=re.findall(r"Overfull[^\n]*|LaTeX Warning: (?:Citation|Reference)[^\n]*undefined",log)
check("compile no overflow or missing references",not warnings,warnings=warnings)
result=dict(status="PASS" if all(c["passed"] for c in checks) else "FAIL",checks=checks,font_summary=font_summary)
(Q/"FINAL_VISUAL_CHECKS.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(result["status"],f"{sum(c['passed'] for c in checks)}/{len(checks)} checks")
for c in checks:
    if not c["passed"]:print(c)
raise SystemExit(0 if result["status"]=="PASS" else 1)
