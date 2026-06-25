$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RunRoot = Join-Path $ProjectRoot "artifacts\paper_runs\wtb_full_revision_20260314"
$LogDir = Join-Path $RunRoot "logs"
$MainRoot = Join-Path $RunRoot "main"
$AblationRoot = Join-Path $RunRoot "ablation"
$SensitivityRoot = Join-Path $RunRoot "sensitivity"
$ProgressFile = Join-Path $RunRoot "progress.log"
$ManifestPath = Join-Path $RunRoot "manifest.json"

New-Item -ItemType Directory -Force -Path $RunRoot | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
New-Item -ItemType Directory -Force -Path $MainRoot | Out-Null
New-Item -ItemType Directory -Force -Path $AblationRoot | Out-Null
New-Item -ItemType Directory -Force -Path $SensitivityRoot | Out-Null

$Manifest = [ordered]@{
    started_at = (Get-Date).ToString("s")
    project_root = $ProjectRoot
    run_root = $RunRoot
    groups = @(
        @{
            name = "main"
            output_dir = $MainRoot
            seeds = @("101", "102", "103", "104", "105")
            variants = @(
                "Capacity-Matched Dense Diffusion-GRU",
                "Unconstrained MoE",
                "Physics-Aligned MoE"
            )
        },
        @{
            name = "ablation"
            output_dir = $AblationRoot
            seeds = @("201", "202", "203")
            variants = @(
                "Capacity-Matched Dense Diffusion-GRU",
                "Unconstrained MoE",
                "MoE + L_bal",
                "MoE + L_bal + L_align",
                "MoE + L_bal + L_align + L_force",
                "Physics-Aligned MoE"
            )
        },
        @{
            name = "sensitivity"
            output_dir = $SensitivityRoot
            seeds = @("301", "302", "303")
            settings = @(
                "lambda_bal: 500, 1000, 1500",
                "lambda_align: 2500, 5000, 7500",
                "physics_force_weight: 5000, 10000, 15000",
                "rated_wind: 10.0, 10.5, 11.0",
                "pitch_threshold: 1.5, 2.0, 2.5",
                "num_experts: 3, 4, 5"
            )
        }
    )
}
$Manifest | ConvertTo-Json -Depth 6 | Set-Content -Path $ManifestPath -Encoding UTF8

function Write-ProgressLine {
    param(
        [string]$Message
    )
    $timestamped = "[{0}] {1}" -f (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"), $Message
    $timestamped | Tee-Object -FilePath $ProgressFile -Append
}

function Invoke-Step {
    param(
        [string]$Name,
        [string[]]$Arguments
    )
    $logPath = Join-Path $LogDir "$Name.log"
    Write-ProgressLine "START $Name"
    & python @Arguments *>> $logPath
    if ($LASTEXITCODE -ne 0) {
        Write-ProgressLine "FAIL $Name (exit=$LASTEXITCODE)"
        throw "Step $Name failed with exit code $LASTEXITCODE"
    }
    New-Item -ItemType File -Force -Path (Join-Path $RunRoot "$Name.done") | Out-Null
    Write-ProgressLine "DONE $Name"
}

try {
    Invoke-Step -Name "preprocess" -Arguments @(
        (Join-Path $ProjectRoot "main.py"),
        "preprocess",
        "--dataset", "wtb",
        "--root-dir", $ProjectRoot
    )

    Invoke-Step -Name "main_5seed" -Arguments @(
        (Join-Path $ProjectRoot "main.py"),
        "paper-batch",
        "--dataset", "wtb",
        "--root-dir", $ProjectRoot,
        "--output-dir", $MainRoot,
        "--groups", "main",
        "--seeds", "101,102,103,104,105",
        "--skip-visuals"
    )

    Invoke-Step -Name "ablation_3seed" -Arguments @(
        (Join-Path $ProjectRoot "main.py"),
        "paper-batch",
        "--dataset", "wtb",
        "--root-dir", $ProjectRoot,
        "--output-dir", $AblationRoot,
        "--groups", "ablation",
        "--seeds", "201,202,203",
        "--ablation-seeds", "201,202,203",
        "--skip-visuals"
    )

    Invoke-Step -Name "sensitivity_3seed" -Arguments @(
        (Join-Path $ProjectRoot "main.py"),
        "paper-batch",
        "--dataset", "wtb",
        "--root-dir", $ProjectRoot,
        "--output-dir", $SensitivityRoot,
        "--groups", "sensitivity",
        "--seeds", "301,302,303",
        "--sensitivity-seeds", "301,302,303",
        "--skip-visuals"
    )

    Write-ProgressLine "ALL_STEPS_COMPLETED"
}
catch {
    Write-ProgressLine ("ERROR: " + $_.Exception.Message)
    throw
}
