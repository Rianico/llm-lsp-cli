from llm_lsp_cli.config.manager import ConfigManager


def test_get_language_config() -> None:
    config = ConfigManager.get_language_config("python")
    assert config is not None
    assert config.command == "pyright-langserver"

def test_get_language_config_not_found() -> None:
    config = ConfigManager.get_language_config("non_existent_language")
    assert config is None
