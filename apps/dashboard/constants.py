from django.db import models


class AlertKind(models.TextChoices):
    OVERDUE_BALANCE = "overdue_balance", "Solde impayé depuis longtemps"
    DEPARTURE_SOON = "departure_soon", "Départ proche avec solde impayé"
    QUOTE_EXPIRED = "quote_expired", "Devis expiré sans réponse"
