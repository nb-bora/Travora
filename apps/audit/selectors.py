from uuid import UUID

from apps.audit.dto import AuditEventInfo
from apps.audit.models import AuditEvent


def events_for_object(object_type: str, object_id: UUID) -> list[AuditEventInfo]:
    events = AuditEvent.objects.filter(object_type=object_type, object_id=object_id).order_by(
        "created_at", "id"
    )
    return [
        AuditEventInfo(
            id=event.id,
            actor_user_id=event.actor_user_id,
            action=event.action,
            object_type=event.object_type,
            object_id=event.object_id,
            metadata=event.metadata,
            created_at=event.created_at,
        )
        for event in events
    ]
