from collections.abc import Callable
from typing import cast

from django.db import transaction
from django.http import HttpRequest, HttpResponse

from apps.shared_kernel.actor import Actor
from apps.tenancy.services.public import TenancyService


class TenantRequest(HttpRequest):
    actor: Actor | None


class TenantMiddleware:
    """Résout l'agence depuis l'identité authentifiée, jamais depuis la requête.

    La requête entière s'exécute dans la transaction de l'agence. Les exceptions étant
    converties en réponses 500 avant de remonter jusqu'ici, une réponse 5xx annule la
    transaction explicitement.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        tenant_request = cast(TenantRequest, request)
        user = request.user
        if not user.is_authenticated:
            tenant_request.actor = None
            return self.get_response(request)
        with TenancyService.actor_scope(user.pk) as actor:
            tenant_request.actor = actor
            response = self.get_response(request)
            if response.status_code >= 500:
                transaction.set_rollback(True)
            return response
