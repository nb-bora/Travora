from uuid import UUID

from apps.accounts.dto import MembershipInfo
from apps.accounts.models import Membership, User
from apps.audit.services.public import AuditService
from apps.shared_kernel.actor import Actor
from apps.shared_kernel.roles import Role


def _create(*, username: str, password: str, role: Role, created_by: UUID | None) -> MembershipInfo:
    user = User.objects.create_user(username=username, password=password)
    membership = Membership.objects.create(user=user, role=role)
    AuditService.record(
        actor_user_id=created_by,
        action="member.created",
        object_type="membership",
        object_id=membership.id,
        metadata={"username": username, "role": role.value},
    )
    return MembershipInfo(user_id=user.id, agency_id=membership.agency_id, role=role)


def create_first_manager(*, username: str, password: str) -> MembershipInfo:
    return _create(username=username, password=password, role=Role.MANAGER, created_by=None)


def create_member(actor: Actor, *, username: str, password: str, role: Role) -> MembershipInfo:
    actor.require_manager()
    return _create(username=username, password=password, role=role, created_by=actor.user_id)
