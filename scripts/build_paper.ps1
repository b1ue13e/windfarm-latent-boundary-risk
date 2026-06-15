$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$input = Join-Path $root "paper_draft.md"
$output = Join-Path $root "paper_draft.pdf"
$csl = Join-Path $root "elsevier-harvard.csl"
$tex = Join-Path $root "paper_draft_compiled.tex"
$buildPdf = Join-Path $root "paper_draft_compiled.pdf"
$localPandoc = Join-Path $root "tools\pandoc-3.9.0.2\pandoc.exe"
$pandoc = if (Test-Path $localPandoc) {
    $localPandoc
} else {
    $command = Get-Command pandoc -ErrorAction SilentlyContinue
    if (-not $command) { throw "Pandoc was not found. Expected local copy at $localPandoc." }
    $command.Source
}
$xelatexCommand = Get-Command xelatex -ErrorAction SilentlyContinue
$localMiKTeXBin = "E:\MiKTeX\miktex\bin\x64"
$localMiKTeX = Join-Path $localMiKTeXBin "xelatex.exe"
$xelatex = if (Test-Path $localMiKTeX) {
    $localMiKTeX
} elseif (Test-Path "C:\texlive\2025\bin\windows\xelatex.exe") {
    "C:\texlive\2025\bin\windows\xelatex.exe"
} elseif ($xelatexCommand) {
    $xelatexCommand.Source
} else {
    throw "XeLaTeX was not found. Install TeX Live or MiKTeX, then rerun this script."
}
$xelatexBin = Split-Path -Parent $xelatex
$env:PATH = "$xelatexBin;$env:PATH"

if (Test-Path $buildPdf) { Remove-Item $buildPdf -Force }
if (Test-Path $output) { Remove-Item $output -Force }

& $pandoc $input --citeproc --csl $csl --standalone -t latex -o $tex
if ($LASTEXITCODE -ne 0) { throw "Pandoc failed to generate $tex." }

$xelatexArgs = @("-interaction=nonstopmode", "-halt-on-error", "-output-directory=$root", $tex)

& $xelatex @xelatexArgs | Out-Null
if ($LASTEXITCODE -ne 0) { throw "XeLaTeX failed on the first pass." }

& $xelatex @xelatexArgs | Out-Null
if ($LASTEXITCODE -ne 0) { throw "XeLaTeX failed on the second pass." }

if (-not (Test-Path $buildPdf)) { throw "XeLaTeX did not produce the expected PDF." }

Copy-Item $buildPdf $output -Force

Write-Host "Built $output"
