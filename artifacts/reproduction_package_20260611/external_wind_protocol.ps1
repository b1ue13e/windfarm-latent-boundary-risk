param(
    [switch]$DownloadScada,
    [switch]$RunTraining,
    [switch]$RunAllTrainingCommands,
    [switch]$ParallelTraining,
    [int]$MaxParallel = 2,
    [string]$DeviceIds = '0'
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot

# Delegated script reuses validated source manifests/guards/caches and refreshes external-wind-source-guard when needed.
$args = @('-ExecutionPolicy', 'Bypass', '-File', 'scripts\run_external_wind_full_evidence.ps1')
if ($DownloadScada) { $args += '-DownloadScada' }
if ($RunTraining) { $args += '-RunTraining' }
if ($RunAllTrainingCommands) { $args += '-RunAllTrainingCommands' }
if ($ParallelTraining) { $args += '-ParallelTraining' }
$args += @('-MaxParallel', [string]$MaxParallel, '-DeviceIds', $DeviceIds)
powershell @args
