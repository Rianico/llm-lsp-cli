"""Unit tests for _extract_server_name_from_path function."""

from pathlib import Path

import pytest


class TestExtractServerNameFromPath:
    """Tests for _extract_server_name_from_path function."""

    def test_extract_server_name_from_full_path(self):
        """Extract basename from full absolute path."""
        from llm_lsp_cli.config.capabilities import _extract_server_name_from_path

        result = _extract_server_name_from_path(
            "/home/user/.local/share/nvim/mason/bin/basedpyright-langserver"
        )
        assert result == "basedpyright-langserver"

    def test_extract_server_name_from_relative_path(self):
        """Extract basename from relative path."""
        from llm_lsp_cli.config.capabilities import _extract_server_name_from_path

        result = _extract_server_name_from_path(
            "./node_modules/.bin/typescript-language-server"
        )
        assert result == "typescript-language-server"

    def test_extract_server_name_from_basename(self):
        """Return unchanged when input is already basename."""
        from llm_lsp_cli.config.capabilities import _extract_server_name_from_path

        result = _extract_server_name_from_path("rust-analyzer")
        assert result == "rust-analyzer"

    def test_extract_server_name_with_special_chars(self):
        """Handle paths with spaces and special characters."""
        from llm_lsp_cli.config.capabilities import _extract_server_name_from_path

        result = _extract_server_name_from_path("/path with spaces/server-name.sh")
        assert result == "server-name.sh"
