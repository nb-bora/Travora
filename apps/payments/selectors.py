from datetime import date
from uuid import UUID

from django.db.models import Count, Sum

from apps.payments.constants import PaymentMethod
from apps.payments.dto import MethodTotal, PaymentView
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


def totals_by_method(*, start: date, end: date) -> list[MethodTotal]:
    """Encaissements non annulés reçus dans [start, end], par mode de paiement."""
    rows = (
        Payment.objects.filter(voided_at__isnull=True, received_on__gte=start, received_on__lte=end)
        .values("method")
        .annotate(count=Count("id"), amount=Sum("amount_xaf"))
        .order_by("method")
    )
    return [
        MethodTotal(PaymentMethod(row["method"]), row["count"], row["amount"] or 0) for row in rows
    ]
