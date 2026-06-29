import logging
import os
import sys

from django.apps import AppConfig

log = logging.getLogger(__name__)


class RunsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "runs"

    def ready(self):
        # Mu2e DAQ service discovery: advertise the HTTP port so the app
        # appears in mu2edaq-discover scans and the control room browser.
        # Only run when actually serving (runserver / gunicorn), never for
        # management commands such as migrate, collectstatic, or test.
        argv0 = os.path.basename(sys.argv[0] if sys.argv else "")
        serving = ("runserver" in sys.argv) or argv0.startswith("gunicorn")
        if not serving:
            return
        try:
            from mu2edaq_discovery import Responder
            port = int(os.environ.get("RUNLOGDB_PORT", "8000"))
            # Keep a reference on the AppConfig so it is not garbage-collected.
            self._discovery_responder = Responder(
                name="Run Log Database", app="runlog-db",
                port=port, scheme="http")
            self._discovery_responder.start()
        except Exception as exc:  # best-effort: never block app startup
            log.warning("Discovery responder not started: %s", exc)
