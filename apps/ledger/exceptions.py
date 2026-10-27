class LedgerError(Exception):
    pass


class UnbalancedTransaction(LedgerError):
    pass


class InvalidPosting(LedgerError):
    pass


class TransactionNotFound(LedgerError):
    pass


class AlreadyReversed(LedgerError):
    pass


class CannotReverseReversal(LedgerError):
    pass


class IdempotencyConflict(LedgerError):
    pass


class DateOutOfRange(LedgerError):
    pass


class PeriodClosed(LedgerError):
    pass


class InvalidClosure(LedgerError):
    pass
