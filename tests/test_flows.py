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


def bus_trip(**overrides: str) -> dict[str, str]:
    day = (timezone.localdate() + timedelta(days=20)).isoformat()
    return {
        "action": "next",
        "origin": "Douala",
        "destination": "Yaoundé",
        "departure_date": day,
        "departure_time": "08:00",
        "carrier": "Transporteur B",
        "station": "Agence centre",
        "service_class": "vip",
        "seats": "3",
        "price_per_seat": "9500",
        "trip_code": "kb-8f3a21",
        "seats_confirmed": "on",
        "customer_name": "Alain Kamga",
        "customer_phone": "+237 699 11 22 33",
    } | overrides


def bus_travellers(**overrides: str) -> dict[str, str]:
    data = {
        "action": "next",
        "form-TOTAL_FORMS": "3",
        "form-INITIAL_FORMS": "0",
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "9",
    }
    people = [("Alain Kamga", "12", "1"), ("Sophie Kamga", "13", "1"), ("Junior Kamga", "14", "2")]
    for index, (name, seat, bags) in enumerate(people):
        data[f"form-{index}-name"] = name
        data[f"form-{index}-traveller_phone"] = "+237 699 11 22 33" if index == 0 else ""
        data[f"form-{index}-seat"] = seat
        data[f"form-{index}-bags"] = bags
    return data | overrides


def test_a_complete_bus_flow_with_an_extra_bag(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    manager.get(reverse("web:flow_start", kwargs={"mode": "bus"}))
    assert manager.post(step("bus", 1), bus_trip()).status_code == 302
    second = manager.get(step("bus", 2)).content.decode()
    assert second.count('name="form-') >= 3  # une ligne par place annoncée
    assert "Plan du car" in second
    assert manager.post(step("bus", 2), bus_travellers()).status_code == 302

    third = manager.get(step("bus", 3)).content.decode()
    assert "Bagage supplémentaire" in third
    assert 'name="bag_price_xaf"' in third
    confirmed = manager.post(
        step("bus", 3),
        {
            "action": "confirm",
            "cost_per_seat_xaf": "8500",
            "bag_price_xaf": "2000",
            "cost_bag_xaf": "1500",
        },
    )
    assert confirmed.status_code == 302

    with TenancyService.scope(agency_a.id):
        case = CasesService.list_cases(agency_a.manager)[0]
        detail = CasesService.get_case(agency_a.manager, case.id)
    assert case.price_total_xaf == 3 * 9_500 + 2_000
    assert case.recognized_margin_xaf == 3 * 1_000 + 500
    assert len(detail.lines) == 4
    assert detail.lines[0].details["seat"] == "12"
    assert detail.lines[0].details["booking_reference"] == "KB8F3A21"

    done = manager.get(confirmed["Location"].replace("/paiement/", "/remise/")).content.decode()
    assert "Billet de voyage · Bus VIP" in done
    assert "KB8F3A21" in done
    assert "Agence centre" in done
    assert "https://wa.me/237699112233" in done


def test_the_bus_flow_requires_the_seats_to_be_confirmed(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    client.get(reverse("web:flow_start", kwargs={"mode": "bus"}))
    data = bus_trip()
    del data["seats_confirmed"]
    response = client.post(step("bus", 1), data)
    assert response.status_code == 422
    assert "Confirmez les places" in response.content.decode()


def test_two_travellers_cannot_share_a_seat(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    client.get(reverse("web:flow_start", kwargs={"mode": "bus"}))
    client.post(step("bus", 1), bus_trip())
    response = client.post(step("bus", 2), bus_travellers(**{"form-1-seat": "12"}))
    assert response.status_code == 422
    assert "saisi deux fois" in response.content.decode()
    bad = client.post(step("bus", 2), bus_travellers(**{"form-1-seat": "abc"}))
    assert "entre 1 et 99" in bad.content.decode()


def test_without_extra_bags_the_bag_fields_disappear(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    client.get(reverse("web:flow_start", kwargs={"mode": "bus"}))
    client.post(step("bus", 1), bus_trip())
    client.post(step("bus", 2), bus_travellers(**{"form-2-bags": "1"}))
    page = client.get(step("bus", 3)).content.decode()
    assert 'name="bag_price_xaf"' not in page
    assert (
        client.post(step("bus", 3), {"action": "confirm", "cost_per_seat_xaf": "8500"}).status_code
        == 302
    )


def test_the_seat_map_highlights_the_chosen_seats(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    client.get(reverse("web:flow_start", kwargs={"mode": "bus"}))
    client.post(step("bus", 1), bus_trip())
    client.post(step("bus", 2), bus_travellers())
    page = client.get(step("bus", 2)).content.decode()
    assert page.count("seat seat-chosen") >= 3
    assert "3 sur 3 places" in page


def test_an_agent_in_the_bus_flow_never_sees_margin_or_cost(agency_a: AgencyFixture) -> None:
    agent = login("alpha-agent")
    agent.get(reverse("web:flow_start", kwargs={"mode": "bus"}))
    agent.post(step("bus", 1), bus_trip())
    agent.post(step("bus", 2), bus_travellers())
    third = agent.get(step("bus", 3)).content.decode()
    assert "Marge" not in third
    assert "Fournisseur" not in third
    agent.post(
        step("bus", 3),
        {
            "action": "confirm",
            "cost_per_seat_xaf": "8500",
            "bag_price_xaf": "2000",
            "cost_bag_xaf": "1500",
        },
    )
    with TenancyService.scope(agency_a.id):
        case = CasesService.list_cases(agency_a.agent)[0]
    assert case.cost_total_xaf is None
    assert case.expected_margin_xaf is None


def train_trip(**overrides: str) -> dict[str, str]:
    day = (timezone.localdate() + timedelta(days=10)).isoformat()
    return {
        "action": "next",
        "origin": "Douala",
        "destination": "Yaoundé",
        "departure_date": day,
        "train": "Train 2",
        "departure_time": "09:00",
        "arrival_time": "13:20",
        "service_class": "comfort",
        "price": "8500",
        "booking_reference": "cr7h2k",
        "seat_confirmed": "on",
        "customer_name": "Awa Mbarga",
        "customer_phone": "+237 655 44 33 22",
    } | overrides


def train_traveller(**overrides: str) -> dict[str, str]:
    return {
        "action": "next",
        "form-TOTAL_FORMS": "1",
        "form-INITIAL_FORMS": "0",
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "9",
        "form-0-name": "Awa Mbarga",
        "form-0-traveller_phone": "+237 655 44 33 22",
        "form-0-doc_type": "cni",
        "form-0-doc_number": "CNI 112 458 903",
        "form-0-fare_type": "adult",
        "form-0-car": "3",
        "form-0-seat": "24",
        "form-0-bags": "1",
    } | overrides


def run_train_flow(client: Client) -> str:
    client.get(reverse("web:flow_start", kwargs={"mode": "train"}))
    assert client.post(step("train", 1), train_trip()).status_code == 302
    assert client.post(step("train", 2), train_traveller()).status_code == 302
    response = client.post(
        step("train", 3), {"action": "confirm", "cost_xaf": "8000", "agency_fee_xaf": "500"}
    )
    assert response.status_code == 302
    return str(response["Location"])


def test_a_complete_train_flow_with_cash_and_change(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    pay_url = run_train_flow(manager)

    with TenancyService.scope(agency_a.id):
        case = CasesService.list_cases(agency_a.manager)[0]
        detail = CasesService.get_case(agency_a.manager, case.id)
    assert case.price_total_xaf == 9_000
    assert case.recognized_margin_xaf == 1_000
    ticket = detail.lines[0]
    assert ticket.details["car"] == "3"
    assert ticket.details["doc_number"] == "CNI 112 458 903"
    assert ticket.details["booking_reference"] == "CR7H2K"

    page = manager.get(pay_url).content.decode()
    assert 'value="cash" checked' in page or "checked" in page.split('value="cash"')[1][:40]
    assert 'id="change-due"' in page
    paid = manager.post(
        pay_url,
        {
            "action": "pay",
            "method": "cash",
            "amount_xaf": "9000",
            "given_xaf": "10000",
            "received_on": str(timezone.localdate()),
            "reference": "",
            "idempotency_key": "cash1",
        },
    )
    assert paid.status_code == 302
    done = manager.get(paid["Location"]).content.decode()
    assert "Billet de train · Confort" in done
    assert "CR7H2K" in done
    assert "3 · 24" in done
    assert "Changer ou annuler" in done
    assert "Dossier soldé" in done


def test_train_validation(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    client.get(reverse("web:flow_start", kwargs={"mode": "train"}))
    no_seat = train_trip()
    del no_seat["seat_confirmed"]
    assert client.post(step("train", 1), no_seat).status_code == 422
    client.post(step("train", 1), train_trip())
    bad = client.post(
        step("train", 2), train_traveller(**{"form-0-car": "x", "form-0-doc_number": ""})
    )
    body = bad.content.decode()
    assert bad.status_code == 422
    assert "Voiture : un numéro entre 1 et 99" in body
    two = train_traveller(**{"form-TOTAL_FORMS": "2"})
    two.update(
        {
            "form-1-name": "Autre Voyageur",
            "form-1-doc_type": "passport",
            "form-1-doc_number": "P 123",
            "form-1-fare_type": "adult",
            "form-1-car": "3",
            "form-1-seat": "24",
            "form-1-bags": "0",
        }
    )
    assert "saisi deux fois" in client.post(step("train", 2), two).content.decode()


def test_the_train_agent_view_hides_cost_and_margin(agency_a: AgencyFixture) -> None:
    agent = login("alpha-agent")
    pay_url = run_train_flow(agent)
    assert "8 000" not in agent.get(pay_url).content.decode()
    with TenancyService.scope(agency_a.id):
        case = CasesService.list_cases(agency_a.agent)[0]
    assert case.cost_total_xaf is None
