"""
Management command: purge_db

Deletes all run-log data from the database: runs, subruns, transitions,
configs, FCL documents, run end info, and lookup tables.

Usage:
    python manage.py purge_db              # prompts for confirmation
    python manage.py purge_db --confirm    # skips the confirmation prompt
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from runs.models import (
    ArtdaqFcl,
    Config,
    Run,
    RunEndInfo,
    RunTransition,
    RunTransitionCause,
    RunTransitionType,
    RunType,
    Subrun,
)

_MODELS_IN_ORDER = [
    # Dependents first to respect FK constraints
    ArtdaqFcl,
    Config,
    RunTransition,
    Subrun,
    RunEndInfo,
    Run,
    RunType,
    RunTransitionType,
    RunTransitionCause,
]


class Command(BaseCommand):
    help = "Delete all run-log data from the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            default=False,
            help="Skip the confirmation prompt and proceed immediately.",
        )

    def handle(self, *args, **options):
        total = sum(m.objects.count() for m in _MODELS_IN_ORDER)

        if total == 0:
            self.stdout.write("Database is already empty — nothing to do.")
            return

        if not options["confirm"]:
            self.stdout.write(
                self.style.WARNING(
                    f"This will permanently delete {total} rows across all run-log tables."
                )
            )
            answer = input("Type 'yes' to continue: ").strip().lower()
            if answer != "yes":
                self.stdout.write("Aborted.")
                return

        with transaction.atomic():
            for model in _MODELS_IN_ORDER:
                count, _ = model.objects.all().delete()
                if count:
                    self.stdout.write(f"  deleted {count} rows from {model._meta.db_table}")

        self.stdout.write(self.style.SUCCESS("Database purged."))
