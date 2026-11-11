"""Verify this figure revision against unchanged saved results; no scientific refits."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_代码/工程"))
from repo_paths import Path, repository_root
import hashlib
import json
import re
import fitz
import numpy as np
import pandas as pd

Q = Path(__file__).resolve().parent
B = Q.parents[1]
ROOT = Path(repository_root())
import os
REPORT_DIR = Path(os.environ["REPRODUCTION_OUTPUT_DIR"]) / "figures" if "REPRODUCTION_OUTPUT_DIR" in os.environ else Q
REPORT_DIR.mkdir(parents=True, exist_ok=True)
checks = []


def check(name, ok, **details):
    checks.append(dict(name=name, passed=bool(ok), **details))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


# The cleanup receipt binds AGENTS.md to the unchanged task-start instructions.
# All scientific input hashes match the retained historical manifest exactly.
input_manifest = Q / "protected_inputs_layout_20261111.json"
for row in json.loads(input_manifest.read_text()):
    check("Unchanged " + row["path"], sha(B / row["path"]) == row["sha256"])
source_receipt = json.loads((B / "qa/visual_redesign_20261027/DATA_RECEIPT.json").read_text())
changed = [p for p, h in source_receipt["source_hashes"].items() if sha(ROOT / p) != h]
check("Original experiment records unchanged", not changed, files=len(source_receipt["source_hashes"]), changed=changed)

f = pd.read_csv(B / "source_data/v2/measurement_fit.csv")
check("All matched arms and fits retained", len(f) == 40 and
      f.groupby(["estimator", "arm"]).size().eq(5).all() and set(f.seed) == set(range(201, 206)))
check("Matched fit points within plotted range", f.C.between(26, 53).all())
check("Matched cost accounting", np.allclose(f.C, f.R+10*f.U, rtol=0, atol=1e-10))
md = pd.read_csv(B / "source_data/v2/measurement_daily.csv")
check("All35 matched weather days retained", len(md) == 280 and set(md.day) == set(range(211, 246)))
co = pd.read_csv(B / "source_data/v2/measurement_contrasts.csv")
check("Six stored simultaneous comparisons", len(co) == 6 and (co.lower*100 >= -20).all()
      and (co.upper*100 <= 6).all())

d = pd.read_csv(B / "source_data/v10/decision_construction.csv")
offsets = pd.read_csv(B / "source_data/v4/historical_offsets.csv")
offset = offsets.loc[np.isclose(offsets.calibration_q, .95), "offset_kw"].iloc[0]
check("All144 decision records", len(d) == 144 and d.decision_utc.nunique() == 144)
check("One-hour target lead", ((pd.to_datetime(d.target_utc)-pd.to_datetime(d.decision_utc)) == pd.Timedelta(hours=1)).all())
check("Stored raw estimate is nonnegative", (d.raw_kw >= 0).all())
check("Stored final request follows correction and second clip", np.allclose(d.reserve_kw, np.maximum(d.raw_kw+offset, 0), rtol=0, atol=1e-10))
check("Stored uncovered shortfall matches definition", np.allclose(d.uncovered_kw, np.maximum(d.shortfall_kw-d.reserve_kw, 0), rtol=0, atol=1e-10))
check("Example scatter retains entire observed shortfall range", d.shortfall_kw.between(0, 300).all())
check("All historical offsets retained", len(offsets) == 5 and offsets.offset_kw.between(-25, 350).all())

daily = pd.read_csv(B / "source_data/v2/cross_year_daily.csv")
summary = pd.read_csv(B / "source_data/v2/cross_year_summary.csv")
fits = pd.read_csv(B / "source_data/v2/cross_year_fits.csv")
check("All20 cross-year fit points", len(fits) == 20 and fits.groupby(["year", "arm"]).size().eq(5).all())
check("Event and severity points within plotted range", (100*fits.V).between(4.9, 7.4).all() and fits.U.between(1.55, 2.1).all())
check("Complete cross-year calendars", len(daily) == 4850 and daily.groupby("year").date.nunique().to_dict() == {2025:365, 2026:120})
empty = daily[daily.N == 0]
check("Twelve target-free days remain missing", empty.date.nunique() == 12 and empty.C.isna().all()
      and set(empty.date) == set(pd.date_range("2025-09-11", "2025-09-22").strftime("%Y-%m-%d")))
for year in [2025, 2026]:
    z = daily[daily.year == year].pivot(index="date", columns=["arm", "seed"], values="C")
    delta = (z.P1-z.WPQ36).mean(axis=1)
    check(f"{year} daily colour range retains all valid effects", delta.dropna().between(-8,8).all())
    check(f"{year} cost-context scatter retains all valid days", z.WPQ36.mean(axis=1).dropna().between(0,290).all())
for (year, arm), group in daily.groupby(["year", "arm"]):
    for metric in ["C", "R", "U", "V"]:
        pooled = np.mean([np.nansum(g[metric]*g.N)/g.N.sum() for _, g in group.groupby("seed")])
        stored = summary[(summary.year == year) & (summary.arm == arm)][metric].iloc[0]
        check(f"{year} {arm} {metric} pooled accounting", abs(pooled-stored) < 1e-10)
check("Cross-year stored cost intervals inside plotted range", (summary.cost_high.dropna()*100 <= 2.3).all())

stems = ["fig1_architecture", "fig2_decision_example", "fig3_measurement", "fig4_cross_year", "fig5_temporal"]
all_tex = (B / "manuscript.tex").read_text(encoding="utf-8")
for p in (B / "sections").glob("*_body.tex"):
    all_tex += p.read_text(encoding="utf-8")
for stem in stems:
    folder = B / "figures/v14"
    check(stem+" three exports", all((folder/(stem+"."+ext)).is_file() for ext in ["pdf", "svg", "png"]))
    svg = (folder/(stem+".svg")).read_text(encoding="utf-8")
    check(stem+" live text and vector geometry", "<text" in svg and "<image" not in svg)
    page = fitz.open(folder/(stem+".pdf"))[0]
    spans = [s for b in page.get_text("dict")["blocks"] for l in b.get("lines",[]) for s in l.get("spans",[]) if s["text"].strip()]
    check(stem+" readable final type", min(s["size"] for s in spans) >= 7)
    check(stem+" physical width", abs(page.rect.width-515.52) < .01)
    check(stem+" text inside canvas", all(s["bbox"][0] >= 0 and s["bbox"][1] >= 0
          and s["bbox"][2] <= page.rect.width and s["bbox"][3] <= page.rect.height for s in spans))
    check(stem+" embedded in main text", f"figures/v14/{stem}.pdf" in all_tex)
    collision = json.loads((Q/(stem+".collisions.json")).read_text())
    check(stem+" no rendered collisions", collision["summary"]["fail"] == 0 and collision["summary"]["warn"] == 0)
    align = json.loads((Q/(stem+".alignment.json")).read_text())
    check(stem+" rendered alignment", align["verdict"] == "PASS")
check("Exactly five main figures", len(re.findall(r"\\begin\{figure\*\}", all_tex)) == 5)
check("No obsolete generated-image disclosure", "image-generation tool produced" not in all_tex)
check("Original statistical and safety boundary retained", all(x in all_tex for x in [
    "not establish a uniform reduction", "2\\%", "10\\%", "minimum identification was not repeated in 2026",
    "does not quantify communication or computing savings"]))
check("Main PDF within journal page limit", len(fitz.open(B/"manuscript.pdf")) <= 10)

report = dict(status="PASS" if all(x["passed"] for x in checks) else "FAIL", checks=checks,
              input_manifest=input_manifest.name,
              scope="Figure transcription, complete record coverage, unchanged inputs and typeset integration. No new inference or publication-quality score.")
(REPORT_DIR/"FINAL_CHECKS.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(report["status"], len(checks), "checks")
for x in checks:
    if not x["passed"]:
        print(x)
raise SystemExit(0 if report["status"] == "PASS" else 1)
