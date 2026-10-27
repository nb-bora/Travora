class QuoteError(Exception):
    pass


class QuoteNotFound(QuoteError):
    pass


class InvalidQuote(QuoteError):
    pass


class QuoteFrozen(QuoteError):
    pass


class InvalidTransition(QuoteError):
    pass
