class PaymentError(Exception):
    pass


class InvalidPayment(PaymentError):
    pass


class DuplicateReference(PaymentError):
    pass


class PaymentNotFound(PaymentError):
    pass


class PaymentAlreadyVoided(PaymentError):
    pass


class IdempotencyConflict(PaymentError):
    pass
