from django.db import models

from apps.shared_kernel.append_only import AppendOnlyModel


class AuditEvent(AppendOnlyModel):
    """Trace d'une action sensible. Ajout seul : jamais modifiée ni supprimée."""

    actor_user_id = models.UUIDField(null=True, blank=True)
    action = models.CharField(max_length=64)
    object_type = models.CharField(max_length=64)
    object_id = models.UUIDField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_event"
        indexes = [
            models.Index(fields=["agency", "-created_at"], name="audit_agency_created_idx"),
            models.Index(
                fields=["agency", "object_type", "object_id"], name="audit_agency_object_idx"
            ),
        ]
