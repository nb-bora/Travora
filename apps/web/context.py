from typing import cast

from django.http import HttpRequest

from apps.shared_kernel.roles import Role
from apps.tenancy.middleware import TenantRequest
from apps.tenancy.services.public import TenancyService


def shell(request: HttpRequest) -> dict[str, object]:
    """Données communes de l'habillage : agence, rôle et initiales de l'utilisateur connecté."""
    actor = cast(TenantRequest, request).actor
    if actor is None or not request.user.is_authenticated:
        return {}
    username = request.user.get_username()
    return {
        "shell": {
            "agency": TenancyService.agency_info(actor).name,
            "role_label": "Gérant" if actor.role is Role.MANAGER else "Agent",
            "is_manager": actor.can_view_financials,
            "username": username,
            "initials": username[:2].upper(),
        }
    }
