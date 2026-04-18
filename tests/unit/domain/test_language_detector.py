"""Tests for language detector - Python and TypeScript project markers."""

from pathlib import Path


class TestLanguageDetectorPythonMarkers:
    """Test Python project detection."""

    def test_detects_pyproject_toml(self, tmp_path: Path) -> None:
        """pyproject.toml → python."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        (tmp_path / "pyproject.toml").touch()

        language = detect_language_from_workspace(str(tmp_path))

        assert language == "python"

    def test_detects_setup_py(self, tmp_path: Path) -> None:
        """setup.py → python."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        (tmp_path / "setup.py").touch()

        language = detect_language_from_workspace(str(tmp_path))

        assert language == "python"

    def test_detects_requirements_txt(self, tmp_path: Path) -> None:
        """requirements.txt → python."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        (tmp_path / "requirements.txt").touch()

        language = detect_language_from_workspace(str(tmp_path))

        assert language == "python"

    def test_multiple_markers_respects_priority(self, tmp_path: Path) -> None:
        """Multiple markers respects priority."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        # Create both pyproject.toml and setup.py
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "setup.py").touch()

        language = detect_language_from_workspace(str(tmp_path))

        # Should detect as python (both are Python markers)
        assert language == "python"

    def test_python_loses_to_higher_priority(self, tmp_path: Path) -> None:
        """Python loses to higher priority languages like TypeScript."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        # Create both Python and TypeScript markers
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "tsconfig.json").touch()

        language = detect_language_from_workspace(str(tmp_path))

        # TypeScript has higher priority than Python
        assert language == "typescript"


class TestLanguageDetectorTypeScriptMarkers:
    """Test TypeScript/JavaScript project detection."""

    def test_detects_tsconfig_json(self, tmp_path: Path) -> None:
        """tsconfig.json → typescript."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        (tmp_path / "tsconfig.json").touch()

        language = detect_language_from_workspace(str(tmp_path))

        assert language == "typescript"

    def test_detects_package_json_without_tsconfig(self, tmp_path: Path) -> None:
        """package.json without tsconfig.json → javascript."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        (tmp_path / "package.json").touch()

        language = detect_language_from_workspace(str(tmp_path))

        assert language == "javascript"

    def test_detects_package_json_with_tsconfig(self, tmp_path: Path) -> None:
        """package.json with tsconfig.json → typescript (priority)."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        (tmp_path / "package.json").touch()
        (tmp_path / "tsconfig.json").touch()

        language = detect_language_from_workspace(str(tmp_path))

        # tsconfig.json has higher priority
        assert language == "typescript"


class TestLanguageDetectorFallback:
    """Test fallback to python for unknown projects."""

    def test_empty_directory_fallback(self, tmp_path: Path) -> None:
        """Empty directory → python."""
        from llm_lsp_cli.utils.language_detector import detect_language_with_fallback

        language = detect_language_with_fallback(str(tmp_path))

        assert language == "python"

    def test_no_markers_fallback(self, tmp_path: Path) -> None:
        """Directory with no markers → python."""
        from llm_lsp_cli.utils.language_detector import detect_language_with_fallback

        # Create some random files that aren't markers
        (tmp_path / "README.md").touch()
        (tmp_path / ".gitignore").touch()

        language = detect_language_with_fallback(str(tmp_path))

        assert language == "python"
