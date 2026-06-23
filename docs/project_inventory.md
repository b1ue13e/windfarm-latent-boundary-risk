# Project Inventory

Last updated: 2026-06-23.

## Current Entry Points

- `main.py`: CLI entry point for preprocessing, training, evidence checks, export, and paper-related guards.
- `windfarm_moe/`: project package with data processing, model, evaluation, evidence export, reproduction, and reviewer-facing diagnostics.
- `scripts/`: PowerShell and Python helper scripts for paper builds, external-wind evidence, diagnostics, and submission packaging.
- `tests/`: focused unit and smoke tests for the package.

## Manuscript Files

- `paper_draft.md`: current manuscript source.
- `paper_draft.pdf`: current rendered manuscript PDF.
- `paper_draft_compiled.tex`: current Pandoc/XeLaTeX intermediate used by evidence-freeze checks.
- `paper_draft_compiled.pdf`: current compiled PDF generated from `paper_draft_compiled.tex`.
- `references.bib`: current bibliography.
- `elsevier-harvard.csl`: CSL file used by `scripts/build_paper.ps1` and submission helpers.
- `AE_MAJOR_REVISION_FAILSAFE_PLAN.md`: Applied Energy major-revision failsafe plan.

These files stay in the repository root because several scripts and guards use them as default paths.

## Data Files

- `wtbdata_245days.csv`: raw WTB dynamic data. This is large and intentionally ignored by Git.
- `sdwpf_baidukddcup2022_turb_location.CSV`: turbine location metadata. It is kept beside the raw dynamic data because the default CLI arguments point to the repository root.
- `data/external_wind/`: external-wind data cache and inspection material.

## Generated Evidence And Outputs

- `artifacts/`: experiment caches, tables, figures, guards, evidence packages, and reviewer-facing exports. Some final evidence files are already tracked, but new generated output is ignored by default to keep Git status readable.
- `pagecheck/`: local PDF page-render checks.
- `tmp/`: scratch space.

## Archives And Logs

- `archives/paper_drafts_202603/`: old manuscript PDFs/TEX files from March 2026, including citation/debug/style-check builds.
- `archives/cloud_exports/`: old cloud upload notes and export packages.
- `archives/raw_results/`: raw XML result export moved out of the root.
- `logs/latex/`: LaTeX auxiliary files and historical XeLaTeX check output.

## Recommended Commands

Build the manuscript:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_paper.ps1
```

Run a focused test slice:

```powershell
python -m pytest tests/test_smoke.py tests/test_paper.py
```

Check current Git state without generated-output noise:

```powershell
git status --short
```
