from pathlib import Path

from django.template.loader import render_to_string

from apps.quotes.dto import QuoteView
from apps.shared_kernel.money import format_xaf


def render_html(
    *,
    quote: QuoteView,
    reference: str,
    customer_name: str,
    agency_name: str,
    logo_path: str,
) -> str:
    return render_to_string(
        "quotes/quote.html",
        {
            "agency_name": agency_name,
            "logo_uri": Path(logo_path).as_uri() if logo_path else "",
            "reference": reference,
            "version": quote.version,
            "customer_name": customer_name,
            "valid_until": quote.valid_until,
            "lines": [
                {
                    "label": line.label,
                    "passenger_name": line.passenger_name,
                    "price": format_xaf(line.price_xaf),
                }
                for line in quote.lines
            ],
            "total": format_xaf(quote.total_xaf),
        },
    )


def render_pdf(html: str) -> bytes:
    from weasyprint import HTML

    return HTML(string=html).write_pdf()
