from collections.abc import Iterator
from datetime import date
from uuid import UUID

import pytest
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, connection, transaction
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.audit.services.public import AuditService
from apps.cases.constants import CaseStatus, LineKind
from apps.cases.exceptions import (
    BalanceNotSettled,
    CaseHasActiveSales,
    CaseNotClosed,
    CaseNotFound,
    CaseNotOpen,
    InvalidLine,
    LineLocked,
)
from apps.cases.services.public import CasesService
from apps.crm.services.public import CrmService
from apps.ledger.constants import Account
from apps.ledger.services.public import LedgerService
from apps.payments.constants import PaymentMethod
from apps.payments.services.public import PaymentsService
from apps.tenancy.services.public import TenancyService
from tests.conftest import AgencyFixture, runtime_role

TODAY = timezone.localdate()


@pytest.fixture
def scoped(agency_a: AgencyFixture) -> Iterator[AgencyFixture]:
    with TenancyService.scope(agency_a.id):
        yield agency_a


def new_case(
    agency: AgencyFixture, name: str = "Marie Ndong", reference: str | None = None
) -> UUID:
    customer = CrmService.find_or_create_customer(agency.agent, name=name, phone="")
    return CasesService.create_case(agency.agent, customer_id=customer.id, reference=reference)


def air_line(
    agency: AgencyFixture, case_id: UUID, *, price: int = 500_000, cost: int | None = 450_000, **kw
):
    return CasesService.add_line(
        agency.agent,
        case_id=case_id,
        kind=LineKind.AIR_TICKET,
        label="DLA-CDG",
        price_xaf=price,
        cost_xaf=cost,
        passenger_name="NDONG/MARIE",
        **kw,
    )


def test_references_follow_the_year_and_never_repeat(scoped: AgencyFixture) -> None:
    first = CasesService.get_case(scoped.manager, new_case(scoped)).summary.reference
    second = CasesService.get_case(scoped.manager, new_case(scoped)).summary.reference
    assert first.endswith("-0001")
    assert second.endswith("-0002")
    assert first[:4] == second[:4] == str(date.today().year)


def test_a_manual_reference_must_be_unique_in_the_agency(scoped: AgencyFixture) -> None:
    new_case(scoped, reference="D-100")
    with pytest.raises(IntegrityError), transaction.atomic():
        new_case(scoped, reference="D-100")


def test_a_line_is_validated(scoped: AgencyFixture) -> None:
    case_id = new_case(scoped)
    with pytest.raises(InvalidLine):
        air_line(scoped, case_id, price=-1)
    with pytest.raises(InvalidLine):
        CasesService.add_line(
            scoped.agent, case_id=case_id, kind=LineKind.FREE_SERVICE, label=" ", price_xaf=10
        )
    with pytest.raises(InvalidLine):
        CasesService.add_line(
            scoped.agent,
            case_id=case_id,
            kind=LineKind.FREE_SERVICE,
            label="Hôtel",
            price_xaf=10,
            ticket_number="1234567890123",
        )


def test_ticket_numbers_keep_only_digits(scoped: AgencyFixture) -> None:
    line = air_line(scoped, new_case(scoped), ticket_number="057-2345 678901")
    assert line.ticket_number == "0572345678901"


def test_an_agent_never_receives_cost_or_margin(scoped: AgencyFixture) -> None:
    case_id = new_case(scoped)
    line = air_line(scoped, case_id)
    CasesService.issue_line(scoped.agent, line_id=line.id, issued_on=TODAY)

    detail = CasesService.get_case(scoped.agent, case_id)
    assert detail.lines[0].cost_xaf is None
    assert detail.lines[0].margin_xaf is None
    summary = detail.summary
    assert summary.cost_total_xaf is None
    assert summary.expected_margin_xaf is None
    assert summary.recognized_margin_xaf is None
    assert summary.has_unknown_cost is None
    assert summary.balance_xaf == 500_000
    assert summary.price_total_xaf == 500_000

    detail = CasesService.get_case(scoped.manager, case_id)
    assert detail.lines[0].cost_xaf == 450_000
    assert detail.lines[0].margin_xaf == 50_000
    assert detail.summary.recognized_margin_xaf == 50_000
    assert detail.summary.expected_margin_xaf == 50_000
    assert CasesService.list_cases(scoped.agent)[0].recognized_margin_xaf is None


def test_an_agent_may_enter_a_cost_but_never_read_it_back(scoped: AgencyFixture) -> None:
    line = air_line(scoped, new_case(scoped), cost=300_000)
    assert line.cost_xaf is None
    assert line.margin_xaf is None


def test_an_unknown_cost_is_flagged_and_blocks_issuing(scoped: AgencyFixture) -> None:
    case_id = new_case(scoped)
    line = air_line(scoped, case_id, cost=None)
    assert CasesService.get_case(scoped.manager, case_id).summary.has_unknown_cost is True
    with pytest.raises(InvalidLine):
        CasesService.issue_line(scoped.agent, line_id=line.id, issued_on=TODAY)

    CasesService.update_line(scoped.agent, line_id=line.id, cost_xaf=450_000)
    CasesService.issue_line(scoped.agent, line_id=line.id, issued_on=TODAY)
    assert CasesService.get_case(scoped.manager, case_id).summary.has_unknown_cost is False


def test_issuing_posts_the_sale_to_the_ledger_once(scoped: AgencyFixture) -> None:
    case_id = new_case(scoped)
    line = air_line(scoped, case_id)
    CasesService.issue_line(scoped.agent, line_id=line.id, issued_on=TODAY)

    assert LedgerService.balances_by_case(scoped.agent) == {case_id: 500_000}
    with pytest.raises(LineLocked):
        CasesService.issue_line(scoped.agent, line_id=line.id, issued_on=TODAY)
    assert LedgerService.balances_by_case(scoped.agent) == {case_id: 500_000}


def test_an_issued_line_can_no_longer_be_edited(scoped: AgencyFixture) -> None:
    line = air_line(scoped, new_case(scoped))
    CasesService.issue_line(scoped.agent, line_id=line.id, issued_on=TODAY)
    with pytest.raises(LineLocked):
        CasesService.update_line(scoped.agent, line_id=line.id, price_xaf=1)


def test_a_zero_value_line_cannot_be_issued(scoped: AgencyFixture) -> None:
    line = air_line(scoped, new_case(scoped), price=0, cost=0)
    with pytest.raises(InvalidLine):
        CasesService.issue_line(scoped.agent, line_id=line.id, issued_on=TODAY)


def test_voiding_an_issued_line_reverses_the_sale_and_is_for_managers(
    scoped: AgencyFixture,
) -> None:
    case_id = new_case(scoped)
    line = air_line(scoped, case_id)
    CasesService.issue_line(scoped.agent, line_id=line.id, issued_on=TODAY)

    with pytest.raises(PermissionDenied):
        CasesService.void_line(scoped.agent, line_id=line.id, voided_on=TODAY)
    voided = CasesService.void_line(scoped.manager, line_id=line.id, voided_on=TODAY)

    assert voided.is_voided
    assert LedgerService.balances_by_case(scoped.agent) == {case_id: 0}
    assert LedgerService.margins_by_case(scoped.manager) == {case_id: 0}
    assert CasesService.get_case(scoped.manager, case_id).summary.price_total_xaf == 0
    with pytest.raises(LineLocked):
        CasesService.void_line(scoped.manager, line_id=line.id, voided_on=TODAY)


def test_a_case_closes_only_when_settled(scoped: AgencyFixture) -> None:
    case_id = new_case(scoped)
    line = air_line(scoped, case_id)
    CasesService.issue_line(scoped.agent, line_id=line.id, issued_on=TODAY)
    with pytest.raises(BalanceNotSettled):
        CasesService.close_case(scoped.agent, case_id=case_id)

    LedgerService.record_payment(
        scoped.agent,
        case_id=case_id,
        account=Account.CASH,
        amount_xaf=500_000,
        occurred_on=TODAY,
        idempotency_key="p",
    )
    CasesService.close_case(scoped.agent, case_id=case_id)

    assert CasesService.get_case(scoped.agent, case_id).summary.status is CaseStatus.CLOSED
    with pytest.raises(CaseNotOpen):
        air_line(scoped, case_id)


def test_cancelling_requires_issued_lines_to_be_voided_first(scoped: AgencyFixture) -> None:
    case_id = new_case(scoped)
    issued = air_line(scoped, case_id)
    CasesService.issue_line(scoped.agent, line_id=issued.id, issued_on=TODAY)
    pending = air_line(scoped, case_id, price=100_000, cost=80_000)

    with pytest.raises(PermissionDenied):
        CasesService.cancel_case(scoped.agent, case_id=case_id, cancelled_on=TODAY)
    with pytest.raises(CaseHasActiveSales):
        CasesService.cancel_case(scoped.manager, case_id=case_id, cancelled_on=TODAY)

    CasesService.void_line(scoped.manager, line_id=issued.id, voided_on=TODAY)
    CasesService.cancel_case(scoped.manager, case_id=case_id, cancelled_on=TODAY)

    detail = CasesService.get_case(scoped.manager, case_id)
    assert detail.summary.status is CaseStatus.CANCELLED
    assert all(line.is_voided for line in detail.lines)
    assert pending.id in {line.id for line in detail.lines}


def test_a_ticket_number_is_unique_among_active_lines_of_an_agency(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    with TenancyService.scope(agency_a.id):
        case_id = new_case(agency_a)
        first = air_line(agency_a, case_id, ticket_number="0572345678901")
        with pytest.raises(IntegrityError), transaction.atomic():
            air_line(agency_a, case_id, ticket_number="0572345678901")
        CasesService.void_line(agency_a.manager, line_id=first.id, voided_on=TODAY)
        air_line(agency_a, case_id, ticket_number="0572345678901")
    with TenancyService.scope(agency_b.id):
        air_line(agency_b, new_case(agency_b), ticket_number="0572345678901")


@pytest.mark.parametrize("kind", [LineKind.BUS_TICKET, LineKind.TRAIN_TICKET, LineKind.BOAT_TICKET])
def test_every_transport_ticket_carries_a_normalised_reference_and_a_carrier(
    scoped: AgencyFixture, kind: LineKind
) -> None:
    line = CasesService.add_line(
        scoped.agent,
        case_id=new_case(scoped),
        kind=kind,
        label="Douala-Yaoundé",
        price_xaf=8_000,
        cost_xaf=7_000,
        ticket_number=" kb-8f3a 21 ",
        carrier=" Touristique Express ",
    )
    assert line.ticket_number == "KB8F3A21"
    assert line.carrier == "Touristique Express"


def test_a_reference_is_unique_per_kind_of_ticket(scoped: AgencyFixture) -> None:
    case_id = new_case(scoped)
    for kind in (LineKind.BUS_TICKET, LineKind.TRAIN_TICKET):
        CasesService.add_line(
            scoped.agent,
            case_id=case_id,
            kind=kind,
            label="Trajet",
            price_xaf=1_000,
            ticket_number="AB1234",
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        CasesService.add_line(
            scoped.agent,
            case_id=case_id,
            kind=LineKind.BUS_TICKET,
            label="Trajet",
            price_xaf=1_000,
            ticket_number="ab-1234",
        )


def test_ticket_numbers_are_proposed_from_pasted_text() -> None:
    text = (
        "E-TICKET 057 2345678901 NDONG/MARIE\n"
        "Billet 057-2345678901 (copie)\n"
        "Autre : 1234567890123 ; trop court 12345678901 ; trop long 12345678901234"
    )
    assert CasesService.propose_ticket_numbers(text) == ["0572345678901", "1234567890123"]


def test_cases_are_invisible_to_other_agencies(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    with TenancyService.scope(agency_b.id):
        foreign = new_case(agency_b)
    with runtime_role(), TenancyService.scope(agency_a.id):
        assert CasesService.list_cases(agency_a.manager) == []
        with pytest.raises(CaseNotFound):
            CasesService.get_case(agency_a.manager, foreign)


def test_sensitive_actions_are_audited(scoped: AgencyFixture) -> None:
    case_id = new_case(scoped)
    line = air_line(scoped, case_id)
    CasesService.issue_line(scoped.agent, line_id=line.id, issued_on=TODAY)
    CasesService.void_line(scoped.manager, line_id=line.id, voided_on=TODAY)

    events = AuditService.events_for_object(scoped.manager, "case_line", line.id)
    assert [event.action for event in events] == ["line.added", "line.issued", "line.voided"]
    with pytest.raises(PermissionDenied):
        AuditService.events_for_object(scoped.agent, "case_line", line.id)


def closed_paid_case(agency: AgencyFixture) -> tuple[UUID, UUID]:
    case_id = new_case(agency)
    line = air_line(agency, case_id)
    CasesService.issue_line(agency.agent, line_id=line.id, issued_on=TODAY)
    LedgerService.record_payment(
        agency.agent,
        case_id=case_id,
        account=Account.CASH,
        amount_xaf=500_000,
        occurred_on=TODAY,
        idempotency_key="p",
    )
    CasesService.close_case(agency.agent, case_id=case_id)
    return case_id, line.id


def test_a_closed_case_cannot_be_made_inconsistent_by_voiding_a_line(
    scoped: AgencyFixture,
) -> None:
    case_id, line_id = closed_paid_case(scoped)
    with pytest.raises(CaseNotOpen):
        CasesService.void_line(scoped.manager, line_id=line_id, voided_on=TODAY)
    summary = CasesService.get_case(scoped.manager, case_id).summary
    assert (summary.status, summary.balance_xaf) == (CaseStatus.CLOSED, 0)


def test_only_a_manager_reopens_a_closed_case_and_it_is_audited(scoped: AgencyFixture) -> None:
    case_id, line_id = closed_paid_case(scoped)
    with pytest.raises(PermissionDenied):
        CasesService.reopen_case(scoped.agent, case_id=case_id)

    CasesService.reopen_case(scoped.manager, case_id=case_id)
    CasesService.void_line(scoped.manager, line_id=line_id, voided_on=TODAY)

    summary = CasesService.get_case(scoped.manager, case_id).summary
    assert summary.status is CaseStatus.OPEN
    assert summary.balance_xaf == -500_000
    actions = [e.action for e in AuditService.events_for_object(scoped.manager, "case", case_id)]
    assert actions == ["case.created", "case.closed", "case.reopened"]


def test_only_a_closed_case_can_be_reopened(scoped: AgencyFixture) -> None:
    open_case = new_case(scoped)
    with pytest.raises(CaseNotClosed):
        CasesService.reopen_case(scoped.manager, case_id=open_case)
    cancelled = new_case(scoped, name="Annulé")
    CasesService.cancel_case(scoped.manager, case_id=cancelled, cancelled_on=TODAY)
    with pytest.raises(CaseNotClosed):
        CasesService.reopen_case(scoped.manager, case_id=cancelled)


def case_row_locks(operation) -> int:
    with CaptureQueriesContext(connection) as captured:
        operation()
    return sum(1 for q in captured if "FOR UPDATE" in q["sql"] and "cases_case" in q["sql"])


def test_every_state_changing_operation_locks_the_case_row(scoped: AgencyFixture) -> None:
    """Le verrou sérialise les opérations concurrentes sur un même dossier."""
    case_id = new_case(scoped)
    line = air_line(scoped, case_id)
    extra = air_line(scoped, case_id, price=100_000, cost=80_000)

    assert case_row_locks(lambda: air_line(scoped, case_id)) >= 1
    assert (
        case_row_locks(
            lambda: CasesService.issue_line(scoped.agent, line_id=line.id, issued_on=TODAY)
        )
        >= 1
    )
    assert (
        case_row_locks(
            lambda: PaymentsService.record_payment(
                scoped.agent,
                case_id=case_id,
                method=PaymentMethod.CASH,
                amount_xaf=500_000,
                received_on=TODAY,
                idempotency_key="lock-1",
            )
        )
        >= 1
    )
    assert (
        case_row_locks(
            lambda: CasesService.void_line(scoped.manager, line_id=extra.id, voided_on=TODAY)
        )
        >= 1
    )
    assert case_row_locks(lambda: CasesService.close_case(scoped.agent, case_id=case_id)) >= 1
    assert case_row_locks(lambda: CasesService.reopen_case(scoped.manager, case_id=case_id)) >= 1
    CasesService.void_line(scoped.manager, line_id=line.id, voided_on=TODAY)
    assert (
        case_row_locks(
            lambda: CasesService.cancel_case(scoped.manager, case_id=case_id, cancelled_on=TODAY)
        )
        >= 1
    )


def test_reading_a_case_does_not_lock_it(scoped: AgencyFixture) -> None:
    case_id = new_case(scoped)
    assert case_row_locks(lambda: CasesService.get_case(scoped.agent, case_id)) == 0
    assert case_row_locks(lambda: CasesService.list_cases(scoped.agent)) == 0
