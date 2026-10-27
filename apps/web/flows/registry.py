"""Parcours disponibles."""

from apps.web.flows.air import AIR
from apps.web.flows.base import FlowDef
from apps.web.flows.bus import BUS

FLOWS: dict[str, FlowDef] = {"air": AIR, "bus": BUS}
