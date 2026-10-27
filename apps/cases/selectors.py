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


def get_case(case_id: UUID, *, lock: bool = False) -> Case:
    """Avec ``lock``, verrouille la ligne du dossier jusqu'à la fin de la transaction.

    Toute opération qui change l'état d'un dossier ou son solde prend ce verrou : deux
    opérations simultanées sur un même dossier s'exécutent l'une après l'autre.
    """
    queryset = Case.objects.select_for_update() if lock else Case.objects.all()
    case = queryset.filter(id=case_id).first()
    if case is None:
        raise CaseNotFound(str(case_id))
    return case


def find_case_id_by_reference(reference: str) -> UUID | None:
    return Case.objects.filter(reference=reference).values_list("id", flat=True).first()


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
        carrier=line.carrier,
        price_xaf=line.price_xaf,
        cost_xaf=line.cost_xaf if financials else None,
        margin_xaf=margin,
        issued_on=line.issued_on,
        is_voided=line.voided_at is not None,
    )


def summaries(
    actor: Actor, *, status: CaseStatus | None = None, case_id: UUID | None = None
) -> list[CaseSummary]:
    financials = actor.can_view_financials
    queryset = Case.objects.all()
    if status is not None:
        queryset = queryset.filter(status=status)
    if case_id is not None:
        queryset = queryset.filter(id=case_id)
    rows = list(
        queryset.annotate(
            price_total=Sum("lines__price_xaf", filter=ACTIVE),
            cost_total=Sum("lines__cost_xaf", filter=ACTIVE),
            unknown_cost=Count("lines", filter=ACTIVE & Q(lines__cost_xaf__isnull=True)),
        ).order_by("-created_at", "id")
    )
    if case_id is None:
        customers = {customer.id: customer.name for customer in CrmService.list_customers(actor)}
    else:
        customers = {
            case.customer_id: CrmService.get_customer(actor, case.customer_id).name for case in rows
        }
    balances = LedgerService.balances_by_case(actor, case_id=case_id)
    first_sales = LedgerService.first_sale_dates(actor, case_id=case_id)
    margins = LedgerService.margins_by_case(actor, case_id=case_id) if financials else {}
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
    summary = summaries(actor, case_id=case_id)[0]
    lines = CaseLine.objects.filter(case_id=case_id).order_by("created_at", "id")
    return CaseDetail(
        summary=summary,
        lines=tuple(line_view(line, financials=actor.can_view_financials) for line in lines),
    )
