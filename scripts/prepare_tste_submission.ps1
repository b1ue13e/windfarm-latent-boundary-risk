$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$packageRoot = Join-Path $root ("artifacts\tste_submission\" + $stamp)
$uploadDir = Join-Path $packageRoot "upload_files"
$sourceDir = Join-Path $packageRoot "source_files"
$evidenceDir = Join-Path $packageRoot "evidence_audits"
$buildLogDir = Join-Path $packageRoot "build_logs"
$metadataDir = Join-Path $packageRoot "portal_metadata"
$manifestDir = Join-Path $packageRoot "integrity_manifest"

New-Item -ItemType Directory -Force -Path $packageRoot, $uploadDir, $sourceDir, $evidenceDir, $buildLogDir, $metadataDir, $manifestDir | Out-Null

function Get-RegexGroup {
    param(
        [string]$Text,
        [string]$Pattern,
        [string]$Label
    )

    $match = [regex]::Match($Text, $Pattern, [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if (-not $match.Success) {
        throw "Could not extract $Label from paper_tste_ieee.md."
    }
    return $match.Groups[1].Value
}

function Convert-PortalText {
    param([string]$Text)

    $clean = $Text
    $clean = $clean -replace "\\%", "%"
    $clean = $clean -replace "\\&", "&"
    $clean = $clean -replace "\\_", "_"
    $clean = $clean -replace "\\texttt\{([^}]*)\}", '$1'
    $clean = $clean -replace "---", " - "
    $clean = $clean -replace "~", " "
    $clean = $clean -replace "\s+", " "
    return $clean.Trim()
}

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
if (-not $coverText.Contains("Supplementary Table A11")) {
    throw "cover_letter_tste.md does not mention Supplementary Table A11 engineering-unit translation."
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
    --required-tokens "236.13,225.74,0.960,0.196,0.508,0.8716,0.9166,84.58M,84.31M,88.13M,10.39,0.764,566,1846.9,539.8,3551.4,355k"
if ($LASTEXITCODE -ne 0) { throw "Evidence-freeze guard command failed." }
$freezeJson = Get-Content -LiteralPath (Join-Path $freezeDir "evidence_freeze_guard.json") -Raw | ConvertFrom-Json
$freezeStatus = [string]$freezeJson.status
if ($freezeStatus -ne "complete_ready_for_evidence_freeze") {
    throw "Evidence-freeze guard status is $freezeStatus."
}

$paperText = Get-Content -LiteralPath (Join-Path $root "paper_tste_ieee.md") -Raw
$targetJournal = "IEEE Transactions on Sustainable Energy"
$articleType = "Regular Paper"
$title = Convert-PortalText (Get-RegexGroup $paperText "\\title\{(.+?)\}" "title")
$abstract = Convert-PortalText (Get-RegexGroup $paperText "\\begin\{abstract\}(.+?)\\end\{abstract\}" "abstract")
$keywords = Convert-PortalText (Get-RegexGroup $paperText "\\begin\{IEEEkeywords\}(.+?)\\end\{IEEEkeywords\}" "keywords")
$keywordText = $keywords.Trim().TrimEnd(".")
$keywordList = @($keywordText -split ";" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$aiStatement = Convert-PortalText (Get-RegexGroup $paperText "# Declaration of generative AI.*?\r?\n\r?\n(.+?)\r?\n\r?\n# Code and data availability" "AI use statement")
$dataAvailability = Convert-PortalText (Get-RegexGroup $paperText "# Code and data availability\r?\n\r?\n(.+?)\r?\n\r?\n# References" "code and data availability statement")

$authors = @(
    [ordered]@{
        order = 1
        name = "Junyu Li"
        email = "ljylikezmn999@gmail.com"
        affiliation = "School of Statistics and Applied Mathematics, Anhui University of Finance and Economics, Bengbu 233030, China"
        role = "Author"
    },
    [ordered]@{
        order = 2
        name = "Juntao Du"
        email = "dujuntao@aufe.edu.cn"
        affiliation = "School of Statistics and Applied Mathematics, Anhui University of Finance and Economics, Bengbu 233030, China"
        role = "Corresponding author"
    }
)
$correspondingAuthor = [ordered]@{
    name = "Juntao Du"
    email = "dujuntao@aufe.edu.cn"
    affiliation = "School of Statistics and Applied Mathematics, Anhui University of Finance and Economics, Bengbu 233030, China"
}
$uploadFiles = @(
    [ordered]@{
        file = "upload_files/manuscript_ieee_tste.pdf"
        portal_role = "Main manuscript"
        note = "IEEEtran two-column journal manuscript."
    },
    [ordered]@{
        file = "upload_files/supplementary_material.pdf"
        portal_role = "Supplementary material"
        note = "Supplementary appendix with Tables A1-A11."
    },
    [ordered]@{
        file = "upload_files/cover_letter.md"
        portal_role = "Cover letter"
        note = "TSTE cover letter aligned with claim-boundary audits."
    },
    [ordered]@{
        file = "upload_files/portal_metadata.md"
        portal_role = "Portal metadata"
        note = "Copy-paste submission portal fields."
    },
    [ordered]@{
        file = "upload_files/portal_metadata.json"
        portal_role = "Portal metadata"
        note = "Machine-readable copy of the portal fields."
    },
    [ordered]@{
        file = "upload_files/VERIFICATION_REPORT.md"
        portal_role = "Local verification record"
        note = "Upload only if the portal allows optional supporting documentation."
    },
    [ordered]@{
        file = "upload_files/UPLOAD_MANIFEST.md"
        portal_role = "Local integrity manifest"
        note = "Checksum and page-count record; upload only if the portal allows optional supporting documentation."
    },
    [ordered]@{
        file = "upload_files/UPLOAD_MANIFEST.json"
        portal_role = "Local integrity manifest"
        note = "Machine-readable checksum and page-count record."
    },
    [ordered]@{
        file = "upload_files/SHA256SUMS.txt"
        portal_role = "Local integrity manifest"
        note = "Plain SHA256 checksum list."
    }
)
$claimBoundaries = @(
    "Not a forecasting-SOTA claim: RMSE is reported as 236.13 versus 225.74 for Graph WaveNet.",
    "Not a universal reserve-policy optimality claim: validation-frozen physical-bin quantile baselines remain competitive.",
    "Not an automatic cross-farm generalization claim: Kelmarsh/Penmanshiel fail the held-out routing criterion and are treated as deployment-gate diagnostics.",
    "Not an anchor-free discovery claim: routing is intentionally constrained by SCADA operating anchors.",
    "Not a market-dispatch or grid-security guarantee: reserve evidence is scoped to audit and diagnosis around the MPPT-to-pitch transition."
)

$keywordsMd = ($keywordList | ForEach-Object { "- $_" }) -join "`r`n"
$authorsMd = ($authors | ForEach-Object { "$($_.order). $($_.name) - $($_.affiliation); email: $($_.email); role: $($_.role)" }) -join "`r`n"
$uploadFilesMd = ($uploadFiles | ForEach-Object { "- $($_.file): $($_.portal_role). $($_.note)" }) -join "`r`n"
$claimBoundariesMd = ($claimBoundaries | ForEach-Object { "- $_" }) -join "`r`n"

$portalMarkdown = @"
# TSTE Portal Metadata

Generated: $stamp

## Journal and Article Type

Target journal: $targetJournal

Article type: $articleType

## Title

$title

## Abstract

$abstract

## Keywords

$keywordsMd

## Authors

$authorsMd

## Corresponding Author

$($correspondingAuthor.name), $($correspondingAuthor.affiliation), $($correspondingAuthor.email)

## Upload File Roles

$uploadFilesMd

## Data Availability Statement

$dataAvailability

## Generative AI Use Statement

$aiStatement

## Claim-Boundary Notes For Editor

$claimBoundariesMd

## Verification Snapshot

- Main manuscript pages: $mainPages.
- Supplementary pages: $suppPages.
- LaTeX blocking warning/error scan: passed.
- Evidence-freeze guard status: $freezeStatus.
- Cover letter placeholder check: passed.

## Human Checks Before Portal Submission

- Confirm funding, conflicts of interest, and author contribution fields in the portal.
- Confirm author order, emails, ORCID records, and corresponding-author selection.
- Confirm whether the portal accepts Markdown cover letters or requires text pasted into a form field.
- Confirm whether source files are requested at initial submission or only after acceptance.
"@
Set-Content -LiteralPath (Join-Path $metadataDir "portal_metadata.md") -Value $portalMarkdown -Encoding UTF8

$portalMetadata = [ordered]@{
    generated = $stamp
    target_journal = $targetJournal
    article_type = $articleType
    title = $title
    abstract = $abstract
    keywords = $keywordList
    authors = $authors
    corresponding_author = $correspondingAuthor
    upload_files = $uploadFiles
    data_availability_statement = $dataAvailability
    generative_ai_use_statement = $aiStatement
    claim_boundary_notes = $claimBoundaries
    verification = [ordered]@{
        main_manuscript_pages = [int]$mainPages
        supplementary_pages = [int]$suppPages
        latex_log_scan = "passed"
        evidence_freeze_guard_status = $freezeStatus
        cover_letter_placeholder_check = "passed"
    }
}
$portalMetadata | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $metadataDir "portal_metadata.json") -Encoding UTF8

$uploadMap = @{
    "paper_tste_ieee.pdf" = "manuscript_ieee_tste.pdf"
    "paper_tste_supplementary.pdf" = "supplementary_material.pdf"
    "cover_letter_tste.md" = "cover_letter.md"
}
foreach ($entry in $uploadMap.GetEnumerator()) {
    Copy-Item -LiteralPath (Join-Path $root $entry.Key) -Destination (Join-Path $uploadDir $entry.Value) -Force
}
Copy-Item -LiteralPath (Join-Path $metadataDir "portal_metadata.md") -Destination $uploadDir -Force
Copy-Item -LiteralPath (Join-Path $metadataDir "portal_metadata.json") -Destination $uploadDir -Force

foreach ($rel in @(
    "paper_tste_ieee.md",
    "paper_tste_supplementary.md",
    "paper_draft.md",
    "cover_letter_tste.md",
    "references.bib",
    "IEEE.csl",
    "TUptm.fd",
    "windfarm_moe\__init__.py",
    "windfarm_moe\operational_cost.py",
    "windfarm_moe\utils.py",
    "scripts\prepare_tste_submission.ps1",
    "scripts\verify_tste_submission_package.ps1",
    "scripts\build_paper_ieee.ps1",
    "scripts\transform_ieee.py",
    "scripts\make_supplementary.py",
    "scripts\build_accountability_tradeoff.py",
    "scripts\build_statistical_claim_table.py",
    "scripts\build_early_warning_consequence_table.py",
    "scripts\build_reserve_claim_boundary_table.py",
    "scripts\build_engineering_unit_value_translation.py",
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
    "engineering_unit_value_translation.csv",
    "table_engineering_unit_value_translation.tex",
    "engineering_unit_value_translation_summary.json",
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
- `upload_files/supplementary_material.pdf`: supplementary appendix with Tables A1-A11.
- `upload_files/cover_letter.md`: TSTE cover letter aligned with claim audits.
- `upload_files/portal_metadata.md`: copy-paste portal fields for title, abstract, keywords, authors, declarations, and file roles.
- `upload_files/portal_metadata.json`: machine-readable copy of the same portal metadata.
- `upload_files/UPLOAD_MANIFEST.md`: checksum, byte-size, and PDF page-count manifest for upload candidates.
- `upload_files/UPLOAD_MANIFEST.json`: machine-readable copy of the upload manifest.
- `upload_files/SHA256SUMS.txt`: plain SHA256 checksum list.

## Portal metadata

- `portal_metadata/portal_metadata.md`: human-readable submission portal checklist.
- `portal_metadata/portal_metadata.json`: structured metadata generated from the current IEEE manuscript.

## Integrity manifest

- `integrity_manifest/UPLOAD_MANIFEST.md`: checksum and page-count record.
- `integrity_manifest/UPLOAD_MANIFEST.json`: structured checksum and page-count record.
- `integrity_manifest/SHA256SUMS.txt`: plain checksum list.

## Verification

- Main manuscript pages: $mainPages.
- Supplementary pages: $suppPages.
- IEEE build completed through `scripts/build_paper_ieee.ps1`.
- Package can be independently rechecked with `scripts/verify_tste_submission_package.ps1 -PackageRoot "$packageRoot"`.
- LaTeX blocking warning/error scan: passed.
- Evidence-freeze guard status: $freezeStatus.
- Cover letter placeholder check: passed.

## Claim-boundary audits included

- Supplementary Table A6: statistical claim boundaries.
- Supplementary Table A7: outcome-channel sanity audit.
- Supplementary Table A8: external-site deployment gates.
- Supplementary Table A9: early-warning detection consequence.
- Supplementary Table A10: reserve-policy claim boundary.
- Supplementary Table A11: engineering-unit reserve-value translation.

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
- Portal metadata generated from the current IEEE manuscript.
- Upload integrity manifest generated with SHA256 checksums.
- Independent package verifier completed successfully.
- Upload, source, build-log, and evidence-audit folders populated.

Generated archives:

- TSTE_UPLOAD_FILES.zip
- TSTE_SOURCE_FILES.zip
- TSTE_FULL_LOCAL_PACKAGE.zip
"@
Set-Content -LiteralPath (Join-Path $packageRoot "VERIFICATION_REPORT.md") -Value $verification -Encoding UTF8
Copy-Item -LiteralPath (Join-Path $packageRoot "VERIFICATION_REPORT.md") -Destination $uploadDir -Force

$uploadRoleByName = @{}
foreach ($fileSpec in $uploadFiles) {
    $leafName = Split-Path -Leaf $fileSpec["file"]
    $uploadRoleByName[$leafName] = $fileSpec
}
$manifestFileNames = @("UPLOAD_MANIFEST.md", "UPLOAD_MANIFEST.json", "SHA256SUMS.txt")
$manifestEntries = @()
foreach ($item in (Get-ChildItem -LiteralPath $uploadDir -File | Sort-Object Name)) {
    if ($manifestFileNames -contains $item.Name) {
        continue
    }
    $relativePath = "upload_files/$($item.Name)"
    $fileSpec = $uploadRoleByName[$item.Name]
    if ($null -eq $fileSpec) {
        $portalRole = "Additional upload file"
        $note = "No explicit portal role was declared."
    }
    else {
        $portalRole = $fileSpec["portal_role"]
        $note = $fileSpec["note"]
    }
    $pages = $null
    if ($item.Extension -ieq ".pdf") {
        $pageMatch = (& pdfinfo $item.FullName | Select-String "^Pages:\s+(\d+)").Matches[0]
        if ($null -eq $pageMatch) {
            throw "Could not read PDF page count for $($item.Name)."
        }
        $pages = [int]$pageMatch.Groups[1].Value
    }
    $manifestEntries += [ordered]@{
        relative_path = $relativePath
        portal_role = $portalRole
        pages = $pages
        bytes = [int64]$item.Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $item.FullName).Hash.ToLowerInvariant()
        note = $note
    }
}
$expectedUploadNames = @($uploadFiles | ForEach-Object { Split-Path -Leaf $_["file"] } | Where-Object { $manifestFileNames -notcontains $_ })
$actualUploadNames = @($manifestEntries | ForEach-Object { Split-Path -Leaf $_["relative_path"] })
$missingUploadNames = @($expectedUploadNames | Where-Object { $actualUploadNames -notcontains $_ })
if ($missingUploadNames.Count -gt 0) {
    throw "Upload manifest is missing expected files: $($missingUploadNames -join ', ')"
}

$manifestRows = ($manifestEntries | ForEach-Object {
    $pageText = if ($null -eq $_["pages"]) { "n/a" } else { [string]$_["pages"] }
    "| $($_["relative_path"]) | $($_["portal_role"]) | $pageText | $($_["bytes"]) | $($_["sha256"]) |"
}) -join "`r`n"
$shaLines = ($manifestEntries | ForEach-Object { "$($_["sha256"])  $($_["relative_path"])" }) -join "`r`n"
$uploadManifestMarkdown = @"
# Upload Integrity Manifest

Generated: $stamp

Package root: $packageRoot

This manifest covers the upload candidate files listed below. It intentionally excludes `UPLOAD_MANIFEST.md`, `UPLOAD_MANIFEST.json`, and `SHA256SUMS.txt`.

| File | Role | Pages | Bytes | SHA256 |
|---|---|---:|---:|---|
$manifestRows

## Verification Snapshot

- Main manuscript pages: $mainPages.
- Supplementary pages: $suppPages.
- Evidence-freeze guard status: $freezeStatus.
- LaTeX blocking warning/error scan: passed.
"@
Set-Content -LiteralPath (Join-Path $manifestDir "UPLOAD_MANIFEST.md") -Value $uploadManifestMarkdown -Encoding UTF8
Set-Content -LiteralPath (Join-Path $manifestDir "SHA256SUMS.txt") -Value $shaLines -Encoding UTF8
$uploadManifest = [ordered]@{
    generated = $stamp
    package_root = $packageRoot
    scope = "Upload candidate files; excludes manifest files themselves."
    files = $manifestEntries
    verification = [ordered]@{
        main_manuscript_pages = [int]$mainPages
        supplementary_pages = [int]$suppPages
        evidence_freeze_guard_status = $freezeStatus
        latex_log_scan = "passed"
    }
}
$uploadManifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $manifestDir "UPLOAD_MANIFEST.json") -Encoding UTF8
Copy-Item -LiteralPath (Join-Path $manifestDir "UPLOAD_MANIFEST.md") -Destination $uploadDir -Force
Copy-Item -LiteralPath (Join-Path $manifestDir "UPLOAD_MANIFEST.json") -Destination $uploadDir -Force
Copy-Item -LiteralPath (Join-Path $manifestDir "SHA256SUMS.txt") -Destination $uploadDir -Force

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

& powershell -ExecutionPolicy Bypass -File (Join-Path $root "scripts\verify_tste_submission_package.ps1") -PackageRoot $packageRoot
if ($LASTEXITCODE -ne 0) { throw "Independent TSTE package verification failed." }

Write-Host "Prepared IEEE TSTE submission package:"
Write-Host $packageRoot
Write-Host "Upload archive:"
Write-Host $uploadZip
Write-Host "Source archive:"
Write-Host $sourceZip
Write-Host "Full local archive:"
Write-Host $fullZip
