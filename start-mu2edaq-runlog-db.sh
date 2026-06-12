#!/usr/bin/env bash
# start-mu2e-rundb-viewer
#
# Bootstraps the virtual environment, applies any pending database migrations,
# then starts the web application.
#
# Environment variables (can also be set in .env):
#   DJANGO_ENV         development | production  (default: development)
#   RUNLOGDB_HOST      bind address               (default: 127.0.0.1)
#   RUNLOGDB_PORT      bind port                  (default: 8000)
#
# In production mode the server is gunicorn.
# In development mode the server is Django's built-in runserver.
# Inside a Docker container both modes run in the foreground automatically.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"
PID_FILE="$SCRIPT_DIR/.runserver.pid"

# ── Step 1: Bootstrap ─────────────────────────────────────────────────────────
"$SCRIPT_DIR/bootstrap-mu2e-rundb-viewer"

# ── Step 2: Check for an already-running instance ────────────────────────────
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "[start] Application is already running (PID $PID)."
        exit 0
    else
        echo "[start] Stale PID file found — removing."
        rm -f "$PID_FILE"
    fi
fi

# ── Step 3: Resolve configuration ────────────────────────────────────────────
export DJANGO_ENV="${DJANGO_ENV:-development}"
export DJANGO_SETTINGS_MODULE="runlogdb.settings"

HOST="${RUNLOGDB_HOST:-127.0.0.1}"
# CRS_PORT_HTTP is exported by the control room crs-app launcher.
PORT="${CRS_PORT_HTTP:-${RUNLOGDB_PORT:-8000}}"

echo "[start] Environment : $DJANGO_ENV"
echo "[start] Address     : $HOST:$PORT"

# ── Step 4: Run migrations ────────────────────────────────────────────────────
cd "$SCRIPT_DIR"
echo "[start] Running migrations ..."
"$PYTHON" manage.py migrate 2>&1 | sed 's/^/          /'

# ── Step 5: Start the server ──────────────────────────────────────────────────
# Detect Docker: /.dockerenv is created by the Docker runtime.
IN_DOCKER=0
[ -f "/.dockerenv" ] && IN_DOCKER=1

# Discovery responder sidecar. Runs as a separate process (rather than
# embedded in Django) so gunicorn's multiple workers don't each announce.
# No-op when mu2edaq-discovery is not installed.
start_discovery_responder() {
    "$PYTHON" - "$PORT" > /dev/null 2>&1 <<'PYEOF' &
import signal, sys
try:
    from mu2edaq_discovery import Responder
except ImportError:
    sys.exit(0)
r = Responder(name="Run Log Database", app="runlog-db",
              port=int(sys.argv[1]), scheme="http")
r.start()
signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
signal.pause()
PYEOF
    echo $! > "$SCRIPT_DIR/.discovery.pid"
}

if [ "$DJANGO_ENV" = "production" ]; then
    GUNICORN="$VENV_DIR/bin/gunicorn"
    if [ "$IN_DOCKER" = "1" ]; then
        echo "[start] Starting gunicorn (foreground / Docker) on $HOST:$PORT ..."
        exec "$GUNICORN" runlogdb.wsgi \
            --bind "$HOST:$PORT" \
            --workers 4
    else
        echo "[start] Starting gunicorn (background) on $HOST:$PORT ..."
        "$GUNICORN" runlogdb.wsgi \
            --bind "$HOST:$PORT" \
            --workers 4 \
            --pid "$PID_FILE" \
            --daemon
        start_discovery_responder
        echo "[start] Application started (PID $(cat "$PID_FILE"))."
        echo "[start] Stop with: ./stop-mu2edaq-runlog-db.sh"
    fi
else
    # Development server — always foreground-friendly; background outside Docker.
    if [ "$IN_DOCKER" = "1" ]; then
        echo "[start] Starting Django dev server (foreground / Docker) on $HOST:$PORT ..."
        exec "$PYTHON" manage.py runserver "$HOST:$PORT" --noreload
    else
        echo "[start] Starting Django dev server (background) on $HOST:$PORT ..."
        "$PYTHON" manage.py runserver "$HOST:$PORT" --noreload \
            > "$SCRIPT_DIR/.runserver.log" 2>&1 &
        echo $! > "$PID_FILE"
        start_discovery_responder
        echo "[start] Application started (PID $!)."
        echo "[start] Logs : $SCRIPT_DIR/.runserver.log"
        echo "[start] Stop : ./stop-mu2edaq-runlog-db.sh"
    fi
fi
