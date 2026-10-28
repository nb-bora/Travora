"""Devis : liste, création depuis un dossier, envoi par WhatsApp, PDF, réponse du client."""

from dataclasses import dataclass
from uuid import UUID

from django import forms
from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.cases.dto import CaseSummary
from apps.cases.exceptions import CaseNotFound
from apps.cases.services.public import CasesService
from apps.quotes.constants import QuoteStatus
from apps.quotes.dto import QuoteView
from apps.quotes.exceptions import QuoteNotFound
from apps.quotes.services.public import QuotesService
from apps.web.access import _actor, agency_required
from apps.web.errors import attempt
from apps.web.forms import WebForm

DEFAULT_VALIDITY_DAYS = 15
DELIVERY_KEY = "quote_delivery"

TABS = (
    ("tous", "Tous"),
    ("draft", "Brouillons"),
    ("sent", "Envoyés"),
    ("accepted", "Acceptés"),
    ("refused", "Refusés"),
    ("expired", "Expirés"),
)

STATUS_BADGES = {
    QuoteStatus.DRAFT: "badge-neutral",
    QuoteStatus.SENT: "badge-info",
    QuoteStatus.ACCEPTED: "badge-success",
    QuoteStatus.REFUSED: "badge-danger",
}


class QuoteForm(WebForm):
    valid_until = forms.DateField(
        label="Valable jusqu'au",
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )

    def clean_valid_until(self):  # type: ignore[no-untyped-def]
        value = self.cleaned_data["valid_until"]
        if value < timezone.localdate():
            raise forms.ValidationError("Choisissez une date à venir.")
        return value


@dataclass(frozen=True)
class QuoteRow:
    quote: QuoteView
    reference: str
    customer_name: str
    badge: str
    label: str


def _label(quote: QuoteView) -> str:
    return "Expiré" if quote.is_expired else quote.status.label


def _badge(quote: QuoteView) -> str:
    return "badge-warning" if quote.is_expired else STATUS_BADGES[quote.status]


def _row(quote: QuoteView, cases: dict[UUID, CaseSummary]) -> QuoteRow:
    case = cases.get(quote.case_id)
    return QuoteRow(
        quote=quote,
        reference=case.reference if case else "—",
        customer_name=case.customer_name if case else "—",
        badge=_badge(quote),
        label=_label(quote),
    )


def _matches(tab: str, quote: QuoteView) -> bool:
    if tab == "expired":
        return quote.is_expired
    if tab in ("draft", "sent", "accepted", "refused"):
        return quote.status.value == tab and not quote.is_expired
    return True


@agency_required
@require_GET
def quote_list(request: HttpRequest) -> HttpResponse:
    actor = _actor(request)
    cases = {case.id: case for case in CasesService.list_cases(actor)}
    quotes = QuotesService.list_quotes(actor)
    tab = request.GET.get("etat", "tous")
    if tab not in dict(TABS):
        tab = "tous"
    query = request.GET.get("q", "").strip().lower()
    rows = [_row(quote, cases) for quote in quotes if _matches(tab, quote)]
    if query:
        rows = [
            row
            for row in rows
            if query in row.reference.lower() or query in row.customer_name.lower()
        ]
    counts = {slug: sum(1 for quote in quotes if _matches(slug, quote)) for slug, _ in TABS}
    context = {
        "rows": rows,
        "tabs": [(slug, label, counts[slug]) for slug, label in TABS],
        "current": tab,
        "query": request.GET.get("q", "").strip(),
        "waiting": counts["sent"],
        "expired": counts["expired"],
    }
    return render(request, "web/quote_list.html", context)


def _load(request: HttpRequest, quote_id: UUID) -> tuple[QuoteView, CaseSummary]:
    actor = _actor(request)
    try:
        quote = QuotesService.get_quote(actor, quote_id)
        summary = CasesService.get_case(actor, quote.case_id).summary
    except (QuoteNotFound, CaseNotFound) as error:
        raise Http404 from error
    return quote, summary


@agency_required
@require_GET
def quote_detail(request: HttpRequest, quote_id: UUID) -> HttpResponse:
    quote, summary = _load(request, quote_id)
    stored = request.session.pop(DELIVERY_KEY, None)
    delivery = stored if stored and stored.get("quote_id") == str(quote_id) else None
    context = {
        "quote": quote,
        "summary": summary,
        "badge": _badge(quote),
        "label": _label(quote),
        "is_draft": quote.status is QuoteStatus.DRAFT,
        "is_sent": quote.status is QuoteStatus.SENT,
        "delivery": delivery,
    }
    return render(request, "web/quote_detail.html", context)


def _to_detail(quote_id: UUID) -> HttpResponse:
    return redirect(reverse("web:quote_detail", kwargs={"quote_id": quote_id}))


@agency_required
@require_POST
def quote_create(request: HttpRequest, case_id: UUID) -> HttpResponse:
    actor = _actor(request)
    target = reverse("web:case_detail", kwargs={"case_id": case_id})
    form = QuoteForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Choisissez une date de validité à venir pour le devis.")
        return redirect(target)
    valid_until = form.cleaned_data["valid_until"]
    created = attempt(
        request,
        lambda: QuotesService.create_draft(actor, case_id=case_id, valid_until=valid_until),
        "Devis créé : relisez-le, puis envoyez-le au client.",
    )
    return _to_detail(created.id) if created is not None else redirect(target)


@agency_required
@require_POST
def quote_send(request: HttpRequest, quote_id: UUID) -> HttpResponse:
    actor = _actor(request)
    delivery = attempt(
        request, lambda: QuotesService.send(actor, quote_id=quote_id), "Devis envoyé."
    )
    if delivery is not None:
        request.session[DELIVERY_KEY] = {
            "quote_id": str(quote_id),
            "message": delivery.message,
            "whatsapp_url": delivery.whatsapp_url,
        }
    return _to_detail(quote_id)


@agency_required
@require_POST
def quote_accept(request: HttpRequest, quote_id: UUID) -> HttpResponse:
    actor = _actor(request)
    attempt(
        request,
        lambda: QuotesService.accept(actor, quote_id=quote_id),
        "Devis accepté par le client.",
    )
    return _to_detail(quote_id)


@agency_required
@require_POST
def quote_refuse(request: HttpRequest, quote_id: UUID) -> HttpResponse:
    actor = _actor(request)
    attempt(request, lambda: QuotesService.refuse(actor, quote_id=quote_id), "Devis refusé.")
    return _to_detail(quote_id)


@agency_required
@require_GET
def quote_pdf(request: HttpRequest, quote_id: UUID) -> HttpResponse:
    quote, summary = _load(request, quote_id)
    content = QuotesService.render_pdf(_actor(request), quote_id=quote_id)
    response = HttpResponse(content, content_type="application/pdf")
    name = f"devis-{summary.reference}-v{quote.version}.pdf"
    response["Content-Disposition"] = f'inline; filename="{name}"'
    return response
