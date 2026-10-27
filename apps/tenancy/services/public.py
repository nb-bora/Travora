"""Façade publique de l'application tenancy : seule surface importable par les autres."""

from contextlib import AbstractContextManager
from uuid import UUID

from apps.shared_kernel.actor import Actor
from apps.shared_kernel.tenant_context import tenant_scope
from apps.tenancy.dto import AgencyInfo
from apps.tenancy.services import commands


class TenancyService:
    @staticmethod
    def create_agency(*, name: str, slug: str) -> AgencyInfo:
        return commands.create_agency(name=name, slug=slug)

    @staticmethod
    def agency_info(actor: Actor) -> AgencyInfo:
        return commands.agency_info(actor)

    @staticmethod
    def set_agency_active(*, user_id: UUID, active: bool) -> AgencyInfo | None:
        return commands.set_agency_active(user_id=user_id, active=active)

    @staticmethod
    def scope(agency_id: UUID, user_id: UUID | None = None) -> AbstractContextManager[None]:
        return tenant_scope(agency_id, user_id)

    @staticmethod
    def actor_scope(user_id: UUID) -> AbstractContextManager[Actor | None]:
        return commands.actor_scope(user_id)
