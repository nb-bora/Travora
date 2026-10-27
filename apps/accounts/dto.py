from dataclasses import dataclass
from uuid import UUID

from apps.shared_kernel.roles import Role


@dataclass(frozen=True)
class MembershipInfo:
    user_id: UUID
    agency_id: UUID
    role: Role
