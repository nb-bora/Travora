from django.db import models


class CaseStatus(models.TextChoices):
    OPEN = "open", "Ouvert"
    CLOSED = "closed", "Clos"
    CANCELLED = "cancelled", "Annulé"


class LineKind(models.TextChoices):
    AIR_TICKET = "air_ticket", "Billet d'avion"
    FREE_SERVICE = "free_service", "Prestation libre"
