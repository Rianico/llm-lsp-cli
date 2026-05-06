"""Unit tests for resolve_language() in commands/shared.py.

Tests verify workspace-level language detection from root markers.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest import MonkeyPatch


class TestDetectLanguageFromMarkers:
    """Tests U1-U7: Detect language from workspace root markers."""

    def test_detect_rust_from_cargo_toml(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """U1: Detect Rust from Cargo.toml."""
        workspace = tmp_path / "rust_project"
        workspace.mkdir()
        (workspace / "Cargo.toml").touch()

        from llm_lsp_cli.commands.shared import resolve_language

        workspace_path, language, available = resolve_language(str(workspace), None)

        assert language == "rust"
        assert Path(workspace_path).resolve() == workspace.resolve()
        assert isinstance(available, list)

    def test_detect_python_from_pyproject(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """U2: Detect Python from pyproject.toml."""
        workspace = tmp_path / "python_project"
        workspace.mkdir()
        (workspace / "pyproject.toml").touch()

        from llm_lsp_cli.commands.shared import resolve_language

        workspace_path, language, available = resolve_language(str(workspace), None)

        assert language == "python"
        assert Path(workspace_path).resolve() == workspace.resolve()
        assert isinstance(available, list)

    def test_detect_typescript_from_tsconfig(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """U3: Detect TypeScript from tsconfig.json."""
        workspace = tmp_path / "ts_project"
        workspace.mkdir()
        (workspace / "tsconfig.json").touch()

        from llm_lsp_cli.commands.shared import resolve_language

        workspace_path, language, available = resolve_language(str(workspace), None)

        assert language == "typescript"
        assert Path(workspace_path).resolve() == workspace.resolve()
        assert isinstance(available, list)

    def test_detect_go_from_go_mod(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """U4: Detect Go from go.mod."""
        workspace = tmp_path / "go_project"
        workspace.mkdir()
        (workspace / "go.mod").touch()

        from llm_lsp_cli.commands.shared import resolve_language

        workspace_path, language, available = resolve_language(str(workspace), None)

        assert language == "go"
        assert Path(workspace_path).resolve() == workspace.resolve()
        assert isinstance(available, list)

    def test_detect_java_from_pom_xml(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """U5: Detect Java from pom.xml."""
        workspace = tmp_path / "java_project"
        workspace.mkdir()
        (workspace / "pom.xml").touch()

        from llm_lsp_cli.commands.shared import resolve_language

        workspace_path, language, available = resolve_language(str(workspace), None)

        assert language == "java"
        assert Path(workspace_path).resolve() == workspace.resolve()
        assert isinstance(available, list)

    def test_detect_cpp_from_cmake(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """U6: Detect C++ from CMakeLists.txt."""
        workspace = tmp_path / "cpp_project"
        workspace.mkdir()
        (workspace / "CMakeLists.txt").touch()

        from llm_lsp_cli.commands.shared import resolve_language

        workspace_path, language, available = resolve_language(str(workspace), None)

        assert language == "cpp"
        assert Path(workspace_path).resolve() == workspace.resolve()
        assert isinstance(available, list)

    def test_detect_csharp_from_sln(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """U7: Detect C# from .sln file."""
        workspace = tmp_path / "csharp_project"
        workspace.mkdir()
        (workspace / "MyProject.sln").touch()

        from llm_lsp_cli.commands.shared import resolve_language

        workspace_path, language, available = resolve_language(str(workspace), None)

        assert language == "csharp"
        assert Path(workspace_path).resolve() == workspace.resolve()
        assert isinstance(available, list)


class TestExplicitLanguageOverride:
    """Tests U8-U9: Explicit language flag overrides detection."""

    def test_explicit_language_overrides_detection(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """U8: Explicit --language overrides detection."""
        workspace = tmp_path / "rust_project"
        workspace.mkdir()
        (workspace / "Cargo.toml").touch()

        from llm_lsp_cli.commands.shared import resolve_language

        workspace_path, language, available = resolve_language(str(workspace), "python")

        assert language == "python"  # Explicit override, not rust
        assert Path(workspace_path).resolve() == workspace.resolve()
        assert isinstance(available, list)

    def test_explicit_workspace_with_marker(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """U9: Explicit workspace path with marker detects language."""
        workspace = tmp_path / "explicit_workspace"
        workspace.mkdir()
        (workspace / "go.mod").touch()

        from llm_lsp_cli.commands.shared import resolve_language

        workspace_path, language, available = resolve_language(str(workspace), None)

        assert language == "go"
        assert Path(workspace_path).resolve() == workspace.resolve()
        assert isinstance(available, list)


class TestNoDetectionWithoutMarkers:
    """Test U10: No detection without markers returns None for language."""

    def test_no_detection_without_markers(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """U10: Empty dir with no explicit language returns None for language."""
        workspace = tmp_path / "empty_workspace"
        workspace.mkdir()

        from llm_lsp_cli.commands.shared import resolve_language

        workspace_path, language, available = resolve_language(str(workspace), None)

        # Should return the workspace path but None for language
        assert language is None
        assert Path(workspace_path).resolve() == workspace.resolve()
        assert isinstance(available, list)


class TestContractValidation:
    """Tests C1-C3: Contract validation for error behavior."""

    def test_error_message_includes_supported_languages(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """C1: Error message includes supported languages list."""
        workspace = tmp_path / "empty_workspace"
        workspace.mkdir()

        # The require_language_or_detect helper should raise CLIError with helpful message
        from llm_lsp_cli.commands.shared import require_language_or_detect
        from llm_lsp_cli.exceptions import CLIError

        with pytest.raises(CLIError) as exc_info:
            require_language_or_detect(str(workspace), None)

        error_msg = str(exc_info.value)
        assert "Supported languages:" in error_msg
        # Should mention at least some common languages
        assert "python" in error_msg.lower() or "rust" in error_msg.lower()

    def test_error_from_cli_exits_with_code_one(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """C2: CLIError when no language detected should cause exit code 1."""
        workspace = tmp_path / "empty_workspace"
        workspace.mkdir()

        from llm_lsp_cli.commands.shared import require_language_or_detect
        from llm_lsp_cli.exceptions import CLIError

        with pytest.raises(CLIError):
            require_language_or_detect(str(workspace), None)

    def test_resolve_language_return_type(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """C3: resolve_language() returns tuple[str, str | None, list[str]]."""
        workspace = tmp_path / "python_project"
        workspace.mkdir()
        (workspace / "pyproject.toml").touch()

        from llm_lsp_cli.commands.shared import resolve_language

        result = resolve_language(str(workspace), None)

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], str)
        # result[1] should be str | None
        assert result[1] is None or isinstance(result[1], str)
        # result[2] should be list[str]
        assert isinstance(result[2], list)
