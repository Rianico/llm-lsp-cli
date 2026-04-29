# Tests for dispatcher _source parameter
"""Tests for _source field in dispatcher output."""

from llm_lsp_cli.output.dispatcher import OutputDispatcher
from llm_lsp_cli.output.protocol import FormattableRecord
from llm_lsp_cli.utils import OutputFormat


class MockRecord(FormattableRecord):
    """Mock record for testing."""

    def __init__(self, name: str, value: int) -> None:
        self._name = name
        self._value = value

    def to_compact_dict(self) -> dict:
        return {"name": self._name, "value": self._value}

    def get_text_line(self) -> str:
        return f"{self._name}: {self._value}"

    def get_csv_headers(self) -> list[str]:
        return ["name", "value"]

    def get_csv_row(self) -> dict:
        return {"name": self._name, "value": self._value}


class TestFormatWithSource:
    """Tests for format() with _source parameter."""

    def test_format_json_with_source(self) -> None:
        """_source at top of JSON single record."""
        record = MockRecord("test", 42)
        dispatcher = OutputDispatcher()
        result = dispatcher.format(
            record, OutputFormat.JSON, _source="Basedpyright: hover of src/main.py"
        )
        import json

        parsed = json.loads(result)
        assert parsed["_source"] == "Basedpyright: hover of src/main.py"
        assert parsed["name"] == "test"
        assert parsed["value"] == 42

    def test_format_yaml_with_source(self) -> None:
        """_source at top of YAML single record."""
        record = MockRecord("test", 42)
        dispatcher = OutputDispatcher()
        result = dispatcher.format(
            record, OutputFormat.YAML, _source="Basedpyright: hover of src/main.py"
        )
        import yaml

        parsed = yaml.safe_load(result)
        assert parsed["_source"] == "Basedpyright: hover of src/main.py"
        assert parsed["name"] == "test"

    def test_format_without_source_unchanged(self) -> None:
        """No _source when param omitted."""
        record = MockRecord("test", 42)
        dispatcher = OutputDispatcher()
        result = dispatcher.format(record, OutputFormat.JSON)
        import json

        parsed = json.loads(result)
        assert "_source" not in parsed
        assert parsed["name"] == "test"

    def test_format_text_ignores_source(self) -> None:
        """TEXT format ignores _source param."""
        record = MockRecord("test", 42)
        dispatcher = OutputDispatcher()
        result = dispatcher.format(
            record, OutputFormat.TEXT, _source="Basedpyright: hover of src/main.py"
        )
        assert result == "test: 42"

    def test_format_csv_ignores_source(self) -> None:
        """CSV format ignores _source param."""
        record = MockRecord("test", 42)
        dispatcher = OutputDispatcher()
        result = dispatcher.format(
            record, OutputFormat.CSV, _source="Basedpyright: hover of src/main.py"
        )
        assert "_source" not in result
        assert "name,value" in result

    def test_source_field_first_in_json(self) -> None:
        """_source appears first in JSON output."""
        record = MockRecord("test", 42)
        dispatcher = OutputDispatcher()
        result = dispatcher.format(
            record, OutputFormat.JSON, _source="Basedpyright: hover of src/main.py"
        )
        import json

        parsed = json.loads(result)
        keys = list(parsed.keys())
        assert keys[0] == "_source"


class TestFormatListWithSource:
    """Tests for format_list() with _source parameter."""

    def test_format_list_json_with_source(self) -> None:
        """_source at top of JSON list output."""
        records = [MockRecord("a", 1), MockRecord("b", 2)]
        dispatcher = OutputDispatcher()
        result = dispatcher.format_list(
            records, OutputFormat.JSON, _source="Basedpyright: definition of src/main.py"
        )
        import json

        parsed = json.loads(result)
        assert parsed["_source"] == "Basedpyright: definition of src/main.py"
        assert "items" in parsed
        assert len(parsed["items"]) == 2

    def test_format_list_yaml_with_source(self) -> None:
        """_source at top of YAML list output."""
        records = [MockRecord("a", 1), MockRecord("b", 2)]
        dispatcher = OutputDispatcher()
        result = dispatcher.format_list(
            records, OutputFormat.YAML, _source="Basedpyright: definition of src/main.py"
        )
        import yaml

        parsed = yaml.safe_load(result)
        assert parsed["_source"] == "Basedpyright: definition of src/main.py"
        assert "items" in parsed

    def test_format_list_without_source_unchanged(self) -> None:
        """No _source when param omitted for list."""
        records = [MockRecord("a", 1), MockRecord("b", 2)]
        dispatcher = OutputDispatcher()
        result = dispatcher.format_list(records, OutputFormat.JSON)
        import json

        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert "_source" not in parsed


class TestFormatGroupedWithSource:
    """Tests for format_grouped() with _source parameter."""

    def test_format_grouped_json_with_source(self) -> None:
        """_source at top of JSON grouped output."""
        grouped_data = [
            {"file": "src/main.py", "symbols": [{"name": "func1"}]},
            {"file": "src/lib.py", "symbols": [{"name": "func2"}]},
        ]
        dispatcher = OutputDispatcher()
        result = dispatcher.format_grouped(
            grouped_data, OutputFormat.JSON, _source="Basedpyright: workspace-symbol"
        )
        import json

        parsed = json.loads(result)
        assert parsed["_source"] == "Basedpyright: workspace-symbol"
        assert "files" in parsed
        assert len(parsed["files"]) == 2

    def test_format_grouped_yaml_with_source(self) -> None:
        """_source at top of YAML grouped output."""
        grouped_data = [
            {"file": "src/main.py", "symbols": [{"name": "func1"}]},
        ]
        dispatcher = OutputDispatcher()
        result = dispatcher.format_grouped(
            grouped_data, OutputFormat.YAML, _source="Basedpyright: workspace-symbol"
        )
        import yaml

        parsed = yaml.safe_load(result)
        assert parsed["_source"] == "Basedpyright: workspace-symbol"
        assert "files" in parsed

    def test_format_grouped_without_source_unchanged(self) -> None:
        """Grouped output always has files key, _source and command optional."""
        grouped_data = [
            {"file": "src/main.py", "symbols": [{"name": "func1"}]},
        ]
        dispatcher = OutputDispatcher()
        result = dispatcher.format_grouped(grouped_data, OutputFormat.JSON)
        import json

        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert "files" in parsed
        assert "_source" not in parsed  # Not provided
        assert "command" not in parsed  # Not provided

    def test_source_field_first_in_yaml(self) -> None:
        """_source appears first in YAML output."""
        grouped_data = [
            {"file": "src/main.py", "symbols": [{"name": "func1"}]},
        ]
        dispatcher = OutputDispatcher()
        result = dispatcher.format_grouped(
            grouped_data, OutputFormat.YAML, _source="Basedpyright: workspace-symbol"
        )
        lines = result.strip().split("\n")
        # First non-empty line should contain _source
        first_key_line = [l for l in lines if l.strip() and not l.strip().startswith("-")][0]
        assert "_source" in first_key_line
