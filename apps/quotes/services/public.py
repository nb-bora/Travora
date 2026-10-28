"""Façade publique de l'application quotes."""

from datetime import date
from uuid import UUID

from apps.quotes import selectors
from apps.quotes.dto import QuoteDelivery, QuoteView
from apps.quotes.services import commands
from apps.shared_kernel.actor import Actor


class QuotesService:
    @staticmethod
    def create_draft(actor: Actor, *, case_id: UUID, valid_until: date) -> QuoteView:
        return commands.create_draft(actor, case_id=case_id, valid_until=valid_until)

    @staticmethod
    def send(actor: Actor, *, quote_id: UUID) -> QuoteDelivery:
        return commands.send(actor, quote_id=quote_id)

    @staticmethod
    def accept(actor: Actor, *, quote_id: UUID) -> QuoteView:
        return commands.accept(actor, quote_id=quote_id)

    @staticmethod
    def refuse(actor: Actor, *, quote_id: UUID) -> QuoteView:
        return commands.refuse(actor, quote_id=quote_id)

    @staticmethod
    def render_pdf(actor: Actor, *, quote_id: UUID) -> bytes:
        return commands.render_quote_pdf(actor, quote_id=quote_id)

    @staticmethod
    def quotes_for_case(actor: Actor, case_id: UUID) -> list[QuoteView]:
        return selectors.quotes_for_case(case_id)

    @staticmethod
    def list_quotes(actor: Actor) -> list[QuoteView]:
        return selectors.all_quotes()

    @staticmethod
    def get_quote(actor: Actor, quote_id: UUID) -> QuoteView:
        return selectors.to_view(selectors.get_quote(quote_id))

    @staticmethod
    def expired_sent_quotes(actor: Actor, *, as_of: date | None = None) -> list[QuoteView]:
        return selectors.expired_sent_quotes(as_of)
