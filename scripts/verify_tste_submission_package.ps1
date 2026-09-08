param(
    [string]$PackageRoot
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

if ([string]::IsNullOrWhiteSpace($PackageRoot)) {
    $latestPath = Join-Path $repoRoot "artifacts\tste_submission\LATEST_PACKAGE.txt"
    if (-not (Test-Path $latestPath)) {
        throw "PackageRoot was not provided and LATEST_PACKAGE.txt does not exist."
    }
    $PackageRoot = (Get-Content -LiteralPath $latestPath -Raw).Trim()
}

$PackageRoot = [System.IO.Path]::GetFullPath($PackageRoot)
if (-not (Test-Path $PackageRoot)) {
    throw "Package root does not exist: $PackageRoot"
}

function Test-RequiredPath {
    param(
        [string]$Path,
        [string]$Label
    )
    if (-not (Test-Path $Path)) {
        throw "Missing $Label`: $Path"
    }
}

function Get-PdfPages {
    param([string]$Path)

    $pageText = & python -c "from pathlib import Path; from pypdf import PdfReader; print(len(PdfReader(str(Path(r'$Path'))).pages))"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not read PDF page count: $Path"
    }
    $pageText = [string]$pageText
    return [int]$pageText.Trim()
}

function Convert-ZipPath {
    param([string]$Path)

    return (($Path -replace "\\", "/") -replace "^\./", "")
}

$uploadDir = Join-Path $PackageRoot "upload_files"
$sourceDir = Join-Path $PackageRoot "source_files"
$evidenceDir = Join-Path $PackageRoot "evidence_audits"
$metadataDir = Join-Path $PackageRoot "portal_metadata"
$manifestDir = Join-Path $PackageRoot "integrity_manifest"

foreach ($required in @(
    @{ Path = $uploadDir; Label = "upload_files directory" },
    @{ Path = $sourceDir; Label = "source_files directory" },
    @{ Path = $evidenceDir; Label = "evidence_audits directory" },
    @{ Path = $metadataDir; Label = "portal_metadata directory" },
    @{ Path = $manifestDir; Label = "integrity_manifest directory" },
    @{ Path = (Join-Path $PackageRoot "README_TSTE_submission.md"); Label = "package README" },
    @{ Path = (Join-Path $PackageRoot "VERIFICATION_REPORT.md"); Label = "verification report" },
    @{ Path = (Join-Path $PackageRoot "TSTE_UPLOAD_FILES.zip"); Label = "upload archive" },
    @{ Path = (Join-Path $PackageRoot "TSTE_SOURCE_FILES.zip"); Label = "source archive" },
    @{ Path = (Join-Path $PackageRoot "TSTE_FULL_LOCAL_PACKAGE.zip"); Label = "full local archive" },
    @{ Path = (Join-Path $manifestDir "UPLOAD_MANIFEST.json"); Label = "upload manifest JSON" },
    @{ Path = (Join-Path $manifestDir "UPLOAD_MANIFEST.md"); Label = "upload manifest Markdown" },
    @{ Path = (Join-Path $manifestDir "SHA256SUMS.txt"); Label = "SHA256 checksum list" },
    @{ Path = (Join-Path $metadataDir "portal_metadata.json"); Label = "portal metadata JSON" },
    @{ Path = (Join-Path $metadataDir "portal_metadata.md"); Label = "portal metadata Markdown" },
    @{ Path = (Join-Path $evidenceDir "evidence_freeze_guard.json"); Label = "evidence freeze guard JSON" },
    @{ Path = (Join-Path $evidenceDir "tste_number_consistency_audit.json"); Label = "TSTE number consistency audit JSON" }
)) {
    Test-RequiredPath -Path $required.Path -Label $required.Label
}

$manifest = Get-Content -LiteralPath (Join-Path $manifestDir "UPLOAD_MANIFEST.json") -Raw | ConvertFrom-Json
$freeze = Get-Content -LiteralPath (Join-Path $evidenceDir "evidence_freeze_guard.json") -Raw | ConvertFrom-Json
if ([string]$freeze.status -ne "complete_ready_for_evidence_freeze") {
    throw "Evidence-freeze guard status is $($freeze.status)."
}
if ([string]$manifest.verification.evidence_freeze_guard_status -ne "complete_ready_for_evidence_freeze") {
    throw "Manifest evidence-freeze status is $($manifest.verification.evidence_freeze_guard_status)."
}
$numberAudit = Get-Content -LiteralPath (Join-Path $evidenceDir "tste_number_consistency_audit.json") -Raw | ConvertFrom-Json
if ([string]$numberAudit.status -ne "complete_tste_number_consistency") {
    throw "TSTE number consistency audit status is $($numberAudit.status)."
}
if ([string]$manifest.verification.number_consistency_audit_status -ne "complete_tste_number_consistency") {
    throw "Manifest number-consistency status is $($manifest.verification.number_consistency_audit_status)."
}

$expectedUploadFiles = @(
    "cover_letter.md",
    "manuscript_ieee_tste.pdf",
    "portal_metadata.json",
    "portal_metadata.md",
    "supplementary_material.pdf",
    "VERIFICATION_REPORT.md",
    "UPLOAD_MANIFEST.md",
    "UPLOAD_MANIFEST.json",
    "SHA256SUMS.txt"
)
foreach ($name in $expectedUploadFiles) {
    Test-RequiredPath -Path (Join-Path $uploadDir $name) -Label "upload file $name"
}

$paperPath = Join-Path $repoRoot "paper_tste_ieee.md"
$expectedTitle = if (Test-Path $paperPath) {
    $match = [regex]::Match((Get-Content -LiteralPath $paperPath -Raw), "\\title\{(.+?)\}", [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if ($match.Success) {
        $t = $match.Groups[1].Value
        $t = $t -replace "\\%", "%" -replace "\\&", "&" -replace "\\_", "_" -replace "\\texttt\{([^}]*)\}", '$1' -replace "---", " - " -replace "~", " " -replace "\s+", " "
        $t.Trim()
    } else {
        "Reliability Breakdown of Wind Turbine Operating Reserve Rules under Stale SCADA Telemetry and Boundary-Risk Posterior Diagnostics"
    }
} else {
    "Reliability Breakdown of Wind Turbine Operating Reserve Rules under Stale SCADA Telemetry and Boundary-Risk Posterior Diagnostics"
}

$coverText = Get-Content -LiteralPath (Join-Path $uploadDir "cover_letter.md") -Raw
if ($coverText.Contains("[Author Names]")) {
    throw "Upload cover letter still contains the [Author Names] placeholder."
}
if (-not $coverText.Contains("Supplementary Table A12")) {
    throw "Upload cover letter does not mention Supplementary Table A12."
}
if (-not $coverText.Contains($expectedTitle)) {
    throw "Upload cover letter does not contain the expected manuscript title: $expectedTitle"
}
if (-not $coverText.Contains("-11.22M kWh") -or (-not $coverText.Contains("+0.021") -and -not $coverText.Contains("+0.064")) -or -not $coverText.Contains("17.6 cumulative machine-operating years")) {
    throw "Upload cover letter is missing key empirical pillar benchmarks."
}

$portalMetadata = Get-Content -LiteralPath (Join-Path $metadataDir "portal_metadata.json") -Raw | ConvertFrom-Json
if ([string]$portalMetadata.title -ne $expectedTitle) {
    throw "Portal metadata title does not match the TSTE manuscript."
}
if (@($portalMetadata.keywords).Count -lt 5) {
    throw "Portal metadata keyword list is unexpectedly short."
}

$shaLines = @(Get-Content -LiteralPath (Join-Path $manifestDir "SHA256SUMS.txt") | Where-Object { $_.Trim() })
$shaByPath = @{}
foreach ($line in $shaLines) {
    $parts = $line -split "\s+", 2
    if ($parts.Count -ne 2) {
        throw "Malformed SHA256SUMS line: $line"
    }
    $shaByPath[$parts[1]] = $parts[0]
}

foreach ($entry in @($manifest.files)) {
    $relativePath = [string]$entry.relative_path
    $path = Join-Path $PackageRoot $relativePath
    Test-RequiredPath -Path $path -Label "manifest file $relativePath"

    $actualBytes = (Get-Item -LiteralPath $path).Length
    if ([int64]$entry.bytes -ne [int64]$actualBytes) {
        throw "Byte size mismatch for $relativePath`: manifest=$($entry.bytes), actual=$actualBytes"
    }

    $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
    if ([string]$entry.sha256 -ne $actualHash) {
        throw "SHA256 mismatch for $relativePath."
    }
    if (-not $shaByPath.ContainsKey($relativePath)) {
        throw "SHA256SUMS.txt is missing $relativePath."
    }
    if ($shaByPath[$relativePath] -ne $actualHash) {
        throw "SHA256SUMS.txt hash mismatch for $relativePath."
    }

    if ($relativePath.EndsWith(".pdf")) {
        $actualPages = Get-PdfPages -Path $path
        if ([int]$entry.pages -ne $actualPages) {
            throw "PDF page-count mismatch for $relativePath`: manifest=$($entry.pages), actual=$actualPages"
        }
    }
}

$mainPages = Get-PdfPages -Path (Join-Path $uploadDir "manuscript_ieee_tste.pdf")
$suppPages = Get-PdfPages -Path (Join-Path $uploadDir "supplementary_material.pdf")
if ($mainPages -gt 10) {
    throw "Main manuscript exceeds 10 pages: $mainPages"
}
if ($suppPages -lt 3 -or $suppPages -gt 15) {
    throw "Supplementary material page count is outside the expected 3-15 page range: $suppPages"
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$uploadZip = Join-Path $PackageRoot "TSTE_UPLOAD_FILES.zip"
$sourceZip = Join-Path $PackageRoot "TSTE_SOURCE_FILES.zip"
$fullZip = Join-Path $PackageRoot "TSTE_FULL_LOCAL_PACKAGE.zip"
$uploadZipEntries = @([System.IO.Compression.ZipFile]::OpenRead($uploadZip).Entries | ForEach-Object { Convert-ZipPath $_.FullName })
$sourceZipEntries = @([System.IO.Compression.ZipFile]::OpenRead($sourceZip).Entries | ForEach-Object { Convert-ZipPath $_.FullName })
$fullZipEntries = @([System.IO.Compression.ZipFile]::OpenRead($fullZip).Entries | ForEach-Object { Convert-ZipPath $_.FullName })

$cacheEntries = @($sourceZipEntries + $fullZipEntries | Where-Object {
    $_ -match "(^|/)__pycache__/" -or $_ -match "\.py[co]$"
})
if ($cacheEntries.Count -gt 0) {
    throw "Submission archives contain Python bytecode/cache files: $($cacheEntries[0])"
}

foreach ($name in $expectedUploadFiles) {
    if ($uploadZipEntries -notcontains $name) {
        throw "Upload archive is missing $name."
    }
}
if ($sourceZipEntries -notcontains "scripts/prepare_tste_submission.ps1") {
    throw "Source archive is missing scripts/prepare_tste_submission.ps1."
}
if ($sourceZipEntries -notcontains "scripts/verify_tste_submission_package.ps1") {
    throw "Source archive is missing scripts/verify_tste_submission_package.ps1."
}
if ($sourceZipEntries -notcontains "scripts/build_engineering_unit_value_translation.py") {
    throw "Source archive is missing scripts/build_engineering_unit_value_translation.py."
}
if ($sourceZipEntries -notcontains "scripts/build_early_warning_classifier_baseline.py") {
    throw "Source archive is missing scripts/build_early_warning_classifier_baseline.py."
}
if ($sourceZipEntries -notcontains "scripts/audit_class_weight_boundary.py") {
    throw "Source archive is missing scripts/audit_class_weight_boundary.py."
}
if ($sourceZipEntries -notcontains "scripts/build_train_weight_cache.py") {
    throw "Source archive is missing scripts/build_train_weight_cache.py."
}
if ($sourceZipEntries -notcontains "scripts/build_class_weight_sensitivity_audit.py") {
    throw "Source archive is missing scripts/build_class_weight_sensitivity_audit.py."
}
if ($sourceZipEntries -notcontains "scripts/verify_tste_number_consistency.py") {
    throw "Source archive is missing scripts/verify_tste_number_consistency.py."
}
if ($sourceZipEntries -notcontains "scripts/eval_farm_aggregate_reserve.py") {
    throw "Source archive is missing scripts/eval_farm_aggregate_reserve.py."
}
if ($sourceZipEntries -notcontains "scripts/eval_markov_gilbert_telemetry.py") {
    throw "Source archive is missing scripts/eval_markov_gilbert_telemetry.py."
}
if ($sourceZipEntries -notcontains "scripts/aggregate_iec_density_eval.py") {
    throw "Source archive is missing scripts/aggregate_iec_density_eval.py."
}
if ($sourceZipEntries -notcontains "tests/test_farm_aggregate_and_markov.py") {
    throw "Source archive is missing tests/test_farm_aggregate_and_markov.py."
}
foreach ($name in @(
    "windfarm_moe/data.py",
    "windfarm_moe/preprocess.py",
    "windfarm_moe/train.py",
    "windfarm_moe/anchor_stress.py",
    "windfarm_moe/regimes.py"
)) {
    if ($sourceZipEntries -notcontains $name) {
        throw "Source archive is missing core module $name."
    }
}
foreach ($name in @(
    "upload_files/manuscript_ieee_tste.pdf",
    "portal_metadata/portal_metadata.json",
    "integrity_manifest/UPLOAD_MANIFEST.json",
    "evidence_audits/evidence_freeze_guard.json",
    "evidence_audits/artifacts/early_warning_classifier_baseline_wtb/early_warning_classifier_baseline_summary.csv",
    "evidence_audits/artifacts/early_warning_classifier_baseline_wtb/early_warning_classifier_baseline_raw.csv",
    "evidence_audits/artifacts/early_warning_classifier_baseline_wtb/early_warning_classifier_baseline_guard.json",
    "evidence_audits/artifacts/class_weight_boundary_audit/class_weight_boundary_audit.csv",
    "evidence_audits/artifacts/class_weight_boundary_audit/class_weight_boundary_audit.json",
    "evidence_audits/artifacts/class_weight_boundary_audit/class_weight_sensitivity_audit.csv",
    "evidence_audits/artifacts/class_weight_boundary_audit/class_weight_sensitivity_audit.json",
    "evidence_audits/artifacts/class_weight_boundary_audit/table_class_weight_sensitivity_audit.tex",
    "evidence_audits/artifacts/trainweight_class_weight_rerun_20260702/suite_summary.json",
    "evidence_audits/engineering_unit_value_translation.csv",
    "evidence_audits/tste_number_consistency_audit.csv"
)) {
    if ($fullZipEntries -notcontains $name) {
        throw "Full local archive is missing $name."
    }
}
foreach ($seed in 201, 202, 203, 204, 205) {
    foreach ($name in @(
        "evidence_audits/artifacts/trainweight_class_weight_rerun_20260702/wtb_bal_align_force_seed$seed/training_summary.json",
        "evidence_audits/artifacts/trainweight_class_weight_rerun_20260702/wtb_bal_align_force_seed$seed/test_metrics/metrics.json"
    )) {
        if ($fullZipEntries -notcontains $name) {
            throw "Full local archive is missing $name."
        }
    }
}

Write-Host "TSTE submission package verification passed:"
Write-Host $PackageRoot
Write-Host "Main pages: $mainPages"
Write-Host "Supplementary pages: $suppPages"
Write-Host "Manifest entries checked: $(@($manifest.files).Count)"
