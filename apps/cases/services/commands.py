from datetime import date
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services.public import AuditService
from apps.cases import selectors
from apps.cases.constants import CaseStatus, LineKind
from apps.cases.dto import CaseLineView
from apps.cases.exceptions import (
    BalanceNotSettled,
    CaseHasActiveSales,
    CaseNotClosed,
    CaseNotOpen,
    InvalidLine,
    LineLocked,
)
from apps.cases.models import Case, CaseLine
from apps.crm.services.public import CrmService
from apps.ledger.services.public import LedgerService
from apps.shared_kernel.actor import Actor

REFERENCE_ATTEMPTS = 5


def _next_reference(offset: int) -> str:
    prefix = f"{timezone.localdate().year}-"
    count = Case.objects.filter(reference__startswith=prefix).count()
    return f"{prefix}{count + 1 + offset:04d}"


def create_case(
    actor: Actor, *, customer_id: UUID, departure_date: date | None, reference: str | None
) -> UUID:
    CrmService.get_customer(actor, customer_id)
    for attempt in range(REFERENCE_ATTEMPTS):
        try:
            with transaction.atomic():
                case = Case.objects.create(
                    customer_id=customer_id,
                    reference=reference or _next_reference(attempt),
                    departure_date=departure_date,
                    created_by=actor.user_id,
                )
        except IntegrityError:
            if reference is not None or attempt == REFERENCE_ATTEMPTS - 1:
                raise
            continue
        AuditService.record(
            actor_user_id=actor.user_id,
            action="case.created",
            object_type="case",
            object_id=case.id,
            metadata={"reference": case.reference},
        )
        return case.id
    raise AssertionError("inatteignable")


def require_open_case(case_id: UUID) -> Case:
    case = selectors.get_case(case_id, lock=True)
    if case.status != CaseStatus.OPEN:
        raise CaseNotOpen(case.reference)
    return case


def _clean_ticket_number(raw: str) -> str:
    return "".join(character for character in raw if character.isdigit())


def _validate_amounts(price_xaf: int | None, cost_xaf: int | None) -> None:
    if price_xaf is not None and price_xaf < 0:
        raise InvalidLine("Le prix n'est jamais négatif.")
    if cost_xaf is not None and cost_xaf < 0:
        raise InvalidLine("Le coût n'est jamais négatif.")


def add_line(
    actor: Actor,
    *,
    case_id: UUID,
    kind: LineKind,
    label: str,
    price_xaf: int,
    cost_xaf: int | None,
    passenger_name: str,
    ticket_number: str,
    raw_text: str,
) -> CaseLineView:
    require_open_case(case_id)
    _validate_amounts(price_xaf, cost_xaf)
    if not label.strip():
        raise InvalidLine("Le libellé est obligatoire.")
    number = _clean_ticket_number(ticket_number)
    if number and kind is not LineKind.AIR_TICKET:
        raise InvalidLine("Seul un billet d'avion porte un numéro de billet.")
    line = CaseLine.objects.create(
        case_id=case_id,
        kind=kind,
        label=label.strip(),
        passenger_name=passenger_name.strip(),
        ticket_number=number,
        price_xaf=price_xaf,
        cost_xaf=cost_xaf,
        raw_text=raw_text,
    )
    AuditService.record(
        actor_user_id=actor.user_id,
        action="line.added",
        object_type="case_line",
        object_id=line.id,
        metadata={"case_id": str(case_id), "kind": kind.value},
    )
    return selectors.line_view(line, financials=actor.can_view_financials)


def _editable_line(line_id: UUID) -> CaseLine:
    line = selectors.get_line(line_id)
    if line.issued_on is not None or line.voided_at is not None:
        raise LineLocked("Une ligne émise ou annulée ne se modifie plus.")
    require_open_case(line.case_id)
    return line


def update_line(
    actor: Actor,
    *,
    line_id: UUID,
    label: str | None,
    passenger_name: str | None,
    ticket_number: str | None,
    price_xaf: int | None,
    cost_xaf: int | None,
) -> CaseLineView:
    line = _editable_line(line_id)
    _validate_amounts(price_xaf, cost_xaf)
    if label is not None:
        if not label.strip():
            raise InvalidLine("Le libellé est obligatoire.")
        line.label = label.strip()
    if passenger_name is not None:
        line.passenger_name = passenger_name.strip()
    if ticket_number is not None:
        number = _clean_ticket_number(ticket_number)
        if number and line.kind != LineKind.AIR_TICKET:
            raise InvalidLine("Seul un billet d'avion porte un numéro de billet.")
        line.ticket_number = number
    if price_xaf is not None:
        line.price_xaf = price_xaf
    if cost_xaf is not None:
        line.cost_xaf = cost_xaf
    line.save()
    AuditService.record(
        actor_user_id=actor.user_id,
        action="line.updated",
        object_type="case_line",
        object_id=line.id,
        metadata={"case_id": str(line.case_id)},
    )
    return selectors.line_view(line, financials=actor.can_view_financials)


def issue_line(actor: Actor, *, line_id: UUID, issued_on: date) -> CaseLineView:
    line = _editable_line(line_id)
    if line.cost_xaf is None:
        raise InvalidLine("Le coût fournisseur est requis pour émettre une ligne.")
    if line.price_xaf == 0 and line.cost_xaf == 0:
        raise InvalidLine("Une ligne sans valeur ne s'émet pas.")
    sale = LedgerService.record_sale(
        actor,
        case_id=line.case_id,
        price_xaf=line.price_xaf,
        cost_xaf=line.cost_xaf,
        occurred_on=issued_on,
        idempotency_key=f"sale:{line.id}",
    )
    line.issued_on = issued_on
    line.sale_transaction_id = sale.id
    line.save()
    AuditService.record(
        actor_user_id=actor.user_id,
        action="line.issued",
        object_type="case_line",
        object_id=line.id,
        metadata={"case_id": str(line.case_id), "price_xaf": line.price_xaf},
    )
    return selectors.line_view(line, financials=actor.can_view_financials)


def void_line(actor: Actor, *, line_id: UUID, voided_on: date) -> CaseLineView:
    actor.require_manager()
    line = selectors.get_line(line_id)
    require_open_case(line.case_id)
    if line.voided_at is not None:
        raise LineLocked("Cette ligne est déjà annulée.")
    if line.sale_transaction_id is not None:
        LedgerService.reverse(actor, transaction_id=line.sale_transaction_id, occurred_on=voided_on)
    line.voided_at = timezone.now()
    line.save()
    AuditService.record(
        actor_user_id=actor.user_id,
        action="line.voided",
        object_type="case_line",
        object_id=line.id,
        metadata={"case_id": str(line.case_id), "was_issued": line.issued_on is not None},
    )
    return selectors.line_view(line, financials=True)


def close_case(actor: Actor, *, case_id: UUID) -> None:
    case = require_open_case(case_id)
    balance = LedgerService.balances_by_case(actor).get(case_id, 0)
    if balance != 0:
        raise BalanceNotSettled(f"Solde restant : {balance} XAF.")
    case.status = CaseStatus.CLOSED
    case.save()
    AuditService.record(
        actor_user_id=actor.user_id,
        action="case.closed",
        object_type="case",
        object_id=case.id,
        metadata={"reference": case.reference},
    )


def reopen_case(actor: Actor, *, case_id: UUID) -> None:
    """Rouvre un dossier clos pour corriger une erreur ; seul un dossier clos se rouvre."""
    actor.require_manager()
    case = selectors.get_case(case_id, lock=True)
    if case.status != CaseStatus.CLOSED:
        raise CaseNotClosed(case.reference)
    case.status = CaseStatus.OPEN
    case.save()
    AuditService.record(
        actor_user_id=actor.user_id,
        action="case.reopened",
        object_type="case",
        object_id=case.id,
        metadata={"reference": case.reference},
    )


def cancel_case(actor: Actor, *, case_id: UUID, cancelled_on: date) -> None:
    actor.require_manager()
    case = require_open_case(case_id)
    active = list(CaseLine.objects.filter(case_id=case_id, voided_at__isnull=True))
    if any(line.issued_on is not None for line in active):
        raise CaseHasActiveSales("Annulez d'abord les lignes émises.")
    for line in active:
        line.voided_at = timezone.now()
        line.save()
    case.status = CaseStatus.CANCELLED
    case.save()
    AuditService.record(
        actor_user_id=actor.user_id,
        action="case.cancelled",
        object_type="case",
        object_id=case.id,
        metadata={"reference": case.reference, "on": cancelled_on.isoformat()},
    )
