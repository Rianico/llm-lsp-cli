"""Tests for server name resolution with fallback chain.

This module tests the get_server_display_name function in output/server_name.py
which provides a priority-based fallback chain for determining the display name
of an LSP server.

Priority chain:
1. serverInfo.name from LSP initialize response (capitalized)
2. Command basename matched against known mapping
3. Command basename with first letter capitalized (fallback)
"""

from __future__ import annotations

import pytest


class TestGetServerDisplayName:
    """Test server name resolution with fallback chain."""

    def test_priority_1_server_info_name_used(self) -> None:
        """When serverInfo.name provided, use it with capitalization."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name="basedpyright",
            command_path="/usr/bin/anything"
        )
        assert result == "Basedpyright"

    def test_priority_2_command_basename_mapping(self) -> None:
        """When serverInfo.name is None, match command basename against known mapping."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name=None,
            command_path="/usr/bin/basedpyright-langserver"
        )
        assert result == "Basedpyright"

    def test_priority_3_command_basename_fallback(self) -> None:
        """When no mapping matches, use capitalized basename."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name=None,
            command_path="/opt/custom-lsp"
        )
        assert result == "Custom-lsp"

    def test_server_info_empty_string_treated_as_absent(self) -> None:
        """Empty string serverInfo.name triggers fallback."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name="",
            command_path="/usr/bin/pyright-langserver"
        )
        # Empty string should fall back to command path mapping
        assert result == "Pyright"

    def test_capitalize_first_letter_only(self) -> None:
        """Only first letter capitalized, rest preserved."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name="basedPyright",
            command_path="/usr/bin/anything"
        )
        assert result == "BasedPyright"

    def test_unknown_server_command_path(self) -> None:
        """Unknown server uses basename with first letter capitalized."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name=None,
            command_path="/home/user/my-custom-lsp-server"
        )
        assert result == "My-custom-lsp-server"

    def test_server_info_name_already_capitalized(self) -> None:
        """Already capitalized name preserved correctly."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name="RustAnalyzer",
            command_path="/usr/bin/rust-analyzer"
        )
        assert result == "RustAnalyzer"

    def test_empty_command_path(self) -> None:
        """Empty command path handled gracefully."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name=None,
            command_path=""
        )
        # Empty command path should return empty string
        assert result == ""


class TestServerNameLanguageFallback:
    """Test language-based fallback when server_info and command_path are unavailable."""

    def test_server_name_with_language_fallback_python(self) -> None:
        """When language='python' and no server_info/command_path, use basedpyright."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name=None,
            command_path="",
            language="python",
        )
        assert result == "Basedpyright"

    def test_server_name_with_language_fallback_typescript(self) -> None:
        """When language='typescript' and no server_info/command_path, use TypeScript."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name=None,
            command_path="",
            language="typescript",
        )
        assert result == "TypeScript"

    def test_server_name_with_language_fallback_rust(self) -> None:
        """When language='rust' and no server_info/command_path, use Rust Analyzer."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name=None,
            command_path="",
            language="rust",
        )
        assert result == "Rust Analyzer"

    def test_server_name_with_language_fallback_go(self) -> None:
        """When language='go' and no server_info/command_path, use Go."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name=None,
            command_path="",
            language="go",
        )
        assert result == "Go"

    def test_server_name_priority_server_info_over_language(self) -> None:
        """server_info takes priority over language fallback."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name="pyright",
            command_path="",
            language="python",
        )
        assert result == "Pyright"

    def test_server_name_priority_command_path_over_language(self) -> None:
        """command_path takes priority over language fallback."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name=None,
            command_path="custom-server",
            language="python",
        )
        assert result == "Custom-server"

    def test_server_name_unknown_language(self) -> None:
        """Unknown language returns empty string."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name=None,
            command_path="",
            language="unknown-lang",
        )
        assert result == ""

    def test_server_name_empty_language(self) -> None:
        """Empty language returns empty string."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name=None,
            command_path="",
            language="",
        )
        assert result == ""


class TestServerNameMapping:
    """Test the known server name mappings."""

    def test_pyright_mapping(self) -> None:
        """pyright-langserver maps to Pyright."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name=None,
            command_path="/usr/bin/pyright-langserver"
        )
        assert result == "Pyright"

    def test_basedpyright_mapping(self) -> None:
        """basedpyright-langserver maps to Basedpyright."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name=None,
            command_path="/usr/bin/basedpyright-langserver"
        )
        assert result == "Basedpyright"

    def test_typescript_mapping(self) -> None:
        """typescript-language-server maps to TypeScript."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name=None,
            command_path="/usr/bin/typescript-language-server"
        )
        assert result == "TypeScript"

    def test_rust_analyzer_mapping(self) -> None:
        """rust-analyzer maps to Rust Analyzer."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name=None,
            command_path="/usr/bin/rust-analyzer"
        )
        assert result == "Rust Analyzer"

    def test_gopls_mapping(self) -> None:
        """gopls maps to Go."""
        from llm_lsp_cli.output.server_name import get_server_display_name

        result = get_server_display_name(
            server_info_name=None,
            command_path="/usr/bin/gopls"
        )
        assert result == "Go"
