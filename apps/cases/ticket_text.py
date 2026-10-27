"""Lecture d'un texte collé (e-ticket, e-mail, message) : des propositions, jamais des certitudes.

Tout ce qui est extrait ici est ensuite montré à l'agent, qui confirme ou corrige. Une valeur
ambiguë n'est pas devinée : elle est laissée vide et signalée dans ``warnings``.

Le texte vient d'un utilisateur : toutes les expressions sont bornées et l'entrée est tronquée,
pour qu'un texte hostile (des milliers d'espaces ou de chiffres) ne coûte jamais un temps de
calcul croissant.
"""

import re
from datetime import date

from apps.cases.dto import TicketProposal

MAX_TEXT = 5_000
MAX_AMOUNT = 10_000_000_000

TICKET_NUMBER = re.compile(r"(?<![0-9])([0-9]{3})[ -]?([0-9]{10})(?![0-9])")

# NOM/PRÉNOM éventuellement suivi d'une civilité : NDONG/MARIE MS, EKANI/PIERRE MR.
NAME_PART = r"[A-Z][A-Z'’-]{1,29}(?: [A-Z][A-Z'’-]{1,29})?"
PASSENGER = re.compile(
    r"\b(" + NAME_PART + r")/(" + NAME_PART + r")(?: (?:MR|MRS|MS|MISS|MSTR|CHD|INF))?\b"
)
CIVILITY = re.compile(r" (?:MR|MRS|MS|MISS|MSTR|CHD|INF)$")

BOOKING_REF = re.compile(
    r"(?:booking(?: ref(?:erence)?)?|pnr|record locator"
    r"|r[ée]f(?:[ée]rence)?(?: de r[ée]servation)?)[ :#]{0,4}([A-Z0-9]{6})\b",
    re.IGNORECASE,
)

ROUTE_ARROW = re.compile(r"\b([A-Z]{3})\b *(?:→|->|–|—|-|/|\bTO\b|\bÀ\b) *\b([A-Z]{3})\b")
# « DLA 20NOV 09:15 → CDG » : jusqu'à trois jetons (date, heure) entre le code et la flèche.
ROUTE_LOOSE = re.compile(r"\b([A-Z]{3})\b(?: [0-9A-Z:.]{1,8}){0,3} *(?:→|->|–|—) *\b([A-Z]{3})\b")
ROUTE_PAREN = re.compile(r"\(([A-Z]{3})\)")

MONTHS = {
    "JAN": 1, "JANV": 1, "FEB": 2, "FEV": 2, "FÉV": 2, "FEVR": 2, "MAR": 3, "MARS": 3,
    "APR": 4, "AVR": 4, "MAY": 5, "MAI": 5, "JUN": 6, "JUIN": 6, "JUL": 7, "JUIL": 7,
    "AUG": 8, "AOU": 8, "AOÛ": 8, "SEP": 9, "SEPT": 9, "OCT": 10, "NOV": 11, "DEC": 12, "DÉC": 12,
}  # fmt: skip
DATE_TEXT = re.compile(r"\b([0-9]{1,2}) ?([A-Za-zéÉûÛ]{3,4})\.?(?: ?([0-9]{4}))?\b")
DATE_NUMERIC = re.compile(r"\b([0-9]{1,2})/([0-9]{1,2})/([0-9]{4})\b")
DATE_ISO = re.compile(r"\b([0-9]{4})-([0-9]{2})-([0-9]{2})\b")
TIME = re.compile(r"(?<![0-9:])([01]?[0-9]|2[0-3]):([0-5][0-9])(?![0-9:])")
ISSUE_WORDS = re.compile(r"issu|[ée]mis|[ée]mission|date of issue", re.IGNORECASE)

AMOUNT = r"([0-9][0-9 .  ]{0,15}[0-9])"
PRICE_BEFORE = re.compile(r"\b(?:XAF|FCFA|F ?CFA|CFA) ?" + AMOUNT, re.IGNORECASE)
PRICE_AFTER = re.compile(AMOUNT + r" ?(?:XAF|FCFA|F ?CFA|CFA)\b", re.IGNORECASE)

CARRIERS = (
    "AIR FRANCE", "BRUSSELS AIRLINES", "ETHIOPIAN AIRLINES", "KENYA AIRWAYS", "ROYAL AIR MAROC",
    "TURKISH AIRLINES", "QATAR AIRWAYS", "EMIRATES", "LUFTHANSA", "KLM", "AIR CANADA",
    "BRITISH AIRWAYS", "CAMAIR-CO", "CAMAIR CO", "CAMRAIL",
)  # fmt: skip

NOT_AIRPORTS = frozenset(
    {
        "MRS", "MS", "MR", "TAX", "FEE", "XAF", "CFA", "EUR", "USD", "AND", "THE", "FOR",
        "NOV", "DEC", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT",
        "AIR", "NON", "YES", "PNR", "ETK", "TKT", "PAX", "ADT", "CHD", "INF",
    }
)  # fmt: skip


def extract_ticket_numbers(text: str) -> list[str]:
    """Propose les numéros de billet trouvés dans un texte collé, sans doublon.

    Un numéro compte 13 chiffres : un préfixe de compagnie à 3 chiffres puis 10 chiffres
    (format décrit par des sources secondaires, à confirmer sur la résolution IATA 722).
    C'est une proposition : l'agent confirme toujours la saisie.
    """
    found: list[str] = []
    for prefix, serial in TICKET_NUMBER.findall(text):
        number = prefix + serial
        if number not in found:
            found.append(number)
    return found


def _title(word: str) -> str:
    return "-".join(part.capitalize() for part in word.split("-"))


def display_name(passenger: str) -> str:
    """``NDONG/MARIE MS`` devient ``Marie Ndong`` (proposition pour le nom du client)."""
    cleaned = CIVILITY.sub("", passenger.strip())
    if "/" not in cleaned:
        return _title(cleaned)
    surname, given = cleaned.split("/", 1)
    return " ".join(_title(word) for word in f"{given} {surname}".split())


def _passengers(text: str) -> list[str]:
    seen: list[str] = []
    for match in PASSENGER.finditer(text):
        name = match.group(0)
        if name not in seen:
            seen.append(name)
    return seen


def _route(text: str) -> tuple[str, str]:
    for pattern in (ROUTE_ARROW, ROUTE_LOOSE):
        for arrow in pattern.finditer(text):
            if not ({arrow.group(1), arrow.group(2)} & NOT_AIRPORTS):
                return arrow.group(1), arrow.group(2)
    codes: list[str] = []
    for code in ROUTE_PAREN.findall(text):
        if code not in codes and code not in NOT_AIRPORTS:
            codes.append(code)
    if len(codes) >= 2:
        return codes[0], codes[1]
    return "", ""


def _next_occurrence(day: int, month: int, today: date) -> date | None:
    for year in (today.year, today.year + 1):
        try:
            candidate = date(year, month, day)
        except ValueError:
            return None
        if candidate >= today:
            return candidate
    return None


def _dates(text: str, today: date) -> tuple[date | None, bool]:
    """Première date de voyage (hors date d'émission) ; ``True`` si l'année a été supposée."""
    for line in text.splitlines():
        if ISSUE_WORDS.search(line):
            continue
        iso = DATE_ISO.search(line)
        if iso:
            try:
                return date(int(iso[1]), int(iso[2]), int(iso[3])), False
            except ValueError:
                continue
        numeric = DATE_NUMERIC.search(line)
        if numeric:
            try:
                return date(int(numeric[3]), int(numeric[2]), int(numeric[1])), False
            except ValueError:
                continue
        for match in DATE_TEXT.finditer(line):
            month = MONTHS.get(match[2].upper().rstrip("."))
            if month is None:
                continue
            day = int(match[1])
            if match[3]:
                try:
                    return date(int(match[3]), month, day), False
                except ValueError:
                    continue
            guessed = _next_occurrence(day, month, today)
            if guessed is not None:
                return guessed, True
    return None, False


def _times(text: str) -> tuple[str, str]:
    """Heure de départ et d'arrivée : les deux premières heures hors lignes d'émission."""
    found: list[str] = []
    for line in text.splitlines():
        if ISSUE_WORDS.search(line):
            continue
        for hours, minutes in TIME.findall(line):
            stamp = f"{int(hours):02d}:{minutes}"
            if stamp not in found:
                found.append(stamp)
    return (found[0] if found else ""), (found[1] if len(found) > 1 else "")


def _price(text: str) -> int | None:
    for pattern in (PRICE_BEFORE, PRICE_AFTER):
        match = pattern.search(text)
        if match:
            digits = re.sub(r"[^0-9]", "", match.group(1))
            if digits and int(digits) <= MAX_AMOUNT:
                return int(digits)
    return None


def _carrier(text: str) -> str:
    upper = text.upper()
    for name in CARRIERS:
        if name in upper:
            return name.title().replace("Camair Co", "Camair-Co")
    return ""


def parse_booking_text(text: str, today: date) -> TicketProposal:
    """Extrait d'un texte collé de quoi préparer un dossier. Rien n'est enregistré."""
    text = re.sub(r"[ \t  ]{2,}", " ", text[:MAX_TEXT])
    numbers = extract_ticket_numbers(text)
    passengers = _passengers(text)
    origin, destination = _route(text)
    departure, year_guessed = _dates(text, today)
    departure_time, arrival_time = _times(text)
    booking = BOOKING_REF.search(text)
    warnings: list[str] = []
    if len(numbers) > 1:
        warnings.append(
            f"{len(numbers)} numéros de billet trouvés : le premier est proposé, "
            "ajoutez les autres depuis le dossier."
        )
    if len(passengers) > 1:
        warnings.append(
            f"{len(passengers)} passagers trouvés : le premier est proposé, "
            "ajoutez les autres depuis le dossier."
        )
    if year_guessed:
        warnings.append("L'année du départ n'est pas écrite : la prochaine date est proposée.")
    if departure is None and (origin or numbers):
        warnings.append("Date de départ non reconnue.")
    price = _price(text)
    if price is None and numbers:
        warnings.append("Prix non reconnu : saisissez le prix de vente.")
    return TicketProposal(
        ticket_numbers=tuple(numbers),
        passengers=tuple(passengers),
        customer_name=display_name(passengers[0]) if passengers else "",
        origin=origin,
        destination=destination,
        departure_date=departure,
        departure_time=departure_time,
        arrival_time=arrival_time,
        carrier=_carrier(text),
        booking_reference=booking.group(1).upper() if booking else "",
        price_xaf=price,
        warnings=tuple(warnings),
    )
