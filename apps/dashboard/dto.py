from dataclasses import dataclass
from datetime import date
from uuid import UUID

from apps.cases.dto import KindSales
from apps.dashboard.constants import AlertKind
from apps.payments.dto import MethodTotal


@dataclass(frozen=True)
class Alert:
    kind: AlertKind
    case_id: UUID
    reference: str
    detail: str


@dataclass(frozen=True)
class DashboardSnapshot:
    """Les quatre chiffres du gérant. ``realized_margin_xaf`` vaut ``None`` pour un agent.

    - ``receivables_xaf`` : somme des soldes positifs des dossiers ;
    - ``realized_margin_xaf`` : marge reconnue des dossiers entièrement soldés ;
    - ``at_risk_cases`` : dossiers ayant un solde en retard ou un départ proche non soldé.
    """

    open_cases: int
    receivables_xaf: int
    realized_margin_xaf: int | None
    at_risk_cases: int
    alerts: tuple[Alert, ...]


@dataclass(frozen=True)
class SalesReport:
    """Ventes émises et encaissements d'une période. Coût et marge : ``None`` pour un agent."""

    start: date
    end: date
    by_kind: tuple[KindSales, ...]
    by_method: tuple[MethodTotal, ...]
    revenue_xaf: int
    collected_xaf: int
    margin_xaf: int | None
