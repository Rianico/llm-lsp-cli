"""Unit tests for exception classes with log_file support."""

from llm_lsp_cli.exceptions import (
    DaemonCrashedError,
    DaemonError,
    DaemonStartupError,
    DaemonStartupTimeoutError,
)


class TestDaemonError:
    """Tests for DaemonError base class."""

    def test_basic_error_without_log_file(self):
        """Test DaemonError without log_file parameter."""
        error = DaemonError("Test error")
        assert error.message == "Test error"
        assert error.log_file is None
        assert str(error) == "Test error"

    def test_error_with_workspace_and_language(self):
        """Test DaemonError with workspace and language context."""
        error = DaemonError(
            "Test error",
            workspace="/path/to/workspace",
            language="python",
        )
        assert error.workspace == "/path/to/workspace"
        assert error.language == "python"
        assert error.log_file is None
        assert "workspace='/path/to/workspace'" in str(error)
        assert "language='python'" in str(error)

    def test_error_with_log_file(self):
        """Test DaemonError with log_file parameter."""
        error = DaemonError(
            "Test error",
            log_file="/path/to/log.txt",
        )
        assert error.log_file == "/path/to/log.txt"
        assert "(log: /path/to/log.txt)" in str(error)

    def test_error_with_all_context(self):
        """Test DaemonError with all context parameters."""
        error = DaemonError(
            "Test error",
            workspace="/path/to/workspace",
            language="python",
            log_file="/path/to/log.txt",
        )
        error_str = str(error)
        assert "workspace='/path/to/workspace'" in error_str
        assert "language='python'" in error_str
        assert "(log: /path/to/log.txt)" in error_str


class TestDaemonStartupError:
    """Tests for DaemonStartupError."""

    def test_startup_error_with_log_file(self):
        """Test DaemonStartupError includes log_file in message."""
        error = DaemonStartupError(
            "Failed to spawn daemon",
            workspace="/path/to/workspace",
            language="python",
            log_file="/path/to/log.txt",
        )
        error_str = str(error)
        assert "Failed to spawn daemon" in error_str
        assert "workspace='/path/to/workspace'" in error_str
        assert "language='python'" in error_str
        assert "(log: /path/to/log.txt)" in error_str


class TestDaemonStartupTimeoutError:
    """Tests for DaemonStartupTimeoutError."""

    def test_timeout_error_with_log_file(self):
        """Test DaemonStartupTimeoutError includes log_file in message."""
        error = DaemonStartupTimeoutError(
            socket_path="/tmp/test.sock",
            timeout=10.0,
            workspace="/path/to/workspace",
            language="python",
            log_file="/path/to/log.txt",
        )
        error_str = str(error)
        assert "timed out after 10.0s" in error_str
        assert "socket: /tmp/test.sock" in error_str
        assert "workspace='/path/to/workspace'" in error_str
        assert "language='python'" in error_str
        assert "(log: /path/to/log.txt)" in error_str

    def test_timeout_error_without_log_file(self):
        """Test DaemonStartupTimeoutError without log_file."""
        error = DaemonStartupTimeoutError(
            socket_path="/tmp/test.sock",
            timeout=10.0,
        )
        error_str = str(error)
        assert "(log:" not in error_str


class TestDaemonCrashedError:
    """Tests for DaemonCrashedError."""

    def test_crashed_error_with_log_file(self):
        """Test DaemonCrashedError includes log_file in message."""
        error = DaemonCrashedError(
            socket_path="/tmp/test.sock",
            workspace="/path/to/workspace",
            language="python",
            log_file="/path/to/log.txt",
        )
        error_str = str(error)
        assert "crashed" in error_str
        assert "socket: /tmp/test.sock" in error_str
        assert "workspace='/path/to/workspace'" in error_str
        assert "language='python'" in error_str
        assert "(log: /path/to/log.txt)" in error_str

    def test_crashed_error_without_log_file(self):
        """Test DaemonCrashedError without log_file."""
        error = DaemonCrashedError(
            socket_path="/tmp/test.sock",
        )
        error_str = str(error)
        assert "(log:" not in error_str
