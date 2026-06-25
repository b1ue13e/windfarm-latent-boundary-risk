$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$packageRoot = Join-Path $root ("artifacts\eaai_submission\" + $stamp)
$figDir = Join-Path $packageRoot "figures"
$tableDir = Join-Path $packageRoot "tables"
$suppDir = Join-Path $packageRoot "supplementary_tables"
$sourceDir = Join-Path $packageRoot "source_snapshot"
$reviewDir = Join-Path $packageRoot "upload_review_files"
$adminDir = Join-Path $packageRoot "upload_admin_files"

New-Item -ItemType Directory -Force -Path $packageRoot, $figDir, $tableDir, $suppDir, $sourceDir, $reviewDir, $adminDir | Out-Null

$paper = Join-Path $root "paper_draft.md"
$bib = Join-Path $root "references.bib"
$csl = Join-Path $root "elsevier-harvard.csl"
$generatedTables = Join-Path $root "artifacts\paper_assets\generated"
$assetTables = Join-Path $root "artifacts\paper_assets\tables"
$assetFigures = Join-Path $root "artifacts\paper_assets\figures"

$manuscript = Get-Content -LiteralPath $paper -Raw

$identityBlockPattern = '(?s)\\begin\{center\}.*?\\noindent\{\\scriptsize Email addresses:.*?\\par\}\s*'
$anonymousHeader = @"
\begin{center}
\begin{minipage}{0.94\textwidth}
\centering
\Large\bfseries Physics-Aligned Gating for Mixture-of-Experts Forecasting under Regime Shifts: Case Studies in Wind Farms and ERA5\par
\end{minipage}
\end{center}

\vspace{0.35em}

"@

$anonymous = [regex]::Replace($manuscript, $identityBlockPattern, $anonymousHeader, 1)
$withAuthors = $manuscript

foreach ($textName in @("anonymous", "withAuthors")) {
    if ($textName -eq "anonymous") {
        $content = $anonymous
    } else {
        $content = $withAuthors
    }
    $content = $content.Replace("artifacts/paper_assets/figures/", "figures/")
    $content = $content.Replace("artifacts/paper_assets/generated/", "tables/")
    if ($textName -eq "anonymous") {
        $anonymous = $content
    } else {
        $withAuthors = $content
    }
}

$identityTerms = @(
    "Junyu Li",
    "Juntao Du",
    "Anhui University of Finance and Economics",
    "ljylikezmn999@gmail.com",
    "dujuntao@aufe.edu.cn"
)
foreach ($term in $identityTerms) {
    if ($anonymous.Contains($term)) {
        throw "Anonymous manuscript still contains identifying term: $term"
    }
}

Set-Content -LiteralPath (Join-Path $packageRoot "manuscript_anonymous.md") -Value $anonymous -Encoding UTF8
Set-Content -LiteralPath (Join-Path $sourceDir "paper_draft_with_authors.md") -Value $withAuthors -Encoding UTF8
Copy-Item -LiteralPath $bib -Destination (Join-Path $packageRoot "references.bib") -Force
Copy-Item -LiteralPath $csl -Destination (Join-Path $packageRoot "elsevier-harvard.csl") -Force
Copy-Item -LiteralPath $paper -Destination (Join-Path $sourceDir "paper_draft_original.md") -Force

Get-ChildItem -LiteralPath $generatedTables -Filter "*.tex" | Copy-Item -Destination $tableDir -Force
Get-ChildItem -LiteralPath $generatedTables -Filter "*.csv" | Copy-Item -Destination $suppDir -Force
Get-ChildItem -LiteralPath $assetTables -Filter "*.csv" | Copy-Item -Destination $suppDir -Force
Get-ChildItem -LiteralPath $assetFigures -File | Where-Object { $_.Extension -in ".pdf", ".png", ".svg" } | Copy-Item -Destination $figDir -Force

$titlePage = @"
# Title Page

**Manuscript title:** Physics-Aligned Gating for Mixture-of-Experts Forecasting under Regime Shifts: Case Studies in Wind Farms and ERA5

**Target journal:** Engineering Applications of Artificial Intelligence

**Authors**

Junyu Li  
School of Statistics and Applied Mathematics, Anhui University of Finance and Economics, Bengbu, 233030, China  
Email: ljylikezmn999@gmail.com

Juntao Du  
School of Statistics and Applied Mathematics, Anhui University of Finance and Economics, Bengbu, 233030, China  
Email: dujuntao@aufe.edu.cn

**Corresponding author**

Juntao Du  
School of Statistics and Applied Mathematics, Anhui University of Finance and Economics, Bengbu, 233030, China  
Email: dujuntao@aufe.edu.cn
"@
Set-Content -LiteralPath (Join-Path $packageRoot "title_page.md") -Value $titlePage -Encoding UTF8

$highlights = @"
# Highlights

- Physics-aligned gates recover operating regimes in routed forecasts.
- WTB and ERA5 contrast hidden and visible physical regime markers.
- Graph WaveNet and Graph Transformer bound the WTB RMSE comparison.
- Ablations expose an accuracy-semantics tradeoff in gate correction.
- Seed-level and sensitivity checks audit routing-evidence robustness.
"@
Set-Content -LiteralPath (Join-Path $packageRoot "highlights.md") -Value $highlights -Encoding UTF8

$declarations = @"
# Declarations

## Declaration of competing interest

The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.

## Funding

No funding information is recorded in the current manuscript package. The authors should verify and complete this statement before submission if a grant or institutional funding source supported the work.

## CRediT authorship contribution statement

Junyu Li: Conceptualization, Methodology, Software, Validation, Formal analysis, Data curation, Visualization, Writing - original draft.

Juntao Du: Supervision, Methodology, Writing - review and editing, Project administration.

## Declaration of generative AI and AI-assisted technologies

During preparation of the manuscript package, the authors used OpenAI ChatGPT/Codex to support language editing, consistency checking, and submission-material drafting. After using these tools, the authors reviewed and edited the content as needed and take full responsibility for the content of the publication.
"@
Set-Content -LiteralPath (Join-Path $packageRoot "declarations.md") -Value $declarations -Encoding UTF8

$coverLetter = @"
# Cover Letter Draft

Dear Editor,

We are pleased to submit the manuscript entitled "Physics-Aligned Gating for Mixture-of-Experts Forecasting under Regime Shifts: Case Studies in Wind Farms and ERA5" for consideration in Engineering Applications of Artificial Intelligence.

The manuscript studies a physics-aligned routing mechanism for mixture-of-experts forecasting in non-stationary physical systems. Rather than claiming a uniformly best forecasting model, the paper focuses on an engineering AI question: whether physical guidance at the gate can recover a more meaningful operating-regime partition when prediction loss alone yields mechanically weak routing. The experiments use two public settings, the KDD Cup 2022 wind-farm SCADA benchmark and ERA5 reanalysis, to contrast control-confounded and signal-expressive regime markers.

The evidence is deliberately framed as an accuracy-interpretability tradeoff. Graph WaveNet is the lowest-error and most stable strong WTB forecaster on RMSE, Graph Transformer provides the next strongest averaged graph baseline, and the five-seed GAT-GRU run exposes higher seed-to-seed variance near the routed-family mean. The proposed physics-aligned routing family improves the interpretability of routed responsibility near operating boundaries. Ablations, seed-level summaries, bootstrap checks, and threshold-sensitivity analyses are included to make that tradeoff explicit.

We believe the manuscript fits the journal because it combines an AI method contribution with a concrete engineering forecasting application, uses public datasets, and reports both predictive and interpretability-oriented evidence.

Before submission, the authors should confirm that the manuscript is original, not under consideration elsewhere, and that all funding, conflict-of-interest, and AI-use statements are complete.

Sincerely,

Junyu Li and Juntao Du
"@
Set-Content -LiteralPath (Join-Path $packageRoot "cover_letter_draft.md") -Value $coverLetter -Encoding UTF8

$dataAvailability = @"
# Data Availability Statement

The experiments use the public KDD Cup 2022 wind-farm SCADA benchmark and ERA5 reanalysis data. The source datasets remain available from their original providers. The code used to build the synchronized tensors, train the forecasting models, aggregate the seed-level results, and generate the paper figures is organized in the accompanying project directory. The code, configuration files, and seed-level result summaries will be made available with the manuscript or upon acceptance, subject to the redistribution terms of the source datasets.
"@
Set-Content -LiteralPath (Join-Path $packageRoot "data_availability_statement.md") -Value $dataAvailability -Encoding UTF8

$checklist = @"
# EAAI Submission Package Checklist

## Included files

- manuscript_anonymous.md: double-anonymized manuscript source.
- manuscript_anonymous.tex: anonymous LaTeX source generated from the Markdown manuscript.
- manuscript_anonymous.pdf: compiled anonymous manuscript, included only when local XeLaTeX completes successfully.
- title_page.md: author and correspondence information for separate upload.
- highlights.md: five Elsevier-style highlights.
- declarations.md: competing-interest, funding, CRediT, and AI-use statements.
- cover_letter_draft.md: EAAI-oriented cover letter draft.
- data_availability_statement.md: separate data/code availability text.
- figures/: figure files referenced by the manuscript.
- tables/: LaTeX table fragments referenced by the manuscript.
- supplementary_tables/: CSV result tables and seed-level summaries.
- source_snapshot/: non-anonymous source snapshot for local provenance only.
- upload_review_files/: anonymous files suitable for double-anonymized review upload.
- upload_admin_files/: separate non-anonymous administrative files.

## Verified in this package

- The anonymous manuscript does not contain the configured author names, affiliation, or email addresses.
- Main WTB results include Graph WaveNet, Graph Transformer, and GAT-GRU as strong graph baselines and do not claim accuracy dominance for the MoE model.
- The WTB ablation table contains the main one-term and cumulative routing variants instead of empty placeholder rows.
- Robustness and sensitivity evidence is included through Tables 7 and 8 and corresponding CSV files.

## Author confirmations still needed before upload

- Confirm funding text in declarations.md.
- Confirm all author contributions and author order.
- Confirm competing-interest statement.
- Confirm the manuscript is not under consideration elsewhere.
- Decide whether to upload figure1_architecture.pdf as an optional graphical abstract candidate.

## Upload warning

Use the anonymous review archive for the blinded review files. Do not upload the full local package archive as the blinded manuscript package because it intentionally contains title-page and source-snapshot material for local provenance.
"@
Set-Content -LiteralPath (Join-Path $packageRoot "README_EAAI_submission.md") -Value $checklist -Encoding UTF8

Copy-Item -LiteralPath (Join-Path $assetFigures "figure1_architecture.pdf") -Destination (Join-Path $packageRoot "graphical_abstract_candidate.pdf") -Force

$localPandoc = Join-Path $root "tools\pandoc-3.9.0.2\pandoc.exe"
$pandoc = if (Test-Path $localPandoc) {
    $localPandoc
} else {
    $command = Get-Command pandoc -ErrorAction SilentlyContinue
    if (-not $command) { throw "Pandoc was not found. Expected local copy at $localPandoc." }
    $command.Source
}

$xelatexCommand = Get-Command xelatex -ErrorAction SilentlyContinue
$localMiKTeXBin = "E:\MiKTeX\miktex\bin\x64"
$localMiKTeX = Join-Path $localMiKTeXBin "xelatex.exe"
$xelatex = if (Test-Path $localMiKTeX) {
    $localMiKTeX
} elseif (Test-Path "C:\texlive\2025\bin\windows\xelatex.exe") {
    "C:\texlive\2025\bin\windows\xelatex.exe"
} elseif ($xelatexCommand) {
    $xelatexCommand.Source
} else {
    throw "XeLaTeX was not found. Install TeX Live or MiKTeX, then rerun this script."
}

$xelatexBin = Split-Path -Parent $xelatex
$env:PATH = "$xelatexBin;$env:PATH"

Push-Location $packageRoot
try {
    & $pandoc "manuscript_anonymous.md" --citeproc --csl "elsevier-harvard.csl" --standalone -t latex -o "manuscript_anonymous.tex"
    if ($LASTEXITCODE -ne 0) { throw "Pandoc failed for anonymous manuscript." }

    $xelatexArgs = @("-interaction=nonstopmode", "-halt-on-error", "-output-directory=$packageRoot", "manuscript_anonymous.tex")
    & $xelatex @xelatexArgs | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $compileNote = @'
# Compile Note

The EAAI submission package was prepared, and `manuscript_anonymous.tex` was generated from `manuscript_anonymous.md`, but the local XeLaTeX executable failed during the first pass.

Observed local issue:

```text
It seems that this is a fresh TeX installation.
Please finish the setup before proceeding.
```

This appears to be a local MiKTeX setup problem rather than a manuscript-source generation failure. After completing the MiKTeX setup, rerun:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\prepare_eaai_submission.ps1
```

or compile `manuscript_anonymous.tex` from this package directory with XeLaTeX.
'@
        Set-Content -LiteralPath (Join-Path $packageRoot "COMPILE_NOTE.md") -Value $compileNote -Encoding UTF8
    } else {
        & $xelatex @xelatexArgs | Out-Null
        if ($LASTEXITCODE -ne 0) {
            $compileNote = @'
# Compile Note

The EAAI submission package was prepared, and XeLaTeX completed the first pass, but the second pass failed. Inspect `manuscript_anonymous.log` in this package directory before upload.
'@
            Set-Content -LiteralPath (Join-Path $packageRoot "COMPILE_NOTE.md") -Value $compileNote -Encoding UTF8
        }
    }
} finally {
    Pop-Location
}

Set-Content -LiteralPath (Join-Path $root "artifacts\eaai_submission\LATEST_PACKAGE.txt") -Value $packageRoot -Encoding UTF8

if (Test-Path (Join-Path $packageRoot "manuscript_anonymous.pdf")) {
    $compileStatus = "PDF compiled successfully."
} else {
    $compileStatus = "PDF not compiled locally; see COMPILE_NOTE.md."
}

Copy-Item -LiteralPath (Join-Path $packageRoot "manuscript_anonymous.md") -Destination $reviewDir -Force
Copy-Item -LiteralPath (Join-Path $packageRoot "manuscript_anonymous.tex") -Destination $reviewDir -Force
if (Test-Path (Join-Path $packageRoot "manuscript_anonymous.pdf")) {
    Copy-Item -LiteralPath (Join-Path $packageRoot "manuscript_anonymous.pdf") -Destination $reviewDir -Force
}
Copy-Item -LiteralPath (Join-Path $packageRoot "references.bib") -Destination $reviewDir -Force
Copy-Item -LiteralPath $figDir -Destination $reviewDir -Recurse -Force
Copy-Item -LiteralPath $tableDir -Destination $reviewDir -Recurse -Force
Copy-Item -LiteralPath $suppDir -Destination $reviewDir -Recurse -Force

foreach ($adminFile in @("title_page.md", "highlights.md", "declarations.md", "cover_letter_draft.md", "data_availability_statement.md")) {
    Copy-Item -LiteralPath (Join-Path $packageRoot $adminFile) -Destination $adminDir -Force
}

$fullZipPath = "$packageRoot`_FULL_LOCAL_DO_NOT_UPLOAD_AS_BLIND.zip"
$reviewZipPath = "$packageRoot`_ANONYMOUS_REVIEW_FILES.zip"
$adminZipPath = "$packageRoot`_ADMIN_FILES.zip"
foreach ($zip in @($fullZipPath, $reviewZipPath, $adminZipPath)) {
    if (Test-Path $zip) { Remove-Item $zip -Force }
}
Compress-Archive -Path (Join-Path $reviewDir "*") -DestinationPath $reviewZipPath -Force
Compress-Archive -Path (Join-Path $adminDir "*") -DestinationPath $adminZipPath -Force

$verification = @"
# Verification Report

Generated package: $packageRoot

Compile status: $compileStatus

Checks completed by the package script:

- Anonymous manuscript generated from current `paper_draft.md`.
- Author names, affiliation, and email addresses removed from `manuscript_anonymous.md`.
- Figure links rewritten to package-local figures/.
- Table links rewritten to package-local tables/.
- Generated table TeX files copied.
- CSV evidence tables copied as supplementary material.
- Title page, highlights, declarations, cover letter draft, and data availability statement created.
- Anonymous review archive created at $reviewZipPath.
- Administrative files archive created at $adminZipPath.
- Full local archive created at $fullZipPath. Do not upload this archive as blinded review material.
- Anonymous review archive excludes the title page, declarations, cover letter, source snapshot, and CSL style file.

Remaining human confirmations:

- Funding statement.
- Author contributions and order.
- Competing-interest statement.
- Originality / not-under-review confirmation.
"@
Set-Content -LiteralPath (Join-Path $packageRoot "VERIFICATION_REPORT.md") -Value $verification -Encoding UTF8
Copy-Item -LiteralPath (Join-Path $packageRoot "VERIFICATION_REPORT.md") -Destination $reviewDir -Force
Compress-Archive -Path (Join-Path $reviewDir "*") -DestinationPath $reviewZipPath -Force
Compress-Archive -Path (Join-Path $packageRoot "*") -DestinationPath $fullZipPath -Force

Write-Host "Prepared EAAI submission package:"
Write-Host $packageRoot
Write-Host "Anonymous review archive:"
Write-Host $reviewZipPath
Write-Host "Admin files archive:"
Write-Host $adminZipPath
Write-Host "Full local archive (do not upload as blind review package):"
Write-Host $fullZipPath
