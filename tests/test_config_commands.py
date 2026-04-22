"""Tests for config subcommands: config list and config init."""

import json
import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from llm_lsp_cli.cli import app

runner = CliRunner()


@contextmanager
def in_directory(path: Path):
    """Context manager to temporarily change working directory."""
    original_cwd = os.getcwd()
    try:
        os.chdir(str(path))
        yield
    finally:
        os.chdir(original_cwd)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    import shutil
    import tempfile

    dirpath = tempfile.mkdtemp()
    yield Path(dirpath)
    shutil.rmtree(dirpath, ignore_errors=True)


@pytest.fixture
def python_project_dir(temp_dir: Path) -> Path:
    """Create temp directory with pyproject.toml."""
    (temp_dir / "pyproject.toml").touch()
    return temp_dir


@pytest.fixture
def rust_project_dir(temp_dir: Path) -> Path:
    """Create temp directory with Cargo.toml."""
    (temp_dir / "Cargo.toml").touch()
    return temp_dir


@pytest.fixture
def typescript_project_dir(temp_dir: Path) -> Path:
    """Create temp directory with tsconfig.json."""
    (temp_dir / "tsconfig.json").write_text("{}")
    return temp_dir


@pytest.fixture
def go_project_dir(temp_dir: Path) -> Path:
    """Create temp directory with go.mod."""
    (temp_dir / "go.mod").touch()
    return temp_dir


@pytest.fixture
def java_project_dir(temp_dir: Path) -> Path:
    """Create temp directory with pom.xml."""
    (temp_dir / "pom.xml").touch()
    return temp_dir


@pytest.fixture
def polyglot_project_dir(temp_dir: Path) -> Path:
    """Create temp directory with multiple project files."""
    (temp_dir / "pyproject.toml").touch()
    (temp_dir / "tsconfig.json").write_text("{}")
    return temp_dir


@pytest.fixture
def empty_project_dir(temp_dir: Path) -> Path:
    """Create empty temp directory (no project markers)."""
    return temp_dir


@pytest.fixture
def clean_config_state() -> Generator[None, None, None]:
    """Temporarily remove existing config for test isolation."""
    from llm_lsp_cli.config import ConfigManager
    from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

    # Reset singleton to ensure fresh initialization
    XdgPaths.reset_for_testing()

    config_path = ConfigManager.get_config_dir() / "config.yaml"
    original_content = None
    existed = config_path.exists()

    if existed:
        original_content = config_path.read_text()
        config_path.unlink()

    yield

    # Reset singleton again for test isolation
    XdgPaths.reset_for_testing()

    # Restore original state
    if existed and original_content:
        config_path.write_text(original_content)
    elif not existed and config_path.exists():
        config_path.unlink()


@pytest.fixture
def custom_config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set custom XDG_CONFIG_HOME for test isolation."""
    config_dir = tmp_path / ".config"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
    return config_dir / "llm-lsp-cli" / "config.yaml"


# =============================================================================
# Test: Capability Files Exist
# =============================================================================


def test_capability_files_exist() -> None:
    """Verify all expected capability files exist."""
    capabilities_dir = (
        Path(__file__).parent.parent / "src" / "llm_lsp_cli" / "config" / "capabilities"
    )

    expected_files = [
        "pyright-langserver.json",
        "basedpyright-langserver.json",
        "typescript-language-server.json",
        "rust-analyzer.json",
        "gopls.json",
        "jdtls.json",
    ]

    for filename in expected_files:
        assert (capabilities_dir / filename).exists(), f"Missing: {filename}"


# =============================================================================
# Test Class: config list - Auto-Detection
# =============================================================================


class TestConfigListAutoDetection:
    """Tests for config list auto-detection behavior."""

    def test_cl_001_default_auto_detection_python_project(
        self, python_project_dir: Path, clean_config_state: None
    ) -> None:
        """CL-001: Default auto-detection in Python project."""
        with in_directory(python_project_dir):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        # Should contain only pyright capabilities (single server)
        assert len(output) == 1
        assert "pyright" in output or "basedpyright" in output

    def test_cl_002_auto_detection_rust_project(
        self, rust_project_dir: Path, clean_config_state: None
    ) -> None:
        """CL-002: Auto-detection in Rust project."""
        with in_directory(rust_project_dir):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert "rust-analyzer" in output

    def test_cl_003_auto_detection_typescript_project(
        self, typescript_project_dir: Path, clean_config_state: None
    ) -> None:
        """CL-003: Auto-detection in TypeScript project."""
        with in_directory(typescript_project_dir):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert "typescript" in output

    def test_cl_004_auto_detection_go_project(
        self, go_project_dir: Path, clean_config_state: None
    ) -> None:
        """CL-004: Auto-detection in Go project."""
        with in_directory(go_project_dir):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert "gopls" in output

    def test_cl_005_auto_detection_java_project(
        self, java_project_dir: Path, clean_config_state: None
    ) -> None:
        """CL-005: Auto-detection in Java project."""
        with in_directory(java_project_dir):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert "jdtls" in output

    def test_cl_006_fallback_when_no_project_files_found(
        self, empty_project_dir: Path, clean_config_state: None
    ) -> None:
        """CL-006: Fallback when no project files found."""
        with in_directory(empty_project_dir):
            result = runner.invoke(app, ["config", "list"])

        # Should show all servers with warning
        assert result.exit_code == 0
        output = json.loads(result.output)
        # Should contain multiple servers
        assert len(output) > 1

    def test_cl_007_polyglot_project_priority(
        self, polyglot_project_dir: Path, clean_config_state: None
    ) -> None:
        """CL-007: Polyglot project priority."""
        with in_directory(polyglot_project_dir):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        # TypeScript has higher priority than Python (8 > 6)
        assert len(output) == 1
        assert "typescript" in output


# =============================================================================
# Test Class: config list - Explicit Override
# =============================================================================


class TestConfigListOverride:
    """Tests for --lsp-server flag override."""

    def test_cl_008_lsp_server_flag_override(
        self, python_project_dir: Path, clean_config_state: None
    ) -> None:
        """CL-008: --lsp-server flag override."""
        with in_directory(python_project_dir):
            result = runner.invoke(app, ["config", "list", "--lsp-server", "rust-analyzer"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        # Should show rust-analyzer, not pyright
        assert len(output) == 1
        assert "rust-analyzer" in output

    def test_cl_009_short_flag_ls(self, python_project_dir: Path, clean_config_state: None) -> None:
        """CL-009: -ls short flag."""
        with in_directory(python_project_dir):
            result = runner.invoke(app, ["config", "list", "-ls", "gopls"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert "gopls" in output

    def test_cl_010_override_with_non_existent_server(
        self, python_project_dir: Path, clean_config_state: None
    ) -> None:
        """CL-010: Override with non-existent server."""
        with in_directory(python_project_dir):
            result = runner.invoke(app, ["config", "list", "--lsp-server", "nonexistent-server"])

        # Should fall back to all servers with warning
        assert result.exit_code == 0
        # Warning goes to stderr, JSON to stdout - but CliRunner combines them
        # Find the JSON part (starts with '{')
        output_str = result.output
        json_start = output_str.find("{")
        output = json.loads(output_str[json_start:])
        # Should contain multiple servers (fallback)
        assert len(output) > 1
        # Verify warning message is present
        assert "Capabilities not found for 'nonexistent-server'" in result.output


# =============================================================================
# Test Class: config list - Format Options
# =============================================================================


class TestConfigListFormats:
    """Tests for output format options."""

    def test_cl_011_json_format_output(
        self, python_project_dir: Path, clean_config_state: None
    ) -> None:
        """CL-011: JSON format output."""
        with in_directory(python_project_dir):
            result = runner.invoke(app, ["config", "list", "--format", "json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert isinstance(output, dict)
        # Should be single server
        assert len(output) == 1

    def test_cl_012_yaml_format_output(
        self, python_project_dir: Path, clean_config_state: None
    ) -> None:
        """CL-012: YAML format output."""
        with in_directory(python_project_dir):
            result = runner.invoke(app, ["config", "list", "--format", "yaml"])

        assert result.exit_code == 0
        output = yaml.safe_load(result.output)
        assert isinstance(output, dict)

    def test_cl_013_text_format_output_single_server(
        self, python_project_dir: Path, clean_config_state: None
    ) -> None:
        """CL-013: Text format output (single server)."""
        with in_directory(python_project_dir):
            result = runner.invoke(app, ["config", "list", "--format", "text"])

        assert result.exit_code == 0
        output = result.output
        # Should have "Capabilities for <server>:" header (single server format)
        assert "Capabilities for" in output
        # Should NOT have server prefix like "pyright:" when single server
        lines = output.strip().split("\n")
        server_lines = [line for line in lines if line.endswith(":")]
        # Single server should NOT have "pyright:" prefix style
        assert not any(line in ["pyright:", "basedpyright:"] for line in server_lines)

    def test_cl_014_text_format_output_all_servers(
        self, empty_project_dir: Path, clean_config_state: None
    ) -> None:
        """CL-014: Text format output (all servers)."""
        with in_directory(empty_project_dir):
            result = runner.invoke(app, ["config", "list", "--format", "text"])

        assert result.exit_code == 0
        output = result.output
        # Each server should be prefixed with name (e.g., "pyright:")
        assert "pyright:" in output

    def test_cl_015_invalid_format_option(
        self, python_project_dir: Path, clean_config_state: None
    ) -> None:
        """CL-015: Invalid format option."""
        with in_directory(python_project_dir):
            result = runner.invoke(app, ["config", "list", "--format", "xml"])

        assert result.exit_code == 1
        assert "Unsupported format: xml" in result.output

    def test_cl_016_short_format_flag(
        self, python_project_dir: Path, clean_config_state: None
    ) -> None:
        """CL-016: Short format flag -f."""
        with in_directory(python_project_dir):
            result = runner.invoke(app, ["config", "list", "-f", "yaml"])

        assert result.exit_code == 0
        output = yaml.safe_load(result.output)
        assert isinstance(output, dict)


# =============================================================================
# Test Class: config init - Creation
# =============================================================================


class TestConfigInit:
    """Tests for config init command."""

    def test_ci_001_fresh_config_creation(self, clean_config_state: None) -> None:
        """CI-001: Fresh config creation."""
        from llm_lsp_cli.config import ConfigManager

        result = runner.invoke(app, ["config", "init"])

        assert result.exit_code == 0
        assert "Created default configuration at:" in result.output

        config_path = ConfigManager.get_config_dir() / "config.yaml"
        assert config_path.exists()

    def test_ci_002_config_file_content_validation(self, clean_config_state: None) -> None:
        """CI-002: Config file content validation."""
        from llm_lsp_cli.config import ConfigManager

        result = runner.invoke(app, ["config", "init"])

        assert result.exit_code == 0
        config_path = ConfigManager.get_config_dir() / "config.yaml"
        content = config_path.read_text()
        config_data = yaml.safe_load(content)

        # Should have languages section
        assert "languages" in config_data
        # Should have python language config
        assert "python" in config_data["languages"]
        assert "command" in config_data["languages"]["python"]

    def test_ci_003_parent_directory_creation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CI-003: Parent directory creation."""
        # Set up custom XDG_CONFIG_HOME
        custom_config = tmp_path / ".config" / "llm-lsp-cli"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))

        # Ensure it doesn't exist
        if custom_config.exists():
            import shutil

            shutil.rmtree(custom_config)

        from llm_lsp_cli.config import ConfigManager

        result = runner.invoke(app, ["config", "init"])

        assert result.exit_code == 0
        config_path = ConfigManager.get_config_dir() / "config.yaml"
        assert config_path.exists()

    def test_ci_004_xdg_compliance(
        self, custom_config_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CI-004: XDG compliance."""
        from llm_lsp_cli.config import ConfigManager

        result = runner.invoke(app, ["config", "init"])

        assert result.exit_code == 0
        # Use ConfigManager to get the actual path (handles macOS /private/var symlink)
        config_path = ConfigManager.get_config_dir() / "config.yaml"
        assert config_path.exists()
        # Verify it's under the custom XDG_CONFIG_HOME
        assert str(config_path).endswith("llm-lsp-cli/config.yaml")


# =============================================================================
# Test Class: config init - Idempotency
# =============================================================================


class TestConfigInitIdempotency:
    """Tests for idempotent behavior."""

    def test_ci_005_second_run_already_exists(self, clean_config_state: None) -> None:
        """CI-005: Second run (already exists)."""
        from llm_lsp_cli.config import ConfigManager

        # First run - create config
        result1 = runner.invoke(app, ["config", "init"])
        assert result1.exit_code == 0

        config_path = ConfigManager.get_config_dir() / "config.yaml"
        original_content = config_path.read_text()

        # Second run - should say already exists
        result2 = runner.invoke(app, ["config", "init"])
        assert result2.exit_code == 0
        assert "Configuration already exists at:" in result2.output

        # File should NOT be modified
        assert config_path.read_text() == original_content

    def test_ci_006_idempotency_multiple_runs(self, clean_config_state: None) -> None:
        """CI-006: Idempotency - multiple runs."""
        from llm_lsp_cli.config import ConfigManager

        # First run
        result1 = runner.invoke(app, ["config", "init"])
        assert result1.exit_code == 0

        config_path = ConfigManager.get_config_dir() / "config.yaml"
        original_content = config_path.read_text()

        # Run three times
        for _ in range(3):
            result = runner.invoke(app, ["config", "init"])
            assert result.exit_code == 0
            assert "Configuration already exists at:" in result.output

        # File should still be unchanged
        assert config_path.read_text() == original_content


# =============================================================================
# Test Class: Integration Tests
# =============================================================================


class TestConfigIntegration:
    """Integration tests for config commands."""

    def test_int_001_config_init_then_config_list(
        self, python_project_dir: Path, clean_config_state: None
    ) -> None:
        """INT-001: config init then config list."""
        # Step 1: Create config
        result_init = runner.invoke(app, ["config", "init"])
        assert result_init.exit_code == 0

        # Step 2: List config
        with in_directory(python_project_dir):
            result_list = runner.invoke(app, ["config", "list"])

        assert result_list.exit_code == 0
        output = json.loads(result_list.output)
        # Should show pyright capabilities (single server)
        assert len(output) == 1
        assert "pyright" in output or "basedpyright" in output

    def test_int_002_config_list_with_custom_server_command(
        self, python_project_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """INT-002: config list with custom server command."""
        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        try:
            # Set up custom config with custom server path
            custom_config_dir = tmp_path / ".config" / "llm-lsp-cli"
            custom_config_dir.mkdir(parents=True)
            custom_config_file = custom_config_dir / "config.yaml"

            custom_config = {
                "languages": {
                    "python": {
                        "command": "/usr/local/bin/custom-pyright",
                        "args": [],
                        "testFilters": [],
                    }
                }
            }
            custom_config_file.write_text(yaml.dump(custom_config))

            # Clear XdgPaths singleton cache before setting new XDG_CONFIG_HOME
            XdgPaths.reset_for_testing()
            monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))

            with in_directory(python_project_dir):
                result = runner.invoke(app, ["config", "list"])

            assert result.exit_code == 0
            output = json.loads(result.output)
            # Should match pyright capabilities (custom-pyright contains "pyright")
            assert "pyright" in output
        finally:
            # Reset singleton for test isolation
            XdgPaths.reset_for_testing()

    def test_int_003_language_detection_config_resolution(
        self, python_project_dir: Path, clean_config_state: None
    ) -> None:
        """INT-003: Language detection + config resolution."""
        from llm_lsp_cli.config import ConfigManager
        from llm_lsp_cli.utils.language_detector import detect_language_with_fallback

        # Create config first
        result_init = runner.invoke(app, ["config", "init"])
        assert result_init.exit_code == 0

        # Test detection chain
        workspace_path = str(python_project_dir)
        detected_lang = detect_language_with_fallback(workspace_path=workspace_path)
        assert detected_lang == "python"

        # Get language config
        lang_config = ConfigManager.get_language_config("python")
        assert lang_config is not None

        # Resolve server name
        server_name = ConfigManager.get_lsp_server_name("python")
        assert "pyright" in server_name.lower()
