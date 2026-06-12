#!/usr/bin/env bash
# stop-mu2edaq-runlog-db.sh
#
# Stops the application that was started by start-mu2edaq-runlog-db.sh.
# Sends SIGTERM and waits up to 10 seconds for a clean shutdown.
# Falls back to SIGKILL if the process does not exit in time.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.runserver.pid"

# Stop the discovery responder sidecar first (if any), so the service
# disappears from discovery before the web port closes.
DISC_PID_FILE="$SCRIPT_DIR/.discovery.pid"
if [ -f "$DISC_PID_FILE" ]; then
    kill "$(cat "$DISC_PID_FILE")" 2>/dev/null || true
    rm -f "$DISC_PID_FILE"
fi

if [ ! -f "$PID_FILE" ]; then
    echo "[stop] No PID file found at $PID_FILE."
    echo "[stop] The application may not be running, or was not started with ./start-mu2edaq-runlog-db.sh."
    exit 0
fi

PID=$(cat "$PID_FILE")

if ! kill -0 "$PID" 2>/dev/null; then
    echo "[stop] Process $PID is not running. Removing stale PID file."
    rm -f "$PID_FILE"
    exit 0
fi

echo "[stop] Stopping application (PID $PID) ..."
kill "$PID"

# Wait up to 10 seconds for a clean exit.
for i in $(seq 1 10); do
    if ! kill -0 "$PID" 2>/dev/null; then
        break
    fi
    sleep 1
done

if kill -0 "$PID" 2>/dev/null; then
    echo "[stop] Process did not exit cleanly after 10 s — sending SIGKILL ..."
    kill -9 "$PID"
fi

rm -f "$PID_FILE"
echo "[stop] Application stopped."
