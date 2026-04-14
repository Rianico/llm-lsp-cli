"""Tests for diagnostic formatting in CompactFormatter."""

import json

from llm_lsp_cli.output.formatter import CompactFormatter, DiagnosticRecord


class TestDiagnosticTransform:
    """Tests for transform_diagnostics method."""

    def test_transform_diagnostics_to_records(self) -> None:
        """Test that LSP diagnostics are transformed to DiagnosticRecord list."""
        formatter = CompactFormatter("/tmp/test")

        diagnostics = [
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

        records = formatter.transform_diagnostics(diagnostics, file_path="/tmp/test/file.py")

        assert isinstance(records, list)
        assert len(records) == 1

        rec = records[0]
        assert isinstance(rec, DiagnosticRecord)
        assert rec.file == "/tmp/test/file.py"
        assert rec.line == 10  # 1-indexed
        assert rec.character == 5  # 1-indexed
        assert rec.severity == 1
        assert rec.severity_name == "Error"
        assert rec.code == "reportGeneralTypeIssues"
        assert rec.source == "Pyright"
        assert "Type" in rec.message


class TestDiagnosticsToText:
    """Tests for diagnostics_to_text method."""

    def test_diagnostics_to_text_format(self) -> None:
        """Test that DiagnosticRecord list is formatted as compact text."""
        formatter = CompactFormatter("/tmp/test")

        records = [
            DiagnosticRecord(
                file="/tmp/test/file.py",
                line=10,
                character=5,
                end_line=10,
                end_character=10,
                severity=1,
                severity_name="Error",
                code="reportGeneralTypeIssues",
                source="Pyright",
                message="Type 'int' is not assignable to type 'str'",
            )
        ]

        text = formatter.diagnostics_to_text(records)

        assert "Error" in text
        assert "Type 'int' is not assignable to type 'str'" in text
        assert "Pyright" in text
        assert "10:5" in text

    def test_diagnostics_to_text_empty(self) -> None:
        """Test that empty diagnostics returns appropriate message."""
        formatter = CompactFormatter("/tmp/test")

        text = formatter.diagnostics_to_text([])

        assert "No diagnostics found" in text


class TestDiagnosticsToJson:
    """Tests for diagnostics_to_json method."""

    def test_diagnostics_to_json_format(self) -> None:
        """Test that DiagnosticRecord list is formatted as JSON."""
        formatter = CompactFormatter("/tmp/test")

        records = [
            DiagnosticRecord(
                file="/tmp/test/file.py",
                line=10,
                character=5,
                end_line=10,
                end_character=10,
                severity=1,
                severity_name="Error",
                code="reportGeneralTypeIssues",
                source="Pyright",
                message="Type error",
            )
        ]

        json_str = formatter.diagnostics_to_json(records)
        data = json.loads(json_str)

        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["file"] == "/tmp/test/file.py"
        assert data[0]["line"] == 10
        assert data[0]["severity"] == 1
        assert data[0]["message"] == "Type error"


class TestDiagnosticsToYaml:
    """Tests for diagnostics_to_yaml method."""

    def test_diagnostics_to_yaml_format(self) -> None:
        """Test that DiagnosticRecord list is formatted as YAML."""
        formatter = CompactFormatter("/tmp/test")

        records = [
            DiagnosticRecord(
                file="/tmp/test/file.py",
                line=10,
                character=5,
                end_line=10,
                end_character=10,
                severity=1,
                severity_name="Error",
                code="test_code",
                source="test",
                message="Test message",
            )
        ]

        yaml_str = formatter.diagnostics_to_yaml(records)

        assert "file:" in yaml_str
        assert "/tmp/test/file.py" in yaml_str
        assert "line: 10" in yaml_str
        assert "message:" in yaml_str


class TestDiagnosticsToCsv:
    """Tests for diagnostics_to_csv method."""

    def test_diagnostics_to_csv_format(self) -> None:
        """Test that DiagnosticRecord list is formatted as CSV."""
        formatter = CompactFormatter("/tmp/test")

        records = [
            DiagnosticRecord(
                file="/tmp/test/file.py",
                line=10,
                character=5,
                end_line=10,
                end_character=10,
                severity=1,
                severity_name="Error",
                code="test_code",
                source="test",
                message="Test message",
            )
        ]

        csv_str = formatter.diagnostics_to_csv(records)

        expected_headers = (
            "file,line,character,end_line,end_character,"
            "severity,severity_name,code,source,message,tags"
        )
        assert expected_headers in csv_str
        assert "/tmp/test/file.py" in csv_str
        assert "10" in csv_str
        assert "Error" in csv_str
