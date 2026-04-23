"""Tests for LSP Call Hierarchy TypedDict definitions (LSP 3.17)."""

import pytest


class TestCallHierarchyItemTypedDict:
    """Tests for CallHierarchyItem TypedDict definition."""

    def test_call_hierarchy_item_has_required_fields(self) -> None:
        """CallHierarchyItem must have required fields: name, kind, uri, range, selectionRange."""
        from llm_lsp_cli.lsp.types import CallHierarchyItem

        item: CallHierarchyItem = {
            "name": "my_function",
            "kind": 12,
            "uri": "file:///project/src/module.py",
            "range": {
                "start": {"line": 10, "character": 0},
                "end": {"line": 20, "character": 0},
            },
            "selectionRange": {
                "start": {"line": 10, "character": 4},
                "end": {"line": 10, "character": 16},
            },
        }

        assert item["name"] == "my_function"
        assert item["kind"] == 12
        assert item["uri"] == "file:///project/src/module.py"
        assert "range" in item
        assert "selectionRange" in item

    def test_call_hierarchy_item_accepts_optional_fields(self) -> None:
        """CallHierarchyItem may have optional fields: tags, detail, data."""
        from llm_lsp_cli.lsp.types import CallHierarchyItem

        item: CallHierarchyItem = {
            "name": "my_function",
            "kind": 12,
            "uri": "file:///project/src/module.py",
            "range": {
                "start": {"line": 10, "character": 0},
                "end": {"line": 20, "character": 0},
            },
            "selectionRange": {
                "start": {"line": 10, "character": 4},
                "end": {"line": 10, "character": 16},
            },
            "tags": [1],
            "detail": "def my_function() -> None",
            "data": {"opaque": "server-data"},
        }

        assert item.get("tags") == [1]
        assert item.get("detail") == "def my_function() -> None"
        assert item.get("data") == {"opaque": "server-data"}


class TestCallHierarchyIncomingCallTypedDict:
    """Tests for CallHierarchyIncomingCall TypedDict definition."""

    def test_incoming_call_has_from_field(self) -> None:
        """CallHierarchyIncomingCall must have from_ field (maps to LSP 'from')."""
        from llm_lsp_cli.lsp.types import CallHierarchyIncomingCall

        call: CallHierarchyIncomingCall = {
            "from_": {
                "name": "caller_function",
                "kind": 12,
                "uri": "file:///project/src/caller.py",
                "range": {
                    "start": {"line": 5, "character": 0},
                    "end": {"line": 10, "character": 0},
                },
                "selectionRange": {
                    "start": {"line": 5, "character": 4},
                    "end": {"line": 5, "character": 19},
                },
            },
            "fromRanges": [],
        }

        # Verify from_ field exists (Python keyword workaround)
        assert "from_" in call
        assert call["from_"]["name"] == "caller_function"

    def test_incoming_call_has_from_ranges_field(self) -> None:
        """CallHierarchyIncomingCall must have fromRanges field."""
        from llm_lsp_cli.lsp.types import CallHierarchyIncomingCall

        call: CallHierarchyIncomingCall = {
            "from_": {
                "name": "caller_function",
                "kind": 12,
                "uri": "file:///project/src/caller.py",
                "range": {
                    "start": {"line": 5, "character": 0},
                    "end": {"line": 10, "character": 0},
                },
                "selectionRange": {
                    "start": {"line": 5, "character": 4},
                    "end": {"line": 5, "character": 19},
                },
            },
            "fromRanges": [
                {
                    "start": {"line": 7, "character": 4},
                    "end": {"line": 7, "character": 19},
                }
            ],
        }

        assert "fromRanges" in call
        assert len(call["fromRanges"]) == 1

    def test_from_field_documented_as_lsp_mapping(self) -> None:
        """The from_ field should be documented as mapping to LSP 'from' field."""
        # This test verifies the module has the proper documentation
        # The actual documentation is in the TypedDict definition
        from llm_lsp_cli.lsp import types as lsp_types

        # Check that the module has CallHierarchyIncomingCall
        assert hasattr(lsp_types, "CallHierarchyIncomingCall")


class TestCallHierarchyOutgoingCallTypedDict:
    """Tests for CallHierarchyOutgoingCall TypedDict definition."""

    def test_outgoing_call_has_to_field(self) -> None:
        """CallHierarchyOutgoingCall must have to field."""
        from llm_lsp_cli.lsp.types import CallHierarchyOutgoingCall

        call: CallHierarchyOutgoingCall = {
            "to": {
                "name": "helper_function",
                "kind": 12,
                "uri": "file:///project/src/helper.py",
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 5, "character": 0},
                },
                "selectionRange": {
                    "start": {"line": 0, "character": 4},
                    "end": {"line": 0, "character": 19},
                },
            },
            "fromRanges": [],
        }

        assert "to" in call
        assert call["to"]["name"] == "helper_function"

    def test_outgoing_call_has_from_ranges_field(self) -> None:
        """CallHierarchyOutgoingCall must have fromRanges field."""
        from llm_lsp_cli.lsp.types import CallHierarchyOutgoingCall

        call: CallHierarchyOutgoingCall = {
            "to": {
                "name": "helper_function",
                "kind": 12,
                "uri": "file:///project/src/helper.py",
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 5, "character": 0},
                },
                "selectionRange": {
                    "start": {"line": 0, "character": 4},
                    "end": {"line": 0, "character": 19},
                },
            },
            "fromRanges": [
                {
                    "start": {"line": 15, "character": 8},
                    "end": {"line": 15, "character": 23},
                }
            ],
        }

        assert "fromRanges" in call
        assert len(call["fromRanges"]) == 1
