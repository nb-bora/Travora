import re

TICKET_NUMBER = re.compile(r"(?<!\d)(\d{3})[ -]?(\d{10})(?!\d)")


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
