$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$packageRoot = Join-Path $root ("artifacts\tste_submission\" + $stamp)
$uploadDir = Join-Path $packageRoot "upload_files"
$sourceDir = Join-Path $packageRoot "source_files"
$evidenceDir = Join-Path $packageRoot "evidence_audits"
$buildLogDir = Join-Path $packageRoot "build_logs"

New-Item -ItemType Directory -Force -Path $packageRoot, $uploadDir, $sourceDir, $evidenceDir, $buildLogDir | Out-Null

$requiredFiles = @(
    "paper_tste_ieee.pdf",
    "paper_tste_supplementary.pdf",
    "cover_letter_tste.md",
    "paper_tste_ieee.md",
    "paper_tste_supplementary.md",
    "references.bib",
    "IEEE.csl",
    "TUptm.fd"
)

foreach ($rel in $requiredFiles) {
    $path = Join-Path $root $rel
    if (-not (Test-Path $path)) {
        throw "Missing required TSTE submission file: $rel"
    }
}

$coverText = Get-Content -LiteralPath (Join-Path $root "cover_letter_tste.md") -Raw
if ($coverText.Contains("[Author Names]")) {
    throw "cover_letter_tste.md still contains the [Author Names] placeholder."
}
if (-not $coverText.Contains("Supplementary Table A10")) {
    throw "cover_letter_tste.md does not mention Supplementary Table A10 claim boundaries."
}

& python (Join-Path $root "scripts\transform_ieee.py")
if ($LASTEXITCODE -ne 0) { throw "IEEE markdown transform failed." }
& python (Join-Path $root "scripts\make_supplementary.py")
if ($LASTEXITCODE -ne 0) { throw "Supplementary markdown generation failed." }
& powershell -ExecutionPolicy Bypass -File (Join-Path $root "scripts\build_paper_ieee.ps1")
if ($LASTEXITCODE -ne 0) { throw "IEEE PDF build failed." }

Copy-Item -LiteralPath (Join-Path $root "build\paper_tste_ieee.pdf") -Destination (Join-Path $root "paper_tste_ieee.pdf") -Force
Copy-Item -LiteralPath (Join-Path $root "build\paper_tste_supplementary.pdf") -Destination (Join-Path $root "paper_tste_supplementary.pdf") -Force

$mainPages = (& pdfinfo (Join-Path $root "paper_tste_ieee.pdf") | Select-String "^Pages:\s+(\d+)").Matches[0].Groups[1].Value
$suppPages = (& pdfinfo (Join-Path $root "paper_tste_supplementary.pdf") | Select-String "^Pages:\s+(\d+)").Matches[0].Groups[1].Value
if ([int]$mainPages -gt 10) {
    throw "IEEE main manuscript exceeds 10 pages: $mainPages"
}

$logPattern = "Font Warning|No file TUptm|undefined citation|Citation .* undefined|Overfull|Undefined control sequence|Some font shapes|TU/ptm|LaTeX Warning: Reference.*undefined|undefined references|LaTeX Error"
$mainLog = Join-Path $root "build\paper_tste_ieee.log"
$suppLog = Join-Path $root "build\paper_tste_supplementary.log"
$logHits = & rg -n $logPattern $mainLog $suppLog -S 2>$null
if ($LASTEXITCODE -eq 0) {
    $logHits | Set-Content -LiteralPath (Join-Path $packageRoot "latex_log_findings.txt") -Encoding UTF8
    throw "LaTeX log contains blocking warnings/errors. See latex_log_findings.txt."
}

$freezeDir = Join-Path $root "artifacts\tste_evidence_freeze_guard"
& python (Join-Path $root "main.py") evidence-freeze-guard `
    --paper-path (Join-Path $root "paper_tste_ieee.md") `
    --compiled-tex (Join-Path $root "build\paper_tste_ieee.tex") `
    --paper-assets-dir (Join-Path $root "artifacts\paper_assets") `
    --final-package-dir (Join-Path $root "artifacts\final_evidence_package") `
    --paired-effects (Join-Path $root "artifacts\strictmask_combined_reviewer_stats\paired_effects_summary.csv") `
    --output-dir $freezeDir `
    --required-tokens "236.13,225.74,0.960,0.196,0.508,0.8716,0.9166,84.58M,84.31M,88.13M,10.39,0.764,566"
if ($LASTEXITCODE -ne 0) { throw "Evidence-freeze guard command failed." }
$freezeJson = Get-Content -LiteralPath (Join-Path $freezeDir "evidence_freeze_guard.json") -Raw | ConvertFrom-Json
$freezeStatus = [string]$freezeJson.status
if ($freezeStatus -ne "complete_ready_for_evidence_freeze") {
    throw "Evidence-freeze guard status is $freezeStatus."
}

$uploadMap = @{
    "paper_tste_ieee.pdf" = "manuscript_ieee_tste.pdf"
    "paper_tste_supplementary.pdf" = "supplementary_material.pdf"
    "cover_letter_tste.md" = "cover_letter.md"
}
foreach ($entry in $uploadMap.GetEnumerator()) {
    Copy-Item -LiteralPath (Join-Path $root $entry.Key) -Destination (Join-Path $uploadDir $entry.Value) -Force
}

foreach ($rel in @(
    "paper_tste_ieee.md",
    "paper_tste_supplementary.md",
    "paper_draft.md",
    "cover_letter_tste.md",
    "references.bib",
    "IEEE.csl",
    "TUptm.fd",
    "scripts\prepare_tste_submission.ps1",
    "scripts\build_paper_ieee.ps1",
    "scripts\transform_ieee.py",
    "scripts\make_supplementary.py",
    "scripts\build_accountability_tradeoff.py",
    "scripts\build_statistical_claim_table.py",
    "scripts\build_early_warning_consequence_table.py",
    "scripts\build_reserve_claim_boundary_table.py",
    "scripts\build_outcome_channel_sanity.py",
    "scripts\build_external_deployment_gate_audit.py"
)) {
    $src = Join-Path $root $rel
    if (Test-Path $src) {
        $dest = Join-Path $sourceDir $rel
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
        Copy-Item -LiteralPath $src -Destination $dest -Force
    }
}

foreach ($rel in @(
    "build\paper_tste_ieee.tex",
    "build\paper_tste_supplementary.tex",
    "build\paper_tste_ieee.log",
    "build\paper_tste_supplementary.log"
)) {
    Copy-Item -LiteralPath (Join-Path $root $rel) -Destination (Join-Path $buildLogDir (Split-Path -Leaf $rel)) -Force
}

$auditFiles = @(
    "statistical_claim_boundaries.csv",
    "table_statistical_claim_boundaries.tex",
    "outcome_channel_sanity_summary.csv",
    "table_outcome_channel_sanity.tex",
    "external_deployment_gate_audit.csv",
    "table_external_deployment_gate_audit.tex",
    "early_warning_consequence_audit.csv",
    "table_early_warning_consequence_audit.tex",
    "reserve_claim_boundary_audit.csv",
    "table_reserve_claim_boundary_audit.tex",
    "accountability_tradeoff.csv",
    "table_accountability_tradeoff.tex"
)
$tableRoot = Join-Path $root "artifacts\final_evidence_package\export\tables"
foreach ($file in $auditFiles) {
    $src = Join-Path $tableRoot $file
    if (Test-Path $src) {
        Copy-Item -LiteralPath $src -Destination (Join-Path $evidenceDir $file) -Force
    }
}
Copy-Item -LiteralPath (Join-Path $freezeDir "evidence_freeze_guard.json") -Destination $evidenceDir -Force
Copy-Item -LiteralPath (Join-Path $freezeDir "evidence_freeze_guard_checks.csv") -Destination $evidenceDir -Force
Copy-Item -LiteralPath (Join-Path $freezeDir "evidence_freeze_required_tokens.csv") -Destination $evidenceDir -Force

$readme = @"
# IEEE TSTE Submission Package

Generated: $stamp

## Upload files

- `upload_files/manuscript_ieee_tste.pdf`: IEEEtran main manuscript.
- `upload_files/supplementary_material.pdf`: supplementary appendix with Tables A1-A10.
- `upload_files/cover_letter.md`: TSTE cover letter aligned with claim audits.

## Verification

- Main manuscript pages: $mainPages.
- Supplementary pages: $suppPages.
- IEEE build completed through `scripts/build_paper_ieee.ps1`.
- LaTeX blocking warning/error scan: passed.
- Evidence-freeze guard status: $freezeStatus.
- Cover letter placeholder check: passed.

## Claim-boundary audits included

- Supplementary Table A6: statistical claim boundaries.
- Supplementary Table A7: outcome-channel sanity audit.
- Supplementary Table A8: external-site deployment gates.
- Supplementary Table A9: early-warning detection consequence.
- Supplementary Table A10: reserve-policy claim boundary.

## Human confirmations before upload

- Confirm funding and conflict-of-interest declarations in the journal portal.
- Confirm author order and corresponding-author metadata.
- Confirm the manuscript is not under consideration elsewhere.
- Check whether the portal requires source files in addition to PDFs.
"@
Set-Content -LiteralPath (Join-Path $packageRoot "README_TSTE_submission.md") -Value $readme -Encoding UTF8

$verification = @"
# Verification Report

Package root: $packageRoot

Checks completed:

- Required files exist.
- Cover letter has no `[Author Names]` placeholder.
- IEEE Markdown and supplementary Markdown regenerated.
- Main and supplementary PDFs rebuilt.
- Main manuscript page count is $mainPages.
- Supplementary page count is $suppPages.
- LaTeX blocking warning/error scan passed.
- Evidence-freeze guard completed with status $freezeStatus.
- Upload, source, build-log, and evidence-audit folders populated.

Generated archives:

- TSTE_UPLOAD_FILES.zip
- TSTE_SOURCE_FILES.zip
- TSTE_FULL_LOCAL_PACKAGE.zip
"@
Set-Content -LiteralPath (Join-Path $packageRoot "VERIFICATION_REPORT.md") -Value $verification -Encoding UTF8
Copy-Item -LiteralPath (Join-Path $packageRoot "VERIFICATION_REPORT.md") -Destination $uploadDir -Force

Set-Content -LiteralPath (Join-Path $root "artifacts\tste_submission\LATEST_PACKAGE.txt") -Value $packageRoot -Encoding UTF8

$uploadZip = Join-Path $packageRoot "TSTE_UPLOAD_FILES.zip"
$sourceZip = Join-Path $packageRoot "TSTE_SOURCE_FILES.zip"
$fullZip = Join-Path $packageRoot "TSTE_FULL_LOCAL_PACKAGE.zip"
foreach ($zip in @($uploadZip, $sourceZip, $fullZip)) {
    if (Test-Path $zip) { Remove-Item $zip -Force }
}
Compress-Archive -Path (Join-Path $uploadDir "*") -DestinationPath $uploadZip -Force
Compress-Archive -Path (Join-Path $sourceDir "*") -DestinationPath $sourceZip -Force
Compress-Archive -Path (Join-Path $packageRoot "*") -DestinationPath $fullZip -Force

Write-Host "Prepared IEEE TSTE submission package:"
Write-Host $packageRoot
Write-Host "Upload archive:"
Write-Host $uploadZip
Write-Host "Source archive:"
Write-Host $sourceZip
Write-Host "Full local archive:"
Write-Host $fullZip
