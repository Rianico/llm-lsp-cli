"""Tests for daemon health check ping."""

from pathlib import Path

from llm_lsp_cli.ipc.models import PingResult


class TestHealthCheckPing:
    """Test ping method returns health status."""

    def test_ping_result_has_daemon_field(self) -> None:
        """PingResult should have daemon health field."""
        result = PingResult(status="healthy", daemon=True, lsp_server=True)
        assert result.daemon is True

    def test_ping_result_has_lsp_server_field(self) -> None:
        """PingResult should have lsp_server health field."""
        result = PingResult(status="healthy", daemon=True, lsp_server=False)
        assert result.lsp_server is False

    def test_ping_result_healthy(self) -> None:
        """Healthy ping should have status='healthy'."""
        result = PingResult(status="healthy", daemon=True, lsp_server=True)
        assert result.status == "healthy"

    def test_ping_result_unhealthy_daemon(self) -> None:
        """Unhealthy daemon should have daemon=False."""
        result = PingResult(status="unhealthy", daemon=False, lsp_server=False)
        assert result.daemon is False

    def test_ping_result_unhealthy_lsp(self) -> None:
        """Unhealthy LSP should have lsp_server=False."""
        result = PingResult(status="unhealthy", daemon=True, lsp_server=False)
        assert result.lsp_server is False
