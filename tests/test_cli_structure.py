"""Tests for CLI reorganization: module structure, command hierarchy, hyphenated naming."""

from pathlib import Path

import pytest
from typer.testing import CliRunner


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def runner() -> CliRunner:
    """Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def cli_app():
    """Import and return main CLI app."""
    from llm_lsp_cli.cli import app

    return app


@pytest.fixture
def daemon_app():
    """Import daemon commands app."""
    from llm_lsp_cli.commands.daemon import app

    return app


@pytest.fixture
def lsp_app():
    """Import LSP commands app."""
    from llm_lsp_cli.commands.lsp import app

    return app


@pytest.fixture
def config_app():
    """Import config commands app."""
    from llm_lsp_cli.commands.config import app

    return app


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Create temporary workspace with sample Python file."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "pyproject.toml").touch()
    src = workspace / "src"
    src.mkdir()
    (src / "main.py").write_text("""
def hello():
    return "Hello"

class MyClass:
    def method(self):
        return self
""")
    return workspace


# =============================================================================
# Phase RED-01: Module Structure
# =============================================================================


class TestModuleStructure:
    """Test that the commands/ module structure exists."""

    def test_commands_package_exists(self):
        """Commands package directory exists."""
        commands_path = Path("src/llm_lsp_cli/commands/__init__.py")
        assert commands_path.exists(), f"Expected {commands_path} to exist"

    def test_daemon_module_exists(self):
        """Daemon commands module exists."""
        daemon_path = Path("src/llm_lsp_cli/commands/daemon.py")
        assert daemon_path.exists(), f"Expected {daemon_path} to exist"

    def test_lsp_module_exists(self):
        """LSP commands module exists."""
        lsp_path = Path("src/llm_lsp_cli/commands/lsp.py")
        assert lsp_path.exists(), f"Expected {lsp_path} to exist"

    def test_config_module_exists(self):
        """Config commands module exists."""
        config_path = Path("src/llm_lsp_cli/commands/config.py")
        assert config_path.exists(), f"Expected {config_path} to exist"

    def test_cli_imports_without_error(self):
        """Main CLI module imports successfully."""
        from llm_lsp_cli.cli import app

        assert app is not None

    def test_commands_init_exports_apps(self):
        """Commands __init__.py exports daemon, lsp, config apps."""
        from llm_lsp_cli.commands import daemon, lsp, config

        assert hasattr(daemon, "app"), "daemon.app must be exported"
        assert hasattr(lsp, "app"), "lsp.app must be exported"
        assert hasattr(config, "app"), "config.app must be exported"


# =============================================================================
# Phase RED-02: Daemon Commands
# =============================================================================


class TestDaemonCommands:
    """Test daemon command registration."""

    def test_daemon_start_registered(self, runner, cli_app):
        """daemon start command is registered."""
        result = runner.invoke(cli_app, ["--help"])
        assert result.exit_code == 0
        assert "daemon" in result.output

    def test_daemon_stop_registered(self, runner, cli_app):
        """daemon stop command is registered."""
        result = runner.invoke(cli_app, ["daemon", "--help"])
        assert result.exit_code == 0
        assert "stop" in result.output

    def test_daemon_restart_registered(self, runner, cli_app):
        """daemon restart command is registered."""
        result = runner.invoke(cli_app, ["daemon", "--help"])
        assert result.exit_code == 0
        assert "restart" in result.output

    def test_daemon_status_registered(self, runner, cli_app):
        """daemon status command is registered."""
        result = runner.invoke(cli_app, ["daemon", "--help"])
        assert result.exit_code == 0
        assert "status" in result.output

    def test_daemon_group_help_shows_commands(self, runner, cli_app):
        """daemon --help shows all 4 commands."""
        result = runner.invoke(cli_app, ["daemon", "--help"])
        assert result.exit_code == 0
        assert "start" in result.output
        assert "stop" in result.output
        assert "restart" in result.output
        assert "status" in result.output

    def test_daemon_commands_in_daemon_py(self):
        """Daemon commands are defined in commands/daemon.py."""
        import inspect

        from llm_lsp_cli.commands.daemon import app

        # Get registered commands
        registered = app.registered_commands
        command_names = [cmd.callback.__name__ if cmd.callback else cmd.name for cmd in registered]

        # Check all 4 daemon commands exist
        assert "start" in command_names or any("start" in str(cmd) for cmd in registered)
        assert "stop" in command_names or any("stop" in str(cmd) for cmd in registered)
        assert "restart" in command_names or any("restart" in str(cmd) for cmd in registered)
        assert "status" in command_names or any("status" in str(cmd) for cmd in registered)


# =============================================================================
# Phase RED-03: Config Commands
# =============================================================================


class TestConfigCommands:
    """Test config command registration."""

    def test_config_list_registered(self, runner, cli_app):
        """config list command is registered."""
        result = runner.invoke(cli_app, ["config", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output

    def test_config_init_registered(self, runner, cli_app):
        """config init command is registered."""
        result = runner.invoke(cli_app, ["config", "--help"])
        assert result.exit_code == 0
        assert "init" in result.output

    def test_config_group_help_shows_commands(self, runner, cli_app):
        """config --help shows both commands."""
        result = runner.invoke(cli_app, ["config", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "init" in result.output

    def test_config_commands_in_config_py(self):
        """Config commands are defined in commands/config.py."""
        from llm_lsp_cli.commands.config import app

        registered = app.registered_commands
        command_names = [cmd.name for cmd in registered if cmd.name]

        assert "list" in command_names, f"Expected 'list' in {command_names}"
        assert "init" in command_names, f"Expected 'init' in {command_names}"


# =============================================================================
# Phase RED-04: LSP Commands
# =============================================================================


class TestLSPCommands:
    """Test LSP command registration."""

    def test_lsp_definition_registered(self, runner, cli_app):
        """lsp definition command is registered."""
        result = runner.invoke(cli_app, ["lsp", "--help"])
        assert result.exit_code == 0
        assert "definition" in result.output

    def test_lsp_references_registered(self, runner, cli_app):
        """lsp references command is registered."""
        result = runner.invoke(cli_app, ["lsp", "--help"])
        assert result.exit_code == 0
        assert "references" in result.output

    def test_lsp_document_symbol_registered(self, runner, cli_app):
        """lsp document-symbol command is registered (hyphenated)."""
        result = runner.invoke(cli_app, ["lsp", "document-symbol", "--help"])
        assert result.exit_code == 0

    def test_lsp_workspace_symbol_registered(self, runner, cli_app):
        """lsp workspace-symbol command is registered (hyphenated)."""
        result = runner.invoke(cli_app, ["lsp", "workspace-symbol", "--help"])
        assert result.exit_code == 0

    def test_lsp_incoming_calls_registered(self, runner, cli_app):
        """lsp incoming-calls command is registered (hyphenated)."""
        result = runner.invoke(cli_app, ["lsp", "incoming-calls", "--help"])
        assert result.exit_code == 0

    def test_lsp_outgoing_calls_registered(self, runner, cli_app):
        """lsp outgoing-calls command is registered (hyphenated)."""
        result = runner.invoke(cli_app, ["lsp", "outgoing-calls", "--help"])
        assert result.exit_code == 0

    def test_lsp_completion_registered(self, runner, cli_app):
        """lsp completion command is registered."""
        result = runner.invoke(cli_app, ["lsp", "--help"])
        assert result.exit_code == 0
        assert "completion" in result.output

    def test_lsp_hover_registered(self, runner, cli_app):
        """lsp hover command is registered."""
        result = runner.invoke(cli_app, ["lsp", "--help"])
        assert result.exit_code == 0
        assert "hover" in result.output

    def test_lsp_diagnostics_registered(self, runner, cli_app):
        """lsp diagnostics command is registered."""
        result = runner.invoke(cli_app, ["lsp", "--help"])
        assert result.exit_code == 0
        assert "diagnostics" in result.output

    def test_lsp_workspace_diagnostics_registered(self, runner, cli_app):
        """lsp workspace-diagnostics command is registered (hyphenated)."""
        result = runner.invoke(cli_app, ["lsp", "workspace-diagnostics", "--help"])
        assert result.exit_code == 0

    def test_lsp_rename_registered(self, runner, cli_app):
        """lsp rename command is registered."""
        result = runner.invoke(cli_app, ["lsp", "--help"])
        assert result.exit_code == 0
        assert "rename" in result.output

    def test_lsp_did_change_registered(self, runner, cli_app):
        """lsp did-change command is registered (hyphenated)."""
        result = runner.invoke(cli_app, ["lsp", "did-change", "--help"])
        assert result.exit_code == 0

    def test_lsp_group_help_shows_all_commands(self, runner, cli_app):
        """lsp --help shows all 12 commands."""
        result = runner.invoke(cli_app, ["lsp", "--help"])
        assert result.exit_code == 0
        # Check for all command names (some hyphenated will show in Usage)
        output = result.output
        assert "definition" in output
        assert "references" in output
        assert "document-symbol" in output
        assert "workspace-symbol" in output
        assert "incoming-calls" in output
        assert "outgoing-calls" in output
        assert "completion" in output
        assert "hover" in output
        assert "diagnostics" in output
        assert "workspace-diagnostics" in output
        assert "rename" in output
        assert "did-change" in output

    def test_lsp_commands_in_lsp_py(self):
        """LSP commands are defined in commands/lsp.py."""
        from llm_lsp_cli.commands.lsp import app

        registered = app.registered_commands
        assert len(registered) == 12, f"Expected 12 LSP commands, got {len(registered)}"


# =============================================================================
# Phase RED-05: Hyphenated Naming
# =============================================================================


class TestHyphenatedNaming:
    """Test hyphenated LSP command naming."""

    def test_document_symbol_uses_hyphen(self, runner, cli_app):
        """lsp document-symbol --help works with hyphen."""
        result = runner.invoke(cli_app, ["lsp", "document-symbol", "--help"])
        assert result.exit_code == 0

    def test_workspace_symbol_uses_hyphen(self, runner, cli_app):
        """lsp workspace-symbol --help works with hyphen."""
        result = runner.invoke(cli_app, ["lsp", "workspace-symbol", "--help"])
        assert result.exit_code == 0

    def test_incoming_calls_uses_hyphen(self, runner, cli_app):
        """lsp incoming-calls --help works with hyphen."""
        result = runner.invoke(cli_app, ["lsp", "incoming-calls", "--help"])
        assert result.exit_code == 0

    def test_outgoing_calls_uses_hyphen(self, runner, cli_app):
        """lsp outgoing-calls --help works with hyphen."""
        result = runner.invoke(cli_app, ["lsp", "outgoing-calls", "--help"])
        assert result.exit_code == 0

    def test_workspace_diagnostics_uses_hyphen(self, runner, cli_app):
        """lsp workspace-diagnostics --help works with hyphen."""
        result = runner.invoke(cli_app, ["lsp", "workspace-diagnostics", "--help"])
        assert result.exit_code == 0

    def test_did_change_uses_hyphen(self, runner, cli_app):
        """lsp did-change --help works with hyphen."""
        result = runner.invoke(cli_app, ["lsp", "did-change", "--help"])
        assert result.exit_code == 0

    def test_document_symbol_function_snake_case(self):
        """Function name remains snake_case: document_symbol."""
        import ast
        import inspect

        from llm_lsp_cli.commands.lsp import app

        # Find the document_symbol command callback
        for cmd in app.registered_commands:
            if cmd.name == "document-symbol":
                callback_name = cmd.callback.__name__ if cmd.callback else None
                assert callback_name == "document_symbol", (
                    f"Expected function name 'document_symbol', got '{callback_name}'"
                )
                return

        pytest.fail("document-symbol command not found")

    def test_hyphenated_in_help_output(self, runner, cli_app):
        """Help output shows hyphenated name in Usage."""
        result = runner.invoke(cli_app, ["lsp", "document-symbol", "--help"])
        assert result.exit_code == 0
        # The Usage line should show the hyphenated name
        assert "document-symbol" in result.output


# =============================================================================
# Phase RED-06: LSPConstants Usage
# =============================================================================


class TestLSPConstantsUsage:
    """Test that LSP commands use LSPConstants for method strings."""

    def test_no_hardcoded_text_document_definition(self):
        """No hardcoded 'textDocument/definition' string in lsp.py."""
        lsp_path = Path("src/llm_lsp_cli/commands/lsp.py")
        if not lsp_path.exists():
            pytest.skip("lsp.py does not exist yet")
        content = lsp_path.read_text()
        # Should not have the hardcoded string (but may have the constant reference)
        # We check for the literal string in quotes
        assert '"textDocument/definition"' not in content
        assert "'textDocument/definition'" not in content

    def test_no_hardcoded_text_document_references(self):
        """No hardcoded 'textDocument/references' string in lsp.py."""
        lsp_path = Path("src/llm_lsp_cli/commands/lsp.py")
        if not lsp_path.exists():
            pytest.skip("lsp.py does not exist yet")
        content = lsp_path.read_text()
        assert '"textDocument/references"' not in content
        assert "'textDocument/references'" not in content

    def test_no_hardcoded_document_symbol(self):
        """No hardcoded 'textDocument/documentSymbol' string in lsp.py."""
        lsp_path = Path("src/llm_lsp_cli/commands/lsp.py")
        if not lsp_path.exists():
            pytest.skip("lsp.py does not exist yet")
        content = lsp_path.read_text()
        assert '"textDocument/documentSymbol"' not in content
        assert "'textDocument/documentSymbol'" not in content

    def test_no_hardcoded_workspace_symbol(self):
        """No hardcoded 'workspace/symbol' string in lsp.py."""
        lsp_path = Path("src/llm_lsp_cli/commands/lsp.py")
        if not lsp_path.exists():
            pytest.skip("lsp.py does not exist yet")
        content = lsp_path.read_text()
        assert '"workspace/symbol"' not in content
        assert "'workspace/symbol'" not in content

    def test_no_hardcoded_call_hierarchy_incoming(self):
        """No hardcoded 'callHierarchy/incomingCalls' string in lsp.py."""
        lsp_path = Path("src/llm_lsp_cli/commands/lsp.py")
        if not lsp_path.exists():
            pytest.skip("lsp.py does not exist yet")
        content = lsp_path.read_text()
        assert '"callHierarchy/incomingCalls"' not in content
        assert "'callHierarchy/incomingCalls'" not in content

    def test_no_hardcoded_call_hierarchy_outgoing(self):
        """No hardcoded 'callHierarchy/outgoingCalls' string in lsp.py."""
        lsp_path = Path("src/llm_lsp_cli/commands/lsp.py")
        if not lsp_path.exists():
            pytest.skip("lsp.py does not exist yet")
        content = lsp_path.read_text()
        assert '"callHierarchy/outgoingCalls"' not in content
        assert "'callHierarchy/outgoingCalls'" not in content

    def test_no_hardcoded_completion(self):
        """No hardcoded 'textDocument/completion' string in lsp.py."""
        lsp_path = Path("src/llm_lsp_cli/commands/lsp.py")
        if not lsp_path.exists():
            pytest.skip("lsp.py does not exist yet")
        content = lsp_path.read_text()
        assert '"textDocument/completion"' not in content
        assert "'textDocument/completion'" not in content

    def test_no_hardcoded_hover(self):
        """No hardcoded 'textDocument/hover' string in lsp.py."""
        lsp_path = Path("src/llm_lsp_cli/commands/lsp.py")
        if not lsp_path.exists():
            pytest.skip("lsp.py does not exist yet")
        content = lsp_path.read_text()
        assert '"textDocument/hover"' not in content
        assert "'textDocument/hover'" not in content

    def test_no_hardcoded_diagnostics(self):
        """No hardcoded 'textDocument/diagnostic' string in lsp.py."""
        lsp_path = Path("src/llm_lsp_cli/commands/lsp.py")
        if not lsp_path.exists():
            pytest.skip("lsp.py does not exist yet")
        content = lsp_path.read_text()
        assert '"textDocument/diagnostic"' not in content
        assert "'textDocument/diagnostic'" not in content

    def test_no_hardcoded_workspace_diagnostics(self):
        """No hardcoded 'workspace/diagnostic' string in lsp.py."""
        lsp_path = Path("src/llm_lsp_cli/commands/lsp.py")
        if not lsp_path.exists():
            pytest.skip("lsp.py does not exist yet")
        content = lsp_path.read_text()
        assert '"workspace/diagnostic"' not in content
        assert "'workspace/diagnostic'" not in content

    def test_no_hardcoded_rename(self):
        """No hardcoded 'textDocument/rename' string in lsp.py."""
        lsp_path = Path("src/llm_lsp_cli/commands/lsp.py")
        if not lsp_path.exists():
            pytest.skip("lsp.py does not exist yet")
        content = lsp_path.read_text()
        assert '"textDocument/rename"' not in content
        assert "'textDocument/rename'" not in content

    def test_no_hardcoded_did_change(self):
        """No hardcoded 'textDocument/didChange' string in lsp.py."""
        lsp_path = Path("src/llm_lsp_cli/commands/lsp.py")
        if not lsp_path.exists():
            pytest.skip("lsp.py does not exist yet")
        content = lsp_path.read_text()
        assert '"textDocument/didChange"' not in content
        assert "'textDocument/didChange'" not in content

    def test_lspconstants_imported(self):
        """LSPConstants is imported in commands/lsp.py."""
        lsp_path = Path("src/llm_lsp_cli/commands/lsp.py")
        if not lsp_path.exists():
            pytest.skip("lsp.py does not exist yet")
        content = lsp_path.read_text()
        assert "LSPConstants" in content, "LSPConstants should be imported in lsp.py"


# =============================================================================
# Phase RED-07: Main CLI Refactoring
# =============================================================================


class TestMainCliRefactor:
    """Test that main cli.py is refactored properly."""

    def test_cli_py_size_under_limit(self):
        """cli.py is under 150 lines."""
        cli_path = Path("src/llm_lsp_cli/cli.py")
        assert cli_path.exists(), "cli.py must exist"
        content = cli_path.read_text()
        lines = content.splitlines()
        # Filter out empty lines and comments for a fair count
        non_empty = [l for l in lines if l.strip() and not l.strip().startswith("#")]
        assert len(non_empty) <= 150, f"cli.py has {len(non_empty)} non-empty lines, expected <= 150"

    def test_cli_py_only_app_registration(self):
        """cli.py contains only app registration, no command definitions."""
        cli_path = Path("src/llm_lsp_cli/cli.py")
        assert cli_path.exists(), "cli.py must exist"
        content = cli_path.read_text()
        # Should have add_typer calls
        assert "add_typer" in content, "cli.py should use app.add_typer()"
        # Should NOT have @app.command decorators for LSP commands
        # (version command is allowed to stay)
        assert '@app.command()\ndef definition' not in content
        assert '@app.command()\ndef references' not in content
        assert '@app.command()\ndef document_symbol' not in content

    def test_cli_py_imports_commands(self):
        """cli.py imports daemon, lsp, config from commands."""
        cli_path = Path("src/llm_lsp_cli/cli.py")
        assert cli_path.exists(), "cli.py must exist"
        content = cli_path.read_text()
        assert "from llm_lsp_cli.commands" in content
        assert "daemon" in content
        assert "lsp" in content
        assert "config" in content

    def test_cli_py_registers_subtypers(self):
        """cli.py registers sub-apps with add_typer."""
        cli_path = Path("src/llm_lsp_cli/cli.py")
        assert cli_path.exists(), "cli.py must exist"
        content = cli_path.read_text()
        assert "app.add_typer" in content
        assert 'name="daemon"' in content or "name='daemon'" in content
        assert 'name="lsp"' in content or "name='lsp'" in content
        assert 'name="config"' in content or "name='config'" in content

    def test_cli_py_has_version_command(self):
        """cli.py still has version command."""
        cli_path = Path("src/llm_lsp_cli/cli.py")
        assert cli_path.exists(), "cli.py must exist"
        content = cli_path.read_text()
        assert "version" in content

    def test_root_help_shows_all_groups(self, runner, cli_app):
        """Root --help shows daemon, lsp, config, version."""
        result = runner.invoke(cli_app, ["--help"])
        assert result.exit_code == 0
        output = result.output
        assert "daemon" in output
        assert "lsp" in output
        assert "config" in output
        assert "version" in output


# =============================================================================
# Phase RED-08: Negative Tests (No Backward Compatibility)
# =============================================================================


class TestBackwardCompatibility:
    """Test that old flat commands fail (no backward compatibility)."""

    def test_old_start_fails(self, runner, cli_app):
        """Old 'start' command fails."""
        result = runner.invoke(cli_app, ["start"])
        assert result.exit_code != 0

    def test_old_stop_fails(self, runner, cli_app):
        """Old 'stop' command fails."""
        result = runner.invoke(cli_app, ["stop"])
        assert result.exit_code != 0

    def test_old_restart_fails(self, runner, cli_app):
        """Old 'restart' command fails."""
        result = runner.invoke(cli_app, ["restart"])
        assert result.exit_code != 0

    def test_old_status_fails(self, runner, cli_app):
        """Old 'status' command fails."""
        result = runner.invoke(cli_app, ["status"])
        assert result.exit_code != 0

    def test_old_definition_fails(self, runner, cli_app):
        """Old 'definition' command fails."""
        result = runner.invoke(cli_app, ["definition"])
        assert result.exit_code != 0

    def test_old_references_fails(self, runner, cli_app):
        """Old 'references' command fails."""
        result = runner.invoke(cli_app, ["references"])
        assert result.exit_code != 0

    def test_old_document_symbol_underscore_fails(self, runner, cli_app):
        """Old 'document_symbol' (underscore) command fails."""
        result = runner.invoke(cli_app, ["document_symbol"])
        assert result.exit_code != 0

    def test_old_workspace_symbol_underscore_fails(self, runner, cli_app):
        """Old 'workspace_symbol' (underscore) command fails."""
        result = runner.invoke(cli_app, ["workspace_symbol"])
        assert result.exit_code != 0

    def test_old_incoming_calls_underscore_fails(self, runner, cli_app):
        """Old 'incoming_calls' (underscore) command fails."""
        result = runner.invoke(cli_app, ["incoming_calls"])
        assert result.exit_code != 0

    def test_old_outgoing_calls_underscore_fails(self, runner, cli_app):
        """Old 'outgoing_calls' (underscore) command fails."""
        result = runner.invoke(cli_app, ["outgoing_calls"])
        assert result.exit_code != 0

    def test_old_workspace_diagnostics_underscore_fails(self, runner, cli_app):
        """Old 'workspace_diagnostics' (underscore) command fails."""
        result = runner.invoke(cli_app, ["workspace_diagnostics"])
        assert result.exit_code != 0

    def test_old_did_change_underscore_fails(self, runner, cli_app):
        """Old 'did_change' (underscore) command fails."""
        result = runner.invoke(cli_app, ["did_change"])
        assert result.exit_code != 0

    def test_lsp_group_underscore_variant_fails(self, runner, cli_app):
        """lsp document_symbol (underscore within lsp group) fails."""
        result = runner.invoke(cli_app, ["lsp", "document_symbol"])
        assert result.exit_code != 0


# =============================================================================
# Phase RED-09: Claude Skill Files
# =============================================================================


class TestSkillFiles:
    """Test Claude skill file structure."""

    def test_main_skill_file_exists(self):
        """Main skill file exists."""
        skill_path = Path(".claude/skills/llm-lsp-cli.md")
        assert skill_path.exists(), f"Expected {skill_path} to exist"

    def test_reference_skill_file_exists(self):
        """Reference skill file exists."""
        ref_path = Path(".claude/skills/references/llm-lsp-cli-config.md")
        assert ref_path.exists(), f"Expected {ref_path} to exist"

    def test_main_skill_has_frontmatter(self):
        """Main skill has YAML frontmatter with required fields."""
        skill_path = Path(".claude/skills/llm-lsp-cli.md")
        if not skill_path.exists():
            pytest.skip("Skill file does not exist yet")
        content = skill_path.read_text()
        assert content.startswith("---"), "Skill must start with YAML frontmatter"
        assert "name:" in content
        assert "type:" in content
        assert "description:" in content

    def test_main_skill_type_domain_knowledge(self):
        """Main skill has type: domain-knowledge."""
        skill_path = Path(".claude/skills/llm-lsp-cli.md")
        if not skill_path.exists():
            pytest.skip("Skill file does not exist yet")
        content = skill_path.read_text()
        assert "type: domain-knowledge" in content or "type: 'domain-knowledge'" in content

    def test_main_skill_uses_hyphenated_names(self):
        """Main skill uses hyphenated command names."""
        skill_path = Path(".claude/skills/llm-lsp-cli.md")
        if not skill_path.exists():
            pytest.skip("Skill file does not exist yet")
        content = skill_path.read_text()
        # Should have hyphenated names
        assert "document-symbol" in content
        assert "workspace-symbol" in content
        assert "incoming-calls" in content
        assert "outgoing-calls" in content
        assert "workspace-diagnostics" in content
        assert "did-change" in content

    def test_skill_has_document_symbol_hyphen(self):
        """Skill contains 'document-symbol' (hyphenated)."""
        skill_path = Path(".claude/skills/llm-lsp-cli.md")
        if not skill_path.exists():
            pytest.skip("Skill file does not exist yet")
        content = skill_path.read_text()
        assert "document-symbol" in content

    def test_skill_has_workspace_symbol_hyphen(self):
        """Skill contains 'workspace-symbol' (hyphenated)."""
        skill_path = Path(".claude/skills/llm-lsp-cli.md")
        if not skill_path.exists():
            pytest.skip("Skill file does not exist yet")
        content = skill_path.read_text()
        assert "workspace-symbol" in content

    def test_skill_has_incoming_calls_hyphen(self):
        """Skill contains 'incoming-calls' (hyphenated)."""
        skill_path = Path(".claude/skills/llm-lsp-cli.md")
        if not skill_path.exists():
            pytest.skip("Skill file does not exist yet")
        content = skill_path.read_text()
        assert "incoming-calls" in content

    def test_skill_has_outgoing_calls_hyphen(self):
        """Skill contains 'outgoing-calls' (hyphenated)."""
        skill_path = Path(".claude/skills/llm-lsp-cli.md")
        if not skill_path.exists():
            pytest.skip("Skill file does not exist yet")
        content = skill_path.read_text()
        assert "outgoing-calls" in content

    def test_skill_has_workspace_diagnostics_hyphen(self):
        """Skill contains 'workspace-diagnostics' (hyphenated)."""
        skill_path = Path(".claude/skills/llm-lsp-cli.md")
        if not skill_path.exists():
            pytest.skip("Skill file does not exist yet")
        content = skill_path.read_text()
        assert "workspace-diagnostics" in content

    def test_skill_has_did_change_hyphen(self):
        """Skill contains 'did-change' (hyphenated)."""
        skill_path = Path(".claude/skills/llm-lsp-cli.md")
        if not skill_path.exists():
            pytest.skip("Skill file does not exist yet")
        content = skill_path.read_text()
        assert "did-change" in content

    def test_skill_no_underscore_document_symbol(self):
        """Skill does NOT contain underscore variant 'document_symbol'."""
        skill_path = Path(".claude/skills/llm-lsp-cli.md")
        if not skill_path.exists():
            pytest.skip("Skill file does not exist yet")
        content = skill_path.read_text()
        # Should not have the underscore variant as a command reference
        # (may appear in code blocks as Python function names, but not as CLI commands)
        # Check that it's not in a CLI command context
        import re
        # Look for "lsp document_symbol" as a CLI command pattern
        underscore_cmd_pattern = r"lsp document_symbol"
        assert not re.search(underscore_cmd_pattern, content), \
            "Skill should not reference 'lsp document_symbol' command (use hyphenated)"

    def test_reference_has_daemon_section(self):
        """Reference file has daemon lifecycle content."""
        ref_path = Path(".claude/skills/references/llm-lsp-cli-config.md")
        if not ref_path.exists():
            pytest.skip("Reference file does not exist yet")
        content = ref_path.read_text()
        assert "daemon" in content.lower()


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for CLI reorganization."""

    def test_full_command_path_daemon_start(self, runner, cli_app):
        """daemon start --help works."""
        result = runner.invoke(cli_app, ["daemon", "start", "--help"])
        assert result.exit_code == 0

    def test_full_command_path_lsp_definition(self, runner, cli_app):
        """lsp definition --help works."""
        result = runner.invoke(cli_app, ["lsp", "definition", "--help"])
        assert result.exit_code == 0

    def test_full_command_path_config_list(self, runner, cli_app):
        """config list --help works."""
        result = runner.invoke(cli_app, ["config", "list", "--help"])
        assert result.exit_code == 0

    def test_all_commands_import_correctly(self):
        """All command modules import without error."""
        # This tests that all the refactored modules have valid imports
        from llm_lsp_cli.cli import app
        from llm_lsp_cli.commands.daemon import app as daemon_app
        from llm_lsp_cli.commands.lsp import app as lsp_app
        from llm_lsp_cli.commands.config import app as config_app

        assert app is not None
        assert daemon_app is not None
        assert lsp_app is not None
        assert config_app is not None
