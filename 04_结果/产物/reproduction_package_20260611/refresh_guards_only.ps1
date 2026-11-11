$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot

powershell -ExecutionPolicy Bypass -File artifacts\science_readiness_dashboard_20260611\refresh_readiness.ps1
