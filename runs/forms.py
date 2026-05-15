from django import forms

_INPUT_CLASS = (
    "rounded-md border border-slate-300 px-3 py-1.5 text-sm "
    "focus:border-mu2e-primary focus:ring-1 focus:ring-mu2e-primary focus:outline-none"
)
_TEXTAREA_CLASS = (
    "w-full rounded-md border border-slate-300 px-3 py-2 text-sm "
    "focus:border-mu2e-primary focus:ring-1 focus:ring-mu2e-primary focus:outline-none"
)
_SELECT_CLASS = (
    "rounded-md border border-slate-300 px-3 py-1.5 text-sm bg-white "
    "focus:border-mu2e-primary focus:ring-1 focus:ring-mu2e-primary focus:outline-none"
)


class RunsByTimeForm(forms.Form):
    start_time = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local", "class": _INPUT_CLASS},
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"],
        label="Start time (UTC)",
    )
    end_time = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local", "class": _INPUT_CLASS},
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"],
        label="End time (UTC)",
    )

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")
        if start and end and start > end:
            raise forms.ValidationError("Start time must be before end time.")
        return cleaned


class SubrunByEwtForm(forms.Form):
    ewt_min = forms.IntegerField(
        label="EWT (min / exact)",
        min_value=0,
        widget=forms.NumberInput(attrs={"class": _INPUT_CLASS, "placeholder": "e.g. 1000"}),
    )
    ewt_max = forms.IntegerField(
        label="EWT max (leave blank for exact match)",
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={"class": _INPUT_CLASS, "placeholder": "optional"}),
    )

    def clean(self):
        cleaned = super().clean()
        ewt_min = cleaned.get("ewt_min")
        ewt_max = cleaned.get("ewt_max")
        if ewt_min is not None and ewt_max is not None and ewt_max < ewt_min:
            raise forms.ValidationError("EWT max must be >= EWT min.")
        return cleaned


# ── Bug report form ───────────────────────────────────────────────────────────

class BugReportForm(forms.Form):
    SEVERITY_CHOICES = [
        ("low", "Low — minor annoyance"),
        ("medium", "Medium — functionality impaired"),
        ("high", "High — major feature broken"),
        ("critical", "Critical — data loss or security issue"),
    ]

    title = forms.CharField(
        label="Title",
        max_length=200,
        widget=forms.TextInput(attrs={"class": _INPUT_CLASS, "placeholder": "Short description of the issue"}),
    )
    severity = forms.ChoiceField(
        label="Severity",
        choices=SEVERITY_CHOICES,
        widget=forms.Select(attrs={"class": _SELECT_CLASS}),
    )
    description = forms.CharField(
        label="Description",
        widget=forms.Textarea(attrs={
            "class": _TEXTAREA_CLASS,
            "rows": 4,
            "placeholder": "What went wrong?",
        }),
    )
    steps = forms.CharField(
        label="Steps to reproduce",
        required=False,
        widget=forms.Textarea(attrs={
            "class": _TEXTAREA_CLASS,
            "rows": 3,
            "placeholder": "1. Go to ...\n2. Click ...\n3. See error",
        }),
    )
    expected = forms.CharField(
        label="Expected behaviour",
        required=False,
        widget=forms.TextInput(attrs={"class": _INPUT_CLASS}),
    )
    actual = forms.CharField(
        label="Actual behaviour",
        required=False,
        widget=forms.TextInput(attrs={"class": _INPUT_CLASS}),
    )


# ── Data entry forms ──────────────────────────────────────────────────────────

class RunForm(forms.Form):
    run_number = forms.IntegerField(
        label="Run number",
        min_value=1,
        widget=forms.NumberInput(attrs={"class": _INPUT_CLASS}),
    )
    run_type_id = forms.IntegerField(
        label="Run type ID",
        required=False,
        widget=forms.NumberInput(attrs={"class": _INPUT_CLASS}),
    )
    run_type = forms.CharField(
        label="Run type (free text)",
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={"class": _INPUT_CLASS}),
    )
    create_time = forms.DateTimeField(
        label="Start time (UTC)",
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local", "class": _INPUT_CLASS},
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"],
    )
    comment = forms.CharField(
        label="Comment",
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={"class": _INPUT_CLASS}),
    )


class RunEndInfoForm(forms.Form):
    run_number = forms.IntegerField(
        label="Run number",
        min_value=1,
        widget=forms.NumberInput(attrs={"class": _INPUT_CLASS}),
    )
    comment = forms.CharField(
        label="End comment",
        required=False,
        widget=forms.Textarea(attrs={"class": _TEXTAREA_CLASS, "rows": 3}),
    )


class SubrunForm(forms.Form):
    run = forms.IntegerField(
        label="Run number",
        min_value=1,
        widget=forms.NumberInput(attrs={"class": _INPUT_CLASS}),
    )
    subrun = forms.IntegerField(
        label="Subrun number",
        min_value=0,
        widget=forms.NumberInput(attrs={"class": _INPUT_CLASS}),
    )
    n_events = forms.IntegerField(
        label="Events",
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={"class": _INPUT_CLASS}),
    )
    n_on_spill = forms.IntegerField(
        label="On-spill events",
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={"class": _INPUT_CLASS}),
    )
    n_off_spill = forms.IntegerField(
        label="Off-spill events",
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={"class": _INPUT_CLASS}),
    )
    n_null = forms.IntegerField(
        label="Null events",
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={"class": _INPUT_CLASS}),
    )
    min_ewt = forms.IntegerField(
        label="Min EWT",
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={"class": _INPUT_CLASS}),
    )
    max_ewt = forms.IntegerField(
        label="Max EWT",
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={"class": _INPUT_CLASS}),
    )
    start_time_unix = forms.IntegerField(
        label="Start time (unix)",
        required=False,
        widget=forms.NumberInput(attrs={"class": _INPUT_CLASS}),
    )
    stop_time_unix = forms.IntegerField(
        label="Stop time (unix)",
        required=False,
        widget=forms.NumberInput(attrs={"class": _INPUT_CLASS}),
    )
