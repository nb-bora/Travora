"""Accès commun aux commandes : l'agence est déduite de l'utilisateur, jamais saisie."""

import getpass
import os
from collections.abc import Iterator
from contextlib import contextmanager

from django.core.management.base import CommandError

from apps.accounts.services.public import AccountsService
from apps.shared_kernel.actor import Actor
from apps.tenancy.services.public import TenancyService


@contextmanager
def actor_for(username: str) -> Iterator[Actor]:
    user_id = AccountsService.find_user_id(username)
    if user_id is None:
        raise CommandError(f"Utilisateur inconnu : {username}")
    with TenancyService.actor_scope(user_id) as actor:
        if actor is None:
            raise CommandError(f"{username} n'appartient à aucune agence active.")
        yield actor


def read_password(env_name: str) -> str:
    """Lit le mot de passe dans l'environnement, sinon le demande sans l'afficher."""
    value = os.environ.get(env_name)
    if value:
        return value
    first = getpass.getpass("Mot de passe : ")
    if first != getpass.getpass("Confirmation : "):
        raise CommandError("Les mots de passe diffèrent.")
    return first
