"""Contexte d'agence.

Les politiques RLS lisent deux variables de transaction PostgreSQL, ``app.agency_id`` et
``app.user_id``. Elles ne sont posées que dans une transaction (``set_config(..., true)``) :
elles disparaissent à la fin de celle-ci, même avec des connexions persistantes. Quand la
transaction est marquée pour annulation, le point de sauvegarde restaure lui-même la valeur
précédente : aucune requête ne doit alors être émise.

Les contraintes différées (équilibre du journal, clés étrangères) sont vérifiées à la sortie
du contexte, tant que la variable d'agence est posée : au COMMIT, elle ne le serait plus et la
RLS masquerait les lignes à contrôler.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import UUID

from django.db import connection, transaction

AGENCY_SETTING = "app.agency_id"
USER_SETTING = "app.user_id"

_current_agency: ContextVar[UUID | None] = ContextVar("current_agency", default=None)


class TenantContextMissing(RuntimeError):
    pass


class TenantMismatch(RuntimeError):
    pass


def _get_setting(name: str) -> str:
    with connection.cursor() as cursor:
        cursor.execute("SELECT COALESCE(current_setting(%s, true), '')", [name])
        row = cursor.fetchone()
    return str(row[0]) if row else ""


def _set_setting(name: str, value: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config(%s, %s, true)", [name, value])


def current_agency_id() -> UUID | None:
    return _current_agency.get()


def require_agency_id() -> UUID:
    agency_id = _current_agency.get()
    if agency_id is None:
        raise TenantContextMissing("Aucune agence dans le contexte courant.")
    return agency_id


@contextmanager
def tenant_scope(agency_id: UUID, user_id: UUID | None = None) -> Iterator[None]:
    """Exécute le bloc dans une transaction liée à l'agence (et à l'utilisateur)."""
    with transaction.atomic():
        previous_agency = _get_setting(AGENCY_SETTING)
        previous_user = _get_setting(USER_SETTING)
        _set_setting(AGENCY_SETTING, str(agency_id))
        if user_id is not None:
            _set_setting(USER_SETTING, str(user_id))
        token = _current_agency.set(agency_id)
        try:
            yield
        finally:
            _current_agency.reset(token)
        if not connection.needs_rollback:
            connection.check_constraints()
            _set_setting(AGENCY_SETTING, previous_agency)
            _set_setting(USER_SETTING, previous_user)


@contextmanager
def user_scope(user_id: UUID) -> Iterator[None]:
    """Autorise la lecture de l'appartenance de cet utilisateur, avant de connaître son agence."""
    with transaction.atomic():
        previous = _get_setting(USER_SETTING)
        _set_setting(USER_SETTING, str(user_id))
        yield
        if not connection.needs_rollback:
            _set_setting(USER_SETTING, previous)
