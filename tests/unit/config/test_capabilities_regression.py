"""Regression tests for existing capabilities behavior."""

from pathlib import Path

import pytest


class TestCapabilitiesRegression:
    """Regression tests ensuring existing functions still work."""

    def test_match_server_filter_exact_match(self):
        """Exact match still works."""
        from llm_lsp_cli.config.capabilities import _match_server_filter

        assert (
            _match_server_filter("pyright", "pyright", "pyright-langserver.json")
            is True
        )
        assert (
            _match_server_filter(
                "pyright-langserver", "pyright", "pyright-langserver.json"
            )
            is True
        )

    def test_match_server_filter_prefix_match(self):
        """Prefix match (e.g., basedpyright matches basedpyright-langserver)."""
        from llm_lsp_cli.config.capabilities import _match_server_filter

        assert (
            _match_server_filter(
                "basedpyright", "basedpyright", "basedpyright-langserver.json"
            )
            is True
        )
        assert (
            _match_server_filter(
                "basedpyright-langserver",
                "basedpyright",
                "basedpyright-langserver.json",
            )
            is True
        )

    def test_load_server_capability_returns_none_for_missing(self):
        """_load_server_capability returns None for missing files."""
        from llm_lsp_cli.config.capabilities import _load_server_capability

        result = _load_server_capability(Path("/nonexistent"), "missing.json")
        assert result is None

    def test_get_server_capabilities_still_works(self):
        """Existing get_server_capabilities function still works."""
        from llm_lsp_cli.config.capabilities import get_server_capabilities

        result = get_server_capabilities()

        assert isinstance(result, dict)
        assert len(result) > 0
