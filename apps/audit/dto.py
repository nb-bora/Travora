from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class AuditEventInfo:
    id: UUID
    actor_user_id: UUID | None
    action: str
    object_type: str
    object_id: UUID
    metadata: dict[str, Any]
    created_at: datetime
