from django.db import models

from apps.payments.constants import PaymentMethod
from apps.shared_kernel.models import TenantScopedModel


class Payment(TenantScopedModel):
    """Encaissement saisi par l'agence. Le solde du dossier est calculé par le journal."""

    case = models.ForeignKey("cases.Case", on_delete=models.PROTECT, related_name="+")
    method = models.CharField(max_length=16, choices=PaymentMethod.choices)
    amount_xaf = models.BigIntegerField()
    reference = models.CharField(max_length=100, blank=True)
    received_on = models.DateField()
    idempotency_key = models.CharField(max_length=64)
    recorded_by = models.UUIDField(null=True, blank=True)
    ledger_transaction_id = models.UUIDField(null=True, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payments_payment"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_xaf__gt=0), name="payment_amount_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(method__in=PaymentMethod.values), name="payment_method_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(method=PaymentMethod.CASH) | ~models.Q(reference=""),
                name="payment_reference_required_unless_cash",
            ),
            models.UniqueConstraint(
                fields=["agency", "reference"],
                condition=~models.Q(reference="") & models.Q(voided_at__isnull=True),
                name="payment_reference_unique_per_agency",
            ),
            models.UniqueConstraint(
                fields=["agency", "idempotency_key"], name="payment_idempotency_unique"
            ),
        ]
        indexes = [models.Index(fields=["agency", "case"], name="payment_agency_case_idx")]
