from django.db import models

from apps.cases.constants import CaseStatus, LineKind
from apps.shared_kernel.models import TenantScopedModel


class Case(TenantScopedModel):
    """Dossier commercial d'un client. Son état financier est dérivé du journal."""

    customer = models.ForeignKey("crm.Customer", on_delete=models.PROTECT, related_name="+")
    reference = models.CharField(max_length=32)
    status = models.CharField(max_length=16, choices=CaseStatus.choices, default=CaseStatus.OPEN)
    departure_date = models.DateField(null=True, blank=True)
    created_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cases_case"
        constraints = [
            models.UniqueConstraint(fields=["agency", "reference"], name="case_reference_unique"),
            models.CheckConstraint(
                condition=models.Q(status__in=CaseStatus.values), name="case_status_valid"
            ),
        ]
        indexes = [
            models.Index(fields=["agency", "status"], name="case_agency_status_idx"),
            models.Index(fields=["agency", "departure_date"], name="case_agency_departure_idx"),
        ]


class CaseLine(TenantScopedModel):
    """Ligne vendue : un billet d'avion ou une prestation libre.

    Le coût reste inconnu (``NULL``) tant qu'il n'a pas été saisi : une ligne ne peut pas
    être émise sans lui, pour ne jamais afficher une fausse marge.
    """

    case = models.ForeignKey(Case, on_delete=models.PROTECT, related_name="lines")
    kind = models.CharField(max_length=16, choices=LineKind.choices)
    label = models.CharField(max_length=200)
    passenger_name = models.CharField(max_length=200, blank=True)
    ticket_number = models.CharField(max_length=32, blank=True)
    price_xaf = models.BigIntegerField()
    cost_xaf = models.BigIntegerField(null=True, blank=True)
    raw_text = models.TextField(blank=True)
    issued_on = models.DateField(null=True, blank=True)
    sale_transaction_id = models.UUIDField(null=True, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cases_line"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(kind__in=LineKind.values), name="case_line_kind_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(price_xaf__gte=0), name="case_line_price_not_negative"
            ),
            models.CheckConstraint(
                condition=models.Q(cost_xaf__isnull=True) | models.Q(cost_xaf__gte=0),
                name="case_line_cost_not_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(issued_on__isnull=True) | models.Q(cost_xaf__isnull=False),
                name="case_line_issued_has_cost",
            ),
            models.CheckConstraint(
                condition=models.Q(kind=LineKind.AIR_TICKET) | models.Q(ticket_number=""),
                name="case_line_ticket_only_for_air",
            ),
            models.UniqueConstraint(
                fields=["agency", "ticket_number"],
                condition=~models.Q(ticket_number="") & models.Q(voided_at__isnull=True),
                name="case_line_ticket_unique_per_agency",
            ),
        ]
        indexes = [models.Index(fields=["agency", "case"], name="case_line_agency_case_idx")]
