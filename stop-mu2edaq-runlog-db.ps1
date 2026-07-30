<#
.SYNOPSIS
    Standardized Mu2e control-room stop script (PowerShell port of
    stop-mu2edaq-runlog-db.sh). Delegates to stop-mu2e-rundb-viewer.ps1.
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$ExtraArgs
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

& (Join-Path $ScriptDir 'stop-mu2e-rundb-viewer.ps1') @ExtraArgs
exit $LASTEXITCODE
