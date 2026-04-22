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

    NOTE: These values (0-4) represent an ordering hierarchy for domain logic,
    NOT Python logging levels. The Python logging infrastructure uses a different
    scale: CRITICAL=50, ERROR=40, WARNING=30, INFO=20, DEBUG=10. The transport
    layer's TRACE_LEVEL=5 follows Python's convention for a level below DEBUG.

    See also: llm_lsp_cli.lsp.transport.TRACE_LEVEL for the actual Python logging level.
    """

    ERROR = 0
    INFO = 1
    SUCCESS = 2
    DEBUG = 3
    TRACE = 4
