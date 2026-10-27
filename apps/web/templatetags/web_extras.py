from django import template

register = template.Library()

NARROW_NBSP = " "
NBSP = " "


@register.filter
def xaf(amount: int | None) -> str:
    """``1 250 000 FCFA`` avec espaces fines insécables ; vide si le montant est masqué."""
    if amount is None:
        return ""
    return f"{amount:,}".replace(",", NARROW_NBSP) + NBSP + "FCFA"


KIND_ICONS = {
    "air_ticket": "M2 16l20-7-7 13-3-6z",
    "bus_ticket": "M5 16V6a2 2 0 012-2h10a2 2 0 012 2v10M5 16h14M5 12h14M8 20v-4M16 20v-4",
    "train_ticket": (
        "M7 3h10a2 2 0 012 2v10a3 3 0 01-3 3H8a3 3 0 01-3-3V5a2 2 0 012-2z"
        "M5 11h14M9 21l2-3M15 21l-2-3"
    ),
    "boat_ticket": "M3 17l2 4h14l2-4zM12 3v10M12 5l6 6h-6",
    "free_service": "M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.7 6.6 19.5l1.2-6L3.3 9.3l6.1-.7z",
}


@register.filter
def kind_icon(kind: object) -> str:
    """Tracé SVG (viewBox 24) de l'icône d'un type de ligne."""
    return KIND_ICONS.get(getattr(kind, "value", str(kind)), KIND_ICONS["free_service"])


METHOD_ICONS = {
    "cash": "M2 7h20v10H2zM12 9.5a2.5 2.5 0 100 5 2.5 2.5 0 000-5zM6 12h.01M18 12h.01",
    "mobile_money": "M8 2h8a1 1 0 011 1v18a1 1 0 01-1 1H8a1 1 0 01-1-1V3a1 1 0 011-1zM11 18h2",
    "transfer": "M3 10l9-6 9 6M5 10v8M9 10v8M15 10v8M19 10v8M3 21h18",
}


@register.filter
def method_icon(method: object) -> str:
    """Tracé SVG (viewBox 24) de l'icône d'un mode de paiement."""
    return METHOD_ICONS.get(str(method), METHOD_ICONS["cash"])


@register.filter
def first_word(value: str) -> str:
    """Prénom approximatif pour « Message pour Marie »."""
    parts = str(value).split()
    return parts[0] if parts else ""
