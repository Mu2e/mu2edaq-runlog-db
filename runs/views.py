from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RunEndInfoForm, RunForm, RunsByTimeForm, SubrunByEwtForm, SubrunForm
from .models import Run, RunEndInfo, RunType, Subrun


@login_required
def run_list(request):
    form = RunsByTimeForm(request.GET or None)
    runs = None

    if form.is_valid():
        qs = Run.objects.select_related("run_type_fk").prefetch_related("end_info")
        start = form.cleaned_data.get("start_time")
        end = form.cleaned_data.get("end_time")
        if start:
            qs = qs.filter(create_time__gte=start)
        if end:
            qs = qs.filter(create_time__lte=end)
        runs = qs.order_by("-run_number")

    return render(request, "runs/run_list.html", {"form": form, "runs": runs})


@login_required
def run_detail(request, run_number):
    run = get_object_or_404(Run.objects.select_related("run_type_fk"), pk=run_number)
    subruns = Subrun.objects.filter(run_fk=run).order_by("subrun")
    total_events = subruns.aggregate(total=Sum("n_events"))["total"]

    try:
        end_info = run.end_info
    except Run.end_info.RelatedObjectDoesNotExist:
        end_info = None

    return render(
        request,
        "runs/run_detail.html",
        {
            "run": run,
            "subruns": subruns,
            "total_events": total_events,
            "end_info": end_info,
        },
    )


@login_required
def subrun_ewt(request):
    form = SubrunByEwtForm(request.GET or None)
    subruns = None

    if form.is_valid():
        ewt_min = form.cleaned_data["ewt_min"]
        ewt_max = form.cleaned_data.get("ewt_max")

        if ewt_max is None:
            subruns = (
                Subrun.objects.filter(min_ewt__lte=ewt_min, max_ewt__gte=ewt_min)
                .select_related("run_fk")
                .order_by("run_fk", "subrun")
            )
        else:
            subruns = (
                Subrun.objects.filter(min_ewt__lte=ewt_max, max_ewt__gte=ewt_min)
                .select_related("run_fk")
                .order_by("run_fk", "subrun")
            )

    return render(request, "runs/subrun_ewt.html", {"form": form, "subruns": subruns})


# ── Data entry ────────────────────────────────────────────────────────────────

@login_required
def entry_index(request):
    """Landing page for all manual data-entry forms."""
    return render(request, "runs/entry_index.html")


@login_required
def entry_run(request):
    form = RunForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        run_type_fk = None
        if d.get("run_type_id"):
            run_type_fk = RunType.objects.filter(pk=d["run_type_id"]).first()
        try:
            Run.objects.create(
                run_number=d["run_number"],
                create_time=d["create_time"],
                run_type=d.get("run_type") or "",
                run_type_fk=run_type_fk,
                comment=d.get("comment") or "",
            )
            messages.success(request, f"Run {d['run_number']} created.")
            return redirect("runs:run_detail", run_number=d["run_number"])
        except IntegrityError:
            form.add_error("run_number", "A run with this number already exists.")
    return render(request, "runs/entry_run.html", {"form": form})


@login_required
def entry_run_end(request):
    form = RunEndInfoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        run = get_object_or_404(Run, pk=d["run_number"])
        try:
            RunEndInfo.objects.create(
                run_number=run,
                comment=d.get("comment") or "",
            )
            messages.success(request, f"End info for run {d['run_number']} recorded.")
            return redirect("runs:run_detail", run_number=d["run_number"])
        except IntegrityError:
            form.add_error("run_number", "End info for this run already exists.")
    return render(request, "runs/entry_run_end.html", {"form": form})


@login_required
def entry_subrun(request):
    form = SubrunForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        run = get_object_or_404(Run, pk=d["run"])
        try:
            Subrun.objects.create(
                run_fk=run,
                subrun=d["subrun"],
                n_events=d.get("n_events"),
                n_on_spill=d.get("n_on_spill"),
                n_off_spill=d.get("n_off_spill"),
                n_null=d.get("n_null"),
                min_ewt=d.get("min_ewt"),
                max_ewt=d.get("max_ewt"),
                start_time_unix=d.get("start_time_unix"),
                stop_time_unix=d.get("stop_time_unix"),
            )
            messages.success(
                request,
                f"Subrun {d['subrun']} for run {d['run']} recorded.",
            )
            return redirect("runs:run_detail", run_number=d["run"])
        except IntegrityError:
            form.add_error("subrun", "This subrun already exists for the given run.")
    return render(request, "runs/entry_subrun.html", {"form": form})
