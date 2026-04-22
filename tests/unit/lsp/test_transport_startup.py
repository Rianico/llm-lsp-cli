"""Unit tests for StdioTransport startup verification."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from llm_lsp_cli.lsp.transport import StdioTransport


class TestTransportStartNoFileOpen:
    """Test StdioTransport.start does not open log file."""

    @pytest.mark.asyncio
    async def test_start_does_not_open_log_file(self) -> None:
        """start() method does not call open() for log file."""
        # Arrange
        from llm_lsp_cli.lsp.transport import StdioTransport

        transport = StdioTransport(command="echo")

        with patch("builtins.open") as mock_open:
            # Mock the subprocess to avoid actually starting it
            mock_process = AsyncMock()
            mock_process.returncode = None
            mock_process.stdin = MagicMock()
            mock_process.stdout = AsyncMock()
            mock_process.stderr = AsyncMock()

            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                with patch("asyncio.create_task"):
                    # Act
                    await transport.start()

            # Assert
            mock_open.assert_not_called()

    def test_log_fh_attribute_not_created(self) -> None:
        """StdioTransport does not create _log_fh attribute."""
        # Arrange
        from llm_lsp_cli.lsp.transport import StdioTransport

        # Act
        transport = StdioTransport(command="echo")

        # Assert
        assert not hasattr(transport, "_log_fh")


class TestTransportStartup:
    """Tests for StdioTransport.start() process verification."""

    @pytest.mark.asyncio
    async def test_process_not_found_raises_runtime_error(self):
        """FileNotFoundError raises RuntimeError with 'command not found'."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            # Simulate command not found
            mock_exec.side_effect = FileNotFoundError("Command not found")

            transport = StdioTransport(command="nonexistent-command")

            with pytest.raises(RuntimeError) as exc_info:
                await transport.start()

            assert "command not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_permission_denied_raises_runtime_error(self):
        """PermissionError raises RuntimeError with 'permission denied'."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            # Simulate permission denied
            mock_exec.side_effect = PermissionError("Permission denied")

            transport = StdioTransport(command="restricted-command")

            with pytest.raises(RuntimeError) as exc_info:
                await transport.start()

            assert "permission denied" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_process_immediate_exit_raises_runtime_error_with_stderr(self):
        """Process exiting immediately raises RuntimeError with stderr output."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            # Mock process that already has returncode set (exited immediately)
            mock_process = AsyncMock()
            mock_process.returncode = 1  # Already exited with error
            mock_process.stderr = AsyncMock()
            mock_process.stderr.read = AsyncMock(return_value=b"Error: invalid configuration\n")
            mock_process.stdin = MagicMock()
            mock_process.stdout = AsyncMock()
            mock_exec.return_value = mock_process

            transport = StdioTransport(command="crashing-command")

            # GREEN phase: RuntimeError raised with stderr
            with pytest.raises(RuntimeError) as exc_info:
                await transport.start()

            # Verify error message includes stderr output
            assert "invalid configuration" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_process_starts_successfully(self):
        """Process starts successfully, _running is set to True."""
        with (
            patch("asyncio.create_subprocess_exec") as mock_exec,
            patch("asyncio.create_task"),  # Mock task creation to avoid background tasks
        ):
            # Mock successful process
            mock_process = AsyncMock()
            mock_process.returncode = None  # Still running
            mock_process.stdin = MagicMock()
            mock_process.stdout = AsyncMock()
            mock_process.stderr = AsyncMock()
            mock_exec.return_value = mock_process

            transport = StdioTransport(command="valid-command")

            # Should not raise
            await transport.start()

            # Verify process was started
            assert transport._process is mock_process
            assert transport._running is True

    @pytest.mark.asyncio
    async def test_stabilization_delay_present(self):
        """Verifies a small stabilization delay is present after process start."""
        with (
            patch("asyncio.create_subprocess_exec") as mock_exec,
            patch("asyncio.create_task"),  # Mock task creation to avoid background tasks
            patch("asyncio.sleep") as mock_sleep,
        ):
            # Mock successful process
            mock_process = AsyncMock()
            mock_process.returncode = None
            mock_process.stdin = MagicMock()
            mock_process.stdout = AsyncMock()
            mock_process.stderr = AsyncMock()
            mock_exec.return_value = mock_process

            transport = StdioTransport(command="valid-command")
            await transport.start()

            # In GREEN phase: sleep should be called for stabilization (50ms)
            assert mock_sleep.called, "Stabilization delay not implemented"
            # Verify the stabilization delay is 50ms
            mock_sleep.assert_called_with(0.05)

    @pytest.mark.asyncio
    async def test_stderr_read_and_included_in_error(self):
        """When process fails, stderr is read and included in error message."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            # Mock process with stderr output
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.stderr = AsyncMock()
            mock_process.stderr.read = AsyncMock(return_value=b"Specific error message\n")
            mock_process.stdin = MagicMock()
            mock_process.stdout = AsyncMock()
            mock_exec.return_value = mock_process

            transport = StdioTransport(command="failing-command")

            with pytest.raises(RuntimeError) as exc_info:
                await transport.start()

            # Verify stderr was read
            mock_process.stderr.read.assert_called_once()
            # Verify stderr content is in error message
            assert "specific error message" in str(exc_info.value).lower()
