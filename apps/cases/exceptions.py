class CaseError(Exception):
    pass


class CaseNotFound(CaseError):
    pass


class LineNotFound(CaseError):
    pass


class CaseNotOpen(CaseError):
    pass


class InvalidLine(CaseError):
    pass


class LineLocked(CaseError):
    pass


class BalanceNotSettled(CaseError):
    pass


class CaseHasActiveSales(CaseError):
    pass
