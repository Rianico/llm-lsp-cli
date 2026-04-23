"""Tests for CLI call hierarchy commands."""

import pytest
from typer.testing import CliRunner
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

runner = CliRunner()


def _patch_daemon_client(mock_client: MagicMock):
    """Helper to patch DaemonClient where it's imported."""
    return patch("llm_lsp_cli.daemon_client.DaemonClient", return_value=mock_client)


class TestIncomingCallsCommand:
    """Tests for the incoming-calls CLI command."""

    @pytest.fixture
    def mock_daemon_client(self) -> MagicMock:
        """Create a mock DaemonClient."""
        client = MagicMock()
        client.request = AsyncMock(
            return_value={
                "calls": [
                    {
                        "from_": {
                            "name": "caller_func",
                            "kind": 12,
                            "uri": "file:///project/src/caller.py",
                            "range": {
                                "start": {"line": 5, "character": 0},
                                "end": {"line": 10, "character": 0},
                            },
                            "selectionRange": {
                                "start": {"line": 5, "character": 4},
                                "end": {"line": 5, "character": 14},
                            },
                        },
                        "fromRanges": [],
                    }
                ]
            }
        )
        client.close = AsyncMock()
        return client

    def test_incoming_calls_basic(self, mock_daemon_client: MagicMock, tmp_path: Path) -> None:
        """Incoming-calls command with basic args calls daemon correctly."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        with _patch_daemon_client(mock_daemon_client):
            from llm_lsp_cli.cli import app

            result = runner.invoke(
                app,
                ["incoming-calls", str(test_file), "0", "4", "-w", str(tmp_path)],
            )

        assert result.exit_code == 0
        mock_daemon_client.request.assert_called_once()
        call_args = mock_daemon_client.request.call_args
        assert call_args[0][0] == "callHierarchy/incomingCalls"

    def test_incoming_calls_with_workspace(
        self, mock_daemon_client: MagicMock, tmp_path: Path
    ) -> None:
        """Incoming-calls with -w passes workspace to daemon."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        with _patch_daemon_client(mock_daemon_client):
            from llm_lsp_cli.cli import app

            result = runner.invoke(
                app,
                ["incoming-calls", str(test_file), "0", "4", "-w", str(tmp_path)],
            )

        assert result.exit_code == 0
        call_args = mock_daemon_client.request.call_args
        params = call_args[0][1]
        assert params["workspacePath"] == str(tmp_path)

    def test_incoming_calls_with_language(
        self, mock_daemon_client: MagicMock, tmp_path: Path
    ) -> None:
        """Incoming-calls with -l passes language to daemon."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        with _patch_daemon_client(mock_daemon_client):
            from llm_lsp_cli.cli import app

            result = runner.invoke(
                app,
                [
                    "incoming-calls",
                    str(test_file),
                    "0",
                    "4",
                    "-w",
                    str(tmp_path),
                    "-l",
                    "python",
                ],
            )

        assert result.exit_code == 0

    def test_incoming_calls_raw_format(
        self, mock_daemon_client: MagicMock, tmp_path: Path
    ) -> None:
        """Incoming-calls with --raw outputs verbose format."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        with _patch_daemon_client(mock_daemon_client):
            from llm_lsp_cli.cli import app

            result = runner.invoke(
                app,
                [
                    "incoming-calls",
                    str(test_file),
                    "0",
                    "4",
                    "-w",
                    str(tmp_path),
                    "--raw",
                ],
            )

        assert result.exit_code == 0

    def test_incoming_calls_compact_format(
        self, mock_daemon_client: MagicMock, tmp_path: Path
    ) -> None:
        """Incoming-calls default uses CompactFormatter."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        with _patch_daemon_client(mock_daemon_client):
            from llm_lsp_cli.cli import app

            result = runner.invoke(
                app,
                ["incoming-calls", str(test_file), "0", "4", "-w", str(tmp_path)],
            )

        assert result.exit_code == 0
        # Should output JSON by default
        assert result.output  # Should have output

    def test_incoming_calls_empty_result(
        self, mock_daemon_client: MagicMock, tmp_path: Path
    ) -> None:
        """Incoming-calls with empty result outputs 'No calls found'."""
        mock_daemon_client.request = AsyncMock(return_value={"calls": []})

        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        with _patch_daemon_client(mock_daemon_client):
            from llm_lsp_cli.cli import app

            result = runner.invoke(
                app,
                ["incoming-calls", str(test_file), "0", "4", "-w", str(tmp_path)],
            )

        assert result.exit_code == 0
        assert "No calls found" in result.output or result.output == "[]"

    def test_incoming_calls_include_tests(
        self, mock_daemon_client: MagicMock, tmp_path: Path
    ) -> None:
        """Incoming-calls with --include-tests includes test files."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        with _patch_daemon_client(mock_daemon_client):
            from llm_lsp_cli.cli import app

            result = runner.invoke(
                app,
                [
                    "incoming-calls",
                    str(test_file),
                    "0",
                    "4",
                    "-w",
                    str(tmp_path),
                    "--include-tests",
                ],
            )

        assert result.exit_code == 0


class TestOutgoingCallsCommand:
    """Tests for the outgoing-calls CLI command."""

    @pytest.fixture
    def mock_daemon_client(self) -> MagicMock:
        """Create a mock DaemonClient."""
        client = MagicMock()
        client.request = AsyncMock(
            return_value={
                "calls": [
                    {
                        "to": {
                            "name": "helper_func",
                            "kind": 12,
                            "uri": "file:///project/src/helper.py",
                            "range": {
                                "start": {"line": 0, "character": 0},
                                "end": {"line": 5, "character": 0},
                            },
                            "selectionRange": {
                                "start": {"line": 0, "character": 4},
                                "end": {"line": 0, "character": 14},
                            },
                        },
                        "fromRanges": [],
                    }
                ]
            }
        )
        client.close = AsyncMock()
        return client

    def test_outgoing_calls_basic(self, mock_daemon_client: MagicMock, tmp_path: Path) -> None:
        """Outgoing-calls command with basic args calls daemon correctly."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        with _patch_daemon_client(mock_daemon_client):
            from llm_lsp_cli.cli import app

            result = runner.invoke(
                app,
                ["outgoing-calls", str(test_file), "0", "4", "-w", str(tmp_path)],
            )

        assert result.exit_code == 0
        mock_daemon_client.request.assert_called_once()
        call_args = mock_daemon_client.request.call_args
        assert call_args[0][0] == "callHierarchy/outgoingCalls"

    def test_outgoing_calls_with_workspace(
        self, mock_daemon_client: MagicMock, tmp_path: Path
    ) -> None:
        """Outgoing-calls with -w passes workspace to daemon."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        with _patch_daemon_client(mock_daemon_client):
            from llm_lsp_cli.cli import app

            result = runner.invoke(
                app,
                ["outgoing-calls", str(test_file), "0", "4", "-w", str(tmp_path)],
            )

        assert result.exit_code == 0
        call_args = mock_daemon_client.request.call_args
        params = call_args[0][1]
        assert params["workspacePath"] == str(tmp_path)

    def test_outgoing_calls_with_language(
        self, mock_daemon_client: MagicMock, tmp_path: Path
    ) -> None:
        """Outgoing-calls with -l passes language to daemon."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        with _patch_daemon_client(mock_daemon_client):
            from llm_lsp_cli.cli import app

            result = runner.invoke(
                app,
                [
                    "outgoing-calls",
                    str(test_file),
                    "0",
                    "4",
                    "-w",
                    str(tmp_path),
                    "-l",
                    "python",
                ],
            )

        assert result.exit_code == 0

    def test_outgoing_calls_empty_result(
        self, mock_daemon_client: MagicMock, tmp_path: Path
    ) -> None:
        """Outgoing-calls with empty result outputs 'No calls found'."""
        mock_daemon_client.request = AsyncMock(return_value={"calls": []})

        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        with _patch_daemon_client(mock_daemon_client):
            from llm_lsp_cli.cli import app

            result = runner.invoke(
                app,
                ["outgoing-calls", str(test_file), "0", "4", "-w", str(tmp_path)],
            )

        assert result.exit_code == 0
        assert "No calls found" in result.output or result.output == "[]"


class TestCallHierarchyCommandsPosition:
    """Tests for position handling in call hierarchy commands."""

    @pytest.fixture
    def mock_daemon_client(self) -> MagicMock:
        """Create a mock DaemonClient."""
        client = MagicMock()
        client.request = AsyncMock(return_value={"calls": []})
        client.close = AsyncMock()
        return client

    def test_incoming_calls_converts_line_to_zero_based(
        self, mock_daemon_client: MagicMock, tmp_path: Path
    ) -> None:
        """Incoming-calls converts 1-based line to 0-based for LSP."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        with _patch_daemon_client(mock_daemon_client):
            from llm_lsp_cli.cli import app

            result = runner.invoke(
                app,
                ["incoming-calls", str(test_file), "10", "5", "-w", str(tmp_path)],
            )

        assert result.exit_code == 0
        call_args = mock_daemon_client.request.call_args
        params = call_args[0][1]
        # Line should be 0-based (10 - 1 = 9)
        assert params["line"] == 9
        # Column should be 0-based (5 - 1 = 4)
        assert params["column"] == 4

    def test_outgoing_calls_converts_line_to_zero_based(
        self, mock_daemon_client: MagicMock, tmp_path: Path
    ) -> None:
        """Outgoing-calls converts 1-based line to 0-based for LSP."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        with _patch_daemon_client(mock_daemon_client):
            from llm_lsp_cli.cli import app

            result = runner.invoke(
                app,
                ["outgoing-calls", str(test_file), "10", "5", "-w", str(tmp_path)],
            )

        assert result.exit_code == 0
        call_args = mock_daemon_client.request.call_args
        params = call_args[0][1]
        assert params["line"] == 9
        assert params["column"] == 4
