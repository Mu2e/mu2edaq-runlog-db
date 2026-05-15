from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(url="/runs/", permanent=False)),
    path("runs/", include("runs.urls")),
    path("accounts/", include("allauth.urls")),
    path("admin/", admin.site.urls),
]
