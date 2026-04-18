"""Tests for ConfigLoader.save() writes YAML format."""

from pathlib import Path


class TestConfigLoaderSaveYaml:
    """Test ConfigLoader.save() writes YAML format."""

    def test_save_dict_to_yaml_path(self, tmp_path: Path) -> None:
        """Saving dict to .yaml path produces valid YAML."""
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        data = {
            "languages": {
                "python": {
                    "command": "pyright-langserver",
                    "args": ["--stdio"],
                }
            },
            "trace_lsp": False,
            "timeout_seconds": 30,
        }

        config_file = tmp_path / "config.yaml"
        ConfigLoader.save(config_file, data)

        # Verify file was written
        assert config_file.exists()

        # Verify it's valid YAML by reading it back
        loaded = ConfigLoader.load(config_file, defaults={})
        assert loaded["languages"]["python"]["command"] == "pyright-langserver"
        assert loaded["trace_lsp"] is False

    def test_save_yaml_human_readable(self, tmp_path: Path) -> None:
        """Saved YAML is human-readable (indentation, no quotes on keys)."""
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        data = {
            "languages": {
                "python": {
                    "command": "pyright-langserver",
                }
            },
        }

        config_file = tmp_path / "config.yaml"
        ConfigLoader.save(config_file, data)

        content = config_file.read_text()

        # Check for YAML characteristics
        assert "languages:" in content
        assert "python:" in content
        assert "command:" in content
        # Should not have JSON-style quotes on keys
        assert '"languages"' not in content

    def test_save_yaml_file_permissions(self, tmp_path: Path) -> None:
        """File permissions allow read/write."""
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        data = {
            "languages": {
                "python": {
                    "command": "pyright-langserver",
                }
            },
        }

        config_file = tmp_path / "config.yaml"
        ConfigLoader.save(config_file, data)

        # Verify file is readable and writable
        assert config_file.stat().st_mode & 0o400  # Readable
        assert config_file.stat().st_mode & 0o200  # Writable
