"""Exceptions for Structural Health Indicator (SHI) module."""


class HealthError(Exception):
    """Base exception for structural health calculation errors."""
    pass


class InvalidHealthConfigError(HealthError):
    """Raised when configuration parameters for SHI calculation are invalid."""
    pass
