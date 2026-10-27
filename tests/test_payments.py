from collections.abc import Iterator
from datetime import date
from uuid import UUID

import pytest
from django.core.exceptions import PermissionDenied

from apps.audit.services.public import AuditService
from apps.cases.constants import LineKind
from apps.cases.exceptions import CaseNotFound, CaseNotOpen
from apps.cases.services.public import CasesService
from apps.crm.services.public import CrmService
from apps.ledger.services.public import LedgerService
from apps.payments.constants import PaymentMethod
from apps.payments.exceptions import (
    DuplicateReference,
    IdempotencyConflict,
    InvalidPayment,
    PaymentAlreadyVoided,
)
from apps.payments.services.public import PaymentsService
from apps.tenancy.services.public import TenancyService
from tests.conftest import AgencyFixture, runtime_role

TODAY = date(2026, 10, 27)


@pytest.fixture
def scoped(agency_a: AgencyFixture) -> Iterator[AgencyFixture]:
    with TenancyService.scope(agency_a.id):
        yield agency_a


def issued_case(agency: AgencyFixture, price: int = 500_000) -> UUID:
    customer = CrmService.find_or_create_customer(agency.agent, name="Marie", phone="")
    case_id = CasesService.create_case(agency.agent, customer_id=customer.id)
    line = CasesService.add_line(
        agency.agent,
        case_id=case_id,
        kind=LineKind.AIR_TICKET,
        label="DLA-CDG",
        price_xaf=price,
        cost_xaf=price - 50_000,
    )
    CasesService.issue_line(agency.agent, line_id=line.id, issued_on=TODAY)
    return case_id


def pay(agency: AgencyFixture, case_id: UUID, amount: int, key: str, **kw):
    return PaymentsService.record_payment(
        agency.agent,
        case_id=case_id,
        method=kw.pop("method", PaymentMethod.CASH),
        amount_xaf=amount,
        received_on=TODAY,
        idempotency_key=key,
        **kw,
    )


def balance(agency: AgencyFixture, case_id: UUID) -> int:
    return CasesService.get_case(agency.agent, case_id).summary.balance_xaf


def test_payments_reduce_the_balance_through_the_ledger(scoped: AgencyFixture) -> None:
    case_id = issued_case(scoped)
    pay(scoped, case_id, 200_000, "k1")
    pay(scoped, case_id, 100_000, "k2", method=PaymentMethod.MOBILE_MONEY, reference="MP-001")

    assert balance(scoped, case_id) == 200_000
    assert LedgerService.balances_by_case(scoped.agent) == {case_id: 200_000}
    assert [p.amount_xaf for p in PaymentsService.payments_for_case(scoped.agent, case_id)] == [
        200_000,
        100_000,
    ]


def test_an_overpayment_leaves_a_credit_instead_of_failing(scoped: AgencyFixture) -> None:
    case_id = issued_case(scoped)
    pay(scoped, case_id, 600_000, "k1")
    assert balance(scoped, case_id) == -100_000


def test_a_reference_is_required_unless_the_payment_is_in_cash(scoped: AgencyFixture) -> None:
    case_id = issued_case(scoped)
    pay(scoped, case_id, 10_000, "cash-ok")
    for method in (PaymentMethod.TRANSFER, PaymentMethod.MOBILE_MONEY):
        with pytest.raises(InvalidPayment):
            pay(scoped, case_id, 10_000, f"k-{method}", method=method)


def test_amounts_and_keys_are_validated(scoped: AgencyFixture) -> None:
    case_id = issued_case(scoped)
    for amount in (0, -5):
        with pytest.raises(InvalidPayment):
            pay(scoped, case_id, amount, "k")
    with pytest.raises(InvalidPayment):
        pay(scoped, case_id, 10, "")


def test_the_same_external_reference_cannot_be_recorded_twice(scoped: AgencyFixture) -> None:
    case_id = issued_case(scoped)
    pay(scoped, case_id, 50_000, "k1", method=PaymentMethod.MOBILE_MONEY, reference="MP-777")
    with pytest.raises(DuplicateReference):
        pay(scoped, case_id, 50_000, "k2", method=PaymentMethod.MOBILE_MONEY, reference="MP-777")
    assert balance(scoped, case_id) == 450_000


def test_a_voided_payment_frees_its_reference(scoped: AgencyFixture) -> None:
    case_id = issued_case(scoped)
    first = pay(scoped, case_id, 50_000, "k1", method=PaymentMethod.TRANSFER, reference="VIR-1")
    PaymentsService.void_payment(scoped.manager, payment_id=first.id, voided_on=TODAY)
    pay(scoped, case_id, 50_000, "k2", method=PaymentMethod.TRANSFER, reference="VIR-1")
    assert balance(scoped, case_id) == 450_000


def test_the_same_reference_may_exist_in_two_agencies(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    for agency in (agency_a, agency_b):
        with TenancyService.scope(agency.id):
            case_id = issued_case(agency)
            pay(agency, case_id, 1_000, "k", method=PaymentMethod.MOBILE_MONEY, reference="MP-1")


def test_a_replay_returns_the_same_payment_and_books_it_once(scoped: AgencyFixture) -> None:
    case_id = issued_case(scoped)
    first = pay(scoped, case_id, 200_000, "same")
    again = pay(scoped, case_id, 200_000, "same")

    assert again.id == first.id
    assert balance(scoped, case_id) == 300_000
    assert len(PaymentsService.payments_for_case(scoped.agent, case_id)) == 1


def test_a_key_cannot_be_reused_for_a_different_payment(scoped: AgencyFixture) -> None:
    case_id = issued_case(scoped)
    pay(scoped, case_id, 200_000, "same")
    with pytest.raises(IdempotencyConflict):
        pay(scoped, case_id, 999, "same")


def test_a_closed_case_refuses_payments(scoped: AgencyFixture) -> None:
    case_id = issued_case(scoped)
    pay(scoped, case_id, 500_000, "k1")
    CasesService.close_case(scoped.agent, case_id=case_id)
    with pytest.raises(CaseNotOpen):
        pay(scoped, case_id, 1, "k2")


def test_voiding_is_for_managers_and_restores_the_balance(scoped: AgencyFixture) -> None:
    case_id = issued_case(scoped)
    payment = pay(scoped, case_id, 200_000, "k1")

    with pytest.raises(PermissionDenied):
        PaymentsService.void_payment(scoped.agent, payment_id=payment.id, voided_on=TODAY)
    voided = PaymentsService.void_payment(scoped.manager, payment_id=payment.id, voided_on=TODAY)

    assert voided.is_voided
    assert balance(scoped, case_id) == 500_000
    with pytest.raises(PaymentAlreadyVoided):
        PaymentsService.void_payment(scoped.manager, payment_id=payment.id, voided_on=TODAY)


def test_payments_are_audited(scoped: AgencyFixture) -> None:
    case_id = issued_case(scoped)
    payment = pay(scoped, case_id, 200_000, "k1")
    PaymentsService.void_payment(scoped.manager, payment_id=payment.id, voided_on=TODAY)
    events = AuditService.events_for_object(scoped.manager, "payment", payment.id)
    assert [event.action for event in events] == ["payment.recorded", "payment.voided"]


def test_a_payment_needs_an_existing_case_of_the_agency(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    with TenancyService.scope(agency_b.id):
        foreign_case = issued_case(agency_b)
    with runtime_role(), TenancyService.scope(agency_a.id):
        with pytest.raises(CaseNotFound):
            pay(agency_a, foreign_case, 1_000, "k")
        assert PaymentsService.payments_for_case(agency_a.agent, foreign_case) == []


def test_a_closed_case_cannot_be_made_inconsistent_by_voiding_a_payment(
    scoped: AgencyFixture,
) -> None:
    case_id = issued_case(scoped)
    payment = pay(scoped, case_id, 500_000, "k1")
    CasesService.close_case(scoped.agent, case_id=case_id)

    with pytest.raises(CaseNotOpen):
        PaymentsService.void_payment(scoped.manager, payment_id=payment.id, voided_on=TODAY)
    assert balance(scoped, case_id) == 0

    CasesService.reopen_case(scoped.manager, case_id=case_id)
    PaymentsService.void_payment(scoped.manager, payment_id=payment.id, voided_on=TODAY)
    assert balance(scoped, case_id) == 500_000
