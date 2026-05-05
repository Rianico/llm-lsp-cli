# pyright: reportUnannotatedClassAttribute=false
"""Structured logging with context tracking."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field


@dataclass
class LogContext:
    """Context information for structured logging.

    Holds request_id, component, and metadata for improved debugging
    and observability.

    Attributes:
        request_id: Unique identifier for request tracking.
        component: Component or module name for context.
        metadata: Additional key-value pairs for context.
    """

    request_id: str | None = None
    component: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialize the context to a dictionary.

        Returns:
            A dictionary representation of the context.
        """
        result: dict[str, object] = {}

        if self.request_id:
            result["request_id"] = self.request_id
        if self.component:
            result["component"] = self.component
        if self.metadata:
            result["metadata"] = self.metadata

        return result


class StructuredLogger:
    """Provides structured logging with context tracking.

    This logger outputs JSON-formatted log entries with context
    information for improved debugging and observability.

    Design: Request ID tracking, exception logging with stack traces.
    """

    def __init__(
        self,
        name: str,
        handler: logging.Handler | None = None,
    ) -> None:
        """Initialize the structured logger.

        Args:
            name: Logger name (typically module or component name).
            handler: Optional logging handler. If not provided, uses
                the default handler.
        """
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.DEBUG)

        # Clear existing handlers to avoid duplicates
        self._logger.handlers.clear()

        if handler:
            self._logger.addHandler(handler)
        else:
            # Default to a console handler with basic formatting
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            self._logger.addHandler(console_handler)

    def _format_message(
        self,
        message: str,
        context: LogContext | None = None,
        extra: dict[str, object] | None = None,
    ) -> tuple[str, dict[str, object]]:
        """Format a log message with context.

        Args:
            message: The log message.
            context: Optional LogContext with request/component info.
            extra: Optional additional fields.

        Returns:
            Tuple of (formatted message, extra dict for logging).
        """
        extra_dict: dict[str, object] = {}

        if context:
            ctx_data = context.to_dict()
            extra_dict.update(ctx_data)

        if extra:
            extra_dict.update(extra)

        # Build formatted message with context
        if extra_dict:
            context_str = " | ".join(f"{k}={v}" for k, v in extra_dict.items())
            return f"[{context_str}] {message}", extra_dict

        return message, extra_dict

    def info(
        self,
        message: str,
        context: LogContext | None = None,
        extra: dict[str, object] | None = None,
    ) -> None:
        """Log an info message.

        Args:
            message: The log message.
            context: Optional LogContext.
            extra: Optional additional fields.
        """
        formatted, extra_dict = self._format_message(message, context, extra)
        self._logger.info(formatted, extra=extra_dict or None)

    def debug(
        self,
        message: str,
        context: LogContext | None = None,
        extra: dict[str, object] | None = None,
    ) -> None:
        """Log a debug message.

        Args:
            message: The log message.
            context: Optional LogContext.
            extra: Optional additional fields.
        """
        formatted, extra_dict = self._format_message(message, context, extra)
        self._logger.debug(formatted, extra=extra_dict or None)

    def warning(
        self,
        message: str,
        context: LogContext | None = None,
        extra: dict[str, object] | None = None,
    ) -> None:
        """Log a warning message.

        Args:
            message: The log message.
            context: Optional LogContext.
            extra: Optional additional fields.
        """
        formatted, extra_dict = self._format_message(message, context, extra)
        self._logger.warning(formatted, extra=extra_dict or None)

    def error(
        self,
        message: str,
        context: LogContext | None = None,
        extra: dict[str, object] | None = None,
    ) -> None:
        """Log an error message.

        Args:
            message: The log message.
            context: Optional LogContext.
            extra: Optional additional fields.
        """
        formatted, extra_dict = self._format_message(message, context, extra)
        self._logger.error(formatted, extra=extra_dict or None)

    def exception(
        self,
        message: str,
        context: LogContext | None = None,
        extra: dict[str, object] | None = None,
    ) -> None:
        """Log an exception with full stack trace.

        Args:
            message: The log message.
            context: Optional LogContext.
            extra: Optional additional fields.
        """
        formatted, extra_dict = self._format_message(message, context, extra)

        self._logger.error(formatted, exc_info=True, extra=extra_dict or None)
