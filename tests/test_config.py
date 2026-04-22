"""Tests for configuration loading."""

from llm_lsp_cli.config.manager import ConfigManager


def test_get_language_config() -> None:
    """Test that python language config is loaded correctly."""
    config = ConfigManager.get_language_config("python")
    assert config is not None
    # Config command should contain 'pyright' (either pyright-langserver or basedpyright-langserver)
    assert "pyright" in config.command.lower()


def test_get_language_config_not_found() -> None:
    """Test that non-existent language returns None."""
    config = ConfigManager.get_language_config("non_existent_language")
    assert config is None
