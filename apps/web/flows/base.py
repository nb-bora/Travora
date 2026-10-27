from dataclasses import dataclass
from datetime import date
from typing import Any, ClassVar
from urllib.parse import quote

from django import forms

from apps.cases.dto import CaseDetail
from apps.web.flows.spec import LineSpec, Mode, Totals


@dataclass(frozen=True)
class Check:
    ok: bool
    title: str
    detail: str = ""


@dataclass(frozen=True)
class LedgerRow:
    account: str
    debit: int
    credit: int


def allocate(total: int, weights: list[int]) -> list[int]:
    """Répartit ``total`` selon ``weights`` sans perdre un franc (plus fort reste)."""
    weight_sum = sum(weights)
    if not weights:
        return []
    if weight_sum == 0:
        base, rest = divmod(total, len(weights))
        return [base + (1 if index < rest else 0) for index in range(len(weights))]
    shares = [total * weight // weight_sum for weight in weights]
    remainders = [total * weight % weight_sum for weight in weights]
    for index in sorted(range(len(weights)), key=lambda i: -remainders[i])[: total - sum(shares)]:
        shares[index] += 1
    return shares


class FlowDef:
    """Ce qui change d'un mode à l'autre ; le moteur (vues, gabarits) reste commun."""

    mode: ClassVar[Mode]
    trip_form: ClassVar[type[forms.Form]]
    traveller_form: ClassVar[type[forms.Form]]
    pricing_form: ClassVar[type[forms.Form]]
    extra_form: ClassVar[type[forms.Form] | None] = None
    pricing_step: ClassVar[int] = 3  # 2 pour l'avion : le tarif se saisit avec les passagers
    template_prefix: ClassVar[str]

    # --- lecture du brouillon -------------------------------------------------------------
    @staticmethod
    def trip(draft: dict[str, Any]) -> dict[str, Any]:
        return draft.get("trip", {})

    def route_label(self, draft: dict[str, Any]) -> str:
        trip = self.trip(draft)
        return f"{trip.get('origin', '')} → {trip.get('destination', '')}".strip(" →")

    def customer(self, draft: dict[str, Any]) -> tuple[str, str]:
        trip = self.trip(draft)
        return trip.get("customer_name", ""), trip.get("customer_phone", "")

    def subtitle(self, draft: dict[str, Any]) -> str:
        return self.route_label(draft)

    # --- règles propres au mode (à surcharger) --------------------------------------------
    def lines(self, draft: dict[str, Any]) -> list[LineSpec]:
        raise NotImplementedError

    def checks(self, draft: dict[str, Any]) -> list[Check]:
        raise NotImplementedError

    # --- crochets de présentation (valeurs par défaut) ------------------------------------
    def step1_hint(self, draft: dict[str, Any]) -> str:
        return "Rien n'est enregistré avant la confirmation de la vente"

    def step1_total(self, draft: dict[str, Any]) -> int | None:
        return None

    def step2_hint(self, draft: dict[str, Any]) -> str:
        return "Total client"

    def step2_total(self, draft: dict[str, Any]) -> int | None:
        return self.totals(draft).price_xaf if draft.get("travellers") else None

    def side_forms(self, post: Any, draft: dict[str, Any], *, bound: bool) -> dict[str, forms.Form]:
        """Formulaires saisis avec les voyageurs (tarif de l'avion, véhicule du bateau)."""
        return {}

    def save_side(self, draft: dict[str, Any], side: dict[str, forms.Form]) -> None:
        return None

    def pricing_kwargs(self, draft: dict[str, Any]) -> dict[str, Any]:
        return {}

    def default_travellers(self, draft: dict[str, Any]) -> list[dict[str, Any]]:
        return [{}]

    def aside(self, formset: Any) -> dict[str, Any]:
        """Contexte supplémentaire de l'étape des voyageurs (plan du car…)."""
        return {}

    def price_lines(self, draft: dict[str, Any]) -> list[dict[str, Any]]:
        """Détail du prix client (désignation, quantité, unitaire, total)."""
        return []

    def confirm_label(self, draft: dict[str, Any]) -> str:
        return "Confirmer la vente"

    def confirm_context(self, draft: dict[str, Any]) -> dict[str, Any]:
        return {}

    def schedule(self, total: int, departure: date | None) -> list[dict[str, Any]] | None:
        return None

    def message(self, detail: CaseDetail, customer: str, agency: str, due: int) -> str:
        raise NotImplementedError

    def done_context(self, detail: CaseDetail) -> dict[str, Any]:
        return {}

    @staticmethod
    def whatsapp_link(phone: str, message: str) -> str:
        """Lien « cliquer pour discuter » : l'agent envoie lui-même le message."""
        return f"https://wa.me/{phone.lstrip('+')}?text={quote(message)}" if phone else ""

    # --- calculs communs ------------------------------------------------------------------
    def totals(self, draft: dict[str, Any]) -> Totals:
        specs = self.lines(draft)
        return Totals(
            price_xaf=sum(spec.price_xaf for spec in specs),
            cost_xaf=sum(spec.cost_xaf or 0 for spec in specs),
            count=len(specs),
        )

    def ledger(self, draft: dict[str, Any]) -> list[LedgerRow]:
        """L'écriture de vente que la confirmation va enregistrer (gérant seulement)."""
        totals = self.totals(draft)
        rows = [LedgerRow("Compte client", totals.price_xaf, 0)]
        rows.append(LedgerRow("Fournisseur", 0, totals.cost_xaf))
        margin = totals.margin_xaf
        rows.append(LedgerRow("Marge", -margin if margin < 0 else 0, margin if margin > 0 else 0))
        return [row for row in rows if row.debit or row.credit]
