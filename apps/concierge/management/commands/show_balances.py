from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.cases.constants import CaseStatus
from apps.cases.dto import CaseSummary
from apps.cases.services.public import CasesService
from apps.concierge.access import actor_for
from apps.shared_kernel.money import format_xaf


def _row(case: CaseSummary, *, financials: bool) -> list[str]:
    row = [
        case.reference,
        case.customer_name,
        f"{case.departure_date:%d/%m/%Y}" if case.departure_date else "",
        format_xaf(case.price_total_xaf),
        format_xaf(case.balance_xaf),
    ]
    if financials:
        row.append(format_xaf(case.recognized_margin_xaf or 0))
    return row


class Command(BaseCommand):
    help = "Affiche, par dossier, le prix, le solde dû et (pour un gérant) la marge reconnue."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--as", dest="as_user", required=True, help="Utilisateur de l'agence")
        parser.add_argument("--all", action="store_true", help="Inclure dossiers clos et annulés")

    def handle(self, *args: Any, **options: Any) -> None:
        with actor_for(options["as_user"]) as actor:
            status = None if options["all"] else CaseStatus.OPEN
            cases = CasesService.list_cases(actor, status=status)
            financials = actor.can_view_financials

        header = ["Référence", "Client", "Départ", "Prix", "Solde dû"]
        if financials:
            header.append("Marge reconnue")
        rows = [header] + [_row(case, financials=financials) for case in cases]
        widths = [max(len(row[index]) for row in rows) for index in range(len(header))]
        for row in rows:
            self.stdout.write(
                "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip()
            )
        receivable = sum(case.balance_xaf for case in cases if case.balance_xaf > 0)
        self.stdout.write(f"\n{len(cases)} dossier(s) ; à encaisser : {format_xaf(receivable)}")
