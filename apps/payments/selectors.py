from uuid import UUID

from apps.payments.constants import PaymentMethod
from apps.payments.dto import PaymentView
from apps.payments.exceptions import PaymentNotFound
from apps.payments.models import Payment


def to_view(payment: Payment) -> PaymentView:
    return PaymentView(
        id=payment.id,
        case_id=payment.case_id,
        method=PaymentMethod(payment.method),
        amount_xaf=payment.amount_xaf,
        reference=payment.reference,
        received_on=payment.received_on,
        is_voided=payment.voided_at is not None,
    )


def get_payment(payment_id: UUID) -> Payment:
    payment = Payment.objects.filter(id=payment_id).first()
    if payment is None:
        raise PaymentNotFound(str(payment_id))
    return payment


def payments_for_case(case_id: UUID) -> list[PaymentView]:
    return [
        to_view(payment)
        for payment in Payment.objects.filter(case_id=case_id).order_by("received_on", "id")
    ]
