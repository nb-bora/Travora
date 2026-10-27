from dataclasses import dataclass
from uuid import UUID

from apps.dashboard.constants import AlertKind


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
