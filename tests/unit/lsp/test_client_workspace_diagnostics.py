"""Tests for unified workspace diagnostic handling in LSPClient.

These tests verify the GUID-based token system, direct cache delegation,
and continuous streaming behavior as specified in ADR 003 Revised.
"""

import asyncio
import re
import typing
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_lsp_cli.lsp.client import LSPClient
from llm_lsp_cli.lsp.constants import LSPConstants


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_transport() -> AsyncMock:
    """Mock LSP transport for testing."""
    transport = AsyncMock()
    transport.send_request = AsyncMock()
    transport.send_notification = AsyncMock()
    transport.send_request_fire_and_forget = AsyncMock()
    transport.on_notification = MagicMock()
    transport.on_request = MagicMock()
    return transport


@pytest.fixture
async def lsp_client(temp_dir: Path) -> typing.AsyncGenerator[LSPClient, None]:
    """Create LSPClient with mocked transport and initialize it."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from llm_lsp_cli.lsp import types as lsp

    client = LSPClient(
        workspace_path=str(temp_dir),
        server_command="pyright-langserver",
        server_args=["--stdio"],
        language_id="python",
    )

    # Create a mock TypedLSPTransport
    mock_typed_transport = MagicMock()
    mock_typed_transport.start = AsyncMock()
    mock_typed_transport.stop = AsyncMock()
    mock_typed_transport.send_notification = AsyncMock()
    mock_typed_transport.send_request_fire_and_forget = AsyncMock()
    mock_typed_transport.send_request = AsyncMock()
    mock_typed_transport.on_notification = MagicMock()
    mock_typed_transport.on_request = MagicMock()
    mock_typed_transport.send_initialize = AsyncMock(return_value=lsp.InitializeResult(
        capabilities=lsp.ServerCapabilities()
    ))

    # Patch TypedLSPTransport to return our mock
    with patch("llm_lsp_cli.lsp.client.TypedLSPTransport", return_value=mock_typed_transport):
        # Initialize to send workspace diagnostic request
        await client.initialize()
        # Store mock on client for test access
        client._mock_transport = mock_typed_transport  # type: ignore
        yield client


@pytest.fixture
def sample_diagnostics() -> list[dict[str, object]]:
    """Sample diagnostic list for testing."""
    return [
        {
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 0, "character": 10},
            },
            "severity": 1,
            "message": "Test error",
            "source": "test",
        }
    ]


# =============================================================================
# Scenario 1: GUID Token Generation
# =============================================================================


class TestGuidTokenGeneration:
    """Tests for GUID token generation in workspace diagnostics."""

    def test_tokens_are_uuid4_format(self, lsp_client: LSPClient) -> None:
        """Test that workspace diagnostic tokens match UUID4 format pattern."""
        # Initialize client to generate tokens
        # The tokens should be generated once on first access
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )

        # Access the workspace diagnostic token
        token = lsp_client.get_workspace_diagnostic_token()

        # Verify it matches UUID4 format
        assert uuid_pattern.match(token), f"Token '{token}' does not match UUID4 format"

    def test_tokens_generated_once_on_first_request(self, lsp_client: LSPClient) -> None:
        """Test that tokens are constant after first generation."""
        # Get token multiple times
        token1 = lsp_client.get_workspace_diagnostic_token()
        token2 = lsp_client.get_workspace_diagnostic_token()

        # Tokens should be identical (generated once, reused)
        assert token1 == token2

    def test_tokens_unique_per_session(self, temp_dir: Path) -> None:
        """Test that different client instances have different tokens."""
        client1 = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        client2 = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        token1 = client1.get_workspace_diagnostic_token()
        token2 = client2.get_workspace_diagnostic_token()

        # Different sessions should have different tokens
        assert token1 != token2


# =============================================================================
# Scenario 2: Workspace Diagnostic Request
# =============================================================================


class TestWorkspaceDiagnosticRequest:
    """Tests for workspace/diagnostic request sending."""

    @pytest.mark.asyncio
    async def test_workspace_diagnostic_request_sent_after_initialized(
        self, lsp_client: LSPClient
    ) -> None:
        """Test that workspace/diagnostic request is sent after initialized notification."""
        # Track calls
        mock_transport = lsp_client._mock_transport  # type: ignore
        send_notification_calls = mock_transport.send_notification.call_args_list

        # Find the initialized notification
        initialized_sent = any(
            call[0][0] == LSPConstants.INITIALIZED for call in send_notification_calls
        )

        # Find the workspace/diagnostic request
        diagnostic_request_sent = any(
            call[0][0] == LSPConstants.WORKSPACE_DIAGNOSTIC
            for call in mock_transport.send_request_fire_and_forget.call_args_list
        )

        # Both should have been sent
        assert initialized_sent, "initialized notification was not sent"
        assert diagnostic_request_sent, "workspace/diagnostic request was not sent"

    @pytest.mark.asyncio
    async def test_workspace_diagnostic_request_sent_only_once(
        self, lsp_client: LSPClient
    ) -> None:
        """Test that workspace/diagnostic request is sent only once."""
        mock_transport = lsp_client._mock_transport  # type: ignore

        # Filter for workspace diagnostic requests
        workspace_diagnostic_calls = [
            call
            for call in mock_transport.send_request_fire_and_forget.call_args_list
            if call[0][0] == LSPConstants.WORKSPACE_DIAGNOSTIC
        ]

        # Should be sent exactly once
        assert len(workspace_diagnostic_calls) == 1

    @pytest.mark.asyncio
    async def test_request_includes_guid_tokens(
        self, lsp_client: LSPClient
    ) -> None:
        """Test that request params include partialResultToken and workDoneToken."""
        # Get the workspace diagnostic request params
        mock_transport = lsp_client._mock_transport  # type: ignore
        calls = mock_transport.send_request_fire_and_forget.call_args_list
        workspace_diagnostic_call = None

        for call in calls:
            if call[0][0] == LSPConstants.WORKSPACE_DIAGNOSTIC:
                workspace_diagnostic_call = call
                break

        assert workspace_diagnostic_call is not None, "workspace/diagnostic request not found"

        params = workspace_diagnostic_call[0][1]

        # Verify tokens are present
        assert "partialResultToken" in params, "partialResultToken missing from params"
        assert "workDoneToken" in params, "workDoneToken missing from params"

        # Verify they match UUID format
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        assert uuid_pattern.match(params["partialResultToken"])
        assert uuid_pattern.match(params["workDoneToken"])


# =============================================================================
# Scenario 3: Progress Handling with GUID Token Matching
# =============================================================================


class TestProgressHandlingWithTokenMatching:
    """Tests for $/progress notification routing via GUID token."""

    @pytest.mark.asyncio
    async def test_progress_matches_guid_token(
        self, lsp_client: LSPClient, sample_diagnostics: list[dict[str, object]]
    ) -> None:
        """Test progress with matching token is handled correctly."""
        # Create test file
        test_file = lsp_client.workspace_path / "test.py"
        test_file.write_text("# test")
        test_uri = test_file.as_uri()

        # Get the workspace diagnostic token
        token = lsp_client.get_workspace_diagnostic_token()

        # Create progress params with matching token
        params = {
            "token": token,
            "value": {
                "items": [
                    {
                        "uri": test_uri,
                        "diagnostics": sample_diagnostics,
                    }
                ],
            },
        }

        # Call progress handler
        lsp_client._handle_progress(params)

        # Give async task time to complete
        await asyncio.sleep(0.01)

        # Verify diagnostics were cached
        cached = await lsp_client._diagnostic_cache.get_diagnostics(test_uri)
        assert len(cached) == 1
        assert cached[0]["message"] == "Test error"

    @pytest.mark.asyncio
    async def test_progress_wrong_token_delegated_to_handler(
        self, lsp_client: LSPClient, mock_transport: AsyncMock
    ) -> None:
        """Test progress with non-matching token is passed to _progress_handler."""
        # Create progress params with wrong token
        params = {
            "token": "wrong-token-not-workspace-diagnostic",
            "value": {
                "kind": "begin",
                "title": "Some Other Progress",
            },
        }

        # Mock _progress_handler
        lsp_client._progress_handler.handle_progress = MagicMock()

        # Call progress handler
        lsp_client._handle_progress(params)

        # Verify it was delegated to _progress_handler
        lsp_client._progress_handler.handle_progress.assert_called_once_with(params)

    @pytest.mark.asyncio
    async def test_progress_without_value_dict_ignored(
        self, lsp_client: LSPClient
    ) -> None:
        """Test malformed progress (without value dict) is ignored."""
        # Create malformed progress params
        params = {
            "token": "some-token",
            "value": None,  # Invalid - should be dict
        }

        # Should not raise
        lsp_client._handle_progress(params)


# =============================================================================
# Scenario 4: Progress Processing and Cache Updates
# =============================================================================


class TestProgressProcessingAndCacheUpdates:
    """Tests for progress notification processing and cache updates."""

    @pytest.mark.asyncio
    async def test_handle_workspace_diagnostic_progress_begin_logged(
        self, lsp_client: LSPClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test 'begin' kind progress is logged only."""
        import logging

        # Set up logging
        logger = logging.getLogger("llm_lsp_cli.lsp.client")
        logger.setLevel(logging.DEBUG)

        token = lsp_client.get_workspace_diagnostic_token()
        params = {
            "token": token,
            "value": {
                "kind": "begin",
                "title": "Workspace Diagnostics",
            },
        }

        lsp_client._handle_progress(params)

        # Verify begin was logged
        assert "begin" in caplog.text.lower() or "started" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_handle_workspace_diagnostic_progress_end_logged(
        self, lsp_client: LSPClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test 'end' kind progress is logged only."""
        import logging

        logger = logging.getLogger("llm_lsp_cli.lsp.client")
        logger.setLevel(logging.DEBUG)

        token = lsp_client.get_workspace_diagnostic_token()
        params = {
            "token": token,
            "value": {
                "kind": "end",
            },
        }

        lsp_client._handle_progress(params)

        # Verify end was logged
        assert "end" in caplog.text.lower() or "complete" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_handle_workspace_diagnostic_progress_items_cached(
        self, lsp_client: LSPClient, sample_diagnostics: list[dict[str, object]]
    ) -> None:
        """Test progress items update cache correctly."""
        # Create test file
        test_file = lsp_client.workspace_path / "test.py"
        test_file.write_text("# test")
        test_uri = test_file.as_uri()

        token = lsp_client.get_workspace_diagnostic_token()
        params = {
            "token": token,
            "value": {
                "items": [
                    {
                        "uri": test_uri,
                        "diagnostics": sample_diagnostics,
                    }
                ],
            },
        }

        lsp_client._handle_progress(params)
        await asyncio.sleep(0.01)

        cached = await lsp_client._diagnostic_cache.get_diagnostics(test_uri)
        assert len(cached) == 1
        assert cached[0]["message"] == "Test error"

    @pytest.mark.asyncio
    async def test_handle_workspace_diagnostic_progress_empty_diagnostics_cached(
        self, lsp_client: LSPClient
    ) -> None:
        """Test empty diagnostics list is still cached for files with no errors."""
        # Create test file
        test_file = lsp_client.workspace_path / "test.py"
        test_file.write_text("# test")
        test_uri = test_file.as_uri()

        token = lsp_client.get_workspace_diagnostic_token()
        params = {
            "token": token,
            "value": {
                "items": [
                    {
                        "uri": test_uri,
                        "diagnostics": [],  # Empty - no errors
                    }
                ],
            },
        }

        lsp_client._handle_progress(params)
        await asyncio.sleep(0.01)

        # Verify file IS in cache with empty diagnostics
        cached = await lsp_client._diagnostic_cache.get_diagnostics(test_uri)
        assert cached == []  # Empty list, but file is cached

    @pytest.mark.asyncio
    async def test_handle_workspace_diagnostic_progress_no_kind_field(
        self, lsp_client: LSPClient, sample_diagnostics: list[dict[str, object]]
    ) -> None:
        """Test basedpyright-style progress (no 'kind' at value level) is handled."""
        # Create test file
        test_file = lsp_client.workspace_path / "test.py"
        test_file.write_text("# test")
        test_uri = test_file.as_uri()

        token = lsp_client.get_workspace_diagnostic_token()
        # basedpyright sends progress without 'kind' at value level
        params = {
            "token": token,
            "value": {
                "items": [
                    {
                        "uri": test_uri,
                        "diagnostics": sample_diagnostics,
                        "kind": "full",  # kind is per-item, not at value level
                    }
                ],
            },
        }

        # Should not raise - handles progress without 'kind' at value level
        lsp_client._handle_progress(params)
        await asyncio.sleep(0.01)

        cached = await lsp_client._diagnostic_cache.get_diagnostics(test_uri)
        assert len(cached) == 1


# =============================================================================
# Scenario 5: Request Workspace Diagnostics
# =============================================================================


class TestRequestWorkspaceDiagnostics:
    """Tests for request_workspace_diagnostics method."""

    @pytest.mark.asyncio
    async def test_request_workspace_diagnostics_returns_cached(
        self, lsp_client: LSPClient, sample_diagnostics: list[dict[str, object]]
    ) -> None:
        """Test request_workspace_diagnostics returns cached diagnostics directly."""
        # Create test file and add to cache
        test_file = lsp_client.workspace_path / "test.py"
        test_file.write_text("# test")
        test_uri = test_file.as_uri()

        await lsp_client._diagnostic_cache.update_diagnostics(test_uri, sample_diagnostics)

        # Mark workspace as indexed
        lsp_client._workspace_indexed.set()

        # Request workspace diagnostics
        result = await lsp_client.request_workspace_diagnostics()

        # Verify returns cached diagnostics
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_request_workspace_diagnostics_waits_for_indexing(
        self, lsp_client: LSPClient
    ) -> None:
        """Test request waits for _workspace_indexed event."""
        # Ensure workspace is indexed
        lsp_client._workspace_indexed.set()

        # Should not raise - waits for indexing
        result = await lsp_client.request_workspace_diagnostics()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_request_workspace_diagnostics_timeout_returns_partial(
        self, lsp_client: LSPClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test timeout logs warning and returns partial results."""
        import logging

        logger = logging.getLogger("llm_lsp_cli.lsp.client")
        logger.setLevel(logging.DEBUG)

        # Don't set _workspace_indexed - let it timeout
        # This should log a warning and return partial results

        # Mock to speed up test - set a short timeout
        with patch("llm_lsp_cli.lsp.client._WORKSPACE_DIAGNOSTIC_TIMEOUT", 0.1):
            result = await lsp_client.request_workspace_diagnostics()

        # Should return partial results (empty list in this case)
        assert isinstance(result, list)
        # Verify warning was logged
        assert "timeout" in caplog.text.lower() or "timed out" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_request_workspace_diagnostics_no_pull_mode_check(
        self, lsp_client: LSPClient
    ) -> None:
        """Test there is no _diagnostic_manager check in request_workspace_diagnostics."""
        # Get the source code of the method
        import inspect

        source = inspect.getsource(lsp_client.request_workspace_diagnostics)

        # Verify no _diagnostic_manager reference
        assert "_diagnostic_manager" not in source, "Should not check _diagnostic_manager"


# =============================================================================
# Scenario 6: Removed Components (Negative Tests)
# =============================================================================


class TestRemovedComponents:
    """Negative tests verifying removed components no longer exist."""

    def test_workspace_diagnostic_manager_not_importable(self) -> None:
        """Test WorkspaceDiagnosticManager class is removed."""
        from llm_lsp_cli.lsp import client

        # Verify class does not exist
        assert not hasattr(client, "WorkspaceDiagnosticManager")

    def test_client_has_no_diagnostic_manager_attribute(self, lsp_client: LSPClient) -> None:
        """Test LSPClient has no _diagnostic_manager attribute."""
        assert not hasattr(lsp_client, "_diagnostic_manager")

    def test_client_has_no_handle_register_capability_request(self, lsp_client: LSPClient) -> None:
        """Test _handle_register_capability_request method is removed."""
        assert not hasattr(lsp_client, "_handle_register_capability_request")

    def test_client_has_no_handle_diagnostic_refresh_request(self, lsp_client: LSPClient) -> None:
        """Test _handle_diagnostic_refresh_request method is removed."""
        assert not hasattr(lsp_client, "_handle_diagnostic_refresh_request")
