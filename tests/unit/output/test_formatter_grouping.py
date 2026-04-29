"""Tests for file grouping in formatter.py.

This module tests the group_symbols_by_file and group_diagnostics_by_file
functions in output/formatter.py for grouping workspace-level output by file.
"""

from __future__ import annotations

import pytest


class TestGroupSymbolsByFile:
    """Test SymbolRecord grouping for workspace-symbol output."""

    def test_groups_multiple_symbols_same_file(self) -> None:
        """Multiple symbols in same file grouped together."""
        from llm_lsp_cli.output.formatter import (
            Position,
            Range,
            SymbolRecord,
            group_symbols_by_file,
        )

        symbols = [
            SymbolRecord(
                file="src/main.py",
                name="func1",
                kind=12,
                kind_name="Function",
                range=Range(Position(0, 0), Position(5, 0)),
            ),
            SymbolRecord(
                file="src/main.py",
                name="func2",
                kind=12,
                kind_name="Function",
                range=Range(Position(6, 0), Position(10, 0)),
            ),
            SymbolRecord(
                file="src/other.py",
                name="MyClass",
                kind=5,
                kind_name="Class",
                range=Range(Position(0, 0), Position(20, 0)),
            ),
        ]

        result = group_symbols_by_file(symbols)

        assert len(result) == 2
        # Find the main.py group
        main_group = next(g for g in result if g["file"] == "src/main.py")
        assert len(main_group["symbols"]) == 2

        # Find the other.py group
        other_group = next(g for g in result if g["file"] == "src/other.py")
        assert len(other_group["symbols"]) == 1

    def test_groups_sorted_by_file_path(self) -> None:
        """Groups sorted alphabetically by file path."""
        from llm_lsp_cli.output.formatter import (
            Position,
            Range,
            SymbolRecord,
            group_symbols_by_file,
        )

        symbols = [
            SymbolRecord(
                file="z.py",
                name="z_func",
                kind=12,
                kind_name="Function",
                range=Range(Position(0, 0), Position(5, 0)),
            ),
            SymbolRecord(
                file="a.py",
                name="a_func",
                kind=12,
                kind_name="Function",
                range=Range(Position(0, 0), Position(5, 0)),
            ),
            SymbolRecord(
                file="m.py",
                name="m_func",
                kind=12,
                kind_name="Function",
                range=Range(Position(0, 0), Position(5, 0)),
            ),
        ]

        result = group_symbols_by_file(symbols)

        # Verify sorted order
        assert result[0]["file"] == "a.py"
        assert result[1]["file"] == "m.py"
        assert result[2]["file"] == "z.py"

    def test_empty_list_returns_empty_list(self) -> None:
        """Empty input produces empty output."""
        from llm_lsp_cli.output.formatter import group_symbols_by_file

        result = group_symbols_by_file([])
        assert result == []

    def test_single_symbol_single_group(self) -> None:
        """Single symbol produces single group."""
        from llm_lsp_cli.output.formatter import (
            Position,
            Range,
            SymbolRecord,
            group_symbols_by_file,
        )

        symbols = [
            SymbolRecord(
                file="x.py",
                name="func",
                kind=12,
                kind_name="Function",
                range=Range(Position(0, 0), Position(5, 0)),
            ),
        ]

        result = group_symbols_by_file(symbols)

        assert len(result) == 1
        assert result[0]["file"] == "x.py"
        assert len(result[0]["symbols"]) == 1

    def test_symbol_record_converted_to_compact_dict(self) -> None:
        """SymbolRecords converted via to_compact_dict()."""
        from llm_lsp_cli.output.formatter import (
            Position,
            Range,
            SymbolRecord,
            group_symbols_by_file,
        )

        symbols = [
            SymbolRecord(
                file="test.py",
                name="MyFunc",
                kind=12,
                kind_name="Function",
                range=Range(Position(1, 0), Position(5, 0)),
                detail="A test function",
            ),
        ]

        result = group_symbols_by_file(symbols)

        # Each symbol should be a dict from to_compact_dict()
        symbol_dict = result[0]["symbols"][0]
        assert isinstance(symbol_dict, dict)
        assert symbol_dict["name"] == "MyFunc"
        assert symbol_dict["kind_name"] == "Function"

    def test_many_symbols_same_file(self) -> None:
        """Many symbols in single file all grouped."""
        from llm_lsp_cli.output.formatter import (
            Position,
            Range,
            SymbolRecord,
            group_symbols_by_file,
        )

        symbols = [
            SymbolRecord(
                file="large.py",
                name=f"func{i}",
                kind=12,
                kind_name="Function",
                range=Range(Position(i * 10, 0), Position(i * 10 + 5, 0)),
            )
            for i in range(50)
        ]

        result = group_symbols_by_file(symbols)

        assert len(result) == 1
        assert result[0]["file"] == "large.py"
        assert len(result[0]["symbols"]) == 50


class TestGroupDiagnosticsByFile:
    """Test DiagnosticRecord grouping for workspace-diagnostics output."""

    def test_groups_multiple_diagnostics_same_file(self) -> None:
        """Multiple diagnostics in same file grouped together."""
        from llm_lsp_cli.output.formatter import (
            DiagnosticRecord,
            Position,
            Range,
            group_diagnostics_by_file,
        )

        diagnostics = [
            DiagnosticRecord(
                file="src/main.py",
                range=Range(Position(0, 0), Position(0, 10)),
                severity=1,
                severity_name="Error",
                code="E001",
                source="pyright",
                message="Undefined variable",
            ),
            DiagnosticRecord(
                file="src/main.py",
                range=Range(Position(5, 0), Position(5, 5)),
                severity=2,
                severity_name="Warning",
                code="W001",
                source="pyright",
                message="Unused import",
            ),
            DiagnosticRecord(
                file="src/other.py",
                range=Range(Position(2, 0), Position(2, 10)),
                severity=1,
                severity_name="Error",
                code="E002",
                source="pyright",
                message="Type error",
            ),
        ]

        result = group_diagnostics_by_file(diagnostics)

        assert len(result) == 2
        main_group = next(g for g in result if g["file"] == "src/main.py")
        assert len(main_group["diagnostics"]) == 2

    def test_groups_sorted_by_file_path(self) -> None:
        """Groups sorted alphabetically by file path."""
        from llm_lsp_cli.output.formatter import (
            DiagnosticRecord,
            Position,
            Range,
            group_diagnostics_by_file,
        )

        diagnostics = [
            DiagnosticRecord(
                file="z.py",
                range=Range(Position(0, 0), Position(0, 10)),
                severity=1,
                severity_name="Error",
                code="E",
                source="test",
                message="Error",
            ),
            DiagnosticRecord(
                file="a.py",
                range=Range(Position(0, 0), Position(0, 10)),
                severity=1,
                severity_name="Error",
                code="E",
                source="test",
                message="Error",
            ),
        ]

        result = group_diagnostics_by_file(diagnostics)

        assert result[0]["file"] == "a.py"
        assert result[1]["file"] == "z.py"

    def test_empty_list_returns_empty_list(self) -> None:
        """Empty input produces empty output."""
        from llm_lsp_cli.output.formatter import group_diagnostics_by_file

        result = group_diagnostics_by_file([])
        assert result == []

    def test_diagnostic_record_converted_to_compact_dict(self) -> None:
        """DiagnosticRecords converted via to_compact_dict()."""
        from llm_lsp_cli.output.formatter import (
            DiagnosticRecord,
            Position,
            Range,
            group_diagnostics_by_file,
        )

        diagnostics = [
            DiagnosticRecord(
                file="test.py",
                range=Range(Position(1, 0), Position(1, 10)),
                severity=1,
                severity_name="Error",
                code="E001",
                source="pyright",
                message="Test error",
            ),
        ]

        result = group_diagnostics_by_file(diagnostics)

        diag_dict = result[0]["diagnostics"][0]
        assert isinstance(diag_dict, dict)
        assert diag_dict["severity_name"] == "Error"
        assert diag_dict["message"] == "Test error"

    def test_mixed_severity_grouped_together(self) -> None:
        """Different severity diagnostics in same file grouped together."""
        from llm_lsp_cli.output.formatter import (
            DiagnosticRecord,
            Position,
            Range,
            group_diagnostics_by_file,
        )

        diagnostics = [
            DiagnosticRecord(
                file="mixed.py",
                range=Range(Position(0, 0), Position(0, 10)),
                severity=1,
                severity_name="Error",
                code="E",
                source="test",
                message="An error",
            ),
            DiagnosticRecord(
                file="mixed.py",
                range=Range(Position(5, 0), Position(5, 5)),
                severity=2,
                severity_name="Warning",
                code="W",
                source="test",
                message="A warning",
            ),
            DiagnosticRecord(
                file="mixed.py",
                range=Range(Position(10, 0), Position(10, 5)),
                severity=3,
                severity_name="Information",
                code="I",
                source="test",
                message="An info",
            ),
        ]

        result = group_diagnostics_by_file(diagnostics)

        assert len(result) == 1
        assert len(result[0]["diagnostics"]) == 3
