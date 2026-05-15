class ProductionRouter:
    """Skip Django-managed migrations for the runs app tables on Postgres.

    The run-log schema (tables in the runs app) already exists in the production
    Postgres database and must not be touched by Django. Django's own internal
    tables (auth, sessions, sites, socialaccount, etc.) are still created normally
    on a fresh Postgres instance.
    """

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        from django.conf import settings

        engine = settings.DATABASES["default"]["ENGINE"]
        if "postgresql" in engine and app_label == "runs":
            return False  # run-log tables pre-exist; never migrate them
        return None  # defer to Django's default for everything else
