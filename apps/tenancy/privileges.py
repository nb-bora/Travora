"""Droits du rôle d'exécution, appliqués après chaque migration.

Le rôle d'exécution reçoit les droits de lecture et d'écriture sur toutes les tables,
sauf sur les tables en ajout seul où UPDATE, DELETE et TRUNCATE sont retirés. Si le rôle
n'existe pas (base locale sans ``infra/postgres/roles.dev.sql``), rien n'est fait.
"""

from typing import Any

from django.apps import apps
from django.db import DEFAULT_DB_ALIAS, connections

from apps.shared_kernel.append_only import AppendOnlyModel

RUNTIME_ROLE = "travora_app"


def grant_runtime_privileges(using: str = DEFAULT_DB_ALIAS, **kwargs: Any) -> None:
    connection = connections[using]
    if connection.vendor != "postgresql":
        return
    append_only_tables = [
        connection.ops.quote_name(model._meta.db_table)
        for model in apps.get_models()
        if issubclass(model, AppendOnlyModel)
    ]
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [RUNTIME_ROLE])
        if cursor.fetchone() is None:
            return
        cursor.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {RUNTIME_ROLE}"
        )
        cursor.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {RUNTIME_ROLE}")
        for table in append_only_tables:
            cursor.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON {table} FROM {RUNTIME_ROLE}")
