"""Façade publique de l'application accounts."""

from uuid import UUID

from apps.accounts import selectors
from apps.accounts.dto import MembershipInfo
from apps.accounts.services import commands
from apps.shared_kernel.actor import Actor
from apps.shared_kernel.roles import Role


class AccountsService:
    @staticmethod
    def find_user_id(username: str) -> UUID | None:
        return selectors.find_user_id(username)

    @staticmethod
    def active_membership(user_id: UUID) -> MembershipInfo | None:
        return selectors.active_membership(user_id)

    @staticmethod
    def create_first_manager(*, username: str, password: str) -> MembershipInfo:
        return commands.create_first_manager(username=username, password=password)

    @staticmethod
    def create_member(actor: Actor, *, username: str, password: str, role: Role) -> MembershipInfo:
        return commands.create_member(actor, username=username, password=password, role=role)
