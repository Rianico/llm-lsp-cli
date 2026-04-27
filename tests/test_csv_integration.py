"""Integration tests for CSV output format feature.

This module contains comprehensive integration tests for CSV output including:
- End-to-end CLI tests with --format csv
- Edge cases: empty results, special CSV characters, large result sets
- Integration with different LSP result types
- Integration with --include-tests flag
- Cross-format consistency tests
"""

import csv
import io
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from llm_lsp_cli.cli import app
from tests.fixtures import (
    COMPLETION_RESPONSE,
    COMPLETION_RESPONSE_EMPTY,
    COMPLETION_RESPONSE_WITH_COMMAS,
    DOCUMENT_SYMBOL_RESPONSE,
    HOVER_RESPONSE,
    HOVER_RESPONSE_EMPTY,
    LOCATION_RESPONSE,
    LOCATION_RESPONSE_EMPTY,
    LOCATION_RESPONSE_WITH_COMMAS,
    LOCATION_RESPONSE_WITH_QUOTES,
    WORKSPACE_SYMBOL_RESPONSE,
    create_location_response_with_test_files,
    create_workspace_symbol_response_with_test_files,
)

runner = CliRunner()


# =============================================================================
# Helper Functions
# =============================================================================


def parse_csv_output(output: str) -> list[dict[str, str]]:
    """Parse CLI CSV output into list of dictionaries.

    Args:
        output: Raw CLI output string

    Returns:
        List of row dictionaries
    """
    reader = csv.DictReader(io.StringIO(output.strip()))
    return list(reader)


def get_csv_header(output: str) -> str:
    """Extract header row from CSV output.

    Args:
        output: Raw CLI output string

    Returns:
        Header row string
    """
    return output.strip().split("\n")[0]


# =============================================================================
# End-to-End CLI Tests with CSV Format
# =============================================================================


class TestE2ECsvDefinition:
    """End-to-end CSV tests for definition command."""

    def test_e2e_definition_csv_parses_correctly(self, temp_file: Path) -> None:
        """Test that definition CSV output can be parsed correctly."""
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

            # Parse CSV and verify structure - compact format
            rows = parse_csv_output(result.output)
            assert len(rows) == 1
            # Compact format uses 'file' and 'range' columns
            assert "file" in rows[0]
            assert "range" in rows[0]
            # LSP (10,4)-(10,20) -> compact "11:5-11:21"
            assert rows[0]["range"] == "11:5-11:21"

    def test_e2e_definition_csv_empty_results(self, temp_file: Path) -> None:
        """Test definition CSV with no results returns empty string."""
        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = LOCATION_RESPONSE_EMPTY

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "definition", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0
            # Empty results should produce empty output
            assert result.output.strip() == ""

    def test_e2e_definition_csv_large_result_set(self, temp_file: Path) -> None:
        """Test definition CSV with many locations."""
        # Create 1000 locations
        locations = [
            {
                "uri": f"file:///path/to/file{i}.py",
                "range": {
                    "start": {"line": i * 10, "character": 0},
                    "end": {"line": i * 10, "character": 20},
                },
            }
            for i in range(1000)
        ]
        mock_response = {"locations": locations}

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
                ["lsp", "definition", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            rows = parse_csv_output(result.output)
            assert len(rows) == 1000
            # Verify first and last rows - compact format uses 'file' column
            assert "file" in rows[0]
            assert "range" in rows[0]
            assert "file0.py" in rows[0]["file"]
            assert "file999.py" in rows[999]["file"]


class TestE2ECsvReferences:
    """End-to-end CSV tests for references command."""

    def test_e2e_references_csv_parses_correctly(self, temp_file: Path) -> None:
        """Test that references CSV output parses correctly."""
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

            rows = parse_csv_output(result.output)
            assert len(rows) == 1
            # Compact CSV uses relative paths in 'file' column
            assert rows[0]["file"] == "/path/to/file.py"

    def test_e2e_references_csv_with_test_filtering(self, temp_file: Path) -> None:
        """Test references CSV respects --include-tests flag."""
        workspace = str(temp_file.parent)

        # Without --include-tests, test files should be filtered
        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = create_location_response_with_test_files()

            result = runner.invoke(
                app,
                ["lsp", "references", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0
            rows = parse_csv_output(result.output)
            assert len(rows) == 1
            # Compact CSV uses relative paths in 'file' column
            assert "test_file.py" not in rows[0]["file"]

        # With --include-tests, all files should be included
        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = create_location_response_with_test_files()

            result = runner.invoke(
                app,
                [
                    "lsp",
                    "references",
                    str(temp_file),
                    "10",
                    "5",
                    "--format",
                    "csv",
                    "--include-tests",
                    "-w",
                    workspace,
                ],
            )
            assert result.exit_code == 0
            rows = parse_csv_output(result.output)
            assert len(rows) == 2


class TestE2ECsvCompletion:
    """End-to-end CSV tests for completion command."""

    def test_e2e_completion_csv_parses_correctly(self, temp_file: Path) -> None:
        """Test completion CSV output parses correctly."""
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

            rows = parse_csv_output(result.output)
            # COMPLETION_RESPONSE has 2 items
            assert len(rows) == 2
            assert rows[0]["label"] == "my_function"
            assert rows[0]["kind_name"] == "Function"

    def test_e2e_completion_csv_empty_results(self, temp_file: Path) -> None:
        """Test completion CSV with no results."""
        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = COMPLETION_RESPONSE_EMPTY

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "completion", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0
            assert result.output.strip() == ""


class TestE2ECsvHover:
    """End-to-end CSV tests for hover command."""

    def test_e2e_hover_csv_parses_correctly(self, temp_file: Path) -> None:
        """Test hover CSV output parses correctly."""
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

            rows = parse_csv_output(result.output)
            assert len(rows) == 1
            # HOVER_RESPONSE contains "def my_function" not "def func()"
            assert "def my_function" in rows[0]["content"]

    def test_e2e_hover_csv_no_hover_data(self, temp_file: Path) -> None:
        """Test hover CSV when no hover data available."""
        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = HOVER_RESPONSE_EMPTY

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "hover", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0
            # When hover is None, outputs a message instead of empty
            assert "No hover information available" in result.output


class TestE2ECsvDocumentSymbol:
    """End-to-end CSV tests for document-symbol command."""

    def test_e2e_document_symbol_csv_parses_correctly(self, temp_file: Path) -> None:
        """Test document-symbol CSV output parses correctly."""
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

            rows = parse_csv_output(result.output)
            assert len(rows) == 1
            assert rows[0]["name"] == "MyClass"
            # New schema uses kind_name instead of kind
            assert rows[0]["kind_name"] == "Class"


class TestE2ECsvWorkspaceSymbol:
    """End-to-end CSV tests for workspace-symbol command."""

    def test_e2e_workspace_symbol_csv_parses_correctly(self, temp_dir: Path) -> None:
        """Test workspace-symbol CSV output parses correctly."""
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

            rows = parse_csv_output(result.output)
            # WORKSPACE_SYMBOL_RESPONSE has 2 symbols
            assert len(rows) == 2
            assert rows[0]["name"] == "MyClass"
            # Compact CSV uses relative paths in 'file' column
            assert rows[0]["file"] == "/path/to/myclass.py"

    def test_e2e_workspace_symbol_csv_with_test_filtering(self, temp_dir: Path) -> None:
        """Test workspace-symbol CSV respects --include-tests flag."""
        # Without --include-tests
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
                ["lsp", "workspace-symbol", "My", "--format", "csv", "-w", str(temp_dir)],
            )
            assert result.exit_code == 0
            rows = parse_csv_output(result.output)
            assert len(rows) == 1
            # Compact CSV uses relative paths in 'file' column
            assert "test" not in rows[0]["file"].lower()

        # With --include-tests
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
                    "csv",
                    "--include-tests",
                    "-w",
                    str(temp_dir),
                ],
            )
            assert result.exit_code == 0
            rows = parse_csv_output(result.output)
            assert len(rows) == 2


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestCsvEdgeCasesSpecialCharacters:
    """Edge case tests for special characters in CSV."""

    def test_csv_uri_with_comma(self, temp_file: Path) -> None:
        """Test CSV escaping when file path contains comma."""
        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = LOCATION_RESPONSE_WITH_COMMAS

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "definition", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            rows = parse_csv_output(result.output)
            assert len(rows) == 1
            # Compact format uses 'file' column with relative path
            assert "file" in rows[0]
            assert "file,with,commas.py" in rows[0]["file"]

    def test_csv_uri_with_quotes(self, temp_file: Path) -> None:
        """Test CSV escaping when file path contains double quotes."""
        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = LOCATION_RESPONSE_WITH_QUOTES

            workspace = str(temp_file.parent)
            result = runner.invoke(
                app,
                ["lsp", "definition", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            rows = parse_csv_output(result.output)
            assert len(rows) == 1
            # Compact format uses 'file' column with relative path
            assert "file" in rows[0]
            assert 'file"with"quotes.py' in rows[0]["file"]

    def test_csv_detail_with_comma(self, temp_file: Path) -> None:
        """Test CSV escaping when detail contains comma."""
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

            rows = parse_csv_output(result.output)
            assert len(rows) == 1
            assert rows[0]["detail"] == "def func(a, b, c):  # has, commas"

    def test_csv_documentation_with_quotes(self, temp_file: Path) -> None:
        """Test CSV escaping when documentation contains quotes."""
        mock_response = {
            "items": [
                {
                    "label": "func",
                    "kind": 12,
                    "detail": "A function",
                    "documentation": 'Docs with "quotes" inside',
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
                ["lsp", "completion", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            rows = parse_csv_output(result.output)
            assert len(rows) == 1
            assert rows[0]["documentation"] == 'Docs with "quotes" inside'

    def test_csv_content_with_newline(self, temp_file: Path) -> None:
        """Test CSV escaping when content contains newlines."""
        mock_response = {
            "hover": {
                "contents": {"kind": "plaintext", "value": "Line1\nLine2\nLine3"},
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
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
                ["lsp", "hover", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            rows = parse_csv_output(result.output)
            assert len(rows) == 1
            # Newlines should be escaped in CSV
            assert "\\n" in rows[0]["content"] or "\n" in rows[0]["content"]

    def test_csv_symbol_name_with_special_chars(self, temp_file: Path) -> None:
        """Test CSV handles special characters in symbol names."""
        mock_response = {
            "symbols": [
                {
                    "name": "function_with_underscore_and_123_numbers",
                    "kind": 12,
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
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
                ["lsp", "document-symbol", str(temp_file), "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            rows = parse_csv_output(result.output)
            assert len(rows) == 1
            assert rows[0]["name"] == "function_with_underscore_and_123_numbers"


class TestCsvEdgeCasesEmptyAndNone:
    """Edge case tests for empty and None values."""

    def test_csv_all_commands_empty_results(self, temp_file: Path) -> None:
        """Test all commands return empty CSV for empty results."""
        empty_responses = {
            "definition": {"locations": []},
            "references": {"locations": []},
            "completion": {"items": []},
            "document-symbol": {"symbols": []},
        }

        for command, response in empty_responses.items():
            with (
                patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
                patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
            ):
                mock_instance = MagicMock()
                mock_instance.is_running.return_value = True
                mock_manager.return_value = mock_instance
                mock_send.return_value = response

                workspace = str(temp_file.parent)
                if command == "document-symbol":
                    result = runner.invoke(
                        app,
                        ["lsp", command, str(temp_file), "--format", "csv", "-w", workspace],
                    )
                else:
                    result = runner.invoke(
                        app,
                        ["lsp", command, str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
                    )
                assert result.exit_code == 0
                assert result.output.strip() == ""

    def test_csv_hover_none_hover(self, temp_file: Path) -> None:
        """Test hover CSV returns message for None hover."""
        mock_response = {"hover": None}

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
                ["lsp", "hover", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0
            # When hover is None, outputs a message instead of empty
            assert "No hover information available" in result.output

    def test_csv_missing_optional_fields(self, temp_file: Path) -> None:
        """Test CSV handles missing optional fields gracefully."""
        mock_response = {"items": [{"label": "simple_item", "kind": 1}]}

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
                ["lsp", "completion", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            rows = parse_csv_output(result.output)
            assert len(rows) == 1
            assert rows[0]["label"] == "simple_item"
            # Missing fields should be empty strings
            assert rows[0]["detail"] == ""
            assert rows[0]["documentation"] == ""


class TestCsvEdgeCasesUnicode:
    """Edge case tests for Unicode characters."""

    def test_csv_unicode_in_label(self, temp_file: Path) -> None:
        """Test CSV handles Unicode in labels."""
        mock_response = {
            "items": [
                {
                    "label": "\u03b1\u03b2\u03b3_func",  # Greek letters
                    "kind": 12,
                    "detail": "function",
                    "documentation": "Docs",
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
                ["lsp", "completion", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            rows = parse_csv_output(result.output)
            assert len(rows) == 1
            assert rows[0]["label"] == "\u03b1\u03b2\u03b3_func"

    def test_csv_unicode_in_detail(self, temp_file: Path) -> None:
        """Test CSV handles Unicode in detail."""
        mock_response = {
            "items": [
                {
                    "label": "func",
                    "kind": 12,
                    "detail": "function with \u4e2d\u6587 chars",  # Chinese
                    "documentation": "Docs",
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
                ["lsp", "completion", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            rows = parse_csv_output(result.output)
            assert len(rows) == 1
            assert rows[0]["detail"] == "function with \u4e2d\u6587 chars"

    def test_csv_unicode_in_symbol_name(self, temp_file: Path) -> None:
        """Test CSV handles Unicode in symbol names."""
        mock_response = {
            "symbols": [
                {
                    "name": "\u65e5\u672c\u8a9e_class",  # Japanese
                    "kind": 5,
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
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
                ["lsp", "document-symbol", str(temp_file), "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            rows = parse_csv_output(result.output)
            assert len(rows) == 1
            assert rows[0]["name"] == "\u65e5\u672c\u8a9e_class"


class TestCsvEdgeCasesLargeResultSets:
    """Edge case tests for large result sets."""

    def test_csv_large_completion_set(self, temp_file: Path) -> None:
        """Test CSV with 5000 completion items."""
        items = [
            {
                "label": f"item_{i}",
                "kind": 12,
                "detail": f"Detail for item {i}",
                "documentation": f"Documentation {i}",
            }
            for i in range(5000)
        ]
        mock_response = {"items": items}

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
                ["lsp", "completion", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            rows = parse_csv_output(result.output)
            assert len(rows) == 5000
            assert rows[0]["label"] == "item_0"
            assert rows[4999]["label"] == "item_4999"

    def test_csv_large_symbol_set(self, temp_file: Path) -> None:
        """Test CSV with 2000 document symbols."""
        symbols = [
            {
                "name": f"symbol_{i}",
                "kind": 12,
                "range": {
                    "start": {"line": i, "character": 0},
                    "end": {"line": i + 1, "character": 0},
                },
            }
            for i in range(2000)
        ]
        mock_response = {"symbols": symbols}

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
                ["lsp", "document-symbol", str(temp_file), "--format", "csv", "-w", workspace],
            )
            assert result.exit_code == 0

            rows = parse_csv_output(result.output)
            assert len(rows) == 2000

    def test_csv_large_workspace_symbol_set(self, temp_dir: Path) -> None:
        """Test CSV with 3000 workspace symbols."""
        symbols = [
            {
                "name": f"Symbol_{i}",
                "kind": 5,
                "location": {
                    "uri": f"file:///path/to/file{i}.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            }
            for i in range(3000)
        ]
        mock_response = {"symbols": symbols}

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
                ["lsp", "workspace-symbol", "Symbol", "--format", "csv", "-w", str(temp_dir)],
            )
            assert result.exit_code == 0

            rows = parse_csv_output(result.output)
            assert len(rows) == 3000


# =============================================================================
# Performance Tests
# =============================================================================


class TestCsvPerformance:
    """Performance tests for CSV output."""

    def test_csv_format_performance_definition(self, temp_file: Path) -> None:
        """Test CSV formatting performance for definition with many results."""
        locations = [
            {
                "uri": f"file:///path/to/file{i}.py",
                "range": {
                    "start": {"line": i, "character": 0},
                    "end": {"line": i, "character": 20},
                },
            }
            for i in range(10000)
        ]
        mock_response = {"locations": locations}

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = mock_response

            workspace = str(temp_file.parent)

            start_time = time.perf_counter()
            result = runner.invoke(
                app,
                ["lsp", "definition", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            elapsed = time.perf_counter() - start_time

            assert result.exit_code == 0
            rows = parse_csv_output(result.output)
            assert len(rows) == 10000
            # Should complete in under 2 seconds
            assert elapsed < 2.0, f"CSV formatting took too long: {elapsed:.2f}s"

    def test_csv_format_performance_completions(self, temp_file: Path) -> None:
        """Test CSV formatting performance for completions."""
        items = [
            {
                "label": f"completion_{i}",
                "kind": 12,
                "detail": f"Detail {i}",
                "documentation": f"Doc {i}",
            }
            for i in range(5000)
        ]
        mock_response = {"items": items}

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.commands.lsp.send_request") as mock_send,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance
            mock_send.return_value = mock_response

            workspace = str(temp_file.parent)

            start_time = time.perf_counter()
            result = runner.invoke(
                app,
                ["lsp", "completion", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            elapsed = time.perf_counter() - start_time

            assert result.exit_code == 0
            rows = parse_csv_output(result.output)
            assert len(rows) == 5000
            # Should complete in under 2 seconds
            assert elapsed < 2.0, f"CSV formatting took too long: {elapsed:.2f}s"


# =============================================================================
# Cross-Format Consistency Tests
# =============================================================================


class TestCsvCrossFormatConsistency:
    """Tests to verify CSV output is consistent with other formats."""

    def test_csv_json_same_data_definition(self, temp_file: Path) -> None:
        """Test CSV and JSON contain same data for definition."""
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

        csv_output: str | None = None
        json_output: str | None = None

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
                ["lsp", "definition", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            csv_output = result.output

            result = runner.invoke(
                app,
                ["lsp", "definition", str(temp_file), "10", "5", "--format", "json", "-w", workspace],
            )
            json_output = result.output

        assert csv_output is not None
        assert json_output is not None

        # Parse both and verify same data - compact format
        csv_rows = parse_csv_output(csv_output)
        import json

        json_data = json.loads(json_output)

        # JSON is now a flat list, not {"locations": [...]}
        assert isinstance(json_data, list)
        assert len(csv_rows) == len(json_data)
        # Both CSV and JSON use 'file' and 'range' in compact format
        assert csv_rows[0]["file"] == json_data[0]["file"]
        assert csv_rows[0]["range"] == json_data[0]["range"]

    def test_csv_json_same_data_completions(self, temp_file: Path) -> None:
        """Test CSV and JSON contain same data for completions."""
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

        csv_output: str | None = None
        json_output: str | None = None

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
                ["lsp", "completion", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )
            csv_output = result.output

            result = runner.invoke(
                app,
                ["lsp", "completion", str(temp_file), "10", "5", "--format", "json", "-w", workspace],
            )
            json_output = result.output

        assert csv_output is not None
        assert json_output is not None

        csv_rows = parse_csv_output(csv_output)
        import json

        json_data = json.loads(json_output)

        # JSON is now a flat list, not {"items": [...]}
        assert isinstance(json_data, list)
        assert len(csv_rows) == len(json_data)
        # Both CSV and JSON use 'label' in compact format
        assert csv_rows[0]["label"] == json_data[0]["label"]


# =============================================================================
# CSV Schema Validation Tests
# =============================================================================


class TestCsvSchemaValidation:
    """Tests to validate CSV schema matches expected structure."""

    def test_csv_schema_definition_columns(self, temp_file: Path) -> None:
        """Test definition CSV has correct column schema."""
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
                ["lsp", "definition", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )

            header = get_csv_header(result.output)
            # Compact format uses 'file' and 'range' columns
            expected_columns = ["file", "range"]
            assert header == ",".join(expected_columns)

    def test_csv_schema_references_columns(self, temp_file: Path) -> None:
        """Test references CSV has correct column schema."""
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
                ["lsp", "references", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )

            header = get_csv_header(result.output)
            expected_columns = ["file", "range"]
            assert header == ",".join(expected_columns)

    def test_csv_schema_completion_columns(self, temp_file: Path) -> None:
        """Test completion CSV has correct column schema."""
        mock_response = {
            "items": [
                {"label": "func", "kind": 12, "detail": "A function", "documentation": "Docs"}
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
                ["lsp", "completion", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )

            header = get_csv_header(result.output)
            # Compact format uses file, label, kind_name, detail, documentation, range, position
            expected_columns = ["file", "label", "kind_name", "detail", "documentation", "range", "position"]
            assert header == ",".join(expected_columns)

    def test_csv_schema_document_symbol_columns(self, temp_file: Path) -> None:
        """Test document-symbol CSV has correct column schema."""
        mock_response = {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": 5,
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
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
                ["lsp", "document-symbol", str(temp_file), "--format", "csv", "-w", workspace],
            )

            header = get_csv_header(result.output)
            # New schema: kind_name instead of kind, selection_range and parent added
            expected_columns = ["file", "name", "kind_name", "range", "selection_range", "detail", "tags", "parent"]
            assert header == ",".join(expected_columns)

    def test_csv_schema_workspace_symbol_columns(self, temp_dir: Path) -> None:
        """Test workspace-symbol CSV has correct column schema."""
        mock_response = {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": 5,
                    "location": {
                        "uri": "file:///test.py",
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 1, "character": 0},
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
                ["lsp", "workspace-symbol", "My", "--format", "csv", "-w", str(temp_dir)],
            )

            header = get_csv_header(result.output)
            # New schema: kind_name instead of kind, selection_range and parent added
            expected_columns = ["file", "name", "kind_name", "range", "selection_range", "detail", "tags", "parent"]
            assert header == ",".join(expected_columns)

    def test_csv_schema_hover_columns(self, temp_file: Path) -> None:
        """Test hover CSV has correct column schema."""
        mock_response = {
            "hover": {
                "contents": {"kind": "plaintext", "value": "Hover content"},
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
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
                ["lsp", "hover", str(temp_file), "10", "5", "--format", "csv", "-w", workspace],
            )

            header = get_csv_header(result.output)
            # Compact format uses 'file', 'content', 'range' columns
            expected_columns = ["file", "content", "range"]
            assert header == ",".join(expected_columns)
