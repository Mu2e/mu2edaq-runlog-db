#!/usr/bin/env bash
#
# stop-mu2edaq-runlog-db.sh - standardized Mu2e control-room stop script.
# The entry point expected by the control room (`crs-app stop runlog-db`).
# Delegates to the existing stop-mu2e-rundb-viewer.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec "$SCRIPT_DIR/stop-mu2e-rundb-viewer" "$@"
