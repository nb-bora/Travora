import re
from datetime import timedelta

from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.cases.services.public import CasesService
from apps.tenancy.services.public import TenancyService
from tests.conftest import PASSWORD, AgencyFixture

ETICKET = (
    "ELECTRONIC TICKET RECEIPT\nPassenger : NDONG/MARIE MS\nTicket number : 057-2345678901\n"
    "Booking ref : K7QX2B\nAirline : AIR FRANCE\nDLA 20NOV 09:15 -> CDG 20NOV 15:40\n"
    "Fare : XAF 520000\nIssued : 03 NOV 2026\n"
)


def login(username: str) -> Client:
    client = Client()
    assert client.login(username=username, password=PASSWORD)
    return client


def step(mode: str, number: int) -> str:
    return reverse("web:flow_step", kwargs={"mode": mode, "step": number})


def air_trip(**overrides: str) -> dict[str, str]:
    day = (timezone.localdate() + timedelta(days=30)).isoformat()
    return {
        "action": "next",
        "origin": "Douala (DLA)",
        "destination": "Paris (CDG)",
        "departure_date": day,
        "departure_time": "09:15",
        "arrival_time": "15:40",
        "carrier": "Air France",
        "booking_reference": "k7qx2b",
        "ticket_time_limit": "",
        "customer_name": "Marie Ndong",
        "customer_phone": "+237 677 12 34 56",
    } | overrides


def air_travellers(count: int = 2, **overrides: str) -> dict[str, str]:
    data = {
        "action": "next",
        "form-TOTAL_FORMS": str(count),
        "form-INITIAL_FORMS": "0",
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "9",
        "pricing-fare_base_xaf": "375000",
        "pricing-taxes_xaf": "95000",
        "pricing-agency_fee_xaf": "50000",
        "pricing-cost_xaf": "470000",
    }
    names = ["NDONG/MARIE MS", "NDONG/JEAN MR", "NDONG/PAUL MR"]
    for index in range(count):
        data[f"form-{index}-name"] = names[index]
        data[f"form-{index}-passenger_type"] = "adult"
        data[f"form-{index}-ticket_number"] = f"057 234567890{index + 1}"
    return data | overrides


def run_air_flow(client: Client, count: int = 2) -> str:
    """Parcours complet jusqu'à la confirmation ; renvoie l'adresse de la page de paiement."""
    client.get(reverse("web:flow_start", kwargs={"mode": "air"}))
    assert client.post(step("air", 1), air_trip()).status_code == 302
    assert client.post(step("air", 2), air_travellers(count)).status_code == 302
    response = client.post(step("air", 3), {"action": "confirm"})
    assert response.status_code == 302
    return str(response["Location"])


def test_the_chooser_offers_the_air_flow_and_start_redirects_to_step_one(
    agency_a: AgencyFixture,
) -> None:
    client = login("alpha-manager")
    page = client.get(reverse("web:flow_chooser")).content.decode()
    assert "Avion" in page
    response = client.get(reverse("web:flow_start", kwargs={"mode": "air"}))
    assert response.status_code == 302
    assert response["Location"] == step("air", 1)
    assert client.get(reverse("web:flow_start", kwargs={"mode": "zeppelin"})).status_code == 404


def test_pasting_a_ticket_fills_step_one_and_the_passengers(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    client.get(reverse("web:flow_start", kwargs={"mode": "air"}))
    response = client.post(step("air", 1), {"action": "paste", "text": ETICKET})
    page = response.content.decode()

    assert response.status_code == 200
    assert "Reconnu dans le texte" in page
    assert "09:15" in page
    assert "15:40" in page
    assert "6 h 25" in page
    for expected in ("K7QX2B", "Marie Ndong", 'value="DLA"', 'value="CDG"', "Air France"):
        assert expected in page

    second = client.get(step("air", 2)).content.decode()
    assert "NDONG/MARIE MS" in second
    assert "0572345678901" in second or "057 2345678901" in second
    assert 'value="520000"' in second


def test_a_complete_air_flow_creates_the_case_issues_the_tickets_and_records_a_payment(
    agency_a: AgencyFixture,
) -> None:
    manager = login("alpha-manager")
    pay_url = run_air_flow(manager)

    page = manager.get(pay_url).content.decode()
    assert "Solde dû" in page
    assert "1 040 000" in page

    with TenancyService.scope(agency_a.id):
        cases = CasesService.list_cases(agency_a.manager)
        assert len(cases) == 1
        detail = CasesService.get_case(agency_a.manager, cases[0].id)
    assert cases[0].price_total_xaf == 1_040_000
    assert cases[0].recognized_margin_xaf == 100_000
    assert [line.issued_on is not None for line in detail.lines] == [True, True]
    assert detail.lines[0].ticket_number == "0572345678901"
    assert detail.lines[0].details["booking_reference"] == "K7QX2B"
    assert detail.lines[0].details["fare_base_xaf"] == 375_000

    key = re.search(r'name="idempotency_key"[^>]*value="([^"]*)"', page)
    assert key is not None
    response = manager.post(
        pay_url,
        {
            "action": "pay",
            "method": "mobile_money",
            "amount_xaf": "520000",
            "received_on": str(timezone.localdate()),
            "reference": "MP240103",
            "idempotency_key": key.group(1),
        },
    )
    assert response.status_code == 302
    done = manager.get(response["Location"]).content.decode()
    assert "2 billets émis" in done
    assert "520 000" in done
    assert "https://wa.me/237677123456?text=" in done
    assert "Présentez-vous à l" in done


def test_confirming_twice_never_creates_two_cases(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    run_air_flow(manager)
    again = manager.post(step("air", 3), {"action": "confirm"})
    assert again.status_code == 302  # plus de brouillon : retour au début, rien créé
    with TenancyService.scope(agency_a.id):
        assert len(CasesService.list_cases(agency_a.manager)) == 1


def test_an_agent_never_sees_the_margin_or_the_ledger_in_the_flow(agency_a: AgencyFixture) -> None:
    agent = login("alpha-agent")
    agent.get(reverse("web:flow_start", kwargs={"mode": "air"}))
    agent.post(step("air", 1), air_trip())
    second = agent.get(step("air", 2)).content.decode()
    assert "Marge prévue" not in second
    assert "reste visible du gérant seulement" in second
    agent.post(step("air", 2), air_travellers())
    third = agent.get(step("air", 3)).content.decode()
    assert "Marge" not in third
    assert "Fournisseur" not in third
    assert "réservé au gérant" in third

    manager_page = login("alpha-manager")
    manager_page.get(reverse("web:flow_start", kwargs={"mode": "air"}))
    manager_page.post(step("air", 1), air_trip())
    manager_page.post(step("air", 2), air_travellers())
    seen = manager_page.get(step("air", 3)).content.decode()
    assert "Fournisseur" in seen
    assert "Marge" in seen


def test_the_agent_who_confirms_stores_the_cost_without_reading_it_back(
    agency_a: AgencyFixture,
) -> None:
    agent = login("alpha-agent")
    pay_url = run_air_flow(agent, count=1)
    page = agent.get(pay_url).content.decode()
    assert "470 000" not in page
    assert "fare_base" not in page


def test_step_validation_explains_each_mistake(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    client.get(reverse("web:flow_start", kwargs={"mode": "air"}))

    bad_trip = client.post(step("air", 1), air_trip(origin="", customer_phone="12"))
    assert bad_trip.status_code == 422
    assert "Numéro invalide" in bad_trip.content.decode()
    short_ref = client.post(step("air", 1), air_trip(booking_reference="AB"))
    assert "compte 6 caractères" in short_ref.content.decode()

    client.post(step("air", 1), air_trip())
    short_ticket = client.post(
        step("air", 2), air_travellers(1, **{"form-0-ticket_number": "057 23456"})
    )
    assert "13 chiffres" in short_ticket.content.decode()
    duplicate = client.post(
        step("air", 2), air_travellers(2, **{"form-1-ticket_number": "057 2345678901"})
    )
    assert duplicate.status_code == 422
    assert "saisi deux fois" in duplicate.content.decode()
    nothing = client.post(
        step("air", 2), air_travellers(1, **{"form-0-DELETE": "on", "form-TOTAL_FORMS": "1"})
    )
    assert nothing.status_code == 422


def test_the_steps_cannot_be_skipped(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    client.get(reverse("web:flow_start", kwargs={"mode": "air"}))
    assert client.get(step("air", 2))["Location"] == step("air", 1)
    client.post(step("air", 1), air_trip())
    assert client.get(step("air", 3))["Location"] == step("air", 2)
    assert client.get(step("air", 4)).status_code == 404


def test_adding_and_removing_passenger_rows_needs_no_validation(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    client.get(reverse("web:flow_start", kwargs={"mode": "air"}))
    client.post(step("air", 1), air_trip())
    added = client.post(step("air", 2), air_travellers(1) | {"action": "add"})
    body = added.content.decode()
    assert added.status_code == 200
    assert 'name="form-1-name"' in body
    assert "field-error" not in body
    removed = client.post(
        step("air", 2),
        air_travellers(2, **{"form-1-DELETE": "on"}) | {"action": "remove"},
    )
    assert 'name="form-1-name"' not in removed.content.decode()


def test_the_issue_deadline_is_shown_and_flags_a_late_one(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    client.get(reverse("web:flow_start", kwargs={"mode": "air"}))
    soon = (timezone.localtime() + timedelta(days=1, hours=3)).strftime("%Y-%m-%dT%H:%M")
    client.post(step("air", 1), air_trip(ticket_time_limit=soon))
    client.post(step("air", 2), air_travellers())
    page = client.get(step("air", 3)).content.decode()
    assert "À émettre avant le" in page
    assert "Il reste 1 j" in page
    assert "annuler la réservation K7QX2B" in page

    late = (timezone.localtime() - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")
    client.post(step("air", 1), air_trip(ticket_time_limit=late))
    assert "Délai dépassé" in client.get(step("air", 3)).content.decode()


def test_a_flow_belongs_to_the_session_of_one_user(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    alpha = login("alpha-manager")
    alpha.get(reverse("web:flow_start", kwargs={"mode": "air"}))
    alpha.post(step("air", 1), air_trip())
    other = login("bravo-manager")
    assert other.get(step("air", 2))["Location"] == reverse(
        "web:flow_start", kwargs={"mode": "air"}
    )
    pay_url = run_air_flow(alpha)
    assert other.get(pay_url).status_code == 404  # le dossier d'une autre agence


def test_the_payment_page_refuses_a_bad_payment_and_keeps_the_input(
    agency_a: AgencyFixture,
) -> None:
    manager = login("alpha-manager")
    pay_url = run_air_flow(manager, count=1)
    response = manager.post(
        pay_url,
        {
            "action": "pay",
            "method": "transfer",
            "amount_xaf": "100000",
            "received_on": str(timezone.localdate()),
            "reference": "",
            "idempotency_key": "k1",
        },
    )
    body = response.content.decode()
    assert response.status_code == 200
    assert "référence" in body.lower()
    assert 'value="100000"' in body
    skip = manager.post(pay_url, {"action": "skip"})
    assert skip.status_code == 302
    assert skip["Location"].endswith("/remise/")
