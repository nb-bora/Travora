"""Parcours guidés : un fil commun (voyage, voyageurs, prix, paiement, remise) par mode.

Un parcours garde un **brouillon** dans la session de l'utilisateur. Rien n'est écrit en base
avant la confirmation de la vente (étape 3) : à ce moment seulement, le client, le dossier et
toutes les lignes sont créés d'un seul bloc, ou rien du tout.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any

from django.http import HttpRequest

from apps.cases.constants import LineKind

DRAFT_KEY = "flow_drafts"
MAX_TRAVELLERS = 9


@dataclass(frozen=True)
class Mode:
    slug: str
    label: str
    kind: LineKind
    steps: tuple[str, ...]  # libellés des cinq étapes
    traveller_word: str  # « passager », « voyageur »…
    price_label: str  # « Prix client »


MODES: dict[str, Mode] = {
    "air": Mode(
        "air", "Avion", LineKind.AIR_TICKET,
        ("Billet", "Passagers", "Émission", "Paiement", "Remise"), "passager", "Tarif",
    ),
    "bus": Mode(
        "bus", "Bus", LineKind.BUS_TICKET,
        ("Départ", "Voyageurs", "Prix", "Paiement", "Billet"), "voyageur", "Prix",
    ),
    "train": Mode(
        "train", "Train", LineKind.TRAIN_TICKET,
        ("Train", "Voyageur", "Prix", "Paiement", "Billet"), "voyageur", "Prix",
    ),
    "boat": Mode(
        "boat", "Bateau", LineKind.BOAT_TICKET,
        ("Traversée", "Passagers", "Prix", "Paiement", "Embarquement"), "passager", "Prix",
    ),
}  # fmt: skip

MODE_BY_KIND = {mode.kind: mode for mode in MODES.values()}


@dataclass(frozen=True)
class LineSpec:
    """Une ligne à créer au moment de la confirmation."""

    kind: LineKind
    label: str
    price_xaf: int
    cost_xaf: int | None
    passenger_name: str = ""
    ticket_number: str = ""
    carrier: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Totals:
    price_xaf: int
    cost_xaf: int
    count: int

    @property
    def margin_xaf(self) -> int:
        return self.price_xaf - self.cost_xaf


def to_json(value: Any) -> Any:
    """Convertit ce que renvoient les formulaires en valeurs que la session sait stocker."""
    if isinstance(value, datetime):
        return value.isoformat(timespec="minutes")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, dict):
        return {key: to_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json(item) for item in value]
    return value


def new_draft(mode: str, token: str) -> dict[str, Any]:
    return {"mode": mode, "token": token, "trip": {}, "travellers": [], "pricing": {}, "done": 0}


def get_draft(request: HttpRequest, mode: str) -> dict[str, Any] | None:
    drafts: dict[str, Any] = request.session.get(DRAFT_KEY, {})
    return drafts.get(mode)


def save_draft(request: HttpRequest, draft: dict[str, Any]) -> None:
    drafts: dict[str, Any] = request.session.get(DRAFT_KEY, {})
    drafts[draft["mode"]] = draft
    request.session[DRAFT_KEY] = drafts


def clear_draft(request: HttpRequest, mode: str) -> None:
    drafts: dict[str, Any] = request.session.get(DRAFT_KEY, {})
    drafts.pop(mode, None)
    request.session[DRAFT_KEY] = drafts
