"""Check presentation-only changes against saved result geometry and source bytes."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
import hashlib
import json
import re
import subprocess
import fitz
import numpy as np
import pandas as pd

Q = Path(__file__).resolve().parent
B = Q.parents[1]
ROOT = Path(repository_root())
PARENT = "5c1bf502b2a8813be95559258000f62574a8fbd9"
checks = []

def check(name, ok, **info):
    checks.append(dict(name=name, passed=bool(ok), **info))

def sha(data):
    return hashlib.sha256(data).hexdigest()

def saved_bytes(path):
    p = subprocess.run(["git", "cat-file", "blob", PARENT + ":" + path.relative_to(ROOT).as_posix()],
                       cwd=ROOT, capture_output=True, timeout=20)
    if p.returncode:
        raise RuntimeError("Missing previous snapshot: " + str(path))
    return p.stdout

protected = [B / ("figures/v12/fig1_overview." + ext) for ext in ("pdf", "svg", "png")]
bad = [p.relative_to(B).as_posix() for p in protected if p.read_bytes() != saved_bytes(p)]
check("Figure 1 byte-identical to previous snapshot", not bad, files=len(protected), mismatches=bad)
csv_paths = list((B / "source_data/v2").glob("*.csv"))
# Git stores these text assets with LF; the Windows checkout uses CRLF. Compare
# complete content after that sole normalization, without rewriting either file.
bad = [p.relative_to(B).as_posix() for p in csv_paths
       if p.read_bytes().replace(b"\r\n", b"\n") != saved_bytes(p).replace(b"\r\n", b"\n")]
check("all quantitative source CSV contents unchanged", not bad, files=len(csv_paths), mismatches=bad,
      normalization="Git LF versus Windows CRLF only; no files rewritten")
receipt = json.loads((B / "qa/visual_redesign_20261027/DATA_RECEIPT.json").read_text())
bad = [p for p, h in receipt["source_hashes"].items() if sha((ROOT / p).read_bytes()) != h]
check("original experiment sources unchanged", not bad, files=len(receipt["source_hashes"]), mismatches=bad)

before = (Q / "PLOT_COORDINATES_BEFORE.json").read_bytes()
after = (Q / "PLOT_COORDINATES_AFTER.json").read_bytes()
check("all plotted data coordinates and axis limits identical", before == after,
      before_sha256=sha(before), after_sha256=sha(after))
tex = B / "sections/result_figures_body.tex"
old = saved_bytes(tex).decode("utf-8")
new = tex.read_text(encoding="utf-8")
check("only figure asset paths changed in result captions", new == old.replace("figures/v2/", "figures/v13/"))

daily = pd.read_csv(B / "source_data/v2/cross_year_daily.csv")
check("complete calendar retained", len(daily) == 4850 and daily.groupby("year").date.nunique().to_dict() == {2025: 365, 2026: 120})
empty = daily[daily.N == 0]
check("target-free days remain gaps", empty.date.nunique() == 12 and empty.C.isna().all())
summary = pd.read_csv(B / "source_data/v2/cross_year_summary.csv")
for (year, arm), group in daily.groupby(["year", "arm"]):
    for metric in ["C", "R", "U", "V"]:
        mean = np.mean([np.nansum(g[metric] * g.N) / g.N.sum() for _, g in group.groupby("seed")])
        original = summary[(summary.year == year) & (summary.arm == arm)][metric].iloc[0]
        check(f"{year} {arm} daily-to-window {metric}", abs(mean - original) < 1e-10)
fits = pd.read_csv(B / "source_data/v2/measurement_fit.csv")
check("all matched five-fit results retained", len(fits) == 40 and set(fits.seed) == set(range(201, 206)))
check("original cost decomposition retained", np.allclose(fits.C, fits.R + 10 * fits.U, rtol=0, atol=1e-10))

stems = ["fig2_measurement", "fig3_cross_year", "fig4_temporal"]
for n, stem in enumerate(stems, 2):
    folder = B / "figures/v13"
    check(stem + " complete exports", all((folder / (stem + "." + e)).is_file() for e in ["pdf", "svg", "png"]))
    check(stem + " editable SVG text", "<text" in (folder / (stem + ".svg")).read_text(encoding="utf-8"))
    doc = fitz.open(folder / (stem + ".pdf"))
    page = doc[0]
    spans = [s for b in page.get_text("dict")["blocks"] for l in b.get("lines", [])
             for s in l.get("spans", []) if s["text"].strip()]
    check(stem + " physical font floor", min(s["size"] for s in spans) >= 7,
          minimum_pt=min(s["size"] for s in spans))
    check(stem + " double-column width", abs(page.rect.width - 515.52) < .01)
    check(stem + " no cropped text", all(s["bbox"][0] >= -.5 and s["bbox"][1] >= -.5
          and s["bbox"][2] <= page.rect.width + .5 and s["bbox"][3] <= page.rect.height + .5 for s in spans))
    collision = json.loads((Q / f"fig{n}.collisions.json").read_text())
    check(stem + " rendered collision audit", collision["verdict"] == "PASS"
          and collision["summary"]["fail"] == 0 and collision["summary"]["warn"] == 0)
    alignment = json.loads((Q / (stem + ".alignment.json")).read_text())
    check(stem + " rendered panel alignment", alignment["verdict"] == "PASS")

main = (B / "manuscript.tex").read_text(encoding="utf-8")
sections = re.findall(r"\\input\{([^}]+)\}", main)
all_tex = "\n".join((B / (p + ".tex")).read_text(encoding="utf-8") for p in sections)
figures = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", all_tex)
check("current assets used in manuscript", figures == ["figures/v12/fig1_overview.pdf"]
      + ["figures/v13/" + s + ".pdf" for s in stems], paths=figures)
doc = fitz.open(B / "manuscript.pdf")
texts = [p.get_text() for p in doc]
caption_pages = {str(n): next((i+1 for i, t in enumerate(texts) if f"Fig. {n}." in t), None) for n in range(1, 5)}
check("four figures present in compiled article", all(caption_pages.values()), pages=caption_pages)
check("Figure 1 stays on page 2", caption_pages["1"] == 2)
ref_page = next(i+1 for i, t in enumerate(texts) if "REFERENCES" in t)
check("all figures before bibliography", all(p and p < ref_page for p in caption_pages.values()), references_page=ref_page)
check("article within page limit", len(doc) <= 10, pages=len(doc))
warnings = re.findall(r"Overfull[^\n]*|LaTeX Warning: (?:Citation|Reference)[^\n]*undefined|LaTeX Font Warning:[^\n]*",
                     (B / "build/manuscript.log").read_text(encoding="utf-8", errors="replace"))
check("no overflow or unresolved typesetting warnings", not warnings, warnings=warnings)
result = dict(status="PASS" if all(c["passed"] for c in checks) else "FAIL", checks=checks)
(Q / "FINAL_CHECKS.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(result["status"], sum(c["passed"] for c in checks), "/", len(checks))
print("Caption pages:", caption_pages, "Article pages:", len(doc))
for c in checks:
    if not c["passed"]:
        print(c)
raise SystemExit(0 if result["status"] == "PASS" else 1)
