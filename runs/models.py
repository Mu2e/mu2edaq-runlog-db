from django.db import models


class RunType(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.CharField(max_length=255)

    class Meta:
        db_table = "run_type"

    def __str__(self):
        return self.name or str(self.id)


class RunTransitionType(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "run_transition_type"

    def __str__(self):
        return self.name or str(self.id)


class RunTransitionCause(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "run_transition_cause"

    def __str__(self):
        return self.name


class Run(models.Model):
    run_number = models.BigIntegerField(primary_key=True)
    comment = models.CharField(max_length=255, null=True, blank=True)
    create_time = models.DateTimeField()
    run_type = models.CharField(max_length=255, null=True, blank=True)
    run_type_fk = models.ForeignKey(
        RunType,
        db_column="run_type_id",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="runs",
    )

    class Meta:
        db_table = "run"

    def __str__(self):
        return f"Run {self.run_number}"


class RunEndInfo(models.Model):
    run_number = models.OneToOneField(
        Run,
        db_column="run_number",
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="end_info",
    )
    comment = models.TextField(null=True, blank=True)
    create_time = models.DateTimeField(null=True, blank=True, auto_now_add=False)

    class Meta:
        db_table = "run_end_info"


class RunTransition(models.Model):
    run_number = models.ForeignKey(
        Run,
        db_column="run_number",
        on_delete=models.CASCADE,
        related_name="transitions",
    )
    type_fk = models.ForeignKey(
        RunTransitionType,
        db_column="type_id",
        on_delete=models.PROTECT,
    )
    cause_fk = models.ForeignKey(
        RunTransitionCause,
        db_column="cause_id",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    transition_time = models.DateTimeField()

    class Meta:
        db_table = "run_transition"
        # No single-column PK in source schema; use composite unique constraint
        unique_together = [("run_number", "type_fk", "transition_time")]


class Subrun(models.Model):
    run_fk = models.ForeignKey(
        Run,
        db_column="run",
        on_delete=models.CASCADE,
        related_name="subruns",
    )
    subrun = models.IntegerField()
    n_events = models.BigIntegerField(null=True, blank=True)
    n_on_spill = models.BigIntegerField(null=True, blank=True)
    n_off_spill = models.BigIntegerField(null=True, blank=True)
    n_null = models.BigIntegerField(null=True, blank=True)
    min_ewt = models.BigIntegerField(null=True, blank=True)
    max_ewt = models.BigIntegerField(null=True, blank=True)
    start_time_unix = models.IntegerField(null=True, blank=True)
    stop_time_unix = models.IntegerField(null=True, blank=True)
    event_mode_counts = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "subrun"
        unique_together = [("run_fk", "subrun")]

    def __str__(self):
        return f"Run {self.run_fk_id} / Subrun {self.subrun}"


class Config(models.Model):
    run_number = models.ForeignKey(
        Run,
        db_column="run_number",
        on_delete=models.CASCADE,
        related_name="configs",
    )
    subsystem = models.TextField()
    config = models.JSONField()
    create_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "config"
        unique_together = [("run_number", "subsystem")]


class ArtdaqFcl(models.Model):
    run_number = models.ForeignKey(
        Run,
        db_column="run_number",
        on_delete=models.CASCADE,
        related_name="fcl_documents",
    )
    name = models.CharField(max_length=255)
    label = models.CharField(max_length=255, null=True, blank=True)
    content = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "artdaq_fcl"
        unique_together = [("run_number", "name")]
