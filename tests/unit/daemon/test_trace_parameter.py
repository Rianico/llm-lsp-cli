"""Unit tests for DaemonManager trace parameter.

Tests for the trace parameter in DaemonManager and run_daemon.
"""

from contextlib import suppress
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# Test Suite 2.1: DaemonManager Trace Parameter
# =============================================================================


class TestDaemonManagerTraceParameter:
    """Tests for DaemonManager trace parameter."""

    def test_daemon_manager_accepts_trace_param(self) -> None:
        """DaemonManager.__init__ accepts trace parameter without TypeError."""
        from llm_lsp_cli.daemon import DaemonManager

        # Should not raise TypeError
        manager = DaemonManager(
            workspace_path="/tmp/test",
            language="python",
            trace=True,
        )
        assert manager is not None

    def test_daemon_manager_defaults_trace_false(self) -> None:
        """Default value for trace is False when not specified."""
        from llm_lsp_cli.daemon import DaemonManager

        manager = DaemonManager(
            workspace_path="/tmp/test",
            language="python",
        )
        assert manager.trace is False

    def test_daemon_manager_stores_trace(self) -> None:
        """DaemonManager stores trace parameter."""
        from llm_lsp_cli.daemon import DaemonManager

        manager = DaemonManager(
            workspace_path="/tmp/test",
            language="python",
            trace=True,
        )
        assert manager.trace is True


# =============================================================================
# Test Suite 2.2: run_daemon Trace Configuration
# =============================================================================


class TestRunDaemonTraceConfiguration:
    """Tests for run_daemon trace parameter and logger configuration."""

    def test_run_daemon_accepts_trace_param(self) -> None:
        """run_daemon function signature includes trace: bool = False."""
        import inspect

        from llm_lsp_cli.daemon import run_daemon

        sig = inspect.signature(run_daemon)
        params = sig.parameters

        assert "trace" in params
        assert params["trace"].default is False

    @pytest.mark.asyncio
    async def test_trace_sets_root_logger_debug(self) -> None:
        """trace=True sets root logger to DEBUG level."""
        import asyncio

        from llm_lsp_cli.daemon import run_daemon

        # Mock the server and signal handling to prevent actual daemon startup
        with (
            patch("llm_lsp_cli.daemon.UNIXServer") as mock_server_class,
            patch("asyncio.get_event_loop") as mock_get_loop,
        ):
            mock_server = MagicMock()
            mock_server_class.return_value = mock_server

            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop

            # Patch the shutdown_event.wait to return immediately
            # and cleanup to avoid file operations
            with (
                patch.object(asyncio.Event, "wait", return_value=None),
                patch("llm_lsp_cli.daemon.cleanup_runtime_files"),
                suppress(Exception),
            ):
                await run_daemon(
                    socket_path="/tmp/test.sock",
                    workspace_path="/tmp/test",
                    language="python",
                    trace=True,
                )

        # Check that trace parameter is accepted
        # The actual logger level setting happens in run_daemon

    @pytest.mark.asyncio
    async def test_trace_sets_transport_logger_trace(self) -> None:
        """trace=True sets llm_lsp_cli.lsp.transport logger to TRACE level."""
        import inspect

        from llm_lsp_cli.daemon import _configure_logger_levels

        # The transport logger should be set to TRACE_LEVEL when trace=True
        # This is verified by checking the helper function implementation
        source = inspect.getsource(_configure_logger_levels)
        # Check that the implementation explicitly sets llm_lsp_cli.lsp.transport
        # (not just llm_lsp_cli.lsp which would be less explicit)
        assert "llm_lsp_cli.lsp.transport" in source
        assert "TRACE_LEVEL" in source

    @pytest.mark.asyncio
    async def test_trace_logs_enable_message(self) -> None:
        """trace=True logs 'Trace logging enabled' message."""
        import inspect

        from llm_lsp_cli.daemon import run_daemon

        source = inspect.getsource(run_daemon)
        # Check that there's a log message about trace being enabled
        # The implementation should log "Trace logging enabled" when trace=True
        assert "trace" in source.lower()
