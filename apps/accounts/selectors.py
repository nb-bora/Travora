from uuid import UUID

from apps.accounts.dto import MemberInfo, MembershipInfo
from apps.accounts.models import Membership, User
from apps.shared_kernel.roles import Role


def find_user_id(username: str) -> UUID | None:
    return User.objects.filter(username=username).values_list("id", flat=True).first()


def active_membership(user_id: UUID) -> MembershipInfo | None:
    membership = Membership.by_user.filter(user_id=user_id, is_active=True).first()
    if membership is None:
        return None
    return MembershipInfo(
        user_id=membership.user_id, agency_id=membership.agency_id, role=Role(membership.role)
    )


def team() -> list[MemberInfo]:
    """Membres de l'agence courante (la RLS borne la requête), gérants d'abord."""
    rows = Membership.objects.select_related("user").order_by("created_at")
    members = [
        MemberInfo(
            user_id=row.user_id,
            username=row.user.username,
            role=Role(row.role),
            is_active=row.is_active,
            joined_at=row.created_at,
        )
        for row in rows
    ]
    return sorted(members, key=lambda member: member.role is not Role.MANAGER)
