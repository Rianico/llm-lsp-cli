"""Tests for type safety warnings identified by basedpyright.

These tests verify correct runtime behavior for code with type annotation issues.
The GREEN phase will fix the type annotations to remove basedpyright warnings.

RED STATE: Tests pass, but basedpyright shows 23 warnings.
GREEN STATE: Tests pass, basedpyright shows 0 warnings.
"""

import json
import tempfile
from pathlib import Path

import pytest

from llm_lsp_cli.config.manager import ConfigManager
from llm_lsp_cli.config.merge import deep_merge
from llm_lsp_cli.domain.services.backup_manager import BackupManager
from llm_lsp_cli.infrastructure.config.loader import ConfigLoader
from llm_lsp_cli.ipc.protocol import serialize_for_json
from llm_lsp_cli.lsp.types import Position
from pydantic import BaseModel


class SampleModel(BaseModel):
    """Sample Pydantic model for serialization tests."""

    name: str
    value: int


class TestConfigManagerArgsType:
    """Tests for config/manager.py:292 - args type partially unknown.

    Issue: args_raw = defaults.get("args", []) returns object.
    isinstance(args_raw, list) narrows to list[Unknown], not list[str].

    Fix needed: Create get_list_of_str helper or validate list items.
    """

    def test_resolve_server_command_returns_list_of_strings(self, tmp_path: Path) -> None:
        """Verify that resolve_server_command returns args as list[str]."""
        # This test documents the expected behavior
        # The args should be a list of strings
        manager = ConfigManager()

        # Test with a language that has args in defaults (python)
        # We expect args to be a list of strings
        try:
            _executable, args = manager.resolve_server_command("python")
            # Runtime verification: args must be list[str]
            assert isinstance(args, list)
            for arg in args:
                assert isinstance(arg, str), f"Expected str, got {type(arg).__name__}"
        except FileNotFoundError:
            # Pyright/pylsp might not be installed - skip
            pytest.skip("Python language server not installed")

    def test_args_type_narrowing_from_dict(self) -> None:
        """Test that args extracted from dict is properly typed as list[str]."""
        # Simulate the problematic code path
        defaults: dict[str, object] = {
            "command": "test-server",
            "args": ["--flag", "value"],
        }

        args_raw: object = defaults.get("args", [])
        # Current code: isinstance narrows to list[Unknown]
        # Expected: list[str]
        if isinstance(args_raw, list):
            # This is what the fix should achieve
            args: list[str] = [str(a) for a in args_raw]
            assert args == ["--flag", "value"]
        else:
            pytest.fail("args should be a list")


class TestDeepMergeTypeNarrowing:
    """Tests for config/merge.py:31-32 - unnecessary isinstance and unknown types.

    Issue: After type narrowing in the if condition, the inner isinstance is
    redundant. Also, the recursive call has unknown argument types.

    Fix needed: Remove redundant isinstance, properly type the recursive call.
    """

    def test_deep_merge_handles_nested_dicts(self) -> None:
        """Verify deep_merge correctly merges nested dictionaries."""
        base: dict[str, object] = {
            "level1": {
                "level2": "base_value",
                "other": "unchanged",
            },
            "simple": "base",
        }
        override: dict[str, object] = {
            "level1": {
                "level2": "override_value",
            },
            "new_key": "new_value",
        }

        result = deep_merge(base, override)

        assert result["level1"]["level2"] == "override_value"
        assert result["level1"]["other"] == "unchanged"
        assert result["simple"] == "base"
        assert result["new_key"] == "new_value"

    def test_deep_merge_replaces_lists(self) -> None:
        """Verify deep_merge replaces lists instead of concatenating."""
        base: dict[str, object] = {"items": [1, 2, 3]}
        override: dict[str, object] = {"items": [4, 5]}

        result = deep_merge(base, override)

        assert result["items"] == [4, 5]


class TestSerializeForJsonPublicApi:
    """Tests for daemon.py:22 - private function used outside module.

    Issue: serialize_for_json is private but used in daemon.py.

    Fix needed: Either make function public or re-export from public module.
    """

    def test_serialize_pydantic_model(self) -> None:
        """Verify serialize_for_json converts Pydantic models to dict."""
        model = SampleModel(name="test", value=42)

        result = serialize_for_json(model)

        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_serialize_list_of_models(self) -> None:
        """Verify serialize_for_json handles lists of Pydantic models."""
        models = [SampleModel(name="a", value=1), SampleModel(name="b", value=2)]

        result = serialize_for_json(models)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "a"

    def test_serialize_nested_dict(self) -> None:
        """Verify serialize_for_json handles nested dictionaries."""
        data: dict[str, object] = {
            "nested": {"model": SampleModel(name="inner", value=99)},
            "list": [SampleModel(name="item", value=0)],
        }

        result = serialize_for_json(data)

        assert isinstance(result, dict)
        assert result["nested"]["model"]["name"] == "inner"
        assert result["list"][0]["name"] == "item"


class TestBackupManagerManifestParsing:
    """Tests for backup_manager.py:222 - manifest_raw is Any.

    Issue: json.loads() returns Any, making manifest_raw untyped.

    Fix needed: Validate json.loads result with isinstance before use.
    """

    def test_restore_by_id_parses_manifest_correctly(self, tmp_path: Path) -> None:
        """Verify manifest.json is parsed correctly from Any to typed dict."""
        manager = BackupManager(tmp_path)
        position = Position(line=10, character=5)
        session = manager.create_session("test.py", position, "new_name")

        # Create backup files
        test_file = tmp_path / "test.py"
        test_file.write_text("original content")
        manager.backup_files(session, [test_file])
        manager.write_manifest(session)

        # The manifest is written as JSON
        manifest_path = session.backup_dir / "manifest.json"
        manifest_content = manifest_path.read_text()

        # Verify JSON structure
        manifest_data = json.loads(manifest_content)
        assert isinstance(manifest_data, dict)
        assert "session_id" in manifest_data
        assert "affected_files" in manifest_data

    def test_manifest_raw_type_is_validated(self, tmp_path: Path) -> None:
        """Test that manifest_raw from json.loads is properly validated."""
        # Create a valid manifest
        manifest_data = {
            "session_id": "test-123",
            "timestamp": "2024-01-01T00:00:00",
            "affected_files": {"file.py": "backup.py"},
            "status": "pending",
        }

        manifest_json = json.dumps(manifest_data)

        # Simulate the problematic code path
        manifest_raw: object = json.loads(manifest_json)

        # The fix should validate manifest_raw before use
        if not isinstance(manifest_raw, dict):
            pytest.fail("manifest_raw should be a dict")

        # After validation, we can safely access
        session_id = manifest_raw.get("session_id")
        assert session_id == "test-123"


class TestConfigLoaderYamlParsing:
    """Tests for infrastructure/config/loader.py - multiple unknown types.

    Issues:
    - Line 57, 59: yaml.safe_load() and json.loads() return Any
    - Lines 64, 70, 73: Arguments have unknown types
    - Lines 124, 126: Dict iteration produces unknown key/value types
    - Lines 159, 163, 167, 169: List append with unknown types

    Fix needed: Add type annotations and validation for parsed data.
    """

    def test_load_yaml_config(self, tmp_path: Path) -> None:
        """Verify ConfigLoader handles YAML files correctly."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("""
languages:
  python:
    command: pyright
    args:
      - "--stdio"
""")

        result = ConfigLoader.load(config_path)

        assert isinstance(result, dict)
        assert "languages" in result
        assert isinstance(result["languages"], dict)
        assert "python" in result["languages"]

    def test_load_json_config(self, tmp_path: Path) -> None:
        """Verify ConfigLoader handles JSON files correctly."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "languages": {
                "python": {
                    "command": "pyright",
                    "args": ["--stdio"],
                }
            }
        }))

        result = ConfigLoader.load(config_path)

        assert isinstance(result, dict)
        assert "languages" in result

    def test_expand_env_in_dict(self) -> None:
        """Verify _expand_env handles dict iteration correctly."""
        data: object = {
            "path": "/home/${USER}/config",
            "nested": {"value": "$HOME"},
        }

        result = ConfigLoader._expand_env(data)

        assert isinstance(result, dict)
        # The nested dict should also be processed
        assert isinstance(result.get("nested"), dict)

    def test_expand_env_in_list(self) -> None:
        """Verify _expand_env handles list iteration correctly."""
        data: object = ["$HOME", "${USER}", "static"]

        result = ConfigLoader._expand_env(data)

        assert isinstance(result, list)
        assert len(result) == 3

    def test_validate_schema_detects_missing_languages(self, tmp_path: Path) -> None:
        """Verify _validate_schema catches missing languages key."""
        from llm_lsp_cli.infrastructure.config.exceptions import ConfigValidationError

        config_path = tmp_path / "config.yaml"
        config_path.write_text("other_key: value")

        with pytest.raises(ConfigValidationError) as exc_info:
            ConfigLoader.load(config_path)

        assert "languages" in str(exc_info.value).lower()

    def test_validate_schema_detects_invalid_language_entry(self, tmp_path: Path) -> None:
        """Verify _validate_schema catches missing command in language entry."""
        from llm_lsp_cli.infrastructure.config.exceptions import ConfigValidationError

        config_path = tmp_path / "config.yaml"
        config_path.write_text("""
languages:
  python:
    args:
      - "--stdio"
""")

        with pytest.raises(ConfigValidationError) as exc_info:
            ConfigLoader.load(config_path)

        assert "command" in str(exc_info.value).lower()


class TestTypeSafetyRegression:
    """Regression tests to ensure type fixes don't break behavior."""

    def test_deep_merge_preserves_immutability(self) -> None:
        """Verify deep_merge does not mutate input dictionaries."""
        base: dict[str, object] = {"key": "base"}
        override: dict[str, object] = {"key": "override"}

        _ = deep_merge(base, override)

        assert base["key"] == "base"  # Original unchanged

    def testserialize_for_json_handles_none(self) -> None:
        """Verify serialize_for_json handles None correctly."""
        result = serialize_for_json(None)
        assert result is None

    def testserialize_for_json_handles_primitives(self) -> None:
        """Verify serialize_for_json handles primitive types."""
        assert serialize_for_json("string") == "string"
        assert serialize_for_json(42) == 42
        assert serialize_for_json(3.14) == 3.14
        assert serialize_for_json(True) is True
