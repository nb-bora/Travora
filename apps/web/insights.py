"""Fiche client et rapports de ventes. Lecture seule : rien n'est écrit ici.

La marge n'est jamais calculée ni rendue pour un agent : la façade renvoie ``None`` et les
gabarits n'affichent aucune colonne de coût.
"""

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.cases.constants import CaseStatus
from apps.cases.dto import CaseSummary
from apps.cases.services.public import CasesService
from apps.crm.dto import CustomerInfo
from apps.crm.exceptions import CustomerNotFound
from apps.crm.services.public import CrmService
from apps.dashboard.services.public import DashboardService
from apps.payments.services.public import PaymentsService
from apps.shared_kernel.actor import Actor
from apps.web.access import _actor, agency_required

PERIODS = (
    ("7j", "7 jours"),
    ("30j", "30 jours"),
    ("mois", "Ce mois"),
    ("annee", "Cette année"),
)
MAX_SPAN_DAYS = 366 * 2
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe(value: object) -> str:
    """Une cellule CSV qui commence par = + - @ serait lue comme une formule par un tableur."""
    text = str(value)
    return "'" + text if text.startswith(FORMULA_PREFIXES) else text


def _csv_response(filename: str, header: list[str], rows: list[list[object]]) -> HttpResponse:
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("﻿")  # BOM : Excel ouvre les accents correctement
    writer = csv.writer(response, delimiter=";")
    writer.writerow(header)
    for row in rows:
        writer.writerow([_safe(cell) for cell in row])
    return response


# --- fiche client -------------------------------------------------------------------------


@dataclass(frozen=True)
class CustomerPayment:
    received_on: date
    reference: str
    case_reference: str
    case_id: UUID
    method: str
    method_value: str
    amount_xaf: int


def _customer_or_404(request: HttpRequest, customer_id: UUID) -> tuple[Actor, CustomerInfo]:
    actor = _actor(request)
    try:
        customer = CrmService.get_customer(actor, customer_id)
    except CustomerNotFound as error:
        raise Http404 from error
    return actor, customer


def _customer_payments(actor: Actor, cases: list[CaseSummary]) -> list[CustomerPayment]:
    rows: list[CustomerPayment] = []
    for case in cases:
        for payment in PaymentsService.payments_for_case(actor, case.id):
            if payment.is_voided:
                continue
            rows.append(
                CustomerPayment(
                    received_on=payment.received_on,
                    reference=payment.reference,
                    case_reference=case.reference,
                    case_id=case.id,
                    method=payment.method.label,
                    method_value=payment.method.value,
                    amount_xaf=payment.amount_xaf,
                )
            )
    rows.sort(key=lambda row: row.received_on, reverse=True)
    return rows


@agency_required
@require_GET
def customer_detail(request: HttpRequest, customer_id: UUID) -> HttpResponse:
    actor, customer = _customer_or_404(request, customer_id)
    cases = CasesService.list_cases(actor, customer_id=customer.id)
    payments = _customer_payments(actor, cases)
    open_cases = [case for case in cases if case.status is CaseStatus.OPEN]
    context = {
        "customer": customer,
        "cases": cases,
        "payments": payments,
        "due_xaf": sum(max(case.balance_xaf, 0) for case in open_cases),
        "open_count": len(open_cases),
        "billed_xaf": sum(
            case.price_total_xaf for case in cases if case.status is not CaseStatus.CANCELLED
        ),
        "paid_xaf": sum(payment.amount_xaf for payment in payments),
    }
    return render(request, "web/customer_detail.html", context)


@agency_required
@require_GET
def customer_export(request: HttpRequest, customer_id: UUID) -> HttpResponse:
    """Fichier lisible de ce que l'agence détient sur le client : fiche, dossiers, encaissements."""
    actor, customer = _customer_or_404(request, customer_id)
    cases = CasesService.list_cases(actor, customer_id=customer.id)
    rows: list[list[object]] = [["Client", customer.name, customer.phone, "", "", ""]]
    for case in cases:
        rows.append(
            ["Dossier", case.reference, case.status.label, case.departure_date or "",
             case.price_total_xaf, case.balance_xaf]
        )  # fmt: skip
    for payment in _customer_payments(actor, cases):
        rows.append(
            ["Encaissement", payment.case_reference, payment.method, payment.received_on,
             payment.amount_xaf, payment.reference]
        )  # fmt: skip
    header = [
        "Type", "Référence ou nom", "Statut, mode ou téléphone", "Date", "Montant FCFA",
        "Solde ou réf.",
    ]  # fmt: skip
    return _csv_response(f"client-{customer.id}.csv", header, rows)


# --- rapports -----------------------------------------------------------------------------


def _parse_day(raw: str) -> date | None:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def resolve_period(request: HttpRequest, today: date) -> tuple[date, date, str, str]:
    """Période demandée → (début, fin, clé du préréglage, message d'erreur éventuel)."""
    default = (today - timedelta(days=29), today, "30j")
    start_raw, end_raw = request.GET.get("du", ""), request.GET.get("au", "")
    if start_raw or end_raw:
        start, end = _parse_day(start_raw), _parse_day(end_raw)
        if start is None or end is None:
            return (*default, "Dates invalides : AAAA-MM-JJ attendu.")
        if start > end:
            return (*default, "La date de début suit la date de fin.")
        if (end - start).days > MAX_SPAN_DAYS:
            return (*default, "Période trop longue : 2 ans au plus.")
        return start, end, "perso", ""
    key = request.GET.get("periode", "30j")
    if key == "7j":
        return today - timedelta(days=6), today, key, ""
    if key == "mois":
        return today.replace(day=1), today, key, ""
    if key == "annee":
        return today.replace(month=1, day=1), today, key, ""
    return (*default, "")


@agency_required
@require_GET
def report(request: HttpRequest) -> HttpResponse:
    actor = _actor(request)
    start, end, key, error = resolve_period(request, timezone.localdate())
    sales = DashboardService.sales_report(actor, start=start, end=end)
    context = {
        "sales": sales,
        "periods": PERIODS,
        "period": key,
        "start": start,
        "end": end,
        "error": error,
        "top_revenue": max((row.revenue_xaf for row in sales.by_kind), default=0),
        "top_collected": max((row.amount_xaf for row in sales.by_method), default=0),
        "is_manager": actor.can_view_financials,
    }
    return render(request, "web/report.html", context)


@agency_required
@require_GET
def report_export(request: HttpRequest) -> HttpResponse:
    actor = _actor(request)
    start, end, _key, _error = resolve_period(request, timezone.localdate())
    sales = DashboardService.sales_report(actor, start=start, end=end)
    manager = actor.can_view_financials
    header = ["Section", "Libellé", "Nombre", "Montant FCFA"]
    if manager:
        header += ["Coût FCFA", "Marge FCFA"]
    rows: list[list[object]] = []
    for line in sales.by_kind:
        row: list[object] = ["Ventes", line.kind.label, line.lines, line.revenue_xaf]
        if manager:
            row += [line.cost_xaf, line.margin_xaf]
        rows.append(row)
    for method in sales.by_method:
        row = ["Encaissements", method.method.label, method.count, method.amount_xaf]
        if manager:
            row += ["", ""]
        rows.append(row)
    return _csv_response(f"rapport-{start}-{end}.csv", header, rows)
