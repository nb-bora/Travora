from django.test import Client
from django.urls import reverse

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
