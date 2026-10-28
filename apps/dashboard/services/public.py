"""Façade publique de l'application dashboard."""

from datetime import date

from apps.dashboard import selectors
from apps.dashboard.dto import DashboardSnapshot, SalesReport
from apps.shared_kernel.actor import Actor


class DashboardService:
    @staticmethod
    def snapshot(actor: Actor, *, today: date | None = None) -> DashboardSnapshot:
        return selectors.snapshot(actor, today)

    @staticmethod
    def sales_report(actor: Actor, *, start: date, end: date) -> SalesReport:
        return selectors.sales_report(actor, start, end)
