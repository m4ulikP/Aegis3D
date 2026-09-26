"""Exceptions for trend analysis evaluation module."""


class TrendError(Exception):
    """Base exception for all trend analysis errors."""
    pass


class InvalidTrendConfigError(TrendError):
    """Raised when trend evaluation configuration parameters are invalid."""
    pass


class InsufficientTrendDataError(TrendError):
    """Raised when trend evaluation cannot proceed due to missing or insufficient data."""
    pass
