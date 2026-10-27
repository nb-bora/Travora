import uuid
from collections.abc import Iterator
from datetime import date

import pytest
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, connection, transaction

from apps.ledger.constants import Account, Direction, TransactionKind
from apps.ledger.dto import PostingLine
from apps.ledger.exceptions import (
    AlreadyReversed,
    CannotReverseReversal,
    IdempotencyConflict,
    InvalidPosting,
    UnbalancedTransaction,
)
from apps.ledger.models import LedgerPosting, LedgerTransaction
from apps.ledger.services import commands
from apps.ledger.services.public import LedgerService
from apps.tenancy.services.public import TenancyService
from tests.conftest import AgencyFixture, runtime_role

TODAY = date(2026, 10, 27)


@pytest.fixture
def case_id() -> uuid.UUID:
    return uuid.uuid7()


@pytest.fixture
def scoped(agency_a: AgencyFixture) -> Iterator[AgencyFixture]:
    with TenancyService.scope(agency_a.id):
        yield agency_a


def sale(agency: AgencyFixture, case_id: uuid.UUID, price: int, cost: int, key: str = "s1"):
    return LedgerService.record_sale(
        agency.agent,
        case_id=case_id,
        price_xaf=price,
        cost_xaf=cost,
        occurred_on=TODAY,
        idempotency_key=key,
    )


def pay(agency: AgencyFixture, case_id: uuid.UUID, amount: int, key: str):
    return LedgerService.record_payment(
        agency.agent,
        case_id=case_id,
        account=Account.MOBILE_MONEY,
        amount_xaf=amount,
        occurred_on=TODAY,
        idempotency_key=key,
    )


def test_a_sale_debits_the_client_and_splits_cost_and_margin(
    scoped: AgencyFixture, case_id: uuid.UUID
) -> None:
    info = sale(scoped, case_id, price=500_000, cost=450_000)

    assert set(info.lines) == {
        PostingLine(Account.CLIENT, Direction.DEBIT, 500_000),
        PostingLine(Account.SUPPLIER, Direction.CREDIT, 450_000),
        PostingLine(Account.MARGIN, Direction.CREDIT, 50_000),
    }
    assert LedgerService.balances_by_case(scoped.agent) == {case_id: 500_000}
    assert LedgerService.margins_by_case(scoped.manager) == {case_id: 50_000}


def test_a_sale_below_cost_books_a_negative_margin(
    scoped: AgencyFixture, case_id: uuid.UUID
) -> None:
    sale(scoped, case_id, price=400_000, cost=450_000)
    assert LedgerService.margins_by_case(scoped.manager) == {case_id: -50_000}
    assert LedgerService.balances_by_case(scoped.agent) == {case_id: 400_000}


def test_a_sale_without_cost_books_the_whole_price_as_margin(
    scoped: AgencyFixture, case_id: uuid.UUID
) -> None:
    info = sale(scoped, case_id, price=25_000, cost=0)
    assert {line.account for line in info.lines} == {Account.CLIENT, Account.MARGIN}
    assert LedgerService.margins_by_case(scoped.manager) == {case_id: 25_000}


def test_payments_reduce_the_balance_and_an_overpayment_makes_it_negative(
    scoped: AgencyFixture, case_id: uuid.UUID
) -> None:
    sale(scoped, case_id, price=500_000, cost=450_000)
    pay(scoped, case_id, 200_000, "p1")
    assert LedgerService.balances_by_case(scoped.agent) == {case_id: 300_000}
    pay(scoped, case_id, 350_000, "p2")
    assert LedgerService.balances_by_case(scoped.agent) == {case_id: -50_000}


def test_the_service_refuses_malformed_entries(scoped: AgencyFixture, case_id: uuid.UUID) -> None:
    def post(*lines: PostingLine) -> None:
        commands.post_transaction(
            case_id=case_id,
            kind=TransactionKind.SALE,
            occurred_on=TODAY,
            lines=lines,
            created_by=None,
        )

    with pytest.raises(UnbalancedTransaction):
        post(
            PostingLine(Account.CLIENT, Direction.DEBIT, 100),
            PostingLine(Account.MARGIN, Direction.CREDIT, 90),
        )
    with pytest.raises(InvalidPosting):
        post(PostingLine(Account.CLIENT, Direction.DEBIT, 100))
    with pytest.raises(InvalidPosting):
        post(
            PostingLine(Account.CLIENT, Direction.DEBIT, 0),
            PostingLine(Account.MARGIN, Direction.CREDIT, 0),
        )
    with pytest.raises(InvalidPosting):
        commands.record_payment(
            case_id=case_id,
            account=Account.MARGIN,
            amount_xaf=100,
            occurred_on=TODAY,
            created_by=None,
            idempotency_key="bad",
        )
    assert LedgerTransaction.objects.count() == 0


def write_unbalanced_entry(agency: AgencyFixture) -> None:
    with TenancyService.scope(agency.id):
        entry = LedgerTransaction.objects.create(
            case_id=uuid.uuid7(), kind=TransactionKind.SALE, occurred_on=TODAY
        )
        LedgerPosting.objects.create(
            transaction=entry, account=Account.CLIENT, direction=Direction.DEBIT, amount_xaf=100
        )


def test_the_database_refuses_an_unbalanced_entry_written_around_the_service(
    agency_a: AgencyFixture,
) -> None:
    with pytest.raises(IntegrityError, match="déséquilibrée"):
        write_unbalanced_entry(agency_a)


def test_the_database_refuses_non_positive_amounts(
    scoped: AgencyFixture, case_id: uuid.UUID
) -> None:
    entry = LedgerTransaction.objects.create(
        case_id=case_id, kind=TransactionKind.SALE, occurred_on=TODAY
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        LedgerPosting.objects.create(
            transaction=entry, account=Account.CLIENT, direction=Direction.DEBIT, amount_xaf=0
        )
    transaction.set_rollback(True)


def test_a_replayed_entry_is_returned_not_duplicated(
    scoped: AgencyFixture, case_id: uuid.UUID
) -> None:
    first = sale(scoped, case_id, price=100_000, cost=80_000, key="same")
    again = sale(scoped, case_id, price=100_000, cost=80_000, key="same")

    assert again.id == first.id
    assert LedgerTransaction.objects.count() == 1
    assert LedgerService.balances_by_case(scoped.agent) == {case_id: 100_000}


def test_an_idempotency_key_cannot_be_reused_for_another_entry(
    scoped: AgencyFixture, case_id: uuid.UUID
) -> None:
    sale(scoped, case_id, price=100_000, cost=80_000, key="same")
    with pytest.raises(IdempotencyConflict):
        sale(scoped, case_id, price=999_000, cost=80_000, key="same")


def test_a_reversal_cancels_the_entry_and_only_once(
    scoped: AgencyFixture, case_id: uuid.UUID
) -> None:
    original = sale(scoped, case_id, price=500_000, cost=450_000)
    reversal = LedgerService.reverse(scoped.manager, transaction_id=original.id, occurred_on=TODAY)

    assert reversal.kind is TransactionKind.REVERSAL
    assert reversal.reverses_id == original.id
    assert LedgerService.balances_by_case(scoped.agent) == {case_id: 0}
    assert LedgerService.margins_by_case(scoped.manager) == {case_id: 0}
    with pytest.raises(AlreadyReversed):
        LedgerService.reverse(scoped.manager, transaction_id=original.id, occurred_on=TODAY)
    with pytest.raises(CannotReverseReversal):
        LedgerService.reverse(scoped.manager, transaction_id=reversal.id, occurred_on=TODAY)


def test_the_database_refuses_a_second_reversal_of_the_same_entry(
    scoped: AgencyFixture, case_id: uuid.UUID
) -> None:
    original = sale(scoped, case_id, price=100, cost=0)
    LedgerService.reverse(scoped.manager, transaction_id=original.id, occurred_on=TODAY)
    entry = LedgerTransaction.objects.get(id=original.id)
    with pytest.raises(IntegrityError), transaction.atomic():
        LedgerTransaction.objects.create(
            case_id=case_id,
            kind=TransactionKind.REVERSAL,
            occurred_on=TODAY,
            reverses=entry,
        )
    transaction.set_rollback(True)


def test_only_a_manager_can_reverse_or_read_margins(
    scoped: AgencyFixture, case_id: uuid.UUID
) -> None:
    original = sale(scoped, case_id, price=100_000, cost=60_000)
    with pytest.raises(PermissionDenied):
        LedgerService.reverse(scoped.agent, transaction_id=original.id, occurred_on=TODAY)
    with pytest.raises(PermissionDenied):
        LedgerService.margins_by_case(scoped.agent)


def test_the_first_sale_date_ignores_reversed_sales(
    scoped: AgencyFixture, case_id: uuid.UUID
) -> None:
    wrong = sale(scoped, case_id, price=100, cost=0, key="wrong")
    LedgerService.reverse(scoped.manager, transaction_id=wrong.id, occurred_on=TODAY)
    assert LedgerService.first_sale_dates(scoped.agent) == {}
    commands.record_sale(
        case_id=case_id,
        price_xaf=100,
        cost_xaf=0,
        occurred_on=date(2026, 11, 2),
        created_by=None,
        idempotency_key="right",
    )
    assert LedgerService.first_sale_dates(scoped.agent) == {case_id: date(2026, 11, 2)}


def test_the_database_refuses_to_alter_a_posting_even_for_the_privileged_role(
    scoped: AgencyFixture, case_id: uuid.UUID
) -> None:
    sale(scoped, case_id, price=100, cost=0)
    with (
        pytest.raises(IntegrityError, match="ajout seul"),
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute("UPDATE ledger_posting SET amount_xaf = amount_xaf + 1")


def test_balances_never_cross_agencies(
    agency_a: AgencyFixture, agency_b: AgencyFixture, case_id: uuid.UUID
) -> None:
    with TenancyService.scope(agency_b.id):
        sale(agency_b, case_id, price=700_000, cost=500_000)
    with runtime_role(), TenancyService.scope(agency_a.id):
        assert LedgerService.balances_by_case(agency_a.agent) == {}
        assert LedgerService.margins_by_case(agency_a.manager) == {}
    with runtime_role(), TenancyService.scope(agency_b.id):
        assert LedgerService.balances_by_case(agency_b.agent) == {case_id: 700_000}
