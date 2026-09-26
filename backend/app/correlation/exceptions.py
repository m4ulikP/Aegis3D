"""Domain exceptions for temporal persistence and sensor correlation."""


class TemporalCorrelationError(Exception):
    """Base exception for temporal persistence and correlation processing errors."""
    pass


class InvalidWindowError(TemporalCorrelationError):
    """Raised when temporal observation window duration is invalid."""
    pass


class InvalidToleranceError(TemporalCorrelationError):
    """Raised when cross-sensor correlation temporal tolerance is invalid."""
    pass
