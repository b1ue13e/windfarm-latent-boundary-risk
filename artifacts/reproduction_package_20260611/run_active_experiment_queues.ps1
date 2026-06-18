$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot

function Test-ProcessPattern {
    param([string]$Pattern)
    $running = Get-CimInstance Win32_Process | Where-Object {
        $commandLine = $_.CommandLine -replace [char]34, ""
        $commandLine -notlike "* -Command *" -and $commandLine -like "*$Pattern*"
    }
    return [bool]$running
}

function Test-QueueScript {
    param([string]$Path)
    $normalized = $Path -replace "/", "\"
    $running = Get-CimInstance Win32_Process -Filter "name = 'powershell.exe'" | Where-Object {
        $commandLine = $_.CommandLine -replace [char]34, ""
        $commandLine -notlike "* -Command *" -and $commandLine -like "*-File $normalized*"
    }
    return [bool]$running
}

if (-not (Test-ProcessPattern "strictmask_baseline_rerun_wtb_full")) {
    Write-Host "Starting/resuming strict strong-baseline paper-batch."
    Start-Process -FilePath "python" -ArgumentList @("main.py", "paper-batch", "--dataset", "wtb", "--root-dir", ".", "--cache-root", "artifacts/cache_strictmask", "--train-days", "180", "--val-days", "30", "--test-days", "35", "--hist-len", "36", "--pred-len", "24", "--output-dir", "artifacts/strictmask_baseline_rerun_wtb_full", "--groups", "strong_baselines", "--variant-keys", "graph_transformer,gat_gru,patchtst", "--seeds", "201,202,203,204,205", "--epochs", "20", "--batch-size", "16", "--hidden-dim", "64", "--skip-visuals") -WorkingDirectory $repoRoot -WindowStyle Hidden
} else {
    Write-Host "Strict strong-baseline paper-batch is already running."
}

$queues = @(
    @{ Name = "goal strict completion"; Path = "artifacts\goal_strict_completion_queue_20260612.ps1"; Pattern = "goal_strict_completion_queue_20260612.ps1" },
    @{ Name = "strict follow-up"; Path = "artifacts\strict_followup_queue_20260611.ps1"; Pattern = "strict_followup_queue_20260611.ps1" },
    @{ Name = "strict extension"; Path = "artifacts\strict_extension_queue_20260611.ps1"; Pattern = "strict_extension_queue_20260611.ps1" },
    @{ Name = "future holdout"; Path = "artifacts\future_holdout_queue_20260611.ps1"; Pattern = "future_holdout_queue_20260611.ps1" },
    @{ Name = "post-queue finalization"; Path = "artifacts\strict_postqueue_finalize_20260611.ps1"; Pattern = "strict_postqueue_finalize_20260611.ps1" }
)

foreach ($queue in $queues) {
    if (Test-QueueScript $queue.Path) {
        Write-Host "$($queue.Name) queue is already running."
        continue
    }
    Write-Host "Starting $($queue.Name) queue."
    Start-Process -FilePath "powershell" -ArgumentList @("-ExecutionPolicy", "Bypass", "-File", $queue.Path) -WorkingDirectory $repoRoot -WindowStyle Hidden
}

if (Test-ProcessPattern "main.py paper-batch") {
    Write-Host "Skipping immediate readiness refresh while a paper-batch process is active; post-queue finalization will refresh it."
} else {
    powershell -ExecutionPolicy Bypass -File artifacts\science_readiness_dashboard_20260611\refresh_readiness.ps1
}
