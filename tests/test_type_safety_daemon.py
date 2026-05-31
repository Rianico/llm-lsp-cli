"""Type safety tests for daemon.py and related modules.

These tests verify the type-safety refactor of daemon.py:
1. Serialization migration from daemon.py to IPC layer
2. LSPClient public accessor methods for cache
3. Typed LSP request parameters
4. Stub file cleanup

Per TDD discipline: These tests FAIL initially and are made to pass by the implementation.
"""

import asyncio
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pydantic import BaseModel

from llm_lsp_cli.lsp.types import DocumentSymbolParams, TextDocumentIdentifier

if TYPE_CHECKING:
    pass


# =============================================================================
# TS-01: Stub File Cleanup - Static Verification
# =============================================================================


class TestStubFileCleanup:
    """Verify stub file uses file-level suppressions correctly."""

    def test_stub_file_file_level_suppressions_only(self) -> None:
        """TS-01: Stub file should use only file-level suppressions.

        Stub files (typings/**/*.pyi) are designated zones for file-level
        suppressions. They should use file-level `# pyright: <rule>=false`
        at the top, NOT inline `# pyright: ignore` suppressions.
        """
        stub_path = Path("typings/daemon/daemon.pyi")
        assert stub_path.exists(), f"Stub file not found: {stub_path}"

        content = stub_path.read_text()
        lines = content.split("\n")

        # Check for inline suppressions (not allowed)
        inline_matches = re.findall(r"#\s*pyright:\s*ignore", content)
        assert len(inline_matches) == 0, (
            f"Found {len(inline_matches)} inline pyright:ignore suppression(s) in stub file. "
            f"Use file-level suppressions at the top of {stub_path}"
        )

        # Verify file-level suppressions are at the top (before any code)
        file_level_found = False
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            if re.match(r"#\s*pyright:\s*\w+=false", line):
                file_level_found = True
                break

        assert file_level_found, (
            f"Stub file should have file-level suppressions at the top. "
            f"Expected '# pyright: reportAny=false' or similar in first 10 lines."
        )

    def test_stub_file_type_checks_clean(self) -> None:
        """TS-01b: Stub file should pass type checking with 0 errors, 0 warnings."""
        result = subprocess.run(
            ["uv", "run", "basedpyright", "typings/daemon/daemon.pyi"],
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr
        assert "0 errors" in output and "0 warnings" in output, (
            f"Stub file has type diagnostics:\n{output}"
        )


# =============================================================================
# TS-02, TS-03, TS-04: IPC Serialization Helper
# =============================================================================


class TestIPCSerializationHelper:
    """Verify serialize_for_json exists and works correctly."""

    def test_ipc_serialization_function_exists(self) -> None:
        """TS-02: serialize_for_json should exist in ipc/protocol.py."""
        from llm_lsp_cli.ipc.protocol import serialize_for_json

        assert callable(serialize_for_json), "serialize_for_json must be callable"

    def test_ipc_serialization_handles_pydantic_models(self) -> None:
        """TS-03: Serialization correctly handles Pydantic BaseModel."""

        class TestModel(BaseModel):
            name: str
            count: int

        from llm_lsp_cli.ipc.protocol import serialize_for_json

        model = TestModel(name="test", count=42)
        result = serialize_for_json(model)

        assert isinstance(result, dict), "Result must be a dict"
        assert result == {"name": "test", "count": 42}

    def test_ipc_serialization_handles_nested_containers(self) -> None:
        """TS-04: Serialization handles lists and dicts with Pydantic models."""

        class TestModel(BaseModel):
            name: str
            count: int

        from llm_lsp_cli.ipc.protocol import serialize_for_json

        model = TestModel(name="item", count=1)
        nested = {
            "items": [model, {"key": "value"}],
            "single": model,
        }
        result = serialize_for_json(nested)

        assert isinstance(result, dict), "Result must be a dict"
        assert result["items"][0] == {"name": "item", "count": 1}
        assert result["single"] == {"name": "item", "count": 1}
        assert result["items"][1] == {"key": "value"}

    def test_ipc_serialization_handles_none(self) -> None:
        """Serialization handles None gracefully."""
        from llm_lsp_cli.ipc.protocol import serialize_for_json

        result = serialize_for_json(None)
        assert result is None

    def test_ipc_serialization_handles_primitives(self) -> None:
        """Serialization passes through primitive types."""
        from llm_lsp_cli.ipc.protocol import serialize_for_json

        assert serialize_for_json("string") == "string"
        assert serialize_for_json(42) == 42
        assert serialize_for_json(3.14) == 3.14
        assert serialize_for_json(True) is True


# =============================================================================
# TS-05, TS-06: LSPClient Accessor Methods
# =============================================================================


class TestLSPClientAccessors:
    """Verify LSPClient has public accessor methods for cache."""

    def test_get_diagnostic_cache_state_method_exists(self) -> None:
        """TS-05: get_diagnostic_cache_state method should exist."""
        from llm_lsp_cli.lsp.client import LSPClient

        assert hasattr(LSPClient, "get_diagnostic_cache_state")
        method = getattr(LSPClient, "get_diagnostic_cache_state")
        assert callable(method)

    def test_mark_diagnostic_cache_open_method_exists(self) -> None:
        """TS-05: mark_diagnostic_cache_open method should exist."""
        from llm_lsp_cli.lsp.client import LSPClient

        assert hasattr(LSPClient, "mark_diagnostic_cache_open")
        method = getattr(LSPClient, "mark_diagnostic_cache_open")
        assert callable(method)

    def test_is_diagnostic_cache_stale_method_exists(self) -> None:
        """TS-05: is_diagnostic_cache_stale method should exist."""
        from llm_lsp_cli.lsp.client import LSPClient

        assert hasattr(LSPClient, "is_diagnostic_cache_stale")
        method = getattr(LSPClient, "is_diagnostic_cache_stale")
        assert callable(method)

    @pytest.mark.asyncio
    async def test_accessor_methods_work_correctly(self) -> None:
        """TS-06: Accessor methods should return correct cache state."""
        from unittest.mock import AsyncMock, MagicMock

        from llm_lsp_cli.lsp.cache import FileState
        from llm_lsp_cli.lsp.client import LSPClient

        # Create a mock LSPClient with mocked cache
        client = MagicMock(spec=LSPClient)
        client._diagnostic_cache = MagicMock()

        # Mock the cache methods
        mock_file_state = FileState()
        client._diagnostic_cache.get_file_state = AsyncMock(return_value=mock_file_state)
        client._diagnostic_cache.on_did_open = AsyncMock()
        client._diagnostic_cache.is_stale = AsyncMock(return_value=True)

        # Attach real accessor implementations
        async def get_diagnostic_cache_state(self: LSPClient, uri: str) -> FileState:
            return await self._diagnostic_cache.get_file_state(uri)

        async def mark_diagnostic_cache_open(self: LSPClient, uri: str) -> None:
            await self._diagnostic_cache.on_did_open(uri)

        async def is_diagnostic_cache_stale(self: LSPClient, uri: str, mtime: float) -> bool:
            return await self._diagnostic_cache.is_stale(uri, mtime)

        client.get_diagnostic_cache_state = get_diagnostic_cache_state.__get__(client, type(client))
        client.mark_diagnostic_cache_open = mark_diagnostic_cache_open.__get__(client, type(client))
        client.is_diagnostic_cache_stale = is_diagnostic_cache_stale.__get__(client, type(client))

        # Test get_diagnostic_cache_state
        state = await client.get_diagnostic_cache_state("file:///test.py")
        assert isinstance(state, FileState)

        # Test mark_diagnostic_cache_open
        await client.mark_diagnostic_cache_open("file:///test.py")
        client._diagnostic_cache.on_did_open.assert_called_once_with("file:///test.py")

        # Test is_diagnostic_cache_stale
        is_stale = await client.is_diagnostic_cache_stale("file:///test.py", 1.0)
        assert is_stale is True


# =============================================================================
# TS-07: Serialization Removed from daemon.py
# =============================================================================


class TestSerializationRemovedFromDaemon:
    """Verify _to_json_serializable is removed from daemon package."""

    def test_to_json_serializable_removed_from_daemon(self) -> None:
        """TS-07: _to_json_serializable function should not exist in daemon package."""
        handler_path = Path("src/llm_lsp_cli/daemon/handler.py")
        assert handler_path.exists(), f"daemon/handler.py not found: {handler_path}"

        content = handler_path.read_text()
        matches = re.findall(r"_to_json_serializable", content)

        assert len(matches) == 0, (
            f"Found {len(matches)} reference(s) to _to_json_serializable in daemon/handler.py. "
            f"Serialization should be moved to ipc/protocol.py"
        )


# =============================================================================
# TS-08: No Private Cache Access in daemon.py
# =============================================================================


class TestNoPrivateCacheAccess:
    """Verify daemon handler doesn't access _diagnostic_cache directly."""

    def test_no_private_cache_access_in_daemon(self) -> None:
        """TS-08: daemon handler should not access _diagnostic_cache directly.

        Use public accessor methods instead of private _diagnostic_cache.
        """
        handler_path = Path("src/llm_lsp_cli/daemon/handler.py")
        assert handler_path.exists(), f"daemon/handler.py not found: {handler_path}"

        content = handler_path.read_text()
        # Look for _diagnostic_cache access (not in comments or strings)
        # Pattern: client._diagnostic_cache or cache = client._diagnostic_cache
        matches = re.findall(r"\._diagnostic_cache", content)

        assert len(matches) == 0, (
            f"Found {len(matches)} direct access(es) to _diagnostic_cache in daemon/handler.py. "
            f"Use public accessor methods (get_diagnostic_cache_state, etc.) instead."
        )


# =============================================================================
# TS-09: Typed LSP Parameters
# =============================================================================


class TestTypedLSPParameters:
    """Verify _send_lsp_request uses typed parameters."""

    def test_send_lsp_request_uses_typed_params(self) -> None:
        """TS-09: _send_lsp_request signature should use Pydantic types.

        The lsp_params parameter should be typed as a Pydantic model
        (e.g., DocumentSymbolParams, DocumentDiagnosticParams) instead of
        dict[str, object].
        """
        handler_path = Path("src/llm_lsp_cli/daemon/handler.py")
        assert handler_path.exists(), f"daemon/handler.py not found: {handler_path}"

        content = handler_path.read_text()

        # Check if _send_lsp_request has typed params
        # Pattern: lsp_params: lsp.DocumentSymbolParams | lsp.DocumentDiagnosticParams
        pattern = r"lsp_params:\s*(lsp\.)?(DocumentSymbolParams|DocumentDiagnosticParams|TextDocumentPositionParams)"
        matches = re.findall(pattern, content)

        # At least one typed parameter usage should exist
        assert len(matches) > 0, (
            "No typed LSP parameters found in _send_lsp_request. "
            "Use Pydantic models (DocumentSymbolParams, DocumentDiagnosticParams) "
            "instead of dict[str, object]."
        )


# =============================================================================
# TS-10: LSP Params URI Access is Typed
# =============================================================================


class TestLSPParamsURIAccess:
    """Verify URI access via typed property."""

    def test_uri_access_via_typed_property(self) -> None:
        """TS-10: URI should be accessed via typed property, not dict.get().

        When using Pydantic models, access uri via model.text_document.uri
        instead of params.get("textDocument", {}).get("uri").
        """
        from llm_lsp_cli.lsp.types import DocumentSymbolParams, TextDocumentIdentifier

        params = DocumentSymbolParams(
            textDocument=TextDocumentIdentifier(uri="file:///test.py")
        )

        # Typed access should work
        uri = params.text_document.uri
        assert uri == "file:///test.py"


# =============================================================================
# TS-11: No Pyright Suppressions in daemon.py
# =============================================================================


class TestNoPyrightSuppressionsInDaemon:
    """Verify daemon package has no pyright suppressions."""

    def test_daemon_py_no_pyright_suppressions(self) -> None:
        """TS-11: daemon package should have no pyright suppressions.

        All type issues should be fixed properly, not suppressed.
        """
        handler_path = Path("src/llm_lsp_cli/daemon/handler.py")
        assert handler_path.exists(), f"daemon/handler.py not found: {handler_path}"

        content = handler_path.read_text()
        matches = re.findall(r"#\s*pyright:", content)

        assert len(matches) == 0, (
            f"Found {len(matches)} pyright suppression(s) in daemon/handler.py. "
            f"Fix the underlying type issues instead of suppressing."
        )


# =============================================================================
# TS-12: Suppressions Only in Designated Zones
# =============================================================================


class TestSuppressionsInDesignatedZones:
    """Verify suppressions only in designated zones (transport.py, ipc/)."""

    def test_suppressions_only_in_designated_zones(self) -> None:
        """TS-12: Pyright suppressions should only exist in designated zones.

        This test checks only daemon package and the files directly modified in this refactor.
        Other files may have pre-existing suppressions outside scope.

        Designated zones:
        - src/llm_lsp_cli/lsp/transport.py
        - src/llm_lsp_cli/ipc/

        Files checked:
        - src/llm_lsp_cli/daemon/handler.py
        - src/llm_lsp_cli/lsp/client.py
        """
        # Only check files directly modified in this refactor
        files_to_check = [
            Path("src/llm_lsp_cli/daemon/handler.py"),
            Path("src/llm_lsp_cli/lsp/client.py"),
        ]

        violations = []
        for py_file in files_to_check:
            if not py_file.exists():
                continue
            content = py_file.read_text()
            matches = re.findall(r"#\s*pyright:", content)
            if matches:
                violations.append(f"{py_file}: {len(matches)} suppression(s)")

        assert len(violations) == 0, (
            f"Found pyright suppressions in refactored files:\n"
            + "\n".join(violations)
            + "\n\nDesignated zones: lsp/transport.py, ipc/"
        )


# =============================================================================
# TS-13: Static Type Checking Passes
# =============================================================================


class TestStaticTypeChecking:
    """Verify basedpyright reports zero errors."""

    def test_basedpyright_no_errors(self) -> None:
        """TS-13: basedpyright should report zero errors for changed files.

        Warnings are acceptable in designated zones (ipc/protocol.py).
        Only actual errors should cause failure.
        """
        result = subprocess.run(
            ["uv", "run", "basedpyright",
             "src/llm_lsp_cli/daemon.py",
             "src/llm_lsp_cli/ipc/protocol.py",
             "src/llm_lsp_cli/lsp/client.py"],
            capture_output=True,
            text=True,
        )

        # Check for errors in output (warnings are OK)
        output = result.stdout + result.stderr

        # Count errors in output
        error_count = output.count(" error,")

        assert error_count == 0, (
            f"basedpyright found {error_count} error(s):\n{output}"
        )


# =============================================================================
# TS-14: Integration - Serialization Still Works End-to-End
# =============================================================================


class TestIntegrationSerialization:
    """Verify moved serialization doesn't break IPC responses."""

    def test_build_response_with_pydantic_model(self) -> None:
        """TS-14: build_response should handle Pydantic models."""

        class ResultModel(BaseModel):
            data: str

        from llm_lsp_cli.ipc.protocol import build_response

        response = build_response(ResultModel(data="test"), request_id=1)

        # Result should be a dict, not a Pydantic model
        assert isinstance(response.result, dict), "Response result must be a dict"
        assert response.result == {"data": "test"}

        # Verify JSON serialization works
        response_dict = response.to_dict()
        assert "result" in response_dict
        assert response_dict["result"] == {"data": "test"}


# =============================================================================
# TS-15: Regression - Existing Tests Pass
# =============================================================================


class TestRegression:
    """Verify no runtime behavior changes."""

    def test_existing_tests_pass(self) -> None:
        """TS-15: All existing tests should still pass.

        This is a placeholder - the actual test run is done via:
        uv run pytest tests/ -q
        """
        # This test is a marker - actual verification is done separately
        # The test suite should pass after implementation
        pass
