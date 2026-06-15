param(
    [string]$RootDir = ".",
    [string]$SourceDir = "data/external_wind",
    [string]$CacheRoot = "artifacts/cache_external_wind",
    [string]$SuiteDir = "artifacts/external_wind_runs",
    [string]$Seeds = "201,202,203,204,205",
    [switch]$DownloadScada,
    [switch]$RunTraining,
    [switch]$RunAllTrainingCommands,
    [switch]$ParallelTraining,
    [int]$MaxParallel = 2,
    [string]$DeviceIds = "0,0"
)

$ErrorActionPreference = "Stop"

$StaticManifestCsv = "artifacts/external_wind_static_mapping_manifest/external_wind_source_manifest.csv"
$FullManifestCsv = "artifacts/external_wind_full_manifest/external_wind_source_manifest.csv"
$SourceGuardJson = "artifacts/external_wind_source_guard/external_wind_source_guard.json"
$InspectionJson = "artifacts/external_wind_inspection/external_wind_scada_inspection.json"
$ExternalGuardJson = "artifacts/external_wind_guard/external_wind_guard.json"
$ExternalRunStatusCsv = "artifacts/external_wind_guard/external_wind_run_status.csv"
$TrainingCommands = "artifacts/external_wind_protocol/external_wind_training_commands.ps1"
$MissingTrainingCommands = "artifacts/external_wind_protocol/external_wind_missing_training_commands.ps1"
$MissingRunStatusCsv = "artifacts/external_wind_protocol/external_wind_missing_run_status.csv"
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

function Invoke-ExternalWindGuardRefresh {
  $CacheDirs = $ExternalCacheDirs -join ","
  python main.py external-wind-guard `
    --dataset external_wind `
    --root-dir $RootDir `
    --output-dir artifacts/external_wind_guard `
    --cache-dirs $CacheDirs `
    --suite-dir $SuiteDir `
    --seeds $Seeds
}

function Get-ExternalWindGroupForModel {
  param([string]$Model)
  switch ($Model) {
    "Graph WaveNet" { return "strong_baselines" }
    "PatchTST" { return "strong_baselines" }
    "Physics-Aligned MoE" { return "main" }
    "MoE + L_bal + L_align + L_force" { return "ablation" }
    default { return "" }
  }
}

function Test-ExternalWindCommandMatchesKey {
  param(
    [string]$Command,
    [string]$Farm,
    [string]$TargetFarm,
    [string]$SplitId,
    [string]$Group
  )
  if ($Command -notmatch "paper-batch") { return $false }
  if ($Command -notmatch "--groups\s+$([regex]::Escape($Group))(\s|$)") { return $false }
  if ($Command -notmatch "--farm\s+$([regex]::Escape($Farm))(\s|$)") { return $false }
  if ($Command -notmatch "--external-split\s+$([regex]::Escape($SplitId))(\s|$)") { return $false }
  if ($TargetFarm) {
    return $Command -match "--external-target-farm\s+$([regex]::Escape($TargetFarm))(\s|$)"
  }
  return $Command -notmatch "--external-target-farm\s+"
}

function New-ExternalWindMissingTrainingCommands {
  param(
    [string]$CommandsPath,
    [string]$OutputPath,
    [string]$MissingCsvPath
  )
  if (-not (Test-Path $CommandsPath)) {
    throw "External wind protocol command file is missing: $CommandsPath"
  }
  if (-not (Test-Path $ExternalRunStatusCsv)) {
    throw "External wind run status is missing: $ExternalRunStatusCsv"
  }

  $rows = Import-Csv $ExternalRunStatusCsv
  $missingRows = @($rows | Where-Object { [string]$_.complete -ne "True" })
  $missingRows | Export-Csv -NoTypeInformation -Encoding UTF8 $MissingCsvPath

  $missingKeys = @{}
  foreach ($row in $missingRows) {
    $group = Get-ExternalWindGroupForModel -Model ([string]$row.model)
    if (-not $group) { continue }
    $key = "{0}|{1}|{2}|{3}" -f $row.farm, $row.target_farm, $row.split_id, $group
    $missingKeys[$key] = @{
      Farm = [string]$row.farm
      TargetFarm = [string]$row.target_farm
      SplitId = [string]$row.split_id
      Group = $group
    }
  }

  $trainingLines = Get-Content $CommandsPath |
    Where-Object { $_ -notmatch "external-wind-preprocess" -and $_.Trim() }
  $selected = New-Object System.Collections.Generic.List[string]
  foreach ($line in $trainingLines) {
    foreach ($entry in $missingKeys.Values) {
      if (Test-ExternalWindCommandMatchesKey `
          -Command $line `
          -Farm $entry.Farm `
          -TargetFarm $entry.TargetFarm `
          -SplitId $entry.SplitId `
          -Group $entry.Group) {
        if (-not $selected.Contains($line)) { $selected.Add($line) }
      }
    }
  }

  $outputLines = New-Object System.Collections.Generic.List[string]
  $outputLines.Add('$ErrorActionPreference = "Stop"')
  $outputLines.Add("")
  $outputLines.Add("# Auto-generated by scripts/run_external_wind_full_evidence.ps1.")
  $outputLines.Add("# Runs only split/model groups with at least one currently missing external wind run.")
  $outputLines.Add("# paper-batch resume/lock handling skips already complete seeds inside each selected group.")
  $outputLines.Add("")
  if ($selected.Count -eq 0) {
    $outputLines.Add('Write-Host "External wind 80-run protocol already has no missing training commands."')
  } else {
    foreach ($line in $selected) { $outputLines.Add($line) }
  }
  $outputLines | Set-Content -Encoding UTF8 $OutputPath

  Write-Host "External wind missing runs: $($missingRows.Count) / $($rows.Count)"
  Write-Host "Missing-only training commands: $($selected.Count) -> $OutputPath"
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

Invoke-ExternalWindGuardRefresh
New-ExternalWindMissingTrainingCommands `
  -CommandsPath "artifacts/external_wind_protocol/external_wind_commands.ps1" `
  -OutputPath $MissingTrainingCommands `
  -MissingCsvPath $MissingRunStatusCsv

if ($RunTraining) {
  $SelectedTrainingCommands = $MissingTrainingCommands
  if ($RunAllTrainingCommands) {
    $SelectedTrainingCommands = $TrainingCommands
    $TrainingSource = "artifacts/external_wind_protocol/external_wind_commands.ps1"
  } else {
    $TrainingSource = $MissingTrainingCommands
  }
  $TrainingLines = Get-Content $TrainingSource |
    Where-Object { $_ -notmatch "external-wind-preprocess" -and $_.Trim() -and $_ -notmatch "^\s*#" -and $_ -notmatch "^\s*Write-Host" -and $_ -notmatch "ErrorActionPreference" } |
    ForEach-Object {
      if ($ParallelTraining -and $_ -match "paper-batch" -and $_ -notmatch "--parallel") {
        "$_ --parallel --max-parallel $MaxParallel --device-ids $DeviceIds"
      } else {
        $_
      }
    }
  $TrainingLines | Set-Content -Encoding UTF8 $SelectedTrainingCommands
  powershell -ExecutionPolicy Bypass -File $SelectedTrainingCommands
  powershell -ExecutionPolicy Bypass -File artifacts/external_wind_protocol/external_wind_reviewer_pack_commands.ps1
}

Invoke-ExternalWindGuardRefresh
