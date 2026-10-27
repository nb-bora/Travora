import uuid

from django.db import models


class Agency(models.Model):
    """Racine de l'isolation : tout le plan de données appartient à une agence."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=64, unique=True)
    logo = models.ImageField(upload_to="agency_logos/", blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tenancy_agency"

    def __str__(self) -> str:
        return self.name
