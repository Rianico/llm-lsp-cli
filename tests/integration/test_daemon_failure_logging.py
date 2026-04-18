"""Integration tests for daemon failure logging."""

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestDaemonFailureLogging:
    """Tests for daemon failure error output."""

    def test_cli_error_output_format(self):
        """Test that CLI prints failure message with log path to stderr.

        Note: Full end-to-end testing requires actual daemon infrastructure.
        This test verifies the exception formatting includes log_file.
        """
        from llm_lsp_cli.exceptions import DaemonStartupError

        # Verify that exceptions include log_file attribute
        error = DaemonStartupError(
            "Test error",
            workspace="/test",
            language="python",
            log_file="/tmp/test.log",
        )
        assert error.log_file == "/tmp/test.log"
        assert "(log: /tmp/test.log)" in str(error)


class TestDaemonClientErrorPaths:
    """Tests for DaemonClient error paths."""

    @pytest.mark.asyncio
    async def test_daemon_client_timeout_includes_log_file(self):
        """Test that DaemonClient timeout error includes log_file."""
        from llm_lsp_cli.daemon_client import DaemonClient
        from llm_lsp_cli.exceptions import DaemonStartupTimeoutError

        client = DaemonClient(
            workspace_path="/tmp/test_workspace",
            language="python",
            startup_timeout=0.01,  # Very short timeout for testing
        )

        # Wait for socket should timeout and include log_file
        with pytest.raises(DaemonStartupTimeoutError) as exc_info:
            await client._wait_for_socket()

        error = exc_info.value
        assert error.log_file is not None
        assert "(log:" in str(error)
