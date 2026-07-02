"""Extract Appendix A from paper_draft.md -> paper_tste_supplementary.md."""
import pathlib
import subprocess
import sys
import pandas as pd

ROOT = pathlib.Path(__file__).parent.parent
src = (ROOT / "paper_draft.md").read_text(encoding="utf-8")

early_warning_builder = ROOT / "scripts" / "build_early_warning_consequence_table.py"
if early_warning_builder.exists():
    subprocess.run([sys.executable, str(early_warning_builder)], cwd=ROOT, check=True)


def replace_section(body: str, heading: str, replacement: str, next_heading: str | None = None) -> str:
    section_start = body.index(heading)
    section_end = len(body) if next_heading is None else body.index(next_heading, section_start)
    return body[:section_start] + replacement + body[section_end:]


app_marker = "# Appendix A. Training and implementation details {.unnumbered}"
app_start = src.index(app_marker)
app_body = src[app_start:].rstrip()

# Fix table widths for IEEEtran
app_body = app_body.replace(
    r"\begin{tabularx}{0.98\textwidth}", r"\begin{tabularx}{\columnwidth}"
)
app_body = app_body.replace(
    r"\begin{tabularx}{0.90\textwidth}", r"\begin{tabularx}{\columnwidth}"
)
app_body = app_body.replace(
    r"\begin{tabularx}{0.98\linewidth}", r"\begin{tabularx}{\columnwidth}"
)
app_body = app_body.replace(r"\textwidth}", r"\columnwidth}")
app_body = app_body.replace(
    "\\begin{table}[H]\n"
    "\\centering\n"
    "\\small\n"
    "\\setlength{\\tabcolsep}{5pt}\n"
    "\\renewcommand{\\arraystretch}{1.1}\n"
    "\\caption*{\\textbf{Table A1.} In-family model comparison used for mechanism validation.}\n"
    "\\begin{tabularx}{\\columnwidth}{>{\\raggedright\\arraybackslash}p{0.18\\columnwidth} >{\\raggedright\\arraybackslash}p{0.16\\columnwidth} >{\\raggedright\\arraybackslash}X >{\\raggedright\\arraybackslash}p{0.20\\columnwidth} >{\\raggedright\\arraybackslash}p{0.18\\columnwidth}}\n",
    "\\begin{table}[H]\n"
    "\\centering\n"
    "\\scriptsize\n"
    "\\setlength{\\tabcolsep}{3pt}\n"
    "\\renewcommand{\\arraystretch}{1.05}\n"
    "\\caption*{\\textbf{Table A1.} In-family model comparison used for mechanism validation.}\n"
    "\\resizebox{\\columnwidth}{!}{%\n"
    "\\begin{tabular}{lllll}\n",
)
app_body = app_body.replace(
    "\\bottomrule\n\\end{tabularx}\n\\end{table}",
    "\\bottomrule\n\\end{tabular}%\n}\n\\end{table}",
    1,
)

channel_role_table = r"""
## Information boundary and channel roles {.unnumbered}

Table A2 makes the leakage and shared-anchor boundary explicit. The routing labels
and some gate anchors deliberately share wind-speed and pitch information; the
reported NMI/ARI therefore audits compliance with a declared SCADA boundary, not
anchor-free discovery.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.6pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A2.} Information boundary and channel-role audit.}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lllll}
\toprule
Quantity & Label construction & Model input / gate anchor & Supervised target & Timing boundary \\
\midrule
\texttt{Wspd} & WTB regime label & history and issue-time anchor & no & $\leq t$ only \\
\texttt{Pab\_mean} & WTB regime label & history and issue-time anchor & no & $\leq t$ only \\
$\texttt{Patv}_{t-H+1:t}$ & no & historical input / issue-time status & no & $\leq t$ only \\
$\texttt{Patv}_{t+1:t+P}$ & no & no & yes & future target only \\
Wake score & auxiliary wake flag & graph-derived anchor & no & computed from issue-time graph \\
Declared regime label & alignment/forcing supervision & no test-time input & no & train/validation supervision only \\
Confirmed threshold stream & degraded-rule comparator & not a model input & no & delayed/missing/noisy in audit \\
\bottomrule
\end{tabular}%
}
\end{table}
```
"""
app_body = app_body.replace("## Auxiliary losses {.unnumbered}", channel_role_table + "\n## Auxiliary losses {.unnumbered}")

statistical_tex = ROOT / "artifacts" / "final_evidence_package" / "export" / "tables" / "table_statistical_claim_boundaries.tex"
if statistical_tex.exists():
    replacement = (
        "## Statistical claim boundaries {.unnumbered}\n\n"
        "Table A6 separates descriptive accuracy-price statements from paired "
        "seed-level tests. The iTransformer row is the displayed five-seed mean "
        "difference used for the main RMSE price; the Graph WaveNet and "
        "boundary-window rows are paired/FDR audit rows and should not be read "
        "as simple differences between table means.\n\n"
        "```{=latex}\n"
        + statistical_tex.read_text(encoding="utf-8").strip()
        + "\n```\n\n"
    )
    app_body = replace_section(
        app_body,
        "## Statistical claim boundaries {.unnumbered}",
        replacement,
        "## Outcome-channel sanity audit {.unnumbered}",
    )

class_weight_sensitivity_tex = ROOT / "artifacts" / "class_weight_boundary_audit" / "table_class_weight_sensitivity_audit.tex"
if class_weight_sensitivity_tex.exists():
    table = class_weight_sensitivity_tex.read_text(encoding="utf-8").strip()
    table = table.replace(
        r"\caption*{\textbf{Class-weight sensitivity audit.} Boundary-router rerun after recomputing alignment and pitch-forcing loss weights from the training split only.}",
        r"\caption*{\textbf{Table A6b.} Class-weight sensitivity audit. Boundary-router rerun after recomputing alignment and pitch-forcing loss weights from the training split only.}",
    )
    insertion = (
        "## Class-weight sensitivity audit {.unnumbered}\n\n"
        "Table A6b makes the class-weight provenance boundary explicit. The legacy "
        "strict-cache row is the originally frozen boundary-router checkpoint used "
        "for the headline audit; the train-only rerun recomputes alignment and "
        "pitch-forcing class weights from the training split only while preserving "
        "the same strict-mask evaluation protocol. The train-only rerun lowers "
        "NMI/ARI but remains above the routing-claim threshold.\n\n"
        "```{=latex}\n"
        + table
        + "\n```\n\n"
    )
    app_body = app_body.replace("## Outcome-channel sanity audit {.unnumbered}", insertion + "## Outcome-channel sanity audit {.unnumbered}", 1)

early_warning_tex = ROOT / "artifacts" / "final_evidence_package" / "export" / "tables" / "table_early_warning_consequence_audit.tex"
if early_warning_tex.exists():
    replacement = (
        "## Early-warning detection consequence {.unnumbered}\n\n"
        "Table A10 reports the reviewer-facing detector control for the label-degradation "
        "audit. The simple classifier is a validation-fit multinomial logistic regression "
        "on the same issue-time anchors. It matches or exceeds the gate on clean-anchor "
        "standalone detection, so the manuscript claims auditable in-model route attribution "
        "rather than classifier superiority. Recovered cells are turbine-time cells per seed "
        "inside the six-step MPPT-to-pitch window and are not MWh, currency, or dispatch-cost "
        "estimates.\n\n"
        "```{=latex}\n"
        + early_warning_tex.read_text(encoding="utf-8").strip()
        + "\n```\n\n"
    )
    app_body = replace_section(
        app_body,
        "## Early-warning detection consequence {.unnumbered}",
        replacement,
        "## Reserve-policy claim-boundary audit {.unnumbered}",
    )

reserve_boundary_tex = ROOT / "artifacts" / "final_evidence_package" / "export" / "tables" / "table_reserve_claim_boundary_audit.tex"
if reserve_boundary_tex.exists():
    replacement = (
        "## Reserve-policy claim-boundary audit {.unnumbered}\n\n"
        "Table A11 is the compact reviewer-facing boundary audit. The CSV keeps the "
        "full wording rules; the table lists the evidence token and claim limit "
        "needed to keep the reserve result diagnostic rather than policy-optimal.\n\n"
        "```{=latex}\n"
        + reserve_boundary_tex.read_text(encoding="utf-8").strip()
        + "\n```\n\n"
    )
    app_body = replace_section(
        app_body,
        "## Reserve-policy claim-boundary audit {.unnumbered}",
        replacement,
        "## Engineering-unit reserve-value translation {.unnumbered}",
    )

engineering_value_tex = ROOT / "artifacts" / "final_evidence_package" / "export" / "tables" / "table_engineering_unit_value_translation.tex"
if engineering_value_tex.exists():
    replacement = (
        "## Engineering-unit reserve-value translation {.unnumbered}\n\n"
        "Table A12 translates the reserve audit into MWh-equivalent forecast-cell "
        "accounting and a 100 EUR/MWh scale marker; it is not a market-settlement, "
        "OPF, unit-commitment, or security-constrained dispatch result.\n\n"
        "```{=latex}\n"
        + engineering_value_tex.read_text(encoding="utf-8").strip()
        + "\n```\n\n"
    )
    app_body = replace_section(
        app_body,
        "## Engineering-unit reserve-value translation {.unnumbered}",
        replacement,
    )

benchmark_path = ROOT / "artifacts" / "paper_assets" / "tables" / "table_main_benchmark.csv"
if benchmark_path.exists():
    benchmark = pd.read_csv(benchmark_path)
    expanded_models = [
        "iTransformer",
        "Graph WaveNet",
        "Boundary-forced router",
    ]
    rows = []
    for model in expanded_models:
        match = benchmark[(benchmark["Panel"].astype(str) == "WTB") & (benchmark["Model"].astype(str) == model)]
        if match.empty:
            continue
        row = match.iloc[0]
        rows.append(
            " & ".join(
                [
                    str(row["Model"]).replace("_", r"\_"),
                    str(row["Overall RMSE"]),
                    str(row["Switch RMSE"]),
                    str(row["n_runs"]),
                ]
            )
            + r" \\"
        )
    anchor_router_path = ROOT / "artifacts" / "final_evidence_package" / "export" / "tables" / "anchor_only_rule_router_main_table.csv"
    if anchor_router_path.exists():
        anchor_router = pd.read_csv(anchor_router_path)
        match = anchor_router[anchor_router["model"].astype(str) == "Anchor-only router"]
        if not match.empty:
            row = match.iloc[0]
            rows.append(
                " & ".join(
                    [
                        "Anchor-only router",
                        f"{float(row['overall_rmse']):.2f}",
                        f"{float(row['switch_rmse']):.2f}",
                        "5",
                    ]
                )
                + r" \\"
            )
    operational_path = ROOT / "artifacts" / "operational_baselines_wtb_strictmask" / "wtb_operational_baselines.csv"
    if operational_path.exists():
        operational = pd.read_csv(operational_path)
        for _, row in operational.iterrows():
            rows.append(
                " & ".join(
                    [
                        str(row["model"]).replace("_", r"\_"),
                        f"{float(row['overall_rmse']):.2f}",
                        f"{float(row['switch_rmse']):.2f}",
                        "det.",
                    ]
                )
                + r" \\"
            )
    if rows:
        expanded_table = "\n".join(
            [
                "",
                "```{=latex}",
                r"\begin{table}[H]",
                r"\centering",
                r"\scriptsize",
                r"\setlength{\tabcolsep}{3pt}",
                r"\renewcommand{\arraystretch}{1.05}",
                r"\caption*{\textbf{Table A13.} Compact WTB strong, anchor-only, and engineering baseline check (mean $\pm$ std across seeds where repeated runs are available; det. denotes a deterministic or single-run engineering baseline).}",
                r"\resizebox{\columnwidth}{!}{%",
                r"\begin{tabular}{lrrr}",
                r"\toprule",
                r"Model & Overall RMSE & Switch RMSE & n \\",
                r"\midrule",
                *rows,
                r"\bottomrule",
                r"\end{tabular}%",
                r"}",
                r"\end{table}",
                "```",
                "",
            ]
        )
        app_body = app_body + expanded_table

supp_yaml = "\n".join([
    "---",
    "documentclass: IEEEtran",
    "classoption:",
    "  - journal",
    "mainfont: TeX Gyre Termes",
    "mathfont: TeX Gyre Termes Math",
    "bibliography: references.bib",
    "csl: IEEE.csl",
    "citeproc: true",
    "link-citations: false",
    "numbersections: false",
    'date: ""',
    "header-includes:",
    "  - \\usepackage{tabularx}",
    "  - \\usepackage{booktabs}",
    "  - \\usepackage{float}",
    "  - \\usepackage{graphicx}",
    "---",
])

out = supp_yaml + "\n\n" + app_body + "\n"
dest = ROOT / "paper_tste_supplementary.md"
dest.write_text(out, encoding="utf-8")
print(f"Written {dest.name}  ({len(out.splitlines())} lines)")
