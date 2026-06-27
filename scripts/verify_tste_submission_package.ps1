param(
    [string]$PackageRoot
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($PackageRoot)) {
    $repoRoot = Split-Path -Parent $PSScriptRoot
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

    $match = (& pdfinfo $Path | Select-String "^Pages:\s+(\d+)").Matches[0]
    if ($null -eq $match) {
        throw "Could not read PDF page count: $Path"
    }
    return [int]$match.Groups[1].Value
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
    @{ Path = (Join-Path $evidenceDir "evidence_freeze_guard.json"); Label = "evidence freeze guard JSON" }
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

$coverText = Get-Content -LiteralPath (Join-Path $uploadDir "cover_letter.md") -Raw
if ($coverText.Contains("[Author Names]")) {
    throw "Upload cover letter still contains the [Author Names] placeholder."
}
if (-not $coverText.Contains("Supplementary Table A10")) {
    throw "Upload cover letter does not mention Supplementary Table A10."
}

$portalMetadata = Get-Content -LiteralPath (Join-Path $metadataDir "portal_metadata.json") -Raw | ConvertFrom-Json
if ([string]$portalMetadata.title -ne "SCADA-Anchored Regime-Aware Routing for Auditable Wind-Turbine Control-Boundary Forecasting") {
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
if ($suppPages -ne 3) {
    throw "Supplementary material page count changed: $suppPages"
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$uploadZip = Join-Path $PackageRoot "TSTE_UPLOAD_FILES.zip"
$sourceZip = Join-Path $PackageRoot "TSTE_SOURCE_FILES.zip"
$fullZip = Join-Path $PackageRoot "TSTE_FULL_LOCAL_PACKAGE.zip"
$uploadZipEntries = @([System.IO.Compression.ZipFile]::OpenRead($uploadZip).Entries | ForEach-Object { Convert-ZipPath $_.FullName })
$sourceZipEntries = @([System.IO.Compression.ZipFile]::OpenRead($sourceZip).Entries | ForEach-Object { Convert-ZipPath $_.FullName })
$fullZipEntries = @([System.IO.Compression.ZipFile]::OpenRead($fullZip).Entries | ForEach-Object { Convert-ZipPath $_.FullName })

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
foreach ($name in @(
    "upload_files/manuscript_ieee_tste.pdf",
    "portal_metadata/portal_metadata.json",
    "integrity_manifest/UPLOAD_MANIFEST.json",
    "evidence_audits/evidence_freeze_guard.json"
)) {
    if ($fullZipEntries -notcontains $name) {
        throw "Full local archive is missing $name."
    }
}

Write-Host "TSTE submission package verification passed:"
Write-Host $PackageRoot
Write-Host "Main pages: $mainPages"
Write-Host "Supplementary pages: $suppPages"
Write-Host "Manifest entries checked: $(@($manifest.files).Count)"
