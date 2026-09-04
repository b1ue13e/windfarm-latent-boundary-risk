"""Transform paper_draft.md -> paper_tste_ieee.md (IEEEtran two-column)."""
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
src = (ROOT / "paper_draft.md").read_text(encoding="utf-8")

# ── 1. New IEEEtran YAML ──────────────────────────────────────────────────────
new_yaml = (
    "---\n"
    "documentclass: IEEEtran\n"
    "classoption:\n"
    "  - journal\n"
    "mainfont: TeX Gyre Termes\n"
    "mathfont: TeX Gyre Termes Math\n"
    "bibliography: references.bib\n"
    "csl: IEEE.csl\n"
    "citeproc: true\n"
    "link-citations: false\n"
    "numbersections: true\n"
    "secnumdepth: 3\n"
    'date: ""\n'
    "header-includes:\n"
    "  - \\usepackage{tabularx}\n"
    "  - \\usepackage{booktabs}\n"
    "  - \\usepackage{float}\n"
    "  - \\usepackage{enumitem}\n"
    "  - \\usepackage{etoolbox}\n"
    "  - \\setlist[itemize]{leftmargin=1.6em}\n"
    "  - \\AtBeginEnvironment{CSLReferences}{\\footnotesize}\n"
    "---"
)

# ── 2. IEEEtran title / author / abstract block ───────────────────────────────
ieee_header = (
    "\\title{SCADA-Anchored Regime-Aware Routing for Operational Reserve Diagnosis "
    "in Wind-Turbine Control-Boundary Forecasting}\n"
    "\n"
    "\\author{%\n"
    "\\IEEEauthorblockN{Junyu Li and Juntao Du\\IEEEauthorrefmark{1}}\n"
    "\\IEEEauthorblockA{School of Statistics and Applied Mathematics,\n"
    "Anhui University of Finance and Economics, Bengbu 233030, China\\\\\n"
    "\\IEEEauthorrefmark{1}Corresponding author: "
    "\\texttt{dujuntao@aufe.edu.cn}}\n"
    "}\n"
    "\n"
    "\\maketitle\n"
    "\n"
    "\\begin{abstract}\n"
    "Wind-farm reserve screening near the MPPT-to-pitch transition depends on "
    "knowing which control law is active, yet the threshold label that identifies "
    "it can be delayed, missing, or noisy exactly where over-forecasts create "
    "shortage exposure. We make this control-boundary assignment auditable "
    "through SCADA-anchored, regime-aware routing. A node-level mixture-of-experts "
    "gate is constrained by operating anchors so each turbine-time route can be "
    "checked against a declared MPPT-to-pitch partition and issued before future "
    "active power is observed. On the KDD Cup 2022 benchmark, recomputing "
    "alignment and forcing class weights from the training split only keeps "
    "the routed forecaster below the RMSE guardrail (229.93 versus 224.34 "
    "for iTransformer) while preserving the routing claim (NMI 0.721, "
    "ARI 0.740); the fully archived legacy checkpoint gives stronger "
    "route alignment (NMI~0.87, ARI~0.92) for the full operational audit. "
    "Under a six-step label delay, the route retains 0.960 "
    "early pitch-window recall "
    "while the delayed threshold rule falls to 0.196; under 50\\% label "
    "availability, the corresponding rule reaches 0.508. A simple issue-time "
    "anchor classifier reaches 1.000 recall and 0.879 precision on clean anchors, "
    "so the claim is not superior standalone detection: the contribution is an "
    "auditable in-model route assignment coupled to forecasting and boundary-window "
    "reserve screening. At shortage-to-reserve cost ratio 10, gate-conditioned "
    "binning lowers same-router boundary-window shortage energy by 14.5\\% and "
    "violation by 1.38 percentage points while carrying about 3.6\\% more reserve; "
    "seed-paired intervals support this same-router diagnostic, but physical-bin "
    "baselines remain competitive. Retrained on the independent ENGIE La Haute "
    "Borne farm, the router provides anchor-observable cross-site mechanism replication "
    "(five-seed NMI~0.941); Kelmarsh/Penmanshiel, lacking pitch observability "
    "and boundary support, define the deployment conditions required before "
    "cross-farm use. The contribution is an auditable control-boundary routing "
    "layer with degraded-label availability evidence, a bounded RMSE guardrail, "
    "same-router reserve-screening evidence, and explicit transfer conditions.\n"
    "\\end{abstract}\n"
    "\n"
    "\\begin{IEEEkeywords}\n"
    "Wind-turbine control boundary; SCADA-anchored routing; regime-aware forecasting; "
    "auditable routing; MPPT-to-pitch transition; mixture-of-experts.\n"
    "\\end{IEEEkeywords}"
)

# ── 3. Extract body: Introduction → end of References (before Appendix A)
#        Nomenclature is Elsevier-style; IEEE papers define symbols inline.
intro_start = src.index("# Introduction")
app_start = src.index("# Appendix A. Training and implementation details {.unnumbered}")
body = src[intro_start:app_start].rstrip()

# ── 4. Table-width substitutions ───────────────────────────────────────────────
body = body.replace(
    r"\begin{tabularx}{0.98\linewidth}", r"\begin{tabularx}{\columnwidth}"
)
body = body.replace(
    r"\begin{tabularx}{0.98\textwidth}", r"\begin{tabularx}{\columnwidth}"
)
body = body.replace(
    r"\begin{tabularx}{0.90\textwidth}", r"\begin{tabularx}{\columnwidth}"
)
body = body.replace(r"{0.96\linewidth}", r"{0.96\columnwidth}")

# ── 4b. Fix equations that overflow 88mm IEEEtran column ─────────────────────
# GRU diffusion update: split across two lines
old_gru = (
    "$$\n"
    "\\mathbf{X}^{(\\ell+1)}_{t}\n"
    "=\n"
    "\\mathrm{LN}\\!\\left(\n"
    "\\mathbf{W}_{\\mathrm{self}}^{(\\ell)}\\mathbf{X}^{(\\ell)}_{t}\n"
    "+\n"
    "\\mathbf{W}_{\\mathrm{in}}^{(\\ell)}\\mathrm{Agg}_{\\mathrm{in}}"
    "(\\mathbf{X}^{(\\ell)}_{t},\\mathcal{A}_t)\n"
    "+\n"
    "\\mathbf{W}_{\\mathrm{out}}^{(\\ell)}\\mathrm{Agg}_{\\mathrm{out}}"
    "(\\mathbf{X}^{(\\ell)}_{t},\\mathcal{A}_t)\n"
    "+\n"
    "\\mathbf{R}^{(\\ell)}\\mathbf{X}^{(\\ell)}_{t}\n"
    "\\right),\n"
    "$$"
)
new_gru = (
    "```{=latex}\n"
    "\\begin{equation}\n"
    "\\begin{split}\n"
    "\\mathbf{X}^{(\\ell+1)}_{t}\n"
    "= \\mathrm{LN}\\!\\Bigl(&\\mathbf{W}_{\\mathrm{self}}^{(\\ell)}"
    "\\mathbf{X}^{(\\ell)}_{t}\n"
    "+\\mathbf{W}_{\\mathrm{in}}^{(\\ell)}\\mathrm{Agg}_{\\mathrm{in}}"
    "(\\mathbf{X}^{(\\ell)}_{t},\\mathcal{A}_t)\\\\\\\\\n"
    "&+\\mathbf{W}_{\\mathrm{out}}^{(\\ell)}\\mathrm{Agg}_{\\mathrm{out}}"
    "(\\mathbf{X}^{(\\ell)}_{t},\\mathcal{A}_t)\n"
    "+\\mathbf{R}^{(\\ell)}\\mathbf{X}^{(\\ell)}_{t}\\Bigr),\n"
    "\\end{split}\n"
    "\\end{equation}\n"
    "```"
)
body = body.replace(old_gru, new_gru)

# Total loss function: split across two lines
old_loss = (
    "$$\n"
    "\\mathcal{L}\n"
    "=\n"
    "\\mathcal{L}_{\\mathrm{pred}}\n"
    "+\n"
    "\\lambda_{\\mathrm{bal}}\\mathcal{L}_{\\mathrm{bal}}\n"
    "+\n"
    "\\lambda_{\\mathrm{align}}\\mathcal{L}_{\\mathrm{align}}\n"
    "+\n"
    "\\lambda_{\\mathrm{force}}\\mathcal{L}_{\\mathrm{force}}\n"
    "+\n"
    "\\lambda_{\\mathrm{aux}}\\mathcal{L}_{\\mathrm{aux}}\n"
    "+\n"
    "\\lambda_{\\mathrm{smooth}}\\mathcal{L}_{\\mathrm{smooth}},\n"
    "$$"
)
new_loss = (
    "```{=latex}\n"
    "\\begin{align}\n"
    "\\mathcal{L} &= \\mathcal{L}_{\\mathrm{pred}}"
    "+ \\lambda_{\\mathrm{bal}}\\mathcal{L}_{\\mathrm{bal}}"
    "+ \\lambda_{\\mathrm{align}}\\mathcal{L}_{\\mathrm{align}}\\nonumber\\\\\\\\\n"
    "&\\quad+ \\lambda_{\\mathrm{force}}\\mathcal{L}_{\\mathrm{force}}"
    "+ \\lambda_{\\mathrm{aux}}\\mathcal{L}_{\\mathrm{aux}}"
    "+ \\lambda_{\\mathrm{smooth}}\\mathcal{L}_{\\mathrm{smooth}},\n"
    "\\end{align}\n"
    "```"
)
body = body.replace(old_loss, new_loss)

# ── 4c. Remove deployment-checklist figure (Table 5 covers same content) ──────
old_checklist_fig = (
    "\n![The new-site protocol turns external failure into a practical safety "
    "check: sensor coverage, local boundary calibration, held-out routing, and "
    "reserve audit must all pass before gate-conditioned reserve allocation is "
    "used.](artifacts/final_evidence_package/export/figures/"
    "new_wind_farm_deployment_checklist.png){ width=94% }\n"
)
body = body.replace(old_checklist_fig, "\n")

# ── 4d. Remove operational decision curve figure (Tables 3–4 cover same data) ─
old_dec_curve = (
    "\n![The decision curve places the reserve benefit beside the measured RMSE "
    "price. Gate-conditioned allocation is attractive only where the "
    "transition-window shortage reduction is worth the added reserve "
    "energy.](artifacts/final_evidence_package/export/figures/"
    "operational_decision_curve.png){ width=92% }\n"
)
body = body.replace(old_dec_curve, "\n")

# ── 4e. Remove secondary case-study figure (routing evidence figure carries the main claim) ─
old_case_studies = (
    "\n![The time-series case studies show why observability matters. The WTB gate "
    "tracks a turbine-control switch that is partly hidden inside SCADA control action, "
    "whereas the ERA5 gate follows a more directly observed thermodynamic marker.]"
    "(artifacts/final_evidence_package/export/figures/figure5_case_studies.pdf){ width=97% }\n"
)
body = body.replace(old_case_studies, "\n")

# ── 4f. Remove accountability trade-off figure (numbers are in text/table; saves IEEE page budget) ──
old_accountability = (
    "\n![Accountability value versus forecasting RMSE price. Citable degraded-label "
    "gain is assigned only after the physical-routing audit passes. \\label{fig:accountability-tradeoff}]"
    "(artifacts/final_evidence_package/export/figures/accountability_tradeoff_curve.pdf){ width=90% }\n"
)
body = body.replace(old_accountability, "\n")
body = body.replace(" (Fig.~\\ref{fig:accountability-tradeoff})", "")

# ── 4g. Remove reserve-diagnostic algorithm box (math in text is sufficient) ──
# The box content starts with \begingroup\footnotesize...\noindent\fbox
# Search for it in the body (after step 4 table-width subs, 0.96\columnwidth)
algo_start = "\n```{=latex}\n\\begingroup\n\\footnotesize\n\\setlength{\\fboxsep}{5pt}"
algo_end   = "\\endgroup\n```\n"
a0 = body.find(algo_start)
if a0 != -1:
    a1 = body.find(algo_end, a0) + len(algo_end)
    body = body[:a0] + "\n" + body[a1:]

# ── 5. Cross-references to Supplementary Appendix A ───────────────────────────
xrefs = [
    ("Exact weights are in Appendix A.",
     "Exact weights are in Supplementary Appendix~A."),
    ("summarized in Appendix A so that",
     "summarized in Supplementary Appendix~A so that"),
    ("reported in the Appendix so that",
     "reported in Supplementary Appendix~A so that"),
    ("Appendix A gives the exact expression",
     "Supplementary Appendix~A gives the exact expression"),
    ("Both formulas are in Appendix A.",
     "Both formulas are in Supplementary Appendix~A."),
    ("Graph construction details are in Appendix A.",
     "Graph construction details are in Supplementary Appendix~A."),
    ("Graph construction equations are in Appendix A",
     "Graph construction equations are in Supplementary Appendix~A"),
]
for old, new in xrefs:
    body = body.replace(old, new)

# ── 6. Remove \clearpage (not suited for IEEEtran journal) ────────────────────
body = body.replace("\n\\clearpage\n", "\n")

# ── 7. Code/data section: add supplementary mention ───────────────────────────
body = body.replace(
    "The provenance package lists the anchor-stress three-step protocol as mandatory."
    " The analysis involves no human subjects.",
    "The provenance package lists the anchor-stress three-step protocol as mandatory."
    " Training algorithm, auxiliary loss formulas, graph-construction details,"
    " shared constants, and routing-weight tables are provided in Supplementary"
    " Appendix~A. The analysis involves no human subjects.",
)

import sys
dest = ROOT / "paper_tste_ieee.md"
if "--force" in sys.argv:
    dest.write_text(out, encoding="utf-8")
    print(f"Force-written {dest.name}")
else:
    print(f"Protected: {dest.name} is the primary source of truth. Pass --force to overwrite.")


# Sanity checks
assert "IEEEtran" in out
assert r"\columnwidth" in out
assert r"\begin{tabularx}{0.98\textwidth}" not in out
assert "# Appendix A. Training" not in out
assert "Supplementary Appendix" in out
assert r"\maketitle" in out
assert r"\begin{IEEEkeywords}" in out
assert "# Nomenclature" not in out          # removed for IEEE
assert r"\begin{equation}" in out            # GRU split equation
assert r"\begin{align}" in out               # loss split equation
assert "deployment_checklist.png" not in out # removed redundant figure
assert "operational_decision_curve.png" not in out  # removed; Tables 3-4 cover it
assert "figure5_case_studies.pdf" not in out         # removed; Figure 4 carries routing evidence
assert "accountability_tradeoff_curve.pdf" not in out
assert r"\fbox" not in out                          # algo box removed
assert "not a claim of forecasting superiority" not in out

print(f"Written paper_tste_ieee.md  ({lines} lines, {words} words) - all checks passed")
