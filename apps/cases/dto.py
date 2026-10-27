from dataclasses import dataclass
from datetime import date
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
