from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.accounts.services.public import AccountsService
from apps.tenancy.services.public import TenancyService


class Command(BaseCommand):
    help = "Suspend ou réactive l'agence d'un membre. Rien n'est supprimé."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--user", required=True, help="Un membre de l'agence concernée")
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--suspend", action="store_true")
        group.add_argument("--activate", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        user_id = AccountsService.find_user_id(options["user"])
        if user_id is None:
            raise CommandError(f"Utilisateur inconnu : {options['user']}")
        info = TenancyService.set_agency_active(user_id=user_id, active=options["activate"])
        if info is None:
            raise CommandError(f"{options['user']} n'appartient à aucune agence.")
        state = "réactivée" if options["activate"] else "suspendue"
        self.stdout.write(self.style.SUCCESS(f"Agence « {info.name} » {state}."))
