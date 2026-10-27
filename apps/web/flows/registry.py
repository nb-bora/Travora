"""Parcours disponibles."""

from apps.web.flows.air import AIR
from apps.web.flows.base import FlowDef

FLOWS: dict[str, FlowDef] = {"air": AIR}
