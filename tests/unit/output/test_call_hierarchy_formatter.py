"""Tests for CompactFormatter call hierarchy transform methods."""

from pathlib import Path

import pytest

from llm_lsp_cli.output.formatter import CallHierarchyRecord, CompactFormatter, Position, Range
from tests.fixtures import (
    CALL_HIERARCHY_INCOMING_RESPONSE,
    CALL_HIERARCHY_OUTGOING_RESPONSE,
)


class TestTransformIncomingCalls:
    """Tests for CompactFormatter.transform_call_hierarchy_incoming method."""

    @pytest.fixture
    def formatter(self, tmp_path: Path) -> CompactFormatter:
        """Create a CompactFormatter for testing."""
        return CompactFormatter(tmp_path)

    def test_transform_incoming_calls_single(self, formatter: CompactFormatter) -> None:
        """Transform single incoming call returns CallHierarchyRecord."""
        calls = CALL_HIERARCHY_INCOMING_RESPONSE["calls"]

        records = formatter.transform_call_hierarchy_incoming(calls)

        assert len(records) == 1
        record = records[0]
        assert record.name == "caller_function"
        assert record.kind == 12
        assert record.kind_name == "Function"

    def test_transform_incoming_calls_multiple(self, formatter: CompactFormatter) -> None:
        """Transform multiple incoming calls returns sorted records."""
        calls = [
            {
                "from": {
                    "name": "func_b",
                    "kind": 12,
                    "uri": "file:///project/src/b.py",
                    "range": {
                        "start": {"line": 5, "character": 0},
                        "end": {"line": 10, "character": 0},
                    },
                    "selectionRange": {
                        "start": {"line": 5, "character": 0},
                        "end": {"line": 5, "character": 6},
                    },
                },
                "fromRanges": [],
            },
            {
                "from": {
                    "name": "func_a",
                    "kind": 12,
                    "uri": "file:///project/src/a.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 5, "character": 0},
                    },
                    "selectionRange": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 6},
                    },
                },
                "fromRanges": [],
            },
        ]

        records = formatter.transform_call_hierarchy_incoming(calls)

        # Should be sorted by file/name
        assert len(records) == 2
        assert records[0].name == "func_a"
        assert records[1].name == "func_b"

    def test_transform_incoming_calls_empty(self, formatter: CompactFormatter) -> None:
        """Transform empty calls returns empty list."""
        records = formatter.transform_call_hierarchy_incoming([])

        assert records == []

    def test_transform_incoming_calls_with_from_ranges(self, formatter: CompactFormatter) -> None:
        """Transform incoming calls with multiple fromRanges."""
        calls = [
            {
                "from": {
                    "name": "caller_func",
                    "kind": 12,
                    "uri": "file:///project/src/caller.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 20, "character": 0},
                    },
                    "selectionRange": {
                        "start": {"line": 0, "character": 4},
                        "end": {"line": 0, "character": 15},
                    },
                },
                "fromRanges": [
                    {
                        "start": {"line": 5, "character": 4},
                        "end": {"line": 5, "character": 15},
                    },
                    {
                        "start": {"line": 10, "character": 8},
                        "end": {"line": 10, "character": 19},
                    },
                ],
            }
        ]

        records = formatter.transform_call_hierarchy_incoming(calls)

        assert len(records) == 1
        assert len(records[0].from_ranges) == 2

    def test_transform_incoming_calls_uri_normalization(self, formatter: CompactFormatter) -> None:
        """Transform converts absolute URI to absolute path."""
        calls = [
            {
                "from": {
                    "name": "caller_func",
                    "kind": 12,
                    "uri": f"file://{formatter.workspace}/src/caller.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 10, "character": 0},
                    },
                    "selectionRange": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 11},
                    },
                },
                "fromRanges": [],
            }
        ]

        records = formatter.transform_call_hierarchy_incoming(calls)

        # URI should be normalized to absolute path
        assert records[0].file == str((formatter.workspace / "src" / "caller.py").resolve())


class TestTransformOutgoingCalls:
    """Tests for CompactFormatter.transform_call_hierarchy_outgoing method."""

    @pytest.fixture
    def formatter(self, tmp_path: Path) -> CompactFormatter:
        """Create a CompactFormatter for testing."""
        return CompactFormatter(tmp_path)

    def test_transform_outgoing_calls_single(self, formatter: CompactFormatter) -> None:
        """Transform single outgoing call returns CallHierarchyRecord."""
        calls = CALL_HIERARCHY_OUTGOING_RESPONSE["calls"]

        records = formatter.transform_call_hierarchy_outgoing(calls)

        assert len(records) == 1
        record = records[0]
        assert record.name == "helper_function"
        assert record.kind == 12
        assert record.kind_name == "Function"

    def test_transform_outgoing_calls_multiple(self, formatter: CompactFormatter) -> None:
        """Transform multiple outgoing calls returns sorted records."""
        calls = [
            {
                "to": {
                    "name": "helper_b",
                    "kind": 12,
                    "uri": "file:///project/src/b.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 5, "character": 0},
                    },
                    "selectionRange": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 8},
                    },
                },
                "fromRanges": [],
            },
            {
                "to": {
                    "name": "helper_a",
                    "kind": 12,
                    "uri": "file:///project/src/a.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 5, "character": 0},
                    },
                    "selectionRange": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 8},
                    },
                },
                "fromRanges": [],
            },
        ]

        records = formatter.transform_call_hierarchy_outgoing(calls)

        # Should be sorted by file/name
        assert len(records) == 2
        assert records[0].name == "helper_a"
        assert records[1].name == "helper_b"

    def test_transform_outgoing_calls_empty(self, formatter: CompactFormatter) -> None:
        """Transform empty calls returns empty list."""
        records = formatter.transform_call_hierarchy_outgoing([])

        assert records == []

    def test_transform_outgoing_calls_with_from_ranges(self, formatter: CompactFormatter) -> None:
        """Transform outgoing calls with multiple fromRanges."""
        calls = [
            {
                "to": {
                    "name": "helper_func",
                    "kind": 12,
                    "uri": "file:///project/src/helper.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 10, "character": 0},
                    },
                    "selectionRange": {
                        "start": {"line": 0, "character": 4},
                        "end": {"line": 0, "character": 15},
                    },
                },
                "fromRanges": [
                    {
                        "start": {"line": 5, "character": 4},
                        "end": {"line": 5, "character": 15},
                    },
                    {
                        "start": {"line": 10, "character": 8},
                        "end": {"line": 10, "character": 19},
                    },
                ],
            }
        ]

        records = formatter.transform_call_hierarchy_outgoing(calls)

        assert len(records) == 1
        assert len(records[0].from_ranges) == 2


class TestCallHierarchyRecord:
    """Tests for CallHierarchyRecord dataclass."""

    def test_call_hierarchy_record_has_required_fields(self) -> None:
        """CallHierarchyRecord must have required fields."""
        rng = Range(start=Position(line=9, character=0), end=Position(line=19, character=0))
        from_rng = Range(start=Position(line=4, character=4), end=Position(line=4, character=15))
        record = CallHierarchyRecord(
            file="src/module.py",
            name="my_function",
            kind=12,
            kind_name="Function",
            range=rng,
            from_ranges=[from_rng],
        )

        assert record.file == "src/module.py"
        assert record.name == "my_function"
        assert record.kind == 12
        assert record.kind_name == "Function"
        assert record.range == rng
        assert record.from_ranges == [from_rng]

    def test_call_hierarchy_record_from_ranges_defaults_to_empty_list(self) -> None:
        """CallHierarchyRecord from_ranges defaults to empty list."""
        rng = Range(start=Position(line=9, character=0), end=Position(line=19, character=0))
        record = CallHierarchyRecord(
            file="src/module.py",
            name="my_function",
            kind=12,
            kind_name="Function",
            range=rng,
        )

        assert record.from_ranges == []
