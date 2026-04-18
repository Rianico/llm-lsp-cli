"""Logging infrastructure for LSP client.

Provides structured, color-coded logging with TTY detection.
"""

import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from llm_lsp_cli.domain.value_objects import LogLevel


class LogComponent(str, Enum):
    """Component identifier for log messages."""

    CLIENT = "client"
    SERVER = "server"
    DAEMON = "daemon"
    TRANSPORT = "transport"


class Colors:
    """ANSI color codes with TTY detection and NO_COLOR support."""

    # ANSI color codes
    RESET = "\033[0m"
    CLI = "\033[36m"       # Cyan for client
    SERVER = "\033[33m"    # Yellow for server
    SUCCESS = "\033[32m"   # Green for success
    ERROR = "\033[31m"     # Red for error
    INFO = "\033[34m"      # Blue for info
    DEBUG = "\033[37m"     # White for debug

    # Flag to track explicit disable
    _disabled = False

    @classmethod
    def supported(cls) -> bool:
        """Check if colors are supported (TTY and no NO_COLOR)."""
        if cls._disabled:
            return False
        if os.environ.get("NO_COLOR"):
            return False
        return sys.stdout.isatty()

    @classmethod
    def disable(cls) -> None:
        """Disable colors by setting all codes to empty strings."""
        cls._disabled = True
        cls.RESET = ""
        cls.CLI = ""
        cls.SERVER = ""
        cls.SUCCESS = ""
        cls.ERROR = ""
        cls.INFO = ""
        cls.DEBUG = ""


@dataclass(frozen=True)
class LogEntry:
    """Immutable log entry.

    Attributes:
        timestamp: ISO-8601 timestamp of the log entry.
        level: Log level (ERROR, INFO, SUCCESS, DEBUG, TRACE).
        component: Component that generated the log (client, server, daemon, transport).
        message: Log message text.
        metadata: Additional key-value pairs.
    """

    timestamp: datetime
    level: LogLevel
    component: LogComponent
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize LogEntry to dictionary."""
        return {
            "timestamp": self.timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "level": self.level.name,
            "component": self.component.value,
            "message": self.message,
            "metadata": self.metadata,
        }


class ColorFormatter:
    """Formats LogEntry with color codes."""

    LEVEL_COLORS: dict[LogLevel, str] = {
        LogLevel.ERROR: Colors.ERROR,
        LogLevel.INFO: Colors.INFO,
        LogLevel.SUCCESS: Colors.SUCCESS,
        LogLevel.DEBUG: Colors.DEBUG,
        LogLevel.TRACE: Colors.DEBUG,
    }

    COMPONENT_COLORS: dict[LogComponent, str] = {
        LogComponent.CLIENT: Colors.CLI,
        LogComponent.SERVER: Colors.SERVER,
        LogComponent.DAEMON: Colors.DEBUG,
        LogComponent.TRANSPORT: Colors.DEBUG,
    }

    def format(self, entry: LogEntry) -> str:
        """Format a LogEntry with colors."""
        if not Colors.supported():
            return self._format_plain(entry)

        level_color = self.LEVEL_COLORS.get(entry.level, "")
        component_color = self.COMPONENT_COLORS.get(entry.component, "")

        return (
            f"{level_color}[{entry.level.name}]{Colors.RESET} "
            f"{component_color}[{entry.component.value}]{Colors.RESET} "
            f"{entry.message}"
        )

    def _format_plain(self, entry: LogEntry) -> str:
        """Format without colors for non-TTY output."""
        return f"[{entry.level.name}] [{entry.component.value}] {entry.message}"


class LSPMessageFormatter:
    """Formats LSP messages with truncation and direction indicators."""

    MAX_PAYLOAD_LENGTH = 200

    def format_trace(self, direction: str, message: dict[str, Any]) -> str:
        """Format an LSP message for trace logging.

        Args:
            direction: Arrow indicator (→ for sent, ← for received).
            message: LSP message dictionary.

        Returns:
            Formatted trace string with method name and truncated payload.
        """
        method = message.get("method", "")
        params = message.get("params", {})

        # Truncate payload if too long
        payload_str = str(params)
        if len(payload_str) > self.MAX_PAYLOAD_LENGTH:
            payload_str = payload_str[: self.MAX_PAYLOAD_LENGTH] + "..."

        # Choose color based on direction
        color = Colors.CLI if direction == "→" else Colors.SERVER

        if not Colors.supported():
            return f"{direction} {method} {payload_str}"

        return f"{color}{direction}{Colors.RESET} {method} {payload_str}"


class LSPLogger:
    """Logger for LSP client with structured output and level filtering.

    Args:
        min_level: Minimum log level to output (default: INFO).
        use_colors: Force colors on/off (None = auto-detect).
        logger: Optional stdlib logger to delegate to.
    """

    def __init__(
        self,
        min_level: LogLevel = LogLevel.INFO,
        use_colors: bool | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._min_level = min_level
        self._logger = logger or logging.getLogger("llm_lsp_cli")

        # Handle color configuration
        if use_colors is False:
            Colors.disable()
        # If use_colors is None or True, auto-detect (do nothing - Colors.supported() handles it)

    def _should_log(self, level: LogLevel) -> bool:
        """Check if a message at the given level should be logged."""
        return level <= self._min_level

    def _log(self, level: LogLevel, component: LogComponent, message: str) -> None:
        """Log a message at the specified level."""
        if not self._should_log(level):
            return

        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            component=component,
            message=message,
        )

        formatter = ColorFormatter()
        self._logger.info(formatter.format(entry))

    def error(self, message: str) -> None:
        """Log an error message."""
        self._log(LogLevel.ERROR, LogComponent.CLIENT, message)

    def info(self, message: str) -> None:
        """Log an info message."""
        self._log(LogLevel.INFO, LogComponent.CLIENT, message)

    def success(self, message: str) -> None:
        """Log a success message."""
        self._log(LogLevel.SUCCESS, LogComponent.CLIENT, message)

    def debug(self, message: str) -> None:
        """Log a debug message."""
        self._log(LogLevel.DEBUG, LogComponent.CLIENT, message)

    def debug_event(self, event_type: str, **metadata: Any) -> None:
        """Log a daemon debug event."""
        message = f"[{event_type}] {metadata}"
        self._log(LogLevel.DEBUG, LogComponent.DAEMON, message)

    def trace(self, message: str) -> None:
        """Log a trace message."""
        self._log(LogLevel.TRACE, LogComponent.CLIENT, message)

    def trace_lsp_message(self, direction: str, message: dict[str, Any]) -> None:
        """Log an LSP message with direction indicator."""
        if not self._should_log(LogLevel.TRACE):
            return

        formatter = LSPMessageFormatter()
        formatted = formatter.format_trace(direction, message)
        self._logger.info(formatted)


__all__ = [
    "Colors",
    "LogComponent",
    "LogEntry",
    "LogLevel",
    "ColorFormatter",
    "LSPMessageFormatter",
    "LSPLogger",
]
