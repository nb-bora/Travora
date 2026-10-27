"""Traduit les erreurs du domaine en messages clairs pour l'utilisateur."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.http import HttpRequest

from apps.cases.exceptions import (
    BalanceNotSettled,
    CaseError,
    CaseHasActiveSales,
    CaseNotClosed,
    CaseNotOpen,
    InvalidLine,
    LineLocked,
)
from apps.crm.exceptions import InvalidPhoneNumber
from apps.ledger.exceptions import LedgerError
from apps.payments.exceptions import DuplicateReference, InvalidPayment, PaymentError


def explain(error: Exception) -> str:
    if isinstance(error, PermissionDenied):
        return "Cette action est réservée au gérant."
    if isinstance(error, CaseNotOpen):
        return f"Le dossier {error} n'est plus ouvert : rien n'a été modifié."
    if isinstance(error, CaseNotClosed):
        return "Ce dossier n'est pas clos."
    if isinstance(error, LineLocked):
        return "Une ligne émise ou annulée ne se modifie plus."
    if isinstance(error, CaseHasActiveSales):
        return "Annulez d'abord les lignes émises de ce dossier."
    if isinstance(error, DuplicateReference):
        return "Cette référence de paiement existe déjà dans l'agence."
    if isinstance(error, (InvalidLine, InvalidPayment, BalanceNotSettled, InvalidPhoneNumber)):
        return str(error)
    if isinstance(error, (LedgerError, CaseError, PaymentError)):
        return str(error) or "Opération refusée."
    if isinstance(error, IntegrityError):
        return "Ce numéro de billet ou cette référence est déjà utilisé."
    raise error


HANDLED = (
    PermissionDenied,
    CaseError,
    PaymentError,
    LedgerError,
    InvalidPhoneNumber,
    IntegrityError,
)


@contextmanager
def reporting(request: HttpRequest, success: str | None = None) -> Iterator[None]:
    """Exécute un geste dans un point de sauvegarde ; le résultat part en message.

    Une erreur du domaine annule uniquement ce geste (le reste de la requête reste sain) et
    s'affiche en clair. Toute autre erreur remonte.
    """
    try:
        with transaction.atomic():
            yield
    except HANDLED as error:
        messages.error(request, explain(error))
    else:
        if success:
            messages.success(request, success)


def attempt[T](
    request: HttpRequest, action: Callable[[], T], success: str | None = None
) -> T | None:
    with reporting(request, success):
        return action()
    return None
