from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from apps.quotes.constants import QuoteStatus


@dataclass(frozen=True)
class QuoteLineData:
    label: str
    passenger_name: str
    price_xaf: int


@dataclass(frozen=True)
class QuoteView:
    id: UUID
    case_id: UUID
    version: int
    status: QuoteStatus
    valid_until: date
    total_xaf: int
    sent_at: datetime | None
    is_expired: bool
    lines: tuple[QuoteLineData, ...]


@dataclass(frozen=True)
class QuoteDelivery:
    quote_id: UUID
    total_xaf: int
    message: str
    whatsapp_url: str
