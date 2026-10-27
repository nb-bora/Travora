from dataclasses import dataclass
from uuid import UUID

from django.core.exceptions import PermissionDenied

from apps.shared_kernel.roles import Role


@dataclass(frozen=True)
class Actor:
    """Utilisateur authentifié et son agence, résolus côté serveur."""

    user_id: UUID
    agency_id: UUID
    role: Role

    @property
    def can_view_financials(self) -> bool:
        return self.role == Role.MANAGER

    def require_manager(self) -> None:
        if self.role != Role.MANAGER:
            raise PermissionDenied("Action réservée au gérant.")
