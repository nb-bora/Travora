"""Détails propres à chaque mode (horaire, place, pièce d'identité…), validés ici une seule fois.

Une ligne garde ses colonnes communes (libellé, passager, référence, prix, coût). Tout ce qui
dépend du mode va dans ``details`` : une liste fermée de clés par type de ligne, des textes
courts ou des entiers, jamais de structure libre. Les clés financières n'apparaissent pas dans
la vue d'un agent : elles révéleraient le coût.
"""

from collections.abc import Mapping
from typing import Any

from apps.cases.constants import LineKind
from apps.cases.exceptions import InvalidLine

TEXT_MAX = 120
INT_MAX = 10_000_000_000

_COMMON: dict[str, type] = {
    "origin": str,
    "destination": str,
    "departure_time": str,
    "arrival_time": str,
    "booking_reference": str,
    "travel_class": str,
    "bags": int,
    "traveller_phone": str,
}

ALLOWED: dict[LineKind, dict[str, type]] = {
    LineKind.AIR_TICKET: _COMMON
    | {
        "ticket_time_limit": str,
        "passenger_type": str,
        "fare_base_xaf": int,
        "taxes_xaf": int,
    },
    LineKind.BUS_TICKET: _COMMON | {"station": str, "seat": str},
    LineKind.TRAIN_TICKET: _COMMON
    | {
        "train": str,
        "car": str,
        "seat": str,
        "doc_type": str,
        "doc_number": str,
        "fare_type": str,
    },
    LineKind.BOAT_TICKET: _COMMON
    | {
        "ship": str,
        "check_in_opens": str,
        "check_in_closes": str,
        "doc_type": str,
        "doc_number": str,
        "birth_date": str,
        "nationality": str,
        "doc_expiry": str,
        "cabin": str,
        "vehicle_plate": str,
        "vehicle_type": str,
        "vehicle_length_m": str,
    },
    LineKind.FREE_SERVICE: {},
}

# Ne sortent jamais vers un agent : base + taxes reconstituent le coût d'achat.
FINANCIAL_KEYS = frozenset({"fare_base_xaf", "taxes_xaf"})


def clean_details(kind: LineKind, details: Mapping[str, Any] | None) -> dict[str, str | int]:
    """Renvoie les détails nettoyés, ou lève ``InvalidLine`` (clé inconnue, type, taille)."""
    allowed = ALLOWED[kind]
    cleaned: dict[str, str | int] = {}
    for key, value in (details or {}).items():
        if key not in allowed:
            raise InvalidLine(f"Détail non prévu pour ce type de ligne : {key}.")
        if value is None or value == "":
            continue
        if allowed[key] is int:
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= INT_MAX:
                raise InvalidLine(f"Détail numérique invalide : {key}.")
            cleaned[key] = value
        else:
            if not isinstance(value, str):
                raise InvalidLine(f"Détail texte invalide : {key}.")
            text = value.strip()
            if len(text) > TEXT_MAX:
                raise InvalidLine(f"Détail trop long : {key} ({TEXT_MAX} caractères au plus).")
            if text:
                cleaned[key] = text
    return cleaned


def visible_details(details: Mapping[str, Any], *, financials: bool) -> dict[str, Any]:
    """Les détails qu'un utilisateur a le droit de lire."""
    if financials:
        return dict(details)
    return {key: value for key, value in details.items() if key not in FINANCIAL_KEYS}
