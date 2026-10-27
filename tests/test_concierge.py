from io import StringIO
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command

from apps.concierge.access import actor_for
from apps.shared_kernel.money import format_xaf
from apps.shared_kernel.roles import Role
from tests.conftest import PASSWORD

HEADER = (
    "reference,customer_name,customer_phone,departure_date,kind,label,passenger_name,"
    "ticket_number,price_xaf,cost_xaf,paid_xaf,payment_method,payment_reference\n"
)
GOOD_ROWS = (
    "2026-0001,Marie Ndong,+237677123456,2026-11-20,air_ticket,DLA-CDG,NDONG/MARIE,"
    "0572345678901,500000,450000,200000,mobile_money,MP-123\n"
    "2026-0001,Marie Ndong,+237677123456,,free_service,Hôtel 2 nuits,,,180000,144000,,,\n"
    "2026-0002,Paul Eto,,,free_service,Transfert,,,25000,20000,25000,cash,\n"
)


@pytest.fixture(autouse=True)
def password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRAVORA_PASSWORD", PASSWORD)


def run(name: str, *args: str) -> str:
    out = StringIO()
    call_command(name, *args, stdout=out, stderr=StringIO())
    return out.getvalue()


@pytest.fixture
def agency(db: None) -> str:
    run("create_agency", "--name", "Alpha Voyages", "--slug", "alpha", "--manager", "alice")
    run("add_member", "--as", "alice", "--username", "bob")
    return "alice"


def write_csv(tmp_path: Path, rows: str = GOOD_ROWS) -> str:
    path = tmp_path / "dossiers.csv"
    path.write_text(HEADER + rows, encoding="utf-8")
    return str(path)


def test_create_agency_makes_a_manager_who_resolves_to_it(agency: str) -> None:
    with actor_for("alice") as actor:
        assert actor.role is Role.MANAGER
    with actor_for("bob") as actor:
        assert actor.role is Role.AGENT


def test_create_agency_refuses_duplicates_and_weak_passwords(
    agency: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(CommandError, match="déjà utilisé"):
        run("create_agency", "--name", "Autre", "--slug", "alpha", "--manager", "carol")
    with pytest.raises(CommandError, match="déjà utilisé"):
        run("create_agency", "--name", "Autre", "--slug", "autre", "--manager", "alice")
    monkeypatch.setenv("TRAVORA_PASSWORD", "123")
    with pytest.raises(CommandError):
        run("create_agency", "--name", "Autre", "--slug", "autre", "--manager", "carol")


def test_only_a_manager_adds_members(agency: str) -> None:
    with pytest.raises(CommandError, match="Seul un gérant"):
        run("add_member", "--as", "bob", "--username", "carol")
    with pytest.raises(CommandError, match="inconnu"):
        run("add_member", "--as", "personne", "--username", "carol")


def test_a_dry_run_imports_nothing(agency: str, tmp_path: Path) -> None:
    output = run("import_cases", "--as", agency, "--file", write_csv(tmp_path))

    assert "2 dossier(s), 3 ligne(s), 2 paiement(s)" in output
    assert "Essai à blanc" in output
    assert "0 dossier(s)" in run("show_balances", "--as", agency, "--all")


def test_a_committed_import_creates_cases_balances_and_margins(agency: str, tmp_path: Path) -> None:
    run("import_cases", "--as", agency, "--file", write_csv(tmp_path), "--commit")

    manager_view = run("show_balances", "--as", agency)
    assert "2026-0001" in manager_view
    assert format_xaf(480_000) in manager_view
    assert format_xaf(86_000) in manager_view
    assert "Marge reconnue" in manager_view
    assert "à encaisser : " + format_xaf(480_000) in manager_view

    agent_view = run("show_balances", "--as", "bob")
    assert format_xaf(480_000) in agent_view
    assert "Marge" not in agent_view
    assert format_xaf(86_000) not in agent_view


def test_the_import_can_be_replayed_without_duplicates(agency: str, tmp_path: Path) -> None:
    path = write_csv(tmp_path)
    run("import_cases", "--as", agency, "--file", path, "--commit")
    replay = run("import_cases", "--as", agency, "--file", path, "--commit")

    assert "0 dossier(s), 0 ligne(s), 0 paiement(s) ; 2 déjà présent(s)" in replay
    assert "à encaisser : " + format_xaf(480_000) in run("show_balances", "--as", agency)


def test_one_invalid_row_cancels_the_whole_import(agency: str, tmp_path: Path) -> None:
    rows = GOOD_ROWS + "2026-0003,Eve,,,free_service,Hôtel,,,abc,,,,\n"
    with pytest.raises(CommandError, match="aucun enregistrement"):
        run("import_cases", "--as", agency, "--file", write_csv(tmp_path, rows), "--commit")
    assert "0 dossier(s)" in run("show_balances", "--as", agency, "--all")


def test_the_csv_must_have_the_expected_shape(agency: str, tmp_path: Path) -> None:
    broken = tmp_path / "cassé.csv"
    broken.write_text("reference,customer_name\nX,Y\n", encoding="utf-8")
    with pytest.raises(CommandError, match="Colonnes manquantes"):
        run("import_cases", "--as", agency, "--file", str(broken))
    with pytest.raises(CommandError, match="référence"):
        run("import_cases", "--as", agency, "--file", write_csv(tmp_path, ",Sans,,,,,,,1,,,,\n"))
    with pytest.raises(CommandError):
        run("import_cases", "--as", agency, "--file", str(tmp_path / "absent.csv"))


def test_only_a_manager_imports(agency: str, tmp_path: Path) -> None:
    with pytest.raises(CommandError, match="Seul un gérant"):
        run("import_cases", "--as", "bob", "--file", write_csv(tmp_path))


def test_local_numbers_need_an_explicit_country_code(agency: str, tmp_path: Path) -> None:
    rows = "2026-0009,Local,0677123456,,free_service,Transfert,,,1000,800,,,\n"
    path = write_csv(tmp_path, rows)
    with pytest.raises(CommandError, match="aucun enregistrement"):
        run("import_cases", "--as", agency, "--file", path, "--commit")
    run(
        "import_cases",
        "--as",
        agency,
        "--file",
        path,
        "--commit",
        "--default-country-code",
        "+237",
    )
    assert "2026-0009" in run("show_balances", "--as", agency)
