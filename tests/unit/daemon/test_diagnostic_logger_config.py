"""Tests for diagnostic logger configuration in daemon.py.

Verifies the _configure_diagnostic_logger() function configures the logger
correctly per ADR-0009.
"""

import logging
import os
import sys
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def reset_diagnostic_logger() -> Generator[None, None, None]:
    """Reset diagnostic logger before and after each test."""
    logger_name = "llm_lsp_cli.lsp.diagnostic"
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    logger.propagate = True
    yield
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    logger.propagate = True


class TestConfigureDiagnosticLogger:
    """Tests for _configure_diagnostic_logger() function."""

    def test_creates_file_handler(self, tmp_path: Path) -> None:
        """_configure_diagnostic_logger creates a FileHandler."""
        from llm_lsp_cli.daemon import _configure_diagnostic_logger

        log_path = tmp_path / "diagnostics.log"
        _configure_diagnostic_logger(log_path)

        logger = logging.getLogger("llm_lsp_cli.lsp.diagnostic")
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.FileHandler)

    def test_sets_propagate_false(self, tmp_path: Path) -> None:
        """Diagnostic logger has propagate=False to prevent duplicate logging."""
        from llm_lsp_cli.daemon import _configure_diagnostic_logger

        log_path = tmp_path / "diagnostics.log"
        _configure_diagnostic_logger(log_path)

        logger = logging.getLogger("llm_lsp_cli.lsp.diagnostic")
        assert logger.propagate is False

    def test_sets_debug_level(self, tmp_path: Path) -> None:
        """Diagnostic logger level is set to DEBUG."""
        from llm_lsp_cli.daemon import _configure_diagnostic_logger

        log_path = tmp_path / "diagnostics.log"
        _configure_diagnostic_logger(log_path)

        logger = logging.getLogger("llm_lsp_cli.lsp.diagnostic")
        assert logger.level == logging.DEBUG

    def test_handler_level_is_debug(self, tmp_path: Path) -> None:
        """FileHandler level is set to DEBUG."""
        from llm_lsp_cli.daemon import _configure_diagnostic_logger

        log_path = tmp_path / "diagnostics.log"
        _configure_diagnostic_logger(log_path)

        logger = logging.getLogger("llm_lsp_cli.lsp.diagnostic")
        assert logger.handlers[0].level == logging.DEBUG

    @pytest.mark.skipif(
        sys.platform == "win32", reason="POSIX permissions not applicable on Windows"
    )
    def test_file_permissions_restrictive(self, tmp_path: Path) -> None:
        """Diagnostic log file has restrictive permissions (0o600)."""
        from llm_lsp_cli.daemon import _configure_diagnostic_logger

        log_path = tmp_path / "diagnostics.log"
        _configure_diagnostic_logger(log_path)

        # Check file permissions
        file_stat = os.stat(log_path)
        file_mode = file_stat.st_mode & 0o777
        assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"

    def test_writes_to_correct_file(self, tmp_path: Path) -> None:
        """Diagnostic logger writes to the specified file."""
        from llm_lsp_cli.daemon import _configure_diagnostic_logger

        log_path = tmp_path / "diagnostics.log"
        _configure_diagnostic_logger(log_path)

        logger = logging.getLogger("llm_lsp_cli.lsp.diagnostic")
        logger.debug("Test diagnostic message")

        # Force flush
        for handler in logger.handlers:
            handler.flush()

        assert log_path.exists()
        content = log_path.read_text()
        assert "Test diagnostic message" in content

    def test_parent_directory_created(self, tmp_path: Path) -> None:
        """Parent directory is created if it doesn't exist."""
        from llm_lsp_cli.daemon import _configure_diagnostic_logger

        log_path = tmp_path / "nested" / "dir" / "diagnostics.log"
        assert not log_path.parent.exists()

        _configure_diagnostic_logger(log_path)

        assert log_path.parent.exists()

    def test_logger_name_is_correct(self, tmp_path: Path) -> None:
        """Diagnostic logger uses correct name."""
        from llm_lsp_cli.daemon import _configure_diagnostic_logger

        log_path = tmp_path / "diagnostics.log"
        _configure_diagnostic_logger(log_path)

        logger = logging.getLogger("llm_lsp_cli.lsp.diagnostic")
        assert logger.name == "llm_lsp_cli.lsp.diagnostic"


class TestDiagnosticLoggerIsolation:
    """Tests for diagnostic logger isolation from main logger."""

    def test_no_propagation_to_parent(self, tmp_path: Path) -> None:
        """Diagnostic logger does not propagate to parent loggers."""
        from llm_lsp_cli.daemon import _configure_diagnostic_logger

        log_path = tmp_path / "diagnostics.log"
        _configure_diagnostic_logger(log_path)

        logger = logging.getLogger("llm_lsp_cli.lsp.diagnostic")
        assert logger.propagate is False

    def test_separate_from_transport_logger(self, tmp_path: Path) -> None:
        """Diagnostic logger is separate from transport logger."""
        from llm_lsp_cli.daemon import _configure_diagnostic_logger

        log_path = tmp_path / "diagnostics.log"
        _configure_diagnostic_logger(log_path)

        diagnostic_logger = logging.getLogger("llm_lsp_cli.lsp.diagnostic")
        transport_logger = logging.getLogger("llm_lsp_cli.lsp.transport")

        # Should be different logger instances
        assert diagnostic_logger is not transport_logger
        # Should have different handlers
        assert diagnostic_logger.handlers != transport_logger.handlers
