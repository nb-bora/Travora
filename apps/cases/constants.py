from django.db import models


class CaseStatus(models.TextChoices):
    OPEN = "open", "Ouvert"
    CLOSED = "closed", "Clos"
    CANCELLED = "cancelled", "Annulé"


class LineKind(models.TextChoices):
    AIR_TICKET = "air_ticket", "Billet d'avion"
    BUS_TICKET = "bus_ticket", "Billet de bus"
    TRAIN_TICKET = "train_ticket", "Billet de train"
    BOAT_TICKET = "boat_ticket", "Billet de bateau"
    FREE_SERVICE = "free_service", "Prestation libre"


# Titres de transport : portent une référence (numéro de billet ou code de réservation).
TICKET_KINDS = frozenset(
    {LineKind.AIR_TICKET, LineKind.BUS_TICKET, LineKind.TRAIN_TICKET, LineKind.BOAT_TICKET}
)
