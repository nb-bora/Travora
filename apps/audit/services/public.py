"""Façade publique de l'application audit."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from apps.audit import selectors
from apps.audit.dto import AuditEventInfo
from apps.audit.services import commands
from apps.shared_kernel.actor import Actor


class AuditService:
    @staticmethod
    def record(
        *,
        actor_user_id: UUID | None,
        action: str,
        object_type: str,
        object_id: UUID,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        commands.record(
            actor_user_id=actor_user_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            metadata=metadata,
        )

    @staticmethod
    def events_for_object(actor: Actor, object_type: str, object_id: UUID) -> list[AuditEventInfo]:
        actor.require_manager()
        return selectors.events_for_object(object_type, object_id)
