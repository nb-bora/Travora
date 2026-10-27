from django.db import models


class Role(models.TextChoices):
    MANAGER = "manager", "Gérant"
    AGENT = "agent", "Agent"
