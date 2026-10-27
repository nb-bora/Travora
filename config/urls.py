from django.urls import include, path

from config.health import healthz

urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("", include("apps.web.urls")),
]
