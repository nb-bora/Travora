import re

from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.cases.constants import LineKind
from apps.cases.services.public import CasesService
from apps.crm.services.public import CrmService
from apps.tenancy.services.public import TenancyService
from tests.conftest import PASSWORD, AgencyFixture


def login(username: str) -> Client:
    client = Client()
    assert client.login(username=username, password=PASSWORD)
    return client


def test_an_anonymous_visitor_is_sent_to_the_login_page(db: None) -> None:
    response = Client().get(reverse("web:today"))
    assert response.status_code == 302
    assert response["Location"].startswith(reverse("web:login"))


def test_the_login_page_renders_and_accepts_valid_credentials(agency_a: AgencyFixture) -> None:
    client = Client()
    assert client.get(reverse("web:login")).status_code == 200
    response = client.post(
        reverse("web:login"), {"username": "alpha-manager", "password": PASSWORD}
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("web:today")


def test_a_wrong_password_shows_a_clear_error(agency_a: AgencyFixture) -> None:
    response = Client().post(reverse("web:login"), {"username": "alpha-manager", "password": "x"})
    assert response.status_code == 200
    assert "Identifiant ou mot de passe incorrect" in response.content.decode()


def test_the_manager_sees_the_margin_and_the_agent_never_does(agency_a: AgencyFixture) -> None:
    manager_page = login("alpha-manager").get(reverse("web:today"))
    agent_page = login("alpha-agent").get(reverse("web:today"))

    assert manager_page.status_code == agent_page.status_code == 200
    assert "Marge encaissée" in manager_page.content.decode()
    assert "Marge" not in agent_page.content.decode()


def test_a_page_only_shows_the_data_of_the_users_own_agency(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    with TenancyService.scope(agency_a.id):
        customer = CrmService.find_or_create_customer(agency_a.agent, name="Client", phone="")
        case_id = CasesService.create_case(agency_a.agent, customer_id=customer.id)
        CasesService.add_line(
            agency_a.agent, case_id=case_id, kind=LineKind.FREE_SERVICE, label="X", price_xaf=1
        )

    page_a = login("alpha-agent").get(reverse("web:today")).content.decode()
    page_b = login("bravo-agent").get(reverse("web:today")).content.decode()

    assert 'stat-value">1<' in page_a
    assert 'stat-value">0<' in page_b


def test_a_suspended_agency_gets_an_explicit_page_and_loses_nothing(
    agency_a: AgencyFixture,
) -> None:
    client = login("alpha-manager")
    TenancyService.set_agency_active(user_id=agency_a.manager.user_id, active=False)

    response = client.get(reverse("web:today"))

    assert response.status_code == 403
    assert "Accès indisponible" in response.content.decode()
    TenancyService.set_agency_active(user_id=agency_a.manager.user_id, active=True)
    assert client.get(reverse("web:today")).status_code == 200


def test_logout_requires_a_post(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    assert client.get(reverse("web:logout")).status_code == 405
    assert client.post(reverse("web:logout")).status_code == 302
    assert client.get(reverse("web:today")).status_code == 302


def create_case_via_web(client: Client, name: str = "Marie Ndong") -> str:
    response = client.post(
        reverse("web:case_create"),
        {"customer_name": name, "customer_phone": "+237677123456", "departure_date": ""},
    )
    assert response.status_code == 302
    return str(response["Location"])


def add_line_via_web(client: Client, url: str, **overrides: str) -> None:
    data = {
        "kind": "air_ticket",
        "label": "DLA-CDG",
        "passenger_name": "NDONG/MARIE",
        "carrier": "Air France",
        "ticket_number": "057-2345678901",
        "price_xaf": "500000",
        "cost_xaf": "450000",
    } | overrides
    assert client.post(f"{url}lignes/", data).status_code == 302


def test_a_full_case_flow_through_the_web_ui(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    url = create_case_via_web(manager)
    add_line_via_web(manager, url)

    page = manager.get(url).content.decode()
    for expected in ("DLA-CDG", "0572345678901", "Air France", "Brouillon"):
        assert expected in page

    line_id = page.split("/lignes/")[1].split("/")[0]
    assert manager.post(f"{url}lignes/{line_id}/emettre/").status_code == 302
    page = manager.get(url).content.decode()
    assert "Émise" in page
    assert "500 000" in page

    payment = {
        "method": "mobile_money",
        "amount_xaf": "500000",
        "reference": "MP-1",
        "received_on": str(timezone.localdate()),
        "idempotency_key": "abc123",
    }
    assert manager.post(f"{url}encaissements/", payment).status_code == 302
    assert manager.post(f"{url}encaissements/", payment).status_code == 302  # double clic
    page = manager.get(url).content.decode()
    assert page.count("MP-1") == 1
    assert "Soldé" in page

    assert manager.post(f"{url}clore/").status_code == 302
    page = manager.get(url).content.decode()
    assert "Clos" in page
    assert "Rouvrir le dossier" in page


def test_an_agent_never_sees_cost_or_margin_in_the_case_pages(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    url = create_case_via_web(manager)
    add_line_via_web(manager, url, cost_xaf="450000")

    agent = login("alpha-agent")
    detail = agent.get(url).content.decode()
    listing = agent.get(reverse("web:case_list")).content.decode()

    for page in (detail, listing):
        assert "450 000" not in page
        assert "Marge" not in page
    assert "Coût" in detail  # le champ de saisie reste, jamais la valeur
    assert "Marge prévue" in manager.get(url).content.decode()


def test_domain_errors_are_explained_and_nothing_is_lost(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    url = create_case_via_web(manager)
    add_line_via_web(manager, url)
    follow = manager.post(
        f"{url}lignes/",
        {"kind": "free_service", "label": "Hôtel", "ticket_number": "123", "price_xaf": "10"},
        follow=True,
    )
    assert "Seul un titre de transport porte un numéro de billet" in follow.content.decode()

    duplicate = manager.post(
        f"{url}lignes/",
        {"kind": "air_ticket", "label": "X", "ticket_number": "0572345678901", "price_xaf": "1"},
        follow=True,
    )
    assert "déjà utilisé" in duplicate.content.decode()
    assert duplicate.status_code == 200

    page = manager.get(url).content.decode()
    line_id = page.split("/lignes/")[1].split("/")[0]
    manager.post(f"{url}lignes/{line_id}/emettre/")
    closed = manager.post(f"{url}clore/", follow=True)
    assert "Solde restant" in closed.content.decode()


def test_an_invalid_form_is_redisplayed_with_errors(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    url = create_case_via_web(manager)
    response = manager.post(f"{url}lignes/", {"kind": "air_ticket", "label": "", "price_xaf": "-5"})
    assert response.status_code == 422
    assert "field-error" in response.content.decode()


def test_an_invalid_phone_number_is_explained(agency_a: AgencyFixture) -> None:
    response = login("alpha-manager").post(
        reverse("web:case_create"),
        {"customer_name": "X", "customer_phone": "12", "departure_date": ""},
    )
    assert response.status_code == 200
    assert "Numéro invalide" in response.content.decode()


def test_another_agency_cannot_open_a_case_by_its_identifier(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    url = create_case_via_web(login("alpha-manager"))
    intruder = login("bravo-manager")
    assert intruder.get(url).status_code == 404
    assert intruder.post(f"{url}clore/").status_code in (302, 404)
    assert "Marie Ndong" not in intruder.get(reverse("web:case_list")).content.decode()


def test_only_the_manager_voids_a_line_and_reopens_a_case(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    url = create_case_via_web(manager)
    add_line_via_web(manager, url)
    page = manager.get(url).content.decode()
    line_id = page.split("/lignes/")[1].split("/")[0]
    manager.post(f"{url}lignes/{line_id}/emettre/")

    agent = login("alpha-agent")
    follow = agent.post(f"{url}lignes/{line_id}/annuler/", follow=True)
    assert "réservée au gérant" in follow.content.decode()
    assert "Annuler" not in agent.get(url).content.decode().split("Encaissements")[0]


def test_the_list_filters_by_state_and_searches(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    create_case_via_web(manager, "Marie Ndong")
    listing = reverse("web:case_list")
    assert "Marie Ndong" in manager.get(listing).content.decode()
    assert "Marie Ndong" not in manager.get(listing, {"etat": "clos"}).content.decode()
    assert "Marie Ndong" in manager.get(listing, {"q": "ndong"}).content.decode()
    assert "Aucun résultat" in manager.get(listing, {"q": "zzz"}).content.decode()


def test_state_changing_actions_refuse_get_requests(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    url = create_case_via_web(manager)
    assert manager.get(f"{url}clore/").status_code == 405
    assert manager.get(f"{url}encaissements/").status_code == 405


def quick_data(**overrides: str) -> dict[str, str]:
    return {
        "kind": "air_ticket",
        "origin": "DLA",
        "destination": "CDG",
        "departure_date": "",
        "customer_name": "Marie Ndong",
        "customer_phone": "+237677123456",
        "passenger_name": "NDONG/MARIE",
        "carrier": "Air France",
        "ticket_number": "057-2345678901",
        "price_xaf": "520000",
        "cost_xaf": "470000",
    } | overrides


def test_the_quick_entry_creates_customer_case_and_line_in_one_gesture(
    agency_a: AgencyFixture,
) -> None:
    agent = login("alpha-agent")
    response = agent.post(reverse("web:quick_entry"), quick_data())
    assert response.status_code == 302

    page = agent.get(response["Location"]).content.decode()
    for expected in ("Marie Ndong", "DLA → CDG", "0572345678901", "Air France"):
        assert expected in page
    assert "470 000" not in page


def test_the_quick_entry_supports_every_mode_and_free_services(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    for kind, ref in (("bus_ticket", "KB-1"), ("train_ticket", "TR-2"), ("boat_ticket", "BT-3")):
        response = client.post(
            reverse("web:quick_entry"),
            quick_data(kind=kind, ticket_number=ref, customer_phone=""),
        )
        assert response.status_code == 302
    service = client.post(
        reverse("web:quick_entry"),
        {
            "kind": "free_service",
            "service_label": "Visa Schengen",
            "customer_name": "Paul Eto",
            "price_xaf": "80000",
        },
    )
    assert service.status_code == 302
    assert "Visa Schengen" in client.get(service["Location"]).content.decode()


def test_the_quick_entry_validates_by_mode_and_keeps_the_input(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    response = client.post(reverse("web:quick_entry"), quick_data(origin="", customer_name=""))
    body = response.content.decode()
    assert response.status_code == 422
    assert body.count("field-error") >= 2
    assert 'value="CDG"' in body  # la saisie n'est pas perdue

    no_label = client.post(
        reverse("web:quick_entry"),
        {"kind": "free_service", "customer_name": "X", "price_xaf": "5"},
    )
    assert no_label.status_code == 422
    assert "Décrivez la prestation" in no_label.content.decode()


def test_a_failed_quick_entry_leaves_nothing_behind(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    client.post(reverse("web:quick_entry"), quick_data())
    again = client.post(
        reverse("web:quick_entry"), quick_data(customer_name="Autre Client", customer_phone="")
    )  # même numéro de billet : refusé
    assert again.status_code == 422
    listing = client.get(reverse("web:case_list")).content.decode()
    assert "Autre Client" not in listing
    assert listing.count("Marie Ndong") == 1


def test_the_list_tabs_count_and_filter_unpaid_and_upcoming_cases(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    soon = str(timezone.localdate() + timezone.timedelta(days=3))
    created = manager.post(
        reverse("web:quick_entry"),
        quick_data(departure_date=soon, ticket_number="", customer_phone=""),
    )
    url = created["Location"]
    line_id = manager.get(url).content.decode().split("/lignes/")[1].split("/")[0]
    manager.post(f"{url}lignes/{line_id}/emettre/")

    listing = reverse("web:case_list")
    unpaid = manager.get(listing, {"etat": "impayes"}).content.decode()
    upcoming = manager.get(listing, {"etat": "depart"}).content.decode()
    closed = manager.get(listing, {"etat": "clos"}).content.decode()

    assert "Marie Ndong" in unpaid
    assert "Marie Ndong" in upcoming
    assert "Marie Ndong" not in closed
    assert 'Impayés <span class="count">1</span>' in unpaid
    assert 'Clos <span class="count">0</span>' in unpaid


def test_the_shell_shows_the_agency_and_the_role(agency_a: AgencyFixture) -> None:
    page = login("alpha-agent").get(reverse("web:today")).content.decode()
    assert "Alpha" in page
    assert ">Agent<" in page


def test_every_page_ships_a_strict_content_security_policy(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    for url in (reverse("web:today"), reverse("web:case_list"), reverse("web:case_create")):
        response = client.get(url)
        policy = response["Content-Security-Policy"]
        assert "default-src 'none'" in policy
        assert "script-src 'self'" in policy
        assert "frame-ancestors 'none'" in policy
        assert "unsafe-inline" not in policy
        assert response["Referrer-Policy"] == "same-origin"


def test_templates_use_no_inline_style_or_script(agency_a: AgencyFixture) -> None:
    """La politique interdit les styles et scripts en ligne : le HTML ne doit pas en contenir."""
    manager = login("alpha-manager")
    url = create_case_via_web(manager)
    add_line_via_web(manager, url)
    pages = [
        Client().get(reverse("web:login")),
        manager.get(reverse("web:today")),
        manager.get(reverse("web:case_list")),
        manager.get(url),
        manager.get(reverse("web:case_create")),
    ]
    for response in pages:
        body = response.content.decode()
        assert " style=" not in body
        assert "<script>" not in body
        assert " onclick=" not in body.lower()


ETICKET = (
    "Passenger : NDONG/MARIE MS\nTicket number : 057-2345678901\nBooking ref : K7QX2B\n"
    "Airline : AIR FRANCE\nDLA -> CDG\nDeparture : 20 NOV 2026 09:15\nFare : XAF 520000\n"
)


def test_pasting_a_ticket_prefills_the_quick_entry_and_saves_nothing(
    agency_a: AgencyFixture,
) -> None:
    manager = login("alpha-manager")
    response = manager.post(reverse("web:paste_booking"), {"text": ETICKET})
    page = response.content.decode()

    assert response.status_code == 200
    assert "Reconnu dans le texte" in page
    for expected in ("0572345678901", "NDONG/MARIE MS", "DLA → CDG", "Air France", "K7QX2B"):
        assert expected in page
    assert 'value="Marie Ndong"' in page
    assert 'value="520000"' in page
    assert (
        "Marie Ndong"
        not in manager.get(reverse("web:case_list"), {"etat": "tous"}).content.decode()
    )


def test_pasting_ordinary_text_says_nothing_was_recognised(agency_a: AgencyFixture) -> None:
    response = login("alpha-agent").post(
        reverse("web:paste_booking"), {"text": "Bonjour, merci de me rappeler demain."}
    )
    assert response.status_code == 200
    assert "Aucun billet reconnu" in response.content.decode()


def test_the_pasted_text_is_escaped_and_bounded(agency_a: AgencyFixture) -> None:
    hostile = "<script>alert(1)</script>" + "x" * 30_000
    page = login("alpha-manager").post(reverse("web:paste_booking"), {"text": hostile})
    body = page.content.decode()
    assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;" in body
    assert body.count("x" * 100) < 250  # tronqué à 20 000 caractères


def test_pasting_requires_a_post_and_a_login(agency_a: AgencyFixture) -> None:
    assert login("alpha-manager").get(reverse("web:paste_booking")).status_code == 405
    assert Client().post(reverse("web:paste_booking"), {"text": ETICKET}).status_code == 302


def test_the_client_list_shows_balances_and_a_whatsapp_reminder(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    url = create_case_via_web(manager)
    add_line_via_web(manager, url)
    line_id = manager.get(url).content.decode().split("/lignes/")[1].split("/")[0]
    manager.post(f"{url}lignes/{line_id}/emettre/")

    page = manager.get(reverse("web:customer_list")).content.decode()

    assert "Marie Ndong" in page
    assert "500 000" in page
    assert "https://wa.me/237677123456?text=" in page
    assert 'rel="noopener noreferrer"' in page
    assert "Marie%20Ndong" in page or "Marie Ndong" in page
    assert (
        "Marie Ndong"
        not in manager.get(reverse("web:customer_list"), {"q": "zzz"}).content.decode()
    )


def test_clients_of_another_agency_never_appear(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    create_case_via_web(login("alpha-manager"))
    assert (
        "Marie Ndong"
        not in login("bravo-manager").get(reverse("web:customer_list")).content.decode()
    )


def test_only_the_manager_voids_a_payment(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    url = create_case_via_web(manager)
    add_line_via_web(manager, url)
    line_id = manager.get(url).content.decode().split("/lignes/")[1].split("/")[0]
    manager.post(f"{url}lignes/{line_id}/emettre/")
    payment = {
        "method": "mobile_money",
        "amount_xaf": "100000",
        "reference": "MP-9",
        "received_on": str(timezone.localdate()),
        "idempotency_key": "void1",
    }
    manager.post(f"{url}encaissements/", payment)
    page = manager.get(url).content.decode()
    found = re.search(r"/encaissements/([0-9a-f-]{36})/annuler/", page)
    assert found is not None
    payment_id = found.group(1)

    agent = login("alpha-agent")
    refused = agent.post(f"{url}encaissements/{payment_id}/annuler/", follow=True)
    assert "réservée au gérant" in refused.content.decode()

    manager.post(f"{url}encaissements/{payment_id}/annuler/")
    assert "Annulé" in manager.get(url).content.decode()


def test_a_pasted_departure_date_reaches_the_date_field_in_iso_format(
    agency_a: AgencyFixture,
) -> None:
    page = login("alpha-manager").post(reverse("web:paste_booking"), {"text": ETICKET}).content
    assert 'value="2026-11-20"' in page.decode()


def hidden_value(page: str, name: str) -> str:
    found = re.search(rf'name="{name}"[^>]*value="([^"]*)"', page)
    assert found is not None, name
    return found.group(1)


def test_a_payment_with_the_form_generated_key_is_recorded(agency_a: AgencyFixture) -> None:
    """Régression : la clé générée par le formulaire dépassait la colonne et donnait un 500."""
    manager = login("alpha-manager")
    url = create_case_via_web(manager)
    add_line_via_web(manager, url)
    line_id = manager.get(url).content.decode().split("/lignes/")[1].split("/")[0]
    manager.post(f"{url}lignes/{line_id}/emettre/")

    page = manager.get(url).content.decode()
    key = hidden_value(page, "idempotency_key")
    response = manager.post(
        f"{url}encaissements/",
        {
            "method": "cash",
            "amount_xaf": "100000",
            "reference": "",
            "received_on": str(timezone.localdate()),
            "idempotency_key": key,
        },
    )
    assert response.status_code == 302
    assert "Encaissement enregistré" in manager.get(url).content.decode()


def test_a_double_submit_of_the_quick_entry_creates_one_case(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    page = manager.get(reverse("web:today")).content.decode()
    token = hidden_value(page, "submission_id")
    data = quick_data(ticket_number="", customer_phone="") | {"submission_id": token}

    first = manager.post(reverse("web:quick_entry"), data)
    second = manager.post(reverse("web:quick_entry"), data)

    assert first.status_code == second.status_code == 302
    assert first["Location"] == second["Location"]
    listing = manager.get(reverse("web:case_list"), {"etat": "tous"}).content.decode()
    assert listing.count("Marie Ndong") == 1


def test_a_domain_refusal_keeps_the_quick_entry_input(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    manager.post(reverse("web:quick_entry"), quick_data())
    again = manager.post(
        reverse("web:quick_entry"), quick_data(customer_name="Autre Client", customer_phone="")
    )  # même numéro de billet
    body = again.content.decode()
    assert again.status_code == 422
    assert 'value="Autre Client"' in body
    assert "déjà utilisée" in body


def test_a_service_ignores_the_ticket_fields_that_are_hidden(agency_a: AgencyFixture) -> None:
    response = login("alpha-manager").post(
        reverse("web:quick_entry"),
        {
            "kind": "free_service",
            "service_label": "Visa",
            "customer_name": "Paul Eto",
            "price_xaf": "80000",
            "ticket_number": "057 2345678901",  # champ masqué mais envoyé
            "carrier": "Air France",
        },
    )
    assert response.status_code == 302


def test_a_line_of_another_case_cannot_be_acted_on_through_this_case(
    agency_a: AgencyFixture,
) -> None:
    manager = login("alpha-manager")
    first = create_case_via_web(manager, "Premier Client")
    second = create_case_via_web(manager, "Second Client")
    add_line_via_web(manager, first)
    line_id = manager.get(first).content.decode().split("/lignes/")[1].split("/")[0]
    assert manager.post(f"{second}lignes/{line_id}/emettre/").status_code == 404


def test_a_post_after_the_session_expired_restarts_from_the_home_page(db: None) -> None:
    response = Client().post("/dossiers/00000000-0000-0000-0000-000000000001/clore/")
    assert response.status_code == 302
    assert response["Location"] == "/connexion/?next=/"


def test_authenticated_pages_are_never_cached(agency_a: AgencyFixture) -> None:
    response = login("alpha-manager").get(reverse("web:today"))
    cache_control = response["Cache-Control"]
    assert "no-store" in cache_control
    assert "private" in cache_control


def bad_login(client: Client, username: str = "alpha-manager") -> str:
    response = client.post(reverse("web:login"), {"username": username, "password": "mauvais"})
    return response.content.decode()


def test_too_many_wrong_passwords_lock_the_account_for_a_while(agency_a: AgencyFixture) -> None:
    client = Client()
    for _ in range(5):
        assert "incorrect" in bad_login(client)
    locked = client.post(
        reverse("web:login"), {"username": "alpha-manager", "password": PASSWORD}
    ).content.decode()
    assert "Trop de tentatives" in locked  # même avec le bon mot de passe

    # un autre identifiant n'est pas touché
    assert (
        Client()
        .post(reverse("web:login"), {"username": "alpha-agent", "password": PASSWORD})
        .status_code
        == 302
    )


def test_a_successful_login_clears_the_failures(agency_a: AgencyFixture) -> None:
    client = Client()
    for _ in range(4):
        bad_login(client)
    assert (
        client.post(
            reverse("web:login"), {"username": "alpha-manager", "password": PASSWORD}
        ).status_code
        == 302
    )
    client.post(reverse("web:logout"))
    for _ in range(4):
        assert "incorrect" in bad_login(client)  # le compteur est reparti de zéro


def test_the_lock_expires_after_the_window(agency_a: AgencyFixture) -> None:
    from datetime import timedelta

    from apps.accounts.models import LoginFailure

    client = Client()
    for _ in range(5):
        bad_login(client)
    LoginFailure.objects.update(created_at=timezone.now() - timedelta(minutes=16))
    assert (
        client.post(
            reverse("web:login"), {"username": "alpha-manager", "password": PASSWORD}
        ).status_code
        == 302
    )


def test_a_logged_in_user_opening_the_login_page_goes_home_whatever_next_says(
    agency_a: AgencyFixture,
) -> None:
    client = login("alpha-manager")
    response = client.get(reverse("web:login") + "?next=/connexion/")
    assert response.status_code == 302
    assert response["Location"] == reverse("web:today")


def test_browser_features_are_cut_off_by_a_permissions_policy(db: None) -> None:
    response = Client().get(reverse("web:login"))
    assert "camera=()" in response["Permissions-Policy"]
    assert "geolocation=()" in response["Permissions-Policy"]


def test_the_login_page_uses_the_outlined_fields_and_its_own_assets(db: None) -> None:
    page = Client().get(reverse("web:login")).content.decode()
    assert "ofield" in page
    assert "web/login.css" in page
    assert "web/login.js" in page
    assert "<script>" not in page  # CSP : pas de script en ligne
