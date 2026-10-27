from django.db import models

from apps.shared_kernel.models import TenantScopedModel


class Customer(TenantScopedModel):
    """Client payeur d'un dossier. Le téléphone est au format E.164."""

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=16, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "crm_customer"
        constraints = [
            models.UniqueConstraint(
                fields=["agency", "phone"],
                condition=~models.Q(phone=""),
                name="customer_phone_unique_per_agency",
            ),
        ]
        indexes = [models.Index(fields=["agency", "name"], name="customer_agency_name_idx")]

    def __str__(self) -> str:
        return self.name
