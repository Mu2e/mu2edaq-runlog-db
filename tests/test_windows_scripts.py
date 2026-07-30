"""Windows PowerShell launch-script coverage.

Added in the windows-compat sweep. runlog-db is a Django app; its launch chain
has PowerShell ports for Windows hosts. On Windows the production server uses
waitress rather than gunicorn (which is Unix-only and uses fork); development
uses Django's runserver on both platforms. These tests lock in the .sh/.ps1
parity and parse-check the ports, and confirm `manage.py check` passes.
"""
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
PWSH = shutil.which("pwsh") or shutil.which("powershell")

# (bash entry point, PowerShell port) — the bash launch scripts have no .sh
# extension, so list them explicitly.
SCRIPT_PAIRS = [
    ("start-mu2edaq-runlog-db.sh", "start-mu2edaq-runlog-db.ps1"),
    ("stop-mu2edaq-runlog-db.sh", "stop-mu2edaq-runlog-db.ps1"),
    ("start-mu2e-rundb-viewer", "start-mu2e-rundb-viewer.ps1"),
    ("stop-mu2e-rundb-viewer", "stop-mu2e-rundb-viewer.ps1"),
    ("bootstrap-mu2e-rundb-viewer", "bootstrap-mu2e-rundb-viewer.ps1"),
]


def test_launch_chain_has_powershell_ports():
    for bash_name, ps1_name in SCRIPT_PAIRS:
        assert (REPO / bash_name).is_file(), f"missing bash script: {bash_name}"
        assert (REPO / ps1_name).is_file(), f"missing PowerShell port: {ps1_name}"


@pytest.mark.skipif(not PWSH, reason="PowerShell not available")
@pytest.mark.parametrize("_bash,ps1", SCRIPT_PAIRS)
def test_powershell_scripts_parse(_bash, ps1):
    path = (REPO / ps1).as_posix()
    code = (
        "$e=$null;"
        f"[System.Management.Automation.Language.Parser]::ParseFile('{path}',[ref]$null,[ref]$e)|Out-Null;"
        "if($e){$e|ForEach-Object{Write-Error $_};exit 1}else{exit 0}"
    )
    result = subprocess.run(
        [PWSH, "-NoProfile", "-NonInteractive", "-Command", code],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr


def test_django_check_passes_on_this_platform():
    env = dict(os.environ, DJANGO_SETTINGS_MODULE="runlogdb.settings")
    result = subprocess.run(
        [sys.executable, "manage.py", "check"],
        cwd=str(REPO), env=env, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
