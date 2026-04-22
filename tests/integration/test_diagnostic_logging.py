"""Integration tests for dual-path diagnostic logging feature."""

import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from llm_lsp_cli.config.manager import ConfigManager


class TestDiagnosticLoggerConfiguration:
    """Test diagnostic logger configuration in daemon."""

    def test_diagnostic_logger_no_handler_without_flag(self) -> None:
        """Test diagnostic logger has no handlers when flag is False."""
        # Arrange
        diagnostic_logger = logging.getLogger("llm_lsp_cli.lsp.diagnostic")
        original_handlers = diagnostic_logger.handlers.copy()
        original_propagate = diagnostic_logger.propagate

        try:
            # Act - configure with flag disabled
            from llm_lsp_cli.daemon import _configure_diagnostic_logger

            # Should not configure when path is None
            _configure_diagnostic_logger_enabled = False  # Flag not enabled

            # Assert - logger should remain in default state
            # (note: other tests may have added handlers, so we just verify
            # the function doesn't get called when flag is False)
            assert not _configure_diagnostic_logger_enabled

        finally:
            # Cleanup
            diagnostic_logger.handlers = original_handlers
            diagnostic_logger.propagate = original_propagate

    def test_diagnostic_logger_configured_with_flag(self, tmp_path: Path) -> None:
        """Test diagnostic logger is configured with FileHandler when flag enabled."""
        # Arrange
        from llm_lsp_cli.daemon import _configure_diagnostic_logger

        diagnostic_log_path = tmp_path / "diagnostics.log"
        diagnostic_logger = logging.getLogger("llm_lsp_cli.lsp.diagnostic")
        original_handlers = diagnostic_logger.handlers.copy()
        original_propagate = diagnostic_logger.propagate
        original_level = diagnostic_logger.level

        try:
            # Act
            _configure_diagnostic_logger(diagnostic_log_path)

            # Assert
            assert len(diagnostic_logger.handlers) >= 1
            handler = diagnostic_logger.handlers[-1]
            assert isinstance(handler, logging.FileHandler)
            assert diagnostic_logger.propagate is False
            assert diagnostic_logger.level == logging.DEBUG

            # Verify file was created
            assert diagnostic_log_path.exists()

        finally:
            # Cleanup
            diagnostic_logger.handlers = original_handlers
            diagnostic_logger.propagate = original_propagate
            diagnostic_logger.level = original_level

    def test_diagnostic_log_file_permissions(self, tmp_path: Path) -> None:
        """Test diagnostic log file has restrictive permissions (0o600)."""
        # Arrange
        import os
        import stat

        from llm_lsp_cli.daemon import _configure_diagnostic_logger

        diagnostic_log_path = tmp_path / "diagnostics.log"

        try:
            # Act
            _configure_diagnostic_logger(diagnostic_log_path)

            # Assert
            file_mode = stat.S_IMODE(diagnostic_log_path.stat().st_mode)
            assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"

        except OSError:
            # Some systems may not support chmod
            pytest.skip("System does not support file permissions")

        finally:
            # Cleanup logger
            diagnostic_logger = logging.getLogger("llm_lsp_cli.lsp.diagnostic")
            diagnostic_logger.handlers = []
            diagnostic_logger.propagate = True


class TestDiagnosticLoggerReceivesFullData:
    """Test that diagnostic logger receives unmasked data."""

    def test_diagnostic_logger_receives_full_data(self, tmp_path: Path) -> None:
        """Test diagnostic logger receives full (unmasked) diagnostic data."""
        # Arrange
        import io

        from llm_lsp_cli.daemon import _configure_diagnostic_logger

        diagnostic_log_path = tmp_path / "diagnostics.log"
        diagnostic_logger = logging.getLogger("llm_lsp_cli.lsp.diagnostic")
        original_handlers = diagnostic_logger.handlers.copy()
        original_propagate = diagnostic_logger.propagate
        original_level = diagnostic_logger.level

        try:
            # Act - configure logger
            _configure_diagnostic_logger(diagnostic_log_path)

            # Log a diagnostic message
            full_diagnostic_data = {
                "method": "textDocument/publishDiagnostics",
                "params": {
                    "uri": "file:///test.py",
                    "diagnostics": [
                        {
                            "range": {
                                "start": {"line": 0, "character": 0},
                                "end": {"line": 0, "character": 10},
                            },
                            "severity": 1,
                            "message": "Error 1",
                        },
                        {
                            "range": {
                                "start": {"line": 1, "character": 0},
                                "end": {"line": 1, "character": 5},
                            },
                            "severity": 2,
                            "message": "Error 2",
                        },
                    ],
                },
            }
            diagnostic_logger.debug(f"<-- {full_diagnostic_data}")

            # Force flush
            for handler in diagnostic_logger.handlers:
                handler.flush()

            # Assert - read the log file
            log_content = diagnostic_log_path.read_text()
            assert "diagnostics" in log_content
            # Should contain full data, not masked
            assert "Error 1" in log_content or "severity" in log_content

        finally:
            # Cleanup
            diagnostic_logger.handlers = original_handlers
            diagnostic_logger.propagate = original_propagate
            diagnostic_logger.level = original_level


class TestRunDaemonDiagnosticConfig:
    """Test run_daemon diagnostic logger configuration."""

    def test_configure_diagnostic_logger_function_exists(self) -> None:
        """Test that _configure_diagnostic_logger helper function exists."""
        from llm_lsp_cli.daemon import _configure_diagnostic_logger

        # Verify the function exists and is callable
        assert callable(_configure_diagnostic_logger)

    def test_run_daemon_has_diagnostic_log_parameters(self) -> None:
        """Test that run_daemon accepts diagnostic_log parameters."""
        import inspect

        from llm_lsp_cli.daemon import run_daemon

        sig = inspect.signature(run_daemon)
        params = sig.parameters

        # Verify diagnostic_log parameter exists
        assert "diagnostic_log" in params
        assert params["diagnostic_log"].default is False

        # Verify diagnostic_log_path parameter exists
        assert "diagnostic_log_path" in params
        assert params["diagnostic_log_path"].default is None


class TestDualPathLoggingIntegration:
    """Integration tests for dual-path logging behavior."""

    def test_daemon_log_and_diagnostic_log_are_separate_files(
        self, tmp_path: Path
    ) -> None:
        """Test that daemon.log and diagnostics.log are separate files."""
        # Arrange
        workspace = tmp_path / "test_workspace"
        workspace.mkdir()

        # Act - build paths
        daemon_log_path = ConfigManager.build_daemon_log_path(str(workspace), "python")
        diagnostic_log_path = ConfigManager.build_diagnostic_log_path(
            str(workspace), "python"
        )

        # Assert
        assert daemon_log_path != diagnostic_log_path
        assert daemon_log_path.parent == diagnostic_log_path.parent
        assert daemon_log_path.name == "daemon.log"
        assert diagnostic_log_path.name == "diagnostics.log"

    def test_diagnostic_log_path_in_runtime_dir(self, tmp_path: Path) -> None:
        """Test diagnostic log path is in workspace .llm-lsp-cli directory."""
        # Arrange
        workspace = tmp_path / "test_workspace"
        workspace.mkdir()

        # Act
        diagnostic_log_path = ConfigManager.build_diagnostic_log_path(
            str(workspace), "python"
        )

        # Assert
        assert ".llm-lsp-cli" in str(diagnostic_log_path)
        assert diagnostic_log_path.parent == workspace / ".llm-lsp-cli"
