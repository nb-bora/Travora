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
