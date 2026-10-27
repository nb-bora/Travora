"""Façade publique de l'application dashboard."""

from datetime import date

from apps.dashboard import selectors
from apps.dashboard.dto import DashboardSnapshot
from apps.shared_kernel.actor import Actor


class DashboardService:
    @staticmethod
    def snapshot(actor: Actor, *, today: date | None = None) -> DashboardSnapshot:
        return selectors.snapshot(actor, today)
