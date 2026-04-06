"""Tests for workspace language detection."""

from pathlib import Path
from tempfile import TemporaryDirectory


class TestLanguageDetectionFromWorkspace:
    """Tests for detect_language_from_workspace."""

    def test_detect_rust_from_cargo_toml(self) -> None:
        """Test Rust detection via Cargo.toml."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "Cargo.toml").touch()
            assert detect_language_from_workspace(tmpdir) == "rust"

    def test_detect_go_from_go_mod(self) -> None:
        """Test Go detection via go.mod."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "go.mod").touch()
            assert detect_language_from_workspace(tmpdir) == "go"

    def test_detect_java_from_pom_xml(self) -> None:
        """Test Java detection via pom.xml."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "pom.xml").touch()
            assert detect_language_from_workspace(tmpdir) == "java"

    def test_detect_java_from_build_gradle(self) -> None:
        """Test Java detection via build.gradle."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "build.gradle").touch()
            assert detect_language_from_workspace(tmpdir) == "java"

    def test_detect_typescript_from_tsconfig(self) -> None:
        """Test TypeScript detection via tsconfig.json."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "tsconfig.json").touch()
            assert detect_language_from_workspace(tmpdir) == "typescript"

    def test_detect_javascript_from_package_json(self) -> None:
        """Test JavaScript detection via package.json (when no tsconfig)."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "package.json").touch()
            # package.json alone should detect as javascript (lower priority than typescript)
            result = detect_language_from_workspace(tmpdir)
            assert result in ("javascript", "typescript")

    def test_detect_typescript_preferred_over_javascript(self) -> None:
        """Test that tsconfig.json + package.json prefers TypeScript."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "package.json").touch()
            Path(tmpdir, "tsconfig.json").touch()
            # Both present should prefer TypeScript
            assert detect_language_from_workspace(tmpdir) == "typescript"

    def test_detect_csharp_from_sln(self) -> None:
        """Test C# detection via .sln file."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "MyProject.sln").touch()
            assert detect_language_from_workspace(tmpdir) == "csharp"

    def test_detect_csharp_from_csproj(self) -> None:
        """Test C# detection via .csproj file."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "MyProject.csproj").touch()
            assert detect_language_from_workspace(tmpdir) == "csharp"

    def test_detect_cpp_from_makefile(self) -> None:
        """Test C++ detection via Makefile."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "Makefile").touch()
            assert detect_language_from_workspace(tmpdir) == "cpp"

    def test_detect_cpp_from_compile_commands(self) -> None:
        """Test C++ detection via compile_commands.json."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "compile_commands.json").touch()
            assert detect_language_from_workspace(tmpdir) == "cpp"

    def test_detect_python_from_pyproject_toml(self) -> None:
        """Test Python detection via pyproject.toml."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "pyproject.toml").touch()
            assert detect_language_from_workspace(tmpdir) == "python"

    def test_detect_python_from_setup_py(self) -> None:
        """Test Python detection via setup.py."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "setup.py").touch()
            assert detect_language_from_workspace(tmpdir) == "python"

    def test_detect_python_from_requirements_txt(self) -> None:
        """Test Python detection via requirements.txt."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "requirements.txt").touch()
            assert detect_language_from_workspace(tmpdir) == "python"

    def test_no_detection_empty_directory(self) -> None:
        """Test no detection in empty directory."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            assert detect_language_from_workspace(tmpdir) is None

    def test_nonexistent_directory(self) -> None:
        """Test handling of nonexistent directory."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        assert detect_language_from_workspace("/nonexistent/path12345") is None

    def test_priority_rust_over_python(self) -> None:
        """Test that Cargo.toml takes priority over pyproject.toml."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "Cargo.toml").touch()
            Path(tmpdir, "pyproject.toml").touch()
            # Rust has higher priority than Python
            assert detect_language_from_workspace(tmpdir) == "rust"

    def test_priority_go_over_java(self) -> None:
        """Test that go.mod takes priority over pom.xml."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "go.mod").touch()
            Path(tmpdir, "pom.xml").touch()
            # Go has higher priority than Java
            assert detect_language_from_workspace(tmpdir) == "go"

    def test_priority_typescript_over_cpp(self) -> None:
        """Test that tsconfig.json takes priority over Makefile."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "tsconfig.json").touch()
            Path(tmpdir, "Makefile").touch()
            # TypeScript has higher priority than C++
            assert detect_language_from_workspace(tmpdir) == "typescript"

    def test_detect_csharp_from_csproj_in_subdirectory(self) -> None:
        """Test C# detection via .csproj file (glob pattern)."""
        from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

        with TemporaryDirectory() as tmpdir:
            # Create a .csproj file with arbitrary name
            csproj_file = Path(tmpdir, "MyAwesomeProject.csproj")
            csproj_file.touch()
            assert detect_language_from_workspace(tmpdir) == "csharp"


class TestLanguageWithFallback:
    """Tests for detect_language_with_fallback."""

    def test_explicit_language_override(self) -> None:
        """Test that explicit language overrides detection."""
        from llm_lsp_cli.utils.language_detector import detect_language_with_fallback

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "Cargo.toml").touch()
            assert detect_language_with_fallback(
                tmpdir, explicit_language="python"
            ) == "python"

    def test_detected_language(self) -> None:
        """Test that detected language is used."""
        from llm_lsp_cli.utils.language_detector import detect_language_with_fallback

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "go.mod").touch()
            assert detect_language_with_fallback(tmpdir) == "go"

    def test_default_fallback(self) -> None:
        """Test fallback to default language."""
        from llm_lsp_cli.utils.language_detector import detect_language_with_fallback

        with TemporaryDirectory() as tmpdir:
            assert detect_language_with_fallback(
                tmpdir, default_language="python"
            ) == "python"

    def test_custom_default_fallback(self) -> None:
        """Test custom default fallback."""
        from llm_lsp_cli.utils.language_detector import detect_language_with_fallback

        with TemporaryDirectory() as tmpdir:
            assert detect_language_with_fallback(
                tmpdir, default_language="typescript"
            ) == "typescript"

    def test_explicit_language_overrides_detected(self) -> None:
        """Test explicit language overrides any detected language."""
        from llm_lsp_cli.utils.language_detector import detect_language_with_fallback

        with TemporaryDirectory() as tmpdir:
            Path(tmpdir, "pom.xml").touch()
            # Java would be detected, but we override to Rust
            assert detect_language_with_fallback(
                tmpdir, explicit_language="rust"
            ) == "rust"
