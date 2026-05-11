"""Tests for type_helpers removal from lsp.py (Step 5-6 of ADR-0028).

These tests verify that:
1. lsp.py does NOT import type_helpers functions
2. lsp.py uses typed daemon RPC params (DaemonPositionParams, etc.)
3. send_request returns typed values that are used directly
"""

import ast
import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestLspNoTypeHelpersImport:
    """Verify lsp.py does not import from type_helpers."""

    def test_lsp_py_no_type_helpers_import(self) -> None:
        """lsp.py must NOT import from type_helpers module."""
        lsp_py_path = Path(__file__).parent.parent.parent / "src" / "llm_lsp_cli" / "commands" / "lsp.py"
        content = lsp_py_path.read_text()

        # Parse the AST to check imports
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                # Check if importing from type_helpers
                if node.module and "type_helpers" in node.module:
                    imported_names = [alias.name for alias in node.names]
                    pytest.fail(
                        f"lsp.py must not import from type_helpers. "
                        f"Found import: from {node.module} import {', '.join(imported_names)}"
                    )


class TestLspUsesTypedParams:
    """Verify lsp.py uses typed daemon RPC params for send_request calls."""

    def test_definition_uses_daemon_position_params(self) -> None:
        """definition command must use DaemonPositionParams for send_request."""
        from llm_lsp_cli.commands.lsp import definition
        from llm_lsp_cli.ipc import DaemonPositionParams
        from llm_lsp_cli.commands.shared import GlobalOptions
        from llm_lsp_cli.utils import OutputFormat

        ctx = MagicMock()
        ctx.obj = GlobalOptions(
            workspace="/workspace",
            language="python",
            output_format=OutputFormat.JSON,
        )

        # Track what params were passed to send_request
        captured_params: list[object] = []

        def capture_send_request(method: str, params: object, language: str | None = None) -> object:
            captured_params.append(params)
            return []  # Return empty list for locations

        with patch("llm_lsp_cli.commands.lsp.send_request", side_effect=capture_send_request):
            with patch("llm_lsp_cli.commands.lsp.validate_file_in_workspace", return_value=Path("/workspace/file.py")):
                with patch("llm_lsp_cli.commands.lsp.build_request_context") as mock_ctx:
                    mock_ctx.return_value = MagicMock(
                        workspace_path="/workspace",
                        language="python",
                        output_format=OutputFormat.JSON,
                        file_path=Path("/workspace/file.py"),
                        line=1,
                        column=1,
                    )
                    with patch("llm_lsp_cli.commands.lsp.typer"):
                        try:
                            definition(ctx, "file.py", 1, 1)
                        except Exception:
                            pass  # Ignore output errors, just check params

        # Verify DaemonPositionParams was used
        assert len(captured_params) == 1, "send_request should be called once"
        assert isinstance(captured_params[0], DaemonPositionParams), (
            f"definition must use DaemonPositionParams, got {type(captured_params[0])}"
        )

    def test_references_uses_daemon_position_params(self) -> None:
        """references command must use DaemonPositionParams for send_request."""
        from llm_lsp_cli.commands.lsp import references
        from llm_lsp_cli.ipc import DaemonPositionParams
        from llm_lsp_cli.commands.shared import GlobalOptions
        from llm_lsp_cli.utils import OutputFormat

        ctx = MagicMock()
        ctx.obj = GlobalOptions(
            workspace="/workspace",
            language="python",
            output_format=OutputFormat.JSON,
        )

        captured_params: list[object] = []

        def capture_send_request(method: str, params: object, language: str | None = None) -> object:
            captured_params.append(params)
            return []  # Return empty list for locations

        with patch("llm_lsp_cli.commands.lsp.send_request", side_effect=capture_send_request):
            with patch("llm_lsp_cli.commands.lsp.build_request_context") as mock_ctx:
                mock_ctx.return_value = MagicMock(
                    workspace_path="/workspace",
                    language="python",
                    output_format=OutputFormat.JSON,
                    file_path=Path("/workspace/file.py"),
                    line=1,
                    column=1,
                )
                with patch("llm_lsp_cli.commands.lsp.typer"):
                    try:
                        references(ctx, "file.py", 1, 1, raw=False)
                    except Exception:
                        pass

        assert len(captured_params) == 1
        assert isinstance(captured_params[0], DaemonPositionParams), (
            f"references must use DaemonPositionParams, got {type(captured_params[0])}"
        )

    def test_document_symbol_uses_daemon_file_params(self) -> None:
        """document-symbol command must use DaemonFileParams for send_request."""
        from llm_lsp_cli.commands.lsp import document_symbol
        from llm_lsp_cli.ipc import DaemonFileParams
        from llm_lsp_cli.commands.shared import GlobalOptions
        from llm_lsp_cli.utils import OutputFormat

        ctx = MagicMock()
        ctx.obj = GlobalOptions(
            workspace="/workspace",
            language="python",
            output_format=OutputFormat.JSON,
        )

        captured_params: list[object] = []

        def capture_send_request(method: str, params: object, language: str | None = None) -> object:
            captured_params.append(params)
            return []  # Return empty list for symbols

        with patch("llm_lsp_cli.commands.lsp.send_request", side_effect=capture_send_request):
            with patch("llm_lsp_cli.commands.lsp.build_request_context") as mock_ctx:
                mock_ctx.return_value = MagicMock(
                    workspace_path="/workspace",
                    language="python",
                    output_format=OutputFormat.JSON,
                    file_path=Path("/workspace/file.py"),
                )
                with patch("llm_lsp_cli.commands.lsp.typer"):
                    try:
                        document_symbol(ctx, "file.py", depth=1, raw=False)
                    except Exception:
                        pass

        assert len(captured_params) == 1
        assert isinstance(captured_params[0], DaemonFileParams), (
            f"document-symbol must use DaemonFileParams, got {type(captured_params[0])}"
        )

    def test_workspace_symbol_uses_daemon_symbol_query_params(self) -> None:
        """workspace-symbol command must use DaemonSymbolQueryParams for send_request."""
        from llm_lsp_cli.commands.lsp import workspace_symbol
        from llm_lsp_cli.ipc import DaemonSymbolQueryParams
        from llm_lsp_cli.commands.shared import GlobalOptions
        from llm_lsp_cli.utils import OutputFormat

        ctx = MagicMock()
        ctx.obj = GlobalOptions(
            workspace="/workspace",
            language="python",
            output_format=OutputFormat.JSON,
        )

        captured_params: list[object] = []

        def capture_send_request(method: str, params: object, language: str | None = None) -> object:
            captured_params.append(params)
            return []  # Return empty list for symbols

        with patch("llm_lsp_cli.commands.lsp.send_request", side_effect=capture_send_request):
            with patch("llm_lsp_cli.commands.lsp.require_language_or_detect", return_value=("/workspace", "python")):
                with patch("llm_lsp_cli.commands.lsp.typer"):
                    try:
                        workspace_symbol(ctx, "query")
                    except Exception:
                        pass

        assert len(captured_params) == 1
        assert isinstance(captured_params[0], DaemonSymbolQueryParams), (
            f"workspace-symbol must use DaemonSymbolQueryParams, got {type(captured_params[0])}"
        )

    def test_incoming_calls_uses_daemon_position_params(self) -> None:
        """incoming-calls command must use DaemonPositionParams for send_request."""
        from llm_lsp_cli.commands.lsp import incoming_calls
        from llm_lsp_cli.ipc import DaemonPositionParams
        from llm_lsp_cli.commands.shared import GlobalOptions
        from llm_lsp_cli.utils import OutputFormat

        ctx = MagicMock()
        ctx.obj = GlobalOptions(
            workspace="/workspace",
            language="python",
            output_format=OutputFormat.JSON,
        )

        captured_params: list[object] = []

        def capture_send_request(method: str, params: object, language: str | None = None) -> object:
            captured_params.append(params)
            return []  # Return empty list for calls

        with patch("llm_lsp_cli.commands.lsp.send_request", side_effect=capture_send_request):
            with patch("llm_lsp_cli.commands.lsp.build_request_context") as mock_ctx:
                mock_ctx.return_value = MagicMock(
                    workspace_path="/workspace",
                    language="python",
                    output_format=OutputFormat.JSON,
                    file_path=Path("/workspace/file.py"),
                    line=1,
                    column=1,
                )
                with patch("llm_lsp_cli.commands.lsp.typer"):
                    try:
                        incoming_calls(ctx, "file.py", 1, 1, raw=False)
                    except Exception:
                        pass

        assert len(captured_params) == 1
        assert isinstance(captured_params[0], DaemonPositionParams), (
            f"incoming-calls must use DaemonPositionParams, got {type(captured_params[0])}"
        )

    def test_outgoing_calls_uses_daemon_position_params(self) -> None:
        """outgoing-calls command must use DaemonPositionParams for send_request."""
        from llm_lsp_cli.commands.lsp import outgoing_calls
        from llm_lsp_cli.ipc import DaemonPositionParams
        from llm_lsp_cli.commands.shared import GlobalOptions
        from llm_lsp_cli.utils import OutputFormat

        ctx = MagicMock()
        ctx.obj = GlobalOptions(
            workspace="/workspace",
            language="python",
            output_format=OutputFormat.JSON,
        )

        captured_params: list[object] = []

        def capture_send_request(method: str, params: object, language: str | None = None) -> object:
            captured_params.append(params)
            return []  # Return empty list for calls

        with patch("llm_lsp_cli.commands.lsp.send_request", side_effect=capture_send_request):
            with patch("llm_lsp_cli.commands.lsp.build_request_context") as mock_ctx:
                mock_ctx.return_value = MagicMock(
                    workspace_path="/workspace",
                    language="python",
                    output_format=OutputFormat.JSON,
                    file_path=Path("/workspace/file.py"),
                    line=1,
                    column=1,
                )
                with patch("llm_lsp_cli.commands.lsp.typer"):
                    try:
                        outgoing_calls(ctx, "file.py", 1, 1, raw=False)
                    except Exception:
                        pass

        assert len(captured_params) == 1
        assert isinstance(captured_params[0], DaemonPositionParams), (
            f"outgoing-calls must use DaemonPositionParams, got {type(captured_params[0])}"
        )

    def test_completion_uses_daemon_position_params(self) -> None:
        """completion command must use DaemonPositionParams for send_request."""
        from llm_lsp_cli.commands.lsp import completion
        from llm_lsp_cli.ipc import DaemonPositionParams
        from llm_lsp_cli.commands.shared import GlobalOptions
        from llm_lsp_cli.utils import OutputFormat

        ctx = MagicMock()
        ctx.obj = GlobalOptions(
            workspace="/workspace",
            language="python",
            output_format=OutputFormat.JSON,
        )

        captured_params: list[object] = []

        def capture_send_request(method: str, params: object, language: str | None = None) -> object:
            captured_params.append(params)
            return []  # Return empty list for items

        with patch("llm_lsp_cli.commands.lsp.send_request", side_effect=capture_send_request):
            with patch("llm_lsp_cli.commands.lsp.build_request_context") as mock_ctx:
                mock_ctx.return_value = MagicMock(
                    workspace_path="/workspace",
                    language="python",
                    output_format=OutputFormat.JSON,
                    file_path=Path("/workspace/file.py"),
                    line=1,
                    column=1,
                )
                with patch("llm_lsp_cli.commands.lsp.typer"):
                    try:
                        completion(ctx, "file.py", 1, 1)
                    except Exception:
                        pass

        assert len(captured_params) == 1
        assert isinstance(captured_params[0], DaemonPositionParams), (
            f"completion must use DaemonPositionParams, got {type(captured_params[0])}"
        )

    def test_hover_uses_daemon_position_params(self) -> None:
        """hover command must use DaemonPositionParams for send_request."""
        from llm_lsp_cli.commands.lsp import hover
        from llm_lsp_cli.ipc import DaemonPositionParams
        from llm_lsp_cli.commands.shared import GlobalOptions
        from llm_lsp_cli.utils import OutputFormat

        ctx = MagicMock()
        ctx.obj = GlobalOptions(
            workspace="/workspace",
            language="python",
            output_format=OutputFormat.JSON,
        )

        captured_params: list[object] = []

        def capture_send_request(method: str, params: object, language: str | None = None) -> object:
            captured_params.append(params)
            return None  # Return None for hover

        with patch("llm_lsp_cli.commands.lsp.send_request", side_effect=capture_send_request):
            with patch("llm_lsp_cli.commands.lsp.build_request_context") as mock_ctx:
                mock_ctx.return_value = MagicMock(
                    workspace_path="/workspace",
                    language="python",
                    output_format=OutputFormat.JSON,
                    file_path=Path("/workspace/file.py"),
                    line=1,
                    column=1,
                )
                with patch("llm_lsp_cli.commands.lsp.typer"):
                    try:
                        hover(ctx, "file.py", 1, 1)
                    except Exception:
                        pass

        assert len(captured_params) == 1
        assert isinstance(captured_params[0], DaemonPositionParams), (
            f"hover must use DaemonPositionParams, got {type(captured_params[0])}"
        )

    def test_diagnostics_uses_daemon_file_params(self) -> None:
        """diagnostics command must use DaemonFileParams for send_request."""
        from llm_lsp_cli.commands.lsp import diagnostics
        from llm_lsp_cli.ipc import DaemonFileParams
        from llm_lsp_cli.commands.shared import GlobalOptions
        from llm_lsp_cli.utils import OutputFormat

        ctx = MagicMock()
        ctx.obj = GlobalOptions(
            workspace="/workspace",
            language="python",
            output_format=OutputFormat.JSON,
        )

        captured_params: list[object] = []

        def capture_send_request(method: str, params: object, language: str | None = None) -> object:
            captured_params.append(params)
            return {"diagnostics": []}  # Return empty dict for diagnostics

        with patch("llm_lsp_cli.commands.lsp.send_request", side_effect=capture_send_request):
            with patch("llm_lsp_cli.commands.lsp.validate_file_in_workspace", return_value=Path("/workspace/file.py")):
                with patch("llm_lsp_cli.commands.lsp.resolve_workspace_path", return_value="/workspace"):
                    with patch("llm_lsp_cli.commands.lsp.typer"):
                        try:
                            diagnostics(ctx, "file.py")
                        except Exception:
                            pass

        assert len(captured_params) == 1
        assert isinstance(captured_params[0], DaemonFileParams), (
            f"diagnostics must use DaemonFileParams, got {type(captured_params[0])}"
        )

    def test_workspace_diagnostics_uses_daemon_workspace_params(self) -> None:
        """workspace-diagnostics command must use DaemonWorkspaceParams for send_request."""
        from llm_lsp_cli.commands.lsp import workspace_diagnostics
        from llm_lsp_cli.ipc import DaemonWorkspaceParams
        from llm_lsp_cli.commands.shared import GlobalOptions
        from llm_lsp_cli.utils import OutputFormat

        ctx = MagicMock()
        ctx.obj = GlobalOptions(
            workspace="/workspace",
            language="python",
            output_format=OutputFormat.JSON,
        )

        captured_params: list[object] = []

        def capture_send_request(method: str, params: object, language: str | None = None) -> object:
            captured_params.append(params)
            return {"diagnostics": []}  # Return empty dict for diagnostics

        with patch("llm_lsp_cli.commands.lsp.send_request", side_effect=capture_send_request):
            with patch("llm_lsp_cli.commands.lsp.require_language_or_detect", return_value=("/workspace", "python")):
                with patch("llm_lsp_cli.commands.lsp.typer"):
                    try:
                        workspace_diagnostics(ctx)
                    except Exception:
                        pass

        assert len(captured_params) == 1
        assert isinstance(captured_params[0], DaemonWorkspaceParams), (
            f"workspace-diagnostics must use DaemonWorkspaceParams, got {type(captured_params[0])}"
        )

    def test_rename_uses_daemon_rename_params(self) -> None:
        """rename command must use DaemonRenameParams for send_request."""
        from llm_lsp_cli.commands.lsp import rename
        from llm_lsp_cli.ipc import DaemonRenameParams
        from llm_lsp_cli.commands.shared import GlobalOptions
        from llm_lsp_cli.utils import OutputFormat
        from llm_lsp_cli.lsp.types import WorkspaceEdit

        ctx = MagicMock()
        ctx.obj = GlobalOptions(
            workspace="/workspace",
            language="python",
            output_format=OutputFormat.JSON,
        )

        captured_params: list[object] = []

        def capture_send_request(method: str, params: object, language: str | None = None) -> object:
            captured_params.append(params)
            # Return a proper WorkspaceEdit object
            return WorkspaceEdit(changes={})

        with patch("llm_lsp_cli.commands.lsp.send_request", side_effect=capture_send_request):
            with patch("llm_lsp_cli.commands.lsp.build_request_context") as mock_ctx:
                mock_ctx.return_value = MagicMock(
                    workspace_path="/workspace",
                    language="python",
                    output_format=OutputFormat.JSON,
                    file_path=Path("/workspace/file.py"),
                    line=1,
                    column=1,
                )
                # Patch resolve_workspace_path to return a valid path
                with patch("llm_lsp_cli.commands.lsp.resolve_workspace_path", return_value="/workspace"):
                    # Patch BackupManager and RenameService at their module location
                    with patch("llm_lsp_cli.domain.services.backup_manager.BackupManager") as mock_backup:
                        mock_backup.return_value = MagicMock()
                        with patch("llm_lsp_cli.domain.services.rename_service.RenameService") as mock_service:
                            mock_service.return_value = MagicMock(preview_from_edit=MagicMock(return_value=[]))
                            with patch("llm_lsp_cli.commands.lsp.typer"):
                                # Pass None for all optional Typer parameters
                                rename(ctx, "file.py", 1, 1, "newName", None, None, None, False, False, None)

        assert len(captured_params) == 1
        assert isinstance(captured_params[0], DaemonRenameParams), (
            f"rename must use DaemonRenameParams, got {type(captured_params[0])}"
        )

    def test_did_change_uses_daemon_file_params(self) -> None:
        """did-change command must use DaemonFileParams for send_request."""
        from llm_lsp_cli.commands.lsp import did_change
        from llm_lsp_cli.ipc import DaemonFileParams
        from llm_lsp_cli.commands.shared import GlobalOptions
        from llm_lsp_cli.utils import OutputFormat

        ctx = MagicMock()
        ctx.obj = GlobalOptions(
            workspace="/workspace",
            language="python",
            output_format=OutputFormat.JSON,
        )

        captured_params: list[object] = []

        def capture_send_request(method: str, params: object, language: str | None = None) -> object:
            captured_params.append(params)
            return {"status": "acknowledged"}

        with patch("llm_lsp_cli.commands.lsp.send_request", side_effect=capture_send_request):
            with patch("llm_lsp_cli.commands.lsp.validate_file_in_workspace", return_value=Path("/workspace/file.py")):
                with patch("llm_lsp_cli.commands.lsp.resolve_workspace_path", return_value="/workspace"):
                    with patch("llm_lsp_cli.commands.lsp.typer"):
                        try:
                            did_change("file.py")
                        except Exception:
                            pass

        assert len(captured_params) == 1
        assert isinstance(captured_params[0], DaemonFileParams), (
            f"did-change must use DaemonFileParams, got {type(captured_params[0])}"
        )


class TestSendRequestReturnsTypedValues:
    """Verify send_request returns typed values when called with typed params."""

    def test_definition_returns_list_location(self) -> None:
        """definition returns list[Location], not dict."""
        from llm_lsp_cli.commands.shared import send_request
        from llm_lsp_cli.ipc import DaemonPositionParams
        from llm_lsp_cli.lsp.types import Location
        from unittest.mock import AsyncMock

        params = DaemonPositionParams(
            workspace_path="/ws",
            file_path="/file.py",
            line=5,
            column=10,
        )

        daemon_response = {
            "locations": [
                {
                    "uri": "file:///tmp/test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 5},
                    },
                }
            ]
        }

        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value=daemon_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = send_request("textDocument/definition", params, language="python")

            # Result should be list[Location], not dict
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            if result:
                assert isinstance(result[0], Location), f"Expected Location, got {type(result[0])}"
