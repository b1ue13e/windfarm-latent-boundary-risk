# Project Inventory

Last updated: 2026-06-28.

Active submission line: IEEE Transactions on Sustainable Energy (TSTE). Applied Energy materials are retained as historical/failsafe artifacts and should not be treated as the current submission target unless explicitly reactivated.

## Current Entry Points

- `main.py`: CLI entry point for preprocessing, training, evidence checks, export, and paper-related guards.
- `windfarm_moe/`: project package with data processing, model, evaluation, evidence export, reproduction, and reviewer-facing diagnostics.
- `scripts/`: PowerShell and Python helper scripts for paper builds, external-wind evidence, diagnostics, and submission packaging.
- `tests/`: focused unit and smoke tests for the package.

## Manuscript Files

- `paper_tste_ieee.md`: active IEEE TSTE main manuscript source.
- `paper_tste_ieee.pdf`: active IEEE TSTE main manuscript PDF, copied from `build/paper_tste_ieee.pdf` by the TSTE packaging script.
- `paper_tste_supplementary.md`: active IEEE TSTE supplementary material source.
- `paper_tste_supplementary.pdf`: active IEEE TSTE supplementary PDF, copied from `build/paper_tste_supplementary.pdf` by the TSTE packaging script.
- `cover_letter_tste.md`: active TSTE cover letter.
- `paper_draft.md`: source manuscript used by `scripts/transform_ieee.py` and retained Applied Energy/failsafe line.
- `paper_draft.pdf`: historical/failsafe rendered manuscript PDF.
- `paper_draft_compiled.tex`: historical/failsafe Pandoc/XeLaTeX intermediate used by legacy evidence-freeze checks.
- `paper_draft_compiled.pdf`: historical/failsafe compiled PDF generated from `paper_draft_compiled.tex`.
- `references.bib`: current bibliography.
- `IEEE.csl`: CSL file used by the active IEEE TSTE build.
- `elsevier-harvard.csl`: CSL file used by legacy Applied Energy build helpers.
- `scripts/build_paper_ieee.ps1`: active TSTE build entry point.
- `scripts/prepare_tste_submission.ps1`: active TSTE submission-package entry point.
- `scripts/build_paper.ps1`: legacy Applied Energy/failsafe build entry point.
- `AE_MAJOR_REVISION_FAILSAFE_PLAN.md`: Applied Energy major-revision failsafe plan, if that line is reactivated.
- `docs/ieee_tste_transfer_execution.md`: IEEE TSTE transfer route, claim boundary, and anchor-stress completion commands.

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

Build the active IEEE TSTE manuscript:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_paper_ieee.ps1
```

Prepare and verify the TSTE submission package:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/prepare_tste_submission.ps1
```

Run a focused test slice:

```powershell
python -m pytest tests/test_smoke.py tests/test_paper.py
```

Check current Git state without generated-output noise:

```powershell
git status --short
```
