import uuid
from typing import Any

from django import forms
from django.utils import timezone

from apps.cases.constants import LineKind
from apps.payments.constants import PaymentMethod

MAX_AMOUNT = 10_000_000_000  # 10 milliards de FCFA : borne de saisie contre les fautes de frappe


class WebForm(forms.Form):
    """Formulaire de base : libellés sans « : » final, comme sur la maquette."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)


class OnceForm(WebForm):
    """Formulaire d'écriture : un jeton caché empêche qu'un double envoi crée deux fois."""

    submission_id = forms.CharField(widget=forms.HiddenInput, max_length=64, required=False)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["submission_id"].initial = lambda: uuid.uuid4().hex


def _amount(label: str, *, required: bool = True) -> forms.IntegerField:
    return forms.IntegerField(
        label=label,
        min_value=0,
        max_value=MAX_AMOUNT,
        required=required,
        localize=False,
        widget=forms.NumberInput(attrs={"class": "money", "inputmode": "numeric", "step": 1}),
    )


class CaseForm(OnceForm):
    customer_name = forms.CharField(label="Nom du client", max_length=200)
    customer_phone = forms.CharField(
        label="Téléphone (format international)", max_length=32, required=False
    )
    departure_date = forms.DateField(
        label="Date de départ",
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )


class LineForm(OnceForm):
    kind = forms.ChoiceField(label="Type", choices=LineKind.choices)
    label = forms.CharField(label="Libellé (trajet, prestation)", max_length=200)
    passenger_name = forms.CharField(label="Passager", max_length=200, required=False)
    carrier = forms.CharField(label="Transporteur", max_length=120, required=False)
    ticket_number = forms.CharField(label="Numéro de billet", max_length=32, required=False)
    price_xaf = _amount("Prix de vente (FCFA)")
    cost_xaf = _amount("Coût d'achat (FCFA)", required=False)


class PaymentForm(WebForm):
    method = forms.ChoiceField(label="Mode", choices=PaymentMethod.choices)
    amount_xaf = forms.IntegerField(
        label="Montant (FCFA)",
        min_value=1,
        max_value=MAX_AMOUNT,
        localize=False,
        widget=forms.NumberInput(attrs={"class": "money", "inputmode": "numeric", "step": 1}),
    )
    reference = forms.CharField(label="Référence", max_length=64, required=False)
    received_on = forms.DateField(
        label="Date de réception", widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
    )
    idempotency_key = forms.CharField(widget=forms.HiddenInput, max_length=64)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["received_on"].initial = timezone.localdate
        self.fields["idempotency_key"].initial = lambda: uuid.uuid4().hex


MODE_CHOICES = [
    (LineKind.AIR_TICKET.value, "Avion"),
    (LineKind.BUS_TICKET.value, "Bus"),
    (LineKind.TRAIN_TICKET.value, "Train"),
    (LineKind.BOAT_TICKET.value, "Bateau"),
    (LineKind.FREE_SERVICE.value, "Prestation"),
]


class QuickEntryForm(OnceForm):
    """Saisie rapide : client, dossier et première ligne en un seul geste."""

    kind = forms.ChoiceField(
        label="Mode",
        choices=MODE_CHOICES,
        initial=LineKind.AIR_TICKET.value,
        widget=forms.RadioSelect,
    )
    origin = forms.CharField(
        label="Départ",
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Douala"}),
    )
    destination = forms.CharField(
        label="Arrivée",
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Yaoundé"}),
    )
    service_label = forms.CharField(label="Prestation", max_length=200, required=False)
    departure_date = forms.DateField(
        label="Date de départ",
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    customer_name = forms.CharField(label="Client", max_length=200)
    customer_phone = forms.CharField(label="Téléphone (+indicatif)", max_length=32, required=False)
    passenger_name = forms.CharField(label="Passager", max_length=200, required=False)
    carrier = forms.CharField(label="Transporteur", max_length=120, required=False)
    ticket_number = forms.CharField(label="Numéro de billet", max_length=32, required=False)
    price_xaf = _amount("Prix (FCFA)")
    cost_xaf = _amount("Coût (FCFA)", required=False)

    def clean(self) -> dict[str, object]:
        data = super().clean() or {}
        kind = data.get("kind")
        if kind == LineKind.FREE_SERVICE.value:
            # Les champs propres aux billets sont masqués pour une prestation : on les ignore.
            data["ticket_number"] = ""
            data["carrier"] = ""
            if not data.get("service_label", "").strip():
                self.add_error("service_label", "Décrivez la prestation.")
            data["label"] = data.get("service_label", "").strip()
        elif kind:
            for name in ("origin", "destination"):
                if not data.get(name, "").strip():
                    self.add_error(name, "Ce champ est obligatoire.")
            data["label"] = (
                f"{data.get('origin', '').strip()} → {data.get('destination', '').strip()}"
            )
        return data


class MemberForm(OnceForm):
    username = forms.RegexField(
        label="Identifiant",
        regex=r"^[\w.@+-]+$",
        max_length=150,
        error_messages={"invalid": "Lettres, chiffres et . @ + - _ seulement, sans espace."},
    )
    password = forms.CharField(
        label="Mot de passe provisoire",
        min_length=8,
        max_length=128,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
    )
    role = forms.ChoiceField(
        label="Rôle", choices=[("agent", "Agent"), ("manager", "Gérant")], initial="agent"
    )


class ClosePeriodForm(WebForm):
    month = forms.CharField(widget=forms.HiddenInput, max_length=7)
    confirm = forms.CharField(label="Tapez CLÔTURER pour confirmer", max_length=20, strip=True)

    def clean_confirm(self) -> str:
        value = self.cleaned_data["confirm"]
        if value.upper() != "CLÔTURER":
            raise forms.ValidationError("Tapez le mot CLÔTURER pour confirmer.")
        return value
