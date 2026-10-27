"""Montants : entiers en francs CFA.

La liste officielle ISO 4217 donne au XAF une unité mineure de 0 : aucun montant
décimal n'est jamais saisi ni stocké.
"""

CURRENCY = "XAF"


def format_xaf(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " FCFA"
