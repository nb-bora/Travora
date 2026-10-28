from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from apps.shared_kernel.roles import Role


@dataclass(frozen=True)
class MembershipInfo:
    user_id: UUID
    agency_id: UUID
    role: Role


@dataclass(frozen=True)
class MemberInfo:
    user_id: UUID
    username: str
    role: Role
    is_active: bool
    joined_at: datetime
