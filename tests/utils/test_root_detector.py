"""Tests for root_detector module - root_markers feature."""

from pathlib import Path

import pytest

# These imports will fail until we create the module - that's expected in RED phase


class TestFindRootByMarkers:
    """Tests for find_root_by_markers function."""

    def test_find_marker_in_same_directory(self, tmp_path: Path) -> None:
        """C1: Find marker in same directory as start_path."""
        from llm_lsp_cli.utils.root_detector import find_root_by_markers

        # Create marker IN the src directory, not parent
        src = tmp_path / "src"
        src.mkdir()
        (src / "pyproject.toml").touch()

        result = find_root_by_markers(src, ["pyproject.toml"])
        assert result == src

    def test_find_marker_in_parent_directory(self, python_project: Path) -> None:
        """C2: Find marker in parent directory."""
        from llm_lsp_cli.utils.root_detector import find_root_by_markers

        deep = python_project / "src" / "myapp"
        result = find_root_by_markers(deep, ["pyproject.toml"])
        assert result == python_project

    def test_glob_pattern_matching(self, tmp_path: Path) -> None:
        """C3: Glob patterns like *.sln match correctly."""
        from llm_lsp_cli.utils.root_detector import find_root_by_markers

        (tmp_path / "MyApp.sln").touch()
        result = find_root_by_markers(tmp_path, ["*.sln"])
        assert result == tmp_path

    def test_glob_pattern_in_parent(self, tmp_path: Path) -> None:
        """C3: Glob patterns work in parent directories."""
        from llm_lsp_cli.utils.root_detector import find_root_by_markers

        (tmp_path / "MyApp.csproj").touch()
        child = tmp_path / "src" / "app"
        child.mkdir(parents=True)
        result = find_root_by_markers(child, ["*.csproj"])
        assert result == tmp_path

    def test_empty_markers_returns_none(self, tmp_path: Path) -> None:
        """S5: Empty markers list returns None."""
        from llm_lsp_cli.utils.root_detector import find_root_by_markers

        result = find_root_by_markers(tmp_path, [])
        assert result is None

    def test_no_markers_found_returns_none(self, tmp_path: Path) -> None:
        """No markers exist in path hierarchy returns None."""
        from llm_lsp_cli.utils.root_detector import find_root_by_markers

        result = find_root_by_markers(tmp_path, ["pyproject.toml", "Cargo.toml"])
        assert result is None

    def test_first_marker_wins(self, tmp_path: Path) -> None:
        """First matching marker in list takes priority."""
        from llm_lsp_cli.utils.root_detector import find_root_by_markers

        (tmp_path / "Cargo.toml").touch()
        (tmp_path / "pyproject.toml").touch()
        result = find_root_by_markers(tmp_path, ["pyproject.toml", "Cargo.toml"])
        assert result == tmp_path
        # pyproject.toml should match first, but both are in same dir

    def test_marker_priority_order(self, tmp_path: Path) -> None:
        """Markers earlier in list are checked first."""
        from llm_lsp_cli.utils.root_detector import find_root_by_markers

        child = tmp_path / "src"
        child.mkdir()
        (tmp_path / "Cargo.toml").touch()
        result = find_root_by_markers(child, ["Cargo.toml", "pyproject.toml"])
        assert result == tmp_path

    def test_start_path_is_file_uses_parent(self, tmp_path: Path) -> None:
        """If start_path is a file, use its parent directory."""
        from llm_lsp_cli.utils.root_detector import find_root_by_markers

        (tmp_path / "pyproject.toml").touch()
        file_path = tmp_path / "src" / "main.py"
        file_path.parent.mkdir(parents=True)
        file_path.touch()
        result = find_root_by_markers(file_path, ["pyproject.toml"])
        assert result == tmp_path

    def test_marker_at_filesystem_root(self, tmp_path: Path) -> None:
        """Search stops at filesystem root without error."""
        from llm_lsp_cli.utils.root_detector import find_root_by_markers

        # Create a deeply nested structure without any marker
        deep = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep.mkdir(parents=True)
        result = find_root_by_markers(deep, ["nonexistent.marker"])
        assert result is None


class TestDetectWorkspaceAndLanguage:
    """Tests for detect_workspace_and_language function."""

    def test_auto_detect_from_file_extension(
        self, python_project: Path, config_python_only: dict[str, dict]
    ) -> None:
        """C4: Auto-detect language from file extension, then find root."""
        from llm_lsp_cli.utils.root_detector import detect_workspace_and_language

        file_path = python_project / "src" / "main.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

        root, language = detect_workspace_and_language(
            file_path=str(file_path),
            explicit_workspace=None,
            explicit_language=None,
            language_configs=config_python_only,
            extension_map={".py": "python"},
        )
        assert root == python_project
        assert language == "python"

    def test_search_all_languages_from_cwd(
        self, rust_project: Path, config_multi_language: dict[str, dict]
    ) -> None:
        """C5: No file path, search all languages from CWD."""
        from llm_lsp_cli.utils.root_detector import detect_workspace_and_language

        root, language = detect_workspace_and_language(
            file_path=None,
            explicit_workspace=None,
            explicit_language=None,
            language_configs=config_multi_language,
            extension_map={".rs": "rust", ".py": "python"},
            cwd=str(rust_project),
        )
        assert root == rust_project
        assert language == "rust"

    def test_explicit_workspace_override(
        self, python_project: Path, tmp_path: Path, config_multi_language: dict[str, dict]
    ) -> None:
        """C6: Explicit workspace and language override auto-detect."""
        from llm_lsp_cli.utils.root_detector import detect_workspace_and_language

        other_dir = tmp_path / "other"
        other_dir.mkdir()

        file_path = python_project / "src" / "main.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

        root, language = detect_workspace_and_language(
            file_path=str(file_path),
            explicit_workspace=str(other_dir),
            explicit_language="rust",
            language_configs=config_multi_language,
            extension_map={".py": "python"},
        )
        assert root == other_dir
        assert language == "rust"

    def test_unsupported_file_type_returns_none_language(
        self, tmp_path: Path, config_python_only: dict[str, dict]
    ) -> None:
        """C7: Unsupported file extension returns (cwd, None)."""
        from llm_lsp_cli.utils.root_detector import detect_workspace_and_language

        file_path = tmp_path / "notes.txt"
        file_path.touch()

        root, language = detect_workspace_and_language(
            file_path=str(file_path),
            explicit_workspace=None,
            explicit_language=None,
            language_configs=config_python_only,
            extension_map={".py": "python"},
        )
        assert root == tmp_path
        assert language is None

    def test_explicit_language_finds_root(
        self, python_project: Path, config_multi_language: dict[str, dict]
    ) -> None:
        """Explicit language without workspace finds root via markers."""
        from llm_lsp_cli.utils.root_detector import detect_workspace_and_language

        deep = python_project / "src" / "myapp"
        deep.mkdir(parents=True, exist_ok=True)

        root, language = detect_workspace_and_language(
            file_path=None,
            explicit_workspace=None,
            explicit_language="python",
            language_configs=config_multi_language,
            extension_map={},
            cwd=str(deep),
        )
        assert root == python_project
        assert language == "python"

    def test_fallback_to_cwd_when_nothing_found(
        self, tmp_path: Path, config_python_only: dict[str, dict]
    ) -> None:
        """Fallback to CWD when no markers found and no file extension match."""
        from llm_lsp_cli.utils.root_detector import detect_workspace_and_language

        root, language = detect_workspace_and_language(
            file_path=None,
            explicit_workspace=None,
            explicit_language=None,
            language_configs=config_python_only,
            extension_map={},
            cwd=str(tmp_path),
        )
        assert root == tmp_path
        assert language is None


class TestFormatUnsupportedMessage:
    """Tests for format_unsupported_message helper."""

    def test_format_with_language(self) -> None:
        """S4: Message format with detected language."""
        from llm_lsp_cli.utils.root_detector import format_unsupported_message

        msg = format_unsupported_message("xyz", ["python", "rust"])
        assert "Unsupported file type: 'xyz'" in msg
        assert "Configured languages: python, rust" in msg
        assert "To add support" in msg

    def test_format_with_none_language(self) -> None:
        """S4: Message format with None language."""
        from llm_lsp_cli.utils.root_detector import format_unsupported_message

        msg = format_unsupported_message(None, ["python", "rust"])
        assert "Unsupported file type" in msg
        assert "Configured languages: python, rust" in msg

    def test_format_with_empty_available(self) -> None:
        """Message format with no configured languages."""
        from llm_lsp_cli.utils.root_detector import format_unsupported_message

        msg = format_unsupported_message("xyz", [])
        assert "Unsupported file type: 'xyz'" in msg
        assert "Configured languages:" in msg


class TestRootDetectorSignatures:
    """Contract tests for function signatures (S1, S2, S3)."""

    def test_find_root_by_markers_signature(self) -> None:
        """S1: find_root_by_markers has correct signature."""
        from llm_lsp_cli.utils.root_detector import find_root_by_markers
        import inspect

        sig = inspect.signature(find_root_by_markers)
        params = list(sig.parameters.keys())
        assert "start_path" in params
        assert "markers" in params

        # Check return annotation
        return_annotation = sig.return_annotation
        # Should be Path | None
        assert return_annotation in (Path | None, "Path | None")

    def test_detect_workspace_and_language_signature(self) -> None:
        """S2: detect_workspace_and_language accepts all 5 parameters per design."""
        from llm_lsp_cli.utils.root_detector import detect_workspace_and_language
        import inspect

        sig = inspect.signature(detect_workspace_and_language)
        params = list(sig.parameters.keys())
        assert "file_path" in params
        assert "explicit_workspace" in params
        assert "explicit_language" in params
        assert "language_configs" in params
        assert "extension_map" in params
        # cwd is optional with default

    def test_format_unsupported_message_signature(self) -> None:
        """S3: format_unsupported_message has correct signature."""
        from llm_lsp_cli.utils.root_detector import format_unsupported_message
        import inspect

        sig = inspect.signature(format_unsupported_message)
        params = list(sig.parameters.keys())
        assert "language" in params
        assert "available" in params


# Fixtures for root_detector tests


@pytest.fixture
def python_project(tmp_path: Path) -> Path:
    """Create a Python project structure with pyproject.toml."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")
    src = tmp_path / "src" / "myapp"
    src.mkdir(parents=True)
    (src / "__init__.py").touch()
    return tmp_path


@pytest.fixture
def rust_project(tmp_path: Path) -> Path:
    """Create a Rust project structure with Cargo.toml."""
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'")
    src = tmp_path / "src"
    src.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def config_python_only() -> dict[str, dict]:
    """Config with only Python language."""
    return {
        "python": {"root_markers": ["pyproject.toml", "setup.py", ".git"]}
    }


@pytest.fixture
def config_multi_language() -> dict[str, dict]:
    """Config with multiple languages."""
    return {
        "python": {"root_markers": ["pyproject.toml"]},
        "rust": {"root_markers": ["Cargo.toml"]},
        "go": {"root_markers": ["go.mod"]},
    }
