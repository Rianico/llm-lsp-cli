"""Tests for language_detector module - regression and extension tests."""

from pathlib import Path

import pytest


class TestLanguageDetectorSignatures:
    """Tests for exported function signatures."""

    def test_detect_language_from_file_signature(self) -> None:
        """detect_language_from_file exists with correct signature."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_file
        import inspect

        sig = inspect.signature(detect_language_from_file)
        params = list(sig.parameters.keys())
        assert "file_path" in params
        assert "default" in params


class TestFileExtensionDetection:
    """Regression tests for file extension detection (R1-R9)."""

    def test_python_detection(self) -> None:
        """R1: .py files detected as python."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_file

        assert detect_language_from_file("main.py") == "python"

    def test_unknown_extension_uses_default(self) -> None:
        """R2: Unknown extension uses default."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_file

        assert detect_language_from_file("file.xyz", default="rust") == "rust"

    def test_typescript_detection(self) -> None:
        """R3: TypeScript .ts and .tsx detection."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_file

        assert detect_language_from_file("app.ts") == "typescript"
        assert detect_language_from_file("component.tsx") == "typescript"

    def test_javascript_detection(self) -> None:
        """R4: JavaScript .js and .jsx detection."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_file

        assert detect_language_from_file("app.js") == "javascript"
        assert detect_language_from_file("component.jsx") == "javascript"

    def test_rust_detection(self) -> None:
        """R5: Rust .rs detection."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_file

        assert detect_language_from_file("main.rs") == "rust"

    def test_go_detection(self) -> None:
        """R6: Go .go detection."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_file

        assert detect_language_from_file("main.go") == "go"

    def test_java_detection(self) -> None:
        """R7: Java .java detection."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_file

        assert detect_language_from_file("Main.java") == "java"

    def test_cpp_detection(self) -> None:
        """R8: C++ detection for various extensions."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_file

        assert detect_language_from_file("main.cpp") == "cpp"
        assert detect_language_from_file("main.c") == "cpp"
        assert detect_language_from_file("header.h") == "cpp"
        assert detect_language_from_file("header.hpp") == "cpp"

    def test_csharp_detection(self) -> None:
        """R9: C# .cs detection."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_file

        assert detect_language_from_file("Program.cs") == "csharp"


class TestNewFileExtensions:
    """Tests for newly added file extensions (C8, C9)."""

    def test_json_detection(self) -> None:
        """C8: JSON .json detection."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_file

        assert detect_language_from_file("config.json") == "json"

    def test_yaml_detection(self) -> None:
        """C9: YAML .yaml and .yml detection."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_file

        assert detect_language_from_file("config.yaml") == "yaml"
        assert detect_language_from_file("config.yml") == "yaml"


class TestFileExtensionMapExport:
    """Tests for FILE_EXTENSION_MAP export."""

    def test_file_extension_map_exists(self) -> None:
        """FILE_EXTENSION_MAP is exported."""
        from llm_lsp_cli.utils.language_detector import FILE_EXTENSION_MAP

        assert isinstance(FILE_EXTENSION_MAP, dict)
        assert ".py" in FILE_EXTENSION_MAP
        assert FILE_EXTENSION_MAP[".py"] == "python"


class TestNegativeConstraints:
    """Tests for forbidden behaviors (N1-N3)."""

    def test_no_language_patterns_dict(self) -> None:
        """N1: LANGUAGE_PATTERNS dict should not exist."""
        import llm_lsp_cli.utils.language_detector as module

        assert not hasattr(module, "LANGUAGE_PATTERNS"), (
            "LANGUAGE_PATTERNS should be removed - use config-driven root_markers instead"
        )

    def test_no_detect_language_from_workspace(self) -> None:
        """N2: detect_language_from_workspace function should be removed."""
        import llm_lsp_cli.utils.language_detector as module

        assert not hasattr(module, "detect_language_from_workspace"), (
            "detect_language_from_workspace should be removed - moved to root_detector"
        )

    def test_no_detect_language_with_fallback(self) -> None:
        """N3: detect_language_with_fallback function should be removed."""
        import llm_lsp_cli.utils.language_detector as module

        assert not hasattr(module, "detect_language_with_fallback"), (
            "detect_language_with_fallback should be removed - use detect_workspace_and_language"
        )


class TestLanguageServerConfigSchema:
    """Tests for LanguageServerConfig schema (S6)."""

    def test_root_markers_field_exists(self) -> None:
        """S6: LanguageServerConfig has root_markers field."""
        from llm_lsp_cli.config.schema import LanguageServerConfig

        # Create a config with root_markers
        config = LanguageServerConfig(
            command="pyright-langserver",
            root_markers=["pyproject.toml", "setup.py"],
        )
        assert hasattr(config, "root_markers")
        assert config.root_markers == ["pyproject.toml", "setup.py"]

    def test_root_markers_default_factory(self) -> None:
        """S6: root_markers uses default_factory for empty list."""
        from llm_lsp_cli.config.schema import LanguageServerConfig

        config = LanguageServerConfig(command="pyright-langserver")
        assert config.root_markers == []

    def test_root_markers_is_list_of_strings(self) -> None:
        """S6: root_markers is list[str] type."""
        from llm_lsp_cli.config.schema import LanguageServerConfig

        config = LanguageServerConfig(
            command="pyright-langserver",
            root_markers=["*.sln", "*.csproj"],
        )
        assert all(isinstance(m, str) for m in config.root_markers)
