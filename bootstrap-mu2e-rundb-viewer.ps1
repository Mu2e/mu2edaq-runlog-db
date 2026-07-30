<#
.SYNOPSIS
    Create the Python virtual environment (.venv) if missing and install/upgrade
    packages from requirements.txt. PowerShell port of bootstrap-mu2e-rundb-viewer.
    Safe to run repeatedly.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $Here '.venv'
$Requirements = Join-Path $Here 'requirements.txt'

$VenvPy = Join-Path $VenvDir 'Scripts\python.exe'
if (-not (Test-Path $VenvPy)) {
    # Prefer 'python'; fall back to the py launcher.
    $Python = $env:PYTHON
    if (-not $Python) {
        if (Get-Command python -ErrorAction SilentlyContinue) { $Python = 'python' }
        elseif (Get-Command py -ErrorAction SilentlyContinue) { $Python = 'py' }
        else { Write-Error 'Python 3.9+ not found on PATH.'; exit 1 }
    }
    Write-Host "[bootstrap] Creating virtual environment at $VenvDir ..."
    & $Python -m venv $VenvDir
} else {
    Write-Host "[bootstrap] Virtual environment exists at $VenvDir"
}

Write-Host '[bootstrap] Installing/updating packages from requirements.txt ...'
& $VenvPy -m pip install --upgrade pip --quiet
& $VenvPy -m pip install -r $Requirements --upgrade --quiet
# waitress is the Windows-friendly production WSGI server (gunicorn is Unix-only).
& $VenvPy -m pip install waitress --quiet
Write-Host '[bootstrap] Done.'
