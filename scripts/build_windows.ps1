# build_windows.ps1 — build ActivityLogger.exe on any Windows machine
# Run from the repo root: .\scripts\build_windows.ps1
#
# Prerequisites: Python 3.12 on PATH.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "==> Creating virtual environment" -ForegroundColor Cyan
python -m venv .venv
.\.venv\Scripts\Activate.ps1

Write-Host "==> Installing dependencies" -ForegroundColor Cyan
pip install --upgrade pip
pip install ".[dev]"

Write-Host "==> Running tests" -ForegroundColor Cyan
pytest tests/ -v
if ($LASTEXITCODE -ne 0) {
    Write-Error "Tests failed — aborting build."
    exit 1
}

Write-Host "==> Building exe with PyInstaller" -ForegroundColor Cyan
Set-Location packaging
pyinstaller activity_logger.spec --clean --noconfirm
Set-Location $RepoRoot

$Exe = Join-Path $RepoRoot "packaging\dist\ActivityLogger.exe"
if (Test-Path $Exe) {
    $Size = (Get-Item $Exe).Length / 1MB
    Write-Host ("==> Build succeeded: {0} ({1:F1} MB)" -f $Exe, $Size) -ForegroundColor Green
} else {
    Write-Error "Build failed — exe not found at $Exe"
    exit 1
}
