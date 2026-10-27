from uuid import UUID

from apps.accounts.dto import MembershipInfo
from apps.accounts.models import Membership, User
from apps.shared_kernel.roles import Role


def find_user_id(username: str) -> UUID | None:
    return User.objects.filter(username=username).values_list("id", flat=True).first()


def active_membership(user_id: UUID) -> MembershipInfo | None:
    membership = Membership.objects.filter(user_id=user_id, is_active=True).first()
    if membership is None:
        return None
    return MembershipInfo(
        user_id=membership.user_id, agency_id=membership.agency_id, role=Role(membership.role)
    )
