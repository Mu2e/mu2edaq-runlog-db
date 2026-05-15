"""
Management command: seed_db

Populates the database with realistic-looking test data.

Usage:
    python manage.py seed_db
    python manage.py seed_db --runs 50 --subruns-per-run 20
    python manage.py seed_db --runs 5 --subruns-per-run 3 --start-run 2000
"""
import datetime
import random

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

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

RUN_TYPE_NAMES = [
    ("physics", "Standard physics data-taking run"),
    ("cosmic", "Cosmic ray calibration run"),
    ("laser", "Laser calibration run"),
    ("pedestal", "Pedestal calibration run"),
    ("noise", "Noise measurement run"),
]

TRANSITION_TYPES = [
    ("start", "Run started"),
    ("stop", "Run stopped"),
    ("pause", "Run paused"),
    ("resume", "Run resumed"),
]

TRANSITION_CAUSES = ["operator", "beam_loss", "detector_issue", "scheduled"]

SUBSYSTEMS = ["tracker", "calorimeter", "crv", "stm", "trigger"]


class Command(BaseCommand):
    help = "Populate the database with configurable test data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--runs",
            type=int,
            default=10,
            help="Number of runs to create (default: 10)",
        )
        parser.add_argument(
            "--subruns-per-run",
            type=int,
            default=5,
            help="Subruns per run (default: 5)",
        )
        parser.add_argument(
            "--start-run",
            type=int,
            default=1001,
            help="Starting run number (default: 1001)",
        )

    def handle(self, *args, **options):
        n_runs = options["runs"]
        n_subruns = options["subruns_per_run"]
        start_run = options["start_run"]

        self.stdout.write(
            f"Seeding {n_runs} runs × {n_subruns} subruns "
            f"(starting at run {start_run}) ..."
        )

        with transaction.atomic():
            run_types = self._ensure_lookup_data()
            self._create_runs(start_run, n_runs, n_subruns, run_types)

        self.stdout.write(self.style.SUCCESS("Done."))

    # ── helpers ──────────────────────────────────────────────────────────────

    def _ensure_lookup_data(self):
        """Create RunType / RunTransitionType / RunTransitionCause rows if absent."""
        run_types = {}
        for i, (name, desc) in enumerate(RUN_TYPE_NAMES, start=1):
            rt, _ = RunType.objects.get_or_create(id=i, defaults={"name": name, "description": desc})
            run_types[name] = rt

        for i, (name, desc) in enumerate(TRANSITION_TYPES, start=1):
            RunTransitionType.objects.get_or_create(id=i, defaults={"name": name, "description": desc})

        for i, name in enumerate(TRANSITION_CAUSES, start=1):
            RunTransitionCause.objects.get_or_create(id=i, defaults={"name": name})

        return run_types

    def _create_runs(self, start_run, n_runs, n_subruns, run_types):
        base_time = timezone.now() - datetime.timedelta(days=n_runs)

        for i in range(n_runs):
            run_number = start_run + i
            if Run.objects.filter(pk=run_number).exists():
                self.stdout.write(f"  run {run_number} already exists — skipping")
                continue

            run_type = random.choice(list(run_types.values()))
            start_time = base_time + datetime.timedelta(hours=i * 2)
            end_time = start_time + datetime.timedelta(minutes=random.randint(30, 180))

            run = Run.objects.create(
                run_number=run_number,
                create_time=start_time,
                run_type=run_type.name,
                run_type_fk=run_type,
                comment=f"Seeded {run_type.name} run",
            )

            RunEndInfo.objects.create(
                run_number=run,
                comment="Normal end of run",
                create_time=end_time,
            )

            # Transitions: start then stop
            start_type = RunTransitionType.objects.get(name="start")
            stop_type = RunTransitionType.objects.get(name="stop")
            cause = RunTransitionCause.objects.get(name="operator")

            RunTransition.objects.create(
                run_number=run, type_fk=start_type, cause_fk=cause, transition_time=start_time
            )
            RunTransition.objects.create(
                run_number=run, type_fk=stop_type, cause_fk=cause, transition_time=end_time
            )

            # Config entries
            for subsystem in random.sample(SUBSYSTEMS, k=random.randint(2, len(SUBSYSTEMS))):
                Config.objects.create(
                    run_number=run,
                    subsystem=subsystem,
                    config={"version": "1.0", "subsystem": subsystem, "run": run_number},
                    create_time=start_time,
                )

            # Subruns
            ewt = random.randint(0, 10000)
            unix_start = int(start_time.timestamp())
            for j in range(n_subruns):
                ewt_span = random.randint(50, 300)
                duration = random.randint(30, 120)
                n_events = random.randint(1000, 20000)
                n_on = int(n_events * random.uniform(0.7, 0.95))
                n_off = int(n_events * random.uniform(0.03, 0.15))
                n_null = n_events - n_on - n_off

                Subrun.objects.create(
                    run_fk=run,
                    subrun=j,
                    n_events=n_events,
                    n_on_spill=n_on,
                    n_off_spill=n_off,
                    n_null=n_null,
                    min_ewt=ewt,
                    max_ewt=ewt + ewt_span - 1,
                    start_time_unix=unix_start,
                    stop_time_unix=unix_start + duration,
                )
                ewt += ewt_span
                unix_start += duration + random.randint(1, 10)

            self.stdout.write(f"  created run {run_number} ({run_type.name}, {n_subruns} subruns)")
