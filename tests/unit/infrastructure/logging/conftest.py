"""Fixtures for logging tests."""

import logging
import sys
from collections.abc import Generator
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from llm_lsp_cli.domain.value_objects import LogLevel
from llm_lsp_cli.infrastructure.logging import (
    Colors,
    LogComponent,
    LogEntry,
)


@pytest.fixture(autouse=True)
def reset_colors_state() -> Generator[None, None, None]:
    """Reset Colors state before and after each test."""
    # Save state
    saved_disabled = Colors._disabled
    saved_reset = Colors.RESET
    saved_cli = Colors.CLI
    saved_server = Colors.SERVER
    saved_success = Colors.SUCCESS
    saved_error = Colors.ERROR
    saved_info = Colors.INFO
    saved_debug = Colors.DEBUG

    # Reset to default
    Colors._disabled = False
    Colors.RESET = "\033[0m"
    Colors.CLI = "\033[36m"
    Colors.SERVER = "\033[33m"
    Colors.SUCCESS = "\033[32m"
    Colors.ERROR = "\033[31m"
    Colors.INFO = "\033[34m"
    Colors.DEBUG = "\033[37m"

    yield

    # Restore state
    Colors._disabled = saved_disabled
    Colors.RESET = saved_reset
    Colors.CLI = saved_cli
    Colors.SERVER = saved_server
    Colors.SUCCESS = saved_success
    Colors.ERROR = saved_error
    Colors.INFO = saved_info
    Colors.DEBUG = saved_debug


@pytest.fixture
def log_entry() -> LogEntry:
    """Standard LogEntry for formatter tests."""
    return LogEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        level=LogLevel.INFO,
        component=LogComponent.CLIENT,
        message="Test message",
    )


@pytest.fixture
def error_log_entry() -> LogEntry:
    """LogEntry with ERROR level."""
    return LogEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        level=LogLevel.ERROR,
        component=LogComponent.CLIENT,
        message="Error occurred",
    )


@pytest.fixture
def success_log_entry() -> LogEntry:
    """LogEntry with SUCCESS level."""
    return LogEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        level=LogLevel.SUCCESS,
        component=LogComponent.CLIENT,
        message="Operation completed",
    )


@pytest.fixture
def lsp_message() -> dict:
    """Sample LSP message for trace formatting."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "textDocument/definition",
        "params": {
            "textDocument": {"uri": "file:///test.py"},
            "position": {"line": 0, "character": 0},
        },
    }


@pytest.fixture
def mock_tty_stdout() -> Generator[None, None, None]:
    """Mock sys.stdout as TTY."""
    with patch.object(sys.stdout, "isatty", return_value=True):
        yield


@pytest.fixture
def mock_non_tty_stdout() -> Generator[None, None, None]:
    """Mock sys.stdout as non-TTY (pipe)."""
    with patch.object(sys.stdout, "isatty", return_value=False):
        yield


@pytest.fixture
def mock_logger() -> MagicMock:
    """Mock stdlib logger for testing LSPLogger."""
    return MagicMock(spec=logging.Logger)
