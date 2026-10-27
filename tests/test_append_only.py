import uuid

import pytest
from django.apps import apps
from django.db import DatabaseError, IntegrityError, connection, transaction

from apps.audit.models import AuditEvent
from apps.shared_kernel.append_only import AppendOnlyModel, AppendOnlyViolation
from apps.tenancy.services.public import TenancyService
from tests.conftest import AgencyFixture, runtime_role


def append_only_tables() -> list[str]:
    return [
        model._meta.db_table for model in apps.get_models() if issubclass(model, AppendOnlyModel)
    ]


def has_privilege(table: str, privilege: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT has_table_privilege('travora_app', %s, %s)", [table, privilege])
        row = cursor.fetchone()
    return bool(row and row[0])


def test_runtime_role_can_only_read_and_insert_append_only_tables(db: None) -> None:
    tables = append_only_tables()
    assert "audit_event" in tables
    for table in tables:
        assert has_privilege(table, "SELECT"), table
        assert has_privilege(table, "INSERT"), table
        for privilege in ("UPDATE", "DELETE", "TRUNCATE"):
            assert not has_privilege(table, privilege), (table, privilege)


def make_event(agency: AgencyFixture) -> AuditEvent:
    with TenancyService.scope(agency.id):
        return AuditEvent.objects.create(action="test", object_type="x", object_id=uuid.uuid7())


def test_the_orm_refuses_to_modify_or_delete(agency_a: AgencyFixture) -> None:
    event = make_event(agency_a)
    with TenancyService.scope(agency_a.id):
        event.action = "changed"
        with pytest.raises(AppendOnlyViolation):
            event.save()
        with pytest.raises(AppendOnlyViolation):
            event.delete()
        with pytest.raises(AppendOnlyViolation):
            AuditEvent.objects.all().update(action="changed")
        with pytest.raises(AppendOnlyViolation):
            AuditEvent.objects.all().delete()


def test_the_database_triggers_refuse_even_the_privileged_role(agency_a: AgencyFixture) -> None:
    make_event(agency_a)
    for statement in ("UPDATE audit_event SET action = 'changed'", "DELETE FROM audit_event"):
        with (
            pytest.raises(IntegrityError, match="ajout seul"),
            transaction.atomic(),
            connection.cursor() as cursor,
        ):
            cursor.execute(statement)
    connection.check_constraints()
    with (
        pytest.raises(IntegrityError, match="ajout seul"),
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute("TRUNCATE audit_event")


def test_the_runtime_role_is_denied_by_privileges(agency_a: AgencyFixture) -> None:
    make_event(agency_a)
    with runtime_role(), TenancyService.scope(agency_a.id):
        for statement in ("UPDATE audit_event SET action = 'changed'", "DELETE FROM audit_event"):
            with (
                pytest.raises(DatabaseError, match="permission denied"),
                transaction.atomic(),
                connection.cursor() as cursor,
            ):
                cursor.execute(statement)
