"""Compare numerical artist coordinates before and after a figure style pass."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
import hashlib
import json
import runpy
import numpy as np
import matplotlib.pyplot as plt

Q=Path(__file__).resolve().parent;B=Q.parents[1]

def arrays(value):
    a=np.asarray(value)
    if a.dtype.kind in "iuf":return np.asarray(a,dtype=float).tolist()
    return a.tolist()

def capture(script):
    ns=runpy.run_path(str(B/"figure_code"/script))
    result={}
    def save(fig,stem,**kwargs):
        plots=[]
        for ax in fig.axes:
            plots.append(dict(
                lines=[dict(x=arrays(l.get_xdata(orig=False)),y=arrays(l.get_ydata(orig=False))) for l in ax.lines],
                bars=[dict(x=float(p.get_x()),y=float(p.get_y()),width=float(p.get_width()),height=float(p.get_height()))
                      for p in ax.patches if p.__class__.__name__=="Rectangle"],
                collections=[dict(kind=c.__class__.__name__,offsets=arrays(c.get_offsets()),
                    paths=[arrays(p.vertices) for p in c.get_paths()]
                      if c.__class__.__name__ in ["LineCollection","PolyCollection","FillBetweenPolyCollection"] else [])
                    for c in ax.collections],
                xlim=arrays(ax.get_xlim()),ylim=arrays(ax.get_ylim())))
        result[stem]=plots;plt.close(fig)
    ns["measurement"].__globals__["save"]=save
    for fn in ["measurement","crossyear","temporal"]:ns[fn]()
    return result

if __name__=="__main__":
    old=capture("results_v2.py");new=capture("results_v13.py")
    # JSON preserves NaNs in the retained missing-day spans. Comparing serialized
    # geometry checks every line, interval endpoint, bar and shaded band.
    a=json.dumps(old,sort_keys=True);b=json.dumps(new,sort_keys=True)
    report=dict(status="PASS" if a==b else "FAIL",baseline="results_v2.py",
        revised="results_v13.py",scope="Numerical coordinates and axis limits; style, text positions, marker sizes and panel rectangles may differ",
        figures=list(old),baseline_sha256=hashlib.sha256(a.encode()).hexdigest(),
        revised_sha256=hashlib.sha256(b.encode()).hexdigest())
    (Q/"PLOT_COORDINATES_BEFORE.json").write_text(json.dumps(old),encoding="utf-8")
    (Q/"PLOT_COORDINATES_AFTER.json").write_text(json.dumps(new),encoding="utf-8")
    (Q/"PLOT_DATA_COMPARISON.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(report["status"],"all plotted numeric coordinates and axis limits")
    raise SystemExit(0 if a==b else 1)
