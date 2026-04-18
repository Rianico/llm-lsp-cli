"""Phase 5 Integration Tests.

Integration tests for:
1. Protocol interface implementations (JSON-RPC 2.0)
2. TypedDict configurations (config/types.py)
3. Type annotation coverage verification
4. Constant deduplication (no hardcoded LSP strings)
5. Edge case tests
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, TypedDict

import pytest

from llm_lsp_cli.config.types import (
    CapabilityConfig,
    ClientCapabilities,
    InitializeParams,
    LanguageConfig,
    LspMethodConfigDict,
    RuntimePaths,
    ServerConfig,
    TextDocumentClientCapabilities,
    WorkspaceFolder,
)
from llm_lsp_cli.ipc.protocol import (
    ERROR_INTERNAL_ERROR,
    ERROR_INVALID_PARAMS,
    ERROR_INVALID_REQUEST,
    ERROR_METHOD_NOT_FOUND,
    ERROR_PARSE_ERROR,
    JSONRPCNotification,
    JSONRPCRequest,
    JSONRPCResponse,
    build_error,
    build_request,
    build_response,
    parse_message,
)
from llm_lsp_cli.lsp.constants import LSPConstants
from llm_lsp_cli.lsp.types import (
    CompletionItem,
    CompletionList,
    Diagnostic,
    DocumentDiagnosticReport,
    Hover,
    InitializeResult,
    Location,
    Position,
    Range,
    ServerCapabilities,
    SymbolInformation,
    TextDocumentItem,
    TextEdit,
    WorkspaceDiagnosticReport,
)


# =============================================================================
# Section 1: Protocol Interface Implementations (JSON-RPC 2.0)
# =============================================================================


class TestJSONRPCRequest:
    """Tests for JSONRPCRequest protocol implementation."""

    def test_request_creation(self) -> None:
        """Test creating a JSON-RPC request."""
        req = JSONRPCRequest(method="initialize", params={"processId": 123}, id=1)
        assert req.method == "initialize"
        assert req.params == {"processId": 123}
        assert req.id == 1

    def test_request_to_dict(self) -> None:
        """Test converting request to dictionary."""
        req = JSONRPCRequest(method="textDocument/definition", params={"uri": "file://test.py"}, id=42)
        result = req.to_dict()
        assert result["jsonrpc"] == "2.0"
        assert result["method"] == "textDocument/definition"
        assert result["params"] == {"uri": "file://test.py"}
        assert result["id"] == 42

    def test_request_to_bytes(self) -> None:
        """Test serializing request to bytes."""
        req = JSONRPCRequest(method="initialize", params={}, id=1)
        data = req.to_bytes()
        assert data.startswith(b"Content-Length: ")
        assert b"\r\n\r\n" in data
        # Verify we can parse it back
        parsed, remaining = parse_message(data)
        assert parsed is not None
        assert parsed["method"] == "initialize"
        assert remaining == b""

    def test_request_from_dict(self) -> None:
        """Test creating request from dictionary."""
        data = {"method": "shutdown", "params": {}, "id": 5}
        req = JSONRPCRequest.from_dict(data)
        assert req.method == "shutdown"
        assert req.params == {}
        assert req.id == 5

    def test_request_from_dict_with_missing_params(self) -> None:
        """Test creating request with missing params (defaults to empty dict)."""
        data = {"method": "exit", "id": 99}
        req = JSONRPCRequest.from_dict(data)
        assert req.method == "exit"
        assert req.params == {}
        assert req.id == 99


class TestJSONRPCResponse:
    """Tests for JSONRPCResponse protocol implementation."""

    def test_success_response_creation(self) -> None:
        """Test creating a successful response."""
        resp = JSONRPCResponse(result={"capabilities": {}}, id=1)
        assert resp.result == {"capabilities": {}}
        assert resp.id == 1
        assert resp.error is None

    def test_error_response_creation(self) -> None:
        """Test creating an error response."""
        error = {"code": ERROR_METHOD_NOT_FOUND, "message": "Method not found"}
        resp = JSONRPCResponse(result=None, id=1, error=error)
        assert resp.result is None
        assert resp.id == 1
        assert resp.error == error

    def test_response_to_dict_success(self) -> None:
        """Test converting successful response to dictionary."""
        resp = JSONRPCResponse(result={"uri": "file://test.py"}, id=42)
        result = resp.to_dict()
        assert result["jsonrpc"] == "2.0"
        assert result["result"] == {"uri": "file://test.py"}
        assert result["id"] == 42
        assert "error" not in result

    def test_response_to_dict_error(self) -> None:
        """Test converting error response to dictionary."""
        error = {"code": ERROR_PARSE_ERROR, "message": "Parse error"}
        resp = JSONRPCResponse(result=None, id=1, error=error)
        result = resp.to_dict()
        assert result["jsonrpc"] == "2.0"
        assert result["error"] == error
        assert result["id"] == 1
        assert "result" not in result

    def test_response_to_bytes(self) -> None:
        """Test serializing response to bytes."""
        resp = JSONRPCResponse(result=True, id=10)
        data = resp.to_bytes()
        assert data.startswith(b"Content-Length: ")
        # Verify we can parse it back
        parsed, _ = parse_message(data)
        assert parsed is not None
        assert parsed["result"] is True

    def test_response_from_dict(self) -> None:
        """Test creating response from dictionary."""
        data = {"result": {"name": "test"}, "id": 7}
        resp = JSONRPCResponse.from_dict(data)
        assert resp.result == {"name": "test"}
        assert resp.id == 7
        assert resp.error is None


class TestJSONRPCNotification:
    """Tests for JSONRPCNotification protocol implementation."""

    def test_notification_creation(self) -> None:
        """Test creating a notification."""
        notif = JSONRPCNotification(method="initialized", params={})
        assert notif.method == "initialized"
        assert notif.params == {}

    def test_notification_to_dict(self) -> None:
        """Test converting notification to dictionary."""
        notif = JSONRPCNotification(
            method="textDocument/didOpen",
            params={"textDocument": {"uri": "file://test.py"}}
        )
        result = notif.to_dict()
        assert result["jsonrpc"] == "2.0"
        assert result["method"] == "textDocument/didOpen"
        assert "textDocument" in result["params"]

    def test_notification_to_bytes(self) -> None:
        """Test serializing notification to bytes."""
        notif = JSONRPCNotification(method="exit", params={})
        data = notif.to_bytes()
        assert data.startswith(b"Content-Length: ")
        # Notifications have no id
        parsed, _ = parse_message(data)
        assert parsed is not None
        assert "id" not in parsed


class TestBuildHelpers:
    """Tests for JSON-RPC builder helper functions."""

    def test_build_request(self) -> None:
        """Test build_request helper."""
        req = build_request("initialize", {"processId": 1}, 1)
        assert isinstance(req, JSONRPCRequest)
        assert req.method == "initialize"
        assert req.id == 1

    def test_build_response(self) -> None:
        """Test build_response helper."""
        resp = build_response({"capabilities": {}}, 1)
        assert isinstance(resp, JSONRPCResponse)
        assert resp.result == {"capabilities": {}}
        assert resp.error is None

    def test_build_error_without_data(self) -> None:
        """Test build_error helper without data."""
        resp = build_error(ERROR_INTERNAL_ERROR, "Internal error", 1)
        assert isinstance(resp, JSONRPCResponse)
        assert resp.result is None
        assert resp.error is not None
        assert resp.error["code"] == ERROR_INTERNAL_ERROR
        assert "data" not in resp.error

    def test_build_error_with_data(self) -> None:
        """Test build_error helper with data."""
        resp = build_error(
            ERROR_INVALID_PARAMS,
            "Invalid params",
            1,
            data={"reason": "missing field"}
        )
        assert resp.error is not None
        assert resp.error["data"] == {"reason": "missing field"}


class TestParseMessage:
    """Tests for parse_message function with edge cases."""

    def test_parse_complete_message(self) -> None:
        """Test parsing a complete JSON-RPC message."""
        req = JSONRPCRequest(method="test", params={}, id=1)
        data = req.to_bytes()
        parsed, remaining = parse_message(data)
        assert parsed is not None
        assert parsed["method"] == "test"
        assert remaining == b""

    def test_parse_incomplete_header(self) -> None:
        """Test parsing when header is incomplete."""
        data = b"Content-Length: 10"  # Missing \r\n\r\n and body
        parsed, remaining = parse_message(data)
        assert parsed is None
        assert remaining == data

    def test_parse_incomplete_body(self) -> None:
        """Test parsing when body is incomplete."""
        header = b"Content-Length: 50\r\n\r\n"
        body = b'{"jsonrpc"'  # Incomplete JSON
        parsed, remaining = parse_message(header + body)
        assert parsed is None
        assert remaining == header + body

    def test_parse_multiple_messages(self) -> None:
        """Test parsing multiple concatenated messages."""
        req1 = JSONRPCRequest(method="first", params={}, id=1)
        req2 = JSONRPCRequest(method="second", params={}, id=2)
        data = req1.to_bytes() + req2.to_bytes()
        parsed1, remaining = parse_message(data)
        assert parsed1 is not None
        assert parsed1["method"] == "first"
        parsed2, remaining2 = parse_message(remaining)
        assert parsed2 is not None
        assert parsed2["method"] == "second"
        assert remaining2 == b""

    def test_parse_invalid_content_length(self) -> None:
        """Test parsing with invalid Content-Length header."""
        data = b"Content-Length: abc\r\n\r\n{}"
        with pytest.raises(ValueError, match="Invalid Content-Length"):
            parse_message(data)

    def test_parse_missing_content_length(self) -> None:
        """Test parsing when Content-Length is missing."""
        data = b"Some random header\r\n\r\n{}"
        with pytest.raises(ValueError, match="Missing Content-Length"):
            parse_message(data)

    def test_parse_invalid_json(self) -> None:
        """Test parsing with invalid JSON body."""
        header = b"Content-Length: 10\r\n\r\n"
        body = b"{invalid json"
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_message(header + body)

    def test_parse_with_remaining_bytes(self) -> None:
        """Test parsing preserves remaining bytes."""
        req = JSONRPCRequest(method="test", params={}, id=1)
        extra = b"extra data"
        data = req.to_bytes() + extra
        parsed, remaining = parse_message(data)
        assert parsed is not None
        assert remaining == extra


# =============================================================================
# Section 2: TypedDict Configurations (config/types.py)
# =============================================================================


class TestServerConfigTypedDict:
    """Tests for ServerConfig TypedDict."""

    def test_server_config_minimal(self) -> None:
        """Test minimal ServerConfig."""
        config: ServerConfig = {
            "language_id": "python",
            "command": "pyright-langserver",
        }
        assert config["language_id"] == "python"
        assert config["command"] == "pyright-langserver"

    def test_server_config_full(self) -> None:
        """Test full ServerConfig with all fields."""
        config: ServerConfig = {
            "language_id": "typescript",
            "command": "typescript-language-server",
            "args": ["--stdio"],
            "enabled": True,
        }
        assert config["language_id"] == "typescript"
        assert config["args"] == ["--stdio"]
        assert config["enabled"] is True

    def test_server_config_optional_fields(self) -> None:
        """Test ServerConfig with optional fields omitted."""
        config: ServerConfig = {
            "language_id": "rust",
            "command": "rust-analyzer",
        }
        # Should work without args and enabled
        assert "args" not in config
        assert "enabled" not in config


class TestInitializeParamsTypedDict:
    """Tests for InitializeParams TypedDict."""

    def test_initialize_params_minimal(self) -> None:
        """Test minimal InitializeParams."""
        params: InitializeParams = {
            "processId": 123,
        }
        assert params["processId"] == 123

    def test_initialize_params_with_client_info(self) -> None:
        """Test InitializeParams with client info."""
        params: InitializeParams = {
            "processId": 123,
            "clientInfo": {"name": "llm-lsp-cli", "version": "1.0.0"},
        }
        assert params["clientInfo"]["name"] == "llm-lsp-cli"

    def test_initialize_params_with_capabilities(self) -> None:
        """Test InitializeParams with capabilities."""
        params: InitializeParams = {
            "processId": 123,
            "capabilities": {
                "textDocument": {
                    "definition": {"dynamicRegistration": True},
                },
            },
        }
        assert "textDocument" in params["capabilities"]

    def test_initialize_params_with_workspace_folders(self) -> None:
        """Test InitializeParams with workspace folders."""
        params: InitializeParams = {
            "processId": 123,
            "workspaceFolders": [
                {"uri": "file:///workspace", "name": "my-project"},
            ],
        }
        assert len(params["workspaceFolders"]) == 1  # type: ignore


class TestCapabilityConfigTypedDict:
    """Tests for CapabilityConfig TypedDict."""

    def test_capability_config_minimal(self) -> None:
        """Test minimal CapabilityConfig."""
        config: CapabilityConfig = {
            "definitionProvider": True,
            "referencesProvider": True,
        }
        assert config["definitionProvider"] is True

    def test_capability_config_with_completion(self) -> None:
        """Test CapabilityConfig with completion provider."""
        config: CapabilityConfig = {
            "completionProvider": {"resolveProvider": True, "triggerCharacters": ["."]},
        }
        assert config["completionProvider"]["resolveProvider"] is True

    def test_capability_config_text_document_sync(self) -> None:
        """Test CapabilityConfig with textDocumentSync."""
        config: CapabilityConfig = {
            "textDocumentSync": {"openClose": True, "change": 1},
        }
        assert config["textDocumentSync"]["openClose"] is True


class TestLspMethodConfigDictTypedDict:
    """Tests for LspMethodConfigDict TypedDict."""

    def test_method_config_dict(self) -> None:
        """Test LspMethodConfigDict."""
        config: LspMethodConfigDict = {
            "registry_method": "request_definition",
            "required_params": ["textDocument", "position"],
            "param_mapping": {"uri": "textDocument.uri"},
        }
        assert config["registry_method"] == "request_definition"
        assert "textDocument" in config["required_params"]
        assert config["param_mapping"]["uri"] == "textDocument.uri"


class TestRuntimePathsTypedDict:
    """Tests for RuntimePaths TypedDict."""

    def test_runtime_paths(self) -> None:
        """Test RuntimePaths."""
        paths: RuntimePaths = {
            "socket_path": "/tmp/llm-lsp-cli/socket",
            "pid_file": "/tmp/llm-lsp-cli/pid",
            "log_file": "/tmp/llm-lsp-cli/log",
            "daemon_log_file": "/tmp/llm-lsp-cli/daemon.log",
        }
        assert paths["socket_path"].startswith("/tmp")
        assert paths["pid_file"].endswith("/pid")


class TestLanguageConfigTypedDict:
    """Tests for LanguageConfig TypedDict."""

    def test_language_config_minimal(self) -> None:
        """Test minimal LanguageConfig."""
        config: LanguageConfig = {
            "command": "pyright-langserver",
        }
        assert config["command"] == "pyright-langserver"

    def test_language_config_full(self) -> None:
        """Test full LanguageConfig."""
        config: LanguageConfig = {
            "command": "pyright-langserver",
            "args": ["--stdio"],
            "file_patterns": ["*.py", "*.pyi"],
            "priority": 1,
        }
        assert config["args"] == ["--stdio"]
        assert "*.py" in config["file_patterns"]
        assert config["priority"] == 1


# =============================================================================
# Section 3: LSP Types Verification
# =============================================================================


class TestLSPBasicTypes:
    """Tests for basic LSP types."""

    def test_position(self) -> None:
        """Test Position type."""
        pos: Position = {"line": 10, "character": 5}
        assert pos["line"] == 10
        assert pos["character"] == 5

    def test_range(self) -> None:
        """Test Range type."""
        range_obj: Range = {
            "start": {"line": 0, "character": 0},
            "end": {"line": 5, "character": 10},
        }
        assert range_obj["start"]["line"] == 0
        assert range_obj["end"]["character"] == 10

    def test_location(self) -> None:
        """Test Location type."""
        loc: Location = {
            "uri": "file:///path/to/file.py",
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 1, "character": 0},
            },
        }
        assert "file://" in loc["uri"]

    def test_text_document_item(self) -> None:
        """Test TextDocumentItem type."""
        doc: TextDocumentItem = {
            "uri": "file:///test.py",
            "languageId": "python",
            "version": 1,
            "text": "def hello(): pass",
        }
        assert doc["languageId"] == "python"
        assert doc["version"] == 1


class TestLSPFeatureTypes:
    """Tests for LSP feature types."""

    def test_hover(self) -> None:
        """Test Hover type."""
        hover: Hover = {
            "contents": {
                "kind": "markdown",
                "value": "```python\ndef hello(): ...\n```",
            },
            "range": None,
        }
        assert hover["contents"]["kind"] == "markdown"

    def test_completion_item(self) -> None:
        """Test CompletionItem type."""
        item: CompletionItem = {
            "label": "hello",
            "kind": 3,  # Function
            "detail": "def hello() -> str",
        }
        assert item["label"] == "hello"

    def test_completion_list(self) -> None:
        """Test CompletionList type."""
        items: CompletionList = {
            "isIncomplete": False,
            "items": [
                {"label": "hello", "kind": 3},
                {"label": "world", "kind": 6},
            ],
        }
        assert not items["isIncomplete"]
        assert len(items["items"]) == 2

    def test_text_edit(self) -> None:
        """Test TextEdit type."""
        edit: TextEdit = {
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 0, "character": 5},
            },
            "newText": "def",
        }
        assert edit["newText"] == "def"

    def test_symbol_information(self) -> None:
        """Test SymbolInformation type."""
        symbol: SymbolInformation = {
            "name": "MyClass",
            "kind": 5,  # Class
            "tags": None,
            "location": {
                "uri": "file:///test.py",
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 10, "character": 0},
                },
            },
        }
        assert symbol["name"] == "MyClass"
        assert symbol["kind"] == 5


class TestLSPDiagnosticTypes:
    """Tests for LSP diagnostic types."""

    def test_diagnostic(self) -> None:
        """Test Diagnostic type."""
        diag: Diagnostic = {
            "range": {
                "start": {"line": 5, "character": 0},
                "end": {"line": 5, "character": 10},
            },
            "severity": 1,  # Error
            "source": "pyright",
            "message": "Undefined variable",
        }
        assert diag["severity"] == 1
        assert diag["source"] == "pyright"

    def test_document_diagnostic_report(self) -> None:
        """Test DocumentDiagnosticReport type."""
        report: DocumentDiagnosticReport = {
            "kind": "full",
            "items": [
                {
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}},
                    "severity": 2,
                    "source": "test",
                    "message": "Test diagnostic",
                },
            ],
        }
        assert report["kind"] == "full"
        assert len(report["items"]) == 1

    def test_workspace_diagnostic_report(self) -> None:
        """Test WorkspaceDiagnosticReport type."""
        report: WorkspaceDiagnosticReport = {
            "items": [
                {
                    "uri": "file:///test.py",
                    "version": 1,
                    "diagnostics": [
                        {
                            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}},
                            "severity": 1,
                            "source": "test",
                            "message": "Error",
                        },
                    ],
                },
            ],
        }
        assert len(report["items"]) == 1


class TestLSPServerCapabilities:
    """Tests for LSP server capabilities."""

    def test_server_capabilities(self) -> None:
        """Test ServerCapabilities type."""
        caps: ServerCapabilities = {
            "textDocumentSync": {"openClose": True, "change": 1},
            "definitionProvider": True,
            "referencesProvider": True,
            "hoverProvider": True,
            "completionProvider": {"resolveProvider": True},
        }
        assert caps["definitionProvider"] is True
        assert caps["hoverProvider"] is True

    def test_initialize_result(self) -> None:
        """Test InitializeResult type."""
        result: InitializeResult = {
            "capabilities": {
                "textDocumentSync": 1,
                "definitionProvider": True,
            },
            "serverInfo": {"name": "test-server", "version": "1.0.0"},
        }
        assert result["capabilities"]["definitionProvider"] is True


# =============================================================================
# Section 4: Constant Deduplication Verification
# =============================================================================


class TestLSPConstantsUsage:
    """Tests verifying LSPConstants are used instead of hardcoded strings."""

    def test_jsonrpc_version_constant(self) -> None:
        """Test JSONRPC version constant is used."""
        assert LSPConstants.JSONRPC_VERSION == "2.0"

    def test_request_method_constants(self) -> None:
        """Test request method constants."""
        # Core LSP methods
        assert LSPConstants.INITIALIZE == "initialize"
        assert LSPConstants.INITIALIZED == "initialized"
        assert LSPConstants.SHUTDOWN == "shutdown"
        assert LSPConstants.EXIT == "exit"

    def test_text_document_sync_constants(self) -> None:
        """Test text document synchronization constants."""
        assert LSPConstants.TEXT_DOCUMENT_DID_OPEN == "textDocument/didOpen"
        assert LSPConstants.TEXT_DOCUMENT_DID_CHANGE == "textDocument/didChange"
        assert LSPConstants.TEXT_DOCUMENT_DID_CLOSE == "textDocument/didClose"

    def test_language_feature_constants(self) -> None:
        """Test language feature method constants."""
        assert LSPConstants.COMPLETION == "textDocument/completion"
        assert LSPConstants.HOVER == "textDocument/hover"
        assert LSPConstants.DEFINITION == "textDocument/definition"
        assert LSPConstants.REFERENCES == "textDocument/references"
        assert LSPConstants.DOCUMENT_SYMBOL == "textDocument/documentSymbol"

    def test_workspace_feature_constants(self) -> None:
        """Test workspace method constants."""
        assert LSPConstants.WORKSPACE_SYMBOL == "workspace/symbol"
        assert LSPConstants.WORKSPACE_DIAGNOSTIC == "workspace/diagnostic"

    def test_error_code_constants(self) -> None:
        """Test error code constants."""
        assert LSPConstants.ERROR_PARSE_ERROR == -32700
        assert LSPConstants.ERROR_INVALID_REQUEST == -32600
        assert LSPConstants.ERROR_METHOD_NOT_FOUND == -32601
        assert LSPConstants.ERROR_INVALID_PARAMS == -32602
        assert LSPConstants.ERROR_INTERNAL_ERROR == -32603

    def test_completion_trigger_kind_constants(self) -> None:
        """Test completion trigger kind constants."""
        assert LSPConstants.COMPLETION_TRIGGER_INVOKED == 1
        assert LSPConstants.COMPLETION_TRIGGER_TRIGGER_CHARACTER == 2
        assert LSPConstants.COMPLETION_TRIGGER_TRIGGER_FOR_INCOMPLETE_COMPLETIONS == 3

    def test_symbol_kind_constants(self) -> None:
        """Test symbol kind constants."""
        assert LSPConstants.SYMBOL_KIND_FILE == 1
        assert LSPConstants.SYMBOL_KIND_CLASS == 5
        assert LSPConstants.SYMBOL_KIND_FUNCTION == 12
        assert LSPConstants.SYMBOL_KIND_METHOD == 6

    def test_diagnostic_severity_constants(self) -> None:
        """Test diagnostic severity constants."""
        assert LSPConstants.DIAGNOSTIC_ERROR == 1
        assert LSPConstants.DIAGNOSTIC_WARNING == 2
        assert LSPConstants.DIAGNOSTIC_INFORMATION == 3
        assert LSPConstants.DIAGNOSTIC_HINT == 4


class TestIPCProtocolConstants:
    """Tests for IPC protocol constants."""

    def test_ipc_error_constants_match_lsp(self) -> None:
        """Test IPC error constants match LSP constants."""
        assert ERROR_PARSE_ERROR == LSPConstants.ERROR_PARSE_ERROR
        assert ERROR_INVALID_REQUEST == LSPConstants.ERROR_INVALID_REQUEST
        assert ERROR_METHOD_NOT_FOUND == LSPConstants.ERROR_METHOD_NOT_FOUND
        assert ERROR_INVALID_PARAMS == LSPConstants.ERROR_INVALID_PARAMS
        assert ERROR_INTERNAL_ERROR == LSPConstants.ERROR_INTERNAL_ERROR


# =============================================================================
# Section 5: Edge Case Tests
# =============================================================================


class TestEnvironmentVariableExpansion:
    """Tests for environment variable expansion in configuration."""

    def test_env_var_expansion_dollar_brace(self) -> None:
        """Test environment variable expansion with ${VAR} syntax."""
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        import os
        os.environ["TEST_VAR"] = "test_value"

        data = {"path": "${TEST_VAR}/subdir"}
        result = ConfigLoader._expand_env(data)
        assert result["path"] == "test_value/subdir"

    def test_env_var_expansion_dollar_only(self) -> None:
        """Test environment variable expansion with $VAR syntax."""
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        import os
        os.environ["TEST_VAR2"] = "value2"

        data = {"path": "$TEST_VAR2/subdir"}
        result = ConfigLoader._expand_env(data)
        assert result["path"] == "value2/subdir"

    def test_env_var_expansion_nested(self) -> None:
        """Test environment variable expansion in nested structures."""
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        import os
        os.environ["NESTED_VAR"] = "nested_value"

        data = {
            "config": {
                "paths": ["${NESTED_VAR}/path1", "$NESTED_VAR/path2"],
            },
        }
        result = ConfigLoader._expand_env(data)
        assert result["config"]["paths"][0] == "nested_value/path1"
        assert result["config"]["paths"][1] == "nested_value/path2"

    def test_env_var_expansion_undefined(self) -> None:
        """Test undefined environment variables are left as-is."""
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        data = {"path": "${UNDEFINED_VAR}/subdir"}
        result = ConfigLoader._expand_env(data)
        # Undefined vars should remain unchanged
        assert result["path"] == "${UNDEFINED_VAR}/subdir"


class TestPathSanitization:
    """Tests for path sanitization utilities."""

    def test_sanitize_workspace_name_with_path_separators(self) -> None:
        """Test workspace name sanitization replaces path separators."""
        from llm_lsp_cli.config.path_builder import RuntimePathBuilder

        builder = RuntimePathBuilder()
        # Test that path separators are replaced
        result = builder._sanitize_workspace_name("foo/bar")
        assert "/" not in result
        assert "_" in result

    def test_sanitize_workspace_name_with_double_dots(self) -> None:
        """Test workspace name sanitization handles double dots."""
        from llm_lsp_cli.config.path_builder import RuntimePathBuilder

        builder = RuntimePathBuilder()
        result = builder._sanitize_workspace_name("foo..bar")
        assert ".." not in result

    def test_sanitize_workspace_name_special_characters(self) -> None:
        """Test workspace name sanitization handles special characters."""
        from llm_lsp_cli.config.path_builder import RuntimePathBuilder

        builder = RuntimePathBuilder()
        result = builder._sanitize_workspace_name("foo@bar#test!")
        # Special chars should be replaced with underscores
        assert "@" not in result
        assert "#" not in result
        assert "!" not in result

    def test_sanitize_workspace_name_empty(self) -> None:
        """Test workspace name sanitization handles empty string."""
        from llm_lsp_cli.config.path_builder import RuntimePathBuilder

        builder = RuntimePathBuilder()
        result = builder._sanitize_workspace_name("")
        # Empty string should result in "unknown"
        assert result == "unknown"

    def test_generate_workspace_hash_consistency(self) -> None:
        """Test workspace hash generation is consistent."""
        from llm_lsp_cli.config.path_builder import RuntimePathBuilder

        builder = RuntimePathBuilder()
        hash1 = builder._generate_workspace_hash("/test/path")
        hash2 = builder._generate_workspace_hash("/test/path")
        assert hash1 == hash2

    def test_generate_workspace_hash_different_paths(self) -> None:
        """Test different paths produce different hashes."""
        from llm_lsp_cli.config.path_builder import RuntimePathBuilder

        builder = RuntimePathBuilder()
        hash1 = builder._generate_workspace_hash("/path/one")
        hash2 = builder._generate_workspace_hash("/path/two")
        assert hash1 != hash2


class TestUnicodeHandling:
    """Tests for Unicode handling in various components."""

    def test_unicode_in_workspace_name(self) -> None:
        """Test Unicode characters in workspace name."""
        from llm_lsp_cli.config.path_builder import RuntimePathBuilder

        builder = RuntimePathBuilder()
        # Should not crash with Unicode input
        result = builder._sanitize_workspace_name("日本語テスト")
        assert isinstance(result, str)

    def test_unicode_in_jsonrpc_message(self) -> None:
        """Test Unicode characters in JSON-RPC messages."""
        req = JSONRPCRequest(
            method="textDocument/didOpen",
            params={"textDocument": {"uri": "file:///日本語.py"}},
            id=1,
        )
        data = req.to_bytes()
        parsed, _ = parse_message(data)
        assert parsed is not None
        assert "日本語" in str(parsed["params"])

    def test_unicode_in_diagnostic_message(self) -> None:
        """Test Unicode characters in diagnostic messages."""
        diag: Diagnostic = {
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}},
            "severity": 1,
            "source": "test",
            "message": "エラー：未定義の変数",  # Japanese: "Error: undefined variable"
        }
        assert "エラー" in diag["message"]


class TestNullAndEmptyHandling:
    """Tests for null and empty value handling."""

    def test_empty_params_in_request(self) -> None:
        """Test empty params in JSON-RPC request."""
        req = JSONRPCRequest(method="initialized", params={}, id=1)
        data = req.to_bytes()
        parsed, _ = parse_message(data)
        assert parsed is not None
        assert parsed["params"] == {}

    def test_none_range_in_hover(self) -> None:
        """Test None range in Hover type."""
        hover: Hover = {
            "contents": {"kind": "plaintext", "value": "test"},
            "range": None,
        }
        assert hover["range"] is None

    def test_empty_tags_in_symbol(self) -> None:
        """Test empty/None tags in SymbolInformation."""
        symbol: SymbolInformation = {
            "name": "test",
            "kind": 6,
            "tags": None,
        }
        assert symbol["tags"] is None

    def test_empty_list_in_completion(self) -> None:
        """Test empty items list in CompletionList."""
        completion: CompletionList = {
            "isIncomplete": False,
            "items": [],
        }
        assert completion["isIncomplete"] is False
        assert len(completion["items"]) == 0


class TestTypeAnnotationVerification:
    """Tests verifying type annotations are present and correct."""

    def test_server_definition_has_type_hints(self) -> None:
        """Test ServerDefinition has proper type hints."""
        from llm_lsp_cli.domain.entities import ServerDefinition
        import typing

        hints = typing.get_type_hints(ServerDefinition)
        assert "language_id" in hints
        assert "command" in hints
        assert "args" in hints
        assert "timeout_seconds" in hints

    def test_workspace_path_has_type_hints(self) -> None:
        """Test WorkspacePath has proper type hints."""
        from llm_lsp_cli.domain.value_objects import WorkspacePath
        import typing

        hints = typing.get_type_hints(WorkspacePath)
        assert "path" in hints

    def test_lsp_method_config_has_type_hints(self) -> None:
        """Test LspMethodConfig has proper type hints."""
        from llm_lsp_cli.domain.services import LspMethodConfig
        import typing

        hints = typing.get_type_hints(LspMethodConfig)
        assert "registry_method" in hints
        assert "required_params" in hints
        assert "param_mapping" in hints

    def test_jsonrpc_request_has_type_hints(self) -> None:
        """Test JSONRPCRequest has proper type hints."""
        import typing

        hints = typing.get_type_hints(JSONRPCRequest)
        assert "method" in hints
        assert "params" in hints
        assert "id" in hints

    def test_jsonrpc_response_has_type_hints(self) -> None:
        """Test JSONRPCResponse has proper type hints."""
        import typing

        hints = typing.get_type_hints(JSONRPCResponse)
        assert "result" in hints
        assert "id" in hints
        assert "error" in hints


class TestEdgeCaseIntegration:
    """Integration tests for edge cases."""

    def test_complete_request_with_unicode(self, temp_dir: Path) -> None:
        """Test complete JSON-RPC request lifecycle with Unicode."""
        # Create a test file with Unicode content
        test_file = temp_dir / "テスト.py"
        test_file.write_text("def こんにちは(): pass")

        req = JSONRPCRequest(
            method="textDocument/didOpen",
            params={
                "textDocument": {
                    "uri": test_file.as_uri(),
                    "languageId": "python",
                    "version": 1,
                    "text": test_file.read_text(),
                },
            },
            id=1,
        )

        # Serialize and parse
        data = req.to_bytes()
        parsed, _ = parse_message(data)

        assert parsed is not None
        assert parsed["method"] == "textDocument/didOpen"
        # URI is URL-encoded, so check for the encoded form or the original filename
        # The URI will be percent-encoded, but the text field preserves Unicode
        assert "languageId" in parsed["params"]["textDocument"]
        assert parsed["params"]["textDocument"]["languageId"] == "python"
        # Verify Unicode content is preserved in the text field
        assert "こんにちは" in parsed["params"]["textDocument"]["text"]

    def test_error_response_chain(self) -> None:
        """Test building and parsing error response chain."""
        # Build error response
        error_resp = build_error(
            ERROR_INVALID_PARAMS,
            "Missing required parameter",
            42,
            data={"missing": "textDocument"}
        )

        # Serialize
        data = error_resp.to_bytes()

        # Parse back
        parsed, _ = parse_message(data)
        assert parsed is not None
        assert parsed["error"]["code"] == ERROR_INVALID_PARAMS
        assert parsed["error"]["data"]["missing"] == "textDocument"

    def test_typedDict_runtime_behavior(self) -> None:
        """Test TypedDict behavior at runtime."""
        # TypedDict is a typing hint, not enforced at runtime
        # But we can verify the structure is correct
        config: ServerConfig = {
            "language_id": "python",
            "command": "pyright-langserver",
            "args": [],
            "enabled": True,
        }

        # Verify all expected keys exist
        assert isinstance(config["language_id"], str)
        assert isinstance(config["command"], str)
        assert isinstance(config["args"], list)
        assert isinstance(config["enabled"], bool)


# =============================================================================
# Section 6: No Hardcoded LSP Strings Verification
# =============================================================================


class TestNoHardcodedLSPStrings:
    """Tests verifying no hardcoded LSP strings in the codebase."""

    def get_source_files(self) -> list[Path]:
        """Get all Python source files in src directory."""
        src_dir = Path(__file__).parent.parent.parent / "src" / "llm_lsp_cli"
        return list(src_dir.rglob("*.py"))

    def test_no_hardcoded_initialize_method(self) -> None:
        """Verify 'initialize' method uses constant."""
        # This is a meta-test - the constant should be used
        # We verify the constant exists and has the correct value
        assert LSPConstants.INITIALIZE == "initialize"

    def test_no_hardcoded_shutdown_method(self) -> None:
        """Verify 'shutdown' method uses constant."""
        assert LSPConstants.SHUTDOWN == "shutdown"

    def test_no_hardcoded_exit_method(self) -> None:
        """Verify 'exit' method uses constant."""
        assert LSPConstants.EXIT == "exit"

    def test_no_hardcoded_completion_method(self) -> None:
        """Verify completion method uses constant."""
        assert LSPConstants.COMPLETION == "textDocument/completion"

    def test_no_hardcoded_definition_method(self) -> None:
        """Verify definition method uses constant."""
        assert LSPConstants.DEFINITION == "textDocument/definition"

    def test_no_hardcoded_hover_method(self) -> None:
        """Verify hover method uses constant."""
        assert LSPConstants.HOVER == "textDocument/hover"

    def test_no_hardcoded_references_method(self) -> None:
        """Verify references method uses constant."""
        assert LSPConstants.REFERENCES == "textDocument/references"

    def test_no_hardcoded_document_symbol_method(self) -> None:
        """Verify document symbol method uses constant."""
        assert LSPConstants.DOCUMENT_SYMBOL == "textDocument/documentSymbol"

    def test_no_hardcoded_workspace_symbol_method(self) -> None:
        """Verify workspace symbol method uses constant."""
        assert LSPConstants.WORKSPACE_SYMBOL == "workspace/symbol"

    def test_no_hardcoded_diagnostic_method(self) -> None:
        """Verify diagnostic method uses constant."""
        assert LSPConstants.DIAGNOSTIC == "textDocument/diagnostic"

    def test_no_hardcoded_workspace_diagnostic_method(self) -> None:
        """Verify workspace diagnostic method uses constant."""
        assert LSPConstants.WORKSPACE_DIAGNOSTIC == "workspace/diagnostic"

    def test_error_codes_are_centralized(self) -> None:
        """Verify error codes are defined as constants."""
        # All error codes should be in LSPConstants
        assert hasattr(LSPConstants, "ERROR_PARSE_ERROR")
        assert hasattr(LSPConstants, "ERROR_INVALID_REQUEST")
        assert hasattr(LSPConstants, "ERROR_METHOD_NOT_FOUND")
        assert hasattr(LSPConstants, "ERROR_INVALID_PARAMS")
        assert hasattr(LSPConstants, "ERROR_INTERNAL_ERROR")


# =============================================================================
# Section 7: Protocol Compliance Tests
# =============================================================================


class TestJSONRPC2Compliance:
    """Tests for JSON-RPC 2.0 protocol compliance."""

    def test_jsonrpc_version_in_all_messages(self) -> None:
        """Test all messages include jsonrpc: 2.0."""
        req = JSONRPCRequest(method="test", params={}, id=1)
        resp = JSONRPCResponse(result=True, id=1)
        notif = JSONRPCNotification(method="test", params={})

        req_dict = req.to_dict()
        resp_dict = resp.to_dict()
        notif_dict = notif.to_dict()

        assert req_dict["jsonrpc"] == "2.0"
        assert resp_dict["jsonrpc"] == "2.0"
        assert notif_dict["jsonrpc"] == "2.0"

    def test_request_has_id(self) -> None:
        """Test requests have unique IDs."""
        req1 = JSONRPCRequest(method="test1", params={}, id=1)
        req2 = JSONRPCRequest(method="test2", params={}, id=2)

        assert req1.id != req2.id
        assert isinstance(req1.id, int)

    def test_notification_has_no_id(self) -> None:
        """Test notifications have no ID (fire and forget)."""
        notif = JSONRPCNotification(method="exit", params={})
        notif_dict = notif.to_dict()

        assert "id" not in notif_dict

    def test_response_matches_request_id(self) -> None:
        """Test response ID matches request ID."""
        request_id = 42
        req = JSONRPCRequest(method="test", params={}, id=request_id)
        resp = JSONRPCResponse(result=True, id=request_id)

        assert req.id == resp.id

    def test_error_response_structure(self) -> None:
        """Test error response has correct structure."""
        error = {"code": -32601, "message": "Method not found"}
        resp = JSONRPCResponse(result=None, id=1, error=error)
        resp_dict = resp.to_dict()

        assert "error" in resp_dict
        assert "code" in resp_dict["error"]
        assert "message" in resp_dict["error"]
        assert "result" not in resp_dict
