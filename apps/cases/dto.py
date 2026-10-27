from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from apps.cases.constants import CaseStatus, LineKind


@dataclass(frozen=True)
class CaseLineView:
    """Ligne d'un dossier. ``cost_xaf`` et ``margin_xaf`` valent ``None`` hors gérant."""

    id: UUID
    kind: LineKind
    label: str
    passenger_name: str
    ticket_number: str
    carrier: str
    details: Mapping[str, Any]
    price_xaf: int
    cost_xaf: int | None
    margin_xaf: int | None
    issued_on: date | None
    is_voided: bool


@dataclass(frozen=True)
class CaseSummary:
    """Dossier avec son état financier dérivé du journal.

    Les champs financiers internes (coût, marges) valent ``None`` pour un agent.
    """

    id: UUID
    reference: str
    customer_id: UUID
    customer_name: str
    status: CaseStatus
    departure_date: date | None
    price_total_xaf: int
    balance_xaf: int
    first_sale_on: date | None
    cost_total_xaf: int | None
    expected_margin_xaf: int | None
    recognized_margin_xaf: int | None
    has_unknown_cost: bool | None


@dataclass(frozen=True)
class CaseDetail:
    summary: CaseSummary
    lines: tuple[CaseLineView, ...]


@dataclass(frozen=True)
class TicketProposal:
    """Ce qu'on a cru lire dans un texte collé. Une valeur vide veut dire « non reconnu »."""

    ticket_numbers: tuple[str, ...]
    passengers: tuple[str, ...]
    customer_name: str
    origin: str
    destination: str
    departure_date: date | None
    departure_time: str
    arrival_time: str
    carrier: str
    booking_reference: str
    price_xaf: int | None
    warnings: tuple[str, ...]

    @property
    def recognised(self) -> bool:
        return bool(self.ticket_numbers or self.passengers or self.origin)
