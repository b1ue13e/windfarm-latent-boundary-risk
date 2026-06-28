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

$tradeoffScript = Join-Path $root "scripts\build_accountability_tradeoff.py"
if (Test-Path $tradeoffScript) {
    & python $tradeoffScript
    if ($LASTEXITCODE -ne 0) { throw "Accountability tradeoff generation failed." }
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
