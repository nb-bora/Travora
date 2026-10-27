from collections.abc import Sequence
from datetime import date, timedelta
from uuid import UUID

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.ledger import selectors
from apps.ledger.constants import TREASURY_ACCOUNTS, Account, Direction, TransactionKind
from apps.ledger.dto import PostingLine, TransactionInfo
from apps.ledger.exceptions import (
    AlreadyReversed,
    CannotReverseReversal,
    DateOutOfRange,
    IdempotencyConflict,
    InvalidClosure,
    InvalidPosting,
    PeriodClosed,
    UnbalancedTransaction,
)
from apps.ledger.models import LedgerPosting, LedgerTransaction, PeriodClosure
from apps.shared_kernel.tenant_context import require_agency_id


def _validate(lines: Sequence[PostingLine]) -> None:
    if len(lines) < 2:
        raise InvalidPosting("Une écriture comporte au moins deux lignes.")
    for line in lines:
        if line.amount_xaf <= 0:
            raise InvalidPosting("Chaque montant est un entier strictement positif.")
    debit = sum(line.amount_xaf for line in lines if line.direction is Direction.DEBIT)
    credit = sum(line.amount_xaf for line in lines if line.direction is Direction.CREDIT)
    if debit != credit:
        raise UnbalancedTransaction(f"Débits ({debit}) et crédits ({credit}) diffèrent.")


def _check_date(occurred_on: date) -> None:
    """Une date comptable n'est ni future, ni trop ancienne, ni dans une période clôturée."""
    today = timezone.localdate()
    if occurred_on > today:
        raise DateOutOfRange("La date d'une écriture ne peut pas être dans le futur.")
    earliest = today - timedelta(days=settings.LEDGER_RETROACTIVITY_DAYS)
    if occurred_on < earliest:
        raise DateOutOfRange(
            f"La date d'une écriture ne remonte pas à plus de "
            f"{settings.LEDGER_RETROACTIVITY_DAYS} jours."
        )
    closed_until = selectors.closed_until()
    if closed_until is not None and occurred_on <= closed_until:
        raise PeriodClosed(f"La période est clôturée jusqu'au {closed_until.isoformat()}.")


def close_period(*, closed_until: date, closed_by: UUID) -> date:
    """Clôture la comptabilité jusqu'à ``closed_until`` inclus. Ne recule jamais."""
    if closed_until > timezone.localdate():
        raise InvalidClosure("On ne clôture pas une période qui n'est pas terminée.")
    current = selectors.closed_until()
    if current is not None and closed_until <= current:
        raise InvalidClosure(f"La période est déjà clôturée jusqu'au {current.isoformat()}.")
    PeriodClosure.objects.create(closed_until=closed_until, closed_by=closed_by)
    return closed_until


def post_transaction(
    *,
    case_id: UUID,
    kind: TransactionKind,
    occurred_on: date,
    lines: Sequence[PostingLine],
    created_by: UUID | None,
    idempotency_key: str | None = None,
    memo: str = "",
    reverses: LedgerTransaction | None = None,
) -> TransactionInfo:
    _validate(lines)
    if idempotency_key is not None:
        existing = selectors.find_by_idempotency_key(idempotency_key)
        if existing is not None:
            return _same_or_conflict(existing, case_id, kind, lines)
    _check_date(occurred_on)
    agency_id = require_agency_id()
    try:
        with transaction.atomic():
            entry = LedgerTransaction.objects.create(
                case_id=case_id,
                kind=kind,
                occurred_on=occurred_on,
                created_by=created_by,
                idempotency_key=idempotency_key or "",
                memo=memo,
                reverses=reverses,
            )
            LedgerPosting.objects.bulk_create(
                LedgerPosting(
                    agency_id=agency_id,
                    transaction=entry,
                    account=line.account,
                    direction=line.direction,
                    amount_xaf=line.amount_xaf,
                )
                for line in lines
            )
    except IntegrityError:
        if idempotency_key is None:
            raise
        existing = selectors.find_by_idempotency_key(idempotency_key)
        if existing is None:
            raise
        return _same_or_conflict(existing, case_id, kind, lines)
    return selectors.to_info(entry)


def _same_or_conflict(
    existing: LedgerTransaction, case_id: UUID, kind: TransactionKind, lines: Sequence[PostingLine]
) -> TransactionInfo:
    info = selectors.to_info(existing)
    same = (
        info.case_id == case_id
        and info.kind == kind
        and sorted(info.lines, key=_line_key) == sorted(lines, key=_line_key)
    )
    if not same:
        raise IdempotencyConflict("Cette clé d'idempotence correspond à une autre écriture.")
    return info


def _line_key(line: PostingLine) -> tuple[str, str, int]:
    return (line.account.value, line.direction.value, line.amount_xaf)


def record_sale(
    *,
    case_id: UUID,
    price_xaf: int,
    cost_xaf: int,
    occurred_on: date,
    created_by: UUID | None,
    idempotency_key: str | None,
) -> TransactionInfo:
    """Vente reconnue : le client doit le prix ; la marge est l'écart entre prix et coût."""
    if price_xaf < 0 or cost_xaf < 0:
        raise InvalidPosting("Prix et coût ne sont jamais négatifs.")
    margin = price_xaf - cost_xaf
    lines = [
        PostingLine(Account.CLIENT, Direction.DEBIT, price_xaf),
        PostingLine(Account.SUPPLIER, Direction.CREDIT, cost_xaf),
    ]
    if margin > 0:
        lines.append(PostingLine(Account.MARGIN, Direction.CREDIT, margin))
    elif margin < 0:
        lines.append(PostingLine(Account.MARGIN, Direction.DEBIT, -margin))
    return post_transaction(
        case_id=case_id,
        kind=TransactionKind.SALE,
        occurred_on=occurred_on,
        lines=[line for line in lines if line.amount_xaf > 0],
        created_by=created_by,
        idempotency_key=idempotency_key,
    )


def record_payment(
    *,
    case_id: UUID,
    account: Account,
    amount_xaf: int,
    occurred_on: date,
    created_by: UUID | None,
    idempotency_key: str | None,
) -> TransactionInfo:
    if account not in TREASURY_ACCOUNTS:
        raise InvalidPosting("Un encaissement entre dans un compte de trésorerie.")
    return post_transaction(
        case_id=case_id,
        kind=TransactionKind.PAYMENT,
        occurred_on=occurred_on,
        lines=[
            PostingLine(account, Direction.DEBIT, amount_xaf),
            PostingLine(Account.CLIENT, Direction.CREDIT, amount_xaf),
        ],
        created_by=created_by,
        idempotency_key=idempotency_key,
    )


def reverse(*, transaction_id: UUID, occurred_on: date, created_by: UUID | None) -> TransactionInfo:
    original = selectors.get_transaction(transaction_id)
    if original.kind == TransactionKind.REVERSAL:
        raise CannotReverseReversal("Une contre-passation ne se contre-passe pas.")
    if hasattr(original, "reversed_by"):
        raise AlreadyReversed(str(transaction_id))
    info = selectors.to_info(original)
    opposite = {Direction.DEBIT: Direction.CREDIT, Direction.CREDIT: Direction.DEBIT}
    return post_transaction(
        case_id=info.case_id,
        kind=TransactionKind.REVERSAL,
        occurred_on=occurred_on,
        lines=[
            PostingLine(line.account, opposite[line.direction], line.amount_xaf)
            for line in info.lines
        ],
        created_by=created_by,
        idempotency_key=f"reversal:{transaction_id}",
        reverses=original,
    )
