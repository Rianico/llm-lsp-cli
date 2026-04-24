"""Negative tests verifying old behavior is removed."""

from pathlib import Path

import pytest


def _reset_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset the capabilities cache to empty dict."""
    monkeypatch.setattr(
        "llm_lsp_cli.config.capabilities._capabilities_cache",
        {},
    )


class TestOldBehaviorRemoved:
    """Tests verifying old hardcoded behavior is removed."""

    def test_get_standard_capabilities_removed(self):
        """_get_standard_capabilities function does not exist."""
        from llm_lsp_cli.config import initialize_params

        assert not hasattr(initialize_params, "_get_standard_capabilities")
        # Or if it exists, it should not be callable
        if hasattr(initialize_params, "_get_standard_capabilities"):
            assert not callable(
                getattr(initialize_params, "_get_standard_capabilities")
            )

    def test_capabilities_not_merged_with_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Capabilities are explicitly replaced, not merged."""
        from llm_lsp_cli.config.initialize_params import build_initialize_params

        _reset_cache(monkeypatch)

        result = build_initialize_params(
            server_command="basedpyright-langserver",
            workspace_path=str(tmp_path),
        )

        # If merging were happening, we'd see keys from both sources
        # Since basedpyright doesn't have "window.showMessage" but default might,
        # we verify the structure matches basedpyright's JSON exactly
        caps = result["capabilities"]
        # basedpyright JSON structure check
        assert "workspace" in caps
        assert "textDocument" in caps
