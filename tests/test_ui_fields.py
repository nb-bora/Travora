"""Champs outlined, états vides et assets d'interface de la couche web."""

from django import forms
from django.template.loader import render_to_string
from django.test import Client
from django.urls import reverse

from apps.web.templatetags.web_extras import (
    field_icon,
    field_prefix,
    field_state,
    field_suffix,
    is_choice_widget,
)
from tests.test_web import AgencyFixture, login


class SampleForm(forms.Form):
    customer_phone = forms.CharField(label="Téléphone")
    price_xaf = forms.IntegerField(label="Prix", min_value=1)
    note = forms.CharField(label="Note", required=False)
    urgent = forms.BooleanField(label="Urgent", required=False)


def render_field(form: SampleForm, name: str) -> str:
    return render_to_string("web/_field.html", {"field": form[name]})


def test_a_phone_field_gets_an_icon_and_the_country_prefix() -> None:
    html = render_field(SampleForm(), "customer_phone")
    assert "control-icon" in html
    assert "+237" in html


def test_an_amount_field_gets_the_currency_suffix() -> None:
    html = render_field(SampleForm(), "price_xaf")
    assert "FCFA" in html
    assert "control-icon" in html


def test_a_field_without_a_matching_icon_stays_plain() -> None:
    form = SampleForm()
    assert field_icon(form["note"]) == ""
    assert field_prefix(form["note"]) == ""
    assert field_suffix(form["note"]) == ""


def test_checkboxes_are_not_wrapped_in_a_control() -> None:
    form = SampleForm()
    assert is_choice_widget(form["urgent"])
    assert "control" not in render_field(form, "urgent")


def test_a_submitted_field_shows_its_error_or_success_state() -> None:
    form = SampleForm({"customer_phone": "699123456", "price_xaf": "0"})
    assert field_state(form["customer_phone"]) == "valid"
    assert field_state(form["price_xaf"]) == "invalid"
    assert field_state(SampleForm()["customer_phone"]) == ""
    assert "is-invalid" in render_field(form, "price_xaf")
    assert "is-valid" in render_field(form, "customer_phone")


def test_the_flow_pages_load_the_motion_assets_and_expose_the_step(
    agency_a: AgencyFixture,
) -> None:
    client = login("alpha-manager")
    page = client.get(reverse("web:flow_start", args=["bus"]), follow=True).content.decode()
    assert "web/flow-ui.css" in page
    assert "web/ui.css" in page
    assert 'data-step="1"' in page
    assert 'data-flow="bus"' in page
    assert "style=" not in page  # CSP : aucun style en ligne


def test_empty_lists_use_the_shared_empty_state(agency_a: AgencyFixture) -> None:
    page = login("alpha-manager").get(reverse("web:customer_list")).content.decode()
    assert "empty-state" in page
    assert "empty-art" in page


def test_the_chooser_page_still_renders_for_a_visitor_redirect(db: None) -> None:
    assert Client().get(reverse("web:flow_chooser")).status_code == 302
