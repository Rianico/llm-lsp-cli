"""Tests for DEFAULT_CONFIG changes - remove initialize_params_file field."""


class TestDefaultsNoInitializeParamsFile:
    """Test DEFAULT_CONFIG does not contain initialize_params_file."""

    def test_python_config_no_initialize_params_file(self) -> None:
        """Python language config in DEFAULT_CONFIG has no initialize_params_file."""
        from llm_lsp_cli.config.defaults import DEFAULT_CONFIG
        from llm_lsp_cli.config.schema import LanguageServerConfig

        python_config = DEFAULT_CONFIG["languages"]["python"]

        # Should not have initialize_params_file key
        assert "initialize_params_file" not in python_config

        # Should still validate as a LanguageServerConfig
        config = LanguageServerConfig(**python_config)
        assert config.command == "pyright-langserver"

    def test_all_language_configs_validate(self) -> None:
        """All language configs validate against updated schema."""
        from llm_lsp_cli.config.defaults import DEFAULT_CONFIG
        from llm_lsp_cli.config.schema import LanguageServerConfig

        for lang_id, lang_config in DEFAULT_CONFIG["languages"].items():  # pyright: ignore[reportUnusedVariable]
            # Should not raise ValidationError
            config = LanguageServerConfig(**lang_config)
            assert config.command is not None
            # None should NOT have initialize_params_file
            assert "initialize_params_file" not in lang_config or \
                   lang_config.get("initialize_params_file") is None
