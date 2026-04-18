"""Tests for LanguageServerConfig schema changes - remove initialize_params_file field."""

import pytest
from pydantic import ValidationError


class TestSchemaNoInitializeParamsFile:
    """Test LanguageServerConfig no longer has initialize_params_file field."""

    def test_schema_without_initialize_params_file_succeeds(self) -> None:
        """Creating LanguageServerConfig without initialize_params_file succeeds."""
        from llm_lsp_cli.config.schema import LanguageServerConfig

        config = LanguageServerConfig(
            command="pyright-langserver",
            args=["--stdio"],
            env={"PATH": "/usr/bin"},
        )

        assert config.command == "pyright-langserver"
        assert config.args == ["--stdio"]
        assert config.env == {"PATH": "/usr/bin"}

    def test_schema_initialize_params_file_ignored(self) -> None:
        """Passing initialize_params_file is ignored (extra='allow') but not stored as typed field."""
        from llm_lsp_cli.config.schema import LanguageServerConfig

        config = LanguageServerConfig(
            command="pyright-langserver",
            args=["--stdio"],
            initialize_params_file="test.json",
        )

        assert config.command == "pyright-langserver"
        assert config.args == ["--stdio"]
        # Should NOT have initialize_params_file as a typed attribute
        assert not hasattr(config, "initialize_params_file") or \
               "initialize_params_file" not in LanguageServerConfig.model_fields

    def test_schema_validation_with_minimal_fields(self) -> None:
        """Schema validation passes with only command, args, env."""
        from llm_lsp_cli.config.schema import LanguageServerConfig

        config = LanguageServerConfig(
            command="rust-analyzer",
            args=[],
            env={},
        )

        assert config.command == "rust-analyzer"
        assert config.args == []
        assert config.env == {}

    def test_schema_command_required(self) -> None:
        """Command field is still required."""
        from llm_lsp_cli.config.schema import LanguageServerConfig

        with pytest.raises(ValidationError):
            LanguageServerConfig()
