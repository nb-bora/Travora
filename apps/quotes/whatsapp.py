from urllib.parse import quote


def whatsapp_link(phone: str, message: str) -> str:
    """Lien ``wa.me`` : l'utilisateur envoie lui-même le message prérempli.

    Sans numéro, le lien ouvre le choix du contact. Le format est décrit par des sources
    tierces : à confirmer sur la documentation officielle de WhatsApp avant la mise en production.
    """
    digits = phone.removeprefix("+")
    base = f"https://wa.me/{digits}" if digits.isdigit() else "https://wa.me/"
    return f"{base}?text={quote(message, safe='')}"
