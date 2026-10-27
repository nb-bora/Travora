from collections.abc import Mapping
from typing import Any
from uuid import UUID

from apps.audit.models import AuditEvent


def record(
    *,
    actor_user_id: UUID | None,
    action: str,
    object_type: str,
    object_id: UUID,
    metadata: Mapping[str, Any] | None = None,
) -> None:
    AuditEvent.objects.create(
        actor_user_id=actor_user_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        metadata=dict(metadata or {}),
    )
