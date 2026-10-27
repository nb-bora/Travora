"""Isolation de chaque table, avec des données réelles dans les deux agences.

Si une table du plan de données est ajoutée sans être alimentée par ``populate``, le test
``test_every_tenant_table_is_populated`` échoue : aucune table ne reste sans preuve.
"""

from datetime import date, timedelta

import pytest
from django.apps import apps
from django.db import connection
from django.db.models import Model

from apps.cases.constants import LineKind
from apps.cases.services.public import CasesService
from apps.crm.services.public import CrmService
from apps.payments.constants import PaymentMethod
from apps.payments.services.public import PaymentsService
from apps.quotes.services.public import QuotesService
from apps.shared_kernel.append_only import AppendOnlyModel
from apps.tenancy.services.public import TenancyService
from tests.conftest import AgencyFixture, runtime_role
from tests.test_isolation import scalar, tenant_tables

TODAY = date(2026, 10, 27)


def populate(agency: AgencyFixture) -> None:
    with TenancyService.scope(agency.id):
        customer = CrmService.find_or_create_customer(
            agency.agent, name="Client", phone="+237677000111"
        )
        case_id = CasesService.create_case(agency.agent, customer_id=customer.id)
        line = CasesService.add_line(
            agency.agent,
            case_id=case_id,
            kind=LineKind.AIR_TICKET,
            label="DLA-CDG",
            price_xaf=500_000,
            cost_xaf=450_000,
            ticket_number="0572345678901",
        )
        CasesService.issue_line(agency.agent, line_id=line.id, issued_on=TODAY)
        PaymentsService.record_payment(
            agency.agent,
            case_id=case_id,
            method=PaymentMethod.MOBILE_MONEY,
            amount_xaf=100_000,
            reference="MP-1",
            received_on=TODAY,
            idempotency_key="k1",
        )
        draft = QuotesService.create_draft(
            agency.agent, case_id=case_id, valid_until=date.today() + timedelta(days=10)
        )
        QuotesService.send(agency.agent, quote_id=draft.id)


@pytest.fixture
def populated(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> tuple[AgencyFixture, AgencyFixture]:
    populate(agency_a)
    populate(agency_b)
    return agency_a, agency_b


def count_for(table: str, agency_id: object) -> int:
    column = "id" if table == "tenancy_agency" else "agency_id"
    return int(scalar(f"SELECT count(*) FROM {table} WHERE {column} = %s", [agency_id]))


def test_every_tenant_table_is_populated(populated: tuple[AgencyFixture, AgencyFixture]) -> None:
    for agency in populated:
        for table in tenant_tables():
            assert count_for(table, agency.id) > 0, f"{table} n'est pas alimentée par populate()"


def test_each_agency_sees_exactly_its_own_rows_in_every_table(
    populated: tuple[AgencyFixture, AgencyFixture],
) -> None:
    expected = {
        (agency.id, table): count_for(table, agency.id)
        for agency in populated
        for table in tenant_tables()
    }
    for agency in populated:
        with runtime_role(), TenancyService.scope(agency.id):
            for table in tenant_tables():
                assert scalar(f"SELECT count(*) FROM {table}") == expected[(agency.id, table)], (
                    table
                )


def test_no_row_is_visible_without_an_agency_in_every_table(
    populated: tuple[AgencyFixture, AgencyFixture],
) -> None:
    with runtime_role():
        for table in tenant_tables():
            assert scalar(f"SELECT count(*) FROM {table}") == 0, table


def test_no_agency_can_touch_the_rows_of_another_in_any_writable_table(
    populated: tuple[AgencyFixture, AgencyFixture],
) -> None:
    first, second = populated
    models: list[type[Model]] = [
        model for model in apps.get_models() if model._meta.db_table in tenant_tables()
    ]
    writable = [m._meta.db_table for m in models if not issubclass(m, AppendOnlyModel)]
    writable.append("tenancy_agency")
    with runtime_role(), TenancyService.scope(first.id), connection.cursor() as cursor:
        for table in writable:
            column = "id" if table == "tenancy_agency" else "agency_id"
            cursor.execute(
                f"UPDATE {table} SET {column} = {column} WHERE {column} = %s", [second.id]
            )
            assert cursor.rowcount == 0, f"UPDATE {table}"
            cursor.execute(f"DELETE FROM {table} WHERE {column} = %s", [second.id])
            assert cursor.rowcount == 0, f"DELETE {table}"
