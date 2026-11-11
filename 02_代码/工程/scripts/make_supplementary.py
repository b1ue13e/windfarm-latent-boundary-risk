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
        "Table A6 separates the train-only RMSE guardrail from paired "
        "seed-level tests on the archived full-audit checkpoint. The iTransformer "
        "row is the displayed five-seed train-only guardrail gap; the Graph WaveNet "
        "and boundary-window rows are legacy full-audit paired/FDR audit rows and "
        "should not be read as the current RMSE guardrail.\n\n"
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

def _gate_evolution_section(csv_path: pathlib.Path) -> str:
    frame = pd.read_csv(csv_path)
    frame = frame[
        frame["model"].astype(str).eq("MoE + L_bal + L_align + L_force")
        & frame["run_dir"].astype(str).str.contains("strictmask_validation_wtb_full", regex=False)
    ].copy()
    grouped = (
        frame.groupby("lag_steps")["gate_matches_new_regime_rate"]
        .agg(["mean", "std", "count"])
        .reset_index()
        .sort_values("lag_steps")
    )
    rows = []
    for _, row in grouped.iterrows():
        rows.append(
            f"{int(row['lag_steps']):+d} & {float(row['mean']):.3f} & {float(row['std']):.3f} & {int(row['count'])} \\\\"
        )
    table = "\n".join(
        [
            "## Gate route-evolution diagnostic {.unnumbered}",
            "",
            "Table A10b checks whether the routed responsibility changes around the declared transition rather than merely replaying a static label. Matching to the new regime peaks at the transition step and drops under lead/lag shifts, supporting a route-evolution audit while not replacing the modular classifier control.",
            "",
            "```{=latex}",
            r"\begin{table}[H]",
            r"\centering",
            r"\scriptsize",
            r"\setlength{\tabcolsep}{4pt}",
            r"\renewcommand{\arraystretch}{1.05}",
            r"\caption*{\textbf{Table A10b.} Gate route-evolution diagnostic around MPPT-to-pitch transitions.}",
            r"\begin{tabular}{rrrr}",
            r"\toprule",
            r"Lag step & Match rate & SD & Seeds \\",
            r"\midrule",
            *rows,
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
            "```",
            "",
        ]
    )
    return table


def _modular_classifier_reserve_section(summary_path: pathlib.Path) -> str:
    frame = pd.read_csv(summary_path)
    key = {
        (str(row["model"]), str(row["policy"])): row
        for _, row in frame.iterrows()
    }
    classifier = key[("Graph WaveNet + live-anchor classifier", "classifier-bin")]
    global_row = key[("Graph WaveNet", "global")]
    physical = key[("Graph WaveNet", "physical-bin")]
    gate = key[("Boundary-forced router", "gate-bin")]

    def m(value: float) -> str:
        return f"{float(value) / 1_000_000:.2f}M"

    return "\n".join(
        [
            "```{=latex}",
            r"\begin{table}[H]",
            r"\centering",
            r"\scriptsize",
            r"\setlength{\tabcolsep}{2pt}",
            r"\renewcommand{\arraystretch}{1.0}",
            r"\caption*{\textbf{Table A10c.} Modular classifier reserve control and responsibility-chain boundary.}",
            r"\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.24\columnwidth} >{\raggedright\arraybackslash}X}",
            r"\toprule",
            r"Control & Result and claim boundary \\",
            r"\midrule",
            f"GWN+classifier-bin & {m(classifier['total_cost_mean'])} improves over GWN/global "
            f"({m(global_row['total_cost_mean'])}) but trails physical-bin/gate-bin "
            f"({m(physical['total_cost_mean'])}/{m(gate['total_cost_mean'])}); paired modular-vs-gate "
            "CI crosses zero, so this is a tested modular control, not an in-model "
            "route-responsibility replacement. \\\\",
            r"\bottomrule",
            r"\end{tabularx}",
            r"\end{table}",
            "```",
            "",
        ]
    )


early_warning_tex = ROOT / "artifacts" / "final_evidence_package" / "export" / "tables" / "table_early_warning_consequence_audit.tex"
if early_warning_tex.exists():
    gate_evolution = ""
    gate_evolution_csv = ROOT / "artifacts" / "mechanism_behavior_pack_wtb" / "gate_transition_lead_lag.csv"
    if gate_evolution_csv.exists():
        gate_evolution = "\n" + _gate_evolution_section(gate_evolution_csv)
    modular_classifier = ""
    modular_classifier_summary = ROOT / "artifacts" / "modular_classifier_reserve_control" / "modular_classifier_reserve_summary.csv"
    if modular_classifier_summary.exists():
        modular_classifier = "\n" + _modular_classifier_reserve_section(modular_classifier_summary)
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
        + "\n```\n"
        + gate_evolution
        + modular_classifier
        + "\n"
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
        "Table A11 is the compact reviewer-facing boundary audit. The same-router "
        "boundary comparison has seed-paired uncertainty support, while physical-bin, "
        "full-sample, and cross-backbone comparisons still bound the claim away from "
        "policy optimality or market-dispatch value.\n\n"
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
        "accounting and an illustrative 100 EUR/MWh reserve-cost-scale marker; it is not a market-settlement, "
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

dest = ROOT / "paper_tste_supplementary.md"
if "--force" in sys.argv:
    dest.write_text(out, encoding="utf-8")
    print(f"Force-written {dest.name}  ({len(out.splitlines())} lines)")
else:
    print(f"Protected: {dest.name} is the primary source of truth. Pass --force to overwrite.")

