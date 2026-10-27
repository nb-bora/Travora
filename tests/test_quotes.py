import importlib
import json
from collections.abc import Iterator
from datetime import date, timedelta
from uuid import UUID

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.cases.constants import LineKind
from apps.cases.exceptions import CaseNotFound, CaseNotOpen
from apps.cases.services.public import CasesService
from apps.crm.services.public import CrmService
from apps.quotes import pdf
from apps.quotes.constants import QuoteStatus
from apps.quotes.exceptions import InvalidQuote, InvalidTransition, QuoteFrozen, QuoteNotFound
from apps.quotes.models import Quote
from apps.quotes.services.public import QuotesService
from apps.quotes.whatsapp import whatsapp_link
from apps.tenancy.services.public import TenancyService
from tests.conftest import AgencyFixture, runtime_role

TODAY = timezone.localdate()
LATER = date.today() + timedelta(days=15)
SECRET_COST = 456_789


def pango_available() -> bool:
    try:
        importlib.import_module("weasyprint")
    except OSError:
        return False
    return True


@pytest.fixture
def scoped(agency_a: AgencyFixture) -> Iterator[AgencyFixture]:
    with TenancyService.scope(agency_a.id):
        yield agency_a


def case_with_lines(agency: AgencyFixture, phone: str = "+237677123456") -> UUID:
    customer = CrmService.find_or_create_customer(agency.agent, name="Marie Ndong", phone=phone)
    case_id = CasesService.create_case(agency.agent, customer_id=customer.id)
    CasesService.add_line(
        agency.agent,
        case_id=case_id,
        kind=LineKind.AIR_TICKET,
        label="DLA-CDG",
        price_xaf=500_000,
        cost_xaf=SECRET_COST,
        passenger_name="NDONG/MARIE",
    )
    CasesService.add_line(
        agency.agent,
        case_id=case_id,
        kind=LineKind.FREE_SERVICE,
        label="Hôtel Paris, 2 nuits",
        price_xaf=180_000,
        cost_xaf=150_000,
    )
    return case_id


def test_a_draft_snapshots_prices_and_never_the_cost(scoped: AgencyFixture) -> None:
    case_id = case_with_lines(scoped)
    view = QuotesService.create_draft(scoped.agent, case_id=case_id, valid_until=LATER)

    assert view.version == 1
    assert view.total_xaf == 680_000
    assert [line.label for line in view.lines] == ["DLA-CDG", "Hôtel Paris, 2 nuits"]
    stored = Quote.objects.get(id=view.id)
    assert "cost" not in json.dumps(stored.lines)
    assert str(SECRET_COST) not in json.dumps(stored.lines)


def test_voided_lines_are_left_out_and_versions_increase(scoped: AgencyFixture) -> None:
    case_id = case_with_lines(scoped)
    first = QuotesService.create_draft(scoped.agent, case_id=case_id, valid_until=LATER)
    detail = CasesService.get_case(scoped.manager, case_id)
    CasesService.void_line(scoped.manager, line_id=detail.lines[1].id, voided_on=TODAY)
    second = QuotesService.create_draft(scoped.agent, case_id=case_id, valid_until=LATER)

    assert (first.version, second.version) == (1, 2)
    assert second.total_xaf == 500_000


def test_a_quote_needs_lines_and_an_open_case(scoped: AgencyFixture) -> None:
    customer = CrmService.find_or_create_customer(scoped.agent, name="Vide", phone="")
    empty = CasesService.create_case(scoped.agent, customer_id=customer.id)
    with pytest.raises(InvalidQuote):
        QuotesService.create_draft(scoped.agent, case_id=empty, valid_until=LATER)

    case_id = case_with_lines(scoped)
    CasesService.cancel_case(scoped.manager, case_id=case_id, cancelled_on=TODAY)
    with pytest.raises(CaseNotOpen):
        QuotesService.create_draft(scoped.agent, case_id=case_id, valid_until=LATER)


def test_sending_freezes_the_version(scoped: AgencyFixture) -> None:
    case_id = case_with_lines(scoped)
    draft = QuotesService.create_draft(scoped.agent, case_id=case_id, valid_until=LATER)
    QuotesService.send(scoped.agent, quote_id=draft.id)

    quote = Quote.objects.get(id=draft.id)
    quote.lines = [{"label": "Autre", "passenger_name": "", "price_xaf": 1}]
    with pytest.raises(QuoteFrozen):
        quote.save()
    quote = Quote.objects.get(id=draft.id)
    quote.valid_until = LATER + timedelta(days=30)
    with pytest.raises(QuoteFrozen):
        quote.save()
    with pytest.raises(InvalidTransition):
        QuotesService.send(scoped.agent, quote_id=draft.id)


def test_a_new_version_is_the_way_to_change_a_sent_quote(scoped: AgencyFixture) -> None:
    case_id = case_with_lines(scoped)
    first = QuotesService.create_draft(scoped.agent, case_id=case_id, valid_until=LATER)
    QuotesService.send(scoped.agent, quote_id=first.id)
    CasesService.add_line(
        scoped.agent,
        case_id=case_id,
        kind=LineKind.FREE_SERVICE,
        label="Transfert",
        price_xaf=20_000,
    )
    second = QuotesService.create_draft(scoped.agent, case_id=case_id, valid_until=LATER)

    assert second.total_xaf == 700_000
    assert QuotesService.quotes_for_case(scoped.agent, case_id)[0].total_xaf == 680_000


def test_a_past_validity_date_cannot_be_sent(scoped: AgencyFixture) -> None:
    case_id = case_with_lines(scoped)
    draft = QuotesService.create_draft(
        scoped.agent, case_id=case_id, valid_until=date.today() - timedelta(days=1)
    )
    with pytest.raises(InvalidQuote):
        QuotesService.send(scoped.agent, quote_id=draft.id)


def test_sending_returns_a_prefilled_whatsapp_link_for_the_customer(
    scoped: AgencyFixture,
) -> None:
    case_id = case_with_lines(scoped)
    draft = QuotesService.create_draft(scoped.agent, case_id=case_id, valid_until=LATER)
    delivery = QuotesService.send(scoped.agent, quote_id=draft.id)

    assert delivery.total_xaf == 680_000
    assert delivery.whatsapp_url.startswith("https://wa.me/237677123456?text=")
    assert "Marie%20Ndong" in delivery.whatsapp_url
    assert "680%E2%80%AF000%20FCFA" in delivery.whatsapp_url
    assert " " not in delivery.whatsapp_url
    assert str(SECRET_COST) not in delivery.message


def test_a_customer_without_phone_gets_a_contact_picker_link(scoped: AgencyFixture) -> None:
    case_id = case_with_lines(scoped, phone="")
    draft = QuotesService.create_draft(scoped.agent, case_id=case_id, valid_until=LATER)
    assert QuotesService.send(scoped.agent, quote_id=draft.id).whatsapp_url.startswith(
        "https://wa.me/?text="
    )


@pytest.mark.parametrize(
    ("phone", "message", "expected"),
    [
        ("+237677123456", "Bonjour", "https://wa.me/237677123456?text=Bonjour"),
        (
            "+237677123456",
            "a b&c=d?\né",
            "https://wa.me/237677123456?text=a%20b%26c%3Dd%3F%0A%C3%A9",
        ),
        ("", "Salut", "https://wa.me/?text=Salut"),
        ("pas-un-numero", "Salut", "https://wa.me/?text=Salut"),
    ],
)
def test_whatsapp_links_are_encoded(phone: str, message: str, expected: str) -> None:
    assert whatsapp_link(phone, message) == expected


def test_a_sent_quote_is_answered_once(scoped: AgencyFixture) -> None:
    case_id = case_with_lines(scoped)
    draft = QuotesService.create_draft(scoped.agent, case_id=case_id, valid_until=LATER)
    with pytest.raises(InvalidTransition):
        QuotesService.accept(scoped.agent, quote_id=draft.id)

    QuotesService.send(scoped.agent, quote_id=draft.id)
    accepted = QuotesService.accept(scoped.agent, quote_id=draft.id)

    assert accepted.status is QuoteStatus.ACCEPTED
    with pytest.raises(InvalidTransition):
        QuotesService.refuse(scoped.agent, quote_id=draft.id)


def test_a_sent_quote_past_its_date_is_reported_as_expired(
    scoped: AgencyFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    case_id = case_with_lines(scoped)
    draft = QuotesService.create_draft(scoped.agent, case_id=case_id, valid_until=LATER)
    QuotesService.send(scoped.agent, quote_id=draft.id)
    assert QuotesService.expired_sent_quotes(scoped.agent) == []

    monkeypatch.setattr(timezone, "localdate", lambda: LATER + timedelta(days=1))
    expired = QuotesService.expired_sent_quotes(scoped.agent)
    assert [quote.id for quote in expired] == [draft.id]
    assert expired[0].is_expired


def test_the_database_refuses_two_quotes_with_the_same_version(scoped: AgencyFixture) -> None:
    case_id = case_with_lines(scoped)
    QuotesService.create_draft(scoped.agent, case_id=case_id, valid_until=LATER)
    with pytest.raises(IntegrityError), transaction.atomic():
        Quote.objects.create(case_id=case_id, version=1, valid_until=LATER, lines=[])


def test_the_html_of_the_quote_shows_prices_and_no_cost(scoped: AgencyFixture) -> None:
    case_id = case_with_lines(scoped)
    view = QuotesService.create_draft(scoped.agent, case_id=case_id, valid_until=LATER)
    html = pdf.render_html(
        quote=view,
        reference="2026-0001",
        customer_name="Marie Ndong",
        agency_name="Alpha Voyages",
        logo_path="",
    )

    assert "2026-0001" in html
    assert "Alpha Voyages" in html
    assert "680 000 FCFA" in html
    assert str(SECRET_COST) not in html


@pytest.mark.skipif(not pango_available(), reason="Bibliothèques Pango absentes")
def test_the_quote_renders_as_a_pdf(scoped: AgencyFixture) -> None:
    case_id = case_with_lines(scoped)
    draft = QuotesService.create_draft(scoped.agent, case_id=case_id, valid_until=LATER)
    assert QuotesService.render_pdf(scoped.agent, quote_id=draft.id).startswith(b"%PDF")


def test_quotes_never_cross_agencies(agency_a: AgencyFixture, agency_b: AgencyFixture) -> None:
    with TenancyService.scope(agency_b.id):
        foreign_case = case_with_lines(agency_b)
        foreign = QuotesService.create_draft(
            agency_b.agent, case_id=foreign_case, valid_until=LATER
        )
    with runtime_role(), TenancyService.scope(agency_a.id):
        assert QuotesService.quotes_for_case(agency_a.agent, foreign_case) == []
        with pytest.raises(CaseNotFound):
            QuotesService.create_draft(agency_a.agent, case_id=foreign_case, valid_until=LATER)
        with pytest.raises(QuoteNotFound):
            QuotesService.send(agency_a.agent, quote_id=foreign.id)
