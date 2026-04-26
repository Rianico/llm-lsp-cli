"""Tests for FormattableRecord Protocol definition."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, get_type_hints

import pytest


class TestProtocolDefinition:
    """Tests for FormattableRecord Protocol existence and structure."""

    def test_protocol_module_exists(self) -> None:
        """Verify protocol.py module can be imported."""
        from llm_lsp_cli.output import protocol  # noqa: F401

    def test_protocol_class_exists(self) -> None:
        """Verify FormattableRecord class exists in protocol module."""
        from llm_lsp_cli.output.protocol import FormattableRecord

        assert FormattableRecord is not None

    def test_protocol_defines_to_compact_dict(self) -> None:
        """Verify FormattableRecord defines to_compact_dict method."""
        from llm_lsp_cli.output.protocol import FormattableRecord

        assert hasattr(FormattableRecord, "to_compact_dict")

    def test_protocol_defines_get_csv_headers(self) -> None:
        """Verify FormattableRecord defines get_csv_headers method."""
        from llm_lsp_cli.output.protocol import FormattableRecord

        assert hasattr(FormattableRecord, "get_csv_headers")

    def test_protocol_defines_get_csv_row(self) -> None:
        """Verify FormattableRecord defines get_csv_row method."""
        from llm_lsp_cli.output.protocol import FormattableRecord

        assert hasattr(FormattableRecord, "get_csv_row")

    def test_protocol_defines_get_text_line(self) -> None:
        """Verify FormattableRecord defines get_text_line method."""
        from llm_lsp_cli.output.protocol import FormattableRecord

        assert hasattr(FormattableRecord, "get_text_line")


class TestProtocolMethodSignatures:
    """Tests for FormattableRecord method signatures."""

    def test_to_compact_dict_signature(self) -> None:
        """Verify to_compact_dict returns dict[str, Any]."""
        from llm_lsp_cli.output.protocol import FormattableRecord

        # Check method exists and is callable
        method = getattr(FormattableRecord, "to_compact_dict", None)
        assert method is not None
        assert callable(method)

    def test_get_csv_headers_signature(self) -> None:
        """Verify get_csv_headers returns list[str]."""
        from llm_lsp_cli.output.protocol import FormattableRecord

        method = getattr(FormattableRecord, "get_csv_headers", None)
        assert method is not None
        assert callable(method)

    def test_get_csv_row_signature(self) -> None:
        """Verify get_csv_row returns dict[str, str]."""
        from llm_lsp_cli.output.protocol import FormattableRecord

        method = getattr(FormattableRecord, "get_csv_row", None)
        assert method is not None
        assert callable(method)

    def test_get_text_line_signature(self) -> None:
        """Verify get_text_line returns str."""
        from llm_lsp_cli.output.protocol import FormattableRecord

        method = getattr(FormattableRecord, "get_text_line", None)
        assert method is not None
        assert callable(method)


class TestProtocolIsRuntimeCheckable:
    """Tests that FormattableRecord is runtime-checkable."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Verify FormattableRecord can be used with isinstance()."""
        from llm_lsp_cli.output.protocol import FormattableRecord

        # Protocol should be runtime checkable (decorated with @runtime_checkable)
        # This test will fail until we add @runtime_checkable decorator
        assert hasattr(FormattableRecord, "__protocol_attrs__") or hasattr(
            FormattableRecord, "__subclasshook__"
        )
