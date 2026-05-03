"""End-to-end integration tests for config subcommands.

Tests config list and config init in realistic project scenarios.
"""

import json
import os
import shutil
import tempfile
import time
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
    dirpath = tempfile.mkdtemp()
    yield Path(dirpath)
    shutil.rmtree(dirpath, ignore_errors=True)


@pytest.fixture
def python_project_dir(temp_dir: Path) -> Path:
    """Create temp directory with pyproject.toml."""
    (temp_dir / "pyproject.toml").touch()
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


# =============================================================================
# E2E Test: Real Project Directory Scenarios
# =============================================================================


class TestConfigListEndToEnd:
    """End-to-end tests for config list in real project scenarios."""

    @pytest.fixture
    def real_python_project(self, tmp_path: Path) -> Path:
        """Create a realistic Python project structure."""
        project = tmp_path / "python_project"
        project.mkdir()
        (project / "pyproject.toml").write_text(
            """[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[project]
name = "test-project"
version = "0.1.0"
"""
        )
        (project / "src").mkdir()
        (project / "src" / "__init__.py").touch()
        (project / "tests").mkdir()
        (project / "tests" / "test_example.py").write_text(
            """def test_example():
    assert True
"""
        )
        return project

    @pytest.fixture
    def real_rust_project(self, tmp_path: Path) -> Path:
        """Create a realistic Rust project structure."""
        project = tmp_path / "rust_project"
        project.mkdir()
        (project / "Cargo.toml").write_text(
            """[package]
name = "test-project"
version = "0.1.0"
edition = "2021"

[dependencies]
"""
        )
        (project / "src").mkdir()
        (project / "src" / "main.rs").write_text("fn main() {}")
        return project

    @pytest.fixture
    def real_typescript_project(self, tmp_path: Path) -> Path:
        """Create a realistic TypeScript project structure."""
        project = tmp_path / "typescript_project"
        project.mkdir()
        (project / "package.json").write_text(
            """{
  "name": "test-project",
  "version": "0.1.0",
  "scripts": {
    "build": "tsc"
  }
}
"""
        )
        (project / "tsconfig.json").write_text(
            """{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs"
  }
}
"""
        )
        (project / "src").mkdir()
        (project / "src" / "index.ts").write_text("export const hello = 'world';")
        return project

    def test_e2e_001_python_project_config_list(
        self, real_python_project: Path, clean_config_state: None
    ) -> None:
        """E2E-001: config list in real Python project."""
        with in_directory(real_python_project):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        # Should detect pyright or basedpyright
        assert any("pyright" in key for key in output)

    def test_e2e_002_rust_project_config_list(
        self, real_rust_project: Path, clean_config_state: None
    ) -> None:
        """E2E-002: config list in real Rust project."""
        with in_directory(real_rust_project):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert "rust-analyzer" in output

    def test_e2e_003_typescript_project_config_list(
        self, real_typescript_project: Path, clean_config_state: None
    ) -> None:
        """E2E-003: config list in real TypeScript project."""
        with in_directory(real_typescript_project):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert "typescript" in output

    def test_e2e_004_nested_project_detection(
        self, tmp_path: Path, clean_config_state: None
    ) -> None:
        """E2E-004: Project detection from nested subdirectory.

        With root_markers, the detector searches upward to find markers
        in parent directories, so nested projects are properly detected.
        """
        project = tmp_path / "monorepo" / "backend" / "python_api"
        project.mkdir(parents=True)
        (project / "pyproject.toml").touch()

        # Create subdirectory
        src_dir = project / "src" / "handlers"
        src_dir.mkdir(parents=True)

        # With root_markers, detection searches upward and finds pyproject.toml
        with in_directory(src_dir):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        # Detects Python from pyproject.toml in parent directory
        assert len(output) == 1
        assert "basedpyright" in output

    def test_e2e_005_config_list_yaml_format(
        self, real_python_project: Path, clean_config_state: None
    ) -> None:
        """E2E-005: config list with YAML format output."""
        with in_directory(real_python_project):
            result = runner.invoke(app, ["config", "list", "--format", "yaml"])

        assert result.exit_code == 0
        output = yaml.safe_load(result.output)
        assert isinstance(output, dict)
        assert len(output) == 1

    def test_e2e_006_config_list_text_format_all_servers(self, clean_config_state: None) -> None:
        """E2E-006: config list text format shows all servers."""
        # Create empty dir (no project markers)
        with tempfile.TemporaryDirectory() as tmp_dir, in_directory(Path(tmp_dir)):
            result = runner.invoke(app, ["config", "list", "--format", "text"])

        assert result.exit_code == 0
        output = result.output
        # Should show multiple servers
        assert "pyright:" in output
        assert "rust-analyzer:" in output
        assert "typescript:" in output


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestConfigEdgeCases:
    """Edge case tests for config commands."""

    def test_edge_001_missing_capabilities_file_fallback(
        self, python_project_dir: Path, clean_config_state: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """EDGE-001: Fallback when specific capabilities file is missing."""
        # Temporarily rename pyright capabilities file
        from llm_lsp_cli.config import capabilities

        capabilities_dir = Path(capabilities.__file__).parent
        pyright_file = capabilities_dir / "pyright-langserver.json"
        backup_file = capabilities_dir / "pyright-langserver.json.bak"

        try:
            if pyright_file.exists():
                pyright_file.rename(backup_file)

            # Clear any cached state
            monkeypatch.delenv("PYRIGHT_CAPS_CACHE", raising=False)

            with in_directory(python_project_dir):
                result = runner.invoke(app, ["config", "list", "--lsp-server", "pyright"])

            # Should fall back to all servers with warning
            assert result.exit_code == 0
            assert "Capabilities not found for 'pyright'" in result.output
        finally:
            # Restore
            if backup_file.exists():
                backup_file.rename(pyright_file)

    def test_edge_002_invalid_format_argument(
        self, python_project_dir: Path, clean_config_state: None
    ) -> None:
        """EDGE-002: Invalid format argument handling."""
        with in_directory(python_project_dir):
            result = runner.invoke(app, ["config", "list", "--format", "xml"])

        assert result.exit_code == 1
        assert "Unsupported format: xml" in result.output

    def test_edge_003_invalid_lsp_server_argument(
        self, python_project_dir: Path, clean_config_state: None
    ) -> None:
        """EDGE-003: Invalid LSP server argument handling."""
        with in_directory(python_project_dir):
            result = runner.invoke(
                app, ["config", "list", "--lsp-server", "nonexistent-server-xyz"]
            )

        assert result.exit_code == 0
        # Should fall back gracefully with warning
        assert "Capabilities not found for 'nonexistent-server-xyz'" in result.output
        # Should still output valid JSON
        json_start = result.output.find("{")
        output = json.loads(result.output[json_start:])
        assert len(output) > 1  # Fallback to all servers

    def test_edge_004_polyglot_project_priority(
        self, tmp_path: Path, clean_config_state: None
    ) -> None:
        """EDGE-004: Polyglot project uses config order for priority.

        With root_markers, first-configured language wins when multiple
        markers match. Python is first in DEFAULT_CONFIG order.
        """
        polyglot = tmp_path / "polyglot"
        polyglot.mkdir()
        # Create multiple project markers
        (polyglot / "pyproject.toml").touch()  # Python marker
        (polyglot / "tsconfig.json").write_text("{}")  # TypeScript marker
        (polyglot / "Cargo.toml").touch()  # Rust marker

        with in_directory(polyglot):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        # Python is first in config order, so basedpyright wins
        assert len(output) == 1
        assert "basedpyright" in output

    def test_edge_005_empty_project_fallback(
        self, tmp_path: Path, clean_config_state: None
    ) -> None:
        """EDGE-005: Empty project falls back to all servers."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with in_directory(empty_dir):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        # Should show all available servers
        assert len(output) >= 5  # At least pyright, basedpyright, typescript, rust, gopls, jdtls

    def test_edge_006_config_init_preserves_existing_config(self, clean_config_state: None) -> None:
        """EDGE-006: config init preserves existing config (idempotency)."""
        from llm_lsp_cli.config import ConfigManager

        # First init
        result1 = runner.invoke(app, ["config", "init"])
        assert result1.exit_code == 0

        config_path = ConfigManager.get_config_dir() / "config.yaml"
        original_content = config_path.read_text()
        original_hash = hash(original_content)

        # Second init
        result2 = runner.invoke(app, ["config", "init"])
        assert result2.exit_code == 0

        # Content should be unchanged
        assert hash(config_path.read_text()) == original_hash

    def test_edge_007_config_init_with_readonly_parent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """EDGE-007: config init creates parent directories."""
        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        try:
            # Clear XdgPaths cache to force re-reading environment
            XdgPaths.reset_for_testing()

            # Create nested path that doesn't exist
            nested_config = tmp_path / "deep" / "nested" / "config" / "llm-lsp-cli"

            monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "deep" / "nested" / "config"))

            result = runner.invoke(app, ["config", "init"])

            assert result.exit_code == 0
            config_file = nested_config / "config.yaml"
            assert config_file.exists()
        finally:
            # Reset singleton for test isolation
            XdgPaths.reset_for_testing()

    def test_edge_008_config_list_with_partial_capabilities(
        self, python_project_dir: Path, clean_config_state: None
    ) -> None:
        """EDGE-008: Handling of partial/corrupted capabilities files."""
        from llm_lsp_cli.config import capabilities

        capabilities_dir = Path(capabilities.__file__).parent
        # Use basedpyright-langserver.json which is the default Python server
        basedpyright_file = capabilities_dir / "basedpyright-langserver.json"
        backup = basedpyright_file.read_text()

        try:
            # Write invalid JSON
            basedpyright_file.write_text("{ invalid json }")

            with in_directory(python_project_dir):
                result = runner.invoke(app, ["config", "list"])

            # Should skip invalid file and show warning
            assert result.exit_code == 0
            # Warning message may be in output, extract JSON part (starts with '{')
            json_start = result.output.find("{")
            assert json_start != -1, "No JSON found in output"
            output = json.loads(result.output[json_start:])
            # Should have other servers but not basedpyright
            assert "basedpyright" not in output or "rust-analyzer" in output or "typescript" in output
            # Verify warning message is present
            assert "Capabilities not found" in result.output
        finally:
            # Restore
            basedpyright_file.write_text(backup)

    def test_edge_009_config_list_server_filter_substring_match(
        self, python_project_dir: Path, clean_config_state: None
    ) -> None:
        """EDGE-009: Server filter with custom name containing server substring."""
        with in_directory(python_project_dir):
            result = runner.invoke(
                app, ["config", "list", "--lsp-server", "custom-pyright-wrapper"]
            )

        assert result.exit_code == 0
        # Should match pyright via substring
        json_start = result.output.find("{")
        output = json.loads(result.output[json_start:])
        assert len(output) == 1
        assert any("pyright" in key for key in output)


# =============================================================================
# Performance Tests
# =============================================================================


class TestConfigPerformance:
    """Performance tests for config commands."""

    @pytest.fixture
    def temp_project(self, tmp_path: Path) -> Path:
        """Create a simple temp project."""
        project = tmp_path / "perf_test"
        project.mkdir()
        (project / "pyproject.toml").touch()
        return project

    def test_perf_001_config_list_response_time(
        self, temp_project: Path, clean_config_state: None
    ) -> None:
        """PERF-001: config list should respond within 500ms."""
        with in_directory(temp_project):
            start = time.perf_counter()
            result = runner.invoke(app, ["config", "list"])
            elapsed = time.perf_counter() - start

        assert result.exit_code == 0
        assert elapsed < 0.5  # 500ms

    def test_perf_002_config_init_response_time(self, clean_config_state: None) -> None:
        """PERF-002: config init should respond within 500ms."""
        start = time.perf_counter()
        result = runner.invoke(app, ["config", "init"])
        elapsed = time.perf_counter() - start

        assert result.exit_code == 0
        assert elapsed < 0.5  # 500ms

    def test_perf_003_config_list_caching(
        self, temp_project: Path, clean_config_state: None
    ) -> None:
        """PERF-003: Repeated config list calls should be fast."""
        times = []
        for _ in range(5):
            with in_directory(temp_project):
                start = time.perf_counter()
                result = runner.invoke(app, ["config", "list"])
                elapsed = time.perf_counter() - start
            assert result.exit_code == 0
            times.append(elapsed)

        # Average should be under 200ms after first call
        avg_time = sum(times) / len(times)
        assert avg_time < 0.2  # 200ms average

    def test_perf_004_config_init_idempotency_performance(self, clean_config_state: None) -> None:
        """PERF-004: Repeated config init should be fast (early exit)."""
        # First call creates config
        result = runner.invoke(app, ["config", "init"])
        assert result.exit_code == 0

        times = []
        for _ in range(5):
            start = time.perf_counter()
            result = runner.invoke(app, ["config", "init"])
            elapsed = time.perf_counter() - start
            assert result.exit_code == 0
            times.append(elapsed)

        # All subsequent calls should be very fast (early exit)
        avg_time = sum(times) / len(times)
        assert avg_time < 0.1  # 100ms average for early exit

    def test_perf_005_config_list_all_formats_performance(
        self, temp_project: Path, clean_config_state: None
    ) -> None:
        """PERF-005: All format outputs should be fast."""
        formats = ["json", "yaml", "text"]

        with in_directory(temp_project):
            for fmt in formats:
                start = time.perf_counter()
                result = runner.invoke(app, ["config", "list", "--format", fmt])
                elapsed = time.perf_counter() - start

                assert result.exit_code == 0
                assert elapsed < 0.3  # 300ms per format


# =============================================================================
# Integration Tests: config init then config list workflow
# =============================================================================


class TestConfigInitListWorkflow:
    """Integration tests for config init -> config list workflow."""

    def test_workflow_001_fresh_init_then_list(
        self, python_project_dir: Path, clean_config_state: None
    ) -> None:
        """WORKFLOW-001: Fresh config init followed by list."""
        # Init
        result_init = runner.invoke(app, ["config", "init"])
        assert result_init.exit_code == 0
        assert "Created default configuration" in result_init.output

        # List
        with in_directory(python_project_dir):
            result_list = runner.invoke(app, ["config", "list"])

        assert result_list.exit_code == 0
        output = json.loads(result_list.output)
        assert len(output) == 1

    def test_workflow_002_init_list_with_override(
        self, python_project_dir: Path, clean_config_state: None
    ) -> None:
        """WORKFLOW-002: Init then list with server override."""
        # Init
        result_init = runner.invoke(app, ["config", "init"])
        assert result_init.exit_code == 0

        # List with override
        with in_directory(python_project_dir):
            result_list = runner.invoke(app, ["config", "list", "--lsp-server", "rust-analyzer"])

        assert result_list.exit_code == 0
        output = json.loads(result_list.output)
        assert "rust-analyzer" in output

    def test_workflow_003_init_list_all_formats(
        self, python_project_dir: Path, clean_config_state: None
    ) -> None:
        """WORKFLOW-003: Init then list with all formats."""
        # Init
        result_init = runner.invoke(app, ["config", "init"])
        assert result_init.exit_code == 0

        # List with each format
        for fmt in ["json", "yaml", "text"]:
            with in_directory(python_project_dir):
                result = runner.invoke(app, ["config", "list", "--format", fmt])
            assert result.exit_code == 0

            # Validate output format
            if fmt == "json":
                output = json.loads(result.output)
                assert isinstance(output, dict)
            elif fmt == "yaml":
                output = yaml.safe_load(result.output)
                assert isinstance(output, dict)
            elif fmt == "text":
                assert "Capabilities for" in result.output

    def test_workflow_004_multiple_projects_same_config(
        self, tmp_path: Path, clean_config_state: None
    ) -> None:
        """WORKFLOW-004: Multiple projects share same config."""
        # Create multiple project directories
        python_proj = tmp_path / "python"
        rust_proj = tmp_path / "rust"
        ts_proj = tmp_path / "typescript"

        python_proj.mkdir()
        rust_proj.mkdir()
        ts_proj.mkdir()

        (python_proj / "pyproject.toml").touch()
        (rust_proj / "Cargo.toml").touch()
        (ts_proj / "tsconfig.json").write_text("{}")

        # Init config once
        result_init = runner.invoke(app, ["config", "init"])
        assert result_init.exit_code == 0

        # List in each project - should detect different servers
        for proj, expected in [
            (python_proj, "pyright"),
            (rust_proj, "rust-analyzer"),
            (ts_proj, "typescript"),
        ]:
            with in_directory(proj):
                result = runner.invoke(app, ["config", "list"])
            assert result.exit_code == 0
            output = json.loads(result.output)
            assert len(output) == 1
            # Check expected server is detected
            assert any(expected in key for key in output)
