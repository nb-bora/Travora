from datetime import date
from uuid import UUID

from django.utils import timezone

from apps.quotes.constants import QuoteStatus
from apps.quotes.dto import QuoteLineData, QuoteView
from apps.quotes.exceptions import QuoteNotFound
from apps.quotes.models import Quote


def to_view(quote: Quote) -> QuoteView:
    lines = tuple(
        QuoteLineData(
            label=item["label"],
            passenger_name=item["passenger_name"],
            price_xaf=item["price_xaf"],
        )
        for item in quote.lines
    )
    return QuoteView(
        id=quote.id,
        case_id=quote.case_id,
        version=quote.version,
        status=QuoteStatus(quote.status),
        valid_until=quote.valid_until,
        total_xaf=sum(line.price_xaf for line in lines),
        sent_at=quote.sent_at,
        is_expired=quote.status == QuoteStatus.SENT and quote.valid_until < timezone.localdate(),
        lines=lines,
    )


def get_quote(quote_id: UUID) -> Quote:
    quote = Quote.objects.filter(id=quote_id).first()
    if quote is None:
        raise QuoteNotFound(str(quote_id))
    return quote


def quotes_for_case(case_id: UUID) -> list[QuoteView]:
    return [to_view(quote) for quote in Quote.objects.filter(case_id=case_id).order_by("version")]


def expired_sent_quotes(as_of: date | None = None) -> list[QuoteView]:
    quotes = Quote.objects.filter(
        status=QuoteStatus.SENT, valid_until__lt=as_of or timezone.localdate()
    ).order_by("valid_until", "id")
    return [to_view(quote) for quote in quotes]
