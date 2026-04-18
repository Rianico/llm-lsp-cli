"""Domain exceptions."""

__all__ = ["NameValidationError", "PathValidationError"]


class PathValidationError(ValueError):
    """Raised when path validation fails."""


class NameValidationError(ValueError):
    """Raised when workspace name validation fails."""
