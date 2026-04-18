"""Unit tests for DaemonClient auto-start functionality."""

import asyncio
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_lsp_cli.daemon_client import DaemonClient
from llm_lsp_cli.exceptions import (
    DaemonCrashedError,
    DaemonError,
    DaemonStartupError,
    DaemonStartupTimeoutError,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_socket_path() -> MagicMock:
    """Mock socket Path object."""
    mock = MagicMock(spec=Path)
    mock.exists = MagicMock(return_value=True)  # Default to existing
    mock.__str__ = MagicMock(return_value="/tmp/test.sock")
    return mock


@pytest.fixture
def mock_daemon_manager() -> Generator[MagicMock, None, None]:
    """Mock DaemonManager for unit tests."""
    with patch("llm_lsp_cli.daemon_client.DaemonManager") as mock:
        yield mock


@pytest.fixture
def mock_unix_client() -> Generator[MagicMock, None, None]:
    """Mock UNIXClient for unit tests."""
    with patch("llm_lsp_cli.daemon_client.UNIXClient") as mock:
        yield mock


@pytest.fixture
def mock_asyncio_create_subprocess() -> Generator[MagicMock, None, None]:
    """Mock asyncio.create_subprocess_exec for unit tests."""
    with patch("llm_lsp_cli.daemon_client.asyncio.create_subprocess_exec") as mock:
        yield mock


# =============================================================================
# Constructor Tests
# =============================================================================


class TestDaemonClientConstructor:
    """Tests for DaemonClient initialization."""

    @patch("llm_lsp_cli.daemon_client.ConfigManager")
    def test_daemon_client_init_defaults(self, mock_config_manager: MagicMock):
        """Default timeout values are set correctly."""
        mock_config_manager.build_socket_path.return_value = Path("/tmp/test.sock")

        client = DaemonClient(
            workspace_path="/test/workspace",
            language="python",
        )

        assert client.startup_timeout == 10.0
        assert client.connection_timeout == 30.0
        assert client.workspace_path == "/test/workspace"
        assert client.language == "python"

    @patch("llm_lsp_cli.daemon_client.ConfigManager")
    def test_daemon_client_init_custom_timeouts(self, mock_config_manager: MagicMock):
        """Custom timeout configuration is stored correctly."""
        mock_config_manager.build_socket_path.return_value = Path("/tmp/test.sock")

        client = DaemonClient(
            workspace_path="/test",
            language="typescript",
            startup_timeout=5.0,
            connection_timeout=20.0,
        )

        assert client.startup_timeout == 5.0
        assert client.connection_timeout == 20.0

    @patch("llm_lsp_cli.daemon_client.ConfigManager")
    def test_daemon_client_builds_socket_path(self, mock_config_manager: MagicMock):
        """Socket path is computed from workspace/language."""
        mock_config_manager.build_socket_path.return_value = Path("/custom/socket.sock")

        client = DaemonClient(
            workspace_path="/workspace",
            language="rust",
        )

        mock_config_manager.build_socket_path.assert_called_once_with(
            workspace_path="/workspace",
            language="rust",
        )
        assert client.socket_path == Path("/custom/socket.sock")


# =============================================================================
# Auto-Start Behavior Tests
# =============================================================================


class TestDaemonClientAutoStart:
    """Tests for auto-start behavior."""

    @pytest.mark.asyncio
    @patch("llm_lsp_cli.daemon_client.ConfigManager")
    async def test_request_auto_starts_daemon(
        self,
        mock_config_manager: MagicMock,
        mock_daemon_manager: MagicMock,
        mock_unix_client: MagicMock,
        mock_asyncio_create_subprocess: MagicMock,
    ):
        """request() starts daemon if not running."""
        # Setup mock socket path that exists
        mock_socket = MagicMock(spec=Path)
        mock_socket.exists.return_value = True
        mock_socket.__str__ = MagicMock(return_value="/tmp/test.sock")
        mock_config_manager.build_socket_path.return_value = mock_socket

        # Setup: is_running() returns False initially
        mock_manager_instance = MagicMock()
        mock_manager_instance.is_running.return_value = False
        mock_daemon_manager.return_value = mock_manager_instance

        # Mock subprocess - daemon starts successfully
        mock_process = AsyncMock()
        mock_process.returncode = None  # Process is running
        mock_asyncio_create_subprocess.return_value = mock_process

        # Mock UNIXClient
        mock_client_instance = AsyncMock()
        mock_client_instance.request = AsyncMock(return_value={"result": "success"})
        mock_client_instance.close = AsyncMock()
        mock_unix_client.return_value = mock_client_instance

        client = DaemonClient("/workspace", "python")

        # Execute
        result = await client.request("textDocument/definition", {"filePath": "/test.py"})

        # Verify daemon subprocess was spawned
        mock_asyncio_create_subprocess.assert_called_once()
        assert result == {"result": "success"}

    @pytest.mark.asyncio
    @patch("llm_lsp_cli.daemon_client.ConfigManager")
    async def test_request_reuses_running_daemon(
        self,
        mock_config_manager: MagicMock,
        mock_daemon_manager: MagicMock,
        mock_unix_client: MagicMock,
    ):
        """request() skips start if daemon already running."""
        # Setup mock socket path
        mock_socket = MagicMock(spec=Path)
        mock_socket.exists.return_value = True
        mock_socket.__str__ = MagicMock(return_value="/tmp/test.sock")
        mock_config_manager.build_socket_path.return_value = mock_socket

        # Setup: is_running() returns True
        mock_manager_instance = MagicMock()
        mock_manager_instance.is_running.return_value = True
        mock_daemon_manager.return_value = mock_manager_instance

        # Mock UNIXClient
        mock_client_instance = AsyncMock()
        mock_client_instance.request = AsyncMock(return_value={"result": "success"})
        mock_client_instance.close = AsyncMock()
        mock_unix_client.return_value = mock_client_instance

        client = DaemonClient("/workspace", "python")

        # Execute
        result = await client.request("textDocument/definition", {"filePath": "/test.py"})

        # Verify daemon was NOT started
        mock_daemon_manager.return_value.start.assert_not_called()
        assert result == {"result": "success"}

    @pytest.mark.asyncio
    @patch("llm_lsp_cli.daemon_client.ConfigManager")
    async def test_notify_auto_starts_daemon(
        self,
        mock_config_manager: MagicMock,
        mock_daemon_manager: MagicMock,
        mock_unix_client: MagicMock,
        mock_asyncio_create_subprocess: MagicMock,
    ):
        """notify() triggers auto-start if daemon not running."""
        # Setup mock socket path
        mock_socket = MagicMock(spec=Path)
        mock_socket.exists.return_value = True
        mock_socket.__str__ = MagicMock(return_value="/tmp/test.sock")
        mock_config_manager.build_socket_path.return_value = mock_socket

        # Setup: is_running() returns False
        mock_manager_instance = MagicMock()
        mock_manager_instance.is_running.return_value = False
        mock_daemon_manager.return_value = mock_manager_instance

        # Mock subprocess - daemon starts successfully
        mock_process = AsyncMock()
        mock_process.returncode = None  # Process is running
        mock_asyncio_create_subprocess.return_value = mock_process

        # Mock UNIXClient
        mock_client_instance = AsyncMock()
        mock_client_instance.notify = AsyncMock()
        mock_client_instance.close = AsyncMock()
        mock_unix_client.return_value = mock_client_instance

        client = DaemonClient("/workspace", "python")

        # Execute
        await client.notify("textDocument/didOpen", {"filePath": "/test.py"})

        # Verify daemon subprocess was spawned
        mock_asyncio_create_subprocess.assert_called_once()


# =============================================================================
# Timeout & Error Handling Tests
# =============================================================================


class TestDaemonClientTimeoutHandling:
    """Tests for timeout and error handling."""

    @pytest.mark.asyncio
    @patch("llm_lsp_cli.daemon_client.ConfigManager")
    async def test_startup_timeout_raises_error(
        self,
        mock_config_manager: MagicMock,
        mock_daemon_manager: MagicMock,
    ):
        """DaemonStartupTimeoutError raised when socket never appears."""
        # Setup mock socket path that never exists
        mock_socket = MagicMock(spec=Path)
        mock_socket.exists.return_value = False
        mock_socket.__str__ = MagicMock(return_value="/tmp/nonexistent.sock")
        mock_config_manager.build_socket_path.return_value = mock_socket

        # Setup: is_running() returns True but socket never exists
        mock_manager_instance = MagicMock()
        mock_manager_instance.is_running.return_value = True
        mock_daemon_manager.return_value = mock_manager_instance

        client = DaemonClient(
            "/workspace",
            "python",
            startup_timeout=0.15,  # Short timeout for test speed (enough for 2-3 backoff cycles)
        )

        # Execute and verify timeout error
        with pytest.raises(DaemonStartupTimeoutError) as exc_info:
            await client.request("textDocument/definition", {"filePath": "/test.py"})

        assert "timed out" in str(exc_info.value).lower()
        assert "/tmp/nonexistent.sock" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("llm_lsp_cli.daemon_client.ConfigManager")
    async def test_startup_failure_wraps_exception(
        self,
        mock_config_manager: MagicMock,
        mock_daemon_manager: MagicMock,
        mock_asyncio_create_subprocess: MagicMock,
    ):
        """DaemonStartupError raised when subprocess spawn fails."""
        # Setup mock socket path
        mock_socket = MagicMock(spec=Path)
        mock_socket.exists.return_value = True
        mock_socket.__str__ = MagicMock(return_value="/tmp/test.sock")
        mock_config_manager.build_socket_path.return_value = mock_socket

        # Setup: is_running() returns False (needs to start)
        mock_manager_instance = MagicMock()
        mock_manager_instance.is_running.return_value = False
        mock_daemon_manager.return_value = mock_manager_instance

        # Mock subprocess to raise an exception
        mock_asyncio_create_subprocess.side_effect = RuntimeError("Spawn failed")

        client = DaemonClient("/workspace", "python")

        # Execute and verify wrapped exception
        with pytest.raises(DaemonStartupError) as exc_info:
            await client.request("textDocument/definition", {"filePath": "/test.py"})

        assert "Failed to start daemon" in str(exc_info.value)
        assert "workspace='/workspace'" in str(exc_info.value)
        assert "language='python'" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("llm_lsp_cli.daemon_client.ConfigManager")
    async def test_daemon_crashed_after_start(
        self,
        mock_config_manager: MagicMock,
        mock_daemon_manager: MagicMock,
        mock_unix_client: MagicMock,
    ):
        """DaemonCrashedError raised when socket exists but connection fails."""
        # Setup mock socket path
        mock_socket = MagicMock(spec=Path)
        mock_socket.exists.return_value = True
        mock_socket.__str__ = MagicMock(return_value="/tmp/crashed.sock")
        mock_config_manager.build_socket_path.return_value = mock_socket

        # Setup: daemon running, but request raises FileNotFoundError
        mock_manager_instance = MagicMock()
        mock_manager_instance.is_running.return_value = True
        mock_daemon_manager.return_value = mock_manager_instance

        # Mock UNIXClient to raise FileNotFoundError
        mock_client_instance = AsyncMock()
        mock_client_instance.request.side_effect = FileNotFoundError()
        mock_client_instance.close = AsyncMock()
        mock_unix_client.return_value = mock_client_instance

        client = DaemonClient("/workspace", "python")

        # Execute and verify crash error
        with pytest.raises(DaemonCrashedError) as exc_info:
            await client.request("textDocument/definition", {"filePath": "/test.py"})

        assert "crashed" in str(exc_info.value).lower()
        assert "/tmp/crashed.sock" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("llm_lsp_cli.daemon_client.ConfigManager")
    async def test_connection_timeout(
        self,
        mock_config_manager: MagicMock,
        mock_daemon_manager: MagicMock,
        mock_unix_client: MagicMock,
    ):
        """DaemonError raised on request timeout."""
        # Setup mock socket path
        mock_socket = MagicMock(spec=Path)
        mock_socket.exists.return_value = True
        mock_socket.__str__ = MagicMock(return_value="/tmp/test.sock")
        mock_config_manager.build_socket_path.return_value = mock_socket

        # Setup: daemon running, but request times out
        mock_manager_instance = MagicMock()
        mock_manager_instance.is_running.return_value = True
        mock_daemon_manager.return_value = mock_manager_instance

        # Mock UNIXClient to raise TimeoutError
        mock_client_instance = AsyncMock()
        mock_client_instance.request.side_effect = asyncio.TimeoutError()
        mock_client_instance.close = AsyncMock()
        mock_unix_client.return_value = mock_client_instance

        client = DaemonClient("/workspace", "python", connection_timeout=30.0)

        # Execute and verify timeout error
        with pytest.raises(DaemonError) as exc_info:
            await client.request("textDocument/definition", {"filePath": "/test.py"})

        assert "timed out" in str(exc_info.value).lower()


# =============================================================================
# Exponential Backoff Tests
# =============================================================================


class TestExponentialBackoff:
    """Tests for exponential backoff behavior."""

    @pytest.mark.asyncio
    @patch("llm_lsp_cli.daemon_client.ConfigManager")
    @patch("llm_lsp_cli.daemon_client.asyncio.sleep")
    async def test_wait_for_socket_exponential_backoff(
        self,
        mock_sleep: AsyncMock,
        mock_config_manager: MagicMock,
        mock_daemon_manager: MagicMock,
        mock_unix_client: MagicMock,
    ):
        """Polling intervals follow exponential backoff: 50ms, 100ms, 200ms, 400ms, ..., 1s cap."""
        # Setup: socket appears after several retries
        call_count = [0]
        socket_exists_after = 4  # Socket appears after 4 checks

        mock_socket = MagicMock(spec=Path)

        def exists_side_effect() -> bool:
            call_count[0] += 1
            return call_count[0] > socket_exists_after

        mock_socket.exists.side_effect = exists_side_effect
        mock_socket.__str__ = MagicMock(return_value="/tmp/test.sock")
        mock_config_manager.build_socket_path.return_value = mock_socket

        mock_manager_instance = MagicMock()
        mock_manager_instance.is_running.return_value = True
        mock_daemon_manager.return_value = mock_manager_instance

        # Mock UNIXClient
        mock_client_instance = AsyncMock()
        mock_client_instance.request = AsyncMock(return_value={"result": "success"})
        mock_client_instance.close = AsyncMock()
        mock_unix_client.return_value = mock_client_instance

        client = DaemonClient("/workspace", "python", startup_timeout=5.0)

        # Execute
        await client.request("textDocument/definition", {"filePath": "/test.py"})

        # Verify exponential backoff calls
        # Expected delays: 0.05, 0.1, 0.2, 0.4 (then socket appears), then 0.01 for final delay
        actual_delays = [call.args[0] for call in mock_sleep.call_args_list]

        # Check exponential backoff pattern (before the final 0.01 delay)
        expected_backoff_delays = [0.05, 0.1, 0.2, 0.4]
        backoff_delays = actual_delays[:-1]  # All but the last (0.01)

        for expected, actual in zip(expected_backoff_delays, backoff_delays, strict=True):
            assert abs(actual - expected) < 0.001, f"Expected {expected}, got {actual}"

        # Verify final 10ms delay after socket appears
        assert actual_delays[-1] == 0.01

    @pytest.mark.asyncio
    @patch("llm_lsp_cli.daemon_client.ConfigManager")
    async def test_wait_for_socket_success_before_timeout(
        self,
        mock_config_manager: MagicMock,
        mock_daemon_manager: MagicMock,
        mock_unix_client: MagicMock,
    ):
        """Returns early when socket appears, no timeout error."""
        # Setup mock socket path that exists immediately
        mock_socket = MagicMock(spec=Path)
        mock_socket.exists.return_value = True
        mock_socket.__str__ = MagicMock(return_value="/tmp/test.sock")
        mock_config_manager.build_socket_path.return_value = mock_socket

        mock_manager_instance = MagicMock()
        mock_manager_instance.is_running.return_value = True
        mock_daemon_manager.return_value = mock_manager_instance

        # Mock UNIXClient
        mock_client_instance = AsyncMock()
        mock_client_instance.request = AsyncMock(return_value={"result": "success"})
        mock_client_instance.close = AsyncMock()
        mock_unix_client.return_value = mock_client_instance

        client = DaemonClient("/workspace", "python", startup_timeout=10.0)

        # Should not raise
        await client.request("textDocument/definition", {"filePath": "/test.py"})

    @pytest.mark.asyncio
    @patch("llm_lsp_cli.daemon_client.ConfigManager")
    @patch("llm_lsp_cli.daemon_client.asyncio.sleep")
    async def test_wait_for_socket_small_delay_after_exists(
        self,
        mock_sleep: AsyncMock,
        mock_config_manager: MagicMock,
        mock_daemon_manager: MagicMock,
        mock_unix_client: MagicMock,
    ):
        """10ms delay called after socket appears."""
        # Setup: socket exists immediately
        mock_socket = MagicMock(spec=Path)
        mock_socket.exists.return_value = True
        mock_socket.__str__ = MagicMock(return_value="/tmp/test.sock")
        mock_config_manager.build_socket_path.return_value = mock_socket

        mock_manager_instance = MagicMock()
        mock_manager_instance.is_running.return_value = True
        mock_daemon_manager.return_value = mock_manager_instance

        # Mock UNIXClient
        mock_client_instance = AsyncMock()
        mock_client_instance.request = AsyncMock(return_value={"result": "success"})
        mock_client_instance.close = AsyncMock()
        mock_unix_client.return_value = mock_client_instance

        client = DaemonClient("/workspace", "python")

        await client.request("textDocument/definition", {"filePath": "/test.py"})

        # Verify 0.01s (10ms) delay called after socket found
        actual_delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert 0.01 in actual_delays


# =============================================================================
# Resource Cleanup Tests
# =============================================================================


class TestResourceCleanup:
    """Tests for resource cleanup."""

    @pytest.mark.asyncio
    @patch("llm_lsp_cli.daemon_client.ConfigManager")
    async def test_close_cleans_up_client(
        self,
        mock_config_manager: MagicMock,
        mock_daemon_manager: MagicMock,
        mock_unix_client: MagicMock,
    ):
        """close() closes underlying client and sets _client to None."""
        # Setup mock socket path
        mock_socket = MagicMock(spec=Path)
        mock_socket.exists.return_value = True
        mock_socket.__str__ = MagicMock(return_value="/tmp/test.sock")
        mock_config_manager.build_socket_path.return_value = mock_socket

        # Setup
        mock_manager_instance = MagicMock()
        mock_manager_instance.is_running.return_value = True
        mock_daemon_manager.return_value = mock_manager_instance

        mock_client_instance = AsyncMock()
        mock_client_instance.request = AsyncMock(return_value={"result": "success"})
        mock_client_instance.close = AsyncMock()
        mock_unix_client.return_value = mock_client_instance

        client = DaemonClient("/workspace", "python")

        # Make a request - note: _client is cleaned up in finally block after request
        await client.request("textDocument/definition", {"filePath": "/test.py"})

        # Verify client.close() was called during request cleanup
        mock_client_instance.close.assert_called_once()

        # Now set up a new client manually to test explicit close()
        client._client = mock_client_instance
        mock_client_instance.reset_mock()

        # Close explicitly
        await client.close()

        # Verify cleanup
        mock_client_instance.close.assert_called_once()
        assert client._client is None

    @pytest.mark.asyncio
    @patch("llm_lsp_cli.daemon_client.ConfigManager")
    async def test_close_idempotent(
        self,
        mock_config_manager: MagicMock,
    ):
        """Multiple close() calls are safe."""
        mock_config_manager.build_socket_path.return_value = Path("/tmp/test.sock")

        client = DaemonClient("/workspace", "python")

        # First close (no-op since no client created)
        await client.close()

        # Second close (should not raise)
        await client.close()
