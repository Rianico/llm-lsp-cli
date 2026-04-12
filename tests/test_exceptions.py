"""Unit tests for exception hierarchy."""

from llm_lsp_cli.exceptions import (
    DaemonCrashedError,
    DaemonError,
    DaemonStartupError,
    DaemonStartupTimeoutError,
)


class TestDaemonErrorBase:
    """Tests for the base DaemonError exception."""

    def test_daemon_error_base_message(self):
        """DaemonError formats message with workspace/language context."""
        error = DaemonError(
            "Test error message",
            workspace="/test/workspace",
            language="python",
        )

        assert "Test error message" in str(error)
        assert "workspace='/test/workspace'" in str(error)
        assert "language='python'" in str(error)

    def test_daemon_error_optional_context(self):
        """Exceptions work without workspace/language."""
        error = DaemonError("Simple error")

        assert "Simple error" in str(error)
        # Should not crash when optional fields are None
        assert error.workspace is None
        assert error.language is None

    def test_daemon_error_workspace_only(self):
        """DaemonError with only workspace context."""
        error = DaemonError("Error", workspace="/test")

        assert "workspace='/test'" in str(error)
        assert "language" not in str(error)

    def test_daemon_error_language_only(self):
        """DaemonError with only language context."""
        error = DaemonError("Error", language="typescript")

        assert "language='typescript'" in str(error)
        assert "workspace" not in str(error)


class TestDaemonStartupError:
    """Tests for DaemonStartupError exception."""

    def test_daemon_startup_error_inherits_from_daemon_error(self):
        """DaemonStartupError inherits from DaemonError."""
        error = DaemonStartupError("Startup failed", workspace="/test", language="python")

        assert isinstance(error, DaemonError)
        assert isinstance(error, Exception)
        assert "Startup failed" in str(error)


class TestDaemonStartupTimeoutError:
    """Tests for DaemonStartupTimeoutError exception."""

    def test_daemon_startup_timeout_error_message(self):
        """Timeout error includes socket path and timeout duration."""
        error = DaemonStartupTimeoutError(
            socket_path="/tmp/test.sock",
            timeout=10.0,
            workspace="/test",
            language="python",
        )

        assert "10.0" in str(error)
        assert "/tmp/test.sock" in str(error)
        assert "timed out" in str(error)

    def test_daemon_startup_timeout_error_inherits_from_daemon_error(self):
        """DaemonStartupTimeoutError inherits from DaemonError."""
        error = DaemonStartupTimeoutError(
            socket_path="/tmp/test.sock",
            timeout=5.0,
        )

        assert isinstance(error, DaemonError)


class TestDaemonCrashedError:
    """Tests for DaemonCrashedError exception."""

    def test_daemon_crashed_error_message(self):
        """Crashed error includes socket path."""
        error = DaemonCrashedError(
            socket_path="/tmp/crashed.sock",
            workspace="/test",
            language="rust",
        )

        assert "/tmp/crashed.sock" in str(error)
        assert "crashed" in str(error).lower()

    def test_daemon_crashed_error_inherits_from_daemon_error(self):
        """DaemonCrashedError inherits from DaemonError."""
        error = DaemonCrashedError(socket_path="/tmp/test.sock")

        assert isinstance(error, DaemonError)
