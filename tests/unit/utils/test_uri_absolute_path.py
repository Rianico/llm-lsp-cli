"""Tests for absolute path output behavior (RED phase).

These tests verify that LSP output uses absolute file paths instead of
workspace-relative paths. Tests should FAIL until GREEN phase implementation.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest
import yaml

from llm_lsp_cli.output.dispatcher import OutputDispatcher
from llm_lsp_cli.utils import OutputFormat


# =============================================================================
# RED Phase: URI Utility Rename Tests
# =============================================================================


class TestUriUtilityRename:
    """RED: Tests verifying uri_to_relative_path is renamed to uri_to_absolute_path."""

    def test_uri_to_relative_path_removed(self) -> None:
        """RED: uri_to_relative_path should no longer exist after rename."""
        with pytest.raises(ImportError):
            from llm_lsp_cli.utils.uri import uri_to_relative_path  # noqa: F401

    def test_uri_to_absolute_path_exported(self) -> None:
        """RED: uri_to_absolute_path should be exported."""
        from llm_lsp_cli.utils.uri import uri_to_absolute_path

        assert callable(uri_to_absolute_path)


class TestUriToAbsolutePathBehavior:
    """RED: Tests for uri_to_absolute_path returning absolute paths."""

    def test_file_uri_inside_workspace_returns_absolute(self, tmp_path: Path) -> None:
        """GREEN: File inside workspace returns absolute path, not relative."""
        from llm_lsp_cli.utils.uri import uri_to_absolute_path

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "src").mkdir()
        (workspace / "src" / "main.py").write_text("")

        uri = (workspace / "src" / "main.py").as_uri()
        result = uri_to_absolute_path(uri, workspace)

        assert Path(result).is_absolute()
        assert result == str((workspace / "src" / "main.py").resolve())

    def test_file_uri_outside_workspace_returns_absolute(self, tmp_path: Path) -> None:
        """GREEN: File outside workspace returns absolute path."""
        from llm_lsp_cli.utils.uri import uri_to_absolute_path

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        other = tmp_path / "other"
        other.mkdir()
        (other / "external.py").write_text("")

        uri = (other / "external.py").as_uri()
        result = uri_to_absolute_path(uri, workspace)

        assert Path(result).is_absolute()
        assert result == str((other / "external.py").resolve())

    def test_non_file_uri_returns_unchanged(self, tmp_path: Path) -> None:
        """GREEN: Non-file URIs returned as-is."""
        from llm_lsp_cli.utils.uri import uri_to_absolute_path

        uri = "https://example.com/file.py"
        result = uri_to_absolute_path(uri, tmp_path)

        assert result == "https://example.com/file.py"

    def test_uri_with_encoded_characters_decoded(self, tmp_path: Path) -> None:
        """GREEN: URL-encoded characters are decoded."""
        from llm_lsp_cli.utils.uri import uri_to_absolute_path

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        file_path = workspace / "file with spaces.py"
        file_path.write_text("")

        uri = file_path.as_uri()  # Encodes spaces as %20
        result = uri_to_absolute_path(uri, workspace)

        assert "file with spaces.py" in result
        assert "%20" not in result

    def test_empty_uri_returns_empty(self) -> None:
        """GREEN: Empty URI returns empty string."""
        from llm_lsp_cli.utils.uri import uri_to_absolute_path

        result = uri_to_absolute_path("", Path("/workspace"))
        assert result == ""

    def test_malformed_file_uri_returns_cwd(self) -> None:
        """GREEN: Malformed file:// URI (no path component) returns resolved cwd.

        Note: urlparse("file://").path == "", and Path("").resolve() returns
        the current working directory. This is acceptable edge case behavior.
        """
        from llm_lsp_cli.utils.uri import uri_to_absolute_path

        result = uri_to_absolute_path("file://", Path("/workspace"))
        # Path("").resolve() returns cwd, so result is an absolute path
        assert Path(result).is_absolute()


# =============================================================================
# RED Phase: Path Resolver Rename Tests
# =============================================================================


class TestPathResolverRename:
    """RED: Tests verifying path resolver functions are renamed."""

    def test_normalize_uri_to_relative_removed(self) -> None:
        """RED: normalize_uri_to_relative should no longer exist."""
        with pytest.raises(ImportError):
            from llm_lsp_cli.output.path_resolver import normalize_uri_to_relative  # noqa: F401

    def test_resolve_path_for_header_removed(self) -> None:
        """RED: resolve_path_for_header should no longer exist."""
        with pytest.raises(ImportError):
            from llm_lsp_cli.output.path_resolver import resolve_path_for_header  # noqa: F401

    def test_normalize_uri_to_absolute_exported(self) -> None:
        """RED: normalize_uri_to_absolute should be exported."""
        from llm_lsp_cli.output.path_resolver import normalize_uri_to_absolute

        assert callable(normalize_uri_to_absolute)

    def test_resolve_path_for_header_absolute_exported(self) -> None:
        """RED: resolve_path_for_header_absolute should be exported."""
        from llm_lsp_cli.output.path_resolver import resolve_path_for_header_absolute

        assert callable(resolve_path_for_header_absolute)


class TestNormalizeUriToAbsoluteBehavior:
    """RED: Tests for normalize_uri_to_absolute returning absolute paths."""

    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        """Create a fake workspace root."""
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        return tmp_path

    def test_file_uri_inside_workspace_returns_absolute(
        self, workspace_root: Path
    ) -> None:
        """GREEN: File inside workspace returns absolute path, not relative."""
        from llm_lsp_cli.output.path_resolver import normalize_uri_to_absolute

        uri = f"file://{workspace_root}/src/utils.py"
        result = normalize_uri_to_absolute(uri, workspace_root)

        assert Path(result).is_absolute()
        assert result == str(workspace_root / "src" / "utils.py")

    def test_file_uri_outside_workspace_returns_absolute(
        self, workspace_root: Path
    ) -> None:
        """GREEN: File outside workspace returns absolute path (not basename)."""
        from llm_lsp_cli.output.path_resolver import normalize_uri_to_absolute

        uri = "file:///other/file.py"
        result = normalize_uri_to_absolute(uri, workspace_root)

        assert result == "/other/file.py"
        assert not result.startswith("file://")

    def test_non_file_uri_returns_unchanged(self, workspace_root: Path) -> None:
        """GREEN: Non-file URIs returned unchanged."""
        from llm_lsp_cli.output.path_resolver import normalize_uri_to_absolute

        uri = "https://example.com/file.py"
        result = normalize_uri_to_absolute(uri, workspace_root)

        assert result == "https://example.com/file.py"

    def test_empty_uri_returns_empty(self, workspace_root: Path) -> None:
        """GREEN: Empty URI returns empty string."""
        from llm_lsp_cli.output.path_resolver import normalize_uri_to_absolute

        result = normalize_uri_to_absolute("", workspace_root)
        assert result == ""

    def test_resolve_path_for_header_absolute_returns_absolute(
        self, workspace_root: Path
    ) -> None:
        """GREEN: Header path resolution returns absolute path."""
        from llm_lsp_cli.output.path_resolver import resolve_path_for_header_absolute

        file_path = workspace_root / "src" / "main.py"
        result = resolve_path_for_header_absolute(str(file_path), workspace_root)

        assert Path(result).is_absolute()
        assert result == str(file_path.resolve())

    def test_resolve_path_for_header_absolute_handles_uri(
        self, workspace_root: Path
    ) -> None:
        """GREEN: Header path resolution handles file:// URIs."""
        from llm_lsp_cli.output.path_resolver import resolve_path_for_header_absolute

        uri = f"file://{workspace_root}/src/main.py"
        result = resolve_path_for_header_absolute(uri, workspace_root)

        assert Path(result).is_absolute()
        assert "file://" not in result


# =============================================================================
# RED Phase: Formatter Output Tests
# =============================================================================


class TestFormatterOutputAbsolutePaths:
    """RED: Tests verifying formatter output uses absolute paths."""

    def test_transform_symbols_produces_absolute_paths(self, tmp_path: Path) -> None:
        """RED: transform_symbols should produce absolute file paths."""
        from llm_lsp_cli.output.formatter import CompactFormatter

        formatter = CompactFormatter(str(tmp_path))
        symbols = [
            {
                "name": "MyClass",
                "kind": 5,
                "location": {
                    "uri": f"file://{tmp_path}/src/models.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 10, "character": 0},
                    },
                },
            }
        ]
        (tmp_path / "src").mkdir()
        records = formatter.transform_symbols(symbols)

        # Currently returns "src/models.py" (relative)
        # Should return absolute path
        assert records[0].file.startswith("/")
        assert tmp_path.name in records[0].file

    def test_transform_locations_produces_absolute_paths(self, tmp_path: Path) -> None:
        """RED: transform_locations should produce absolute file paths."""
        from llm_lsp_cli.output.formatter import CompactFormatter

        formatter = CompactFormatter(str(tmp_path))
        locations = [
            {
                "uri": f"file://{tmp_path}/src/main.py",
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 10, "character": 0},
                },
            }
        ]
        (tmp_path / "src").mkdir()
        records = formatter.transform_locations(locations)

        assert records[0].file.startswith("/")
        assert tmp_path.name in records[0].file

    def test_json_output_contains_absolute_paths(self, tmp_path: Path) -> None:
        """GREEN: JSON output should contain absolute file paths at top level."""
        from llm_lsp_cli.output.formatter import CompactFormatter

        formatter = CompactFormatter(str(tmp_path))
        symbols = [
            {
                "name": "TestClass",
                "kind": 5,
                "location": {
                    "uri": f"file://{tmp_path}/src/test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            }
        ]
        (tmp_path / "src").mkdir()
        records = formatter.transform_symbols(symbols)
        # Pass file_path to get it at top level
        file_path = str(tmp_path / "src" / "test.py")
        result = OutputDispatcher().format_list(records, OutputFormat.JSON, file_path=file_path)
        parsed = json.loads(result)

        # File path is at top level in JSON output
        assert parsed["file"] == file_path
        assert parsed["file"].startswith("/")

    def test_yaml_output_contains_absolute_paths(self, tmp_path: Path) -> None:
        """GREEN: YAML output should contain absolute file paths at top level."""
        from llm_lsp_cli.output.formatter import CompactFormatter

        formatter = CompactFormatter(str(tmp_path))
        symbols = [
            {
                "name": "TestClass",
                "kind": 5,
                "location": {
                    "uri": f"file://{tmp_path}/src/test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            }
        ]
        (tmp_path / "src").mkdir()
        records = formatter.transform_symbols(symbols)
        # Pass file_path to get it at top level
        file_path = str(tmp_path / "src" / "test.py")
        result = OutputDispatcher().format_list(records, OutputFormat.YAML, file_path=file_path)
        parsed = yaml.safe_load(result)

        # File path is at top level in YAML output
        assert parsed["file"] == file_path
        assert parsed["file"].startswith("/")

    def test_csv_output_contains_absolute_paths(self, tmp_path: Path) -> None:
        """RED: CSV output should contain absolute file paths."""
        from llm_lsp_cli.output.formatter import CompactFormatter

        formatter = CompactFormatter(str(tmp_path))
        symbols = [
            {
                "name": "TestClass",
                "kind": 5,
                "location": {
                    "uri": f"file://{tmp_path}/src/test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            }
        ]
        (tmp_path / "src").mkdir()
        records = formatter.transform_symbols(symbols)
        result = OutputDispatcher().format_list(records, OutputFormat.CSV)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert rows[0]["file"].startswith("/")

    def test_text_output_contains_absolute_paths(self, tmp_path: Path) -> None:
        """GREEN: TEXT output for locations should contain absolute file paths."""
        from llm_lsp_cli.output.formatter import CompactFormatter

        formatter = CompactFormatter(str(tmp_path))
        # Use locations which have "file: range" format in TEXT
        locations = [
            {
                "uri": f"file://{tmp_path}/src/test.py",
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 1, "character": 0},
                },
            }
        ]
        (tmp_path / "src").mkdir()
        records = formatter.transform_locations(locations)
        result = OutputDispatcher().format_list(records, OutputFormat.TEXT)

        # TEXT format for locations is "file: range"
        assert str(tmp_path / "src" / "test.py") in result


# =============================================================================
# RED Phase: Call Hierarchy Output Tests
# =============================================================================


class TestCallHierarchyAbsolutePaths:
    """RED: Tests verifying call hierarchy output uses absolute paths."""

    def test_incoming_calls_have_absolute_paths(self, tmp_path: Path) -> None:
        """RED/GRN: Incoming call hierarchy should have absolute file paths."""
        from llm_lsp_cli.output.formatter import CompactFormatter

        formatter = CompactFormatter(str(tmp_path))
        calls = [
            {
                "from": {
                    "uri": f"file://{tmp_path}/src/caller.py",
                    "name": "caller_func",
                    "kind": 12,
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 10, "character": 0},
                    },
                },
                "fromRanges": [
                    {"start": {"line": 5, "character": 0}, "end": {"line": 5, "character": 20}}
                ],
            }
        ]
        (tmp_path / "src").mkdir()
        records = formatter.transform_call_hierarchy_incoming(calls)

        assert records[0].file.startswith("/")
        assert tmp_path.name in records[0].file

    def test_outgoing_calls_have_absolute_paths(self, tmp_path: Path) -> None:
        """RED/GRN: Outgoing call hierarchy should have absolute file paths."""
        from llm_lsp_cli.output.formatter import CompactFormatter

        formatter = CompactFormatter(str(tmp_path))
        calls = [
            {
                "to": {
                    "uri": f"file://{tmp_path}/src/callee.py",
                    "name": "callee_func",
                    "kind": 12,
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 10, "character": 0},
                    },
                },
                "fromRanges": [
                    {"start": {"line": 5, "character": 0}, "end": {"line": 5, "character": 20}}
                ],
            }
        ]
        (tmp_path / "src").mkdir()
        records = formatter.transform_call_hierarchy_outgoing(calls)

        assert records[0].file.startswith("/")


# =============================================================================
# RED Phase: Diagnostic Output Tests
# =============================================================================


class TestDiagnosticsAbsolutePaths:
    """RED: Tests verifying diagnostic output uses absolute paths."""

    def test_diagnostics_have_absolute_paths(self, tmp_path: Path) -> None:
        """RED/GRN: Diagnostic records should have absolute file paths."""
        from llm_lsp_cli.output.formatter import CompactFormatter

        formatter = CompactFormatter(str(tmp_path))
        diagnostics = [
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
                "severity": 1,
                "message": "Test error",
                "source": "pyright",
            }
        ]
        file_path = str(tmp_path / "src" / "test.py")
        records = formatter.transform_diagnostics(diagnostics, file_path)

        assert records[0].file == file_path
        assert records[0].file.startswith("/")

    def test_workspace_diagnostics_grouped_by_absolute_paths(
        self, tmp_path: Path
    ) -> None:
        """RED/GRN: Workspace diagnostics should group by absolute file paths."""
        from llm_lsp_cli.output.formatter import (
            DiagnosticRecord,
            Position,
            Range,
            group_diagnostics_by_file,
        )

        diagnostics = [
            DiagnosticRecord(
                file=str(tmp_path / "src" / "a.py"),
                range=Range(start=Position(0, 0), end=Position(0, 10)),
                severity=1,
                severity_name="Error",
                code=None,
                source="pyright",
                message="Error in a.py",
            ),
            DiagnosticRecord(
                file=str(tmp_path / "src" / "b.py"),
                range=Range(start=Position(0, 0), end=Position(0, 10)),
                severity=1,
                severity_name="Error",
                code=None,
                source="pyright",
                message="Error in b.py",
            ),
        ]
        grouped = group_diagnostics_by_file(diagnostics)

        files = [g["file"] for g in grouped]
        assert all(f.startswith("/") for f in files)


# =============================================================================
# RED Phase: Grouping Function Tests
# =============================================================================


class TestGroupingAbsolutePaths:
    """RED: Tests verifying grouping functions use absolute paths."""

    def test_group_symbols_by_file_uses_absolute_paths(self, tmp_path: Path) -> None:
        """RED/GRN: Symbol grouping should use absolute file paths."""
        from llm_lsp_cli.output.formatter import (
            Position,
            Range,
            SymbolRecord,
            group_symbols_by_file,
        )

        records = [
            SymbolRecord(
                file=str(tmp_path / "src" / "a.py"),
                name="func_a",
                kind=12,
                kind_name="Function",
                range=Range(start=Position(0, 0), end=Position(10, 0)),
            ),
            SymbolRecord(
                file=str(tmp_path / "src" / "b.py"),
                name="func_b",
                kind=12,
                kind_name="Function",
                range=Range(start=Position(0, 0), end=Position(10, 0)),
            ),
        ]
        grouped = group_symbols_by_file(records)

        files = [g["file"] for g in grouped]
        assert all(f.startswith("/") for f in files)

    def test_group_locations_by_file_uses_absolute_paths(self, tmp_path: Path) -> None:
        """RED/GRN: Location grouping should use absolute file paths."""
        from llm_lsp_cli.output.formatter import (
            LocationRecord,
            Position,
            Range,
            group_locations_by_file,
        )

        records = [
            LocationRecord(
                file=str(tmp_path / "src" / "a.py"),
                range=Range(start=Position(0, 0), end=Position(10, 0)),
            ),
            LocationRecord(
                file=str(tmp_path / "src" / "b.py"),
                range=Range(start=Position(0, 0), end=Position(10, 0)),
            ),
        ]
        grouped = group_locations_by_file(records)

        files = [g["file"] for g in grouped]
        assert all(f.startswith("/") for f in files)
