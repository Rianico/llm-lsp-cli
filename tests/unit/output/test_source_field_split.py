"""Tests for split _source field and file field removal."""

import json

import pytest

from llm_lsp_cli.output.dispatcher import OutputDispatcher
from llm_lsp_cli.output.formatter import DiagnosticRecord, Range, SymbolRecord
from llm_lsp_cli.utils import OutputFormat


class TestSourceFieldSplit:
    """Tests for splitting _source into _source (server) and file (path)."""

    def test_format_list_splits_source_for_file_level_command(
        self,
    ) -> None:
        """format_list should split _source into _source (server) and file (path)."""
        dispatcher = OutputDispatcher()
        records = [
            DiagnosticRecord(
                file="src/main.py",
                range=Range.from_dict({"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 5}}),
                severity=1,
                severity_name="Error",
                code="E001",
                source="basedpyright",
                message="Test error",
            )
        ]

        # _source should be "Basedpyright" (server only), file should be separate
        result = dispatcher.format_list(
            records,
            OutputFormat.JSON,
            _source="Basedpyright",
            file_path="src/main.py",
        )
        data = json.loads(result)

        assert data["_source"] == "Basedpyright"
        assert data["file"] == "src/main.py"
        assert "items" in data

    def test_format_list_file_not_in_items(self) -> None:
        """Items should NOT contain file field - it's at the top level."""
        dispatcher = OutputDispatcher()
        records = [
            DiagnosticRecord(
                file="src/main.py",
                range=Range.from_dict({"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 5}}),
                severity=1,
                severity_name="Error",
                code="E001",
                source="basedpyright",
                message="Test error",
            )
        ]

        result = dispatcher.format_list(
            records,
            OutputFormat.JSON,
            _source="Basedpyright",
            file_path="src/main.py",
        )
        data = json.loads(result)

        # Items should NOT have file field
        assert "file" not in data["items"][0]
        assert "range" in data["items"][0]
        assert "severity_name" in data["items"][0]

    def test_format_list_yaml_splits_source(self) -> None:
        """YAML format should also split _source."""
        dispatcher = OutputDispatcher()
        records = [
            SymbolRecord(
                file="src/utils.py",
                name="my_func",
                kind=12,
                kind_name="Function",
                range=Range.from_dict({"start": {"line": 0, "character": 0}, "end": {"line": 5, "character": 0}}),
            )
        ]

        result = dispatcher.format_list(
            records,
            OutputFormat.YAML,
            _source="Basedpyright",
            file_path="src/utils.py",
        )

        assert "_source: Basedpyright" in result
        assert "file: src/utils.py" in result

    def test_format_hover_includes_file_at_top_level(self) -> None:
        """format (single record) should include file at top level for hover."""
        dispatcher = OutputDispatcher()
        record = SymbolRecord(
            file="src/main.py",
            name="MyClass",
            kind=5,
            kind_name="Class",
            range=Range.from_dict({"start": {"line": 0, "character": 0}, "end": {"line": 10, "character": 0}}),
        )

        result = dispatcher.format(
            record,
            OutputFormat.JSON,
            _source="Basedpyright",
            file_path="src/main.py",
        )
        data = json.loads(result)

        assert data["_source"] == "Basedpyright"
        assert data["file"] == "src/main.py"
        # Record fields should NOT have file
        assert "name" in data
        assert "file" not in {k for k in data.keys() if k != "file"} or data.get("file") == "src/main.py"


class TestDiagnosticRecordNoFileInDict:
    """Tests for DiagnosticRecord.to_compact_dict() not including file."""

    def test_diagnostic_to_compact_dict_no_file(self) -> None:
        """DiagnosticRecord.to_compact_dict() should NOT include file field."""
        record = DiagnosticRecord(
            file="src/main.py",
            range=Range.from_dict({"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 5}}),
            severity=1,
            severity_name="Error",
            code="E001",
            source="basedpyright",
            message="Test error",
        )

        result = record.to_compact_dict()

        assert "file" not in result
        assert result["range"] == "1:1-1:6"
        assert result["severity_name"] == "Error"
        assert result["message"] == "Test error"


class TestSymbolRecordNoFileInDict:
    """Tests for SymbolRecord.to_compact_dict() not including file."""

    def test_symbol_to_compact_dict_no_file(self) -> None:
        """SymbolRecord.to_compact_dict() should NOT include file field."""
        record = SymbolRecord(
            file="src/main.py",
            name="my_func",
            kind=12,
            kind_name="Function",
            range=Range.from_dict({"start": {"line": 0, "character": 0}, "end": {"line": 5, "character": 0}}),
        )

        result = record.to_compact_dict()

        assert "file" not in result
        assert result["name"] == "my_func"
        assert result["kind_name"] == "Function"
        assert result["range"] == "1:1-6:1"


class TestWorkspaceCommandsKeepFileInGroups:
    """Tests for workspace-level commands keeping file in groups (not items)."""

    def test_workspace_symbol_keeps_file_in_groups(self) -> None:
        """Workspace-symbol should have file in group, not in items."""
        dispatcher = OutputDispatcher()
        grouped_data = [
            {
                "file": "src/main.py",
                "symbols": [
                    {"name": "my_func", "kind_name": "Function", "range": "1:1-6:1"}
                ]
            }
        ]

        result = dispatcher.format_grouped(
            grouped_data,
            OutputFormat.JSON,
            items_key="symbols",
            _source="Basedpyright",
        )
        data = json.loads(result)

        assert data["_source"] == "Basedpyright"
        assert data["files"][0]["file"] == "src/main.py"
        # Item should NOT have file
        assert "file" not in data["files"][0]["symbols"][0]

    def test_workspace_diagnostics_keeps_file_in_groups(self) -> None:
        """Workspace-diagnostics should have file in group, not in items."""
        dispatcher = OutputDispatcher()
        grouped_data = [
            {
                "file": "src/main.py",
                "diagnostics": [
                    {"range": "1:1-1:6", "severity_name": "Error", "message": "Test"}
                ]
            }
        ]

        result = dispatcher.format_grouped(
            grouped_data,
            OutputFormat.JSON,
            items_key="diagnostics",
            _source="Basedpyright",
        )
        data = json.loads(result)

        assert data["_source"] == "Basedpyright"
        assert data["files"][0]["file"] == "src/main.py"
        # Item should NOT have file
        assert "file" not in data["files"][0]["diagnostics"][0]
