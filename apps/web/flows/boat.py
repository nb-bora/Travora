"""Parcours bateau : pièces d'identité, véhicule en option, heure limite d'enregistrement."""

from datetime import date, datetime, timedelta
from typing import Any, ClassVar

from django import forms
from django.utils import timezone

from apps.cases.constants import LineKind
from apps.cases.dto import CaseDetail
from apps.web.flows.air import money, plural
from apps.web.flows.base import Check, FlowDef, allocate
from apps.web.flows.fields import (
    WebForm,
    amount,
    clean_phone,
    date_field,
    text,
    time_field,
    upper_code,
)
from apps.web.flows.spec import MODES, LineSpec, to_json

DECKS = [("deck", "Siège pont"), ("cabin", "Cabine")]
DECK_LABELS = dict(DECKS)
VEHICLE_TYPES = [("car", "Voiture"), ("suv", "4×4"), ("van", "Camionnette")]
VEHICLE_LABELS = dict(VEHICLE_TYPES)
DOC_VALIDITY_MONTHS = 6
BALANCE_DAYS_BEFORE = 7


class BoatTripForm(WebForm):
    UNIQUE = ()
    origin = text("Port de départ", max_length=80, placeholder="Douala")
    destination = text("Port d'arrivée", max_length=80, placeholder="Malabo")
    departure_date = date_field("Date")
    carrier = text("Compagnie maritime", max_length=120)
    ship = text("Navire", max_length=80, required=False)
    check_in_opens = time_field("Ouverture de l'enregistrement")
    check_in_closes = time_field("Clôture de l'enregistrement", required=True)
    boarding_time = time_field("Embarquement")
    departure_time = time_field("Départ", required=True)
    arrival_time = time_field("Arrivée prévue")
    passenger_price = amount("Prix par passager (FCFA)")
    with_vehicle = forms.BooleanField(label="Transporter un véhicule", required=False)
    with_cabin = forms.BooleanField(label="Cabine (sinon siège sur le pont)", required=False)
    vehicle_price = amount("Prix du véhicule (FCFA)", required=False, initial=0)
    customer_name = text("Client", max_length=200)
    customer_phone = text("Téléphone du client", max_length=32, required=False)

    def clean_customer_phone(self) -> str:
        return clean_phone(self.cleaned_data["customer_phone"])

    def clean(self) -> dict[str, Any]:
        data = super().clean() or {}
        if data.get("with_vehicle") and not data.get("vehicle_price"):
            self.add_error("vehicle_price", "Indiquez le prix du véhicule.")
        if not data.get("with_vehicle"):
            data["vehicle_price"] = 0
        opens, closes = data.get("check_in_opens"), data.get("check_in_closes")
        if opens and closes and opens >= closes:
            self.add_error("check_in_closes", "La clôture doit suivre l'ouverture.")
        return data


class BoatTravellerForm(WebForm):
    UNIQUE = ("doc_number",)
    name = text("Nom comme sur le passeport", max_length=200)
    birth_date = date_field("Naissance")
    nationality = text("Nationalité", max_length=60, placeholder="Camerounaise")
    doc_number = text("Passeport", max_length=40, placeholder="P 1048827")
    doc_expiry = date_field("Valable jusqu'au")

    def clean_doc_number(self) -> str:
        return upper_code(self.cleaned_data["doc_number"])

    def clean_birth_date(self) -> date:
        born = self.cleaned_data["birth_date"]
        if born > timezone.localdate():
            raise forms.ValidationError("La date de naissance est dans le futur.")
        return born


class BoatVehicleForm(WebForm):
    plate = text("Plaque", max_length=20, placeholder="LT 123 AB", css="plate")
    vehicle_type = forms.ChoiceField(label="Type", choices=VEHICLE_TYPES, initial="car")
    length_m = text("Longueur (m)", max_length=6, placeholder="4,5")

    def clean_plate(self) -> str:
        return self.cleaned_data["plate"].strip().upper()


class BoatPricingForm(WebForm):
    port_tax_xaf = amount("Taxe portuaire par passager (FCFA)")
    agency_fee_xaf = amount("Frais d'agence (FCFA)", required=False, initial=0)
    cost_total_xaf = amount("Coût total payé à la compagnie et au port (FCFA)")

    def clean_agency_fee_xaf(self) -> int:
        return self.cleaned_data["agency_fee_xaf"] or 0


def months_between(day: date, later: date) -> int:
    return (
        (later.year - day.year) * 12 + later.month - day.month - (1 if later.day < day.day else 0)
    )


def passport_status(expiry: str, departure: str) -> str:
    """« ok » ou « verify » : la validité exigée varie selon le pays, on signale sans refuser."""
    if not expiry or not departure:
        return "ok"
    left = months_between(date.fromisoformat(departure), date.fromisoformat(expiry))
    return "ok" if left >= DOC_VALIDITY_MONTHS else "verify"


def time_range(opens: str, closes: str) -> str:
    return f"{opens}–{closes}" if opens and closes else closes or opens


class BoatFlow(FlowDef):
    mode = MODES["boat"]
    trip_form: ClassVar = BoatTripForm
    traveller_form: ClassVar = BoatTravellerForm
    pricing_form: ClassVar = BoatPricingForm
    extra_form: ClassVar = BoatVehicleForm
    pricing_step = 3
    template_prefix = "web/flow/boat"
    default_method = "transfer"
    default_share = "half"

    # --- présentation --------------------------------------------------------------------
    def subtitle(self, draft: dict[str, Any]) -> str:
        trip = self.trip(draft)
        parts = [self.route_label(draft)]
        if trip.get("departure_date"):
            day = datetime.fromisoformat(trip["departure_date"]).strftime("%d/%m")
            parts.append(f"{day} {trip.get('departure_time', '')}".strip())
        if trip.get("ship"):
            parts.append(trip["ship"])
        return " · ".join(part for part in parts if part)

    def step1_hint(self, draft: dict[str, Any]) -> str:
        return "Prix d'un passager"

    def step1_total(self, draft: dict[str, Any]) -> int | None:
        return self.trip(draft).get("passenger_price") or None

    def step1_context(self, draft: dict[str, Any]) -> dict[str, Any]:
        trip = self.trip(draft)
        closing = trip.get("check_in_closes")
        return {"closing": closing}

    def step2_total(self, draft: dict[str, Any]) -> int | None:
        trip = self.trip(draft)
        count = len(draft.get("travellers", [])) or 1
        total = count * trip.get("passenger_price", 0) + trip.get("vehicle_price", 0)
        return total or None

    def step2_hint(self, draft: dict[str, Any]) -> str:
        count = len(draft.get("travellers", [])) or 1
        vehicle = " + véhicule" if self.trip(draft).get("with_vehicle") else ""
        return f"{count} {plural(count, 'passager')}{vehicle}"

    def side_forms(self, post: Any, draft: dict[str, Any], *, bound: bool) -> dict[str, forms.Form]:
        if not self.trip(draft).get("with_vehicle"):
            return {}
        if post is not None and bound:
            return {"vehicle_form": BoatVehicleForm(post, prefix="vehicle")}
        initial = draft.get("vehicle", {})
        if post is not None:
            initial = {
                name: post.get(f"vehicle-{name}", "") for name in BoatVehicleForm.base_fields
            }
        return {"vehicle_form": BoatVehicleForm(initial=initial, prefix="vehicle")}

    def save_side(self, draft: dict[str, Any], side: dict[str, forms.Form]) -> None:
        form = side.get("vehicle_form")
        draft["vehicle"] = to_json(form.cleaned_data) if form is not None else {}

    # --- lignes et prix ------------------------------------------------------------------
    def lines(self, draft: dict[str, Any]) -> list[LineSpec]:
        trip, pricing = self.trip(draft), draft.get("pricing", {})
        vehicle = draft.get("vehicle", {})
        tax = pricing.get("port_tax_xaf", 0)
        fare = trip.get("passenger_price", 0) + tax
        deck = "cabin" if trip.get("with_cabin") else "deck"
        common = {
            "origin": trip.get("origin", ""),
            "destination": trip.get("destination", ""),
            "departure_time": trip.get("departure_time", ""),
            "arrival_time": trip.get("arrival_time", ""),
            "ship": trip.get("ship", ""),
            "check_in_opens": trip.get("check_in_opens", ""),
            "check_in_closes": trip.get("check_in_closes", ""),
            "boarding_time": trip.get("boarding_time", ""),
            "cabin": deck,
            "doc_type": "passport",
        }
        specs: list[LineSpec] = []
        for index, traveller in enumerate(draft.get("travellers", [])):
            details = common | {
                "doc_number": traveller["doc_number"],
                "birth_date": traveller["birth_date"],
                "nationality": traveller["nationality"],
                "doc_expiry": traveller["doc_expiry"],
            }
            if index == 0 and trip.get("with_vehicle"):
                details |= {
                    "vehicle_plate": vehicle.get("plate", ""),
                    "vehicle_type": vehicle.get("vehicle_type", ""),
                    "vehicle_length_m": vehicle.get("length_m", ""),
                }
            specs.append(
                LineSpec(
                    kind=LineKind.BOAT_TICKET,
                    label=self.route_label(draft),
                    price_xaf=fare,
                    cost_xaf=None,
                    passenger_name=traveller["name"],
                    carrier=trip.get("carrier", ""),
                    details=details,
                )
            )
        if trip.get("with_vehicle"):
            kind = VEHICLE_LABELS.get(vehicle.get("vehicle_type", ""), "Véhicule")
            specs.append(
                LineSpec(
                    LineKind.FREE_SERVICE,
                    f"Véhicule · {kind} {vehicle.get('plate', '')}".strip(),
                    trip.get("vehicle_price", 0),
                    None,
                )
            )
        # Le coût total payé à la compagnie se répartit au prorata des prix : aucun franc perdu.
        total_cost = pricing.get("cost_total_xaf")
        if total_cost is not None:
            shares = allocate(total_cost, [spec.price_xaf for spec in specs])
            specs = [
                LineSpec(
                    s.kind,
                    s.label,
                    s.price_xaf,
                    share,
                    s.passenger_name,
                    s.ticket_number,
                    s.carrier,
                    s.details,
                )  # fmt: skip
                for s, share in zip(specs, shares, strict=True)
            ]
        fee = pricing.get("agency_fee_xaf", 0)
        if fee:
            specs.append(
                LineSpec(
                    LineKind.FREE_SERVICE,
                    "Frais d'agence",
                    fee,
                    0 if total_cost is not None else None,
                )
            )
        return specs

    def price_lines(self, draft: dict[str, Any]) -> list[dict[str, Any]]:
        trip, pricing = self.trip(draft), draft.get("pricing", {})
        travellers = draft.get("travellers", [])
        count = len(travellers)
        when = ""
        if trip.get("departure_date"):
            when = datetime.fromisoformat(trip["departure_date"]).strftime("%d/%m/%Y")
        deck = DECK_LABELS["cabin" if trip.get("with_cabin") else "deck"]
        rows = [
            {
                "label": f"Passager adulte · {deck.lower()}",
                "detail": " · ".join(
                    part
                    for part in (trip.get("ship", ""), when, trip.get("departure_time", ""))
                    if part
                ),
                "qty": count,
                "unit": trip.get("passenger_price", 0),
                "total": count * trip.get("passenger_price", 0),
            }
        ]
        if trip.get("with_vehicle"):
            vehicle = draft.get("vehicle", {})
            rows.append(
                {
                    "label": "Véhicule",
                    "detail": f"{vehicle.get('plate', '')} · {vehicle.get('length_m', '')} m",
                    "qty": 1,
                    "unit": trip.get("vehicle_price", 0),
                    "total": trip.get("vehicle_price", 0),
                }
            )
        rows.append(
            {
                "label": "Taxes portuaires",
                "detail": "Par passager",
                "qty": count,
                "unit": pricing.get("port_tax_xaf", 0),
                "total": count * pricing.get("port_tax_xaf", 0),
                "unit_field": "id_port_tax_xaf",
            }
        )
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
        trip = self.trip(draft)
        count = len(draft.get("travellers", []))
        base = count * trip.get("passenger_price", 0) + trip.get("vehicle_price", 0)
        return {
            "base_total": base,
            "passenger_count": count,
            "live_total": f"{base} + id_port_tax_xaf*{count} + id_agency_fee_xaf",
        }

    def checks(self, draft: dict[str, Any]) -> list[Check]:
        trip, travellers = self.trip(draft), draft.get("travellers", [])
        count = len(travellers)
        closes = trip.get("check_in_closes", "")
        weak = [
            t["name"]
            for t in travellers
            if passport_status(t["doc_expiry"], trip.get("departure_date", "")) == "verify"
        ]
        return [
            Check(True, "Traversée et horaires saisis",
                  f"Enregistrement clos à {closes}" if closes else ""),
            Check(count > 0, f"{count} {plural(count, 'passager')} avec pièce d'identité",
                  "Nom, naissance, nationalité, passeport"),
            Check(not weak, "Validité des passeports",
                  "À vérifier : " + ", ".join(weak) + f" (moins de {DOC_VALIDITY_MONTHS} mois "
                  "après le départ ; certains pays l'exigent)" if weak
                  else f"Valables plus de {DOC_VALIDITY_MONTHS} mois après le départ"),
            Check(draft.get("pricing", {}).get("cost_total_xaf") is not None, "Coût d'achat saisi",
                  "À saisir ci-dessus : sans coût, pas de vente"),
        ]  # fmt: skip

    # --- paiement et remise --------------------------------------------------------------
    def schedule(self, total: int, departure: date | None) -> list[dict[str, Any]] | None:
        deposit = (total + 1) // 2
        balance = total - deposit
        due = (
            f"À encaisser avant le {departure - timedelta(days=BALANCE_DAYS_BEFORE):%d/%m/%Y} "
            f"({BALANCE_DAYS_BEFORE} jours avant le départ)"
            if departure
            else "À encaisser avant le départ"
        )
        return [
            {"title": "Acompte · 50 %", "when": "À encaisser aujourd'hui", "amount": deposit,
             "tag": "En cours", "tone": "info", "state": "now"},
            {"title": "Solde", "when": due, "amount": balance, "tag": "À venir", "tone": "neutral",
             "state": "later"},
        ]  # fmt: skip

    def message(self, detail: CaseDetail, customer: str, agency: str, due: int) -> str:
        tickets = [
            ln for ln in detail.lines if not ln.is_voided and ln.kind is LineKind.BOAT_TICKET
        ]
        first = tickets[0] if tickets else None
        info = first.details if first else {}
        plate = info.get("vehicle_plate", "")
        head = f"Bonjour {customer.split()[0] if customer else ''}, votre traversée "
        head += first.label if first else ""
        if detail.summary.departure_date:
            head += f" le {detail.summary.departure_date:%d/%m/%Y}"
        head += f", {info['ship']}." if info.get("ship") else "."
        parts = [head]
        window = time_range(info.get("check_in_opens", ""), info.get("check_in_closes", ""))
        if window:
            parts.append(
                f"Enregistrement de {window.replace('–', ' à ')}, départ à "
                f"{info.get('departure_time', '')}."
            )
        papers = "vos passeports"
        if plate:
            papers += f" et les papiers du véhicule {plate}"
        parts.append(f"Apportez {papers}.")
        if due and detail.summary.departure_date:
            limit = detail.summary.departure_date - timedelta(days=BALANCE_DAYS_BEFORE)
            parts.append(f"Solde à régler avant le {limit:%d/%m/%Y} : {money(due)}.")
        elif due:
            parts.append(f"Solde restant : {money(due)}.")
        parts.append(f"— {agency}")
        return "\n".join(parts)

    def done_context(self, detail: CaseDetail) -> dict[str, Any]:
        tickets = [
            ln for ln in detail.lines if not ln.is_voided and ln.kind is LineKind.BOAT_TICKET
        ]
        first = tickets[0] if tickets else None
        info = first.details if first else {}
        has_vehicle = any(
            ln.label.startswith("Véhicule") for ln in detail.lines if not ln.is_voided
        )
        timeline = [
            ("Ouverture", info.get("check_in_opens", ""), "Enregistrement"),
            ("Clôture", info.get("check_in_closes", ""), "Dernier moment pour se présenter"),
            ("Embarquement", info.get("boarding_time", ""), "Montée à bord"),
            (
                "Départ",
                info.get("departure_time", ""),
                f"Arrivée prévue {info.get('arrival_time', '')}"
                if info.get("arrival_time")
                else "",
            ),
        ]
        docs = [
            ("Passeports valides", "Un par passager, nom identique au billet"),
            ("Confirmation de la traversée", "Message ou billet imprimé"),
        ]
        if has_vehicle:
            plate = info.get("vehicle_plate", "")
            docs.append(
                (
                    "Papiers du véhicule",
                    "Carte grise et assurance" + (f", plaque {plate}" if plate else ""),
                )
            )
        docs.append(("Moyen de régler les frais", "Si une taxe est due sur place"))
        return {
            "timeline": [(a, b, c) for a, b, c in timeline if b],
            "docs": docs,
            "ship": info.get("ship", ""),
            "next_cards": [
                {
                    "title": "Rappeler le solde",
                    "tag": "Proposé",
                    "tone": "info",
                    "text": "Quatre jours avant l'échéance, avec le message pré-rempli.",
                },
                {
                    "title": "Annuler un billet",
                    "tag": "Gérant",
                    "tone": "neutral",
                    "text": "Réservé au gérant. Écriture inverse, avec trace d'audit.",
                },
            ],  # fmt: skip
        }


BOAT = BoatFlow()
