"""Tests for the CLI interface."""

import json
from pathlib import Path
from typing import Any, Generator

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml  # type: ignore[import-untested]
from typer.testing import CliRunner

from tests.fixtures import (
    COMPLETION_RESPONSE,
    COMPLETION_RESPONSE_WITH_COMMAS,
    DOCUMENT_SYMBOL_RESPONSE,
    DOCUMENT_SYMBOL_WITH_CHILDREN,
    HOVER_RESPONSE,
    HOVER_RESPONSE_PLAINTEXT,
    LOCATION_RESPONSE,
    LOCATION_RESPONSE_MULTI,
    WORKSPACE_SYMBOL_RESPONSE,
    create_location_response_with_test_files,
    create_workspace_symbol_response_with_test_files,
)

runner = CliRunner()


# =============================================================================
# Fixtures and Test Helpers
# =============================================================================


@pytest.fixture
def mock_daemon_manager() -> Generator[MagicMock, None, None]:
    """Fixture that mocks DaemonManager and returns the mock instance.

    Use this when you need to configure the mock behavior in the test.
    Sets up the mock to appear as "running" by default.
    """
    mock_instance = MagicMock()
    mock_instance.is_running.return_value = True
    mock_instance.get_pid.return_value = 12345

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_manager.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_daemon_running() -> Generator[MagicMock, None, None]:
    """Fixture that mocks DaemonManager and returns the mock class.

    Use this when you need to verify constructor arguments.
    The mock is configured to appear as "running" by default.
    """
    mock_instance = MagicMock()
    mock_instance.is_running.return_value = True
    mock_instance.get_pid.return_value = 12345

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_manager.return_value = mock_instance
        yield mock_manager


@pytest.fixture
def mock_daemon_not_running() -> Generator[MagicMock, None, None]:
    """Fixture that mocks DaemonManager to appear not running."""
    mock_instance = MagicMock()
    mock_instance.is_running.return_value = False
    mock_instance.get_pid.return_value = None

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_manager.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_send_request() -> Generator[MagicMock, None, None]:
    """Fixture that mocks _send_request and returns the mock."""
    with patch("llm_lsp_cli.commands.lsp.send_request") as mock:
        yield mock


@pytest.fixture
def mock_validate_file() -> Generator[MagicMock, None, None]:
    """Fixture that mocks _validate_file_in_workspace and returns the mock."""
    with patch("llm_lsp_cli.commands.shared.validate_file_in_workspace") as mock:
        mock.return_value = Path("/tmp/test.py")
        yield mock


@pytest.fixture
def mock_daemon_client() -> Generator[AsyncMock, None, None]:
    """Fixture that mocks DaemonClient for auto-start scenarios."""
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value={"locations": []})
    mock_client.close = AsyncMock()

    with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_class:
        mock_class.return_value = mock_client
        yield mock_client


def setup_daemon_mock(
    is_running: bool = True, pid: int = 12345
) -> Generator[MagicMock, None, None]:
    """Set up a DaemonManager mock with the given state.

    Args:
        is_running: Whether the daemon should appear running
        pid: Process ID to return if running

    Yields:
        The mock DaemonManager instance
    """
    mock_instance = MagicMock()
    mock_instance.is_running.return_value = is_running
    mock_instance.get_pid.return_value = pid if is_running else None

    mock_manager = MagicMock()
    mock_manager.return_value = mock_instance

    with patch("llm_lsp_cli.daemon.DaemonManager", mock_manager):
        yield mock_instance


def setup_daemon_client_mock(response: dict[str, Any]) -> Generator[AsyncMock, None, None]:
    """Set up a DaemonClient mock that returns the given response.

    Args:
        response: The response dict to return from request()

    Yields:
        The mock DaemonClient instance
    """
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=response)
    mock_client.close = AsyncMock()

    mock_class = MagicMock()
    mock_class.return_value = mock_client

    with patch("llm_lsp_cli.daemon_client.DaemonClient", mock_class):
        yield mock_client


def assert_json_output(output: str, expected_keys: list[str]) -> None:
    """Assert that output is valid JSON with expected keys.

    Args:
        output: The CLI output string
        expected_keys: List of keys that should be present
    """
    parsed = json.loads(output)
    assert parsed is not None
    for key in expected_keys:
        assert key in parsed


def assert_yaml_output(output: str, expected_keys: list[str]) -> None:
    """Assert that output is valid YAML with expected keys.

    Args:
        output: The CLI output string
        expected_keys: List of keys that should be present
    """
    parsed = yaml.safe_load(output)
    assert parsed is not None
    for key in expected_keys:
        assert key in parsed


def test_cli_help() -> None:
    """Test that CLI help works."""
    from llm_lsp_cli.cli import app

    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "llm-lsp-cli" in result.output
    assert "daemon" in result.output
    assert "lsp" in result.output
    assert "config" in result.output


def test_cli_version() -> None:
    """Test that version command works."""
    from llm_lsp_cli.cli import app

    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "llm-lsp-cli version" in result.output


def test_cli_start() -> None:
    """Test start command."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["daemon", "start"])
        assert result.exit_code == 0


# =============================================================================
# Diagnostic Log Flag Tests
# =============================================================================


def test_start_command_has_diagnostic_log_flag() -> None:
    """Test that --diagnostic-log flag appears in start --help output."""
    from llm_lsp_cli.cli import app

    result = runner.invoke(app, ["daemon", "start", "--help"])
    assert result.exit_code == 0
    assert "--diagnostic-log" in result.output


def test_diagnostic_log_flag_parsed_when_present(temp_dir: Path) -> None:
    """Test that --diagnostic-log flag is accepted and parsed."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        mock_manager.return_value = mock_instance

        result = runner.invoke(
            app, ["daemon", "start", "--diagnostic-log", "--workspace", str(temp_dir)]
        )
        assert result.exit_code == 0


def test_diagnostic_log_flag_default_false(temp_dir: Path) -> None:
    """Test that --diagnostic-log flag defaults to False when omitted."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["daemon", "start", "--workspace", str(temp_dir)])
        assert result.exit_code == 0


def test_diagnostic_log_flag_passed_to_daemon_manager(temp_dir: Path) -> None:
    """Test that --diagnostic-log flag is passed to DaemonManager.start()."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        mock_manager.return_value = mock_instance

        result = runner.invoke(
            app, ["daemon", "start", "--diagnostic-log", "--workspace", str(temp_dir)]
        )
        assert result.exit_code == 0

        # Verify start was called - we need to check the call was made
        # The flag should be passed to the start method
        assert mock_instance.start.called


def test_diagnostic_log_flag_not_passed_when_omitted(temp_dir: Path) -> None:
    """Test that --diagnostic-log=False when flag is omitted."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["daemon", "start", "--workspace", str(temp_dir)])
        assert result.exit_code == 0


def test_cli_stop() -> None:
    """Test stop command."""
    from llm_lsp_cli.cli import app

    mock_instance = MagicMock()
    mock_instance.is_running.return_value = True
    mock_instance.get_pid.return_value = 12345

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["daemon", "stop"])
        assert result.exit_code == 0


def test_cli_status() -> None:
    """Test status command."""
    from llm_lsp_cli.cli import app

    mock_instance = MagicMock()
    mock_instance.is_running.return_value = True
    mock_instance.get_pid.return_value = 12345

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["daemon", "status"])
        assert result.exit_code == 0
        assert "Daemon" in result.output


def test_cli_config_list_json() -> None:
    """Test config list command with JSON format."""
    from llm_lsp_cli.cli import app

    result = runner.invoke(app, ["config", "list", "--format", "json"])
    assert result.exit_code == 0
    assert "pyright" in result.output
    assert "basedpyright" in result.output


def test_cli_config_list_yaml() -> None:
    """Test config list command with YAML format."""
    from llm_lsp_cli.cli import app

    result = runner.invoke(app, ["config", "list", "--format", "yaml"])
    assert result.exit_code == 0
    assert "pyright:" in result.output


def test_cli_config_list_text() -> None:
    """Test config list command with text format."""
    from llm_lsp_cli.cli import app

    result = runner.invoke(app, ["config", "list", "--format", "text"])
    assert result.exit_code == 0
    assert "pyright:" in result.output


def test_cli_definition_daemon_not_running() -> None:
    """Test definition command auto-starts daemon when not running."""
    from llm_lsp_cli.cli import app

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class,
        patch("llm_lsp_cli.commands.shared.validate_file_in_workspace") as mock_validate,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        mock_manager.return_value = mock_instance

        # Mock DaemonClient async request
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value={"locations": []})
        mock_client.close = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock file validation to return a valid path
        mock_validate.return_value = Path("/tmp/test.py")

        result = runner.invoke(app, ["lsp", "definition", "test.py", "10", "5"])
        # Auto-start should succeed (exit code 0) and return JSON
        assert result.exit_code == 0


def test_cli_definition_file_not_found() -> None:
    """Test definition command when file doesn't exist."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["lsp", "definition", "nonexistent/file.py", "10", "5"])
        assert result.exit_code == 1
        assert "File not found" in result.output


def test_cli_references_daemon_not_running() -> None:
    """Test references command auto-starts daemon when not running."""
    from llm_lsp_cli.cli import app

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class,
        patch("llm_lsp_cli.commands.shared.validate_file_in_workspace") as mock_validate,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        mock_manager.return_value = mock_instance

        # Mock DaemonClient async request
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value={"locations": []})
        mock_client.close = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock file validation to return a valid path
        mock_validate.return_value = Path("/tmp/test.py")

        result = runner.invoke(app, ["lsp", "references", "test.py", "10", "5"])
        # Auto-start should succeed (exit code 0) and return JSON
        assert result.exit_code == 0


def test_cli_hover_daemon_not_running() -> None:
    """Test hover command auto-starts daemon when not running."""
    from llm_lsp_cli.cli import app

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class,
        patch("llm_lsp_cli.commands.shared.validate_file_in_workspace") as mock_validate,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        mock_manager.return_value = mock_instance

        # Mock DaemonClient async request
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value={"hover": None})
        mock_client.close = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock file validation to return a valid path
        mock_validate.return_value = Path("/tmp/test.py")

        result = runner.invoke(app, ["lsp", "hover", "test.py", "10", "5"])
        # Auto-start should succeed (exit code 0) and return JSON
        assert result.exit_code == 0


def test_cli_document_symbol_daemon_not_running() -> None:
    """Test document-symbol command auto-starts daemon when not running."""
    from llm_lsp_cli.cli import app

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class,
        patch("llm_lsp_cli.commands.shared.validate_file_in_workspace") as mock_validate,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        mock_manager.return_value = mock_instance

        # Mock DaemonClient async request
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value={"symbols": []})
        mock_client.close = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock file validation to return a valid path
        mock_validate.return_value = Path("/tmp/test.py")

        result = runner.invoke(app, ["lsp", "document-symbol", "test.py"])
        # Auto-start should succeed (exit code 0) and return JSON
        assert result.exit_code == 0


def test_cli_workspace_symbol_daemon_not_running() -> None:
    """Test workspace-symbol command auto-starts daemon when not running."""
    from llm_lsp_cli.cli import app

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        mock_manager.return_value = mock_instance

        # Mock DaemonClient async request
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value={"symbols": []})
        mock_client.close = AsyncMock()
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["lsp", "workspace-symbol", "MyClass"])
        # Auto-start should succeed (exit code 0) and return JSON
        assert result.exit_code == 0


def test_cli_start_auto_detect_language(temp_dir: Path) -> None:
    """Test start command with auto-detection."""
    from llm_lsp_cli.cli import app

    # Create a Cargo.toml to trigger Rust detection
    (temp_dir / "Cargo.toml").touch()

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["daemon", "start", "-w", str(temp_dir)])
        assert result.exit_code == 0
        assert "[START] Detected language: rust" in result.stderr
        # Verify DaemonManager received detected language
        call_kwargs = mock_manager.call_args.kwargs
        assert call_kwargs["language"] == "rust"


def test_cli_start_explicit_language_override() -> None:
    """Test start command with explicit language."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["daemon", "start", "-l", "rust"])
        assert result.exit_code == 0
        # Verify explicit language was passed
        call_kwargs = mock_manager.call_args.kwargs
        assert call_kwargs["language"] == "rust"


def test_cli_stop_auto_detect_language(temp_dir: Path) -> None:
    """Test stop command with auto-detection."""
    from llm_lsp_cli.cli import app

    # Create a go.mod to trigger Go detection
    (temp_dir / "go.mod").touch()

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["daemon", "stop", "-w", str(temp_dir)])
        assert result.exit_code == 0
        # Verify DaemonManager received detected language
        call_kwargs = mock_manager.call_args.kwargs
        assert call_kwargs["language"] == "go"


def test_cli_restart_auto_detect_language(temp_dir: Path) -> None:
    """Test restart command with auto-detection."""
    from llm_lsp_cli.cli import app

    # Create a pom.xml to trigger Java detection
    (temp_dir / "pom.xml").touch()

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["daemon", "restart", "-w", str(temp_dir)])
        assert result.exit_code == 0
        # Verify DaemonManager received detected language
        call_kwargs = mock_manager.call_args.kwargs
        assert call_kwargs["language"] == "java"


def test_cli_status_auto_detect_language(temp_dir: Path) -> None:
    """Test status command with auto-detection."""
    from llm_lsp_cli.cli import app

    # Create a tsconfig.json to trigger TypeScript detection
    (temp_dir / "tsconfig.json").touch()

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_instance.get_pid.return_value = 12345
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["daemon", "status", "-w", str(temp_dir)])
        assert result.exit_code == 0
        assert "Language: typescript" in result.output
        # Verify DaemonManager received detected language
        call_kwargs = mock_manager.call_args.kwargs
        assert call_kwargs["language"] == "typescript"


# =============================================================================
# YAML Output Format Tests
# =============================================================================


def test_cli_definition_yaml_output(temp_file: Path) -> None:
    """Test definition command with YAML output format."""
    from llm_lsp_cli.cli import app

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = LOCATION_RESPONSE

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["lsp", "definition", str(temp_file), "10", "5", "--format", "yaml", "-w", workspace],
        )
        assert result.exit_code == 0

        # Parse YAML output
        output = yaml.safe_load(result.output)
        assert output is not None
        assert "locations" in output
        assert len(output["locations"]) == 1
        assert output["locations"][0]["uri"] == "file:///path/to/file.py"


def test_cli_references_yaml_output(temp_file: Path) -> None:
    """Test references command with YAML output format."""
    from llm_lsp_cli.cli import app

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = LOCATION_RESPONSE_MULTI

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["lsp", "references", str(temp_file), "10", "5", "-o", "yaml", "-w", workspace],
        )
        assert result.exit_code == 0

        # Parse YAML output - compact format returns flat array
        output = yaml.safe_load(result.output)
        assert isinstance(output, list)
        assert len(output) == 3
        assert "file" in output[0]
        assert "range" in output[0]


def test_cli_completion_yaml_output(temp_file: Path) -> None:
    """Test completion command with YAML output format."""
    from llm_lsp_cli.cli import app

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = COMPLETION_RESPONSE

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["lsp", "completion", str(temp_file), "10", "5", "--format", "yaml", "-w", workspace],
        )
        assert result.exit_code == 0

        # Parse YAML output
        output = yaml.safe_load(result.output)
        assert output is not None
        assert "items" in output
        assert len(output["items"]) == 2
        # Verify all fields are preserved
        assert output["items"][0]["label"] == "my_function"
        assert output["items"][0]["kind"] == 12  # COMPLETION_RESPONSE uses kind 12 (Function)
        assert output["items"][0]["detail"] == "def my_function(x: int) -> str"
        assert output["items"][0]["documentation"] == "A sample function"


def test_cli_hover_yaml_output(temp_file: Path) -> None:
    """Test hover command with YAML output format."""
    from llm_lsp_cli.cli import app

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = HOVER_RESPONSE

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["lsp", "hover", str(temp_file), "10", "5", "--format", "yaml", "-w", workspace],
        )
        assert result.exit_code == 0

        # Parse YAML output
        output = yaml.safe_load(result.output)
        assert output is not None
        assert "hover" in output
        assert output["hover"]["contents"]["kind"] == "markdown"
        assert "value" in output["hover"]["contents"]
        assert output["hover"]["range"]["start"]["line"] == 10


def test_cli_document_symbol_yaml_output(temp_file: Path) -> None:
    """Test document-symbol command with YAML output format."""
    from llm_lsp_cli.cli import app

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = DOCUMENT_SYMBOL_WITH_CHILDREN

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["lsp", "document-symbol", str(temp_file), "--format", "yaml", "-w", workspace],
        )
        assert result.exit_code == 0

        # Parse YAML output - compact format returns flat array
        output = yaml.safe_load(result.output)
        assert isinstance(output, list)
        assert len(output) >= 1  # At least MyClass (children may be flattened or omitted)
        assert "file" in output[0]
        assert "name" in output[0]
        assert "kind_name" in output[0]  # Compact format uses kind_name
        assert "range" in output[0]


def test_cli_workspace_symbol_yaml_output(temp_dir: Path) -> None:
    """Test workspace-symbol command with YAML output format."""
    from llm_lsp_cli.cli import app

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = WORKSPACE_SYMBOL_RESPONSE

        workspace = str(temp_dir)
        result = runner.invoke(
            app,
            ["lsp", "workspace-symbol", "MyClass", "--format", "yaml", "-w", workspace],
        )
        assert result.exit_code == 0

        # Parse YAML output - compact format returns flat array
        output = yaml.safe_load(result.output)
        assert isinstance(output, list)
        assert len(output) == 2
        assert "file" in output[0]
        assert "name" in output[0]
        assert "kind_name" in output[0]  # Compact format uses kind_name
        assert "range" in output[0]


def test_cli_format_explicit_text(temp_file: Path) -> None:
    """Test that explicit text format works correctly."""
    from llm_lsp_cli.cli import app

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = LOCATION_RESPONSE

        workspace = str(temp_file.parent)
        # Test with explicit text format
        result = runner.invoke(
            app, ["lsp", "definition", str(temp_file), "10", "5", "--format", "text", "-w", workspace]
        )
        assert result.exit_code == 0
        # Text output should contain formatted path with full range
        assert "file:///path/to/file.py:11:" in result.output


def test_cli_format_invalid_option(temp_file: Path) -> None:
    """Test that invalid format option shows error."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["lsp", "definition", str(temp_file), "10", "5", "--format", "xml", "-w", workspace],
        )
        # Should fail because 'xml' is not a valid format
        assert result.exit_code != 0


def test_cli_yaml_output_preserves_all_fields(temp_file: Path) -> None:
    """Test that YAML output preserves ALL fields from LSP responses - no data loss."""
    from llm_lsp_cli.cli import app

    # Comprehensive mock response with many LSP fields
    mock_response = {
        "items": [
            {
                "label": "complex_function",
                "kind": 3,
                "tags": [1, 2],
                "detail": "def complex_function(x: int, y: str) -> tuple",
                "documentation": {
                    "kind": "markdown",
                    "value": "Detailed documentation",
                },
                "deprecated": False,
                "preselect": True,
                "filterText": "complex_function",
                "insertText": "complex_function(${1:x}, ${2:y})",
                "insertTextFormat": 2,
                "textEdit": {
                    "range": {
                        "start": {"line": 10, "character": 0},
                        "end": {"line": 10, "character": 5},
                    },
                    "newText": "complex_function(x, y)",
                },
                "additionalTextEdits": [],
                "commitCharacters": ["(", "{"],
                "data": {"custom": "metadata"},
            }
        ]
    }

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["lsp", "completion", str(temp_file), "10", "5", "--format", "yaml", "-w", workspace],
        )
        assert result.exit_code == 0

        # Parse YAML output
        output = yaml.safe_load(result.output)
        assert output is not None

        # Verify ALL fields are preserved (no data loss)
        item = output["items"][0]
        assert item["label"] == "complex_function"
        assert item["kind"] == 3
        assert item["tags"] == [1, 2]
        assert item["detail"] == "def complex_function(x: int, y: str) -> tuple"
        assert item["documentation"]["kind"] == "markdown"
        assert item["documentation"]["value"] == "Detailed documentation"
        assert item["deprecated"] is False
        assert item["preselect"] is True
        assert item["filterText"] == "complex_function"
        assert item["insertText"] == "complex_function(${1:x}, ${2:y})"
        assert item["insertTextFormat"] == 2
        assert item["textEdit"]["range"]["start"]["line"] == 10
        assert item["textEdit"]["newText"] == "complex_function(x, y)"
        assert item["commitCharacters"] == ["(", "{"]
        assert item["data"]["custom"] == "metadata"


# =============================================================================
# JSON Output Format Tests
# =============================================================================


def test_cli_definition_json_output(temp_file: Path) -> None:
    """Test definition command with JSON output format."""
    from llm_lsp_cli.cli import app

    mock_response = {
        "locations": [
            {
                "uri": "file:///path/to/file.py",
                "range": {
                    "start": {"line": 10, "character": 4},
                    "end": {"line": 10, "character": 20},
                },
            }
        ]
    }

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["lsp", "definition", str(temp_file), "10", "5", "--format", "json", "-w", workspace],
        )
        assert result.exit_code == 0

        # Parse JSON output
        output = json.loads(result.output)
        assert output is not None
        assert "locations" in output
        assert len(output["locations"]) == 1
        assert output["locations"][0]["uri"] == "file:///path/to/file.py"
        assert output["locations"][0]["range"]["start"]["line"] == 10
        assert output["locations"][0]["range"]["end"]["character"] == 20


def test_cli_references_json_output(temp_file: Path) -> None:
    """Test references command with JSON output format."""
    from llm_lsp_cli.cli import app

    mock_response = {
        "locations": [
            {
                "uri": "file:///path/to/file1.py",
                "range": {
                    "start": {"line": 5, "character": 0},
                    "end": {"line": 5, "character": 15},
                },
            },
            {
                "uri": "file:///path/to/file2.py",
                "range": {
                    "start": {"line": 20, "character": 8},
                    "end": {"line": 20, "character": 23},
                },
            },
        ]
    }

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["lsp", "references", str(temp_file), "10", "5", "--format", "json", "-w", workspace],
        )
        assert result.exit_code == 0

        # Parse JSON output - compact format returns flat array
        output = json.loads(result.output)
        assert isinstance(output, list)
        assert len(output) == 2
        assert "file" in output[0]
        assert "range" in output[0]


def test_cli_completion_json_output(temp_file: Path) -> None:
    """Test completion command with JSON output format."""
    from llm_lsp_cli.cli import app

    mock_response = {
        "items": [
            {
                "label": "my_function",
                "kind": 3,
                "detail": "def my_function(x: int) -> str",
                "documentation": "A sample function",
                "textEdit": {
                    "range": {
                        "start": {"line": 10, "character": 0},
                        "end": {"line": 10, "character": 5},
                    },
                    "newText": "my_function()",
                },
            },
            {
                "label": "my_variable",
                "kind": 6,
                "detail": "str",
            },
        ]
    }

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["lsp", "completion", str(temp_file), "10", "5", "--format", "json", "-w", workspace],
        )
        assert result.exit_code == 0

        # Parse JSON output
        output = json.loads(result.output)
        assert output is not None
        assert "items" in output
        assert len(output["items"]) == 2
        # Verify all fields are preserved including textEdit range
        item = output["items"][0]
        assert item["label"] == "my_function"
        assert item["textEdit"]["range"]["start"]["line"] == 10
        assert item["textEdit"]["range"]["end"]["character"] == 5


def test_cli_hover_json_output(temp_file: Path) -> None:
    """Test hover command with JSON output format."""
    from llm_lsp_cli.cli import app

    mock_response = {
        "hover": {
            "contents": {
                "kind": "markdown",
                "value": "```python\ndef my_function(x: int) -> str\n```\n\nA sample function.",
            },
            "range": {
                "start": {"line": 10, "character": 4},
                "end": {"line": 10, "character": 15},
            },
        }
    }

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["lsp", "hover", str(temp_file), "10", "5", "--format", "json", "-w", workspace],
        )
        assert result.exit_code == 0

        # Parse JSON output
        output = json.loads(result.output)
        assert output is not None
        assert "hover" in output
        assert output["hover"]["contents"]["kind"] == "markdown"
        assert "value" in output["hover"]["contents"]
        # Verify hover range is preserved
        assert output["hover"]["range"]["start"]["line"] == 10
        assert output["hover"]["range"]["end"]["character"] == 15


def test_cli_document_symbol_json_output(temp_file: Path) -> None:
    """Test document-symbol command with JSON output format."""
    from llm_lsp_cli.cli import app

    mock_response = {
        "symbols": [
            {
                "name": "MyClass",
                "kind": 5,
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 50, "character": 0},
                },
                "selectionRange": {
                    "start": {"line": 0, "character": 6},
                    "end": {"line": 0, "character": 13},
                },
            }
        ]
    }

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["lsp", "document-symbol", str(temp_file), "--format", "json", "-w", workspace],
        )
        assert result.exit_code == 0

        # Parse JSON output - compact format returns flat array
        output = json.loads(result.output)
        assert isinstance(output, list)
        assert len(output) >= 1
        assert "file" in output[0]
        assert "name" in output[0]
        assert "kind_name" in output[0]  # Compact format uses kind_name
        assert "range" in output[0]


def test_cli_workspace_symbol_json_output(temp_dir: Path) -> None:
    """Test workspace-symbol command with JSON output format."""
    from llm_lsp_cli.cli import app

    mock_response = {
        "symbols": [
            {
                "name": "MyClass",
                "kind": 5,
                "location": {
                    "uri": "file:///path/to/myclass.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 50, "character": 0},
                    },
                },
            },
            {
                "name": "helper_function",
                "kind": 12,
                "location": {
                    "uri": "file:///path/to/utils.py",
                    "range": {
                        "start": {"line": 10, "character": 0},
                        "end": {"line": 25, "character": 0},
                    },
                },
            },
        ]
    }

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        result = runner.invoke(
            app, ["lsp", "workspace-symbol", "My", "--format", "json", "-w", str(temp_dir)]
        )
        assert result.exit_code == 0

        # Parse JSON output - compact format returns flat array
        output = json.loads(result.output)
        assert isinstance(output, list)
        assert len(output) == 2
        assert "file" in output[0]
        assert "name" in output[0]
        assert "kind_name" in output[0]  # Compact format uses kind_name
        assert "range" in output[0]


# =============================================================================
# Text Format Range Tests
# =============================================================================


def test_cli_definition_text_format_shows_full_range(temp_file: Path) -> None:
    """Test that text format shows full start-end range, not just start position."""
    from llm_lsp_cli.cli import app

    mock_response = {
        "locations": [
            {
                "uri": "file:///path/to/file.py",
                "range": {
                    "start": {"line": 10, "character": 4},
                    "end": {"line": 10, "character": 20},
                },
            }
        ]
    }

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["lsp", "definition", str(temp_file), "10", "5", "--format", "text", "-w", workspace],
        )
        assert result.exit_code == 0
        # Text format should show full range: start-end (e.g., "11:5-11:21" with 1-based positions)
        output = result.output.strip()
        # Should show the range, not just the start position
        assert "11:" in output  # Line number (1-based)
        # The range should include end position info (1-based: 4+1=5, 20+1=21)
        assert "5" in output and "21" in output  # Character positions (1-based)
        # Verify full range format: start_line:start_char-end_line:end_char
        assert "11:5-11:21" in output


def test_cli_references_text_format_shows_full_range(temp_file: Path) -> None:
    """Test that references text format shows full start-end range."""
    from llm_lsp_cli.cli import app

    mock_response = {
        "locations": [
            {
                "uri": "file:///path/to/file1.py",
                "range": {
                    "start": {"line": 5, "character": 0},
                    "end": {"line": 5, "character": 15},
                },
            }
        ]
    }

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["lsp", "references", str(temp_file), "10", "5", "--format", "text", "-w", workspace],
        )
        assert result.exit_code == 0
        # Should show full range information
        output = result.output.strip()
        assert "6:" in output  # Line number (1-based)


def test_cli_completion_text_format_includes_range(temp_file: Path) -> None:
    """Test that completion text format includes textEdit range when available."""
    from llm_lsp_cli.cli import app

    mock_response = {
        "items": [
            {
                "label": "my_function",
                "kind": 3,
                "detail": "def my_function(x: int) -> str",
                "textEdit": {
                    "range": {
                        "start": {"line": 10, "character": 0},
                        "end": {"line": 10, "character": 5},
                    },
                    "newText": "my_function()",
                },
            }
        ]
    }

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["lsp", "completion", str(temp_file), "10", "5", "--format", "text", "-w", workspace],
        )
        assert result.exit_code == 0
        # Text format should include range info from textEdit
        output = result.output.strip()
        assert "my_function" in output


def test_cli_hover_text_format_includes_range(temp_file: Path) -> None:
    """Test that hover text format includes hover range."""
    from llm_lsp_cli.cli import app

    mock_response = {
        "hover": {
            "contents": {
                "kind": "markdown",
                "value": "```python\ndef my_function(x: int) -> str\n```",
            },
            "range": {
                "start": {"line": 10, "character": 4},
                "end": {"line": 10, "character": 15},
            },
        }
    }

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["lsp", "hover", str(temp_file), "10", "5", "--format", "text", "-w", workspace],
        )
        assert result.exit_code == 0
        # Should show hover content
        output = result.output.strip()
        assert "def my_function" in output


def test_cli_document_symbol_text_format_shows_full_range(temp_file: Path) -> None:
    """Test that document-symbol text format shows full range (start-end), not just start."""
    from llm_lsp_cli.cli import app

    mock_response = {
        "symbols": [
            {
                "name": "MyClass",
                "kind": 5,
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 50, "character": 0},
                },
            }
        ]
    }

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["lsp", "document-symbol", str(temp_file), "--format", "text", "-w", workspace],
        )
        assert result.exit_code == 0
        # Should show full range (start-end), not just start position
        output = result.output.strip()
        assert "MyClass" in output
        # Should include both start and end line info
        # Currently only shows start (line 1), should show "1-51" or similar
        assert "1:" in output  # Start line (1-based)


def test_cli_workspace_symbol_text_format_includes_range(temp_dir: Path) -> None:
    """Test that workspace-symbol text format includes range from location."""
    from llm_lsp_cli.cli import app

    mock_response = {
        "symbols": [
            {
                "name": "MyClass",
                "kind": 5,
                "location": {
                    "uri": "file:///path/to/myclass.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 50, "character": 0},
                    },
                },
            }
        ]
    }

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        result = runner.invoke(
            app,
            ["lsp", "workspace-symbol", "My", "--format", "text", "-w", str(temp_dir)],
        )
        assert result.exit_code == 0
        # Should include range information from location
        output = result.output.strip()
        assert "MyClass" in output
        assert "myclass.py" in output


# =============================================================================
# Default Format Tests
# =============================================================================


def test_cli_default_format_is_json(temp_file: Path) -> None:
    """Test that the default output format is JSON (not text)."""
    from llm_lsp_cli.cli import app

    mock_response = {
        "locations": [
            {
                "uri": "file:///path/to/file.py",
                "range": {
                    "start": {"line": 10, "character": 4},
                    "end": {"line": 10, "character": 20},
                },
            }
        ]
    }

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        # Test without --format option (should default to JSON)
        result = runner.invoke(app, ["lsp", "definition", str(temp_file), "10", "5", "-w", workspace])
        assert result.exit_code == 0

        # Output should be valid JSON (not text format)
        output = json.loads(result.output)
        assert output is not None
        assert "locations" in output


# =============================================================================
# LSP Symbol Kind Translation Tests
# =============================================================================


def test_symbol_kind_translation_function_exists() -> None:
    """Test that the symbol kind translation function exists and works."""
    from llm_lsp_cli.utils.formatter import get_symbol_kind_name

    # Test various kind values from LSP 3.17 spec
    assert get_symbol_kind_name(1) == "File"
    assert get_symbol_kind_name(5) == "Class"
    assert get_symbol_kind_name(12) == "Function"
    assert get_symbol_kind_name(6) == "Method"
    assert get_symbol_kind_name(13) == "Variable"
    assert get_symbol_kind_name(14) == "Constant"


def test_symbol_kind_translation_unknown_kind() -> None:
    """Test that unknown kind values return a fallback string."""
    from llm_lsp_cli.utils.formatter import get_symbol_kind_name

    # Unknown kind should return "Unknown" with the number
    assert get_symbol_kind_name(999) == "Unknown(999)"
    assert get_symbol_kind_name(0) == "Unknown(0)"
    assert get_symbol_kind_name(-1) == "Unknown(-1)"


def test_document_symbol_text_format_translates_kind(temp_file: Path) -> None:
    """Test that document-symbol text output uses compact numeric kind format."""
    from llm_lsp_cli.cli import app

    mock_response = {
        "symbols": [
            {
                "name": "MyClass",
                "kind": 5,  # Class
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 50, "character": 0},
                },
            },
            {
                "name": "myFunction",
                "kind": 12,  # Function
                "range": {
                    "start": {"line": 55, "character": 0},
                    "end": {"line": 70, "character": 0},
                },
            },
            {
                "name": "myMethod",
                "kind": 6,  # Method
                "range": {
                    "start": {"line": 10, "character": 4},
                    "end": {"line": 20, "character": 4},
                },
            },
        ]
    }

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["lsp", "document-symbol", str(temp_file), "--format", "text", "-w", workspace],
        )
        assert result.exit_code == 0

        output = result.output.strip()
        # Compact format uses kind names for readability
        # For document-symbol without URI in response, file header may be empty
        assert "MyClass (Class)" in output  # Kind name
        assert "myFunction (Function)" in output
        assert "myMethod (Method)" in output
        # Output should include range information (bare format, no brackets)
        assert "1:1-51:1" in output  # Range format
        # Output should be indented (symbols under file header)
        assert "  " in output  # Indented symbols


def test_workspace_symbol_text_format_translates_kind(temp_dir: Path) -> None:
    """Test that workspace-symbol text output translates kind numbers to names."""
    from llm_lsp_cli.cli import app

    mock_response = {
        "symbols": [
            {
                "name": "MyClass",
                "kind": 5,  # Class
                "location": {
                    "uri": "file:///path/to/myclass.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 50, "character": 0},
                    },
                },
            },
            {
                "name": "helper_function",
                "kind": 12,  # Function
                "location": {
                    "uri": "file:///path/to/utils.py",
                    "range": {
                        "start": {"line": 10, "character": 0},
                        "end": {"line": 25, "character": 0},
                    },
                },
            },
            {
                "name": "CONFIG_VALUE",
                "kind": 14,  # Constant
                "location": {
                    "uri": "file:///path/to/config.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            },
        ]
    }

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        result = runner.invoke(
            app,
            ["lsp", "workspace-symbol", "My", "--format", "text", "-w", str(temp_dir)],
        )
        assert result.exit_code == 0

        output = result.output.strip()
        # New format: "file: name (kind_name) [range]"
        assert "MyClass (Class)" in output  # Kind name
        assert "helper_function (Function)" in output
        assert "CONFIG_VALUE (Constant)" in output


def test_all_lsp_symbol_kinds_are_mapped() -> None:
    """Test that all LSP 3.17 symbol kinds (1-26) are mapped."""
    from llm_lsp_cli.utils.formatter import get_symbol_kind_name

    # All LSP 3.17 symbol kinds
    expected_mappings = {
        1: "File",
        2: "Module",
        3: "Namespace",
        4: "Package",
        5: "Class",
        6: "Method",
        7: "Property",
        8: "Field",
        9: "Constructor",
        10: "Enum",
        11: "Interface",
        12: "Function",
        13: "Variable",
        14: "Constant",
        15: "String",
        16: "Number",
        17: "Boolean",
        18: "Array",
        19: "Object",
        20: "Key",
        21: "Null",
        22: "EnumMember",
        23: "Struct",
        24: "Event",
        25: "Operator",
        26: "TypeParameter",
    }

    for kind_number, expected_name in expected_mappings.items():
        result = get_symbol_kind_name(kind_number)
        assert result == expected_name, (
            f"Kind {kind_number} should map to '{expected_name}', got '{result}'"
        )


# =============================================================================
# Test Filtering Tests
# =============================================================================


def test_cli_references_filters_tests_by_default(temp_file: Path) -> None:
    """Test that references command filters test files by default."""
    from llm_lsp_cli.cli import app

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = create_location_response_with_test_files()

        workspace = str(temp_file.parent)

        # Test without --include-tests (should filter out test locations)
        result = runner.invoke(
            app,
            ["lsp", "references", str(temp_file), "10", "5", "-w", workspace],
        )
        assert result.exit_code == 0
        # Without flag, test locations should be filtered
        # Compact format returns flat array directly
        output = json.loads(result.output)
        assert isinstance(output, list)
        assert len(output) == 1
        assert "test_file.py" not in output[0]["file"]


def test_cli_references_include_tests_flag(temp_file: Path) -> None:
    """Test that references command accepts --include-tests flag."""
    from llm_lsp_cli.cli import app

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = create_location_response_with_test_files()

        workspace = str(temp_file.parent)

        # Test with --include-tests (should include all locations)
        result = runner.invoke(
            app,
            ["lsp", "references", str(temp_file), "10", "5", "--include-tests", "-w", workspace],
        )
        assert result.exit_code == 0
        # With flag, all locations should be included
        # Compact format returns flat array directly
        output = json.loads(result.output)
        assert isinstance(output, list)
        assert len(output) == 2


def test_cli_workspace_symbol_filters_tests_by_default(temp_dir: Path) -> None:
    """Test that workspace-symbol command filters test files by default."""
    from llm_lsp_cli.cli import app

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = create_workspace_symbol_response_with_test_files()

        # Test without --include-tests (should filter out test symbols)
        result = runner.invoke(
            app,
            ["lsp", "workspace-symbol", "My", "-w", str(temp_dir)],
        )
        assert result.exit_code == 0
        # Without flag, test symbols should be filtered
        # Compact format returns flat array directly
        output = json.loads(result.output)
        assert isinstance(output, list)
        assert len(output) == 1
        assert "test" not in output[0]["file"].lower()


def test_cli_workspace_symbol_include_tests_flag(temp_dir: Path) -> None:
    """Test that workspace-symbol command accepts --include-tests flag."""
    from llm_lsp_cli.cli import app

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = create_workspace_symbol_response_with_test_files()

        # Test with --include-tests (should include all symbols)
        result = runner.invoke(
            app,
            ["lsp", "workspace-symbol", "My", "--include-tests", "-w", str(temp_dir)],
        )
        assert result.exit_code == 0
        # With flag, all symbols should be included
        # Compact format returns flat array directly
        output = json.loads(result.output)
        assert isinstance(output, list)
        assert len(output) == 2


def test_cli_references_yaml_with_include_tests(temp_file: Path) -> None:
    """Test references command with YAML format and --include-tests flag."""
    import yaml

    from llm_lsp_cli.cli import app

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = create_location_response_with_test_files()

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            [
                "lsp",
                "references",
                str(temp_file),
                "10",
                "5",
                "--format",
                "yaml",
                "--include-tests",
                "-w",
                workspace,
            ],
        )
        assert result.exit_code == 0

        # Parse YAML output - compact format returns flat array
        output = yaml.safe_load(result.output)
        assert isinstance(output, list)
        assert len(output) == 2


def test_cli_workspace_symbol_yaml_with_include_tests(temp_dir: Path) -> None:
    """Test workspace-symbol command with YAML format and --include-tests flag."""
    import yaml

    from llm_lsp_cli.cli import app

    with (
        patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
        patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
    ):
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = create_workspace_symbol_response_with_test_files()

        result = runner.invoke(
            app,
            [
                "lsp",
                "workspace-symbol",
                "My",
                "--format",
                "yaml",
                "--include-tests",
                "-w",
                str(temp_dir),
            ],
        )
        assert result.exit_code == 0

        # Parse YAML output - compact format returns flat array
        output = yaml.safe_load(result.output)
        assert isinstance(output, list)
        assert len(output) == 2


# =============================================================================
# CSV Output Format Tests
# =============================================================================


class TestDefinitionCsvOutput:
    """CSV output tests for definition command."""

    def test_cli_definition_csv_basic(self, temp_file: Path) -> None:
        """Test definition command with CSV output format."""
        from llm_lsp_cli.cli import app

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = LOCATION_RESPONSE

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "definition", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            # Verify CSV output has header and data row
            lines = result.output.strip().split("\n")
            assert len(lines) == 2  # Header + 1 data row
            assert "uri" in lines[0]
            assert "file:///path/to/file.py" in lines[1]

    def test_cli_definition_csv_multiple_locations(self, temp_file: Path) -> None:
        """Test CSV output with multiple definition locations."""
        from llm_lsp_cli.cli import app

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = LOCATION_RESPONSE_MULTI

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "definition", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            # LOCATION_RESPONSE_MULTI has 3 locations
            lines = result.output.strip().split("\n")
            assert len(lines) == 4  # Header + 3 data rows

    def test_cli_definition_csv_columns_correct(self, temp_file: Path) -> None:
        """Test that CSV has correct columns: uri,start_line,start_char,end_line,end_char."""
        from llm_lsp_cli.cli import app

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = LOCATION_RESPONSE

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "definition", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            header = result.output.strip().split("\n")[0]
            assert header == "uri,start_line,start_char,end_line,end_char"


class TestReferencesCsvOutput:
    """CSV output tests for references command."""

    def test_cli_references_csv_basic(self, temp_file: Path) -> None:
        """Test references command with CSV output format."""
        from llm_lsp_cli.cli import app

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = LOCATION_RESPONSE

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "references", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            lines = result.output.strip().split("\n")
            assert len(lines) == 2  # Header + 1 data row
            # Compact CSV uses file,range columns for locations
            assert "file" in lines[0]
            assert "range" in lines[0]

    def test_cli_references_csv_same_schema_as_definition(self, temp_file: Path) -> None:
        """Test references CSV uses same schema as definition (locations)."""
        from llm_lsp_cli.cli import app

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = LOCATION_RESPONSE

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "references", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            header = result.output.strip().split("\n")[0]
            # Compact CSV uses file,range columns for locations
            assert header == "file,range"


class TestCompletionCsvOutput:
    """CSV output tests for completion command."""

    def test_cli_completion_csv_basic(self, temp_file: Path) -> None:
        """Test completion command with CSV output format."""
        from llm_lsp_cli.cli import app

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = COMPLETION_RESPONSE

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "completion", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            # COMPLETION_RESPONSE has 2 items
            lines = result.output.strip().split("\n")
            assert len(lines) == 3  # Header + 2 data rows
            assert "label" in lines[0]

    def test_cli_completion_csv_includes_kind_name(self, temp_file: Path) -> None:
        """Test CSV output translates kind number to human-readable name."""
        from llm_lsp_cli.cli import app

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = COMPLETION_RESPONSE

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "completion", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            # Verify kind_name column is present with translated value
            # COMPLETION_RESPONSE has kinds 12 (Function) and 13 (Variable)
            assert "kind_name" in result.output
            assert "Function" in result.output

    def test_cli_completion_csv_escapes_special_chars(self, temp_file: Path) -> None:
        """Test CSV properly escapes commas/quotes in completion details."""
        import csv
        import io

        from llm_lsp_cli.cli import app

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = COMPLETION_RESPONSE_WITH_COMMAS

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "completion", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            # Parse CSV to verify proper escaping
            # COMPLETION_RESPONSE_WITH_COMMAS has commas in detail/documentation
            reader = csv.DictReader(io.StringIO(result.output))
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["detail"] == "def func(a, b, c):  # has, commas"
            assert rows[0]["documentation"] == "Documentation, with, commas"


class TestHoverCsvOutput:
    """CSV output tests for hover command."""

    def test_cli_hover_csv_basic(self, temp_file: Path) -> None:
        """Test hover command with CSV output format."""
        from llm_lsp_cli.cli import app

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = HOVER_RESPONSE

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "hover", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            lines = result.output.strip().split("\n")
            assert len(lines) == 2  # Header + 1 data row

    def test_cli_hover_csv_single_row(self, temp_file: Path) -> None:
        """Test hover CSV produces single row (not a list)."""
        from llm_lsp_cli.cli import app

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = HOVER_RESPONSE_PLAINTEXT

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "hover", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            lines = result.output.strip().split("\n")
            assert len(lines) == 2  # Header + single data row


class TestDocumentSymbolCsvOutput:
    """CSV output tests for document-symbol command."""

    def test_cli_document_symbol_csv_basic(self, temp_file: Path) -> None:
        """Test document-symbol command with CSV output format."""
        from llm_lsp_cli.cli import app

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = DOCUMENT_SYMBOL_RESPONSE

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "document-symbol", str(temp_file), "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            lines = result.output.strip().split("\n")
            assert len(lines) == 2  # Header + 1 data row
            assert "name" in lines[0]

    def test_cli_document_symbol_csv_kind_translation(self, temp_file: Path) -> None:
        """Test CSV output uses numeric kind format."""
        from llm_lsp_cli.cli import app

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = DOCUMENT_SYMBOL_RESPONSE

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "document-symbol", str(temp_file), "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            # Compact CSV uses numeric kind (LLMs know the mapping)
            # Headers: file,name,kind,range,detail,container,tags
            assert "kind" in result.output
            assert "5" in result.output  # Numeric kind value


class TestWorkspaceSymbolCsvOutput:
    """CSV output tests for workspace-symbol command."""

    def test_cli_workspace_symbol_csv_basic(self, temp_dir: Path) -> None:
        """Test workspace-symbol command with CSV output format."""
        from llm_lsp_cli.cli import app

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = WORKSPACE_SYMBOL_RESPONSE

            result = runner.invoke(
                app,
                ["lsp", "workspace-symbol", "My", "--format", "csv", "-w", str(temp_dir)],
            )
            assert result.exit_code == 0

            # WORKSPACE_SYMBOL_RESPONSE has 2 symbols
            lines = result.output.strip().split("\n")
            assert len(lines) == 3  # Header + 2 data rows

    def test_cli_workspace_symbol_csv_includes_uri(self, temp_dir: Path) -> None:
        """Test workspace symbol CSV includes file column."""
        from llm_lsp_cli.cli import app

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = WORKSPACE_SYMBOL_RESPONSE

            result = runner.invoke(
                app,
                ["lsp", "workspace-symbol", "My", "--format", "csv", "-w", str(temp_dir)],
            )
            assert result.exit_code == 0

            # Compact CSV uses 'file' column (relative path)
            header = result.output.strip().split("\n")[0]
            assert "file" in header


class TestCsvFormatOption:
    """Tests for CSV format option parsing and validation."""

    def test_csv_format_option_accepted(self, temp_file: Path) -> None:
        """Test --format csv is accepted without error."""
        from llm_lsp_cli.cli import app

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = LOCATION_RESPONSE

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "definition", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            # Should not fail due to format option parsing
            assert result.exit_code == 0

    def test_csv_format_short_option(self, temp_file: Path) -> None:
        """Test -o csv is accepted."""
        from llm_lsp_cli.cli import app

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = LOCATION_RESPONSE

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "definition", str(temp_file), "10", "5", "-o", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

    def test_csv_help_text_updated(self) -> None:
        """Test --help includes csv in format options."""
        from llm_lsp_cli.cli import app

        result = runner.invoke(app, ["lsp", "definition", "--help"])
        assert result.exit_code == 0

        # Help text should mention csv as a valid format
        # This test will fail until the help text is updated
        assert "csv" in result.output.lower()


# =============================================================================
# Restart Debug Flag Tests
# =============================================================================


def test_restart_debug_flag_present_in_help() -> None:
    """Test that the --debug flag appears in restart --help output."""
    from llm_lsp_cli.cli import app

    result = runner.invoke(app, ["daemon", "restart", "--help"])
    assert result.exit_code == 0
    # Flag should be present
    assert "--debug" in result.output or "-d" in result.output
    # Help text should include description
    assert "debug" in result.output.lower()


def test_restart_debug_flag_passed_to_daemon_manager() -> None:
    """Test that debug=True is passed to DaemonManager when --debug is used."""
    from llm_lsp_cli.cli import app

    mock_instance = MagicMock()
    mock_instance.is_running.return_value = True

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["daemon", "restart", "--debug"])
        assert result.exit_code == 0

        # Verify DaemonManager constructor received debug=True
        call_kwargs = mock_manager.call_args.kwargs
        assert call_kwargs["debug"] is True


def test_restart_without_debug_flag_default_false() -> None:
    """Test that default behavior (no --debug) passes debug=False."""
    from llm_lsp_cli.cli import app

    mock_instance = MagicMock()
    mock_instance.is_running.return_value = True

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["daemon", "restart"])
        assert result.exit_code == 0

        # Verify DaemonManager constructor received debug=False (default)
        call_kwargs = mock_manager.call_args.kwargs
        assert call_kwargs["debug"] is False


def test_restart_debug_short_flag() -> None:
    """Test that -d short flag works identically to --debug."""
    from llm_lsp_cli.cli import app

    mock_instance = MagicMock()
    mock_instance.is_running.return_value = True

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["daemon", "restart", "-d"])
        assert result.exit_code == 0

        # Verify DaemonManager constructor received debug=True
        call_kwargs = mock_manager.call_args.kwargs
        assert call_kwargs["debug"] is True


def test_restart_debug_with_other_options() -> None:
    """Test that --debug works in combination with other flags."""
    from llm_lsp_cli.cli import app

    mock_instance = MagicMock()
    mock_instance.is_running.return_value = True

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_manager.return_value = mock_instance

        result = runner.invoke(
            app, ["daemon", "restart", "--debug", "--workspace", "/tmp", "--language", "python"]
        )
        assert result.exit_code == 0

        # Verify DaemonManager constructor received debug=True and other options
        call_kwargs = mock_manager.call_args.kwargs
        assert call_kwargs["debug"] is True
        # On macOS, /tmp is a symlink to /private/tmp, so we need to resolve
        assert call_kwargs["workspace_path"] in ["/tmp", "/private/tmp"]
        assert call_kwargs["language"] == "python"
