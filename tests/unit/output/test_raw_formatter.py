"""Tests for RawFormatter zero-transformation passthrough behavior."""

import json
from pathlib import Path
from typing import Any

import yaml

from llm_lsp_cli.utils import OutputFormat


class TestRawFormatterExists:
    """Tests for RawFormatter class existence."""

    def test_raw_formatter_importable(self) -> None:
        """RawFormatter class must be importable."""
        from llm_lsp_cli.output.raw_formatter import RawFormatter

        assert RawFormatter is not None

    def test_raw_formatter_init_with_workspace(self, tmp_path: Path) -> None:
        """RawFormatter must be initializable with workspace path."""
        from llm_lsp_cli.output.raw_formatter import RawFormatter

        formatter = RawFormatter(str(tmp_path))
        assert formatter is not None


class TestRawFormatterFormatJson:
    """Tests for RawFormatter.format with JSON output."""

    def test_format_json_returns_identical_json(self, tmp_path: Path) -> None:
        """format with JSON must return identical JSON to input."""
        from llm_lsp_cli.output.raw_formatter import RawFormatter

        formatter = RawFormatter(str(tmp_path))
        lsp_response: dict[str, Any] = {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": 5,
                    "location": {
                        "uri": "file:///project/src/models.py",
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 50, "character": 0},
                        },
                    },
                }
            ]
        }
        result = formatter.format(lsp_response, OutputFormat.JSON)
        parsed = json.loads(result)

        # Must be identical to original response
        assert parsed == lsp_response

    def test_format_json_preserves_all_fields(self, tmp_path: Path) -> None:
        """format with JSON must preserve all LSP fields including data, tags, selectionRange."""
        from llm_lsp_cli.output.raw_formatter import RawFormatter

        formatter = RawFormatter(str(tmp_path))
        lsp_response: dict[str, Any] = {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": 5,
                    "location": {
                        "uri": "file:///project/src/models.py",
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 50, "character": 0},
                        },
                    },
                    "selectionRange": {
                        "start": {"line": 0, "character": 6},
                        "end": {"line": 0, "character": 13},
                    },
                    "tags": [1],
                    "data": {"serverId": "pyright"},
                }
            ]
        }
        result = formatter.format(lsp_response, OutputFormat.JSON)
        parsed = json.loads(result)

        # All fields must be preserved
        assert parsed["symbols"][0]["selectionRange"] is not None
        assert parsed["symbols"][0]["tags"] == [1]
        assert parsed["symbols"][0]["data"] == {"serverId": "pyright"}

    def test_format_json_no_path_normalization(self, tmp_path: Path) -> None:
        """format with JSON must NOT normalize URIs."""
        from llm_lsp_cli.output.raw_formatter import RawFormatter

        formatter = RawFormatter(str(tmp_path))
        lsp_response: dict[str, Any] = {
            "locations": [
                {
                    "uri": "file:///absolute/path/to/file.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                }
            ]
        }
        result = formatter.format(lsp_response, OutputFormat.JSON)
        parsed = json.loads(result)

        # URI must remain unchanged (not normalized to relative)
        assert parsed["locations"][0]["uri"] == "file:///absolute/path/to/file.py"

    def test_format_json_no_filtering(self, tmp_path: Path) -> None:
        """format with JSON must NOT filter test files."""
        from llm_lsp_cli.output.raw_formatter import RawFormatter

        formatter = RawFormatter(str(tmp_path))
        lsp_response: dict[str, Any] = {
            "locations": [
                {
                    "uri": "file:///project/src/file.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
                {
                    "uri": "file:///project/tests/test_file.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            ]
        }
        result = formatter.format(lsp_response, OutputFormat.JSON)
        parsed = json.loads(result)

        # Both locations must be present (test file not filtered)
        assert len(parsed["locations"]) == 2

    def test_format_json_empty_response(self, tmp_path: Path) -> None:
        """format with JSON must handle empty response correctly."""
        from llm_lsp_cli.output.raw_formatter import RawFormatter

        formatter = RawFormatter(str(tmp_path))
        lsp_response: dict[str, Any] = {"locations": []}
        result = formatter.format(lsp_response, OutputFormat.JSON)
        parsed = json.loads(result)

        assert parsed == {"locations": []}

    def test_format_json_null_in_response(self, tmp_path: Path) -> None:
        """format with JSON must preserve null values."""
        from llm_lsp_cli.output.raw_formatter import RawFormatter

        formatter = RawFormatter(str(tmp_path))
        lsp_response: dict[str, Any] = {"locations": None}
        result = formatter.format(lsp_response, OutputFormat.JSON)
        parsed = json.loads(result)

        assert parsed == {"locations": None}


class TestRawFormatterFormatYaml:
    """Tests for RawFormatter.format with YAML output."""

    def test_format_yaml_returns_full_yaml(self, tmp_path: Path) -> None:
        """format with YAML must return full YAML structure."""
        from llm_lsp_cli.output.raw_formatter import RawFormatter

        formatter = RawFormatter(str(tmp_path))
        lsp_response: dict[str, Any] = {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": 5,
                    "location": {
                        "uri": "file:///project/src/models.py",
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 50, "character": 0},
                        },
                    },
                }
            ]
        }
        result = formatter.format(lsp_response, OutputFormat.YAML)
        parsed = yaml.safe_load(result)

        assert parsed == lsp_response

    def test_format_yaml_preserves_unicode(self, tmp_path: Path) -> None:
        """format with YAML must preserve unicode characters."""
        from llm_lsp_cli.output.raw_formatter import RawFormatter

        formatter = RawFormatter(str(tmp_path))
        lsp_response: dict[str, Any] = {
            "symbols": [
                {
                    "name": "alpha_beta_gamma_Class",
                    "kind": 5,
                    "location": {
                        "uri": "file:///project/src/models.py",
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 1, "character": 0},
                        },
                    },
                }
            ]
        }
        result = formatter.format(lsp_response, OutputFormat.YAML)
        parsed = yaml.safe_load(result)
        assert parsed["symbols"][0]["name"] == "alpha_beta_gamma_Class"


class TestRawFormatterFormatText:
    """Tests for RawFormatter.format with TEXT output."""

    def test_format_text_outputs_json(self, tmp_path: Path) -> None:
        """format with TEXT should output JSON for raw LSP response (no standard text format)."""
        from llm_lsp_cli.output.raw_formatter import RawFormatter

        formatter = RawFormatter(str(tmp_path))
        lsp_response: dict[str, Any] = {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": 5,
                }
            ]
        }
        result = formatter.format(lsp_response, OutputFormat.TEXT)

        # For raw mode with text format, output JSON (LSP has no standard text format)
        parsed = json.loads(result)
        assert parsed == lsp_response


class TestRawFormatterFormatCsv:
    """Tests for RawFormatter.format with CSV output."""

    def test_format_csv_outputs_json_or_error(self, tmp_path: Path) -> None:
        """format with CSV should output JSON (CSV not suitable for raw LSP response)."""
        from llm_lsp_cli.output.raw_formatter import RawFormatter

        formatter = RawFormatter(str(tmp_path))
        lsp_response: dict[str, Any] = {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": 5,
                    "location": {
                        "uri": "file:///project/src/models.py",
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 50, "character": 0},
                        },
                    },
                }
            ]
        }
        # For raw mode with CSV, we output JSON passthrough
        result = formatter.format(lsp_response, OutputFormat.CSV)
        parsed = json.loads(result)
        assert parsed == lsp_response


class TestRawFormatterLocationsPassthrough:
    """Tests for RawFormatter locations passthrough."""

    def test_format_json_locations(self, tmp_path: Path) -> None:
        """format with JSON must pass through locations response unchanged."""
        from llm_lsp_cli.output.raw_formatter import RawFormatter

        formatter = RawFormatter(str(tmp_path))
        lsp_response: dict[str, Any] = {
            "locations": [
                {
                    "uri": "file:///project/src/main.py",
                    "range": {
                        "start": {"line": 5, "character": 0},
                        "end": {"line": 5, "character": 20},
                    },
                }
            ]
        }
        result = formatter.format(lsp_response, OutputFormat.JSON)
        parsed = json.loads(result)

        assert parsed == lsp_response


class TestRawFormatterCallHierarchyPassthrough:
    """Tests for RawFormatter call hierarchy passthrough."""

    def test_format_json_incoming_calls(self, tmp_path: Path) -> None:
        """format with JSON must pass through incoming calls response unchanged."""
        from llm_lsp_cli.output.raw_formatter import RawFormatter

        formatter = RawFormatter(str(tmp_path))
        lsp_response: dict[str, Any] = {
            "calls": [
                {
                    "from": {
                        "name": "caller_function",
                        "kind": 12,
                        "uri": "file:///project/src/caller.py",
                        "range": {
                            "start": {"line": 5, "character": 0},
                            "end": {"line": 10, "character": 0},
                        },
                    },
                    "fromRanges": [
                        {
                            "start": {"line": 7, "character": 4},
                            "end": {"line": 7, "character": 19},
                        }
                    ],
                }
            ]
        }
        result = formatter.format(lsp_response, OutputFormat.JSON)
        parsed = json.loads(result)

        assert parsed == lsp_response

    def test_format_json_outgoing_calls(self, tmp_path: Path) -> None:
        """format with JSON must pass through outgoing calls response unchanged."""
        from llm_lsp_cli.output.raw_formatter import RawFormatter

        formatter = RawFormatter(str(tmp_path))
        lsp_response: dict[str, Any] = {
            "calls": [
                {
                    "to": {
                        "name": "helper_function",
                        "kind": 12,
                        "uri": "file:///project/src/helper.py",
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 5, "character": 0},
                        },
                    },
                    "fromRanges": [
                        {
                            "start": {"line": 15, "character": 8},
                            "end": {"line": 15, "character": 23},
                        }
                    ],
                }
            ]
        }
        result = formatter.format(lsp_response, OutputFormat.JSON)
        parsed = json.loads(result)

        assert parsed == lsp_response


class TestRawFormatterDiagnosticsPassthrough:
    """Tests for RawFormatter diagnostics passthrough."""

    def test_format_json_diagnostics(self, tmp_path: Path) -> None:
        """format with JSON must pass through diagnostics response unchanged."""
        from llm_lsp_cli.output.raw_formatter import RawFormatter

        formatter = RawFormatter(str(tmp_path))
        lsp_response: dict[str, Any] = {
            "diagnostics": [
                {
                    "range": {
                        "start": {"line": 9, "character": 4},
                        "end": {"line": 9, "character": 10},
                    },
                    "severity": 1,
                    "code": "reportGeneralTypeIssues",
                    "source": "Pyright",
                    "message": "Type 'int' is not assignable to type 'str'",
                }
            ]
        }
        result = formatter.format(lsp_response, OutputFormat.JSON)
        parsed = json.loads(result)

        assert parsed == lsp_response
