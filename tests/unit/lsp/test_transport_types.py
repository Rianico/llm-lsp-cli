"""Tests that StdioTransport return types enforce object boundary.

These tests verify that StdioTransport.send_request() returns `object` instead of `Any`,
establishing a strict type boundary that forces callers to use TypedLSPTransport.
"""

import inspect
from pathlib import Path
from typing import Any

import pytest

from llm_lsp_cli.lsp.transport import StdioTransport


class TestTransportReturnType:
    """Tests that StdioTransport return types enforce object boundary."""

    def test_send_request_return_type_is_object(self) -> None:
        """T1.1: send_request return annotation is object, not Any."""
        sig = inspect.signature(StdioTransport.send_request)
        return_annotation = sig.return_annotation

        assert return_annotation is object, (
            f"Expected return type 'object', got {return_annotation}"
        )
        assert return_annotation is not Any, (
            "Return type must not be Any (type safety boundary)"
        )

    def test_send_request_params_type_is_object_dict(self) -> None:
        """T1.2: send_request params annotation uses dict[str, object]."""
        sig = inspect.signature(StdioTransport.send_request)
        params_param = sig.parameters["params"]
        annotation = str(params_param.annotation)

        assert "object" in annotation, (
            f"Expected params to contain 'object', got {annotation}"
        )
        assert "Any" not in annotation, (
            "Params must not use Any (type safety boundary)"
        )


class TestTransportInternalTypes:
    """Tests for internal type annotations in StdioTransport."""

    def test_pending_dict_annotation(self) -> None:
        """T2.1: _pending annotation should use Future[object] not Future[Any]."""
        # Check the class annotation
        annotations = StdioTransport.__annotations__
        pending_annotation = annotations.get("_pending")

        if pending_annotation is not None:
            annotation_str = str(pending_annotation)
            # The annotation should NOT contain Any
            assert "Any" not in annotation_str, (
                f"_pending must not use Any, got {annotation_str}"
            )


class TestPyrightSuppressions:
    """Tests that transport files have no file-level pyright suppressions."""

    def test_transport_py_no_file_level_suppressions(self) -> None:
        """T3.1: transport.py has no file-level pyright suppressions."""
        import llm_lsp_cli.lsp.transport as transport_module

        source_path = Path(transport_module.__file__)
        content = source_path.read_text()
        lines = content.splitlines()[:20]

        file_level_suppressions = [
            line for line in lines
            if line.strip().startswith("# pyright:")
        ]

        assert len(file_level_suppressions) == 0, (
            f"Found file-level pyright suppressions in transport.py: "
            f"{file_level_suppressions}"
        )

    def test_typed_transport_py_no_file_level_suppressions(self) -> None:
        """T3.2: typed_transport.py has no file-level pyright suppressions."""
        import llm_lsp_cli.lsp.typed_transport as typed_transport_module

        source_path = Path(typed_transport_module.__file__)
        content = source_path.read_text()
        lines = content.splitlines()[:20]

        file_level_suppressions = [
            line for line in lines
            if line.strip().startswith("# pyright:")
        ]

        assert len(file_level_suppressions) == 0, (
            f"Found file-level pyright suppressions in typed_transport.py: "
            f"{file_level_suppressions}"
        )
