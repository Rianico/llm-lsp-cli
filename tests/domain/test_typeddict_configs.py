"""Tests for TypedDict configurations."""

from typing import get_type_hints

from llm_lsp_cli.config.types import (
    ServerConfig,
    InitializeParams,
    CapabilityConfig,
    LspMethodConfigDict,
    WorkspaceFolder,
    ClientCapabilities,
    TextDocumentClientCapabilities,
    LanguageConfig,
    RuntimePaths,
)


class TestServerConfig:
    """Tests for ServerConfig TypedDict."""

    def test_server_config_has_required_keys(self):
        """Verify ServerConfig has expected keys."""
        hints = get_type_hints(ServerConfig)

        # Expected keys
        assert "language_id" in hints
        assert "command" in hints

    def test_server_config_allows_optional_keys(self):
        """Verify ServerConfig allows optional configuration keys."""
        # Should be able to construct with minimal keys
        config: ServerConfig = {
            "language_id": "python",
            "command": "pyright-langserver",
        }
        assert config["language_id"] == "python"
        assert config["command"] == "pyright-langserver"

    def test_server_config_with_args(self):
        """Verify ServerConfig accepts optional args."""
        config: ServerConfig = {
            "language_id": "typescript",
            "command": "typescript-language-server",
            "args": ["--stdio"],
            "enabled": True,
        }
        assert config["args"] == ["--stdio"]
        assert config["enabled"] is True


class TestInitializeParams:
    """Tests for InitializeParams TypedDict."""

    def test_initialize_params_structure(self):
        """Verify InitializeParams has LSP initialize structure."""
        params: InitializeParams = {
            "processId": 12345,
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
            "locale": "en",
            "rootPath": "/tmp/workspace",
            "rootUri": "file:///tmp/workspace",
            "capabilities": {},
            "trace": "off",
        }
        assert params["processId"] == 12345
        assert params["clientInfo"]["name"] == "test-client"

    def test_initialize_params_minimal(self):
        """Verify InitializeParams works with minimal fields."""
        params: InitializeParams = {
            "processId": None,
            "capabilities": {},
        }
        assert params["processId"] is None


class TestCapabilityConfig:
    """Tests for CapabilityConfig TypedDict."""

    def test_capability_config_text_document_sync(self):
        """Verify CapabilityConfig supports textDocumentSync."""
        config: CapabilityConfig = {
            "textDocumentSync": {
                "openClose": True,
                "change": 1,  # Full sync
            },
            "definitionProvider": True,
        }
        # Use .get() for safer access to nested TypedDict
        sync_config = config.get("textDocumentSync", {})
        assert isinstance(sync_config, dict)
        assert sync_config.get("openClose") is True
        assert config.get("definitionProvider") is True

    def test_capability_config_providers(self):
        """Verify CapabilityConfig supports various providers."""
        config: CapabilityConfig = {
            "definitionProvider": True,
            "referencesProvider": True,
            "hoverProvider": True,
            "documentSymbolProvider": True,
            "workspaceSymbolProvider": True,
        }
        assert config["definitionProvider"] is True
        assert config["referencesProvider"] is True


class TestLspMethodConfigDict:
    """Tests for LspMethodConfigDict TypedDict."""

    def test_method_config_dict_structure(self):
        """Verify LspMethodConfigDict has correct structure."""
        config: LspMethodConfigDict = {
            "registry_method": "request_definition",
            "required_params": ["textDocument", "position"],
            "param_mapping": {"uri": "textDocument.uri"},
        }
        assert config["registry_method"] == "request_definition"
        assert "textDocument" in config["required_params"]
        assert config["param_mapping"]["uri"] == "textDocument.uri"

    def test_method_config_dict_empty_params(self):
        """Verify LspMethodConfigDict works with empty params."""
        config: LspMethodConfigDict = {
            "registry_method": "request_workspace_diagnostics",
            "required_params": [],
            "param_mapping": {},
        }
        assert config["registry_method"] == "request_workspace_diagnostics"
        assert config["required_params"] == []


class TestWorkspaceFolder:
    """Tests for WorkspaceFolder TypedDict."""

    def test_workspace_folder_structure(self):
        """Verify WorkspaceFolder has correct structure."""
        folder: WorkspaceFolder = {
            "uri": "file:///tmp/workspace",
            "name": "workspace",
        }
        assert folder["uri"] == "file:///tmp/workspace"
        assert folder["name"] == "workspace"


class TestClientCapabilities:
    """Tests for ClientCapabilities TypedDict."""

    def test_client_capabilities_structure(self):
        """Verify ClientCapabilities has correct structure."""
        caps: ClientCapabilities = {
            "workspace": {},
            "textDocument": {},
            "window": {},
        }
        assert caps["workspace"] is not None
        assert caps["textDocument"] is not None


class TestTextDocumentClientCapabilities:
    """Tests for TextDocumentClientCapabilities TypedDict."""

    def test_text_document_capabilities(self):
        """Verify TextDocumentClientCapabilities has correct structure."""
        caps: TextDocumentClientCapabilities = {
            "synchronization": {},
            "completion": {},
            "hover": {},
            "definition": {},
            "references": {},
            "documentSymbol": {},
        }
        assert caps["synchronization"] is not None
        assert caps["definition"] is not None


class TestLanguageConfig:
    """Tests for LanguageConfig TypedDict."""

    def test_language_config_structure(self):
        """Verify LanguageConfig has correct structure."""
        config: LanguageConfig = {
            "command": "pyright-langserver",
            "args": ["--stdio"],
            "file_patterns": ["*.py"],
            "priority": 1,
        }
        assert config["command"] == "pyright-langserver"
        assert config["file_patterns"] == ["*.py"]

    def test_language_config_minimal(self):
        """Verify LanguageConfig works with minimal fields."""
        config: LanguageConfig = {
            "command": "rust-analyzer",
        }
        assert config["command"] == "rust-analyzer"


class TestRuntimePaths:
    """Tests for RuntimePaths TypedDict."""

    def test_runtime_paths_structure(self):
        """Verify RuntimePaths has correct structure."""
        paths: RuntimePaths = {
            "socket_path": "/tmp/llm-lsp/socket.sock",
            "pid_file": "/tmp/llm-lsp/pid.lock",
            "log_file": "/tmp/llm-lsp/log.txt",
            "daemon_log_file": "/tmp/llm-lsp/daemon.log",
        }
        assert paths["socket_path"] == "/tmp/llm-lsp/socket.sock"
        assert paths["pid_file"] == "/tmp/llm-lsp/pid.lock"
