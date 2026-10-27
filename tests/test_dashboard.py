from collections.abc import Iterator
from datetime import date, timedelta
from uuid import UUID

import pytest
from pytest_django.fixtures import SettingsWrapper

from apps.cases.constants import LineKind
from apps.cases.services.public import CasesService
from apps.crm.services.public import CrmService
from apps.dashboard.constants import AlertKind
from apps.dashboard.services.public import DashboardService
from apps.ledger.constants import Account
from apps.ledger.services.public import LedgerService
from apps.quotes.services.public import QuotesService
from apps.tenancy.services.public import TenancyService
from tests.conftest import AgencyFixture, runtime_role

TODAY = date(2026, 10, 27)


@pytest.fixture
def scoped(agency_a: AgencyFixture) -> Iterator[AgencyFixture]:
    with TenancyService.scope(agency_a.id):
        yield agency_a


def make_case(
    agency: AgencyFixture,
    *,
    price: int = 500_000,
    cost: int = 450_000,
    sold_on: date | None = TODAY,
    departure: date | None = None,
    paid: int = 0,
    name: str = "Client",
) -> UUID:
    customer = CrmService.find_or_create_customer(agency.agent, name=name, phone="")
    case_id = CasesService.create_case(
        agency.agent, customer_id=customer.id, departure_date=departure
    )
    line = CasesService.add_line(
        agency.agent,
        case_id=case_id,
        kind=LineKind.FREE_SERVICE,
        label="Prestation",
        price_xaf=price,
        cost_xaf=cost,
    )
    if sold_on is not None:
        CasesService.issue_line(agency.agent, line_id=line.id, issued_on=sold_on)
    if paid:
        LedgerService.record_payment(
            agency.agent,
            case_id=case_id,
            account=Account.CASH,
            amount_xaf=paid,
            occurred_on=TODAY,
            idempotency_key=f"pay:{case_id}",
        )
    return case_id


def test_the_four_numbers(scoped: AgencyFixture) -> None:
    make_case(scoped, paid=200_000)
    settled = make_case(scoped, price=300_000, cost=260_000, paid=300_000)
    make_case(scoped, sold_on=None)
    CasesService.close_case(scoped.manager, case_id=settled)

    snapshot = DashboardService.snapshot(scoped.manager, today=TODAY)

    assert snapshot.open_cases == 2
    assert snapshot.receivables_xaf == 300_000
    assert snapshot.realized_margin_xaf == 40_000
    assert snapshot.at_risk_cases == 0
    assert snapshot.alerts == ()


def test_an_agent_sees_no_margin_but_the_same_balances(scoped: AgencyFixture) -> None:
    make_case(scoped, paid=200_000)
    snapshot = DashboardService.snapshot(scoped.agent, today=TODAY)
    assert snapshot.realized_margin_xaf is None
    assert snapshot.receivables_xaf == 300_000
    assert snapshot.open_cases == 1


def test_an_unpaid_balance_raises_an_alert_after_the_threshold(
    scoped: AgencyFixture, settings: SettingsWrapper
) -> None:
    settings.OVERDUE_DAYS = 14
    late = make_case(scoped, sold_on=TODAY - timedelta(days=15), name="Retard")
    make_case(scoped, sold_on=TODAY - timedelta(days=14), name="Limite")
    make_case(scoped, sold_on=TODAY - timedelta(days=30), paid=500_000, name="Soldé")

    snapshot = DashboardService.snapshot(scoped.manager, today=TODAY)

    assert [(a.kind, a.case_id) for a in snapshot.alerts] == [(AlertKind.OVERDUE_BALANCE, late)]
    assert snapshot.at_risk_cases == 1


def test_a_close_departure_with_a_balance_raises_an_alert(
    scoped: AgencyFixture, settings: SettingsWrapper
) -> None:
    settings.UPCOMING_DEPARTURE_DAYS = 7
    soon = make_case(scoped, departure=TODAY + timedelta(days=3), name="Bientôt")
    make_case(scoped, departure=TODAY + timedelta(days=3), paid=500_000, name="Payé")
    make_case(scoped, departure=TODAY + timedelta(days=10), name="Loin")
    make_case(scoped, departure=TODAY - timedelta(days=2), name="Passé")

    alerts = DashboardService.snapshot(scoped.manager, today=TODAY).alerts

    assert [(a.kind, a.case_id) for a in alerts] == [(AlertKind.DEPARTURE_SOON, soon)]


def test_a_case_with_two_alerts_counts_once_as_at_risk(
    scoped: AgencyFixture, settings: SettingsWrapper
) -> None:
    settings.OVERDUE_DAYS = 14
    settings.UPCOMING_DEPARTURE_DAYS = 7
    make_case(scoped, sold_on=TODAY - timedelta(days=20), departure=TODAY + timedelta(days=2))

    snapshot = DashboardService.snapshot(scoped.manager, today=TODAY)

    assert len(snapshot.alerts) == 2
    assert snapshot.at_risk_cases == 1


def test_an_expired_sent_quote_raises_an_alert(scoped: AgencyFixture) -> None:
    case_id = make_case(scoped, paid=500_000)
    draft = QuotesService.create_draft(
        scoped.agent, case_id=case_id, valid_until=date.today() + timedelta(days=5)
    )
    QuotesService.send(scoped.agent, quote_id=draft.id)

    assert DashboardService.snapshot(scoped.manager, today=TODAY).alerts == ()
    later = date.today() + timedelta(days=6)
    alerts = DashboardService.snapshot(scoped.manager, today=later).alerts
    assert [a.kind for a in alerts] == [AlertKind.QUOTE_EXPIRED]


def test_the_dashboard_only_counts_its_own_agency(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    with TenancyService.scope(agency_b.id):
        make_case(agency_b, price=900_000, cost=800_000)
    with TenancyService.scope(agency_a.id):
        make_case(agency_a, price=100_000, cost=60_000)

    with runtime_role(), TenancyService.scope(agency_a.id):
        snapshot = DashboardService.snapshot(agency_a.manager, today=TODAY)
    assert snapshot.open_cases == 1
    assert snapshot.receivables_xaf == 100_000
