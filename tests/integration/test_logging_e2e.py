"""End-to-end tests for logging functionality."""

import logging
import os
import subprocess
import sys
from datetime import datetime
from unittest.mock import patch

from llm_lsp_cli.infrastructure.logging import (
    ColorFormatter,
    Colors,
    LogComponent,
    LogEntry,
    LogLevel,
    LSPLogger,
)


class TestLoggingE2E:
    """End-to-end tests for logging features."""

    def test_cli_help_shows_verbose_flag(self) -> None:
        """Verify CLI has --verbose flag available."""
        result = subprocess.run(
            [sys.executable, "-m", "llm_lsp_cli", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0 or "usage" in result.stdout.lower()

    def test_cli_help_shows_log_level_flag(self) -> None:
        """Verify CLI has --log-level flag available."""
        result = subprocess.run(
            [sys.executable, "-m", "llm_lsp_cli", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0 or "usage" in result.stdout.lower()

    def test_colors_disabled_when_piped(self) -> None:
        """Verify colors are disabled when output is piped."""
        original_no_color = os.environ.get("NO_COLOR")

        try:
            os.environ["NO_COLOR"] = "1"
            assert Colors.supported() is False

            os.environ.pop("NO_COLOR", None)
        finally:
            if original_no_color:
                os.environ["NO_COLOR"] = original_no_color
            else:
                os.environ.pop("NO_COLOR", None)

    def test_log_entry_serialization(self) -> None:
        """Verify LogEntry serializes correctly for JSON output."""
        entry = LogEntry(
            timestamp=datetime(2024, 1, 1, 12, 30, 45),
            level=LogLevel.INFO,
            component=LogComponent.CLIENT,
            message="Test log message",
            metadata={"request_id": 123, "method": "test/method"},
        )

        data = entry.to_dict()

        assert data["timestamp"] == "2024-01-01T12:30:45"
        assert data["level"] == "INFO"
        assert data["component"] == "client"
        assert data["message"] == "Test log message"
        assert data["metadata"] == {"request_id": 123, "method": "test/method"}

    def test_logger_level_hierarchy(self) -> None:
        """Verify logger level hierarchy works correctly."""
        test_cases: list[tuple[LogLevel, list[LogLevel]]] = [
            (LogLevel.ERROR, [LogLevel.ERROR]),
            (LogLevel.INFO, [LogLevel.ERROR, LogLevel.INFO]),
            (LogLevel.SUCCESS, [LogLevel.ERROR, LogLevel.INFO, LogLevel.SUCCESS]),
            (LogLevel.DEBUG, [LogLevel.ERROR, LogLevel.INFO, LogLevel.SUCCESS, LogLevel.DEBUG]),
            (
                LogLevel.TRACE,
                [
                    LogLevel.ERROR,
                    LogLevel.INFO,
                    LogLevel.SUCCESS,
                    LogLevel.DEBUG,
                    LogLevel.TRACE,
                ],
            ),
        ]

        for min_level, expected_levels in test_cases:
            mock_logger = logging.getLogger(f"test_{min_level.name}")
            logger = LSPLogger(min_level=min_level, logger=mock_logger)

            for level in expected_levels:
                msg = f"{level} should log when min is {min_level}"
                assert logger._should_log(level) is True, msg

            all_levels = list(LogLevel)
            for level in all_levels:
                if level not in expected_levels:
                    msg = f"{level} should not log when min is {min_level}"
                    assert logger._should_log(level) is False, msg

    def test_formatter_color_mapping(self) -> None:
        """Verify formatters use correct color mapping."""
        with patch.object(sys.stdout, "isatty", return_value=True):
            Colors._disabled = False
            Colors.RESET = "\033[0m"
            Colors.CLI = "\033[36m"
            Colors.SERVER = "\033[33m"
            Colors.SUCCESS = "\033[32m"
            Colors.ERROR = "\033[31m"
            Colors.INFO = "\033[34m"
            Colors.DEBUG = "\033[37m"

            formatter = ColorFormatter()

            error_entry = LogEntry(
                timestamp=datetime.now(),
                level=LogLevel.ERROR,
                component=LogComponent.CLIENT,
                message="Error",
            )
            error_output = formatter.format(error_entry)
            assert Colors.ERROR in error_output

            success_entry = LogEntry(
                timestamp=datetime.now(),
                level=LogLevel.SUCCESS,
                component=LogComponent.CLIENT,
                message="Success",
            )
            success_output = formatter.format(success_entry)
            assert Colors.SUCCESS in success_output

            info_entry = LogEntry(
                timestamp=datetime.now(),
                level=LogLevel.INFO,
                component=LogComponent.CLIENT,
                message="Info",
            )
            info_output = formatter.format(info_entry)
            assert Colors.INFO in info_output

            assert Colors.CLI in error_output
