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


FIELD_ICONS = (
    (
        ("phone", "tel"),
        "M5 4h4l2 5-2.5 1.5a11 11 0 005 5L15 13l5 2v4a2 2 0 01-2 2A16 16 0 013 6a2 2 0 012-2z",
    ),
    (("mail",), "M3 5h18v14H3zM3 7l9 6 9-6"),
    (
        ("origin", "destination", "station", "city", "port"),
        "M12 21s7-6 7-11a7 7 0 10-14 0c0 5 7 11 7 11zM12 7.5a2.5 2.5 0 100 5 2.5 2.5 0 000-5z",
    ),
    (("time",), "M12 4a8 8 0 100 16 8 8 0 000-16zM12 8v4l3 2"),
    (("date", "_on", "_at"), "M4 6h16v14H4zM4 10h16M8 3v4M16 3v4"),
    (
        ("name", "holder", "passenger", "traveller"),
        "M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2M16 7a4 4 0 11-8 0 4 4 0 018 0z",
    ),
    (
        ("carrier", "company", "agency"),
        "M4 21V5l8-2v18M12 9h8v12M7 8h2M7 12h2M7 16h2M15 13h2M15 17h2",
    ),
    (
        ("document", "passport", "id_", "plate", "vehicle"),
        "M3 5h18v14H3zM8 11a2 2 0 100-4 2 2 0 000 4zM5 16a3 3 0 016 0M14 9h4M14 13h4",
    ),
    (
        ("ticket", "reference", "booking", "code"),
        "M5 9V6h14v3a2 2 0 000 4v3H5v-3a2 2 0 000-4zM10 6v10",
    ),
    (("xaf", "price", "cost", "fare", "tax", "fee", "amount"), METHOD_ICONS["cash"]),
    (("method",), METHOD_ICONS["transfer"]),
)
CHOICE_WIDGETS = {"radioselect", "checkbox", "checkboxselectmultiple"}


def _name(field: object) -> str:
    return str(getattr(field, "name", "")).lower()


@register.filter
def field_icon(field: object) -> str:
    """Tracé SVG de l'icône interne d'un champ, déduit de son nom ; vide si aucun ne convient."""
    name = _name(field)
    for keys, path in FIELD_ICONS:
        if any(key in name for key in keys):
            return path
    return ""


@register.filter
def field_prefix(field: object) -> str:
    return "+237" if "phone" in _name(field) else ""


@register.filter
def field_suffix(field: object) -> str:
    return "FCFA" if _name(field).endswith("_xaf") else ""


@register.filter
def field_state(field: object) -> str:
    """``invalid`` si le champ a une erreur, ``valid`` s'il a été soumis sans erreur."""
    if getattr(field, "errors", None):
        return "invalid"
    form = getattr(field, "form", None)
    if form is not None and form.is_bound and field.value():  # type: ignore[attr-defined]
        return "valid"
    return ""


@register.filter
def is_choice_widget(field: object) -> bool:
    return str(getattr(field, "widget_type", "")) in CHOICE_WIDGETS
