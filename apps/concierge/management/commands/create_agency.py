from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import IntegrityError, transaction

from apps.accounts.services.public import AccountsService
from apps.concierge.access import read_password
from apps.tenancy.services.public import TenancyService


class Command(BaseCommand):
    help = "Crée une agence et son premier gérant. Le mot de passe est lu dans l'environnement."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--name", required=True, help="Nom de l'agence")
        parser.add_argument("--slug", required=True, help="Identifiant court, unique")
        parser.add_argument("--manager", required=True, help="Identifiant de connexion du gérant")
        parser.add_argument(
            "--password-env",
            default="TRAVORA_PASSWORD",
            help="Variable d'environnement contenant le mot de passe (sinon, saisie masquée)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        password = read_password(options["password_env"])
        try:
            with transaction.atomic():
                agency = TenancyService.create_agency(name=options["name"], slug=options["slug"])
                with TenancyService.scope(agency.id):
                    AccountsService.create_first_manager(
                        username=options["manager"], password=password
                    )
        except ValidationError as error:
            raise CommandError("; ".join(error.messages)) from error
        except IntegrityError as error:
            raise CommandError("Identifiant d'agence ou de gérant déjà utilisé.") from error
        self.stdout.write(
            self.style.SUCCESS(f"Agence {agency.name} créée ; gérant : {options['manager']}.")
        )
