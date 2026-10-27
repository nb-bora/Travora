"""Contrôle de l'image de production : le rendu PDF réel fonctionne (Pango et polices)."""

import os
import sys
import uuid
from datetime import date

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
django.setup()

from apps.quotes import pdf  # noqa: E402
from apps.quotes.constants import QuoteStatus  # noqa: E402
from apps.quotes.dto import QuoteLineData, QuoteView  # noqa: E402


def main() -> int:
    quote = QuoteView(
        id=uuid.uuid7(),
        case_id=uuid.uuid7(),
        version=1,
        status=QuoteStatus.DRAFT,
        valid_until=date(2026, 12, 31),
        total_xaf=680_000,
        sent_at=None,
        is_expired=False,
        lines=(
            QuoteLineData("DLA-CDG", "NDONG/MARIE", 500_000),
            QuoteLineData("Hôtel Paris, 2 nuits", "", 180_000),
        ),
    )
    html = pdf.render_html(
        quote=quote,
        reference="2026-0001",
        customer_name="Marie Ndong",
        agency_name="Agence d'essai",
        logo_path="",
    )
    data = pdf.render_pdf(html)
    if not data.startswith(b"%PDF"):
        print("Le rendu n'a pas produit un PDF.")
        return 1
    print(f"PDF produit : {len(data)} octets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
