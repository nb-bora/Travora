from django.db import models


class QuoteStatus(models.TextChoices):
    DRAFT = "draft", "Brouillon"
    SENT = "sent", "Envoyé"
    ACCEPTED = "accepted", "Accepté"
    REFUSED = "refused", "Refusé"
