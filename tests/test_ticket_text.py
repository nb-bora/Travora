from datetime import date

from apps.cases.services.public import CasesService
from apps.cases.ticket_text import display_name

TODAY = date(2026, 10, 27)

ETICKET = """ELECTRONIC TICKET RECEIPT
Passenger : NDONG/MARIE MS
Ticket number : 057-2345678901
Booking ref : K7QX2B
Airline : AIR FRANCE
From : DOUALA (DLA)   To : PARIS CDG (CDG)
Departure : 20 NOV 2026 09:15
Fare : XAF 520000
Issued : 03 NOV 2026
"""


def parse(text: str):
    return CasesService.propose_booking(text, today=TODAY)


def test_a_complete_eticket_is_read_field_by_field() -> None:
    proposal = parse(ETICKET)

    assert proposal.ticket_numbers == ("0572345678901",)
    assert proposal.passengers == ("NDONG/MARIE MS",)
    assert proposal.customer_name == "Marie Ndong"
    assert (proposal.origin, proposal.destination) == ("DLA", "CDG")
    assert proposal.departure_date == date(2026, 11, 20)
    assert proposal.carrier == "Air France"
    assert proposal.booking_reference == "K7QX2B"
    assert proposal.price_xaf == 520_000
    assert proposal.warnings == ()
    assert proposal.recognised


def test_the_issue_date_is_never_taken_for_the_departure_date() -> None:
    text = "Issued : 03 NOV 2026\nDLA -> CDG\nDeparture 20NOV 09:15"
    proposal = parse(text)
    assert proposal.departure_date == date(2026, 11, 20)


def test_a_date_without_a_year_takes_the_next_occurrence_and_says_so() -> None:
    proposal = parse("DLA-CDG 15JAN 08:00 ticket 057 2345678901")
    assert proposal.departure_date == date(2027, 1, 15)
    assert any("année" in warning for warning in proposal.warnings)


def test_numeric_and_iso_dates_are_understood() -> None:
    assert parse("Départ le 20/11/2026").departure_date == date(2026, 11, 20)
    assert parse("departure 2026-12-05").departure_date == date(2026, 12, 5)


def test_an_impossible_date_is_not_invented() -> None:
    assert parse("Départ le 31/02/2026 057 2345678901").departure_date is None


def test_prices_are_read_before_or_after_the_currency() -> None:
    assert parse("Total 520 000 FCFA").price_xaf == 520_000
    assert parse("Prix : FCFA 1 250 000").price_xaf == 1_250_000
    assert parse("Prix : 80000 XAF").price_xaf == 80_000
    assert parse("Aucun montant ici 057 2345678901").price_xaf is None


def test_several_tickets_and_passengers_are_flagged_not_guessed() -> None:
    text = (
        "NDONG/MARIE MS 057-2345678901\nNDONG/JEAN MR 057-2345678902\n"
        "DLA → CDG 20 NOV 2026 XAF 1040000"
    )
    proposal = parse(text)
    assert proposal.ticket_numbers == ("0572345678901", "0572345678902")
    assert proposal.passengers == ("NDONG/MARIE MS", "NDONG/JEAN MR")
    assert len(proposal.warnings) == 2


def test_missing_fields_are_empty_and_explained() -> None:
    proposal = parse("Billet 057 2345678901 NDONG/MARIE")
    assert proposal.departure_date is None
    assert proposal.price_xaf is None
    assert "Date de départ non reconnue." in proposal.warnings
    assert any("Prix non reconnu" in warning for warning in proposal.warnings)


def test_ordinary_text_is_not_mistaken_for_a_booking() -> None:
    proposal = parse("Bonjour, pouvez-vous me rappeler demain à propos du devis ? Merci.")
    assert not proposal.recognised
    assert proposal.ticket_numbers == ()
    assert proposal.origin == ""


def test_words_in_capitals_are_not_taken_for_airports() -> None:
    proposal = parse("TAX - FEE and MR/MS notes")
    assert proposal.origin == ""
    assert proposal.destination == ""


def test_display_names() -> None:
    assert display_name("NDONG/MARIE MS") == "Marie Ndong"
    assert display_name("EKANI/PIERRE-ANTOINE MR") == "Pierre-Antoine Ekani"
    assert display_name("ADAMS") == "Adams"


def test_hostile_pasted_text_is_read_in_bounded_time() -> None:
    import time

    hostile = [
        "booking" + " " * 20_000 + "!",
        "1 " * 10_000,
        "Fare : XAF " + "1" * 5_000,
        "057-" * 5_000,
    ]
    for text in hostile:
        started = time.perf_counter()
        parse(text)
        assert time.perf_counter() - started < 0.5


def test_an_absurd_amount_is_ignored_not_crashing() -> None:
    assert parse("Fare : XAF " + "9" * 14).price_xaf is None
