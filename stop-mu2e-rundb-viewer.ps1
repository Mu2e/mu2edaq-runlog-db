<#
.SYNOPSIS
    Stop the application started by start-mu2e-rundb-viewer.ps1 (PowerShell port
    of stop-mu2e-rundb-viewer): graceful close, then a forced kill after 10s.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile = Join-Path $ScriptDir '.runserver.pid'

function Test-ProcessAlive([int]$ProcId) {
    return [bool](Get-Process -Id $ProcId -ErrorAction SilentlyContinue)
}

if (-not (Test-Path $PidFile)) {
    Write-Host "[stop] No PID file found at $PidFile."
    Write-Host '[stop] The application may not be running, or was not started with .\start-mu2e-rundb-viewer.ps1.'
    exit 0
}

$ProcId = [int]((Get-Content $PidFile -Raw).Trim())
if (-not (Test-ProcessAlive $ProcId)) {
    Write-Host "[stop] Process $ProcId is not running. Removing stale PID file."
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    exit 0
}

Write-Host "[stop] Stopping application (PID $ProcId) ..."
$proc = Get-Process -Id $ProcId -ErrorAction SilentlyContinue
if ($proc) { $proc.CloseMainWindow() | Out-Null }
for ($i = 0; $i -lt 10; $i++) {
    if (-not (Test-ProcessAlive $ProcId)) { break }
    Start-Sleep -Seconds 1
}
if (Test-ProcessAlive $ProcId) {
    Write-Host '[stop] Process did not exit cleanly after 10 s -- forcing ...'
    Stop-Process -Id $ProcId -Force -ErrorAction SilentlyContinue
}
Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
Write-Host '[stop] Application stopped.'
