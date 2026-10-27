"""Preuves d'isolation entre agences.

Les tests de lecture et d'écriture endossent le rôle d'exécution ``travora_app`` : le
super-utilisateur qui crée la base de test contourne toujours la RLS.
"""

import uuid

import pytest
from django.apps import apps
from django.db import DatabaseError, connection, transaction

from apps.accounts.models import Membership
from apps.audit.models import AuditEvent
from apps.shared_kernel.models import TenantManager, TenantScopedModel
from apps.shared_kernel.tenant_context import (
    TenantContextMissing,
    TenantMismatch,
    user_scope,
)
from apps.tenancy.services.public import TenancyService
from tests.conftest import AgencyFixture, runtime_role


def tenant_tables() -> list[str]:
    tables = [
        model._meta.db_table for model in apps.get_models() if issubclass(model, TenantScopedModel)
    ]
    return [*tables, "tenancy_agency"]


def test_every_tenant_model_defaults_to_the_agency_filtered_manager() -> None:
    for model in apps.get_models():
        if issubclass(model, TenantScopedModel):
            assert isinstance(model._default_manager, TenantManager), model.__name__


def scalar(sql: str, params: list[object] | None = None) -> object:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
    return row[0] if row else None


def test_every_tenant_table_has_forced_rls_and_a_policy(db: None) -> None:
    tables = tenant_tables()
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class "
            "WHERE relname = ANY(%s) AND relkind = 'r'",
            [tables],
        )
        flags = {name: (rls, forced) for name, rls, forced in cursor.fetchall()}
        cursor.execute(
            "SELECT DISTINCT tablename FROM pg_policies WHERE tablename = ANY(%s)", [tables]
        )
        with_policy = {row[0] for row in cursor.fetchall()}

    assert set(flags) == set(tables)
    assert all(rls and forced for rls, forced in flags.values())
    assert with_policy == set(tables)


def test_runtime_role_owns_nothing_and_cannot_bypass_rls(db: None) -> None:
    assert scalar("SELECT rolsuper FROM pg_roles WHERE rolname = 'travora_app'") is False
    assert scalar("SELECT rolbypassrls FROM pg_roles WHERE rolname = 'travora_app'") is False
    assert scalar("SELECT count(*) FROM pg_tables WHERE tableowner = 'travora_app'") == 0


def test_without_context_no_row_is_visible(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    with runtime_role():
        for table in tenant_tables():
            assert scalar(f"SELECT count(*) FROM {table}") == 0, table


def test_scope_exposes_only_the_agency_own_rows(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    with runtime_role(), TenancyService.scope(agency_a.id):
        assert set(AuditEvent.objects.values_list("agency_id", flat=True)) == {agency_a.id}
        assert set(Membership.objects.values_list("agency_id", flat=True)) == {agency_a.id}
        assert scalar("SELECT array_agg(id) FROM tenancy_agency") == [agency_a.id]


def test_database_rejects_a_row_written_for_another_agency(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    with (
        runtime_role(),
        TenancyService.scope(agency_a.id),
        pytest.raises(DatabaseError, match="row-level security"),
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute(
            "INSERT INTO audit_event (id, agency_id, action, object_type, object_id, "
            "metadata, created_at) VALUES (%s, %s, 'x', 'x', %s, '{}', now())",
            [uuid.uuid7(), agency_b.id, uuid.uuid7()],
        )


def test_update_and_delete_never_reach_another_agency(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    before = scalar("SELECT count(*) FROM accounts_membership WHERE agency_id = %s", [agency_b.id])
    with runtime_role(), TenancyService.scope(agency_a.id), connection.cursor() as cursor:
        cursor.execute(
            "UPDATE accounts_membership SET role = 'manager' WHERE agency_id = %s", [agency_b.id]
        )
        assert cursor.rowcount == 0
        cursor.execute("DELETE FROM accounts_membership WHERE agency_id = %s", [agency_b.id])
        assert cursor.rowcount == 0
    assert (
        scalar("SELECT count(*) FROM accounts_membership WHERE agency_id = %s", [agency_b.id])
        == before
    )
    assert (
        scalar(
            "SELECT count(*) FROM accounts_membership WHERE agency_id = %s AND role = 'manager'",
            [agency_b.id],
        )
        == 1
    )


def test_membership_is_readable_through_the_user_context_for_its_owner_only(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    with runtime_role(), user_scope(agency_a.manager.user_id):
        memberships = list(Membership.by_user.all())
    assert [m.user_id for m in memberships] == [agency_a.manager.user_id]


def test_the_orm_refuses_to_stamp_a_row_for_another_agency(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    with TenancyService.scope(agency_a.id), pytest.raises(TenantMismatch):
        AuditEvent.objects.create(
            agency_id=agency_b.id, action="x", object_type="x", object_id=uuid.uuid7()
        )


def test_the_orm_refuses_a_write_without_agency_context(db: None) -> None:
    with pytest.raises(TenantContextMissing):
        AuditEvent.objects.create(action="x", object_type="x", object_id=uuid.uuid7())
