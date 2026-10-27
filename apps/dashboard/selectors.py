from datetime import date

from django.conf import settings
from django.utils import timezone

from apps.cases.constants import CaseStatus
from apps.cases.services.public import CasesService
from apps.dashboard.constants import AlertKind
from apps.dashboard.dto import Alert, DashboardSnapshot
from apps.quotes.services.public import QuotesService
from apps.shared_kernel.actor import Actor
from apps.shared_kernel.money import format_xaf


def snapshot(actor: Actor, today: date | None = None) -> DashboardSnapshot:
    today = today or timezone.localdate()
    cases = CasesService.list_cases(actor)
    open_cases = [case for case in cases if case.status is CaseStatus.OPEN]
    by_id = {case.id: case for case in cases}

    alerts: list[Alert] = []
    at_risk: set[object] = set()
    for case in open_cases:
        if case.balance_xaf <= 0:
            continue
        owed = format_xaf(case.balance_xaf)
        if case.first_sale_on is not None:
            days = (today - case.first_sale_on).days
            if days > settings.OVERDUE_DAYS:
                alerts.append(
                    Alert(
                        AlertKind.OVERDUE_BALANCE,
                        case.id,
                        case.reference,
                        f"{owed} dus depuis {days} jours",
                    )
                )
                at_risk.add(case.id)
        if case.departure_date is not None:
            until = (case.departure_date - today).days
            if 0 <= until <= settings.UPCOMING_DEPARTURE_DAYS:
                alerts.append(
                    Alert(
                        AlertKind.DEPARTURE_SOON,
                        case.id,
                        case.reference,
                        f"départ dans {until} jours, {owed} restent dus",
                    )
                )
                at_risk.add(case.id)

    for quote in QuotesService.expired_sent_quotes(actor, as_of=today):
        quoted_case = by_id.get(quote.case_id)
        if quoted_case is not None:
            alerts.append(
                Alert(
                    AlertKind.QUOTE_EXPIRED,
                    quoted_case.id,
                    quoted_case.reference,
                    f"devis v{quote.version} expiré le {quote.valid_until:%d/%m/%Y}",
                )
            )

    realized = None
    if actor.can_view_financials:
        realized = sum(
            case.recognized_margin_xaf or 0
            for case in cases
            if case.first_sale_on is not None and case.balance_xaf <= 0
        )
    return DashboardSnapshot(
        open_cases=len(open_cases),
        receivables_xaf=sum(case.balance_xaf for case in cases if case.balance_xaf > 0),
        realized_margin_xaf=realized,
        at_risk_cases=len(at_risk),
        alerts=tuple(alerts),
    )
