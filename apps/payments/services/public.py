"""Façade publique de l'application payments."""

from datetime import date
from uuid import UUID

from apps.payments import selectors
from apps.payments.constants import PaymentMethod
from apps.payments.dto import MethodTotal, PaymentView
from apps.payments.services import commands
from apps.shared_kernel.actor import Actor


class PaymentsService:
    @staticmethod
    def record_payment(
        actor: Actor,
        *,
        case_id: UUID,
        method: PaymentMethod,
        amount_xaf: int,
        received_on: date,
        idempotency_key: str,
        reference: str = "",
    ) -> PaymentView:
        return commands.record_payment(
            actor,
            case_id=case_id,
            method=method,
            amount_xaf=amount_xaf,
            reference=reference,
            received_on=received_on,
            idempotency_key=idempotency_key,
        )

    @staticmethod
    def void_payment(actor: Actor, *, payment_id: UUID, voided_on: date) -> PaymentView:
        return commands.void_payment(actor, payment_id=payment_id, voided_on=voided_on)

    @staticmethod
    def payments_for_case(actor: Actor, case_id: UUID) -> list[PaymentView]:
        return selectors.payments_for_case(case_id)

    @staticmethod
    def totals_by_method(actor: Actor, *, start: date, end: date) -> list[MethodTotal]:
        return selectors.totals_by_method(start=start, end=end)
