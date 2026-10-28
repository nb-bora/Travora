import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.shared_kernel.models import TenantScopedModel
from apps.shared_kernel.roles import Role


class User(AbstractUser):
    """Identité globale : résolue avant de connaître l'agence, donc hors RLS."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)


class Membership(TenantScopedModel):
    """Appartenance d'un utilisateur à une agence, avec son rôle (une agence par utilisateur)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="membership"
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Résolution de l'agence d'un utilisateur avant que l'agence soit connue : la RLS
    # n'expose alors que sa propre ligne (variable ``app.user_id``).
    by_user = models.Manager["Membership"]()

    class Meta:
        db_table = "accounts_membership"
        default_manager_name = "objects"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=Role.values), name="membership_role_valid"
            ),
        ]
        indexes = [models.Index(fields=["agency", "role"], name="membership_agency_role_idx")]


class LoginFailure(models.Model):
    """Échec de connexion : sert à ralentir les devinettes de mot de passe.

    Table globale comme ``User`` : l'identité se vérifie avant de connaître l'agence.
    """

    username = models.CharField(max_length=150, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "accounts_login_failure"

    def __str__(self) -> str:
        return f"{self.username} @ {self.created_at:%Y-%m-%d %H:%M}"
