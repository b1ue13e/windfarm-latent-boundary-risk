"""Extract Appendix A from paper_draft.md -> paper_tste_supplementary.md."""
import pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).parent.parent
src = (ROOT / "paper_draft.md").read_text(encoding="utf-8")

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

benchmark_path = ROOT / "artifacts" / "paper_assets" / "tables" / "table_main_benchmark.csv"
if benchmark_path.exists():
    benchmark = pd.read_csv(benchmark_path)
    expanded_models = [
        "Graph WaveNet",
        "Graph Transformer",
        "GAT-GRU",
        "PatchTST",
        "iTransformer",
        "TiDE",
        "Physics-Aligned MoE",
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
                    str(row["Overall MAE"]),
                    str(row["Switch RMSE"]),
                    str(row["Switch MAE"]),
                    str(row["n_runs"]),
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
                r"\caption*{\textbf{Table A12.} Expanded WTB strict-cache forecasting baselines (mean $\pm$ std across seeds where repeated runs are available).}",
                r"\resizebox{\columnwidth}{!}{%",
                r"\begin{tabular}{lrrrrr}",
                r"\toprule",
                r"Model & Overall RMSE & Overall MAE & Switch RMSE & Switch MAE & n \\",
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
    "csl: elsevier-numbered.csl",
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
