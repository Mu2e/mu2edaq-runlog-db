#!/usr/bin/env bash
#
# start-mu2edaq-runlog-db.sh - standardized Mu2e control-room start script.
# The entry point expected by the control room (`crs-app start runlog-db`).
# Maps CRS_PORT_HTTP -> RUNLOGDB_PORT and starts the viewer via the existing
# start-mu2e-rundb-viewer. Extra arguments are forwarded.
#
# Port precedence: CRS_PORT_HTTP env > RUNLOGDB_PORT env > built-in default
# (8000, matching apps.yaml).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export RUNLOGDB_PORT="${CRS_PORT_HTTP:-${RUNLOGDB_PORT:-8000}}"

exec "$SCRIPT_DIR/start-mu2e-rundb-viewer" "$@"
