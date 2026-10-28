"""Parcours bus : départ et gare, places numérotées, plusieurs voyageurs, Mobile Money."""

from datetime import datetime
from typing import Any, ClassVar

from django import forms

from apps.cases.constants import LineKind
from apps.cases.dto import CaseDetail
from apps.web.flows.air import money, plural
from apps.web.flows.base import Check, FlowDef
from apps.web.flows.fields import (
    WebForm,
    amount,
    clean_phone,
    date_field,
    integer,
    text,
    time_field,
)
from apps.web.flows.spec import MODES, LineSpec

CLASSES = [("vip", "VIP"), ("standard", "Classique")]
CLASS_LABELS = dict(CLASSES)
FRANCHISE = 1  # bagages gratuits par voyageur
SEAT_ROWS = 9  # plan du car : 9 rangées de 4 places
BAG_NOTE = "Un bagage de plus que la franchise du transporteur ajoute un supplément."


class BusTripForm(WebForm):
    UNIQUE = ()
    origin = text("Départ", max_length=80, placeholder="Douala", suggest=True)
    destination = text("Arrivée", max_length=80, placeholder="Yaoundé", suggest=True)
    departure_date = date_field("Date")
    departure_time = time_field("Heure de départ", required=True)
    carrier = text("Transporteur", max_length=120)
    station = text("Gare ou agence de départ", max_length=120, required=False)
    service_class = forms.ChoiceField(label="Classe", choices=CLASSES, initial="vip")
    seats = integer("Places", minimum=1, maximum=9, initial=1)
    price_per_seat = amount("Prix de vente par place (FCFA)")
    trip_code = text("Code de voyage", max_length=32, required=False)
    seats_confirmed = forms.BooleanField(
        label="Places confirmées par téléphone", required=True,
        error_messages={"required": "Confirmez les places auprès du transporteur avant de vendre."},
    )  # fmt: skip
    customer_name = text("Client", max_length=200)
    customer_phone = text("Téléphone du client", max_length=32, required=False)

    def clean_customer_phone(self) -> str:
        return clean_phone(self.cleaned_data["customer_phone"])

    def clean_trip_code(self) -> str:
        code = self.cleaned_data["trip_code"].upper()
        return "".join(ch for ch in code if ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")


class BusTravellerForm(WebForm):
    UNIQUE = ("seat",)
    name = text("Nom du voyageur", max_length=200)
    traveller_phone = text("Téléphone (rappel SMS)", max_length=32, required=False)
    seat = text("Place", max_length=3, placeholder="12")
    bags = integer("Bagages", minimum=0, maximum=9, initial=1)

    def clean_traveller_phone(self) -> str:
        return clean_phone(self.cleaned_data["traveller_phone"])

    def clean_seat(self) -> str:
        seat = self.cleaned_data["seat"].strip()
        if not seat.isascii() or not seat.isdigit() or not 1 <= int(seat) <= 99:
            raise forms.ValidationError("Un numéro de place entre 1 et 99.")
        return str(int(seat))


class BusPricingForm(WebForm):
    cost_per_seat_xaf = amount("Coût par place (FCFA)")
    bag_price_xaf = amount("Prix du bagage supplémentaire (FCFA)", required=False)
    cost_bag_xaf = amount("Coût du bagage supplémentaire (FCFA)", required=False)

    def __init__(self, *args: Any, extra_bags: int = 0, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.extra_bags = extra_bags
        if extra_bags == 0:
            del self.fields["bag_price_xaf"]
            del self.fields["cost_bag_xaf"]
        else:
            self.fields["bag_price_xaf"].required = True
            self.fields["cost_bag_xaf"].required = True


def extra_bags(travellers: list[dict[str, Any]]) -> int:
    return sum(max(int(t.get("bags", 0)) - FRANCHISE, 0) for t in travellers)


def seat_map(chosen: set[str]) -> list[dict[str, Any]]:
    """Plan du car : 4 places par rangée, une allée au milieu ; les places choisies ressortent."""
    cells: list[dict[str, Any]] = []
    number = 0
    for _ in range(SEAT_ROWS):
        for column in range(5):
            if column == 2:
                cells.append({"gap": True})
                continue
            number += 1
            cells.append({"n": number, "chosen": str(number) in chosen})
    return cells


class BusFlow(FlowDef):
    mode = MODES["bus"]
    trip_form: ClassVar = BusTripForm
    traveller_form: ClassVar = BusTravellerForm
    pricing_form: ClassVar = BusPricingForm
    pricing_step = 3
    template_prefix = "web/flow/bus"

    # --- présentation --------------------------------------------------------------------
    def subtitle(self, draft: dict[str, Any]) -> str:
        trip = self.trip(draft)
        parts = [self.route_label(draft)]
        if trip.get("departure_date"):
            day = datetime.fromisoformat(trip["departure_date"]).strftime("%d/%m")
            parts.append(f"{day} {trip.get('departure_time', '')}".strip())
        if trip.get("service_class"):
            parts.append(CLASS_LABELS.get(trip["service_class"], ""))
        return " · ".join(part for part in parts if part)

    def seat_total(self, draft: dict[str, Any]) -> int:
        trip = self.trip(draft)
        return trip.get("seats", 0) * trip.get("price_per_seat", 0)

    def step1_hint(self, draft: dict[str, Any]) -> str:
        return "Places × prix de vente"

    def step1_total(self, draft: dict[str, Any]) -> int | None:
        return self.seat_total(draft) or None

    def step2_hint(self, draft: dict[str, Any]) -> str:
        seats = " · ".join(t["seat"] for t in draft.get("travellers", []))
        return f"Places {seats}" if seats else "Places"

    def step2_total(self, draft: dict[str, Any]) -> int | None:
        count = len(draft.get("travellers", [])) or self.trip(draft).get("seats", 0)
        return count * self.trip(draft).get("price_per_seat", 0) or None

    def default_travellers(self, draft: dict[str, Any]) -> list[dict[str, Any]]:
        return [{} for _ in range(self.trip(draft).get("seats", 1))]

    def aside(self, formset: Any) -> dict[str, Any]:
        chosen = {str(form["seat"].value() or "").strip() for form in formset}
        chosen.discard("")
        return {"seat_map": seat_map(chosen), "chosen_count": len(chosen), "bag_note": BAG_NOTE}

    def pricing_kwargs(self, draft: dict[str, Any]) -> dict[str, Any]:
        return {"extra_bags": extra_bags(draft.get("travellers", []))}

    def confirm_context(self, draft: dict[str, Any]) -> dict[str, Any]:
        return {
            "extra_bags": extra_bags(draft.get("travellers", [])),
            "seat_total": len(draft.get("travellers", []))
            * self.trip(draft).get("price_per_seat", 0),
            "live_total": self._live_total(draft),
        }

    def _live_total(self, draft: dict[str, Any]) -> str:
        extra = extra_bags(draft.get("travellers", []))
        seats = len(draft.get("travellers", [])) * self.trip(draft).get("price_per_seat", 0)
        return f"{seats} + id_bag_price_xaf*{extra}" if extra else ""

    # --- lignes et prix ------------------------------------------------------------------
    def lines(self, draft: dict[str, Any]) -> list[LineSpec]:
        trip, pricing = self.trip(draft), draft.get("pricing", {})
        common = {
            "origin": trip.get("origin", ""),
            "destination": trip.get("destination", ""),
            "departure_time": trip.get("departure_time", ""),
            "station": trip.get("station", ""),
            "travel_class": trip.get("service_class", ""),
            "booking_reference": trip.get("trip_code", ""),
        }
        specs = [
            LineSpec(
                kind=LineKind.BUS_TICKET,
                label=self.route_label(draft),
                price_xaf=trip.get("price_per_seat", 0),
                cost_xaf=pricing.get("cost_per_seat_xaf"),
                passenger_name=traveller["name"],
                carrier=trip.get("carrier", ""),
                details=common
                | {
                    "seat": traveller["seat"],
                    "bags": traveller.get("bags", 0),
                    "traveller_phone": traveller.get("traveller_phone", ""),
                },
            )
            for traveller in draft.get("travellers", [])
        ]
        extra = extra_bags(draft.get("travellers", []))
        if extra:
            specs.append(
                LineSpec(
                    kind=LineKind.FREE_SERVICE,
                    label=f"Bagage supplémentaire × {extra}",
                    price_xaf=extra * pricing.get("bag_price_xaf", 0),
                    cost_xaf=(
                        extra * pricing["cost_bag_xaf"] if "cost_bag_xaf" in pricing else None
                    ),
                )
            )
        return specs

    def price_lines(self, draft: dict[str, Any]) -> list[dict[str, Any]]:
        trip, pricing = self.trip(draft), draft.get("pricing", {})
        travellers = draft.get("travellers", [])
        seats = " · ".join(t["seat"] for t in travellers)
        when = ""
        if trip.get("departure_date"):
            when = datetime.fromisoformat(trip["departure_date"]).strftime("%d/%m/%Y")
        rows = [
            {
                "label": f"Place {CLASS_LABELS.get(trip.get('service_class', ''), '')} · "
                f"{self.route_label(draft)}",
                "detail": f"{when} · {trip.get('departure_time', '')} · places {seats}",
                "qty": len(travellers),
                "unit": trip.get("price_per_seat", 0),
                "total": len(travellers) * trip.get("price_per_seat", 0),
            }
        ]
        extra = extra_bags(travellers)
        if extra:
            unit = pricing.get("bag_price_xaf", 0)
            rows.append(
                {
                    "label": "Bagage supplémentaire",
                    "detail": f"Franchise : {FRANCHISE} bagage par voyageur",
                    "qty": extra,
                    "unit": unit,
                    "total": extra * unit,
                    "unit_field": "id_bag_price_xaf",
                }
            )
        return rows

    def checks(self, draft: dict[str, Any]) -> list[Check]:
        travellers = draft.get("travellers", [])
        count = len(travellers)
        return [
            Check(True, f"{count} {plural(count, 'place confirmée', 'places confirmées')} "
                        "par le transporteur"),
            Check(count > 0, f"{count} {plural(count, 'voyageur nommé', 'voyageurs nommés')} "
                             "avec leur place"),
            Check(draft.get("pricing", {}).get("cost_per_seat_xaf") is not None,
                  "Coût d'achat saisi", "À saisir ci-dessus : sans coût, pas de vente"),
        ]  # fmt: skip

    # --- remise --------------------------------------------------------------------------
    def message(self, detail: CaseDetail, customer: str, agency: str, due: int) -> str:
        tickets = [ln for ln in detail.lines if not ln.is_voided and ln.kind is LineKind.BUS_TICKET]
        first = tickets[0] if tickets else None
        info = first.details if first else {}
        when = detail.summary.departure_date
        head = f"Bonjour {customer.split()[0] if customer else ''}, votre voyage "
        head += first.label if first else ""
        if when:
            head += f" le {when:%d/%m/%Y}"
        if info.get("departure_time"):
            head += f" à {info['departure_time']}"
        seats = ", ".join(str(t.details.get("seat", "")) for t in tickets)
        klass = CLASS_LABELS.get(info.get("travel_class", ""), "")
        parts = [head + (f" ({klass}, places {seats})." if seats else ".")]
        if info.get("booking_reference"):
            parts.append(f"Code : {info['booking_reference']}.")
        where = f" à {info['station']}" if info.get("station") else ""
        parts.append(f"Soyez à la gare{where} 45 min avant le départ.")
        if due:
            parts.append(f"Solde restant : {money(due)}.")
        parts.append(f"— {agency}")
        return "\n".join(parts)

    def done_context(self, detail: CaseDetail) -> dict[str, Any]:
        tickets = [ln for ln in detail.lines if not ln.is_voided and ln.kind is LineKind.BUS_TICKET]
        first = tickets[0] if tickets else None
        info = first.details if first else {}
        bags = sum(int(t.details.get("bags", 0)) for t in tickets)
        when = detail.summary.departure_date
        return {
            "ticket": {
                "title": "Billet de voyage · Bus "
                + CLASS_LABELS.get(info.get("travel_class", ""), ""),
                "from": info.get("origin", ""),
                "to": info.get("destination", ""),
                "code": info.get("booking_reference", ""),
                "seats": [str(t.details.get("seat", "")) for t in tickets],
                "facts": [
                    ("Date", f"{when:%d/%m/%Y}" if when else "—"),
                    ("Départ", info.get("departure_time", "—")),
                    ("Gare", info.get("station", "—")),
                    ("Transporteur", first.carrier if first and first.carrier else "—"),
                    ("Voyageurs", f"{len(tickets)} {plural(len(tickets), 'voyageur')}"),
                    ("Bagages", str(bags)),
                ],
            }
        }


BUS = BusFlow()
