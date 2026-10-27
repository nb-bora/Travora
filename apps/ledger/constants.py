from django.db import models


class Account(models.TextChoices):
    CLIENT = "client", "Compte client"
    CASH = "cash", "Caisse"
    BANK = "bank", "Banque"
    MOBILE_MONEY = "mobile_money", "Mobile Money"
    SUPPLIER = "supplier", "Fournisseur"
    MARGIN = "margin", "Marge"


TREASURY_ACCOUNTS = (Account.CASH, Account.BANK, Account.MOBILE_MONEY)


class Direction(models.TextChoices):
    DEBIT = "debit", "Débit"
    CREDIT = "credit", "Crédit"


class TransactionKind(models.TextChoices):
    SALE = "sale", "Vente"
    PAYMENT = "payment", "Encaissement"
    REVERSAL = "reversal", "Contre-passation"
