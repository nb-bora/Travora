"""Parcours avion : billet électronique à 13 chiffres, délai d'émission, tarif et taxes séparés."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, ClassVar

from django import forms
from django.utils import timezone

from apps.cases.constants import LineKind
from apps.cases.dto import CaseDetail, TicketProposal
from apps.cases.services.public import CasesService
from apps.web.flows.base import Check, FlowDef
from apps.web.flows.fields import (
    WebForm,
    amount,
    clean_phone,
    date_field,
    datetime_field,
    text,
    time_field,
    upper_code,
)
from apps.web.flows.spec import MODES, LineSpec, to_json

PASSENGER_TYPES = [("adult", "Adulte"), ("child", "Enfant"), ("infant", "Bébé")]
NARROW = " "


def plural(count: int, singular: str, plural_form: str | None = None) -> str:
    return singular if count <= 1 else (plural_form or singular + "s")


def money(value: int) -> str:
    return f"{value:,}".replace(",", NARROW) + " FCFA"


class AirTripForm(WebForm):
    UNIQUE = ()
    origin = text("Départ", max_length=80, placeholder="Douala (DLA)")
    destination = text("Arrivée", max_length=80, placeholder="Paris (CDG)")
    departure_date = date_field("Date de départ")
    departure_time = time_field("Heure de départ")
    arrival_time = time_field("Heure d'arrivée")
    carrier = text("Compagnie", max_length=120, required=False)
    booking_reference = text("Référence de réservation", max_length=12, required=False)
    ticket_time_limit = datetime_field("Émettre avant le")
    customer_name = text("Client", max_length=200)
    customer_phone = text(
        "Téléphone du client", max_length=32, required=False, placeholder="+237 6…"
    )

    def clean_booking_reference(self) -> str:
        return upper_code(self.cleaned_data["booking_reference"], length=6, label="Une référence")

    def clean_customer_phone(self) -> str:
        return clean_phone(self.cleaned_data["customer_phone"])


class AirTravellerForm(WebForm):
    UNIQUE = ("ticket_number",)
    name = text("Nom sur le billet", max_length=200, placeholder="NDONG/MARIE MS")
    passenger_type = forms.ChoiceField(label="Type", choices=PASSENGER_TYPES, initial="adult")
    ticket_number = text("Numéro de billet", max_length=20, placeholder="057 2345678901")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        number = str(self.initial.get("ticket_number", ""))
        if len(number) == 13 and number.isdigit():
            self.initial["ticket_number"] = f"{number[:3]} {number[3:]}"

    def clean_ticket_number(self) -> str:
        digits = "".join(ch for ch in self.cleaned_data["ticket_number"] if ch in "0123456789")
        if len(digits) != 13:
            raise forms.ValidationError("Un numéro de billet aérien compte 13 chiffres.")
        return digits

    def clean_name(self) -> str:
        return self.cleaned_data["name"].strip().upper()


class AirPricingForm(WebForm):
    fare_base_xaf = amount("Tarif de base (FCFA)")
    taxes_xaf = amount("Taxes et surcharges (FCFA)")
    agency_fee_xaf = amount("Frais d'agence (FCFA)")
    cost_xaf = amount("Coût d'achat par passager (FCFA)")


@dataclass(frozen=True)
class PasteResult:
    draft: dict[str, Any]
    proposal: TicketProposal
    timeline: dict[str, str]
    count: int


def initials(name: str) -> str:
    parts = name.replace("/", " ").split()
    return "".join(part[0] for part in parts[:2]).upper() or "?"


def time_left(draft: dict[str, Any]) -> dict[str, Any] | None:
    """Délai d'émission : titre, temps restant et pourcentage restant sur 72 h."""
    raw = draft.get("trip", {}).get("ticket_time_limit")
    if not raw:
        return None
    limit = datetime.fromisoformat(raw)
    if timezone.is_naive(limit):
        limit = timezone.make_aware(limit)
    remaining = limit - timezone.now()
    title = "À émettre avant le " + timezone.localtime(limit).strftime("%d/%m/%Y à %H:%M")
    if remaining <= timedelta(0):
        return {"title": title, "left": "Délai dépassé", "percent": 0, "late": True}
    days, hours = remaining.days, remaining.seconds // 3600
    left = f"Il reste {days} j {hours} h" if days else f"Il reste {hours} h"
    percent = max(4, min(100, int(remaining / timedelta(hours=72) * 100)))
    return {"title": title, "left": left, "percent": percent, "late": False}


def prefill_from_proposal(proposal: TicketProposal) -> dict[str, Any]:
    """Brouillon initial d'un collage de billet : tout est à confirmer par l'agent."""
    trip = {
        "origin": proposal.origin,
        "destination": proposal.destination,
        "departure_date": proposal.departure_date.isoformat() if proposal.departure_date else "",
        "carrier": proposal.carrier,
        "booking_reference": proposal.booking_reference,
        "customer_name": proposal.customer_name,
        "departure_time": proposal.departure_time,
        "arrival_time": proposal.arrival_time,
    }
    names = list(proposal.passengers) or [""]
    numbers = list(proposal.ticket_numbers)
    travellers = []
    for index in range(max(len(names), len(numbers), 1)):
        travellers.append(
            {
                "name": names[index] if index < len(names) else "",
                "passenger_type": "adult",
                "ticket_number": numbers[index] if index < len(numbers) else "",
            }
        )
    pricing = {"fare_base_xaf": proposal.price_xaf} if proposal.price_xaf else {}
    return {"trip": {k: v for k, v in trip.items() if v}, "travellers": travellers,
            "pricing": pricing}  # fmt: skip


def recognised(proposal: TicketProposal) -> int:
    """Nombre d'éléments lus dans le texte collé (pour « 6 éléments sûrs »)."""
    return sum(
        bool(item)
        for item in (
            proposal.ticket_numbers,
            proposal.passengers,
            proposal.origin,
            proposal.departure_date,
            proposal.carrier,
            proposal.booking_reference,
            proposal.price_xaf,
        )
    )


def timeline_of(proposal: TicketProposal) -> dict[str, str]:
    """Horaires et durée du vol, quand le texte donne les deux heures."""
    dep, arr = proposal.departure_time, proposal.arrival_time
    duration = ""
    if dep and arr:
        start = datetime.strptime(dep, "%H:%M")
        end = datetime.strptime(arr, "%H:%M")
        minutes = int((end - start).total_seconds() // 60)
        if minutes < 0:
            minutes += 24 * 60
        duration = f"{minutes // 60} h {minutes % 60:02d}"
    return {"dep_time": dep, "arr_time": arr, "duration": duration}


AIR_NEXT = [
    {
        "title": "Rappel la veille",
        "tag": "Proposé",
        "tone": "info",
        "text": "Prévenir le client la veille avec l'heure et le terminal.",
    },
    {
        "title": "Relancer le solde",
        "tag": "Automatique",
        "tone": "warning",
        "text": "Un rappel s'affichera si le retard dépasse 10 jours.",
    },
    {
        "title": "Annuler un billet",
        "tag": "Gérant",
        "tone": "neutral",
        "text": "Réservé au gérant. Écriture inverse, avec trace d'audit.",
    },
]


class AirFlow(FlowDef):
    mode = MODES["air"]
    trip_form: ClassVar = AirTripForm
    traveller_form: ClassVar = AirTravellerForm
    pricing_form: ClassVar = AirPricingForm
    pricing_step = 2
    template_prefix = "web/flow/air"

    # --- présentation --------------------------------------------------------------------
    def subtitle(self, draft: dict[str, Any]) -> str:
        trip = self.trip(draft)
        parts = [self.route_label(draft)]
        if trip.get("departure_date"):
            parts.append(datetime.fromisoformat(trip["departure_date"]).strftime("%d/%m/%Y"))
        if trip.get("customer_name"):
            parts.append(trip["customer_name"])
        return " · ".join(part for part in parts if part)

    def step1_hint(self, draft: dict[str, Any]) -> str:
        return "Rien n'est enregistré avant l'émission"

    def per_passenger(self, draft: dict[str, Any]) -> int:
        pricing = draft.get("pricing", {})
        return sum(pricing.get(key, 0) for key in ("fare_base_xaf", "taxes_xaf", "agency_fee_xaf"))

    def step2_total(self, draft: dict[str, Any]) -> int | None:
        if not draft.get("pricing"):
            return None
        return self.per_passenger(draft) * max(len(draft.get("travellers", [])), 1)

    def paste(self, text: str) -> PasteResult:
        proposal = CasesService.propose_booking(text[:5_000], today=timezone.localdate())
        draft = prefill_from_proposal(proposal) if proposal.recognised else {}
        return PasteResult(
            draft=draft,
            proposal=proposal,
            timeline=timeline_of(proposal),
            count=recognised(proposal),
        )

    # --- tarif saisi avec les passagers --------------------------------------------------
    def side_forms(self, post: Any, draft: dict[str, Any], *, bound: bool) -> dict[str, forms.Form]:
        if post is not None and bound:
            return {"pricing_form": AirPricingForm(post, prefix="pricing")}
        initial = draft.get("pricing", {})
        if post is not None:
            initial = {name: post.get(f"pricing-{name}", "") for name in AirPricingForm.base_fields}
        return {"pricing_form": AirPricingForm(initial=initial, prefix="pricing")}

    def save_side(self, draft: dict[str, Any], side: dict[str, forms.Form]) -> None:
        draft["pricing"] = to_json(side["pricing_form"].cleaned_data)

    # --- lignes, contrôles, confirmation ------------------------------------------------
    def lines(self, draft: dict[str, Any]) -> list[LineSpec]:
        trip, pricing = self.trip(draft), draft.get("pricing", {})
        common = {
            "origin": trip.get("origin", ""),
            "destination": trip.get("destination", ""),
            "departure_time": trip.get("departure_time", ""),
            "arrival_time": trip.get("arrival_time", ""),
            "booking_reference": trip.get("booking_reference", ""),
            "ticket_time_limit": trip.get("ticket_time_limit", ""),
            "traveller_phone": trip.get("customer_phone", ""),
            "fare_base_xaf": pricing.get("fare_base_xaf", 0),
            "taxes_xaf": pricing.get("taxes_xaf", 0),
        }
        return [
            LineSpec(
                kind=LineKind.AIR_TICKET,
                label=self.route_label(draft),
                price_xaf=self.per_passenger(draft),
                cost_xaf=pricing.get("cost_xaf"),
                passenger_name=traveller["name"],
                ticket_number=traveller["ticket_number"],
                carrier=trip.get("carrier", ""),
                details=common | {"passenger_type": traveller["passenger_type"]},
            )
            for traveller in draft.get("travellers", [])
        ]

    def checks(self, draft: dict[str, Any]) -> list[Check]:
        trip, travellers = self.trip(draft), draft.get("travellers", [])
        count = len(travellers)
        numbers = [t["ticket_number"] for t in travellers]
        formatted = " · ".join(f"{n[:3]} {n[3:]}" for n in numbers)
        when = ""
        if trip.get("departure_date"):
            when = datetime.fromisoformat(trip["departure_date"]).strftime("%d/%m/%Y")
        if trip.get("departure_time"):
            when += f" à {trip['departure_time']}"
        itinerary = f"{self.route_label(draft)}, {when}"
        if trip.get("carrier"):
            itinerary += f", {trip['carrier']}"
        return [
            Check(True, "Itinéraire vérifié", itinerary),
            Check(
                count > 0,
                f"{count} {plural(count, 'passager nommé', 'passagers nommés')}",
                " · ".join(t["name"] for t in travellers),
            ),
            Check(
                len(set(numbers)) == len(numbers) and all(len(n) == 13 for n in numbers),
                "Numéros de billet saisis",
                f"{formatted} (13 chiffres chacun)",
            ),
            Check(
                draft.get("pricing", {}).get("cost_xaf") is not None,
                "Coût d'achat renseigné",
                "Sans coût, une ligne ne peut pas être émise",
            ),
            Check(
                self.totals(draft).price_xaf > 0,
                "Prix client fixé",
                f"{money(self.totals(draft).price_xaf)} pour {count} {plural(count, 'passager')}",
            ),
        ]

    def confirm_label(self, draft: dict[str, Any]) -> str:
        count = len(draft.get("travellers", []))
        return "Émettre le billet" if count == 1 else f"Émettre les {count} billets"

    def confirm_context(self, draft: dict[str, Any]) -> dict[str, Any]:
        return {
            "ttl": time_left(draft),
            "booking_reference": self.trip(draft).get("booking_reference", ""),
        }

    # --- remise -------------------------------------------------------------------------
    def message(self, detail: CaseDetail, customer: str, agency: str, due: int) -> str:
        lines = [line for line in detail.lines if not line.is_voided]
        first = lines[0] if lines else None
        details = first.details if first else {}
        head = f"Bonjour {customer.split()[0] if customer else ''}, voici votre voyage "
        head += first.label if first else ""
        if detail.summary.departure_date:
            head += f" le {detail.summary.departure_date:%d/%m/%Y}"
        extras = [first.carrier if first else "", ""]
        if details.get("departure_time"):
            extras[1] = f"départ {details['departure_time']}"
        extra_text = ", ".join(part for part in extras if part)
        parts = [head + (f" ({extra_text})." if extra_text else ".")]
        tickets = ", ".join(
            f"{line.ticket_number[:3]}-{line.ticket_number[3:]} ({line.passenger_name})"
            for line in lines
        )
        if tickets:
            parts.append(f"Billets : {tickets}.")
        reference = details.get("booking_reference")
        parts.append(
            (f"Référence : {reference}. " if reference else "")
            + "Présentez-vous à l'aéroport 3 h avant le départ."
        )
        if due:
            parts.append(f"Solde restant : {money(due)}.")
        parts.append(f"— {agency}")
        return "\n".join(parts)

    def done_context(self, detail: CaseDetail) -> dict[str, Any]:
        return {"next_cards": AIR_NEXT}


AIR = AirFlow()
