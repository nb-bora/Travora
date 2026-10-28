import re
from datetime import date, timedelta

from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.cases.constants import LineKind
from apps.cases.services.public import CasesService
from apps.crm.services.public import CrmService
from apps.dashboard.services.public import DashboardService
from apps.payments.services.public import PaymentsService
from apps.tenancy.services.public import TenancyService
from apps.web.insights import _safe
from tests.conftest import AgencyFixture
from tests.test_web import add_line_via_web, create_case_via_web, login


def sell(manager: Client, *, name: str = "Marie Ndong", reference: str = "MP-1") -> str:
    """Un dossier, une ligne émise de 500 000 (coût 450 000) et un encaissement de 200 000."""
    url = create_case_via_web(manager, name)
    add_line_via_web(manager, url)
    line_id = (
        manager.get(url)
        .content.decode()
        .replace(" ", " ")
        .replace(" ", " ")
        .split("/lignes/")[1]
        .split("/")[0]
    )
    assert manager.post(f"{url}lignes/{line_id}/emettre/").status_code == 302
    payment = {
        "method": "mobile_money",
        "amount_xaf": "200000",
        "reference": reference,
        "received_on": str(timezone.localdate()),
        "idempotency_key": f"key-{reference}",
    }
    assert manager.post(f"{url}encaissements/", payment).status_code == 302
    return url


def customer_url(client: Client) -> str:
    page = (
        client.get(reverse("web:customer_list"))
        .content.decode()
        .replace(" ", " ")
        .replace(" ", " ")
    )
    match = re.search(r'href="(/clients/[0-9a-f-]{36}/)"', page)
    assert match
    return match.group(1)


def test_the_customer_sheet_shows_cases_payments_and_balance(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    sell(manager)
    page = manager.get(customer_url(manager)).content.decode().replace(" ", " ").replace(" ", " ")
    for expected in ("Marie Ndong", "+237677123456", "Mobile Money", "MP-1", "À venir"):
        assert expected in page
    assert "300 000" in page  # solde dû
    assert "200 000" in page  # encaissé


def test_the_customer_sheet_hides_cost_and_margin_from_an_agent(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    sell(manager)
    page = (
        login("alpha-agent")
        .get(customer_url(manager))
        .content.decode()
        .replace(" ", " ")
        .replace(" ", " ")
    )
    assert "Marie Ndong" in page
    assert "450 000" not in page
    assert "50 000" not in page


def test_another_agency_cannot_open_a_customer_sheet(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    manager = login("alpha-manager")
    sell(manager)
    url = customer_url(manager)
    assert login("bravo-manager").get(url).status_code == 404
    assert login("bravo-manager").get(url + "export/").status_code == 404


def test_the_customer_export_is_a_csv_of_the_sheet(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    sell(manager)
    response = manager.get(customer_url(manager) + "export/")
    assert response["Content-Type"].startswith("text/csv")
    assert "attachment" in response["Content-Disposition"]
    body = response.content.decode("utf-8")
    assert "Marie Ndong" in body
    assert "Encaissement" in body
    assert "MP-1" in body


def test_the_unknown_customer_is_a_404(agency_a: AgencyFixture) -> None:
    unknown = reverse("web:customer_detail", args=["00000000-0000-0000-0000-000000000001"])
    assert login("alpha-manager").get(unknown).status_code == 404


def test_the_report_adds_up_sales_and_collections(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    sell(manager)
    page = manager.get(reverse("web:report")).content.decode().replace(" ", " ").replace(" ", " ")
    for expected in ("Billet d&#x27;avion", "Billet d'avion", "Mobile Money"):
        if expected in page:
            break
    else:
        raise AssertionError("mode de vente absent")
    assert "500 000" in page
    assert "200 000" in page
    assert "Marge sur ventes" in page
    assert "50 000" in page


def test_the_report_never_shows_the_margin_to_an_agent(agency_a: AgencyFixture) -> None:
    sell(login("alpha-manager"))
    agent = login("alpha-agent")
    page = agent.get(reverse("web:report")).content.decode().replace(" ", " ").replace(" ", " ")
    assert "500 000" in page
    assert "Marge" not in page
    assert "450 000" not in page
    csv_body = agent.get(reverse("web:report_export")).content.decode("utf-8")
    assert "Marge" not in csv_body
    assert "Coût" not in csv_body
    assert "450000" not in csv_body


def test_the_manager_report_export_has_cost_and_margin(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    sell(manager)
    body = manager.get(reverse("web:report_export")).content.decode("utf-8")
    assert "Marge FCFA" in body
    assert "450000" in body
    assert "50000" in body


def test_the_report_period_presets_and_validation(agency_a: AgencyFixture) -> None:
    manager = login("alpha-manager")
    sell(manager)
    for key in ("7j", "30j", "mois", "annee", "n-importe-quoi"):
        assert manager.get(reverse("web:report"), {"periode": key}).status_code == 200
    today = timezone.localdate()
    old = str(today - timedelta(days=400))
    empty = (
        manager.get(reverse("web:report"), {"du": old, "au": old})
        .content.decode()
        .replace(" ", " ")
        .replace(" ", " ")
    )
    assert "Aucune vente émise sur cette période." in empty
    assert "Aucun encaissement sur cette période." in empty
    for params, message in (
        ({"du": "pas-une-date", "au": str(today)}, "Dates invalides"),
        ({"du": str(today), "au": str(today - timedelta(days=1))}, "suit la date de fin"),
        ({"du": "2000-01-01", "au": str(today)}, "2 ans au plus"),
    ):
        assert message in manager.get(reverse("web:report"), params).content.decode().replace(
            " ", " "
        ).replace(" ", " ")


def test_the_pages_require_a_login(db: None) -> None:
    for name in ("web:report", "web:report_export"):
        assert Client().get(reverse(name)).status_code == 302


def test_csv_cells_that_look_like_formulas_are_neutralised() -> None:
    assert _safe("=1+1") == "'=1+1"
    assert _safe("@cmd") == "'@cmd"
    assert _safe("Douala") == "Douala"


def test_the_sales_report_facade_hides_costs_from_an_agent(agency_a: AgencyFixture) -> None:
    with TenancyService.scope(agency_a.id):
        customer = CrmService.find_or_create_customer(
            agency_a.manager, name="Paul Etoa", phone="+237677000111"
        )
        case = CasesService.create_case(
            agency_a.manager, customer_id=customer.id, departure_date=None
        )
        line = CasesService.add_line(
            agency_a.manager,
            case_id=case,
            kind=LineKind.FREE_SERVICE,
            label="Visa",
            price_xaf=40_000,
            cost_xaf=30_000,
        )
        today = date.today()
        CasesService.issue_line(agency_a.manager, line_id=line.id, issued_on=today)

        manager_view = DashboardService.sales_report(agency_a.manager, start=today, end=today)
        agent_view = DashboardService.sales_report(agency_a.agent, start=today, end=today)
        assert manager_view.margin_xaf == 10_000
        assert manager_view.by_kind[0].cost_xaf == 30_000
        assert agent_view.margin_xaf is None
        assert agent_view.by_kind[0].cost_xaf is None
        assert agent_view.by_kind[0].margin_xaf is None
        assert agent_view.revenue_xaf == 40_000
        assert PaymentsService.totals_by_method(agency_a.agent, start=today, end=today) == []
