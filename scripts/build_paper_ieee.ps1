$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$localPandoc = Join-Path $root "tools\pandoc-3.9.0.2\pandoc.exe"
$pandoc = if (Test-Path $localPandoc) { $localPandoc } else {
    $c = Get-Command pandoc -ErrorAction SilentlyContinue
    if (-not $c) { throw "Pandoc not found." }
    $c.Source
}
$localMiKTeX = "E:\MiKTeX\miktex\bin\x64\xelatex.exe"
$xelatex = if (Test-Path $localMiKTeX) { $localMiKTeX } elseif (
    Test-Path "C:\texlive\2025\bin\windows\xelatex.exe") {
    "C:\texlive\2025\bin\windows\xelatex.exe"
} else {
    $c = Get-Command xelatex -ErrorAction SilentlyContinue
    if (-not $c) { throw "XeLaTeX not found." }
    $c.Source
}
$env:PATH = (Split-Path -Parent $xelatex) + ";$env:PATH"

$restoreRunTargetsScript = Join-Path $root "scripts\restore_run_targets.py"
if (Test-Path $restoreRunTargetsScript) {
    & python $restoreRunTargetsScript --root-dir $root
    if ($LASTEXITCODE -ne 0) { throw "Run target/mask restore preflight failed." }
}

$tradeoffScript = Join-Path $root "scripts\build_accountability_tradeoff.py"
if (Test-Path $tradeoffScript) {
    & python $tradeoffScript
    if ($LASTEXITCODE -ne 0) { throw "Accountability tradeoff generation failed." }
}

$appliedEnergyScript = Join-Path $root "scripts\build_applied_energy_diagnostics.py"
if (Test-Path $appliedEnergyScript) {
    & python $appliedEnergyScript
    if ($LASTEXITCODE -ne 0) { throw "Applied-energy diagnostic generation failed." }
    $appliedDir = Join-Path $root "artifacts\applied_energy_diagnostics"
    $finalTablesDir = Join-Path $root "artifacts\final_evidence_package\export\tables"
    $finalFiguresDir = Join-Path $root "artifacts\final_evidence_package\export\figures"
    New-Item -ItemType Directory -Force -Path $finalTablesDir, $finalFiguresDir | Out-Null
    foreach ($item in Get-ChildItem -LiteralPath $appliedDir -File | Where-Object { $_.Extension -in @(".csv", ".tex", ".json") }) {
        Copy-Item -LiteralPath $item.FullName -Destination (Join-Path $finalTablesDir $item.Name) -Force
    }
    foreach ($item in Get-ChildItem -LiteralPath $appliedDir -File | Where-Object { $_.Extension -in @(".png", ".pdf", ".svg") }) {
        Copy-Item -LiteralPath $item.FullName -Destination (Join-Path $finalFiguresDir $item.Name) -Force
    }
}

$classWeightAuditScript = Join-Path $root "scripts\audit_class_weight_boundary.py"
$trainWeightCacheScript = Join-Path $root "scripts\build_train_weight_cache.py"
$strictCacheDir = Join-Path $root "artifacts\cache_strictmask\wtb_245d"
$trainWeightCacheDir = Join-Path $root "artifacts\cache_strictmask_trainweights\wtb_245d"
if ((Test-Path $trainWeightCacheScript) -and (Test-Path (Join-Path $strictCacheDir "metadata.json")) -and -not (Test-Path (Join-Path $trainWeightCacheDir "metadata.json"))) {
    & python $trainWeightCacheScript --source-cache $strictCacheDir --target-cache $trainWeightCacheDir
    if ($LASTEXITCODE -ne 0) { throw "Train-weight cache generation failed." }
}
if (Test-Path $classWeightAuditScript) {
    & python $classWeightAuditScript
    if ($LASTEXITCODE -ne 0) { throw "Class-weight boundary audit failed." }
}
$classWeightSensitivityScript = Join-Path $root "scripts\build_class_weight_sensitivity_audit.py"
$classWeightRerunMetric = Join-Path $root "artifacts\trainweight_class_weight_rerun_20260702\wtb_bal_align_force_seed201\test_metrics\metrics.json"
if ((Test-Path $classWeightSensitivityScript) -and (Test-Path $classWeightRerunMetric)) {
    & python $classWeightSensitivityScript
    if ($LASTEXITCODE -ne 0) { throw "Class-weight sensitivity audit failed." }
}

$statisticalClaimScript = Join-Path $root "scripts\build_statistical_claim_table.py"
if (Test-Path $statisticalClaimScript) {
    & python $statisticalClaimScript
    if ($LASTEXITCODE -ne 0) { throw "Statistical claim table generation failed." }
}

$earlyWarningConsequenceScript = Join-Path $root "scripts\build_early_warning_consequence_table.py"
if (Test-Path $earlyWarningConsequenceScript) {
    & python $earlyWarningConsequenceScript
    if ($LASTEXITCODE -ne 0) { throw "Early-warning consequence table generation failed." }
}

$modularClassifierReserveScript = Join-Path $root "scripts\build_modular_classifier_reserve_baseline.py"
if (Test-Path $modularClassifierReserveScript) {
    & python $modularClassifierReserveScript
    if ($LASTEXITCODE -ne 0) { throw "Modular classifier reserve control generation failed." }
}

$reserveClaimBoundaryScript = Join-Path $root "scripts\build_reserve_claim_boundary_table.py"
if (Test-Path $reserveClaimBoundaryScript) {
    & python $reserveClaimBoundaryScript
    if ($LASTEXITCODE -ne 0) { throw "Reserve claim-boundary table generation failed." }
}

$engineeringValueScript = Join-Path $root "scripts\build_engineering_unit_value_translation.py"
if (Test-Path $engineeringValueScript) {
    & python $engineeringValueScript
    if ($LASTEXITCODE -ne 0) { throw "Engineering-unit value translation generation failed." }
}

$outcomeSanityScript = Join-Path $root "scripts\build_outcome_channel_sanity.py"
if (Test-Path $outcomeSanityScript) {
    & python $outcomeSanityScript
    if ($LASTEXITCODE -ne 0) { throw "Outcome-channel sanity generation failed." }
}

$externalGateScript = Join-Path $root "scripts\build_external_deployment_gate_audit.py"
if (Test-Path $externalGateScript) {
    & python $externalGateScript
    if ($LASTEXITCODE -ne 0) { throw "External deployment-gate audit generation failed." }
}

$numberConsistencyScript = Join-Path $root "scripts\verify_tste_number_consistency.py"
if (Test-Path $numberConsistencyScript) {
    & python $numberConsistencyScript --output-dir (Join-Path $root "artifacts\tste_number_consistency_audit")
    if ($LASTEXITCODE -ne 0) { throw "TSTE number consistency audit failed." }
}

# paper_tste_ieee.md and paper_tste_supplementary.md are maintained directly as primary source of truth.
# Legacy one-time transforms (transform_ieee.py, make_supplementary.py) are disarmed to avoid overwriting.


function Build-PDF {
    param($md, $label)
    $tex = Join-Path $root "build\${label}.tex"
    $pdf = Join-Path $root "build\${label}.pdf"
    $buildDir = Join-Path $root "build"
    $fontShim = Join-Path $root "TUptm.fd"
    if (Test-Path $tex) { Remove-Item $tex -Force }
    if (Test-Path $pdf) { Remove-Item $pdf -Force }
    $null = New-Item -ItemType Directory -Force -Path $buildDir
    if (Test-Path $fontShim) {
        Copy-Item -LiteralPath $fontShim -Destination (Join-Path $buildDir "TUptm.fd") -Force
    }
    & $pandoc $md --citeproc --csl (Join-Path $root "IEEE.csl") `
        --standalone -t latex -o $tex
    if ($LASTEXITCODE -ne 0) { throw "Pandoc failed on $md" }
    $args = @("-interaction=nonstopmode", "-halt-on-error",
              "-output-directory=$(Join-Path $root 'build')", $tex)
    & $xelatex @args | Out-Null
    & $xelatex @args | Out-Null
    if (-not (Test-Path $pdf)) { throw "XeLaTeX did not produce $pdf" }
    Write-Host "Built $pdf"
    $pdf
}

# Main IEEE paper
$mainPdf = Build-PDF (Join-Path $root "paper_tste_ieee.md") "paper_tste_ieee"

# Supplementary appendix
$suppPdf = Build-PDF (Join-Path $root "paper_tste_supplementary.md") "paper_tste_supplementary"

Write-Host ""
Write-Host "=== IEEE TSTE build complete ==="
Write-Host "  Main:          $mainPdf"
Write-Host "  Supplementary: $suppPdf"
