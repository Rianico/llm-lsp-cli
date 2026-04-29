"""Tests for TODO cleanup (Issue 3)."""

from pathlib import Path


class TestTodoCleanup:
    """Verify scattered TODO comments are removed."""

    def test_todo_pattern_absent_from_commands_lsp(self) -> None:
        """Direct file content check for TODO removal."""
        lsp_commands_path = Path("src/llm_lsp_cli/commands/lsp.py")
        content = lsp_commands_path.read_text()

        todo_pattern = "TODO: Pass actual server_info.name from LSPClient"

        assert (
            todo_pattern not in content
        ), f"Found unremoved TODO: {todo_pattern}"

    def test_no_scattered_todos_in_commands_lsp(self) -> None:
        """Verify the specific TODO pattern is removed from commands/lsp.py."""
        import subprocess

        result = subprocess.run(
            ["rg", "TODO: Pass actual server_info.name", "src/llm_lsp_cli/commands/lsp.py"],
            capture_output=True,
            text=True,
            cwd="/Users/zhengxk/development/ai/llm-lsp-cli",
        )

        # Should find no matches (rg returns 1 when no matches found)
        assert result.returncode == 1, "TODO comments should be removed from commands/lsp.py"
        assert result.stdout == ""
