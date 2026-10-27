import uuid
from typing import Any

from django.db import models

from apps.shared_kernel.tenant_context import (
    TenantContextMissing,
    TenantMismatch,
    current_agency_id,
)


class TenantScopedModel(models.Model):
    """Table du plan de données : chaque ligne appartient à une agence."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    agency = models.ForeignKey(
        "tenancy.Agency", on_delete=models.PROTECT, editable=False, related_name="+"
    )

    class Meta:
        abstract = True

    def save(self, *args: Any, **kwargs: Any) -> None:
        current = current_agency_id()
        if self.agency_id is None:
            if current is None:
                raise TenantContextMissing(f"{type(self).__name__} sans agence dans le contexte.")
            self.agency_id = current
        elif current is not None and self.agency_id != current:
            raise TenantMismatch(f"{type(self).__name__} appartient à une autre agence.")
        super().save(*args, **kwargs)
