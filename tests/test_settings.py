from datetime import date

from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.services.public import AccountsService
from apps.ledger.services.public import LedgerService
from apps.tenancy.services.public import TenancyService
from apps.web.reglages import _recent_months
from tests.conftest import PASSWORD, AgencyFixture


def login(username: str) -> Client:
    client = Client()
    assert client.login(username=username, password=PASSWORD)
    return client


def last_month_key() -> str:
    return _recent_months(None)[0].key


def test_the_settings_page_is_for_the_manager_only(agency_a: AgencyFixture) -> None:
    page = login("alpha-manager").get(reverse("web:settings"))
    assert page.status_code == 200
    body = page.content.decode()
    assert "Réglages" in body
    assert "alpha-agent" in body
    assert "Identité de l'agence" in body

    assert login("alpha-agent").get(reverse("web:settings")).status_code == 403


def test_the_navigation_link_is_hidden_from_agents(agency_a: AgencyFixture) -> None:
    link = reverse("web:settings")
    assert link in login("alpha-manager").get(reverse("web:today")).content.decode()
    assert link not in login("alpha-agent").get(reverse("web:today")).content.decode()


def test_an_anonymous_visitor_cannot_open_the_settings(db: None) -> None:
    response = Client().get(reverse("web:settings"))
    assert response.status_code == 302
    assert reverse("web:login") in response["Location"]


def test_settings_never_list_another_agencys_members(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    body = login("alpha-manager").get(reverse("web:settings")).content.decode()
    assert "bravo-agent" not in body


def test_the_manager_adds_an_agent_who_can_then_sign_in(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    response = client.post(
        reverse("web:member_add"),
        {"username": "nouveau.agent", "password": "Un-mot-de-passe-solide-77", "role": "agent"},
        follow=True,
    )
    assert response.status_code == 200
    assert "nouveau.agent peut maintenant se connecter." in response.content.decode()
    assert Client().login(username="nouveau.agent", password="Un-mot-de-passe-solide-77")
    with TenancyService.scope(agency_a.id):
        names = [member.username for member in AccountsService.team(agency_a.manager)]
    assert "nouveau.agent" in names


def test_an_agent_cannot_add_members(agency_a: AgencyFixture) -> None:
    response = login("alpha-agent").post(
        reverse("web:member_add"),
        {"username": "intrus", "password": "Un-mot-de-passe-solide-77", "role": "manager"},
    )
    assert response.status_code == 403
    assert AccountsService.find_user_id("intrus") is None


def test_adding_a_member_rejects_a_taken_username_and_a_weak_password(
    agency_a: AgencyFixture,
) -> None:
    client = login("alpha-manager")
    taken = client.post(
        reverse("web:member_add"),
        {"username": "alpha-agent", "password": "Un-mot-de-passe-solide-77", "role": "agent"},
    )
    assert taken.status_code == 400
    assert "déjà pris" in taken.content.decode()

    weak = client.post(
        reverse("web:member_add"),
        {"username": "faible", "password": "12345678", "role": "agent"},
    )
    assert weak.status_code == 400
    assert AccountsService.find_user_id("faible") is None

    spaces = client.post(
        reverse("web:member_add"),
        {"username": "avec espace", "password": "Un-mot-de-passe-solide-77", "role": "agent"},
    )
    assert spaces.status_code == 400
    assert "sans espace" in spaces.content.decode()


def test_closing_a_period_needs_the_typed_confirmation(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    key = last_month_key()
    page = client.get(reverse("web:period_close"), {"mois": key})
    assert page.status_code == 200
    assert "Cette action est définitive" in page.content.decode()

    refused = client.post(reverse("web:period_close"), {"month": key, "confirm": "oui"})
    assert refused.status_code == 400
    with TenancyService.scope(agency_a.id):
        assert LedgerService.closed_until(agency_a.manager) is None

    done = client.post(
        reverse("web:period_close"), {"month": key, "confirm": "clôturer"}, follow=True
    )
    assert "La comptabilité est close jusqu'au" in done.content.decode()
    with TenancyService.scope(agency_a.id):
        closed = LedgerService.closed_until(agency_a.manager)
    assert closed is not None
    assert closed < timezone.localdate()


def test_closing_twice_is_explained_not_crashed(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    key = last_month_key()
    client.post(reverse("web:period_close"), {"month": key, "confirm": "CLÔTURER"})
    again = client.post(
        reverse("web:period_close"), {"month": key, "confirm": "CLÔTURER"}, follow=True
    )
    assert "déjà clôturée" in again.content.decode()


def test_an_unknown_month_is_refused(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    response = client.get(reverse("web:period_close"), {"mois": "2999-01"}, follow=True)
    assert "Choisissez un des mois proposés." in response.content.decode()
    future = client.post(reverse("web:period_close"), {"month": "garbage", "confirm": "CLÔTURER"})
    assert future.status_code == 302


def test_an_agent_cannot_close_a_period(agency_a: AgencyFixture) -> None:
    key = last_month_key()
    client = login("alpha-agent")
    assert client.get(reverse("web:period_close"), {"mois": key}).status_code == 403
    response = client.post(reverse("web:period_close"), {"month": key, "confirm": "CLÔTURER"})
    assert response.status_code == 403


def test_closed_months_are_marked_on_the_settings_page(agency_a: AgencyFixture) -> None:
    client = login("alpha-manager")
    key = last_month_key()
    client.post(reverse("web:period_close"), {"month": key, "confirm": "CLÔTURER"})
    body = client.get(reverse("web:settings")).content.decode()
    assert 'badge-success">✓ ' in body


def test_recent_months_run_from_the_latest_finished_month(db: None) -> None:
    rows = _recent_months(date(2000, 1, 1))
    assert len(rows) == 12
    assert rows[0].last_day < timezone.localdate()
    assert rows[0].last_day > rows[1].last_day
    assert not any(row.closed for row in rows)
    assert all(row.closed for row in _recent_months(timezone.localdate()))
