"""Tests for daemon RPC param models (Step 2 of ADR-0028).

These tests verify the flat camelCase param models in ipc/cli_params.py
that match the daemon's expected wire format.
"""

import pytest
from pydantic import ValidationError


class TestDaemonPositionParams:
    """Test DaemonPositionParams model construction and serialization."""

    def test_import_from_ipc(self) -> None:
        """DaemonPositionParams should be importable from llm_lsp_cli.ipc."""
        from llm_lsp_cli.ipc import DaemonPositionParams

        assert DaemonPositionParams is not None

    def test_construction_with_snake_case(self) -> None:
        """DaemonPositionParams should accept snake_case field names."""
        from llm_lsp_cli.ipc import DaemonPositionParams

        params = DaemonPositionParams(
            workspace_path="/ws",
            file_path="/file.py",
            line=5,
            column=10,
        )
        assert params.workspace_path == "/ws"
        assert params.file_path == "/file.py"
        assert params.line == 5
        assert params.column == 10

    def test_construction_with_camel_case_alias(self) -> None:
        """DaemonPositionParams should accept camelCase aliases."""
        from llm_lsp_cli.ipc import DaemonPositionParams

        params = DaemonPositionParams(
            workspacePath="/ws",  # alias
            filePath="/file.py",  # alias
            line=5,
            column=10,
        )
        assert params.workspace_path == "/ws"
        assert params.file_path == "/file.py"

    def test_default_values(self) -> None:
        """line and column should default to 0."""
        from llm_lsp_cli.ipc import DaemonPositionParams

        params = DaemonPositionParams(
            workspace_path="/ws",
            file_path="/file.py",
        )
        assert params.line == 0
        assert params.column == 0

    def test_required_fields(self) -> None:
        """workspace_path and file_path should be required."""
        from llm_lsp_cli.ipc import DaemonPositionParams

        with pytest.raises(ValidationError):
            DaemonPositionParams()  # Missing required fields

        with pytest.raises(ValidationError):
            DaemonPositionParams(workspace_path="/ws")  # Missing file_path

    def test_serialization_to_camel_case(self) -> None:
        """model_dump(by_alias=True) should produce flat camelCase format."""
        from llm_lsp_cli.ipc import DaemonPositionParams

        params = DaemonPositionParams(
            workspace_path="/ws",
            file_path="/file.py",
            line=5,
            column=10,
        )
        dumped = params.model_dump(mode="json", by_alias=True)
        assert dumped == {
            "workspacePath": "/ws",
            "filePath": "/file.py",
            "line": 5,
            "column": 10,
        }

    def test_extra_fields_ignored(self) -> None:
        """Extra fields should be ignored (extra='ignore')."""
        from llm_lsp_cli.ipc import DaemonPositionParams

        # Should not raise - extra fields are ignored
        params = DaemonPositionParams(
            workspace_path="/ws",
            file_path="/file.py",
            unknown_field="value",  # type: ignore[call-arg]
        )
        assert params.workspace_path == "/ws"
        assert not hasattr(params, "unknown_field")


class TestDaemonFileParams:
    """Test DaemonFileParams model."""

    def test_import_from_ipc(self) -> None:
        """DaemonFileParams should be importable from llm_lsp_cli.ipc."""
        from llm_lsp_cli.ipc import DaemonFileParams

        assert DaemonFileParams is not None

    def test_construction(self) -> None:
        """DaemonFileParams should accept workspace_path and file_path."""
        from llm_lsp_cli.ipc import DaemonFileParams

        params = DaemonFileParams(
            workspace_path="/ws",
            file_path="/file.py",
        )
        assert params.workspace_path == "/ws"
        assert params.file_path == "/file.py"

    def test_serialization_to_camel_case(self) -> None:
        """model_dump(by_alias=True) should produce flat camelCase format."""
        from llm_lsp_cli.ipc import DaemonFileParams

        params = DaemonFileParams(
            workspace_path="/ws",
            file_path="/file.py",
        )
        dumped = params.model_dump(mode="json", by_alias=True)
        assert dumped == {
            "workspacePath": "/ws",
            "filePath": "/file.py",
        }


class TestDaemonWorkspaceParams:
    """Test DaemonWorkspaceParams model."""

    def test_import_from_ipc(self) -> None:
        """DaemonWorkspaceParams should be importable from llm_lsp_cli.ipc."""
        from llm_lsp_cli.ipc import DaemonWorkspaceParams

        assert DaemonWorkspaceParams is not None

    def test_construction(self) -> None:
        """DaemonWorkspaceParams should accept workspace_path only."""
        from llm_lsp_cli.ipc import DaemonWorkspaceParams

        params = DaemonWorkspaceParams(workspace_path="/ws")
        assert params.workspace_path == "/ws"

    def test_serialization_to_camel_case(self) -> None:
        """model_dump(by_alias=True) should produce flat camelCase format."""
        from llm_lsp_cli.ipc import DaemonWorkspaceParams

        params = DaemonWorkspaceParams(workspace_path="/ws")
        dumped = params.model_dump(mode="json", by_alias=True)
        assert dumped == {"workspacePath": "/ws"}


class TestDaemonRenameParams:
    """Test DaemonRenameParams model (inherits DaemonPositionParams)."""

    def test_import_from_ipc(self) -> None:
        """DaemonRenameParams should be importable from llm_lsp_cli.ipc."""
        from llm_lsp_cli.ipc import DaemonRenameParams

        assert DaemonRenameParams is not None

    def test_construction(self) -> None:
        """DaemonRenameParams should add new_name to position params."""
        from llm_lsp_cli.ipc import DaemonRenameParams

        params = DaemonRenameParams(
            workspace_path="/ws",
            file_path="/f.py",
            line=1,
            column=0,
            new_name="bar",
        )
        assert params.workspace_path == "/ws"
        assert params.file_path == "/f.py"
        assert params.line == 1
        assert params.column == 0
        assert params.new_name == "bar"

    def test_serialization_to_camel_case(self) -> None:
        """model_dump(by_alias=True) should include newName."""
        from llm_lsp_cli.ipc import DaemonRenameParams

        params = DaemonRenameParams(
            workspace_path="/ws",
            file_path="/f.py",
            line=1,
            column=0,
            new_name="bar",
        )
        dumped = params.model_dump(mode="json", by_alias=True)
        assert dumped == {
            "workspacePath": "/ws",
            "filePath": "/f.py",
            "line": 1,
            "column": 0,
            "newName": "bar",
        }

    def test_new_name_required(self) -> None:
        """new_name should be required."""
        from llm_lsp_cli.ipc import DaemonRenameParams

        with pytest.raises(ValidationError):
            DaemonRenameParams(
                workspace_path="/ws",
                file_path="/f.py",
                # Missing new_name
            )


class TestDaemonSymbolQueryParams:
    """Test DaemonSymbolQueryParams model (inherits DaemonWorkspaceParams)."""

    def test_import_from_ipc(self) -> None:
        """DaemonSymbolQueryParams should be importable from llm_lsp_cli.ipc."""
        from llm_lsp_cli.ipc import DaemonSymbolQueryParams

        assert DaemonSymbolQueryParams is not None

    def test_construction(self) -> None:
        """DaemonSymbolQueryParams should add query to workspace params."""
        from llm_lsp_cli.ipc import DaemonSymbolQueryParams

        params = DaemonSymbolQueryParams(
            workspace_path="/ws",
            query="MyClass",
        )
        assert params.workspace_path == "/ws"
        assert params.query == "MyClass"

    def test_serialization_to_camel_case(self) -> None:
        """model_dump(by_alias=True) should include query."""
        from llm_lsp_cli.ipc import DaemonSymbolQueryParams

        params = DaemonSymbolQueryParams(
            workspace_path="/ws",
            query="MyClass",
        )
        dumped = params.model_dump(mode="json", by_alias=True)
        assert dumped == {
            "workspacePath": "/ws",
            "query": "MyClass",
        }


class TestIPCExports:
    """Test that all 5 models are exported from ipc module."""

    def test_all_models_in_all(self) -> None:
        """All 5 daemon param models should be in __all__."""
        from llm_lsp_cli import ipc

        expected_models = [
            "DaemonPositionParams",
            "DaemonFileParams",
            "DaemonWorkspaceParams",
            "DaemonRenameParams",
            "DaemonSymbolQueryParams",
        ]
        for model_name in expected_models:
            assert model_name in ipc.__all__, f"{model_name} not in ipc.__all__"
            assert hasattr(ipc, model_name), f"{model_name} not importable from ipc"
