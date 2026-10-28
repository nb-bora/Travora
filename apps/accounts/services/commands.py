from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone

from apps.accounts.dto import MembershipInfo
from apps.accounts.models import LoginFailure, Membership, User
from apps.audit.services.public import AuditService
from apps.shared_kernel.actor import Actor
from apps.shared_kernel.roles import Role


def _create(*, username: str, password: str, role: Role, created_by: UUID | None) -> MembershipInfo:
    validate_password(password)
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


def record_login_failure(*, username: str, ip_address: str | None) -> None:
    cutoff = timezone.now() - timedelta(days=1)
    LoginFailure.objects.filter(created_at__lt=cutoff).delete()  # ménage : rien ne s'accumule
    LoginFailure.objects.create(username=username[:150].lower(), ip_address=ip_address or None)


def too_many_login_failures(*, username: str) -> bool:
    window = timezone.now() - timedelta(minutes=settings.LOGIN_LOCK_MINUTES)
    recent = LoginFailure.objects.filter(username=username[:150].lower(), created_at__gte=window)
    return recent.count() >= settings.LOGIN_MAX_FAILURES


def clear_login_failures(*, username: str) -> None:
    LoginFailure.objects.filter(username=username[:150].lower()).delete()
