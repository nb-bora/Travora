from datetime import date
from typing import Any

from django.core.exceptions import PermissionDenied
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from apps.concierge.access import actor_for
from apps.ledger.exceptions import InvalidClosure
from apps.ledger.services.public import LedgerService


class Command(BaseCommand):
    help = "Clôture la comptabilité de l'agence jusqu'à une date (incluse). Ne recule jamais."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--as", dest="as_user", required=True, help="Gérant")
        parser.add_argument("--until", required=True, help="Dernier jour clôturé (AAAA-MM-JJ)")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            until = date.fromisoformat(options["until"])
        except ValueError as error:
            raise CommandError("Date invalide : utiliser AAAA-MM-JJ.") from error
        try:
            with actor_for(options["as_user"]) as actor, transaction.atomic():
                LedgerService.close_period(actor, closed_until=until)
        except PermissionDenied as error:
            raise CommandError("Seul un gérant clôture une période.") from error
        except InvalidClosure as error:
            raise CommandError(str(error)) from error
        self.stdout.write(self.style.SUCCESS(f"Comptabilité clôturée jusqu'au {until}."))
