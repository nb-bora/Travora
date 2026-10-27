"""Champs de formulaire communs aux parcours."""

import re
from typing import Any

from django import forms

from apps.crm.exceptions import InvalidPhoneNumber
from apps.crm.services.public import CrmService
from apps.web.forms import MAX_AMOUNT, WebForm

__all__ = [
    "WebForm",
    "amount",
    "clean_phone",
    "date_field",
    "datetime_field",
    "integer",
    "text",
    "time_field",
    "upper_code",
]

NUMBER_ATTRS = {"class": "money", "inputmode": "numeric", "step": 1, "min": 0}


def amount(label: str, *, required: bool = True, initial: int | None = None) -> forms.IntegerField:
    return forms.IntegerField(
        label=label,
        min_value=0,
        max_value=MAX_AMOUNT,
        required=required,
        initial=initial,
        localize=False,
        widget=forms.NumberInput(attrs=NUMBER_ATTRS),
    )


def integer(label: str, *, minimum: int = 0, maximum: int = 99, initial: int | None = None,
            required: bool = True) -> forms.IntegerField:  # fmt: skip
    return forms.IntegerField(
        label=label,
        min_value=minimum,
        max_value=maximum,
        initial=initial,
        required=required,
        localize=False,
        widget=forms.NumberInput(attrs={"class": "money", "inputmode": "numeric", "step": 1}),
    )


def text(label: str, *, max_length: int = 120, required: bool = True, placeholder: str = "",
         css: str = "") -> forms.CharField:  # fmt: skip
    attrs: dict[str, str] = {}
    if placeholder:
        attrs["placeholder"] = placeholder
    if css:
        attrs["class"] = css
    return forms.CharField(
        label=label,
        max_length=max_length,
        required=required,
        strip=True,
        widget=forms.TextInput(attrs=attrs),
    )


def date_field(label: str, *, required: bool = True) -> forms.DateField:
    return forms.DateField(
        label=label,
        required=required,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )


def time_field(label: str, *, required: bool = False) -> forms.TimeField:
    return forms.TimeField(
        label=label,
        required=required,
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
    )


def datetime_field(label: str, *, required: bool = False) -> forms.DateTimeField:
    return forms.DateTimeField(
        label=label,
        required=required,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
    )


CODE = re.compile(r"[A-Z0-9]+")


def upper_code(value: str, *, length: int | None = None, label: str = "Ce code") -> str:
    """Code alphanumérique en majuscules (ASCII), éventuellement d'une longueur exacte."""
    cleaned = "".join(ch for ch in value.upper() if ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    if value.strip() and length is not None and len(cleaned) != length:
        raise forms.ValidationError(f"{label} compte {length} caractères.")
    return cleaned


def clean_phone(value: str) -> str:
    """Numéro au format international ; message clair si invalide."""
    try:
        return CrmService.normalize_phone(value)
    except InvalidPhoneNumber as error:
        raise forms.ValidationError(str(error)) from error


def initial_from(data: dict[str, Any] | None) -> dict[str, Any]:
    return dict(data or {})
