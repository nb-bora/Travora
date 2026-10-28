import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from urllib.parse import quote
from uuid import UUID

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.cases.constants import CaseStatus, LineKind
from apps.cases.dto import CaseSummary
from apps.cases.exceptions import CaseNotFound
from apps.cases.services.public import CasesService
from apps.crm.services.public import CrmService
from apps.dashboard.constants import AlertKind
from apps.dashboard.services.public import DashboardService
from apps.payments.constants import PaymentMethod
from apps.payments.services.public import PaymentsService
from apps.quotes.services.public import QuotesService
from apps.shared_kernel.actor import Actor
from apps.tenancy.services.public import TenancyService
from apps.web.access import _actor, agency_required
from apps.web.errors import attempt
from apps.web.forms import CaseForm, LineForm, PaymentForm, QuickEntryForm


def _today_context(actor: Actor, quick_form: QuickEntryForm | None = None) -> dict[str, object]:
    snapshot = DashboardService.snapshot(actor)
    overdue = [a for a in snapshot.alerts if a.kind is AlertKind.OVERDUE_BALANCE]
    return {
        "snapshot": snapshot,
        "is_manager": actor.can_view_financials,
        "quick_form": quick_form or QuickEntryForm(),
        "overdue_count": len(overdue),
        "alert_icons": {
            AlertKind.OVERDUE_BALANCE.value: "badge-danger",
            AlertKind.DEPARTURE_SOON.value: "badge-warning",
            AlertKind.QUOTE_EXPIRED.value: "badge-neutral",
        },
    }


@agency_required
@require_GET
def today(request: HttpRequest) -> HttpResponse:
    """Écran d'accueil : saisie rapide et chiffres du jour. Le rôle décide de ce qui est montré."""
    return render(request, "web/today.html", _today_context(_actor(request)))


MAX_PASTE = 5_000
DONE_KEY = "done_submissions"
REMEMBERED = 40


def _already_done(request: HttpRequest, token: str) -> str | None:
    """Adresse du résultat d'un envoi déjà traité avec ce jeton (double clic, rejeu réseau)."""
    done: dict[str, str] = request.session.get(DONE_KEY, {})
    return done.get(token) if token else None


def _remember(request: HttpRequest, token: str, url: str) -> None:
    if not token:
        return
    done: dict[str, str] = request.session.get(DONE_KEY, {})
    done[token] = url
    request.session[DONE_KEY] = dict(list(done.items())[-REMEMBERED:])


@agency_required
@require_POST
def paste_booking(request: HttpRequest) -> HttpResponse:
    """Lit un texte collé et pré-remplit la saisie rapide. Rien n'est enregistré."""
    actor = _actor(request)
    text = request.POST.get("text", "")[:MAX_PASTE]
    proposal = CasesService.propose_booking(text, today=timezone.localdate())
    initial: dict[str, object] = {}
    if proposal.recognised:
        initial = {
            "kind": LineKind.AIR_TICKET.value,
            "origin": proposal.origin,
            "destination": proposal.destination,
            "departure_date": proposal.departure_date,
            "customer_name": proposal.customer_name,
            "passenger_name": proposal.passengers[0] if proposal.passengers else "",
            "carrier": proposal.carrier,
            "ticket_number": proposal.ticket_numbers[0] if proposal.ticket_numbers else "",
            "price_xaf": proposal.price_xaf,
        }
    context = _today_context(actor, QuickEntryForm(initial=initial))
    context.update({"proposal": proposal, "pasted_text": text})
    return render(request, "web/today.html", context)


@agency_required
@require_POST
def quick_entry(request: HttpRequest) -> HttpResponse:
    """Crée le client, le dossier et sa première ligne en un seul geste, ou rien du tout."""
    actor = _actor(request)
    form = QuickEntryForm(request.POST)
    if not form.is_valid():
        return render(request, "web/today.html", _today_context(actor, form), status=422)
    data = form.cleaned_data
    token = data.get("submission_id", "")
    if (url := _already_done(request, token)) is not None:
        return redirect(url)

    def create() -> UUID:
        customer = CrmService.find_or_create_customer(
            actor, name=data["customer_name"], phone=data["customer_phone"]
        )
        case_id = CasesService.create_case(
            actor, customer_id=customer.id, departure_date=data["departure_date"]
        )
        CasesService.add_line(
            actor,
            case_id=case_id,
            kind=LineKind(data["kind"]),
            label=data["label"],
            price_xaf=data["price_xaf"],
            cost_xaf=data["cost_xaf"],
            passenger_name=data["passenger_name"],
            ticket_number=data["ticket_number"],
            carrier=data["carrier"],
        )
        return case_id

    case_id = attempt(request, create, "Dossier créé avec sa première ligne.")
    if case_id is None:  # refus du domaine : la saisie est conservée, le message l'explique
        return render(request, "web/today.html", _today_context(actor, form), status=422)
    target = reverse("web:case_detail", kwargs={"case_id": case_id})
    _remember(request, token, target)
    return redirect(target)


SOON = timedelta(days=settings.UPCOMING_DEPARTURE_DAYS)

FILTERS = {
    "ouverts": "Ouverts",
    "depart": f"Départs sous {settings.UPCOMING_DEPARTURE_DAYS} jours",
    "impayes": "Impayés",
    "clos": "Clos",
    "tous": "Tous",
}


def _matches(case: CaseSummary, key: str, today_: date) -> bool:
    is_open = case.status is CaseStatus.OPEN
    if key == "ouverts":
        return is_open
    if key == "depart":
        return (
            is_open
            and case.departure_date is not None
            and today_ <= case.departure_date <= today_ + SOON
        )
    if key == "impayes":
        return is_open and case.balance_xaf > 0
    if key == "clos":
        return case.status is CaseStatus.CLOSED
    return True


@agency_required
@require_GET
def case_list(request: HttpRequest) -> HttpResponse:
    actor = _actor(request)
    key = request.GET.get("etat", "ouverts")
    if key not in FILTERS:
        key = "ouverts"
    today_ = timezone.localdate()
    everything = CasesService.list_cases(actor)
    counts = {slug: sum(_matches(c, slug, today_) for c in everything) for slug in FILTERS}
    cases = [case for case in everything if _matches(case, key, today_)]
    query = request.GET.get("q", "").strip().lower()
    if query:
        cases = [
            case
            for case in cases
            if query in case.reference.lower() or query in case.customer_name.lower()
        ]
    return render(
        request,
        "web/case_list.html",
        {
            "cases": cases,
            "tabs": [(slug, label, counts[slug]) for slug, label in FILTERS.items()],
            "current": key,
            "query": query,
            "is_manager": actor.can_view_financials,
            "today": today_,
            "total_open": counts["ouverts"],
            "attention": counts["impayes"],
        },
    )


@agency_required
@require_http_methods(["GET", "POST"])
def case_create(request: HttpRequest) -> HttpResponse:
    actor = _actor(request)
    form = CaseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        token = data.get("submission_id", "")
        if (url := _already_done(request, token)) is not None:
            return redirect(url)

        def create() -> UUID:
            customer = CrmService.find_or_create_customer(
                actor, name=data["customer_name"], phone=data["customer_phone"]
            )
            return CasesService.create_case(
                actor, customer_id=customer.id, departure_date=data["departure_date"]
            )

        case_id = attempt(request, create, "Dossier créé.")
        if case_id is not None:
            target = reverse("web:case_detail", kwargs={"case_id": case_id})
            _remember(request, token, target)
            return redirect(target)
    return render(request, "web/case_form.html", {"form": form})


def _detail_context(
    request: HttpRequest,
    actor: Actor,
    case_id: UUID,
    *,
    line_form: LineForm | None = None,
    payment_form: PaymentForm | None = None,
) -> dict[str, object]:
    try:
        detail = CasesService.get_case(actor, case_id)
    except CaseNotFound as error:
        raise Http404 from error
    return {
        "detail": detail,
        "summary": detail.summary,
        "payments": PaymentsService.payments_for_case(actor, case_id),
        "quotes": QuotesService.quotes_for_case(actor, case_id),
        "quote_default_date": timezone.localdate() + timedelta(days=15),
        "line_form": line_form or LineForm(),
        "payment_form": payment_form
        or PaymentForm(initial={"amount_xaf": max(detail.summary.balance_xaf, 0) or None}),
        "is_manager": actor.can_view_financials,
        "is_open": detail.summary.status is CaseStatus.OPEN,
    }


@agency_required
@require_GET
def case_detail(request: HttpRequest, case_id: UUID) -> HttpResponse:
    actor = _actor(request)
    return render(request, "web/case_detail.html", _detail_context(request, actor, case_id))


@agency_required
@require_POST
def line_add(request: HttpRequest, case_id: UUID) -> HttpResponse:
    actor = _actor(request)
    form = LineForm(request.POST)
    if not form.is_valid():
        context = _detail_context(request, actor, case_id, line_form=form)
        return render(request, "web/case_detail.html", context, status=422)
    data = form.cleaned_data
    token = data.get("submission_id", "")
    target = reverse("web:case_detail", kwargs={"case_id": case_id})
    if _already_done(request, token) is not None:
        return redirect(target)
    added = attempt(
        request,
        lambda: CasesService.add_line(
            actor,
            case_id=case_id,
            kind=LineKind(data["kind"]),
            label=data["label"],
            price_xaf=data["price_xaf"],
            cost_xaf=data["cost_xaf"],
            passenger_name=data["passenger_name"],
            ticket_number=data["ticket_number"],
            carrier=data["carrier"],
        ),
        "Ligne ajoutée.",
    )
    if added is not None:
        _remember(request, token, target)
    return redirect(target)


@agency_required
@require_POST
def payment_add(request: HttpRequest, case_id: UUID) -> HttpResponse:
    actor = _actor(request)
    form = PaymentForm(request.POST)
    if not form.is_valid():
        context = _detail_context(request, actor, case_id, payment_form=form)
        return render(request, "web/case_detail.html", context, status=422)
    data = form.cleaned_data
    attempt(
        request,
        lambda: PaymentsService.record_payment(
            actor,
            case_id=case_id,
            method=PaymentMethod(data["method"]),
            amount_xaf=data["amount_xaf"],
            reference=data["reference"],
            received_on=data["received_on"],
            idempotency_key=f"web:{uuid.uuid5(case_id, data['idempotency_key']).hex}",
        ),
        "Encaissement enregistré.",
    )
    return redirect("web:case_detail", case_id=case_id)


def _ensure_belongs(
    actor: Actor, case_id: UUID, *, line_id: UUID | None = None, payment_id: UUID | None = None
) -> None:
    """404 si la ligne ou le paiement n'est pas rattaché au dossier de l'adresse."""
    try:
        detail = CasesService.get_case(actor, case_id)
    except CaseNotFound as error:
        raise Http404 from error
    if line_id is not None and line_id not in {line.id for line in detail.lines}:
        raise Http404
    if payment_id is not None and payment_id not in {
        payment.id for payment in PaymentsService.payments_for_case(actor, case_id)
    }:
        raise Http404


def _line_action(request: HttpRequest, case_id: UUID, line_id: UUID, name: str) -> HttpResponse:
    actor = _actor(request)
    _ensure_belongs(actor, case_id, line_id=line_id)
    today_ = timezone.localdate()
    if name == "issue":
        attempt(
            request,
            lambda: CasesService.issue_line(actor, line_id=line_id, issued_on=today_),
            "Ligne émise.",
        )
    else:
        attempt(
            request,
            lambda: CasesService.void_line(actor, line_id=line_id, voided_on=today_),
            "Ligne annulée.",
        )
    return redirect("web:case_detail", case_id=case_id)


@agency_required
@require_POST
def line_issue(request: HttpRequest, case_id: UUID, line_id: UUID) -> HttpResponse:
    return _line_action(request, case_id, line_id, "issue")


@agency_required
@require_POST
def line_void(request: HttpRequest, case_id: UUID, line_id: UUID) -> HttpResponse:
    return _line_action(request, case_id, line_id, "void")


@agency_required
@require_POST
def case_close(request: HttpRequest, case_id: UUID) -> HttpResponse:
    actor = _actor(request)
    attempt(request, lambda: CasesService.close_case(actor, case_id=case_id), "Dossier clos.")
    return redirect("web:case_detail", case_id=case_id)


@agency_required
@require_POST
def case_reopen(request: HttpRequest, case_id: UUID) -> HttpResponse:
    actor = _actor(request)
    attempt(request, lambda: CasesService.reopen_case(actor, case_id=case_id), "Dossier rouvert.")
    return redirect("web:case_detail", case_id=case_id)


@agency_required
@require_POST
def payment_void(request: HttpRequest, case_id: UUID, payment_id: UUID) -> HttpResponse:
    actor = _actor(request)
    _ensure_belongs(actor, case_id, payment_id=payment_id)
    today_ = timezone.localdate()
    attempt(
        request,
        lambda: PaymentsService.void_payment(actor, payment_id=payment_id, voided_on=today_),
        "Encaissement annulé.",
    )
    return redirect("web:case_detail", case_id=case_id)


@dataclass(frozen=True)
class CustomerRow:
    id: UUID
    name: str
    phone: str
    open: int
    due: int
    whatsapp: str


def _whatsapp_link(phone: str, name: str, balance_xaf: int, agency: str) -> str:
    """Lien « cliquer pour discuter » : l'agent envoie lui-même le message depuis WhatsApp."""
    message = (
        f"Bonjour {name}, il reste {balance_xaf:,} FCFA à régler pour votre voyage. "
        f"Pouvez-vous nous indiquer quand vous pourrez effectuer le paiement ? "
        f"Merci. — {agency}"
    ).replace(",", " ")
    return f"https://wa.me/{phone.lstrip('+')}?text={quote(message)}"


@agency_required
@require_GET
def customer_list(request: HttpRequest) -> HttpResponse:
    actor = _actor(request)
    agency = TenancyService.agency_info(actor).name
    cases = CasesService.list_cases(actor)
    by_customer: dict[UUID, dict[str, int]] = {}
    for case in cases:
        entry = by_customer.setdefault(case.customer_id, {"open": 0, "due": 0})
        if case.status is CaseStatus.OPEN:
            entry["open"] += 1
            entry["due"] += max(case.balance_xaf, 0)
    query = request.GET.get("q", "").strip().lower()
    rows: list[CustomerRow] = []
    for customer in CrmService.list_customers(actor):
        if query and query not in customer.name.lower() and query not in customer.phone:
            continue
        figures = by_customer.get(customer.id, {"open": 0, "due": 0})
        link = ""
        if figures["due"] > 0 and customer.phone:
            link = _whatsapp_link(customer.phone, customer.name, figures["due"], agency)
        rows.append(
            CustomerRow(
                id=customer.id,
                name=customer.name,
                phone=customer.phone,
                open=figures["open"],
                due=figures["due"],
                whatsapp=link,
            )
        )
    rows.sort(key=lambda row: (-row.due, row.name.lower()))
    return render(request, "web/customer_list.html", {"rows": rows, "query": query})
