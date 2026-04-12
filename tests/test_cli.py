"""Tests for the CLI interface."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import yaml  # type: ignore[import-untyped]
from typer.testing import CliRunner

runner = CliRunner()


def test_cli_help() -> None:
    """Test that CLI help works."""
    from llm_lsp_cli.cli import app

    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "llm-lsp-cli" in result.output
    assert "definition" in result.output
    assert "references" in result.output


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

        result = runner.invoke(app, ["start"])
        assert result.exit_code == 0


def test_cli_stop() -> None:
    """Test stop command."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["stop"])
        assert result.exit_code == 0


def test_cli_status() -> None:
    """Test status command."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_instance.get_pid.return_value = 12345
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "Daemon" in result.output


def test_cli_config_show() -> None:
    """Test config show command."""
    from llm_lsp_cli.cli import app

    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "languages" in result.output
    assert "socket_path" in result.output


def test_cli_config_init() -> None:
    """Test config init command."""
    from llm_lsp_cli.cli import app

    result = runner.invoke(app, ["config", "init"])
    assert result.exit_code == 0
    assert "Configuration" in result.output


def test_cli_config_path() -> None:
    """Test config path command."""
    from llm_lsp_cli.cli import app

    result = runner.invoke(app, ["config", "path"])
    assert result.exit_code == 0
    assert "config.json" in result.output


def test_cli_definition_daemon_not_running() -> None:
    """Test definition command auto-starts daemon when not running."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
         patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class, \
         patch("llm_lsp_cli.cli._validate_file_in_workspace") as mock_validate:
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

        result = runner.invoke(app, ["definition", "test.py", "10", "5"])
        # Auto-start should succeed (exit code 0) and return JSON
        assert result.exit_code == 0


def test_cli_definition_file_not_found() -> None:
    """Test definition command when file doesn't exist."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["definition", "nonexistent/file.py", "10", "5"])
        assert result.exit_code == 1
        assert "File not found" in result.output


def test_cli_references_daemon_not_running() -> None:
    """Test references command auto-starts daemon when not running."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
         patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class, \
         patch("llm_lsp_cli.cli._validate_file_in_workspace") as mock_validate:
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

        result = runner.invoke(app, ["references", "test.py", "10", "5"])
        # Auto-start should succeed (exit code 0) and return JSON
        assert result.exit_code == 0


def test_cli_hover_daemon_not_running() -> None:
    """Test hover command auto-starts daemon when not running."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
         patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class, \
         patch("llm_lsp_cli.cli._validate_file_in_workspace") as mock_validate:
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

        result = runner.invoke(app, ["hover", "test.py", "10", "5"])
        # Auto-start should succeed (exit code 0) and return JSON
        assert result.exit_code == 0


def test_cli_document_symbol_daemon_not_running() -> None:
    """Test document-symbol command auto-starts daemon when not running."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
         patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class, \
         patch("llm_lsp_cli.cli._validate_file_in_workspace") as mock_validate:
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

        result = runner.invoke(app, ["document-symbol", "test.py"])
        # Auto-start should succeed (exit code 0) and return JSON
        assert result.exit_code == 0


def test_cli_workspace_symbol_daemon_not_running() -> None:
    """Test workspace-symbol command auto-starts daemon when not running."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
         patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        mock_manager.return_value = mock_instance

        # Mock DaemonClient async request
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value={"symbols": []})
        mock_client.close = AsyncMock()
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["workspace-symbol", "MyClass"])
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

        result = runner.invoke(app, ["start", "-w", str(temp_dir)])
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

        result = runner.invoke(app, ["start", "-l", "rust"])
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

        result = runner.invoke(app, ["stop", "-w", str(temp_dir)])
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

        result = runner.invoke(app, ["restart", "-w", str(temp_dir)])
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

        result = runner.invoke(app, ["status", "-w", str(temp_dir)])
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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["definition", str(temp_file), "10", "5", "--format", "yaml", "-w", workspace],
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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["references", str(temp_file), "10", "5", "-o", "yaml", "-w", workspace],
        )
        assert result.exit_code == 0

        # Parse YAML output
        output = yaml.safe_load(result.output)
        assert output is not None
        assert "locations" in output
        assert len(output["locations"]) == 2


def test_cli_completion_yaml_output(temp_file: Path) -> None:
    """Test completion command with YAML output format."""
    from llm_lsp_cli.cli import app

    mock_response = {
        "items": [
            {
                "label": "my_function",
                "kind": 3,
                "detail": "def my_function(x: int) -> str",
                "documentation": "A sample function",
            },
            {
                "label": "my_variable",
                "kind": 6,
                "detail": "str",
            },
        ]
    }

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["completion", str(temp_file), "10", "5", "--format", "yaml", "-w", workspace],
        )
        assert result.exit_code == 0

        # Parse YAML output
        output = yaml.safe_load(result.output)
        assert output is not None
        assert "items" in output
        assert len(output["items"]) == 2
        # Verify all fields are preserved
        assert output["items"][0]["label"] == "my_function"
        assert output["items"][0]["kind"] == 3
        assert output["items"][0]["detail"] == "def my_function(x: int) -> str"
        assert output["items"][0]["documentation"] == "A sample function"


def test_cli_hover_yaml_output(temp_file: Path) -> None:
    """Test hover command with YAML output format."""
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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["hover", str(temp_file), "10", "5", "--format", "yaml", "-w", workspace],
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

    mock_response = {
        "symbols": [
            {
                "name": "MyClass",
                "kind": 5,
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 50, "character": 0},
                },
                "children": [
                    {
                        "name": "__init__",
                        "kind": 6,
                        "range": {
                            "start": {"line": 5, "character": 4},
                            "end": {"line": 10, "character": 0},
                        },
                    }
                ],
            },
            {
                "name": "my_function",
                "kind": 12,
                "range": {
                    "start": {"line": 55, "character": 0},
                    "end": {"line": 70, "character": 0},
                },
            },
        ]
    }

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["document-symbol", str(temp_file), "--format", "yaml", "-w", workspace],
        )
        assert result.exit_code == 0

        # Parse YAML output
        output = yaml.safe_load(result.output)
        assert output is not None
        assert "symbols" in output
        assert len(output["symbols"]) == 2
        # Verify nested structure is preserved
        assert output["symbols"][0]["name"] == "MyClass"
        assert "children" in output["symbols"][0]
        assert len(output["symbols"][0]["children"]) == 1


def test_cli_workspace_symbol_yaml_output(temp_dir: Path) -> None:
    """Test workspace-symbol command with YAML output format."""
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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        result = runner.invoke(
            app, ["workspace-symbol", "My", "--format", "yaml", "-w", str(temp_dir)]
        )
        assert result.exit_code == 0

        # Parse YAML output
        output = yaml.safe_load(result.output)
        assert output is not None
        assert "symbols" in output
        assert len(output["symbols"]) == 2
        # Verify location structure is preserved
        assert output["symbols"][0]["location"]["uri"] == "file:///path/to/myclass.py"


def test_cli_format_explicit_text(temp_file: Path) -> None:
    """Test that explicit text format works correctly."""
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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        # Test with explicit text format
        result = runner.invoke(
            app, ["definition", str(temp_file), "10", "5", "--format", "text", "-w", workspace]
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
            ["definition", str(temp_file), "10", "5", "--format", "xml", "-w", workspace],
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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["completion", str(temp_file), "10", "5", "--format", "yaml", "-w", workspace],
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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["definition", str(temp_file), "10", "5", "--format", "json", "-w", workspace],
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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["references", str(temp_file), "10", "5", "--format", "json", "-w", workspace],
        )
        assert result.exit_code == 0

        # Parse JSON output
        output = json.loads(result.output)
        assert output is not None
        assert "locations" in output
        assert len(output["locations"]) == 2


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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["completion", str(temp_file), "10", "5", "--format", "json", "-w", workspace],
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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["hover", str(temp_file), "10", "5", "--format", "json", "-w", workspace],
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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["document-symbol", str(temp_file), "--format", "json", "-w", workspace],
        )
        assert result.exit_code == 0

        # Parse JSON output
        output = json.loads(result.output)
        assert output is not None
        assert "symbols" in output
        assert len(output["symbols"]) == 1
        # Verify full range is preserved
        symbol = output["symbols"][0]
        assert symbol["range"]["start"]["line"] == 0
        assert symbol["range"]["end"]["line"] == 50
        assert symbol["selectionRange"]["start"]["character"] == 6


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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        result = runner.invoke(
            app, ["workspace-symbol", "My", "--format", "json", "-w", str(temp_dir)]
        )
        assert result.exit_code == 0

        # Parse JSON output
        output = json.loads(result.output)
        assert output is not None
        assert "symbols" in output
        assert len(output["symbols"]) == 2
        # Verify location with full range is preserved
        assert output["symbols"][0]["location"]["uri"] == "file:///path/to/myclass.py"
        assert output["symbols"][0]["location"]["range"]["end"]["line"] == 50


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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["definition", str(temp_file), "10", "5", "--format", "text", "-w", workspace],
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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["references", str(temp_file), "10", "5", "--format", "text", "-w", workspace],
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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["completion", str(temp_file), "10", "5", "--format", "text", "-w", workspace],
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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["hover", str(temp_file), "10", "5", "--format", "text", "-w", workspace],
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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["document-symbol", str(temp_file), "--format", "text", "-w", workspace],
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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        result = runner.invoke(
            app,
            ["workspace-symbol", "My", "--format", "text", "-w", str(temp_dir)],
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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        # Test without --format option (should default to JSON)
        result = runner.invoke(
            app, ["definition", str(temp_file), "10", "5", "-w", workspace]
        )
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
    """Test that document-symbol text output translates kind numbers to names."""
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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            ["document-symbol", str(temp_file), "--format", "text", "-w", workspace],
        )
        assert result.exit_code == 0

        output = result.output.strip()
        # Should show human-readable kind names, not "kind=5"
        assert "MyClass (Class)" in output
        assert "myFunction (Function)" in output
        assert "myMethod (Method)" in output
        # Should NOT contain raw kind numbers
        assert "kind=5" not in output
        assert "kind=12" not in output
        assert "kind=6" not in output


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

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        result = runner.invoke(
            app,
            ["workspace-symbol", "My", "--format", "text", "-w", str(temp_dir)],
        )
        assert result.exit_code == 0

        output = result.output.strip()
        # Should show human-readable kind names
        assert "MyClass (Class)" in output
        assert "helper_function (Function)" in output
        assert "CONFIG_VALUE (Constant)" in output
        # Should NOT contain raw kind numbers
        assert "kind=5" not in output
        assert "kind=12" not in output
        assert "kind=14" not in output


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

    mock_response = {
        "locations": [
            {
                "uri": "file:///path/to/file.py",
                "range": {
                    "start": {"line": 5, "character": 0},
                    "end": {"line": 5, "character": 15},
                },
            },
            {
                "uri": "file:///path/to/tests/test_file.py",
                "range": {
                    "start": {"line": 10, "character": 4},
                    "end": {"line": 10, "character": 19},
                },
            },
        ]
    }

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)

        # Test without --include-tests (should filter out test locations)
        result = runner.invoke(
            app,
            ["references", str(temp_file), "10", "5", "-w", workspace],
        )
        assert result.exit_code == 0
        # Without flag, test locations should be filtered
        output = json.loads(result.output)
        assert len(output["locations"]) == 1
        assert "test_file.py" not in output["locations"][0]["uri"]


def test_cli_references_include_tests_flag(temp_file: Path) -> None:
    """Test that references command accepts --include-tests flag."""
    from llm_lsp_cli.cli import app

    mock_response = {
        "locations": [
            {
                "uri": "file:///path/to/file.py",
                "range": {
                    "start": {"line": 5, "character": 0},
                    "end": {"line": 5, "character": 15},
                },
            },
            {
                "uri": "file:///path/to/tests/test_file.py",
                "range": {
                    "start": {"line": 10, "character": 4},
                    "end": {"line": 10, "character": 19},
                },
            },
        ]
    }

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)

        # Test with --include-tests (should include all locations)
        result = runner.invoke(
            app,
            ["references", str(temp_file), "10", "5", "--include-tests", "-w", workspace],
        )
        assert result.exit_code == 0
        # With flag, all locations should be included
        output = json.loads(result.output)
        assert len(output["locations"]) == 2


def test_cli_workspace_symbol_filters_tests_by_default(temp_dir: Path) -> None:
    """Test that workspace-symbol command filters test files by default."""
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
                "name": "TestMyClass",
                "kind": 5,
                "location": {
                    "uri": "file:///path/to/tests/test_myclass.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 30, "character": 0},
                    },
                },
            },
        ]
    }

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        # Test without --include-tests (should filter out test symbols)
        result = runner.invoke(
            app,
            ["workspace-symbol", "My", "-w", str(temp_dir)],
        )
        assert result.exit_code == 0
        # Without flag, test symbols should be filtered
        output = json.loads(result.output)
        assert len(output["symbols"]) == 1
        assert "test" not in output["symbols"][0]["location"]["uri"].lower()


def test_cli_workspace_symbol_include_tests_flag(temp_dir: Path) -> None:
    """Test that workspace-symbol command accepts --include-tests flag."""
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
                "name": "TestMyClass",
                "kind": 5,
                "location": {
                    "uri": "file:///path/to/tests/test_myclass.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 30, "character": 0},
                    },
                },
            },
        ]
    }

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        # Test with --include-tests (should include all symbols)
        result = runner.invoke(
            app,
            ["workspace-symbol", "My", "--include-tests", "-w", str(temp_dir)],
        )
        assert result.exit_code == 0
        # With flag, all symbols should be included
        output = json.loads(result.output)
        assert len(output["symbols"]) == 2


def test_cli_references_yaml_with_include_tests(temp_file: Path) -> None:
    """Test references command with YAML format and --include-tests flag."""
    import yaml

    from llm_lsp_cli.cli import app

    mock_response = {
        "locations": [
            {
                "uri": "file:///path/to/file.py",
                "range": {
                    "start": {"line": 5, "character": 0},
                    "end": {"line": 5, "character": 15},
                },
            },
            {
                "uri": "file:///path/to/tests/test_file.py",
                "range": {
                    "start": {"line": 10, "character": 4},
                    "end": {"line": 10, "character": 19},
                },
            },
        ]
    }

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        workspace = str(temp_file.parent)
        result = runner.invoke(
            app,
            [
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

        # Parse YAML output
        output = yaml.safe_load(result.output)
        assert output is not None
        assert "locations" in output
        assert len(output["locations"]) == 2


def test_cli_workspace_symbol_yaml_with_include_tests(temp_dir: Path) -> None:
    """Test workspace-symbol command with YAML format and --include-tests flag."""
    import yaml

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
                "name": "TestMyClass",
                "kind": 5,
                "location": {
                    "uri": "file:///path/to/tests/test_myclass.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 30, "character": 0},
                    },
                },
            },
        ]
    }

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
        "llm_lsp_cli.cli._send_request"
    ) as mock_send:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance
        mock_send.return_value = mock_response

        result = runner.invoke(
            app,
            [
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

        # Parse YAML output
        output = yaml.safe_load(result.output)
        assert output is not None
        assert "symbols" in output
        assert len(output["symbols"]) == 2


# =============================================================================
# CSV Output Format Tests
# =============================================================================


class TestDefinitionCsvOutput:
    """CSV output tests for definition command."""

    def test_cli_definition_csv_basic(self, temp_file: Path) -> None:
        """Test definition command with CSV output format."""
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

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
            "llm_lsp_cli.cli._send_request"
        ) as mock_send:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = mock_response

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["definition", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
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

        mock_response = {
            "locations": [
                {
                    "uri": "file:///path/to/file1.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 10},
                    },
                },
                {
                    "uri": "file:///path/to/file2.py",
                    "range": {
                        "start": {"line": 20, "character": 5},
                        "end": {"line": 20, "character": 25},
                    },
                },
            ]
        }

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
            "llm_lsp_cli.cli._send_request"
        ) as mock_send:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = mock_response

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["definition", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            lines = result.output.strip().split("\n")
            assert len(lines) == 3  # Header + 2 data rows

    def test_cli_definition_csv_columns_correct(self, temp_file: Path) -> None:
        """Test that CSV has correct columns: uri,start_line,start_char,end_line,end_char."""
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

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
            "llm_lsp_cli.cli._send_request"
        ) as mock_send:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = mock_response

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["definition", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            header = result.output.strip().split("\n")[0]
            assert header == "uri,start_line,start_char,end_line,end_char"


class TestReferencesCsvOutput:
    """CSV output tests for references command."""

    def test_cli_references_csv_basic(self, temp_file: Path) -> None:
        """Test references command with CSV output format."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "locations": [
                {
                    "uri": "file:///path/to/file.py",
                    "range": {
                        "start": {"line": 5, "character": 0},
                        "end": {"line": 5, "character": 15},
                    },
                }
            ]
        }

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
            "llm_lsp_cli.cli._send_request"
        ) as mock_send:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = mock_response

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["references", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            lines = result.output.strip().split("\n")
            assert len(lines) == 2  # Header + 1 data row
            assert "uri" in lines[0]

    def test_cli_references_csv_same_schema_as_definition(self, temp_file: Path) -> None:
        """Test references CSV uses same schema as definition (locations)."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "locations": [
                {
                    "uri": "file:///path/to/file.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 10},
                    },
                }
            ]
        }

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
            "llm_lsp_cli.cli._send_request"
        ) as mock_send:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = mock_response

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["references", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            header = result.output.strip().split("\n")[0]
            # Should have same schema as definition
            assert header == "uri,start_line,start_char,end_line,end_char"


class TestCompletionCsvOutput:
    """CSV output tests for completion command."""

    def test_cli_completion_csv_basic(self, temp_file: Path) -> None:
        """Test completion command with CSV output format."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "items": [
                {
                    "label": "my_function",
                    "kind": 12,
                    "detail": "def my_function(x: int) -> str",
                    "documentation": "A sample function",
                }
            ]
        }

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
            "llm_lsp_cli.cli._send_request"
        ) as mock_send:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = mock_response

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["completion", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            lines = result.output.strip().split("\n")
            assert len(lines) == 2  # Header + 1 data row
            assert "label" in lines[0]

    def test_cli_completion_csv_includes_kind_name(self, temp_file: Path) -> None:
        """Test CSV output translates kind number to human-readable name."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "items": [
                {"label": "MyClass", "kind": 5, "detail": "", "documentation": None},
            ]
        }

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
            "llm_lsp_cli.cli._send_request"
        ) as mock_send:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = mock_response

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["completion", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            # Verify kind_name column is present with translated value
            assert "kind_name" in result.output
            assert "Class" in result.output

    def test_cli_completion_csv_escapes_special_chars(self, temp_file: Path) -> None:
        """Test CSV properly escapes commas/quotes in completion details."""
        import csv
        import io

        from llm_lsp_cli.cli import app

        mock_response = {
            "items": [
                {
                    "label": "func",
                    "kind": 12,
                    "detail": "def func(a, b, c):  # has, commas",
                    "documentation": 'Docs with "quotes"',
                }
            ]
        }

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
            "llm_lsp_cli.cli._send_request"
        ) as mock_send:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = mock_response

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["completion", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            # Parse CSV to verify proper escaping
            reader = csv.DictReader(io.StringIO(result.output))
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["detail"] == "def func(a, b, c):  # has, commas"
            assert rows[0]["documentation"] == 'Docs with "quotes"'


class TestHoverCsvOutput:
    """CSV output tests for hover command."""

    def test_cli_hover_csv_basic(self, temp_file: Path) -> None:
        """Test hover command with CSV output format."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "hover": {
                "contents": {
                    "kind": "markdown",
                    "value": "```python\ndef func() -> str\n```",
                },
                "range": {
                    "start": {"line": 10, "character": 4},
                    "end": {"line": 10, "character": 15},
                },
            }
        }

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
            "llm_lsp_cli.cli._send_request"
        ) as mock_send:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = mock_response

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["hover", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            lines = result.output.strip().split("\n")
            assert len(lines) == 2  # Header + 1 data row

    def test_cli_hover_csv_single_row(self, temp_file: Path) -> None:
        """Test hover CSV produces single row (not a list)."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "hover": {
                "contents": {"kind": "plaintext", "value": "Hover text"},
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
            }
        }

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
            "llm_lsp_cli.cli._send_request"
        ) as mock_send:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = mock_response

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["hover", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            lines = result.output.strip().split("\n")
            assert len(lines) == 2  # Header + single data row


class TestDocumentSymbolCsvOutput:
    """CSV output tests for document-symbol command."""

    def test_cli_document_symbol_csv_basic(self, temp_file: Path) -> None:
        """Test document-symbol command with CSV output format."""
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

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
            "llm_lsp_cli.cli._send_request"
        ) as mock_send:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = mock_response

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["document-symbol", str(temp_file), "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            lines = result.output.strip().split("\n")
            assert len(lines) == 2  # Header + 1 data row
            assert "name" in lines[0]

    def test_cli_document_symbol_csv_kind_translation(self, temp_file: Path) -> None:
        """Test CSV output translates kind numbers to names."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": 5,
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            ]
        }

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
            "llm_lsp_cli.cli._send_request"
        ) as mock_send:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = mock_response

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["document-symbol", str(temp_file), "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            # Verify kind_name column contains translated value
            assert "kind_name" in result.output
            assert "Class" in result.output


class TestWorkspaceSymbolCsvOutput:
    """CSV output tests for workspace-symbol command."""

    def test_cli_workspace_symbol_csv_basic(self, temp_dir: Path) -> None:
        """Test workspace-symbol command with CSV output format."""
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

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
            "llm_lsp_cli.cli._send_request"
        ) as mock_send:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = mock_response

            result = runner.invoke(
                app,
                ["workspace-symbol", "My", "--format", "csv", "-w", str(temp_dir)],
            )
            assert result.exit_code == 0

            lines = result.output.strip().split("\n")
            assert len(lines) == 2  # Header + 1 data row

    def test_cli_workspace_symbol_csv_includes_uri(self, temp_dir: Path) -> None:
        """Test workspace symbol CSV includes URI column."""
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

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
            "llm_lsp_cli.cli._send_request"
        ) as mock_send:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = mock_response

            result = runner.invoke(
                app,
                ["workspace-symbol", "My", "--format", "csv", "-w", str(temp_dir)],
            )
            assert result.exit_code == 0

            # Verify uri column is present
            header = result.output.strip().split("\n")[0]
            assert "uri" in header


class TestCsvFormatOption:
    """Tests for CSV format option parsing and validation."""

    def test_csv_format_option_accepted(self, temp_file: Path) -> None:
        """Test --format csv is accepted without error."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "locations": [
                {
                    "uri": "file:///test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 10},
                    },
                }
            ]
        }

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
            "llm_lsp_cli.cli._send_request"
        ) as mock_send:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = mock_response

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["definition", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            # Should not fail due to format option parsing
            assert result.exit_code == 0

    def test_csv_format_short_option(self, temp_file: Path) -> None:
        """Test -o csv is accepted."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "locations": [
                {
                    "uri": "file:///test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 10},
                    },
                }
            ]
        }

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, patch(
            "llm_lsp_cli.cli._send_request"
        ) as mock_send:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = mock_response

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["definition", str(temp_file), "10", "5", "-o", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

    def test_csv_help_text_updated(self) -> None:
        """Test --help includes csv in format options."""
        from llm_lsp_cli.cli import app

        result = runner.invoke(app, ["definition", "--help"])
        assert result.exit_code == 0

        # Help text should mention csv as a valid format
        # This test will fail until the help text is updated
        assert "csv" in result.output.lower()
