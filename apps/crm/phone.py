import re

from apps.crm.exceptions import InvalidPhoneNumber

E164 = re.compile(r"\+[1-9][0-9]{6,14}")
SEPARATORS = re.compile(r"[\s().-]")


def normalize_phone(raw: str, default_country_code: str = "") -> str:
    """Renvoie le numéro au format E.164 ; une chaîne vide reste vide.

    Un numéro sans indicatif n'est complété que si l'appelant fournit explicitement
    ``default_country_code`` : aucun plan de numérotation n'est supposé.
    """
    cleaned = SEPARATORS.sub("", raw)
    if not cleaned:
        return ""
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if not cleaned.startswith("+") and default_country_code:
        cleaned = default_country_code + cleaned.lstrip("0")
    if not E164.fullmatch(cleaned):
        raise InvalidPhoneNumber(f"Numéro invalide : {raw!r} (format attendu : +indicatif...)")
    return cleaned
