<#
.SYNOPSIS
    Standardized Mu2e control-room start script (PowerShell port of
    start-mu2edaq-runlog-db.sh). Maps CRS_PORT_HTTP -> RUNLOGDB_PORT and starts
    the viewer via start-mu2e-rundb-viewer.ps1. Extra arguments are forwarded.

    Port precedence: CRS_PORT_HTTP > RUNLOGDB_PORT > 8000.
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$ExtraArgs
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$env:RUNLOGDB_PORT = if ($env:CRS_PORT_HTTP) { $env:CRS_PORT_HTTP } elseif ($env:RUNLOGDB_PORT) { $env:RUNLOGDB_PORT } else { '8000' }

& (Join-Path $ScriptDir 'start-mu2e-rundb-viewer.ps1') @ExtraArgs
exit $LASTEXITCODE
