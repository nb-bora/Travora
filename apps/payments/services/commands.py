from datetime import date
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services.public import AuditService
from apps.cases.services.public import CasesService
from apps.ledger.services.public import LedgerService
from apps.payments import selectors
from apps.payments.constants import ACCOUNT_BY_METHOD, PaymentMethod
from apps.payments.dto import PaymentView
from apps.payments.exceptions import (
    DuplicateReference,
    IdempotencyConflict,
    InvalidPayment,
    PaymentAlreadyVoided,
)
from apps.payments.models import Payment
from apps.shared_kernel.actor import Actor


def _replay(
    payment: Payment, case_id: UUID, method: PaymentMethod, amount_xaf: int, reference: str
) -> PaymentView:
    same = (
        payment.case_id == case_id
        and payment.method == method
        and payment.amount_xaf == amount_xaf
        and payment.reference == reference
    )
    if not same:
        raise IdempotencyConflict("Cette clé d'idempotence correspond à un autre paiement.")
    return selectors.to_view(payment)


def record_payment(
    actor: Actor,
    *,
    case_id: UUID,
    method: PaymentMethod,
    amount_xaf: int,
    reference: str,
    received_on: date,
    idempotency_key: str,
) -> PaymentView:
    reference = reference.strip()
    if amount_xaf <= 0:
        raise InvalidPayment("Le montant est un entier strictement positif.")
    if method is not PaymentMethod.CASH and not reference:
        raise InvalidPayment("Une référence est obligatoire hors espèces.")
    if not idempotency_key:
        raise InvalidPayment("Une clé d'idempotence est obligatoire.")
    CasesService.require_open_case(actor, case_id)

    existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
    if existing is not None:
        return _replay(existing, case_id, method, amount_xaf, reference)
    if reference and Payment.objects.filter(reference=reference, voided_at__isnull=True).exists():
        raise DuplicateReference(reference)

    try:
        with transaction.atomic():
            payment = Payment.objects.create(
                case_id=case_id,
                method=method,
                amount_xaf=amount_xaf,
                reference=reference,
                received_on=received_on,
                idempotency_key=idempotency_key,
                recorded_by=actor.user_id,
            )
            entry = LedgerService.record_payment(
                actor,
                case_id=case_id,
                account=ACCOUNT_BY_METHOD[method],
                amount_xaf=amount_xaf,
                occurred_on=received_on,
                idempotency_key=f"payment:{payment.id}",
            )
            payment.ledger_transaction_id = entry.id
            payment.save()
    except IntegrityError:
        replay = Payment.objects.filter(idempotency_key=idempotency_key).first()
        if replay is None:
            raise
        return _replay(replay, case_id, method, amount_xaf, reference)

    AuditService.record(
        actor_user_id=actor.user_id,
        action="payment.recorded",
        object_type="payment",
        object_id=payment.id,
        metadata={"case_id": str(case_id), "method": method.value, "amount_xaf": amount_xaf},
    )
    return selectors.to_view(payment)


def void_payment(actor: Actor, *, payment_id: UUID, voided_on: date) -> PaymentView:
    actor.require_manager()
    payment = selectors.get_payment(payment_id)
    CasesService.require_open_case(actor, payment.case_id)
    if payment.voided_at is not None or payment.ledger_transaction_id is None:
        raise PaymentAlreadyVoided(str(payment_id))
    LedgerService.reverse(
        actor, transaction_id=payment.ledger_transaction_id, occurred_on=voided_on
    )
    payment.voided_at = timezone.now()
    payment.save()
    AuditService.record(
        actor_user_id=actor.user_id,
        action="payment.voided",
        object_type="payment",
        object_id=payment.id,
        metadata={"case_id": str(payment.case_id), "amount_xaf": payment.amount_xaf},
    )
    return selectors.to_view(payment)
