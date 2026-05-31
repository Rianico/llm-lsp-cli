"""Tests for send_request overloads and response unwrapping (Step 4 of ADR-0028).

These tests verify that send_request:
1. Accepts daemon RPC param models
2. Serializes them to flat camelCase
3. Unwraps response dicts using RESPONSE_KEYS
4. Validates inner values with Pydantic models
5. Returns typed results
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


class TestSendRequestParamSerialization:
    """Test that send_request correctly serializes BaseModel params."""

    def test_base_model_params_serialized_to_camel_case(self) -> None:
        """When params is a BaseModel, serialize via model_dump(by_alias=True)."""
        from llm_lsp_cli.commands.shared import send_request
        from llm_lsp_cli.ipc import DaemonPositionParams

        params = DaemonPositionParams(
            workspace_path="/ws",
            file_path="/file.py",
            line=5,
            column=10,
        )

        # Mock DaemonClient to capture what's sent
        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value={"locations": []})
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            send_request("textDocument/definition", params, language="python")

            # Verify request was called with serialized params
            call_args = mock_client.request.call_args
            sent_params = call_args[0][1]  # Second argument to request

            assert sent_params == {
                "workspacePath": "/ws",
                "filePath": "/file.py",
                "line": 5,
                "column": 10,
            }

    def test_dict_params_passed_through(self) -> None:
        """When params is a dict, pass through without transformation."""
        from llm_lsp_cli.commands.shared import send_request

        params = {"workspacePath": "/ws", "filePath": "/file.py", "line": 5, "column": 10}

        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value={"locations": []})
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            send_request("textDocument/definition", params, language="python")

            call_args = mock_client.request.call_args
            sent_params = call_args[0][1]

            # Dict should be passed as-is
            assert sent_params == params


class TestSendRequestResponseUnwrapping:
    """Test that send_request correctly unwraps and validates responses."""

    def test_definition_unwraps_to_location_list(self) -> None:
        """textDocument/definition unwraps locations and returns list[Location]."""
        from llm_lsp_cli.commands.shared import send_request
        from llm_lsp_cli.ipc import DaemonPositionParams
        from llm_lsp_cli.lsp.types import Location

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

            # Result should be unwrapped list[Location], not the wrapper dict
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], Location)
            assert result[0].uri == "file:///tmp/test.py"

    def test_hover_unwraps_to_hover_or_none(self) -> None:
        """textDocument/hover unwraps hover and returns Hover | None."""
        from llm_lsp_cli.commands.shared import send_request
        from llm_lsp_cli.ipc import DaemonPositionParams
        from llm_lsp_cli.lsp.types import Hover

        params = DaemonPositionParams(
            workspace_path="/ws",
            file_path="/file.py",
            line=5,
            column=10,
        )

        # Test with actual hover content
        daemon_response = {
            "hover": {
                "contents": {"kind": "plaintext", "value": "test"},
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 5},
                },
            }
        }

        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value=daemon_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = send_request("textDocument/hover", params, language="python")

            assert isinstance(result, Hover)

    def test_hover_none_response(self) -> None:
        """textDocument/hover returns None when hover is None."""
        from llm_lsp_cli.commands.shared import send_request
        from llm_lsp_cli.ipc import DaemonPositionParams

        params = DaemonPositionParams(
            workspace_path="/ws",
            file_path="/file.py",
            line=5,
            column=10,
        )

        daemon_response = {"hover": None}

        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value=daemon_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = send_request("textDocument/hover", params, language="python")

            assert result is None

    def test_completion_unwraps_to_item_list(self) -> None:
        """textDocument/completion unwraps items and returns list[CompletionItem]."""
        from llm_lsp_cli.commands.shared import send_request
        from llm_lsp_cli.ipc import DaemonPositionParams
        from llm_lsp_cli.lsp.types import CompletionItem

        params = DaemonPositionParams(
            workspace_path="/ws",
            file_path="/file.py",
            line=5,
            column=10,
        )

        daemon_response = {
            "items": [
                {"label": "test_item", "kind": 3},
            ]
        }

        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value=daemon_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = send_request("textDocument/completion", params, language="python")

            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], CompletionItem)
            assert result[0].label == "test_item"

    def test_completion_none_response(self) -> None:
        """textDocument/completion returns None when items is None."""
        from llm_lsp_cli.commands.shared import send_request
        from llm_lsp_cli.ipc import DaemonPositionParams

        params = DaemonPositionParams(
            workspace_path="/ws",
            file_path="/file.py",
            line=5,
            column=10,
        )

        daemon_response = {"items": None}

        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value=daemon_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = send_request("textDocument/completion", params, language="python")

            assert result is None

    def test_call_hierarchy_incoming_unwraps_to_call_list(self) -> None:
        """callHierarchy/incomingCalls unwraps calls."""
        from llm_lsp_cli.commands.shared import send_request
        from llm_lsp_cli.ipc import DaemonPositionParams
        from llm_lsp_cli.lsp.types import CallHierarchyIncomingCall

        params = DaemonPositionParams(
            workspace_path="/ws",
            file_path="/file.py",
            line=5,
            column=10,
        )

        daemon_response = {
            "calls": [
                {
                    "from": {
                        "name": "caller",
                        "kind": 12,
                        "uri": "file:///tmp/caller.py",
                        "range": {
                            "start": {"line": 1, "character": 0},
                            "end": {"line": 1, "character": 10},
                        },
                        "selectionRange": {
                            "line": 1,
                            "character": 0,
                            "start": {"line": 1, "character": 0},
                            "end": {"line": 1, "character": 10},
                        },
                    },
                    "fromRanges": [],
                }
            ]
        }

        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value=daemon_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = send_request(
                "callHierarchy/incomingCalls", params, language="python"
            )

            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], CallHierarchyIncomingCall)

    def test_rename_unwraps_to_workspace_edit(self) -> None:
        """textDocument/rename unwraps workspace_edit."""
        from llm_lsp_cli.commands.shared import send_request
        from llm_lsp_cli.ipc import DaemonRenameParams
        from llm_lsp_cli.lsp.types import WorkspaceEdit

        params = DaemonRenameParams(
            workspace_path="/ws",
            file_path="/file.py",
            line=5,
            column=10,
            new_name="newName",
        )

        daemon_response = {
            "workspace_edit": {
                "changes": {
                    "file:///tmp/test.py": [
                        {
                            "range": {
                                "start": {"line": 0, "character": 0},
                                "end": {"line": 0, "character": 5},
                            },
                            "newText": "newName",
                        }
                    ]
                }
            }
        }

        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value=daemon_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = send_request("textDocument/rename", params, language="python")

            assert isinstance(result, WorkspaceEdit)


class TestSendRequestDictReturns:
    """Test methods that return dict[str, object] (diagnostics, did-change)."""

    def test_diagnostics_returns_dict(self) -> None:
        """textDocument/diagnostic returns dict[str, object] (no unwrapping)."""
        from llm_lsp_cli.commands.shared import send_request
        from llm_lsp_cli.ipc import DaemonFileParams

        params = DaemonFileParams(
            workspace_path="/ws",
            file_path="/file.py",
        )

        daemon_response = {
            "diagnostics": [
                {
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 5},
                    },
                    "message": "test error",
                }
            ]
        }

        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value=daemon_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = send_request("textDocument/diagnostic", params, language="python")

            # Should return the dict as-is (no unwrapping for diagnostics)
            assert isinstance(result, dict)
            assert "diagnostics" in result

    def test_did_change_returns_none(self) -> None:
        """textDocument/didChange returns None (acknowledgment only, no data)."""
        from llm_lsp_cli.commands.shared import send_request
        from llm_lsp_cli.ipc import DaemonFileParams

        params = DaemonFileParams(
            workspace_path="/ws",
            file_path="/file.py",
        )

        daemon_response = {"status": "acknowledged"}

        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value=daemon_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = send_request("textDocument/didChange", params, language="python")

            # didChange returns None - success is implied by no exception
            assert result is None


class TestSendRequestUnknownMethod:
    """Test fallback behavior for unknown methods."""

    def test_unknown_method_with_dict_params_returns_unwrapped_value(self) -> None:
        """Unknown method with dict params returns unwrapped result value."""
        from llm_lsp_cli.commands.shared import send_request

        params = {"key": "value"}

        daemon_response = {"result": "data"}

        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value=daemon_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = send_request("unknown/method", params, language="python")

            # Gateway always unwraps using RESPONSE_KEYS
            assert result == "data"


class TestSendRequestValidationFailure:
    """Test that validation errors surface (no silent fallback)."""

    def test_invalid_response_raises_error(self) -> None:
        """If response fails validation, raise an error (no fallback to dict)."""
        from llm_lsp_cli.commands.shared import send_request
        from llm_lsp_cli.ipc import DaemonPositionParams

        params = DaemonPositionParams(
            workspace_path="/ws",
            file_path="/file.py",
            line=5,
            column=10,
        )

        # Invalid location (missing required 'range' field)
        daemon_response = {
            "locations": [
                {"uri": "file:///tmp/test.py"},  # Missing 'range'
            ]
        }

        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value=daemon_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            # Should raise ValidationError, not return dict
            with pytest.raises(Exception):
                send_request("textDocument/definition", params, language="python")


class TestSendRequestWorkspacePathExtraction:
    """Test workspace_path extraction from BaseModel params."""

    def test_workspace_path_from_base_model(self) -> None:
        """When params is BaseModel, extract workspace_path from model field."""
        from llm_lsp_cli.commands.shared import send_request
        from llm_lsp_cli.ipc import DaemonPositionParams

        params = DaemonPositionParams(
            workspace_path="/custom/workspace",
            file_path="/file.py",
            line=5,
            column=10,
        )

        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value={"locations": []})
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            send_request("textDocument/definition", params, language="python")

            # DaemonClient should be created with correct workspace_path
            call_kwargs = mock_client_class.call_args[1]
            assert call_kwargs["workspace_path"] == "/custom/workspace"


class TestSendRequestLanguageDetection:
    """Test language detection from BaseModel params."""

    def test_language_from_file_path_in_base_model(self) -> None:
        """When params is BaseModel, detect language from file_path field."""
        from llm_lsp_cli.commands.shared import send_request
        from llm_lsp_cli.ipc import DaemonPositionParams

        params = DaemonPositionParams(
            workspace_path="/ws",
            file_path="/file.ts",  # TypeScript file
            line=5,
            column=10,
        )

        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value={"locations": []})
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            # No explicit language - should detect from file extension
            send_request("textDocument/definition", params)

            call_kwargs = mock_client_class.call_args[1]
            # Language should be detected from .ts extension
            assert call_kwargs["language"] == "typescript"
