"""Domain exceptions for baseline statistical processing."""


class BaselineError(Exception):
    """Base exception for baseline processing errors."""
    pass


class InsufficientDataError(BaselineError):
    """Raised when insufficient qualifying events exist to compute a baseline."""
    pass


class InvalidTimeWindowError(BaselineError):
    """Raised when the specified observation window is invalid (e.g. valid_until <= valid_from)."""
    pass


class ZoneNotFoundError(BaselineError):
    """Raised when requested Zone does not exist in the database."""
    pass
