import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from django.db import transaction

from apps.accounts.services.public import AccountsService
from apps.audit.services.public import AuditService
from apps.shared_kernel.actor import Actor
from apps.shared_kernel.tenant_context import tenant_scope, user_scope
from apps.tenancy.dto import AgencyInfo
from apps.tenancy.models import Agency


def _info(agency: Agency) -> AgencyInfo:
    return AgencyInfo(
        id=agency.id,
        name=agency.name,
        slug=agency.slug,
        logo_path=agency.logo.path if agency.logo else "",
    )


def create_agency(*, name: str, slug: str) -> AgencyInfo:
    agency_id = uuid.uuid7()
    with tenant_scope(agency_id):
        agency = Agency.objects.create(id=agency_id, name=name, slug=slug)
    return _info(agency)


def agency_info(actor: Actor) -> AgencyInfo:
    return _info(Agency.objects.get(id=actor.agency_id))


@contextmanager
def actor_scope(user_id: UUID) -> Iterator[Actor | None]:
    """Résout l'agence et le rôle de l'utilisateur, puis ouvre le contexte d'agence.

    Renvoie ``None`` sans ouvrir aucun contexte d'agence si l'utilisateur n'a pas
    d'appartenance active ou si son agence est suspendue.
    """
    with transaction.atomic():
        with user_scope(user_id):
            membership = AccountsService.active_membership(user_id)
        if membership is None:
            yield None
            return
        with tenant_scope(membership.agency_id, user_id):
            agency_is_active = Agency.objects.filter(
                id=membership.agency_id, is_active=True
            ).exists()
        if not agency_is_active:
            yield None
            return
        with tenant_scope(membership.agency_id, user_id):
            yield Actor(user_id=user_id, agency_id=membership.agency_id, role=membership.role)


def set_agency_active(*, user_id: UUID, active: bool) -> AgencyInfo | None:
    """Suspend ou réactive l'agence d'un de ses membres (opération du concierge).

    La suspension ne supprime rien : les données restent intactes et inaltérées, mais plus
    personne de l'agence ne peut se connecter ni lire. Renvoie ``None`` si l'utilisateur
    n'appartient à aucune agence.
    """
    with transaction.atomic():
        with user_scope(user_id):
            membership = AccountsService.active_membership(user_id)
        if membership is None:
            return None
        with tenant_scope(membership.agency_id, user_id):
            agency = Agency.objects.get(id=membership.agency_id)
            if agency.is_active != active:
                agency.is_active = active
                agency.save(update_fields=["is_active"])
                AuditService.record(
                    actor_user_id=user_id,
                    action="agency.reactivated" if active else "agency.suspended",
                    object_type="agency",
                    object_id=agency.id,
                )
            return _info(agency)
