"""Façade publique de l'application ledger.

Le coût et la marge ne sortent d'ici que pour un gérant ; les soldes clients restent lisibles
par les agents, qui encaissent.
"""

from datetime import date
from uuid import UUID

from apps.audit.services.public import AuditService
from apps.ledger import selectors
from apps.ledger.constants import Account
from apps.ledger.dto import TransactionInfo
from apps.ledger.services import commands
from apps.shared_kernel.actor import Actor


class LedgerService:
    @staticmethod
    def record_sale(
        actor: Actor,
        *,
        case_id: UUID,
        price_xaf: int,
        cost_xaf: int,
        occurred_on: date,
        idempotency_key: str,
    ) -> TransactionInfo:
        return commands.record_sale(
            case_id=case_id,
            price_xaf=price_xaf,
            cost_xaf=cost_xaf,
            occurred_on=occurred_on,
            created_by=actor.user_id,
            idempotency_key=idempotency_key,
        )

    @staticmethod
    def record_payment(
        actor: Actor,
        *,
        case_id: UUID,
        account: Account,
        amount_xaf: int,
        occurred_on: date,
        idempotency_key: str,
    ) -> TransactionInfo:
        return commands.record_payment(
            case_id=case_id,
            account=account,
            amount_xaf=amount_xaf,
            occurred_on=occurred_on,
            created_by=actor.user_id,
            idempotency_key=idempotency_key,
        )

    @staticmethod
    def close_period(actor: Actor, *, closed_until: date) -> date:
        actor.require_manager()
        result = commands.close_period(closed_until=closed_until, closed_by=actor.user_id)
        AuditService.record(
            actor_user_id=actor.user_id,
            action="period.closed",
            object_type="agency",
            object_id=actor.agency_id,
            metadata={"closed_until": closed_until.isoformat()},
        )
        return result

    @staticmethod
    def closed_until(actor: Actor) -> date | None:
        return selectors.closed_until()

    @staticmethod
    def reverse(actor: Actor, *, transaction_id: UUID, occurred_on: date) -> TransactionInfo:
        actor.require_manager()
        return commands.reverse(
            transaction_id=transaction_id, occurred_on=occurred_on, created_by=actor.user_id
        )

    @staticmethod
    def balances_by_case(actor: Actor) -> dict[UUID, int]:
        return selectors.balances_by_case()

    @staticmethod
    def margins_by_case(actor: Actor) -> dict[UUID, int]:
        actor.require_manager()
        return selectors.margins_by_case()

    @staticmethod
    def first_sale_dates(actor: Actor) -> dict[UUID, date]:
        return selectors.first_sale_dates()
