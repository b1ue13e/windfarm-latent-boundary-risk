param(
    [string]$RootDir = ".",
    [string]$SourceDir = "data/external_wind",
    [string]$CacheRoot = "artifacts/cache_external_wind",
    [string]$SuiteDir = "artifacts/external_wind_runs",
    [string]$Seeds = "201,202,203,204,205",
    [switch]$DownloadScada,
    [switch]$RunTraining
)

$ErrorActionPreference = "Stop"

$StaticManifestCsv = "artifacts/external_wind_static_mapping_manifest/external_wind_source_manifest.csv"
$FullManifestCsv = "artifacts/external_wind_full_manifest/external_wind_source_manifest.csv"
$SourceGuardJson = "artifacts/external_wind_source_guard/external_wind_source_guard.json"
$InspectionJson = "artifacts/external_wind_inspection/external_wind_scada_inspection.json"
$ExternalCacheDirs = @(
  "$CacheRoot/external_wind_kelmarsh_chronological",
  "$CacheRoot/external_wind_penmanshiel_chronological",
  "$CacheRoot/external_wind_kelmarsh_to_penmanshiel_leave_one_farm_out",
  "$CacheRoot/external_wind_penmanshiel_to_kelmarsh_leave_one_farm_out"
)
$RequiredCacheFiles = @(
  "metadata.json",
  "features.npy",
  "physics.npy",
  "regime_primary.npy",
  "regime_primary_valid.npy",
  "regime_valid.npy",
  "anchor_index.npy",
  "node_ids.npy"
)

function Test-ExternalWindCacheComplete {
  param([string]$CacheDir)
  foreach ($Name in $RequiredCacheFiles) {
    if (-not (Test-Path (Join-Path $CacheDir $Name))) { return $false }
  }
  try {
    $Metadata = Get-Content (Join-Path $CacheDir "metadata.json") -Raw | ConvertFrom-Json
  } catch {
    return $false
  }
  return [string]$Metadata.dataset -eq "external_wind"
}

function Test-ExternalWindSourceGuardComplete {
  if (-not (Test-Path $SourceGuardJson)) { return $false }
  try {
    $Guard = Get-Content $SourceGuardJson -Raw | ConvertFrom-Json
  } catch {
    return $false
  }
  return [string]$Guard.status -eq "complete_external_source_evidence" -and [string]$Guard.claim_gate -ne "blocked_not_citable"
}

function Invoke-ExternalWindPreprocessIfNeeded {
  param(
    [string]$CacheDir,
    [string]$Farm,
    [string]$Split,
    [string]$TargetFarm = ""
  )
  if (Test-ExternalWindCacheComplete -CacheDir $CacheDir) {
    Write-Host "Using existing external wind cache: $CacheDir"
    return
  }
  $PreprocessArgs = @(
    "main.py", "external-wind-preprocess",
    "--dataset", "external_wind",
    "--root-dir", $RootDir,
    "--external-source-dir", $SourceDir,
    "--cache-root", $CacheRoot,
    "--farm", $Farm
  )
  if ($TargetFarm) { $PreprocessArgs += @("--external-target-farm", $TargetFarm) }
  $PreprocessArgs += @("--external-split", $Split)
  python @PreprocessArgs
}

if ($DownloadScada -or -not (Test-Path $StaticManifestCsv)) {
  $StaticFetchArgs = @(
    "main.py", "external-wind-fetch",
    "--dataset", "external_wind",
    "--root-dir", $RootDir,
    "--external-source-dir", $SourceDir,
    "--output-dir", "artifacts/external_wind_static_mapping_manifest",
    "--farms", "kelmarsh,penmanshiel",
    "--no-scada",
    "--include-mapping"
  )
  if ($DownloadScada) { $StaticFetchArgs += "--download" }
  python @StaticFetchArgs
} else {
  Write-Host "Using existing external wind static/mapping manifest: $StaticManifestCsv"
}

if ($DownloadScada -or -not (Test-Path $FullManifestCsv)) {
  $FullFetchArgs = @(
    "main.py", "external-wind-fetch",
    "--dataset", "external_wind",
    "--root-dir", $RootDir,
    "--external-source-dir", $SourceDir,
    "--output-dir", "artifacts/external_wind_full_manifest",
    "--farms", "kelmarsh,penmanshiel"
  )
  if ($DownloadScada) { $FullFetchArgs += "--download" }
  python @FullFetchArgs
} else {
  Write-Host "Using existing external wind full source manifest: $FullManifestCsv"
}

if ($DownloadScada -or -not (Test-ExternalWindSourceGuardComplete)) {
  python main.py external-wind-source-guard `
    --dataset external_wind `
    --root-dir $RootDir `
    --output-dir artifacts/external_wind_source_guard `
    --manifest-path artifacts/external_wind_full_manifest/external_wind_source_manifest.csv `
    --farms kelmarsh,penmanshiel `
    --min-files 31 `
    --min-total-bytes 10000000000
} else {
  Write-Host "Using existing external wind source guard: $SourceGuardJson"
}

if ($DownloadScada -or -not (Test-Path $InspectionJson)) {
  python main.py external-wind-inspect `
    --dataset external_wind `
    --root-dir $RootDir `
    --external-source-dir $SourceDir `
    --output-dir artifacts/external_wind_inspection `
    --farms kelmarsh,penmanshiel `
    --max-members-per-zip 3
} else {
  Write-Host "Using existing external wind inspection: $InspectionJson"
}

Invoke-ExternalWindPreprocessIfNeeded `
  -CacheDir $ExternalCacheDirs[0] `
  -Farm kelmarsh `
  -Split chronological

Invoke-ExternalWindPreprocessIfNeeded `
  -CacheDir $ExternalCacheDirs[1] `
  -Farm penmanshiel `
  -Split chronological

Invoke-ExternalWindPreprocessIfNeeded `
  -CacheDir $ExternalCacheDirs[2] `
  -Farm kelmarsh `
  -TargetFarm penmanshiel `
  -Split leave-one-farm-out

Invoke-ExternalWindPreprocessIfNeeded `
  -CacheDir $ExternalCacheDirs[3] `
  -Farm penmanshiel `
  -TargetFarm kelmarsh `
  -Split leave-one-farm-out

python main.py external-wind-protocol `
  --dataset external_wind `
  --root-dir $RootDir `
  --external-source-dir $SourceDir `
  --cache-root $CacheRoot `
  --output-dir artifacts/external_wind_protocol `
  --suite-dir $SuiteDir `
  --seeds $Seeds `
  --farms kelmarsh,penmanshiel

if ($RunTraining) {
  $TrainingCommands = "artifacts/external_wind_protocol/external_wind_training_commands.ps1"
  Get-Content artifacts/external_wind_protocol/external_wind_commands.ps1 |
    Where-Object { $_ -notmatch "external-wind-preprocess" -and $_.Trim() } |
    Set-Content -Encoding UTF8 $TrainingCommands
  powershell -ExecutionPolicy Bypass -File $TrainingCommands
  powershell -ExecutionPolicy Bypass -File artifacts/external_wind_protocol/external_wind_reviewer_pack_commands.ps1
}

$CacheDirs = $ExternalCacheDirs -join ","

python main.py external-wind-guard `
  --dataset external_wind `
  --root-dir $RootDir `
  --output-dir artifacts/external_wind_guard `
  --cache-dirs $CacheDirs `
  --suite-dir $SuiteDir `
  --seeds $Seeds
