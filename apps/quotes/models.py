from typing import Any

from django.db import models

from apps.quotes.constants import QuoteStatus
from apps.quotes.exceptions import QuoteFrozen
from apps.shared_kernel.models import TenantScopedModel

FROZEN_FIELDS = ("case_id", "version", "valid_until", "lines")


class Quote(TenantScopedModel):
    """Devis versionné. Il ne contient que ce que le client voit : jamais coût ni marge.

    Dès l'envoi, la version est figée : une modification passe par une nouvelle version.
    """

    case = models.ForeignKey("cases.Case", on_delete=models.PROTECT, related_name="+")
    version = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=QuoteStatus.choices, default=QuoteStatus.DRAFT)
    valid_until = models.DateField()
    lines = models.JSONField()
    sent_at = models.DateTimeField(null=True, blank=True)
    created_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "quotes_quote"
        constraints = [
            models.UniqueConstraint(
                fields=["agency", "case", "version"], name="quote_version_unique_per_case"
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=QuoteStatus.values), name="quote_status_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(status=QuoteStatus.DRAFT) | models.Q(sent_at__isnull=False),
                name="quote_sent_has_date",
            ),
        ]
        indexes = [models.Index(fields=["agency", "case"], name="quote_agency_case_idx")]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            stored = Quote.objects.filter(pk=self.pk).values(*FROZEN_FIELDS, "sent_at").first()
            if stored is not None and stored["sent_at"] is not None:
                changed = [name for name in FROZEN_FIELDS if stored[name] != getattr(self, name)]
                if changed:
                    raise QuoteFrozen(f"Devis envoyé : {', '.join(changed)} ne se modifie plus.")
        super().save(*args, **kwargs)
