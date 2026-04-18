"""Logging value objects for domain layer."""

from enum import IntEnum

__all__ = ["LogLevel"]


class LogLevel(IntEnum):
    """Log level hierarchy for filtering log messages.

    Levels are ordered from lowest (most severe) to highest (most verbose):
    - ERROR: Only errors (level 0)
    - INFO: Errors + info messages (level 1)
    - SUCCESS: Errors + info + success messages (level 2)
    - DEBUG: Errors + info + success + debug messages (level 3)
    - TRACE: All messages including full LSP payloads (level 4)
    """

    ERROR = 0
    INFO = 1
    SUCCESS = 2
    DEBUG = 3
    TRACE = 4
