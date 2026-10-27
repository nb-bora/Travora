from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import IntegrityError, transaction

from apps.accounts.services.public import AccountsService
from apps.concierge.access import actor_for, read_password
from apps.shared_kernel.roles import Role


class Command(BaseCommand):
    help = "Ajoute un agent ou un gérant à l'agence d'un gérant existant."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--as", dest="as_user", required=True, help="Gérant qui ajoute")
        parser.add_argument("--username", required=True, help="Identifiant du nouveau membre")
        parser.add_argument("--role", choices=Role.values, default=Role.AGENT.value)
        parser.add_argument("--password-env", default="TRAVORA_PASSWORD")

    def handle(self, *args: Any, **options: Any) -> None:
        password = read_password(options["password_env"])
        try:
            with actor_for(options["as_user"]) as actor, transaction.atomic():
                AccountsService.create_member(
                    actor,
                    username=options["username"],
                    password=password,
                    role=Role(options["role"]),
                )
        except PermissionDenied as error:
            raise CommandError("Seul un gérant peut ajouter un membre.") from error
        except ValidationError as error:
            raise CommandError("; ".join(error.messages)) from error
        except IntegrityError as error:
            raise CommandError("Cet identifiant est déjà utilisé.") from error
        self.stdout.write(
            self.style.SUCCESS(f"{options['username']} ajouté avec le rôle {options['role']}.")
        )
