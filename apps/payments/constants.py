from django.db import models

from apps.ledger.constants import Account


class PaymentMethod(models.TextChoices):
    CASH = "cash", "Espèces"
    TRANSFER = "transfer", "Virement"
    MOBILE_MONEY = "mobile_money", "Mobile Money"


ACCOUNT_BY_METHOD = {
    PaymentMethod.CASH: Account.CASH,
    PaymentMethod.TRANSFER: Account.BANK,
    PaymentMethod.MOBILE_MONEY: Account.MOBILE_MONEY,
}
