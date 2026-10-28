"""Parcours train : horaire, classe, voiture et place, pièce d'identité du voyageur."""

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
    upper_code,
)
from apps.web.flows.spec import MODES, LineSpec

CLASSES = [
    ("first", "Première", "Siège large, climatisé"),
    ("comfort", "Confort", "Siège inclinable"),
    ("economy", "Économique", "Siège standard"),
]
CLASS_LABELS = {value: label for value, label, _ in CLASSES}
DOC_TYPES = [("cni", "Carte nationale d'identité"), ("passport", "Passeport"),
             ("licence", "Permis de conduire")]  # fmt: skip
DOC_LABELS = dict(DOC_TYPES)
FARES = [("adult", "Adulte"), ("child", "Enfant")]
SEATS_PER_CAR = 48
SEATS_PER_ROW = 12


class TrainTripForm(WebForm):
    UNIQUE = ()
    origin = text("Gare de départ", max_length=80, placeholder="Douala", suggest=True)
    destination = text("Gare d'arrivée", max_length=80, placeholder="Yaoundé", suggest=True)
    departure_date = date_field("Date")
    train = text("Train", max_length=80, placeholder="Train 2")
    departure_time = time_field("Départ", required=True)
    arrival_time = time_field("Arrivée", required=True)
    service_class = forms.ChoiceField(
        label="Classe", choices=[(v, label) for v, label, _ in CLASSES], initial="comfort",
        widget=forms.RadioSelect,
    )  # fmt: skip
    price = amount("Prix du billet (FCFA)")
    booking_reference = text("Référence du billet", max_length=12, required=False)
    seat_confirmed = forms.BooleanField(
        label="Place confirmée auprès de l'opérateur", required=True,
        error_messages={"required": "Confirmez la place auprès de l'opérateur avant de vendre."},
    )  # fmt: skip
    customer_name = text("Client", max_length=200)
    customer_phone = text("Téléphone du client", max_length=32, required=False)

    def clean_customer_phone(self) -> str:
        return clean_phone(self.cleaned_data["customer_phone"])

    def clean_booking_reference(self) -> str:
        return upper_code(self.cleaned_data["booking_reference"])


class TrainTravellerForm(WebForm):
    UNIQUE = ("seat_key",)
    name = text("Nom comme sur la pièce d'identité", max_length=200)
    traveller_phone = text("Téléphone", max_length=32, required=False)
    doc_type = forms.ChoiceField(label="Type de pièce", choices=DOC_TYPES, initial="cni")
    doc_number = text("Numéro de la pièce", max_length=40, placeholder="CNI 112 458 903")
    fare_type = forms.ChoiceField(label="Tarif", choices=FARES, initial="adult")
    car = text("Voiture", max_length=3, placeholder="3")
    seat = text("Place", max_length=3, placeholder="24")
    bags = integer("Bagages", minimum=0, maximum=9, initial=1)

    def clean_traveller_phone(self) -> str:
        return clean_phone(self.cleaned_data["traveller_phone"])

    def _number(self, field: str, label: str) -> str:
        value = self.cleaned_data[field].strip()
        if not value.isascii() or not value.isdigit() or not 1 <= int(value) <= 99:
            raise forms.ValidationError(f"{label} : un numéro entre 1 et 99.")
        return str(int(value))

    def clean_car(self) -> str:
        return self._number("car", "Voiture")

    def clean_seat(self) -> str:
        return self._number("seat", "Place")

    def clean(self) -> dict[str, Any]:
        data = super().clean() or {}
        if data.get("car") and data.get("seat"):
            data["seat_key"] = f"voiture {data['car']} place {data['seat']}"
        return data


class TrainPricingForm(WebForm):
    cost_xaf = amount("Coût du billet (FCFA)")
    agency_fee_xaf = amount("Frais d'agence (FCFA)", required=False, initial=0)

    def clean_agency_fee_xaf(self) -> int:
        return self.cleaned_data["agency_fee_xaf"] or 0


def seat_map(car: str, chosen: set[tuple[str, str]]) -> list[dict[str, Any]]:
    """Plan d'une voiture ; les places du voyageur dans cette voiture ressortent."""
    return [
        {"n": number, "chosen": (car, str(number)) in chosen}
        for number in range(1, SEATS_PER_CAR + 1)
    ]


CHANGE_OPTIONS = [
    {
        "title": "Changer de train",
        "tag": "Disponible",
        "tone": "success",
        "text": "Annuler la vente, puis en créer une nouvelle avec le bon horaire. "
        "Les deux écritures restent visibles.",
    },
    {
        "title": "Annuler le billet",
        "tag": "Gérant",
        "tone": "neutral",
        "text": "Réservé au gérant. Écriture inverse datée d'aujourd'hui, trace d'audit.",
    },
    {
        "title": "Suivre un remboursement",
        "tag": "À venir",
        "tone": "warning",
        "text": "Montant et date du remboursement par l'opérateur, rapprochés du dossier.",
    },
]


class TrainFlow(FlowDef):
    mode = MODES["train"]
    trip_form: ClassVar = TrainTripForm
    traveller_form: ClassVar = TrainTravellerForm
    pricing_form: ClassVar = TrainPricingForm
    pricing_step = 3
    template_prefix = "web/flow/train"
    default_method = "cash"

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

    def step1_hint(self, draft: dict[str, Any]) -> str:
        return "Prix du billet par voyageur"

    def step1_total(self, draft: dict[str, Any]) -> int | None:
        return self.trip(draft).get("price") or None

    def step1_context(self, draft: dict[str, Any]) -> dict[str, Any]:
        return {"class_cards": CLASSES}

    def step2_total(self, draft: dict[str, Any]) -> int | None:
        count = len(draft.get("travellers", [])) or 1
        return (self.trip(draft).get("price", 0) * count) or None

    def aside(self, formset: Any) -> dict[str, Any]:
        rows = [
            (str(form["car"].value() or "").strip(), str(form["seat"].value() or "").strip())
            for form in formset
        ]
        chosen = {(car, seat) for car, seat in rows if car and seat}
        shown = rows[0][0] if rows and rows[0][0] else "?"
        return {
            "seat_map": seat_map(shown, chosen),
            "car_number": shown,
            "class_cards": CLASSES,
        }

    # --- lignes et prix ------------------------------------------------------------------
    def lines(self, draft: dict[str, Any]) -> list[LineSpec]:
        trip, pricing = self.trip(draft), draft.get("pricing", {})
        common = {
            "origin": trip.get("origin", ""),
            "destination": trip.get("destination", ""),
            "departure_time": trip.get("departure_time", ""),
            "arrival_time": trip.get("arrival_time", ""),
            "travel_class": trip.get("service_class", ""),
            "booking_reference": trip.get("booking_reference", ""),
            "train": trip.get("train", ""),
        }
        specs = [
            LineSpec(
                kind=LineKind.TRAIN_TICKET,
                label=self.route_label(draft),
                price_xaf=trip.get("price", 0),
                cost_xaf=pricing.get("cost_xaf"),
                passenger_name=traveller["name"],
                details=common
                | {
                    "car": traveller["car"],
                    "seat": traveller["seat"],
                    "doc_type": traveller["doc_type"],
                    "doc_number": traveller["doc_number"],
                    "fare_type": traveller["fare_type"],
                    "bags": traveller.get("bags", 0),
                    "traveller_phone": traveller.get("traveller_phone", ""),
                },
            )
            for traveller in draft.get("travellers", [])
        ]
        fee = pricing.get("agency_fee_xaf", 0)
        if fee:
            specs.append(LineSpec(LineKind.FREE_SERVICE, "Frais d'agence", fee, 0))
        return specs

    def price_lines(self, draft: dict[str, Any]) -> list[dict[str, Any]]:
        trip, pricing = self.trip(draft), draft.get("pricing", {})
        travellers = draft.get("travellers", [])
        when = ""
        if trip.get("departure_date"):
            when = datetime.fromisoformat(trip["departure_date"]).strftime("%d/%m/%Y")
        places = " · ".join(f"voiture {t['car']}, place {t['seat']}" for t in travellers)
        rows = [
            {
                "label": "Billet de train · classe "
                + CLASS_LABELS.get(trip.get("service_class", ""), ""),
                "detail": " · ".join(
                    part
                    for part in (
                        self.route_label(draft),
                        when,
                        trip.get("departure_time", ""),
                        places,
                    )
                    if part
                ),
                "qty": len(travellers),
                "unit": trip.get("price", 0),
                "total": len(travellers) * trip.get("price", 0),
            }
        ]
        rows.append(
            {
                "label": "Frais d'agence",
                "detail": "Service de l'agence",
                "qty": 1,
                "unit": pricing.get("agency_fee_xaf", 0),
                "total": pricing.get("agency_fee_xaf", 0),
                "unit_field": "id_agency_fee_xaf",
            }
        )
        return rows

    def confirm_context(self, draft: dict[str, Any]) -> dict[str, Any]:
        seats = len(draft.get("travellers", [])) * self.trip(draft).get("price", 0)
        return {"live_total": f"{seats} + id_agency_fee_xaf", "seat_total": seats}

    def checks(self, draft: dict[str, Any]) -> list[Check]:
        travellers = draft.get("travellers", [])
        count = len(travellers)
        return [
            Check(True, "Place confirmée auprès de l'opérateur"),
            Check(count > 0, f"{plural(count, 'Voyageur nommé', 'Voyageurs nommés')} avec "
                             f"{plural(count, 'sa pièce', 'leur pièce')} d'identité"),
            Check(draft.get("pricing", {}).get("cost_xaf") is not None, "Coût d'achat saisi",
                  "À saisir ci-dessus : sans coût, pas de vente"),
        ]  # fmt: skip

    # --- remise --------------------------------------------------------------------------
    def message(self, detail: CaseDetail, customer: str, agency: str, due: int) -> str:
        tickets = [
            ln for ln in detail.lines if not ln.is_voided and ln.kind is LineKind.TRAIN_TICKET
        ]
        first = tickets[0] if tickets else None
        info = first.details if first else {}
        head = f"Bonjour {customer.split()[0] if customer else ''}, votre train "
        head += first.label if first else ""
        if detail.summary.departure_date:
            head += f" le {detail.summary.departure_date:%d/%m/%Y}"
        times = info.get("departure_time", "")
        if times and info.get("arrival_time"):
            times += f" (arrivée {info['arrival_time']})"
        klass = CLASS_LABELS.get(info.get("travel_class", ""), "")
        parts = [head + (f" : {info['train']}" if info.get("train") else "") + "."]
        parts.append(f"Départ {times}, classe {klass}." if times else f"Classe {klass}.")
        places = ", ".join(
            f"voiture {t.details.get('car')} place {t.details.get('seat')}" for t in tickets
        )
        if places:
            parts.append(f"{places.capitalize()}.")
        if info.get("booking_reference"):
            parts.append(f"Référence : {info['booking_reference']}.")
        parts.append("Pensez à votre pièce d'identité : elle peut être demandée au contrôle.")
        if due:
            parts.append(f"Solde restant : {money(due)}.")
        parts.append(f"— {agency}")
        return "\n".join(parts)

    def done_context(self, detail: CaseDetail) -> dict[str, Any]:
        tickets = [
            ln for ln in detail.lines if not ln.is_voided and ln.kind is LineKind.TRAIN_TICKET
        ]
        first = tickets[0] if tickets else None
        info = first.details if first else {}
        when = detail.summary.departure_date
        names = ", ".join(t.passenger_name for t in tickets) or "—"
        return {
            "ticket": {
                "title": "Billet de train · " + CLASS_LABELS.get(info.get("travel_class", ""), ""),
                "from": info.get("origin", ""),
                "to": info.get("destination", ""),
                "code": info.get("booking_reference", ""),
                "stub_label": "Référence",
                "seats_label": "Voiture · place",
                "seats": [f"{t.details.get('car')} · {t.details.get('seat')}" for t in tickets],
                "note": "Pièce d'identité à présenter",
                "facts": [
                    ("Date", f"{when:%d/%m/%Y}" if when else "—"),
                    ("Départ", info.get("departure_time", "—")),
                    ("Arrivée", info.get("arrival_time", "—")),
                    ("Train", info.get("train", "—")),
                    ("Voyageurs", names),
                    ("Bagages", str(sum(int(t.details.get("bags", 0)) for t in tickets))),
                ],
            },
            "change_options": CHANGE_OPTIONS,
        }


TRAIN = TrainFlow()
