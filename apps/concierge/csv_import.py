"""Import de dossiers ouverts depuis un CSV, pour le démarrage à chaud d'une agence.

Une ligne du fichier est une ligne de dossier ; les lignes qui partagent la même
``reference`` forment un dossier. Un dossier déjà présent est ignoré : l'import est rejouable.
"""

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from django.db import IntegrityError, transaction

from apps.cases.constants import LineKind
from apps.cases.exceptions import CaseError
from apps.cases.services.public import CasesService
from apps.crm.services.public import CrmService
from apps.ledger.exceptions import LedgerError
from apps.payments.constants import PaymentMethod
from apps.payments.exceptions import PaymentError
from apps.payments.services.public import PaymentsService
from apps.shared_kernel.actor import Actor

COLUMNS = (
    "reference",
    "customer_name",
    "customer_phone",
    "departure_date",
    "kind",
    "label",
    "passenger_name",
    "ticket_number",
    "price_xaf",
    "cost_xaf",
    "paid_xaf",
    "payment_method",
    "payment_reference",
)
EXPECTED_ERRORS = (ValueError, CaseError, PaymentError, LedgerError, IntegrityError)


class CsvFormatError(Exception):
    pass


@dataclass(frozen=True)
class Row:
    number: int
    values: dict[str, str]


@dataclass
class ImportReport:
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    lines: int = 0
    payments: int = 0


def read_rows(path: Path) -> dict[str, list[Row]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise CsvFormatError(f"Colonnes manquantes : {', '.join(missing)}")
        groups: dict[str, list[Row]] = defaultdict(list)
        for number, raw in enumerate(reader, start=2):
            values = {column: (raw.get(column) or "").strip() for column in COLUMNS}
            if not values["reference"]:
                raise CsvFormatError(f"Ligne {number} : la référence du dossier est obligatoire.")
            groups[values["reference"]].append(Row(number, values))
    return dict(groups)


def _amount(row: Row, column: str, *, required: bool = False) -> int | None:
    raw = row.values[column]
    if not raw:
        if required:
            raise ValueError(f"{column} est obligatoire")
        return None
    if not raw.isdigit():
        raise ValueError(f"{column} doit être un entier en XAF (reçu : {raw!r})")
    return int(raw)


def _import_group(
    actor: Actor,
    reference: str,
    rows: list[Row],
    *,
    sale_date: date,
    default_country_code: str,
    report: ImportReport,
) -> None:
    first = rows[0].values
    customer = CrmService.find_or_create_customer(
        actor,
        name=first["customer_name"],
        phone=first["customer_phone"],
        default_country_code=default_country_code,
    )
    departure = date.fromisoformat(first["departure_date"]) if first["departure_date"] else None
    case_id = CasesService.create_case(
        actor, customer_id=customer.id, departure_date=departure, reference=reference
    )
    for row in rows:
        price = _amount(row, "price_xaf", required=True)
        cost = _amount(row, "cost_xaf")
        assert price is not None
        line = CasesService.add_line(
            actor,
            case_id=case_id,
            kind=LineKind(row.values["kind"] or LineKind.FREE_SERVICE.value),
            label=row.values["label"],
            price_xaf=price,
            cost_xaf=cost,
            passenger_name=row.values["passenger_name"],
            ticket_number=row.values["ticket_number"],
        )
        report.lines += 1
        if cost is not None:
            CasesService.issue_line(actor, line_id=line.id, issued_on=sale_date)
        paid = _amount(row, "paid_xaf")
        if paid:
            PaymentsService.record_payment(
                actor,
                case_id=case_id,
                method=PaymentMethod(row.values["payment_method"] or PaymentMethod.CASH.value),
                amount_xaf=paid,
                reference=row.values["payment_reference"],
                received_on=sale_date,
                idempotency_key=f"import:{reference}:{row.number}",
            )
            report.payments += 1


def import_cases(
    actor: Actor, path: Path, *, sale_date: date, default_country_code: str
) -> ImportReport:
    groups = read_rows(path)
    report = ImportReport()
    for reference, rows in groups.items():
        if CasesService.find_case_id_by_reference(actor, reference) is not None:
            report.skipped.append(reference)
            continue
        try:
            with transaction.atomic():
                _import_group(
                    actor,
                    reference,
                    rows,
                    sale_date=sale_date,
                    default_country_code=default_country_code,
                    report=report,
                )
        except EXPECTED_ERRORS as error:
            numbers = ", ".join(str(row.number) for row in rows)
            report.errors.append(f"Dossier {reference} (lignes {numbers}) : {error}")
            continue
        report.created.append(reference)
    return report
