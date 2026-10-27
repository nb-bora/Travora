from datetime import date
from pathlib import Path
from typing import Any

from django.core.exceptions import PermissionDenied
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from apps.concierge.access import actor_for
from apps.concierge.csv_import import COLUMNS, CsvFormatError, import_cases


class Command(BaseCommand):
    help = (
        "Importe des dossiers ouverts depuis un CSV (colonnes : " + ", ".join(COLUMNS) + "). "
        "Sans --commit, l'import est un essai à blanc : rien n'est enregistré."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--as", dest="as_user", required=True, help="Gérant de l'agence")
        parser.add_argument("--file", required=True, type=Path, help="Fichier CSV (UTF-8)")
        parser.add_argument("--commit", action="store_true", help="Enregistrer pour de bon")
        parser.add_argument(
            "--sale-date",
            default=date.today().isoformat(),
            help="Date de vente et d'encaissement des lignes importées (AAAA-MM-JJ)",
        )
        parser.add_argument(
            "--default-country-code",
            default="",
            help="Indicatif ajouté aux numéros sans indicatif (ex. +237) ; aucun par défaut",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            sale_date = date.fromisoformat(options["sale_date"])
        except ValueError as error:
            raise CommandError("--sale-date doit être au format AAAA-MM-JJ.") from error

        with actor_for(options["as_user"]) as actor:
            try:
                actor.require_manager()
            except PermissionDenied as error:
                raise CommandError("Seul un gérant peut importer des dossiers.") from error
            try:
                report = import_cases(
                    actor,
                    options["file"],
                    sale_date=sale_date,
                    default_country_code=options["default_country_code"],
                )
            except (CsvFormatError, OSError) as error:
                raise CommandError(str(error)) from error

            self.stdout.write(
                f"{len(report.created)} dossier(s), {report.lines} ligne(s), "
                f"{report.payments} paiement(s) ; {len(report.skipped)} déjà présent(s) ignoré(s)."
            )
            if report.errors:
                for message in report.errors:
                    self.stderr.write(message)
                transaction.set_rollback(True)
                raise CommandError(
                    f"{len(report.errors)} dossier(s) en erreur : aucun enregistrement."
                )
            if not options["commit"]:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("Essai à blanc : rien n'a été enregistré."))
                return
        self.stdout.write(self.style.SUCCESS("Import enregistré."))
