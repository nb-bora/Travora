from datetime import date
from uuid import UUID

from django.db.models import Max
from django.utils import timezone

from apps.audit.services.public import AuditService
from apps.cases.services.public import CasesService
from apps.crm.services.public import CrmService
from apps.quotes import pdf, selectors
from apps.quotes.constants import QuoteStatus
from apps.quotes.dto import QuoteDelivery, QuoteView
from apps.quotes.exceptions import InvalidQuote, InvalidTransition
from apps.quotes.models import Quote
from apps.quotes.whatsapp import whatsapp_link
from apps.shared_kernel.actor import Actor
from apps.shared_kernel.money import format_xaf
from apps.tenancy.services.public import TenancyService


def create_draft(actor: Actor, *, case_id: UUID, valid_until: date) -> QuoteView:
    CasesService.require_open_case(actor, case_id)
    detail = CasesService.get_case(actor, case_id)
    lines = [
        {"label": line.label, "passenger_name": line.passenger_name, "price_xaf": line.price_xaf}
        for line in detail.lines
        if not line.is_voided
    ]
    if not lines:
        raise InvalidQuote("Le dossier n'a aucune ligne à chiffrer.")
    last = Quote.objects.filter(case_id=case_id).aggregate(last=Max("version"))["last"] or 0
    quote = Quote.objects.create(
        case_id=case_id,
        version=last + 1,
        valid_until=valid_until,
        lines=lines,
        created_by=actor.user_id,
    )
    return selectors.to_view(quote)


def send(actor: Actor, *, quote_id: UUID) -> QuoteDelivery:
    quote = selectors.get_quote(quote_id)
    if quote.status != QuoteStatus.DRAFT:
        raise InvalidTransition("Seul un brouillon peut être envoyé.")
    if quote.valid_until < timezone.localdate():
        raise InvalidQuote("La date de validité du devis est passée.")
    quote.status = QuoteStatus.SENT
    quote.sent_at = timezone.now()
    quote.save()

    view = selectors.to_view(quote)
    summary = CasesService.get_case(actor, quote.case_id).summary
    customer = CrmService.get_customer(actor, summary.customer_id)
    agency = TenancyService.agency_info(actor)
    message = (
        f"Bonjour {customer.name}, voici votre devis {summary.reference} d'un montant de "
        f"{format_xaf(view.total_xaf)}, valable jusqu'au {quote.valid_until:%d/%m/%Y}. "
        f"{agency.name}"
    )
    AuditService.record(
        actor_user_id=actor.user_id,
        action="quote.sent",
        object_type="quote",
        object_id=quote.id,
        metadata={"case_id": str(quote.case_id), "version": quote.version},
    )
    return QuoteDelivery(
        quote_id=quote.id,
        total_xaf=view.total_xaf,
        message=message,
        whatsapp_url=whatsapp_link(customer.phone, message),
    )


def _answer(actor: Actor, *, quote_id: UUID, status: QuoteStatus) -> QuoteView:
    quote = selectors.get_quote(quote_id)
    if quote.status != QuoteStatus.SENT:
        raise InvalidTransition("Seul un devis envoyé reçoit une réponse.")
    quote.status = status
    quote.save()
    AuditService.record(
        actor_user_id=actor.user_id,
        action=f"quote.{status.value}",
        object_type="quote",
        object_id=quote.id,
        metadata={"case_id": str(quote.case_id), "version": quote.version},
    )
    return selectors.to_view(quote)


def accept(actor: Actor, *, quote_id: UUID) -> QuoteView:
    return _answer(actor, quote_id=quote_id, status=QuoteStatus.ACCEPTED)


def refuse(actor: Actor, *, quote_id: UUID) -> QuoteView:
    return _answer(actor, quote_id=quote_id, status=QuoteStatus.REFUSED)


def render_quote_pdf(actor: Actor, *, quote_id: UUID) -> bytes:
    view = selectors.to_view(selectors.get_quote(quote_id))
    summary = CasesService.get_case(actor, view.case_id).summary
    agency = TenancyService.agency_info(actor)
    html = pdf.render_html(
        quote=view,
        reference=summary.reference,
        customer_name=summary.customer_name,
        agency_name=agency.name,
        logo_path=agency.logo_path,
    )
    return pdf.render_pdf(html)
