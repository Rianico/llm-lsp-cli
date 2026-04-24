"""Unit tests for get_capabilities_for_server_path function."""

import json
from pathlib import Path

import pytest


def _reset_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset the capabilities cache to empty dict."""
    monkeypatch.setattr(
        "llm_lsp_cli.config.capabilities._capabilities_cache",
        {},
    )


class TestGetCapabilitiesForServerPath:
    """Tests for get_capabilities_for_server_path function."""

    def test_get_capabilities_known_server_basename(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Known server returns specific JSON capabilities."""
        from llm_lsp_cli.config.capabilities import (
            get_capabilities_for_server_path,
        )

        _reset_cache(monkeypatch)

        result = get_capabilities_for_server_path("basedpyright-langserver")

        assert "capabilities" in result
        assert "initializationOptions" in result
        # Should match basedpyright capabilities structure
        assert result["capabilities"]["workspace"]["configuration"] is True

    def test_get_capabilities_known_server_full_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Known server from full path returns specific JSON."""
        from llm_lsp_cli.config.capabilities import get_capabilities_for_server_path

        _reset_cache(monkeypatch)

        result = get_capabilities_for_server_path(
            "/usr/local/bin/basedpyright-langserver"
        )

        assert "capabilities" in result
        assert "initializationOptions" in result

    def test_get_capabilities_unknown_server_fallback(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ):
        """Unknown server falls back to default.json with warning log."""
        from llm_lsp_cli.config.capabilities import get_capabilities_for_server_path

        _reset_cache(monkeypatch)

        with caplog.at_level("WARNING"):
            result = get_capabilities_for_server_path("unknown-server-xyz")

        assert "capabilities" in result
        # Should log warning about fallback
        assert "default" in caplog.text.lower() or "fallback" in caplog.text.lower()

    def test_get_capabilities_caching(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker
    ):
        """Second call returns cached value without disk read."""
        from llm_lsp_cli.config.capabilities import (
            get_capabilities_for_server_path,
        )

        _reset_cache(monkeypatch)

        # First call - should read from disk
        result1 = get_capabilities_for_server_path("basedpyright-langserver")

        # Mock file operations to verify cache is used
        mock_load = mocker.patch(
            "llm_lsp_cli.config.capabilities._load_server_capability"
        )

        # Second call - should use cache
        result2 = get_capabilities_for_server_path("basedpyright-langserver")

        mock_load.assert_not_called()
        assert result1 == result2

    def test_get_capabilities_different_servers_return_different_capabilities(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Different server paths return different capabilities (cache keyed by server)."""
        from llm_lsp_cli.config.capabilities import get_capabilities_for_server_path

        _reset_cache(monkeypatch)

        result_pyright = get_capabilities_for_server_path("pyright-langserver")
        result_rust = get_capabilities_for_server_path("rust-analyzer")

        # Both should have capabilities
        assert "capabilities" in result_pyright
        assert "capabilities" in result_rust

        # But they should be different (different servers have different configs)
        # pyright has workspace.configuration, rust-analyzer has different structure
        assert result_pyright != result_rust

    def test_get_capabilities_missing_default_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Missing default.json raises FileNotFoundError."""
        from llm_lsp_cli.config.capabilities import get_capabilities_for_server_path

        _reset_cache(monkeypatch)
        # Patch get_capabilities_dir to return empty temp dir
        monkeypatch.setattr(
            "llm_lsp_cli.config.capabilities.get_capabilities_dir",
            lambda: tmp_path,
        )

        with pytest.raises(FileNotFoundError):
            get_capabilities_for_server_path("unknown-server")

    def test_get_capabilities_invalid_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Invalid JSON in default.json raises JSONDecodeError."""
        import json

        from llm_lsp_cli.config.capabilities import get_capabilities_for_server_path

        # Create temp dir with invalid JSON
        caps_dir = tmp_path / "capabilities"
        caps_dir.mkdir()
        (caps_dir / "default.json").write_text("{invalid json}")

        _reset_cache(monkeypatch)
        monkeypatch.setattr(
            "llm_lsp_cli.config.capabilities.get_capabilities_dir",
            lambda: caps_dir,
        )

        with pytest.raises(json.JSONDecodeError):
            get_capabilities_for_server_path("unknown-server")

    def test_get_capabilities_uses_match_server_filter(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Server matching uses existing _match_server_filter function."""
        from llm_lsp_cli.config.capabilities import get_capabilities_for_server_path

        _reset_cache(monkeypatch)

        # Test prefix match (e.g., "basedpyright" matches "basedpyright-langserver")
        result = get_capabilities_for_server_path("basedpyright")
        assert "capabilities" in result
