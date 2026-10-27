"""Façade publique de l'application cases.

Les vues renvoyées ne contiennent ni coût ni marge pour un agent : le filtrage est fait ici,
côté serveur, jamais par l'interface.
"""

from datetime import date
from uuid import UUID

from apps.cases import selectors
from apps.cases.constants import CaseStatus, LineKind
from apps.cases.dto import CaseDetail, CaseLineView, CaseSummary
from apps.cases.services import commands
from apps.cases.ticket_text import extract_ticket_numbers
from apps.shared_kernel.actor import Actor


class CasesService:
    @staticmethod
    def create_case(
        actor: Actor,
        *,
        customer_id: UUID,
        departure_date: date | None = None,
        reference: str | None = None,
    ) -> UUID:
        return commands.create_case(
            actor, customer_id=customer_id, departure_date=departure_date, reference=reference
        )

    @staticmethod
    def add_line(
        actor: Actor,
        *,
        case_id: UUID,
        kind: LineKind,
        label: str,
        price_xaf: int,
        cost_xaf: int | None = None,
        passenger_name: str = "",
        ticket_number: str = "",
        raw_text: str = "",
    ) -> CaseLineView:
        return commands.add_line(
            actor,
            case_id=case_id,
            kind=kind,
            label=label,
            price_xaf=price_xaf,
            cost_xaf=cost_xaf,
            passenger_name=passenger_name,
            ticket_number=ticket_number,
            raw_text=raw_text,
        )

    @staticmethod
    def update_line(
        actor: Actor,
        *,
        line_id: UUID,
        label: str | None = None,
        passenger_name: str | None = None,
        ticket_number: str | None = None,
        price_xaf: int | None = None,
        cost_xaf: int | None = None,
    ) -> CaseLineView:
        return commands.update_line(
            actor,
            line_id=line_id,
            label=label,
            passenger_name=passenger_name,
            ticket_number=ticket_number,
            price_xaf=price_xaf,
            cost_xaf=cost_xaf,
        )

    @staticmethod
    def issue_line(actor: Actor, *, line_id: UUID, issued_on: date) -> CaseLineView:
        return commands.issue_line(actor, line_id=line_id, issued_on=issued_on)

    @staticmethod
    def void_line(actor: Actor, *, line_id: UUID, voided_on: date) -> CaseLineView:
        return commands.void_line(actor, line_id=line_id, voided_on=voided_on)

    @staticmethod
    def close_case(actor: Actor, *, case_id: UUID) -> None:
        commands.close_case(actor, case_id=case_id)

    @staticmethod
    def reopen_case(actor: Actor, *, case_id: UUID) -> None:
        commands.reopen_case(actor, case_id=case_id)

    @staticmethod
    def cancel_case(actor: Actor, *, case_id: UUID, cancelled_on: date) -> None:
        commands.cancel_case(actor, case_id=case_id, cancelled_on=cancelled_on)

    @staticmethod
    def require_open_case(actor: Actor, case_id: UUID) -> None:
        commands.require_open_case(case_id)

    @staticmethod
    def get_case(actor: Actor, case_id: UUID) -> CaseDetail:
        return selectors.case_detail(actor, case_id)

    @staticmethod
    def list_cases(actor: Actor, *, status: CaseStatus | None = None) -> list[CaseSummary]:
        return selectors.summaries(actor, status=status)

    @staticmethod
    def find_case_id_by_reference(actor: Actor, reference: str) -> UUID | None:
        return selectors.find_case_id_by_reference(reference)

    @staticmethod
    def propose_ticket_numbers(text: str) -> list[str]:
        return extract_ticket_numbers(text)
