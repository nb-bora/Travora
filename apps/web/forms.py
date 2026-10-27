import uuid

from django import forms
from django.utils import timezone

from apps.cases.constants import LineKind
from apps.payments.constants import PaymentMethod

MAX_AMOUNT = 10_000_000_000  # 10 milliards de FCFA : borne de saisie contre les fautes de frappe


def _amount(label: str, *, required: bool = True) -> forms.IntegerField:
    return forms.IntegerField(
        label=label, min_value=0, max_value=MAX_AMOUNT, required=required, localize=False
    )


class CaseForm(forms.Form):
    customer_name = forms.CharField(label="Nom du client", max_length=200)
    customer_phone = forms.CharField(
        label="Téléphone (format international)", max_length=32, required=False
    )
    departure_date = forms.DateField(
        label="Date de départ", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )


class LineForm(forms.Form):
    kind = forms.ChoiceField(label="Type", choices=LineKind.choices)
    label = forms.CharField(label="Libellé (trajet, prestation)", max_length=200)
    passenger_name = forms.CharField(label="Passager", max_length=200, required=False)
    carrier = forms.CharField(label="Transporteur", max_length=120, required=False)
    ticket_number = forms.CharField(label="Numéro de billet", max_length=32, required=False)
    price_xaf = _amount("Prix de vente (FCFA)")
    cost_xaf = _amount("Coût d'achat (FCFA)", required=False)


class PaymentForm(forms.Form):
    method = forms.ChoiceField(label="Mode", choices=PaymentMethod.choices)
    amount_xaf = forms.IntegerField(
        label="Montant (FCFA)", min_value=1, max_value=MAX_AMOUNT, localize=False
    )
    reference = forms.CharField(label="Référence", max_length=64, required=False)
    received_on = forms.DateField(
        label="Date de réception", widget=forms.DateInput(attrs={"type": "date"})
    )
    idempotency_key = forms.CharField(widget=forms.HiddenInput, max_length=64)

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.fields["received_on"].initial = timezone.localdate
        self.fields["idempotency_key"].initial = lambda: uuid.uuid4().hex
