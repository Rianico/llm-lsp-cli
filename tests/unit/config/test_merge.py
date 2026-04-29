"""Unit tests for deep_merge() function in config/merge.py."""

import pytest


class TestDeepMergeShallow:
    """Tests for top-level key replacement (shallow merge behavior)."""

    def test_shallow_override_replaces_value(self) -> None:
        """Top-level key in override replaces base value."""
        from llm_lsp_cli.config.merge import deep_merge

        base = {"timeout_seconds": 30, "trace_lsp": False}
        override = {"timeout_seconds": 60}

        result = deep_merge(base, override)

        assert result["timeout_seconds"] == 60
        assert result["trace_lsp"] is False

    def test_shallow_new_key_added(self) -> None:
        """New top-level key in override is added to result."""
        from llm_lsp_cli.config.merge import deep_merge

        base = {"timeout_seconds": 30}
        override = {"trace_lsp": True}

        result = deep_merge(base, override)

        assert result["timeout_seconds"] == 30
        assert result["trace_lsp"] is True


class TestDeepMergeNested:
    """Tests for recursive nested dict merge."""

    def test_nested_dict_merged_recursively(self) -> None:
        """Nested dicts are merged, not replaced."""
        from llm_lsp_cli.config.merge import deep_merge

        base = {
            "languages": {
                "python": {"command": "pyright-langserver", "args": ["--stdio"]},
            }
        }
        override = {
            "languages": {
                "python": {"args": ["--stdio", "--verbose"]},
            }
        }

        result = deep_merge(base, override)

        # command from base preserved, args from override
        assert result["languages"]["python"]["command"] == "pyright-langserver"
        assert result["languages"]["python"]["args"] == ["--stdio", "--verbose"]

    def test_nested_new_key_added(self) -> None:
        """New nested key in override is added."""
        from llm_lsp_cli.config.merge import deep_merge

        base = {
            "languages": {
                "python": {"command": "pyright-langserver"},
            }
        }
        override = {
            "languages": {
                "python": {"args": ["--stdio"]},
            }
        }

        result = deep_merge(base, override)

        assert result["languages"]["python"]["command"] == "pyright-langserver"
        assert result["languages"]["python"]["args"] == ["--stdio"]


class TestDeepMergeLists:
    """Tests for list handling (lists are replaced, not concatenated)."""

    def test_lists_replaced_not_concatenated(self) -> None:
        """Lists in override replace base lists entirely."""
        from llm_lsp_cli.config.merge import deep_merge

        base = {"languages": {"python": {"args": ["--stdio", "--verbose"]}}}
        override = {"languages": {"python": {"args": ["--quiet"]}}}

        result = deep_merge(base, override)

        assert result["languages"]["python"]["args"] == ["--quiet"]

    def test_list_in_override_replaces_base_list(self) -> None:
        """When both base and override have lists, override wins."""
        from llm_lsp_cli.config.merge import deep_merge

        base = {"items": [1, 2, 3]}
        override = {"items": [4, 5]}

        result = deep_merge(base, override)

        assert result["items"] == [4, 5]


class TestDeepMergeEmptyInputs:
    """Tests for empty dict edge cases."""

    def test_empty_override_returns_base_copy(self) -> None:
        """Empty override dict returns copy of base."""
        from llm_lsp_cli.config.merge import deep_merge

        base = {"timeout_seconds": 30}
        override: dict[str, object] = {}

        result = deep_merge(base, override)

        assert result == {"timeout_seconds": 30}

    def test_empty_base_returns_override_copy(self) -> None:
        """Empty base dict returns copy of override."""
        from llm_lsp_cli.config.merge import deep_merge

        base: dict[str, object] = {}
        override = {"timeout_seconds": 60}

        result = deep_merge(base, override)

        assert result == {"timeout_seconds": 60}

    def test_both_empty_returns_empty(self) -> None:
        """Both empty dicts returns empty dict."""
        from llm_lsp_cli.config.merge import deep_merge

        base: dict[str, object] = {}
        override: dict[str, object] = {}

        result = deep_merge(base, override)

        assert result == {}


class TestDeepMergeImmutability:
    """Tests that deep_merge does not mutate input dicts."""

    def test_base_not_mutated(self) -> None:
        """Input base dict is not modified."""
        from llm_lsp_cli.config.merge import deep_merge

        base = {"languages": {"python": {"command": "pyright"}}}
        override = {"languages": {"python": {"args": ["--stdio"]}}}

        base_copy = {"languages": {"python": {"command": "pyright"}}}
        deep_merge(base, override)

        assert base == base_copy

    def test_override_not_mutated(self) -> None:
        """Input override dict is not modified."""
        from llm_lsp_cli.config.merge import deep_merge

        base = {"languages": {"python": {"command": "pyright"}}}
        override = {"languages": {"python": {"args": ["--stdio"]}}}

        override_copy = {"languages": {"python": {"args": ["--stdio"]}}}
        deep_merge(base, override)

        assert override == override_copy


class TestDeepMergeTypeMismatch:
    """Tests for type mismatch handling."""

    def test_dict_overridden_by_non_dict(self) -> None:
        """When override has non-dict where base has dict, override wins."""
        from llm_lsp_cli.config.merge import deep_merge

        base = {"config": {"nested": "value"}}
        override = {"config": "simple_string"}

        result = deep_merge(base, override)

        assert result["config"] == "simple_string"

    def test_non_dict_overridden_by_dict(self) -> None:
        """When override has dict where base has non-dict, override wins."""
        from llm_lsp_cli.config.merge import deep_merge

        base = {"config": "simple_string"}
        override = {"config": {"nested": "value"}}

        result = deep_merge(base, override)

        assert result["config"] == {"nested": "value"}
