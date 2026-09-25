$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$cPandoc = Get-Command pandoc -ErrorAction SilentlyContinue
$localPandoc = Join-Path $root "tools\pandoc-3.9.0.2\pandoc.exe"
$pandoc = if ($env:PANDOC_PATH -and (Test-Path $env:PANDOC_PATH)) { $env:PANDOC_PATH } elseif ($cPandoc) { $cPandoc.Source } elseif (Test-Path $localPandoc) { $localPandoc } else { "pandoc" }

$cXelatex = Get-Command xelatex -ErrorAction SilentlyContinue
$localMiKTeX = "E:\MiKTeX\miktex\bin\x64\xelatex.exe"
$localTexlive = "C:\texlive\2025\bin\windows\xelatex.exe"
$xelatex = if ($env:XELATEX_PATH -and (Test-Path $env:XELATEX_PATH)) { $env:XELATEX_PATH } elseif ($cXelatex) { $cXelatex.Source } elseif (Test-Path $localMiKTeX) { $localMiKTeX } elseif (Test-Path $localTexlive) { $localTexlive } else { "xelatex" }
if (Test-Path (Split-Path -Parent $xelatex)) {
    $env:PATH = (Split-Path -Parent $xelatex) + ";$env:PATH"
}

function Build-PDF {
    param($md, $label)
    $tex = "$root\build\${label}.tex"
    $pdf = "$root\build\${label}.pdf"
    New-Item -ItemType Directory -Force -Path "$root\build" | Out-Null
    if (Test-Path $tex) { Remove-Item $tex -Force }
    if (Test-Path $pdf) { Remove-Item $pdf -Force }
    if (Test-Path "$root\TUptm.fd") {
        Copy-Item -LiteralPath "$root\TUptm.fd" -Destination "$root\build\TUptm.fd" -Force
    }
    & $pandoc $md --citeproc --csl "$root\IEEE.csl" --standalone -t latex -o $tex
    if ($LASTEXITCODE -ne 0) { throw "Pandoc failed on $md" }
    & $xelatex -interaction=nonstopmode -halt-on-error "-output-directory=$root\build" $tex | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "XeLaTeX pass 1 failed on $label" }
    & $xelatex -interaction=nonstopmode -halt-on-error "-output-directory=$root\build" $tex | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "XeLaTeX pass 2 failed on $label" }
    if (-not (Test-Path $pdf)) { throw "XeLaTeX did not produce $pdf" }
    Copy-Item -LiteralPath $pdf -Destination "$root\${label}.pdf" -Force
    Write-Host "Built $pdf and copied to $root\${label}.pdf"
}

Build-PDF "$root\paper_tste_ieee.md" "paper_tste_ieee"
Build-PDF "$root\paper_tste_supplementary.md" "paper_tste_supplementary"
Write-Host "=== PDF BUILD COMPLETE ==="
