from datetime import date
from uuid import UUID

from django.db.models import BigIntegerField, Case, F, Min, Sum, When

from apps.ledger.constants import Account, Direction, TransactionKind
from apps.ledger.dto import PostingLine, TransactionInfo
from apps.ledger.exceptions import TransactionNotFound
from apps.ledger.models import LedgerPosting, LedgerTransaction

DEBIT_POSITIVE = Case(
    When(direction=Direction.DEBIT, then=F("amount_xaf")),
    default=-F("amount_xaf"),
    output_field=BigIntegerField(),
)
CREDIT_POSITIVE = Case(
    When(direction=Direction.CREDIT, then=F("amount_xaf")),
    default=-F("amount_xaf"),
    output_field=BigIntegerField(),
)


def to_info(transaction: LedgerTransaction) -> TransactionInfo:
    return TransactionInfo(
        id=transaction.id,
        case_id=transaction.case_id,
        kind=TransactionKind(transaction.kind),
        occurred_on=transaction.occurred_on,
        lines=tuple(
            PostingLine(Account(p.account), Direction(p.direction), p.amount_xaf)
            for p in transaction.postings.order_by("id")
        ),
        reverses_id=transaction.reverses_id,
    )


def get_transaction(transaction_id: UUID) -> LedgerTransaction:
    transaction = LedgerTransaction.objects.filter(id=transaction_id).first()
    if transaction is None:
        raise TransactionNotFound(str(transaction_id))
    return transaction


def find_by_idempotency_key(key: str) -> LedgerTransaction | None:
    return LedgerTransaction.objects.filter(idempotency_key=key).first()


def balances_by_case() -> dict[UUID, int]:
    """Montant que le client doit encore : débits moins crédits du compte client."""
    rows = (
        LedgerPosting.objects.filter(account=Account.CLIENT)
        .values("transaction__case_id")
        .annotate(total=Sum(DEBIT_POSITIVE))
    )
    return {row["transaction__case_id"]: row["total"] for row in rows}


def margins_by_case() -> dict[UUID, int]:
    rows = (
        LedgerPosting.objects.filter(account=Account.MARGIN)
        .values("transaction__case_id")
        .annotate(total=Sum(CREDIT_POSITIVE))
    )
    return {row["transaction__case_id"]: row["total"] for row in rows}


def first_sale_dates() -> dict[UUID, date]:
    """Date de la première vente non annulée de chaque dossier."""
    rows = (
        LedgerTransaction.objects.filter(kind=TransactionKind.SALE, reversed_by__isnull=True)
        .values("case_id")
        .annotate(first=Min("occurred_on"))
    )
    return {row["case_id"]: row["first"] for row in rows}
