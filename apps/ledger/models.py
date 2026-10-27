from django.db import models

from apps.ledger.constants import Account, Direction, TransactionKind
from apps.shared_kernel.append_only import AppendOnlyModel


class LedgerTransaction(AppendOnlyModel):
    """Écriture comptable d'un dossier. Immuable : une erreur se corrige par contre-passation."""

    case_id = models.UUIDField(db_index=True)
    kind = models.CharField(max_length=16, choices=TransactionKind.choices)
    occurred_on = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=64, blank=True, default="")
    memo = models.CharField(max_length=200, blank=True)
    reverses = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reversed_by",
    )

    class Meta:
        db_table = "ledger_transaction"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(kind__in=TransactionKind.values),
                name="ledger_transaction_kind_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(kind=TransactionKind.REVERSAL, reverses__isnull=False)
                    | (~models.Q(kind=TransactionKind.REVERSAL) & models.Q(reverses__isnull=True))
                ),
                name="ledger_transaction_reversal_links_original",
            ),
            models.UniqueConstraint(
                fields=["agency", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="ledger_transaction_idempotency_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["agency", "case_id"], name="ledger_tx_agency_case_idx"),
            models.Index(fields=["agency", "occurred_on"], name="ledger_tx_agency_date_idx"),
        ]


class LedgerPosting(AppendOnlyModel):
    """Ligne d'une écriture : un montant entier en XAF, au débit ou au crédit d'un compte."""

    transaction = models.ForeignKey(
        LedgerTransaction, on_delete=models.PROTECT, related_name="postings"
    )
    account = models.CharField(max_length=16, choices=Account.choices)
    direction = models.CharField(max_length=8, choices=Direction.choices)
    amount_xaf = models.BigIntegerField()

    class Meta:
        db_table = "ledger_posting"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_xaf__gt=0), name="ledger_posting_amount_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(account__in=Account.values), name="ledger_posting_account_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(direction__in=Direction.values),
                name="ledger_posting_direction_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["agency", "transaction"], name="ledger_posting_tx_idx"),
            models.Index(fields=["agency", "account"], name="ledger_posting_account_idx"),
        ]
