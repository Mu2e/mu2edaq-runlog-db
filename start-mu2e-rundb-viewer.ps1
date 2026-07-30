<#
.SYNOPSIS
    Bootstrap the venv, apply migrations, and start the web application on
    Windows. PowerShell port of start-mu2e-rundb-viewer.

.DESCRIPTION
    DJANGO_ENV=development (default) runs Django's runserver; production runs
    waitress (the Windows-friendly WSGI server -- gunicorn is Unix-only and uses
    fork). The server is backgrounded via Start-Process with a PID file so
    stop-mu2e-rundb-viewer.ps1 can stop it.

    Environment: DJANGO_ENV, RUNLOGDB_HOST (default 127.0.0.1), RUNLOGDB_PORT
    (default 8000).
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$ExtraArgs
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir
$VenvPy = Join-Path $ScriptDir '.venv\Scripts\python.exe'
$PidFile = Join-Path $ScriptDir '.runserver.pid'

function Test-ProcessAlive([int]$ProcId) {
    return [bool](Get-Process -Id $ProcId -ErrorAction SilentlyContinue)
}

# Step 1: bootstrap
& (Join-Path $ScriptDir 'bootstrap-mu2e-rundb-viewer.ps1')

# Step 2: already-running check
if (Test-Path $PidFile) {
    $old = (Get-Content $PidFile -Raw).Trim()
    if ($old -match '^\d+$' -and (Test-ProcessAlive ([int]$old))) {
        Write-Host "[start] Application is already running (PID $old)."
        exit 0
    }
    Write-Host '[start] Stale PID file found -- removing.'
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

# Step 3: configuration
$djangoEnv = if ($env:DJANGO_ENV) { $env:DJANGO_ENV } else { 'development' }
$env:DJANGO_SETTINGS_MODULE = 'runlogdb.settings'
$hostAddr = if ($env:RUNLOGDB_HOST) { $env:RUNLOGDB_HOST } else { '127.0.0.1' }
$port = if ($env:RUNLOGDB_PORT) { $env:RUNLOGDB_PORT } else { '8000' }
Write-Host "[start] Environment : $djangoEnv"
Write-Host "[start] Address     : ${hostAddr}:${port}"

# Step 4: migrations
Write-Host '[start] Running migrations ...'
& $VenvPy manage.py migrate

# Step 5: start the server (backgrounded)
$log = Join-Path $ScriptDir '.runserver.log'
if ($djangoEnv -eq 'production') {
    $waitress = Join-Path $ScriptDir '.venv\Scripts\waitress-serve.exe'
    if (Test-Path $waitress) {
        Write-Host "[start] Starting waitress (background) on ${hostAddr}:${port} ..."
        $proc = Start-Process -FilePath $waitress `
            -ArgumentList @("--listen=${hostAddr}:${port}", 'runlogdb.wsgi:application') `
            -WorkingDirectory $ScriptDir -RedirectStandardOutput $log `
            -RedirectStandardError "$log.err" -WindowStyle Hidden -PassThru
    } else {
        Write-Warning 'waitress not installed; falling back to runserver. Run bootstrap-mu2e-rundb-viewer.ps1.'
        $proc = Start-Process -FilePath $VenvPy `
            -ArgumentList @('manage.py', 'runserver', "${hostAddr}:${port}", '--noreload') `
            -WorkingDirectory $ScriptDir -RedirectStandardOutput $log `
            -RedirectStandardError "$log.err" -WindowStyle Hidden -PassThru
    }
} else {
    Write-Host "[start] Starting Django dev server (background) on ${hostAddr}:${port} ..."
    $proc = Start-Process -FilePath $VenvPy `
        -ArgumentList @('manage.py', 'runserver', "${hostAddr}:${port}", '--noreload') `
        -WorkingDirectory $ScriptDir -RedirectStandardOutput $log `
        -RedirectStandardError "$log.err" -WindowStyle Hidden -PassThru
}
Set-Content -Path $PidFile -Value $proc.Id -Encoding ascii
Write-Host "[start] Application started (PID $($proc.Id))."
Write-Host "[start] Logs : $log"
Write-Host '[start] Stop : .\stop-mu2e-rundb-viewer.ps1'
