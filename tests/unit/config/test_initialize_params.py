"""Unit tests for build_initialize_params integration with capabilities loading."""

import os
from pathlib import Path

import pytest


def _reset_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset the capabilities cache to empty dict."""
    monkeypatch.setattr(
        "llm_lsp_cli.config.capabilities._capabilities_cache",
        {},
    )


class TestBuildInitializeParamsIntegration:
    """Tests for build_initialize_params using loaded capabilities."""

    def test_build_initialize_params_uses_loaded_capabilities(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """build_initialize_params uses JSON-loaded capabilities."""
        from llm_lsp_cli.config.initialize_params import build_initialize_params

        _reset_cache(monkeypatch)

        result = build_initialize_params(
            server_command="basedpyright-langserver",
            workspace_path=str(tmp_path),
        )

        # Should have loaded capabilities from JSON, not hardcoded minimal set
        assert "workspace" in result["capabilities"]
        assert "textDocument" in result["capabilities"]

    def test_build_initialize_params_injects_dynamic_fields(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Dynamic fields are injected into final params."""
        from llm_lsp_cli.config.initialize_params import build_initialize_params

        _reset_cache(monkeypatch)

        result = build_initialize_params(
            server_command="basedpyright-langserver",
            workspace_path=str(tmp_path),
        )

        assert result["processId"] == os.getpid()
        assert result["clientInfo"]["name"] == "llm-lsp-cli"
        assert "version" in result["clientInfo"]
        assert result["rootUri"].startswith("file://")
        assert len(result["workspaceFolders"]) == 1
        assert result["workspaceFolders"][0]["uri"] == result["rootUri"]

    def test_build_initialize_params_includes_init_options(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """initializationOptions from JSON are included in params."""
        from llm_lsp_cli.config.initialize_params import build_initialize_params

        _reset_cache(monkeypatch)

        result = build_initialize_params(
            server_command="basedpyright-langserver",
            workspace_path=str(tmp_path),
        )

        assert "initializationOptions" in result
        # basedpyright-langserver.json has disablePullDiagnostics
        assert "disablePullDiagnostics" in result["initializationOptions"]
