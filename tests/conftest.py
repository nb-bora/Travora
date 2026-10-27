from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from uuid import UUID

import pytest
from django.db import connection

from apps.accounts.services.public import AccountsService
from apps.shared_kernel.actor import Actor
from apps.shared_kernel.roles import Role
from apps.tenancy.services.public import TenancyService

PASSWORD = "mot-de-passe-solide-123"


@dataclass(frozen=True)
class AgencyFixture:
    id: UUID
    manager: Actor
    agent: Actor


@contextmanager
def runtime_role() -> Iterator[None]:
    """Endosse le rôle d'exécution : le super-utilisateur de test contourne la RLS."""
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL ROLE travora_app")
    try:
        yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute("RESET ROLE")


def make_agency(slug: str) -> AgencyFixture:
    info = TenancyService.create_agency(name=slug.title(), slug=slug)
    with TenancyService.scope(info.id):
        manager = AccountsService.create_first_manager(
            username=f"{slug}-manager", password=PASSWORD
        )
        manager_actor = Actor(user_id=manager.user_id, agency_id=info.id, role=Role.MANAGER)
        agent = AccountsService.create_member(
            manager_actor, username=f"{slug}-agent", password=PASSWORD, role=Role.AGENT
        )
    return AgencyFixture(
        id=info.id,
        manager=manager_actor,
        agent=Actor(user_id=agent.user_id, agency_id=info.id, role=Role.AGENT),
    )


@pytest.fixture
def agency_a(db: None) -> AgencyFixture:
    return make_agency("alpha")


@pytest.fixture
def agency_b(db: None) -> AgencyFixture:
    return make_agency("bravo")
