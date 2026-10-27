from typing import cast
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.cases.constants import CaseStatus, LineKind
from apps.cases.exceptions import CaseNotFound
from apps.cases.services.public import CasesService
from apps.crm.services.public import CrmService
from apps.dashboard.services.public import DashboardService
from apps.payments.constants import PaymentMethod
from apps.payments.services.public import PaymentsService
from apps.shared_kernel.actor import Actor
from apps.tenancy.middleware import TenantRequest
from apps.web.errors import attempt, reporting
from apps.web.forms import CaseForm, LineForm, PaymentForm, QuickEntryForm


class NoAgency(Exception):
    """Authentifié mais sans agence active (aucune appartenance, ou agence suspendue)."""


def _actor(request: HttpRequest) -> Actor:
    actor = cast(TenantRequest, request).actor
    if actor is None:
        raise NoAgency
    return actor


def agency_required(view):  # type: ignore[no-untyped-def]
    """Exige un utilisateur connecté avec une agence active ; sinon redirige ou explique."""

    def wrapper(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        try:
            return view(request, *args, **kwargs)
        except NoAgency:
            return render(request, "web/no_agency.html", status=403)

    wrapper.__name__ = view.__name__
    return wrapper


@agency_required
@require_GET
def today(request: HttpRequest) -> HttpResponse:
    """Écran d'accueil : les chiffres du jour. Le rôle décide de ce qui est montré."""
    actor = _actor(request)
    return render(
        request,
        "web/today.html",
        {
            "snapshot": DashboardService.snapshot(actor),
            "is_manager": actor.can_view_financials,
            "quick_form": QuickEntryForm(),
        },
    )


@agency_required
@require_POST
def quick_entry(request: HttpRequest) -> HttpResponse:
    """Crée le client, le dossier et sa première ligne en un seul geste, ou rien du tout."""
    actor = _actor(request)
    form = QuickEntryForm(request.POST)
    if not form.is_valid():
        context = {
            "snapshot": DashboardService.snapshot(actor),
            "is_manager": actor.can_view_financials,
            "quick_form": form,
        }
        return render(request, "web/today.html", context, status=422)
    data = form.cleaned_data
    case_id: UUID | None = None
    with reporting(request):
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
    if case_id is None:
        return redirect("web:today")
    messages.success(request, "Dossier créé avec sa première ligne.")
    return redirect("web:case_detail", case_id=case_id)


FILTERS = {
    "ouverts": ("Ouverts", CaseStatus.OPEN),
    "clos": ("Clos", CaseStatus.CLOSED),
    "annules": ("Annulés", CaseStatus.CANCELLED),
    "tous": ("Tous", None),
}


@agency_required
@require_GET
def case_list(request: HttpRequest) -> HttpResponse:
    actor = _actor(request)
    key = request.GET.get("etat", "ouverts")
    if key not in FILTERS:
        key = "ouverts"
    cases = CasesService.list_cases(actor, status=FILTERS[key][1])
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
            "filters": [(slug, label) for slug, (label, _) in FILTERS.items()],
            "current": key,
            "query": query,
            "is_manager": actor.can_view_financials,
            "today": timezone.localdate(),
        },
    )


@agency_required
@require_http_methods(["GET", "POST"])
def case_create(request: HttpRequest) -> HttpResponse:
    actor = _actor(request)
    form = CaseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        case_id: UUID | None = None
        with reporting(request):
            customer = CrmService.find_or_create_customer(
                actor, name=data["customer_name"], phone=data["customer_phone"]
            )
            case_id = CasesService.create_case(
                actor, customer_id=customer.id, departure_date=data["departure_date"]
            )
        if case_id is not None:
            messages.success(request, "Dossier créé.")
            return redirect("web:case_detail", case_id=case_id)
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
        "line_form": line_form or LineForm(),
        "payment_form": payment_form or PaymentForm(),
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
    attempt(
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
    return redirect("web:case_detail", case_id=case_id)


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
            idempotency_key=f"web:{case_id}:{data['idempotency_key']}",
        ),
        "Encaissement enregistré.",
    )
    return redirect("web:case_detail", case_id=case_id)


def _line_action(request: HttpRequest, case_id: UUID, line_id: UUID, name: str) -> HttpResponse:
    actor = _actor(request)
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
