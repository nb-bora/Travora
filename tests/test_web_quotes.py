import importlib
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.cases.constants import LineKind
from apps.cases.services.public import CasesService
from apps.crm.services.public import CrmService
from apps.quotes.constants import QuoteStatus
from apps.quotes.models import Quote
from apps.quotes.services.public import QuotesService
from apps.tenancy.services.public import TenancyService
from tests.conftest import PASSWORD, AgencyFixture

SECRET_COST = 456_789
LATER = timezone.localdate() + timedelta(days=10)


def login(username: str) -> Client:
    client = Client()
    assert client.login(username=username, password=PASSWORD)
    return client


def make_case(agency: AgencyFixture) -> UUID:
    with TenancyService.scope(agency.id):
        customer = CrmService.find_or_create_customer(
            agency.agent, name="Marie Ndong", phone="+237677123456"
        )
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
    return case_id


def make_quote(agency: AgencyFixture, case_id: UUID) -> UUID:
    with TenancyService.scope(agency.id):
        return QuotesService.create_draft(agency.agent, case_id=case_id, valid_until=LATER).id


def test_the_quote_pages_require_a_login(db: None) -> None:
    for name in ("web:quote_list",):
        response = Client().get(reverse(name))
        assert response.status_code == 302
        assert response["Location"].startswith(reverse("web:login"))


def test_an_agent_creates_a_draft_from_the_case_without_seeing_costs(
    agency_a: AgencyFixture,
) -> None:
    case_id = make_case(agency_a)
    client = login("alpha-agent")

    case_page = client.get(reverse("web:case_detail", args=[case_id])).content.decode()
    assert "Créer un devis" in case_page
    assert str(SECRET_COST) not in case_page

    response = client.post(
        reverse("web:quote_create", args=[case_id]), {"valid_until": LATER.isoformat()}
    )
    assert response.status_code == 302
    detail = client.get(response["Location"]).content.decode()
    assert "DLA-CDG" in detail
    assert "500" in detail
    assert "Envoyer au client" in detail
    assert str(SECRET_COST) not in detail


def test_a_past_validity_date_is_refused_with_a_message(agency_a: AgencyFixture) -> None:
    case_id = make_case(agency_a)
    client = login("alpha-manager")
    past = (timezone.localdate() - timedelta(days=1)).isoformat()

    response = client.post(reverse("web:quote_create", args=[case_id]), {"valid_until": past})
    assert response.status_code == 302
    assert response["Location"] == reverse("web:case_detail", args=[case_id])
    page = client.get(response["Location"]).content.decode()
    assert "date de validité à venir" in page
    with TenancyService.scope(agency_a.id):
        assert QuotesService.quotes_for_case(agency_a.agent, case_id) == []


def test_a_case_without_lines_explains_why_no_quote_is_made(agency_a: AgencyFixture) -> None:
    with TenancyService.scope(agency_a.id):
        customer = CrmService.find_or_create_customer(agency_a.agent, name="Vide", phone="")
        case_id = CasesService.create_case(agency_a.agent, customer_id=customer.id)
    client = login("alpha-manager")

    response = client.post(
        reverse("web:quote_create", args=[case_id]), {"valid_until": LATER.isoformat()}
    )
    page = client.get(response["Location"]).content.decode()
    assert "aucune ligne à chiffrer" in page


def test_sending_shows_the_whatsapp_message_once_and_freezes_the_quote(
    agency_a: AgencyFixture,
) -> None:
    case_id = make_case(agency_a)
    quote_id = make_quote(agency_a, case_id)
    client = login("alpha-agent")

    response = client.post(reverse("web:quote_send", args=[quote_id]))
    assert response.status_code == 302
    page = client.get(response["Location"]).content.decode()
    assert "https://wa.me/237677123456" in page
    assert "Ouvrir WhatsApp" in page
    assert "Le client accepte" in page
    assert "Envoyer au client" not in page

    again = client.get(reverse("web:quote_detail", args=[quote_id])).content.decode()
    assert "Ouvrir WhatsApp" not in again  # le message ne s'affiche qu'une fois

    repeat = client.post(reverse("web:quote_send", args=[quote_id]))
    assert "Seul un brouillon peut être envoyé" in client.get(repeat["Location"]).content.decode()


def test_the_customer_answer_is_recorded_and_cannot_be_given_twice(
    agency_a: AgencyFixture,
) -> None:
    case_id = make_case(agency_a)
    quote_id = make_quote(agency_a, case_id)
    client = login("alpha-manager")
    premature = client.post(reverse("web:quote_accept", args=[quote_id]))
    assert (
        "Seul un devis envoyé reçoit une réponse"
        in client.get(premature["Location"]).content.decode()
    )

    client.post(reverse("web:quote_send", args=[quote_id]))
    client.post(reverse("web:quote_accept", args=[quote_id]))
    with TenancyService.scope(agency_a.id):
        assert QuotesService.get_quote(agency_a.agent, quote_id).status is QuoteStatus.ACCEPTED

    page = client.get(reverse("web:quote_detail", args=[quote_id])).content.decode()
    assert "a reçu une réponse" in page
    again = client.post(reverse("web:quote_refuse", args=[quote_id]))
    assert (
        "Seul un devis envoyé reçoit une réponse" in client.get(again["Location"]).content.decode()
    )


def test_a_refused_quote_is_listed_under_its_tab(agency_a: AgencyFixture) -> None:
    case_id = make_case(agency_a)
    quote_id = make_quote(agency_a, case_id)
    client = login("alpha-manager")
    client.post(reverse("web:quote_send", args=[quote_id]))
    client.post(reverse("web:quote_refuse", args=[quote_id]))

    refused = client.get(reverse("web:quote_list"), {"etat": "refused"}).content.decode()
    drafts = client.get(reverse("web:quote_list"), {"etat": "draft"}).content.decode()
    assert "Marie Ndong" in refused
    assert "Marie Ndong" not in drafts


def test_the_list_filters_by_search_and_ignores_unknown_tabs(agency_a: AgencyFixture) -> None:
    case_id = make_case(agency_a)
    make_quote(agency_a, case_id)
    client = login("alpha-agent")

    everything = client.get(reverse("web:quote_list"), {"etat": "n'importe quoi"})
    assert "Marie Ndong" in everything.content.decode()
    match = client.get(reverse("web:quote_list"), {"q": "ndong"}).content.decode()
    assert "Marie Ndong" in match
    miss = client.get(reverse("web:quote_list"), {"q": "zzz"}).content.decode()
    assert "Aucun résultat pour" in miss
    empty = login("alpha-manager").get(reverse("web:quote_list"), {"etat": "expired"})
    assert "Aucun devis ici" in empty.content.decode()


def test_an_expired_quote_is_flagged_everywhere(agency_a: AgencyFixture) -> None:
    case_id = make_case(agency_a)
    quote_id = make_quote(agency_a, case_id)
    client = login("alpha-manager")
    client.post(reverse("web:quote_send", args=[quote_id]))
    with TenancyService.scope(agency_a.id):
        Quote.objects.filter(id=quote_id).update(
            valid_until=timezone.localdate() - timedelta(days=2)
        )

    expired = client.get(reverse("web:quote_list"), {"etat": "expired"}).content.decode()
    assert "Marie Ndong" in expired
    detail = client.get(reverse("web:quote_detail", args=[quote_id])).content.decode()
    assert "Ce devis est expiré" in detail
    case_page = client.get(reverse("web:case_detail", args=[case_id])).content.decode()
    assert "Expiré" in case_page


def test_an_unknown_quote_is_a_404(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    ghost = uuid4()
    assert client.get(reverse("web:quote_detail", args=[ghost])).status_code == 404
    assert client.get(reverse("web:quote_pdf", args=[ghost])).status_code == 404
    missing = client.post(reverse("web:quote_send", args=[ghost]))
    assert missing.status_code == 302
    assert client.get(missing["Location"]).status_code == 404


def test_a_quote_of_another_agency_is_invisible(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    foreign_case = make_case(agency_b)
    foreign = make_quote(agency_b, foreign_case)
    client = login("alpha-manager")

    assert client.get(reverse("web:quote_detail", args=[foreign])).status_code == 404
    assert "Marie Ndong" not in client.get(reverse("web:quote_list")).content.decode()


def pango_available() -> bool:
    try:
        importlib.import_module("weasyprint")
    except OSError:
        return False
    return True


@pytest.mark.skipif(not pango_available(), reason="Bibliothèques Pango absentes")
def test_the_pdf_is_served_inline_and_never_cached(agency_a: AgencyFixture) -> None:
    case_id = make_case(agency_a)
    quote_id = make_quote(agency_a, case_id)

    response = login("alpha-agent").get(reverse("web:quote_pdf", args=[quote_id]))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert 'filename="devis-' in response["Content-Disposition"]
    assert "no-store" in response["Cache-Control"]
    assert response.content.startswith(b"%PDF")


def test_the_pdf_view_serves_what_the_facade_renders(
    agency_a: AgencyFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    case_id = make_case(agency_a)
    quote_id = make_quote(agency_a, case_id)
    monkeypatch.setattr(QuotesService, "render_pdf", lambda actor, quote_id: b"%PDF-test")

    response = login("alpha-agent").get(reverse("web:quote_pdf", args=[quote_id]))

    assert response.status_code == 200
    assert response.content == b"%PDF-test"
    assert response["Content-Type"] == "application/pdf"
    assert "no-store" in response["Cache-Control"]
