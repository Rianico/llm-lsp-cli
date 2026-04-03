"""Tests for the CLI interface."""

from unittest.mock import MagicMock, patch

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
    """Test definition command when daemon is not running."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["definition", "test.py", "10", "5"])
        assert result.exit_code == 1
        assert "Daemon is not running" in result.output


def test_cli_definition_file_not_found() -> None:
    """Test definition command when file doesn't exist."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = True
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["definition", "/nonexistent/file.py", "10", "5"])
        assert result.exit_code == 1
        assert "File not found" in result.output


def test_cli_references_daemon_not_running() -> None:
    """Test references command when daemon is not running."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["references", "test.py", "10", "5"])
        assert result.exit_code == 1
        assert "Daemon is not running" in result.output


def test_cli_hover_daemon_not_running() -> None:
    """Test hover command when daemon is not running."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["hover", "test.py", "10", "5"])
        assert result.exit_code == 1
        assert "Daemon is not running" in result.output


def test_cli_document_symbol_daemon_not_running() -> None:
    """Test document-symbol command when daemon is not running."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["document-symbol", "test.py"])
        assert result.exit_code == 1
        assert "Daemon is not running" in result.output


def test_cli_workspace_symbol_daemon_not_running() -> None:
    """Test workspace-symbol command when daemon is not running."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_instance = MagicMock()
        mock_instance.is_running.return_value = False
        mock_manager.return_value = mock_instance

        result = runner.invoke(app, ["workspace-symbol", "MyClass"])
        assert result.exit_code == 1
        assert "Daemon is not running" in result.output
