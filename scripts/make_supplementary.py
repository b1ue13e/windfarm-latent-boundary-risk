"""Extract Appendix A from paper_draft.md -> paper_tste_supplementary.md."""
import pathlib

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
    "\\bottomrule\n\\end{tabularx}\n\\end{table}\n```\n\n## Auxiliary losses",
    "\\bottomrule\n\\end{tabular}%\n}\n\\end{table}\n```\n\n## Auxiliary losses",
    1,
)

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
