"""Accès communs aux vues : utilisateur connecté, agence active, pages jamais mises en cache."""

from typing import cast

from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.cache import patch_cache_control

from apps.shared_kernel.actor import Actor
from apps.tenancy.middleware import TenantRequest


class NoAgency(Exception):
    """Authentifié mais sans agence active (aucune appartenance, ou agence suspendue)."""


def _actor(request: HttpRequest) -> Actor:
    actor = cast(TenantRequest, request).actor
    if actor is None:
        raise NoAgency
    return actor


def agency_required(view):  # type: ignore[no-untyped-def]
    """Exige un utilisateur connecté avec une agence active ; sinon redirige ou explique."""

    def wrapper(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        if not request.user.is_authenticated:
            # Après une session expirée, un POST ne se rejoue pas : on repart de l'accueil.
            target = request.get_full_path() if request.method in ("GET", "HEAD") else "/"
            return redirect_to_login(target)
        try:
            response = view(request, *args, **kwargs)
        except NoAgency:
            response = render(request, "web/no_agency.html", status=403)
        patch_cache_control(response, no_store=True, private=True)
        return response

    wrapper.__name__ = view.__name__
    return wrapper
