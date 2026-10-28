from dataclasses import dataclass
from datetime import date
from uuid import UUID

from apps.payments.constants import PaymentMethod


@dataclass(frozen=True)
class PaymentView:
    id: UUID
    case_id: UUID
    method: PaymentMethod
    amount_xaf: int
    reference: str
    received_on: date
    is_voided: bool


@dataclass(frozen=True)
class MethodTotal:
    method: PaymentMethod
    count: int
    amount_xaf: int
