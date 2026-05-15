from django.urls import path

from . import views

app_name = "runs"

urlpatterns = [
    # Query views
    path("", views.run_list, name="run_list"),
    path("<int:run_number>/subruns/", views.run_detail, name="run_detail"),
    path("subruns/ewt/", views.subrun_ewt, name="subrun_ewt"),
    # Data entry
    path("entry/", views.entry_index, name="entry_index"),
    path("entry/run/", views.entry_run, name="entry_run"),
    path("entry/run-end/", views.entry_run_end, name="entry_run_end"),
    path("entry/subrun/", views.entry_subrun, name="entry_subrun"),
    # Misc
    path("bug-report/", views.bug_report, name="bug_report"),
    path("about/", views.about, name="about"),
]
