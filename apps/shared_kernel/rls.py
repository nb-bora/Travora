"""Instructions SQL des politiques d'isolation et des gardes d'ajout seul.

Chaque fonction renvoie ``(instructions, instructions_inverses)`` pour ``migrations.RunSQL``.
"""

AGENCY_SETTING_SQL = "NULLIF(current_setting('app.agency_id', true), '')::uuid"
USER_SETTING_SQL = "NULLIF(current_setting('app.user_id', true), '')::uuid"
AGENCY_PREDICATE = f"agency_id = {AGENCY_SETTING_SQL}"


def tenant_policy(
    table: str, *, using: str = AGENCY_PREDICATE, check: str | None = None
) -> tuple[list[str], list[str]]:
    """RLS activée et forcée : sans variable d'agence, aucune ligne n'est visible."""
    return (
        [
            f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY",
            f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY",
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING ({using}) WITH CHECK ({check or using})",
        ],
        [
            f"DROP POLICY tenant_isolation ON {table}",
            f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY",
            f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY",
        ],
    )


FORBID_MUTATION_FUNCTION = """
CREATE OR REPLACE FUNCTION forbid_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '% est en ajout seul', TG_TABLE_NAME USING ERRCODE = 'restrict_violation';
END
$$
"""


def append_only_guard(table: str) -> tuple[list[str], list[str]]:
    """Déclencheurs refusant UPDATE, DELETE et TRUNCATE, quel que soit le rôle."""
    return (
        [
            FORBID_MUTATION_FUNCTION,
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION forbid_mutation()",
            f"CREATE TRIGGER {table}_no_truncate BEFORE TRUNCATE ON {table} "
            "FOR EACH STATEMENT EXECUTE FUNCTION forbid_mutation()",
        ],
        [
            f"DROP TRIGGER {table}_no_truncate ON {table}",
            f"DROP TRIGGER {table}_append_only ON {table}",
        ],
    )
