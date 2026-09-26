"""Domain exceptions for rule-based anomaly detection."""


class AnomalyError(Exception):
    """Base exception for anomaly detection processing errors."""
    pass


class InvalidEventDataError(AnomalyError):
    """Raised when event features are missing, non-finite, or malformed."""
    pass


class InvalidBaselineError(AnomalyError):
    """Raised when baseline statistics are missing, negative, or non-finite."""
    pass


class InvalidThresholdError(AnomalyError):
    """Raised when anomaly threshold configuration is invalid."""
    pass


class BaselineNotFoundError(AnomalyError):
    """Raised when no baseline exists for a zone during service analysis."""
    pass
