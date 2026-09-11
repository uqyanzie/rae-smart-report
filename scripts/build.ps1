#requires -Version 5.1
<#
.SYNOPSIS
    Builds the RAESmartReport SPA and packages the standalone desktop executable.

.DESCRIPTION
    Runs the Vite production build in frontend/ then invokes PyInstaller with
    packaging.spec. The resulting dist/RAE-Smart-Report.exe bundles the backend,
    the built SPA, and the Lazada SKU-mapping artifact.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/build.ps1
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "==> Building frontend (Vite)"
Push-Location (Join-Path $root "frontend")
try {
    npm run build
} finally {
    Pop-Location
}

Write-Host "==> Packaging desktop executable (PyInstaller)"
python -m PyInstaller (Join-Path $root "packaging.spec") --noconfirm --clean

$exe = Join-Path $root "dist\RAE-Smart-Report.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "Build finished but $exe was not produced."
}
Write-Host "==> Done: $exe"
