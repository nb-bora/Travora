from dataclasses import dataclass
from datetime import date
from uuid import UUID

from apps.ledger.constants import Account, Direction, TransactionKind


@dataclass(frozen=True)
class PostingLine:
    account: Account
    direction: Direction
    amount_xaf: int


@dataclass(frozen=True)
class TransactionInfo:
    id: UUID
    case_id: UUID
    kind: TransactionKind
    occurred_on: date
    lines: tuple[PostingLine, ...]
    reverses_id: UUID | None
