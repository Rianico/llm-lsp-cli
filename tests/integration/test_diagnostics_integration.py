"""Integration tests for diagnostics commands.

Tests the full end-to-end flow of diagnostics commands:
- CLI commands (diagnostics, workspace_diagnostics)
- Daemon routing
- Server registry methods
- LSP client integration
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from typer.testing import CliRunner

from llm_lsp_cli.lsp.types import Diagnostic, WorkspaceDiagnosticItem

runner = CliRunner()

# Use current working directory as workspace for tests to avoid path boundary issues
TEST_WORKSPACE = str(Path.cwd())
TEST_FILE = str(Path.cwd() / "test_file.py")


class TestDiagnosticsCommand:
    """Integration tests for the diagnostics command."""

    @pytest.fixture
    def mock_diagnostics_response(self) -> list[dict]:
        """Mock diagnostics response for a single file."""
        return [
            {
                "range": {
                    "start": {"line": 4, "character": 0},
                    "end": {"line": 4, "character": 20},
                },
                "severity": 1,  # Error
                "code": "E0001",
                "source": "pyright",
                "message": "Undefined variable 'x'",
                "tags": [],
            },
            {
                "range": {
                    "start": {"line": 10, "character": 4},
                    "end": {"line": 10, "character": 15},
                },
                "severity": 2,  # Warning
                "code": "W0002",
                "source": "pyright",
                "message": "Unused import 'os'",
                "tags": [],
            },
        ]

    def test_diagnostics_text_format(self, mock_diagnostics_response: list[dict]) -> None:
        """Test diagnostics command with text output format."""
        from llm_lsp_cli.cli import app

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
             patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class, \
             patch("pathlib.Path.exists", return_value=True):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                return_value={"diagnostics": mock_diagnostics_response}
            )
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app,
                ["diagnostics", TEST_FILE, "-o", "text"],
            )

            assert result.exit_code == 0
            assert "Error" in result.output
            assert "Undefined variable" in result.output
            assert "Warning" in result.output
            assert "Unused import" in result.output

    def test_diagnostics_json_format(self, mock_diagnostics_response: list[dict]) -> None:
        """Test diagnostics command with JSON output format."""
        from llm_lsp_cli.cli import app

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
             patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class, \
             patch("pathlib.Path.exists", return_value=True):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                return_value={"diagnostics": mock_diagnostics_response}
            )
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app,
                ["diagnostics", TEST_FILE, "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert isinstance(parsed, list)
            assert len(parsed) == 2
            assert parsed[0]["severity_name"] == "Error"
            assert parsed[0]["message"] == "Undefined variable 'x'"
            assert parsed[1]["severity_name"] == "Warning"

    def test_diagnostics_yaml_format(self, mock_diagnostics_response: list[dict]) -> None:
        """Test diagnostics command with YAML output format."""
        from llm_lsp_cli.cli import app

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
             patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class, \
             patch("pathlib.Path.exists", return_value=True):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                return_value={"diagnostics": mock_diagnostics_response}
            )
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app,
                ["diagnostics", TEST_FILE, "-o", "yaml"],
            )

            assert result.exit_code == 0
            parsed = yaml.safe_load(result.output)
            assert isinstance(parsed, list)
            assert len(parsed) == 2
            assert parsed[0]["severity_name"] == "Error"
            assert parsed[0]["message"] == "Undefined variable 'x'"

    def test_diagnostics_csv_format(self, mock_diagnostics_response: list[dict]) -> None:
        """Test diagnostics command with CSV output format."""
        from llm_lsp_cli.cli import app

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
             patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class, \
             patch("pathlib.Path.exists", return_value=True):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                return_value={"diagnostics": mock_diagnostics_response}
            )
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app,
                ["diagnostics", TEST_FILE, "-o", "csv"],
            )

            assert result.exit_code == 0
            lines = result.output.strip().split("\n")
            assert len(lines) == 3  # header + 2 data rows
            assert "severity" in lines[0]
            assert "message" in lines[0]

    def test_diagnostics_empty_results(self) -> None:
        """Test diagnostics command with empty results."""
        from llm_lsp_cli.cli import app

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
             patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class, \
             patch("pathlib.Path.exists", return_value=True):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value={"diagnostics": []})
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app,
                ["diagnostics", TEST_FILE, "-o", "text"],
            )

            assert result.exit_code == 0
            assert "No diagnostics found" in result.output


class TestWorkspaceDiagnosticsCommand:
    """Integration tests for the workspace_diagnostics command."""

    @pytest.fixture
    def mock_workspace_diagnostics_response(self) -> list[dict]:
        """Mock workspace diagnostics response."""
        return [
            {
                "uri": f"file://{TEST_WORKSPACE}/src/main.py",
                "version": 1,
                "diagnostics": [
                    {
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 0, "character": 10},
                        },
                        "severity": 1,
                        "code": "E0001",
                        "source": "pyright",
                        "message": "Missing type annotation",
                    },
                ],
            },
            {
                "uri": f"file://{TEST_WORKSPACE}/src/utils.py",
                "version": 1,
                "diagnostics": [
                    {
                        "range": {
                            "start": {"line": 5, "character": 0},
                            "end": {"line": 5, "character": 15},
                        },
                        "severity": 2,
                        "code": "W0002",
                        "source": "pyright",
                        "message": "Unused variable",
                    },
                ],
            },
            {
                "uri": f"file://{TEST_WORKSPACE}/tests/test_main.py",
                "version": 1,
                "diagnostics": [
                    {
                        "range": {
                            "start": {"line": 10, "character": 0},
                            "end": {"line": 10, "character": 20},
                        },
                        "severity": 1,
                        "code": "E0003",
                        "source": "pyright",
                        "message": "Test file error",
                    },
                ],
            },
        ]

    def test_workspace_diagnostics_text_format(
        self, mock_workspace_diagnostics_response: list[dict]
    ) -> None:
        """Test workspace_diagnostics command with text output format."""
        from llm_lsp_cli.cli import app

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
             patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class, \
             patch("pathlib.Path.exists", return_value=True):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                return_value={"diagnostics": mock_workspace_diagnostics_response}
            )
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app,
                ["workspace-diagnostics", "-w", TEST_WORKSPACE, "-o", "text"],
            )

            assert result.exit_code == 0
            # Should include non-test file diagnostics
            assert "Missing type annotation" in result.output
            assert "Unused variable" in result.output

    def test_workspace_diagnostics_json_format(
        self, mock_workspace_diagnostics_response: list[dict]
    ) -> None:
        """Test workspace_diagnostics command with JSON output format."""
        from llm_lsp_cli.cli import app

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
             patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class, \
             patch("pathlib.Path.exists", return_value=True):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                return_value={"diagnostics": mock_workspace_diagnostics_response}
            )
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app,
                ["workspace-diagnostics", "-w", TEST_WORKSPACE, "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert isinstance(parsed, list)
            # Should have 2 diagnostics (test file filtered out by default)
            assert len(parsed) == 2
            assert any(d["message"] == "Missing type annotation" for d in parsed)
            assert any(d["message"] == "Unused variable" for d in parsed)

    def test_workspace_diagnostics_includes_tests(
        self, mock_workspace_diagnostics_response: list[dict]
    ) -> None:
        """Test workspace_diagnostics with --include-tests flag."""
        from llm_lsp_cli.cli import app

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
             patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class, \
             patch("pathlib.Path.exists", return_value=True):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                return_value={"diagnostics": mock_workspace_diagnostics_response}
            )
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "workspace-diagnostics",
                    "-w",
                    TEST_WORKSPACE,
                    "-o",
                    "json",
                    "--include-tests",
                ],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert isinstance(parsed, list)
            # Should have 3 diagnostics (test file included)
            assert len(parsed) == 3
            assert any("Test file" in d["message"] for d in parsed)

    def test_workspace_diagnostics_empty_results(self) -> None:
        """Test workspace_diagnostics command with empty results."""
        from llm_lsp_cli.cli import app

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
             patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class, \
             patch("pathlib.Path.exists", return_value=True):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value={"diagnostics": []})
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app,
                ["workspace-diagnostics", "-w", TEST_WORKSPACE, "-o", "text"],
            )

            assert result.exit_code == 0
            assert "No diagnostics found" in result.output


class TestDaemonRouting:
    """Tests for daemon routing of diagnostic methods."""

    def test_lsp_methods_includes_diagnostics(self) -> None:
        """Test that LSP_METHODS includes diagnostic methods."""
        from llm_lsp_cli.daemon import RequestHandler

        # Create a handler to access class attributes
        handler = RequestHandler.__new__(RequestHandler)

        assert "textDocument/diagnostic" in handler.LSP_METHODS
        assert "workspace/diagnostic" in handler.LSP_METHODS

        # Verify method mapping
        assert handler.LSP_METHODS["textDocument/diagnostic"][0] == "request_diagnostics"
        assert handler.LSP_METHODS["workspace/diagnostic"][0] == "request_workspace_diagnostics"

    def test_response_keys_includes_diagnostics(self) -> None:
        """Test that RESPONSE_KEYS includes diagnostic response keys."""
        from llm_lsp_cli.daemon import RequestHandler

        handler = RequestHandler.__new__(RequestHandler)

        assert "textDocument/diagnostic" in handler.RESPONSE_KEYS
        assert "workspace/diagnostic" in handler.RESPONSE_KEYS

        # Verify response key mapping
        assert handler.RESPONSE_KEYS["textDocument/diagnostic"] == "diagnostics"
        assert handler.RESPONSE_KEYS["workspace/diagnostic"] == "diagnostics"

    @pytest.mark.asyncio
    async def test_handle_diagnostics_method(self) -> None:
        """Test that daemon correctly handles diagnostic requests."""
        from llm_lsp_cli.daemon import RequestHandler

        handler = RequestHandler(
            workspace_path="/tmp/test",
            language="python",
        )

        # Mock registry methods
        mock_diagnostics = [
            {"range": {"start": {"line": 0, "character": 0}}, "message": "Test error"}
        ]

        with patch.object(
            handler._registry,
            "request_diagnostics",
            new=AsyncMock(return_value=mock_diagnostics),
        ):
            result = await handler.handle(
                "textDocument/diagnostic",
                {
                    "workspacePath": "/tmp/test",
                    "filePath": "/tmp/test/file.py",
                },
            )

            assert "diagnostics" in result
            assert len(result["diagnostics"]) == 1
            assert result["diagnostics"][0]["message"] == "Test error"

    @pytest.mark.asyncio
    async def test_handle_workspace_diagnostics_method(self) -> None:
        """Test that daemon correctly handles workspace diagnostic requests."""
        from llm_lsp_cli.daemon import RequestHandler

        handler = RequestHandler(
            workspace_path="/tmp/test",
            language="python",
        )

        # Mock registry methods
        mock_workspace_diagnostics = [
            {
                "uri": "file:///tmp/test/file.py",
                "diagnostics": [
                    {"range": {"start": {"line": 0, "character": 0}}, "message": "Test error"}
                ],
            }
        ]

        with patch.object(
            handler._registry,
            "request_workspace_diagnostics",
            new=AsyncMock(return_value=mock_workspace_diagnostics),
        ):
            result = await handler.handle(
                "workspace/diagnostic",
                {"workspacePath": "/tmp/test"},
            )

            assert "diagnostics" in result
            assert len(result["diagnostics"]) == 1
            assert result["diagnostics"][0]["uri"] == "file:///tmp/test/file.py"


class TestServerRegistryMethods:
    """Tests for server registry diagnostic methods."""

    @pytest.mark.asyncio
    async def test_request_diagnostics(self) -> None:
        """Test server registry request_diagnostics method."""
        from llm_lsp_cli.server import ServerRegistry

        registry = ServerRegistry(lsp_conf=None)

        mock_client = AsyncMock()
        mock_client.request_diagnostics = AsyncMock(
            return_value=[
                {"range": {"start": {"line": 0}}, "message": "Test diagnostic"}
            ]
        )

        with patch.object(
            registry,
            "get_or_create_workspace",
            new=AsyncMock(return_value=AsyncMock(ensure_initialized=AsyncMock(return_value=mock_client))),
        ):
            result = await registry.request_diagnostics(
                workspace_path="/tmp/test",
                file_path="/tmp/test/file.py",
            )

            assert len(result) == 1
            assert result[0]["message"] == "Test diagnostic"

    @pytest.mark.asyncio
    async def test_request_workspace_diagnostics(self) -> None:
        """Test server registry request_workspace_diagnostics method."""
        from llm_lsp_cli.server import ServerRegistry

        registry = ServerRegistry(lsp_conf=None)

        mock_client = AsyncMock()
        mock_client.request_workspace_diagnostics = AsyncMock(
            return_value=[
                {
                    "uri": "file:///tmp/test/file.py",
                    "diagnostics": [{"message": "Test diagnostic"}],
                }
            ]
        )

        with patch.object(
            registry,
            "get_or_create_workspace",
            new=AsyncMock(return_value=AsyncMock(ensure_initialized=AsyncMock(return_value=mock_client))),
        ):
            result = await registry.request_workspace_diagnostics(
                workspace_path="/tmp/test",
            )

            assert len(result) == 1
            assert result[0]["uri"] == "file:///tmp/test/file.py"
