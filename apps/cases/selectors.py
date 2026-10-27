from uuid import UUID

from django.db.models import Count, Q, Sum

from apps.cases.constants import CaseStatus, LineKind
from apps.cases.dto import CaseDetail, CaseLineView, CaseSummary
from apps.cases.exceptions import CaseNotFound, LineNotFound
from apps.cases.models import Case, CaseLine
from apps.crm.services.public import CrmService
from apps.ledger.services.public import LedgerService
from apps.shared_kernel.actor import Actor

ACTIVE = Q(lines__voided_at__isnull=True)


def get_case(case_id: UUID) -> Case:
    case = Case.objects.filter(id=case_id).first()
    if case is None:
        raise CaseNotFound(str(case_id))
    return case


def get_line(line_id: UUID) -> CaseLine:
    line = CaseLine.objects.filter(id=line_id).select_related("case").first()
    if line is None:
        raise LineNotFound(str(line_id))
    return line


def line_view(line: CaseLine, *, financials: bool) -> CaseLineView:
    margin = None
    if financials and line.cost_xaf is not None:
        margin = line.price_xaf - line.cost_xaf
    return CaseLineView(
        id=line.id,
        kind=LineKind(line.kind),
        label=line.label,
        passenger_name=line.passenger_name,
        ticket_number=line.ticket_number,
        price_xaf=line.price_xaf,
        cost_xaf=line.cost_xaf if financials else None,
        margin_xaf=margin,
        issued_on=line.issued_on,
        is_voided=line.voided_at is not None,
    )


def summaries(actor: Actor, *, status: CaseStatus | None = None) -> list[CaseSummary]:
    financials = actor.can_view_financials
    queryset = Case.objects.all()
    if status is not None:
        queryset = queryset.filter(status=status)
    rows = list(
        queryset.annotate(
            price_total=Sum("lines__price_xaf", filter=ACTIVE),
            cost_total=Sum("lines__cost_xaf", filter=ACTIVE),
            unknown_cost=Count("lines", filter=ACTIVE & Q(lines__cost_xaf__isnull=True)),
        ).order_by("-created_at", "id")
    )
    customers = {customer.id: customer.name for customer in CrmService.list_customers(actor)}
    balances = LedgerService.balances_by_case(actor)
    first_sales = LedgerService.first_sale_dates(actor)
    margins = LedgerService.margins_by_case(actor) if financials else {}
    result = []
    for case in rows:
        price_total = case.price_total or 0
        cost_total = case.cost_total or 0
        result.append(
            CaseSummary(
                id=case.id,
                reference=case.reference,
                customer_id=case.customer_id,
                customer_name=customers.get(case.customer_id, ""),
                status=CaseStatus(case.status),
                departure_date=case.departure_date,
                price_total_xaf=price_total,
                balance_xaf=balances.get(case.id, 0),
                first_sale_on=first_sales.get(case.id),
                cost_total_xaf=cost_total if financials else None,
                expected_margin_xaf=price_total - cost_total if financials else None,
                recognized_margin_xaf=margins.get(case.id, 0) if financials else None,
                has_unknown_cost=case.unknown_cost > 0 if financials else None,
            )
        )
    return result


def case_detail(actor: Actor, case_id: UUID) -> CaseDetail:
    get_case(case_id)
    summary = next(item for item in summaries(actor) if item.id == case_id)
    lines = CaseLine.objects.filter(case_id=case_id).order_by("created_at", "id")
    return CaseDetail(
        summary=summary,
        lines=tuple(line_view(line, financials=actor.can_view_financials) for line in lines),
    )
