"""Tests for LSPLogger."""

import dataclasses
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from llm_lsp_cli.infrastructure.logging import (
    LogComponent,
    LogEntry,
    LogLevel,
    LSPLogger,
)


class TestLoggerLevelFiltering:
    """Test logger level filtering behavior."""

    def test_logger_respects_min_level(self, mock_logger: MagicMock) -> None:
        """Verify messages below min_level are not logged."""
        logger = LSPLogger(min_level=LogLevel.ERROR, logger=mock_logger)

        # Should not log INFO when min is ERROR
        logger.info("Test message")

        mock_logger.info.assert_not_called()

    def test_logger_passes_through_above_min_level(self, mock_logger: MagicMock) -> None:
        """Verify messages at or above min_level are logged."""
        logger = LSPLogger(min_level=LogLevel.INFO, logger=mock_logger)

        # Should log ERROR when min is INFO
        logger.error("Test error")

        mock_logger.info.assert_called_once()


class TestLoggerMethods:
    """Test logger convenience methods."""

    def test_trace_lsp_message(self, mock_logger: MagicMock, lsp_message: dict) -> None:
        """Verify trace_lsp_message formats and logs correctly."""
        logger = LSPLogger(min_level=LogLevel.TRACE, logger=mock_logger)

        logger.trace_lsp_message("→", lsp_message)

        mock_logger.info.assert_called_once()
        called_args = mock_logger.info.call_args[0][0]
        assert "textDocument/definition" in called_args
        assert "→" in called_args

    def test_success_logs_with_green_color(self, mock_logger: MagicMock) -> None:
        """Verify success() method logs with SUCCESS level."""
        logger = LSPLogger(min_level=LogLevel.SUCCESS, logger=mock_logger)

        logger.success("Operation completed")

        mock_logger.info.assert_called_once()
        called_args = mock_logger.info.call_args[0][0]
        assert "Operation completed" in called_args
        assert "SUCCESS" in called_args

    def test_error_logs_with_red_color(self, mock_logger: MagicMock) -> None:
        """Verify error() method logs with ERROR level."""
        logger = LSPLogger(min_level=LogLevel.ERROR, logger=mock_logger)

        logger.error("Operation failed")

        mock_logger.info.assert_called_once()
        called_args = mock_logger.info.call_args[0][0]
        assert "Operation failed" in called_args
        assert "ERROR" in called_args

    def test_debug_event_logs_daemon_events(self, mock_logger: MagicMock) -> None:
        """Verify debug_event() logs with DAEMON component."""
        logger = LSPLogger(min_level=LogLevel.DEBUG, logger=mock_logger)

        logger.debug_event("state_change", state="pending")

        mock_logger.info.assert_called_once()
        called_args = mock_logger.info.call_args[0][0]
        assert "state_change" in called_args
        assert "[daemon]" in called_args

    def test_info_logs_with_client_component(self, mock_logger: MagicMock) -> None:
        """Verify info() logs with CLIENT component."""
        logger = LSPLogger(min_level=LogLevel.INFO, logger=mock_logger)

        logger.info("Starting operation")

        mock_logger.info.assert_called_once()
        called_args = mock_logger.info.call_args[0][0]
        assert "Starting operation" in called_args
        assert "[client]" in called_args

    def test_multiple_calls_accumulate(self, mock_logger: MagicMock) -> None:
        """Verify multiple log calls accumulate."""
        logger = LSPLogger(min_level=LogLevel.INFO, logger=mock_logger)

        logger.info("First message")
        logger.error("Second message")

        assert mock_logger.info.call_count == 2


class TestLogEntry:
    """Test LogEntry dataclass."""

    def test_log_entry_is_immutable(self) -> None:
        """Verify LogEntry frozen dataclass cannot be modified."""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            component=LogComponent.CLIENT,
            message="Test",
        )

        with pytest.raises(dataclasses.FrozenInstanceError):
            entry.message = "Modified"  # type: ignore[attr-defined]

    def test_log_entry_to_dict(self) -> None:
        """Verify LogEntry serializes to dictionary correctly."""
        entry = LogEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            level=LogLevel.INFO,
            component=LogComponent.CLIENT,
            message="Test",
            metadata={"key": "value"},
        )

        data = entry.to_dict()

        assert data["timestamp"] == "2024-01-01T12:00:00"
        assert data["level"] == "INFO"
        assert data["component"] == "client"
        assert data["message"] == "Test"
        assert data["metadata"] == {"key": "value"}


class TestLoggerColorDetection:
    """Test logger color detection."""

    def test_logger_auto_detects_colors(self) -> None:
        """Verify logger auto-detects color support when use_colors=None."""
        LSPLogger(use_colors=None)
        # Should work without error

    def test_logger_explicit_use_colors_false_disables(
        self, mock_non_tty_stdout: None, mock_logger: MagicMock
    ) -> None:
        """Verify explicit use_colors=False disables colors."""
        logger = LSPLogger(use_colors=False, logger=mock_logger)
        logger.info("Test message")

        # Verify no color codes in output
        called_args = mock_logger.info.call_args[0][0]
        assert "\033" not in called_args
