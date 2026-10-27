from typing import cast

from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.dashboard.services.public import DashboardService
from apps.tenancy.middleware import TenantRequest


def today(request: HttpRequest) -> HttpResponse:
    """Écran d'accueil : les chiffres du jour. Le rôle décide de ce qui est montré."""
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    actor = cast(TenantRequest, request).actor
    if actor is None:
        # Authentifié mais sans agence active (aucune appartenance, ou agence suspendue).
        return render(request, "web/no_agency.html", status=403)
    return render(
        request,
        "web/today.html",
        {"snapshot": DashboardService.snapshot(actor), "is_manager": actor.can_view_financials},
    )
