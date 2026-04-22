"""Unit tests for dual-path diagnostic logging with masking.

Tests for the _mask_diagnostics() function and dual logging behavior in StdioTransport.
"""

import copy
import json
import logging
from io import StringIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from llm_lsp_cli.lsp.transport import StdioTransport

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def log_capture_handler() -> Any:
    """Fixture to capture log output for assertions."""
    logger = logging.getLogger("llm_lsp_cli.lsp.transport")
    handler = logging.StreamHandler(StringIO())
    handler.setLevel(logging.DEBUG)
    original_level = logger.level
    original_handlers = logger.handlers.copy()
    logger.handlers = [handler]
    logger.setLevel(logging.DEBUG)

    yield handler

    # Cleanup
    logger.handlers = original_handlers
    logger.setLevel(original_level)


@pytest.fixture
def mock_diagnostic_logger() -> Any:
    """Mock the diagnostic logger."""
    with patch("llm_lsp_cli.lsp.transport._diagnostic_logger") as mock:
        yield mock


@pytest.fixture
def mock_both_loggers() -> Any:
    """Mock both daemon.logger and _diagnostic_logger simultaneously."""
    with (
        patch("llm_lsp_cli.lsp.transport.logger") as mock_daemon,
        patch("llm_lsp_cli.lsp.transport._diagnostic_logger") as mock_diag,
    ):
        yield mock_daemon, mock_diag


@pytest.fixture
def transport_with_trace() -> StdioTransport:
    """Create a StdioTransport with trace=True for message handling tests."""
    return StdioTransport(command="echo", trace=True)


@pytest.fixture
def sample_didopen_payload() -> dict[str, Any]:
    """Standard textDocument/didOpen notification payload."""
    return {
        "jsonrpc": "2.0",
        "method": "textDocument/didOpen",
        "params": {
            "textDocument": {
                "uri": "file:///project/src/main.py",
                "languageId": "python",
                "version": 1,
                "text": "def hello():\n    print('hello')\n",
            }
        },
    }


@pytest.fixture
def sample_didchange_payload() -> dict[str, Any]:
    """Standard textDocument/didChange notification payload (incremental)."""
    return {
        "jsonrpc": "2.0",
        "method": "textDocument/didChange",
        "params": {
            "textDocument": {"uri": "file:///project/src/main.py", "version": 2},
            "contentChanges": [
                {
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 3},
                    },
                    "text": "class",
                },
                {
                    "range": {
                        "start": {"line": 1, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                    "text": "# new line\n",
                },
            ],
        },
    }


# =============================================================================
# 1. Unit Tests: _mask_diagnostics() Function
# =============================================================================


class TestMaskDiagnosticsFunction:
    """Tests for the _mask_diagnostics() masking function."""

    def test_mask_progress_notification(self) -> None:
        """Test masking of $/progress notifications with diagnostics."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "method": "$/progress",
            "params": {
                "token": "workspace_diagnostics",
                "value": {
                    "items": [
                        {"diagnostics": [{"range": {"start": {"line": 0}}, "message": "error1"}]},
                        {
                            "diagnostics": [
                                {"range": {"start": {"line": 1}}, "message": "error2"},
                                {"range": {"start": {"line": 2}}, "message": "error3"},
                            ]
                        },
                    ]
                },
            },
        }

        # Act
        result = _mask_diagnostics(input_data)

        # Assert
        assert result["method"] == "$/progress"
        assert result["params"]["token"] == "workspace_diagnostics"
        # Check items array is masked
        items = result["params"]["value"]["items"]
        assert isinstance(items, str)
        assert "array_len: 2" in items

    def test_mask_publish_diagnostics_notification(self) -> None:
        """Test masking of textDocument/publishDiagnostics notifications."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "method": "textDocument/publishDiagnostics",
            "params": {
                "uri": "file:///project/src/module.py",
                "diagnostics": [
                    {
                        "range": {"start": {"line": 10, "character": 4}},
                        "severity": 1,
                        "message": "undefined variable",
                    },
                    {
                        "range": {"start": {"line": 11, "character": 0}},
                        "severity": 2,
                        "message": "unused import",
                    },
                ],
            },
        }

        # Act
        result = _mask_diagnostics(input_data)

        # Assert
        assert result["method"] == "textDocument/publishDiagnostics"
        # URI preserved
        assert result["params"]["uri"] == "file:///project/src/module.py"
        # Diagnostics array masked
        diagnostics = result["params"]["diagnostics"]
        assert isinstance(diagnostics, str)
        assert "array_len: 2" in diagnostics

    def test_mask_diagnostic_response(self) -> None:
        """Test masking of diagnostic response with items array."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "id": 42,
            "result": {
                "items": [
                    {"uri": "file:///a.py", "diagnostics": []},
                    {"uri": "file:///b.py", "diagnostics": []},
                    {"uri": "file:///c.py", "diagnostics": []},
                ]
            },
        }

        # Act
        result = _mask_diagnostics(input_data)

        # Assert
        assert result["id"] == 42
        # Items array masked
        items = result["result"]["items"]
        assert isinstance(items, str)
        assert "array_len: 3" in items

    def test_mask_diagnostics_does_not_mutate_input(self) -> None:
        """Test that _mask_diagnostics does not mutate the input data."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        original_data: dict[str, Any] = {
            "method": "textDocument/publishDiagnostics",
            "params": {
                "uri": "file:///test.py",
                "diagnostics": [{"message": "error"}],
            },
        }
        data_copy = copy.deepcopy(original_data)

        # Act
        _mask_diagnostics(original_data)

        # Assert
        assert original_data == data_copy

    def test_mask_empty_diagnostics(self) -> None:
        """Test masking of empty diagnostics arrays."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "method": "textDocument/publishDiagnostics",
            "params": {
                "uri": "file:///test.py",
                "diagnostics": [],
            },
        }

        # Act
        result = _mask_diagnostics(input_data)

        # Assert
        assert result["params"]["uri"] == "file:///test.py"
        diagnostics = result["params"]["diagnostics"]
        assert isinstance(diagnostics, str)
        assert "array_len: 0" in diagnostics

    def test_mask_missing_fields(self) -> None:
        """Test masking handles missing fields gracefully."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        # Test cases with missing fields
        test_cases: list[dict[str, Any]] = [
            {"method": "test"},  # No params
            {"method": "test", "params": {}},  # Params without diagnostics
            {
                "method": "$/progress",
                "params": {"token": "test"},
            },  # Progress without value.items
        ]

        # Act & Assert - should not raise
        for input_data in test_cases:
            result = _mask_diagnostics(input_data)
            assert result is not None

    def test_mask_non_diagnostic_message(self) -> None:
        """Test that non-diagnostic messages pass through unchanged."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "method": "window/logMessage",
            "params": {
                "type": 3,
                "message": "Server initialized",
            },
        }
        expected = copy.deepcopy(input_data)

        # Act
        result = _mask_diagnostics(input_data)

        # Assert
        assert result == expected

    def test_mask_nested_diagnostic_structure(self) -> None:
        """Test masking of nested diagnostic structures."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "id": 1,
            "result": {
                "kind": "full",
                "items": [
                    {
                        "uri": "file:///a.py",
                        "diagnostics": [
                            {"range": {"start": {"line": 0}}, "message": "error1"},
                            {"range": {"start": {"line": 1}}, "message": "error2"},
                        ],
                    },
                    {
                        "uri": "file:///b.py",
                        "diagnostics": [
                            {"range": {"start": {"line": 5}}, "message": "error3"},
                        ],
                    },
                ],
            },
        }

        # Act
        result = _mask_diagnostics(input_data)

        # Assert
        # Top-level items should be masked
        items = result["result"]["items"]
        assert isinstance(items, str)
        assert "array_len: 2" in items


# =============================================================================
# 2. Unit Tests: Dual Logging in _handle_message()
# =============================================================================


class TestDualLoggingInHandleMessage:
    """Tests for dual logging behavior in _handle_message()."""

    @pytest.mark.asyncio
    async def test_handle_message_with_trace_enables_dual_logging(
        self, log_capture_handler: Any, mock_diagnostic_logger: MagicMock
    ) -> None:
        """Test that trace=True enables logging to both loggers."""
        # Arrange
        transport = StdioTransport(command="echo", trace=True)

        # Use a proper notification structure (not a response)
        message_with_diagnostics = {
            "jsonrpc": "2.0",
            "method": "textDocument/publishDiagnostics",
            "params": {
                "uri": "file:///test.py",
                "diagnostics": [{"message": "error"}],
            },
        }
        body = json.dumps(message_with_diagnostics).encode()

        # Act
        await transport._handle_message(body)

        # Assert - logger.debug should be called (masked output)
        log_output = log_capture_handler.stream.getvalue()
        assert "array_len:" in log_output

    @pytest.mark.asyncio
    async def test_handle_message_without_trace_no_logging(
        self, mock_diagnostic_logger: MagicMock
    ) -> None:
        """Test that trace=False disables debug logging."""
        # Arrange
        transport = StdioTransport(command="echo", trace=False)

        message_with_diagnostics = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "method": "textDocument/publishDiagnostics",
                "params": {
                    "uri": "file:///test.py",
                    "diagnostics": [{"message": "error"}],
                },
            },
        }
        body = json.dumps(message_with_diagnostics).encode()

        # Capture log output
        logger = logging.getLogger("llm_lsp_cli.lsp.transport")
        handler = logging.StreamHandler(StringIO())
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        original_level = logger.level
        logger.setLevel(logging.DEBUG)

        # Act
        await transport._handle_message(body)

        # Cleanup
        logger.removeHandler(handler)
        logger.setLevel(original_level)

        # Assert - no debug log output about the message content
        # (warning about unknown request is expected from routing logic)
        log_output = handler.stream.getvalue()
        # The key assertion: no "<--" debug log about message content
        assert "<--" not in log_output

    @pytest.mark.asyncio
    async def test_handle_message_routing_unaffected_by_masking(
        self, mock_diagnostic_logger: MagicMock
    ) -> None:
        """Test that message routing is unaffected by masking."""
        # Arrange
        transport = StdioTransport(command="echo", trace=True)

        handler_called = False
        received_params: dict[str, Any] = {}

        def notification_handler(params: dict[str, Any]) -> None:
            nonlocal handler_called, received_params
            handler_called = True
            received_params = params

        transport.on_notification("test/notification", notification_handler)

        message = {
            "method": "test/notification",
            "params": {"key": "value", "diagnostics": [{"message": "error"}]},
        }
        body = json.dumps(message).encode()

        # Act
        await transport._handle_message(body)

        # Assert - handler receives original (unmasked) data
        assert handler_called
        assert "diagnostics" in received_params
        assert isinstance(received_params["diagnostics"], list)


# =============================================================================
# 3. Extended Verification: Helper Functions
# =============================================================================


class TestMaskArrayHelper:
    """Tests for _mask_array() helper function."""

    def test_mask_array_masks_present_array(self) -> None:
        """Test _mask_array masks a present array."""
        from llm_lsp_cli.lsp.transport import _mask_array

        target: dict[str, Any] = {"key": [1, 2, 3]}
        _mask_array(target, "key", "test")

        assert target["key"] == "... (test_len: 3)"

    def test_mask_array_ignores_missing_key(self) -> None:
        """Test _mask_array ignores missing key."""
        from llm_lsp_cli.lsp.transport import _mask_array

        target: dict[str, Any] = {"other": "value"}
        _mask_array(target, "missing", "test")

        assert target == {"other": "value"}

    def test_mask_array_ignores_non_array_value(self) -> None:
        """Test _mask_array ignores non-array value."""
        from llm_lsp_cli.lsp.transport import _mask_array

        target: dict[str, Any] = {"key": "not an array"}
        _mask_array(target, "key", "test")

        assert target["key"] == "not an array"

    def test_mask_array_default_description(self) -> None:
        """Test _mask_array uses default description."""
        from llm_lsp_cli.lsp.transport import _mask_array

        target: dict[str, Any] = {"items": [1, 2]}
        _mask_array(target, "items")

        assert target["items"] == "... (array_len: 2)"


class TestMaskProgressItemsHelper:
    """Tests for _mask_progress_items() helper function."""

    def test_mask_progress_items_with_valid_params(self) -> None:
        """Test _mask_progress_items with valid params structure."""
        from llm_lsp_cli.lsp.transport import _mask_progress_items

        params: dict[str, Any] = {
            "token": "test",
            "value": {"items": [{"diagnostics": []}, {"diagnostics": []}]},
        }
        _mask_progress_items(params)

        assert params["value"]["items"] == "... (array_len: 2)"

    def test_mask_progress_items_missing_value(self) -> None:
        """Test _mask_progress_items with missing value key."""
        from llm_lsp_cli.lsp.transport import _mask_progress_items

        params: dict[str, Any] = {"token": "test"}
        _mask_progress_items(params)

        assert params == {"token": "test"}

    def test_mask_progress_items_missing_items(self) -> None:
        """Test _mask_progress_items with missing items in value."""
        from llm_lsp_cli.lsp.transport import _mask_progress_items

        params: dict[str, Any] = {"token": "test", "value": {"other": "data"}}
        _mask_progress_items(params)

        assert params["value"] == {"other": "data"}

    def test_mask_progress_items_non_dict_params(self) -> None:
        """Test _mask_progress_items with non-dict params."""
        from llm_lsp_cli.lsp.transport import _mask_progress_items

        _mask_progress_items("not a dict")  # type: ignore
        _mask_progress_items(None)  # type: ignore


class TestMaskDiagnosticsParamsHelper:
    """Tests for _mask_diagnostics_params() helper function."""

    def test_mask_diagnostics_params_with_valid_params(self) -> None:
        """Test _mask_diagnostics_params with valid params."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics_params

        params: dict[str, Any] = {
            "uri": "file:///test.py",
            "diagnostics": [{"message": "error1"}, {"message": "error2"}],
        }
        _mask_diagnostics_params(params)

        assert params["diagnostics"] == "... (array_len: 2)"
        assert params["uri"] == "file:///test.py"

    def test_mask_diagnostics_params_missing_diagnostics(self) -> None:
        """Test _mask_diagnostics_params with missing diagnostics."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics_params

        params: dict[str, Any] = {"uri": "file:///test.py"}
        _mask_diagnostics_params(params)

        assert params == {"uri": "file:///test.py"}

    def test_mask_diagnostics_params_non_dict_params(self) -> None:
        """Test _mask_diagnostics_params with non-dict params."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics_params

        _mask_diagnostics_params("not a dict")  # type: ignore
        _mask_diagnostics_params(None)  # type: ignore


class TestMaskResultItemsHelper:
    """Tests for _mask_result_items() helper function."""

    def test_mask_result_items_with_valid_result(self) -> None:
        """Test _mask_result_items with valid result structure."""
        from llm_lsp_cli.lsp.transport import _mask_result_items

        result_data: dict[str, Any] = {"items": [{"uri": "a.py"}, {"uri": "b.py"}]}
        _mask_result_items(result_data)

        assert result_data["items"] == "... (array_len: 2)"

    def test_mask_result_items_missing_items(self) -> None:
        """Test _mask_result_items with missing items."""
        from llm_lsp_cli.lsp.transport import _mask_result_items

        result_data: dict[str, Any] = {"other": "data"}
        _mask_result_items(result_data)

        assert result_data == {"other": "data"}

    def test_mask_result_items_non_dict_result(self) -> None:
        """Test _mask_result_items with non-dict result."""
        from llm_lsp_cli.lsp.transport import _mask_result_items

        _mask_result_items("not a dict")  # type: ignore
        _mask_result_items(None)  # type: ignore


# =============================================================================
# 4. Extended Verification: Edge Cases
# =============================================================================


class TestMaskDiagnosticsEdgeCases:
    """Extended edge case tests for _mask_diagnostics()."""

    def test_mask_multiple_diagnostic_patterns_in_same_message(self) -> None:
        """Test masking when multiple diagnostic patterns could apply."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        # Message with both method-based masking AND result.items
        input_data: dict[str, Any] = {
            "id": 1,
            "method": "textDocument/publishDiagnostics",
            "params": {"uri": "file:///test.py", "diagnostics": [{"message": "error"}]},
            "result": {"items": [{"uri": "a.py"}]},
        }

        result = _mask_diagnostics(input_data)

        # params.diagnostics should be masked (method-based)
        assert result["params"]["diagnostics"] == "... (array_len: 1)"
        # result.items should also be masked
        assert result["result"]["items"] == "... (array_len: 1)"

    def test_mask_progress_with_empty_items_array(self) -> None:
        """Test masking $/progress with empty items array."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "method": "$/progress",
            "params": {"token": "test", "value": {"items": []}},
        }

        result = _mask_diagnostics(input_data)

        assert result["params"]["value"]["items"] == "... (array_len: 0)"

    def test_mask_with_non_list_items_does_not_mask(self) -> None:
        """Test that non-list items are not masked."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "id": 1,
            "result": {"items": "already a string"},
        }

        result = _mask_diagnostics(input_data)

        assert result["result"]["items"] == "already a string"

    def test_mask_with_deeply_nested_structure(self) -> None:
        """Test masking with deeply nested diagnostic structure."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "method": "$/progress",
            "params": {
                "token": "wdi",
                "value": {
                    "items": [
                        {
                            "uri": "file:///a.py",
                            "diagnostics": [
                                {
                                    "range": {
                                        "start": {"line": 0, "character": 0},
                                        "end": {"line": 0, "character": 10},
                                    },
                                    "severity": 1,
                                    "code": "E001",
                                    "source": "pyright",
                                    "message": "Type error",
                                    "relatedInformation": [
                                        {"location": {"uri": "file:///b.py"}, "message": "ref"}
                                    ],
                                }
                            ],
                        }
                    ]
                },
            },
        }

        result = _mask_diagnostics(input_data)

        # Top-level items should be masked
        assert isinstance(result["params"]["value"]["items"], str)
        assert "array_len: 1" in result["params"]["value"]["items"]
        # Original structure should be preserved in input
        msg = input_data["params"]["value"]["items"][0]["diagnostics"][0]["message"]
        assert msg == "Type error"

    def test_mask_preserves_jsonrpc_version(self) -> None:
        """Test that jsonrpc version is preserved."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": "textDocument/publishDiagnostics",
            "params": {"diagnostics": [{"message": "error"}]},
        }

        result = _mask_diagnostics(input_data)

        assert result["jsonrpc"] == "2.0"

    def test_mask_preserves_id_field(self) -> None:
        """Test that id field is preserved."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "id": 999,
            "result": {"items": [{"uri": "a.py"}]},
        }

        result = _mask_diagnostics(input_data)

        assert result["id"] == 999

    def test_mask_with_unknown_method_passes_through(self) -> None:
        """Test that unknown method messages pass through (except result.items)."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "method": "unknown/method",
            "params": {"data": [1, 2, 3]},
        }

        result = _mask_diagnostics(input_data)

        # Unknown method - params should not be masked
        assert result["params"]["data"] == [1, 2, 3]

    def test_mask_progress_value_not_dict(self) -> None:
        """Test $/progress when value is not a dict."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "method": "$/progress",
            "params": {"token": "test", "value": "not a dict"},
        }

        result = _mask_diagnostics(input_data)

        # Should not crash, value should be preserved
        assert result["params"]["value"] == "not a dict"

    def test_mask_result_items_in_result_with_additional_keys(self) -> None:
        """Test result.items masking when result has other keys."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "id": 1,
            "result": {
                "kind": "full",
                "items": [{"uri": "a.py"}],
                "other": "data",
            },
        }

        result = _mask_diagnostics(input_data)

        assert result["result"]["items"] == "... (array_len: 1)"
        assert result["result"]["kind"] == "full"
        assert result["result"]["other"] == "data"


# =============================================================================
# 5. Test Class 7: _classify_method() and LogCategory
# =============================================================================


class TestLogCategoryEnum:
    """Tests for LogCategory enum and _classify_method() function."""

    def test_skip_progress(self) -> None:
        from llm_lsp_cli.lsp.transport import LogCategory, _classify_method

        assert _classify_method("$/progress") == LogCategory.SKIP

    def test_daemon_window_log_message(self) -> None:
        from llm_lsp_cli.lsp.transport import LogCategory, _classify_method

        assert _classify_method("window/logMessage") == LogCategory.DAEMON

    def test_daemon_workspace_configuration(self) -> None:
        from llm_lsp_cli.lsp.transport import LogCategory, _classify_method

        assert _classify_method("workspace/configuration") == LogCategory.DAEMON

    def test_daemon_client_register_capability(self) -> None:
        from llm_lsp_cli.lsp.transport import LogCategory, _classify_method

        assert _classify_method("client/registerCapability") == LogCategory.DAEMON

    def test_mask_didopen(self) -> None:
        from llm_lsp_cli.lsp.transport import LogCategory, _classify_method

        assert _classify_method("textDocument/didOpen") == LogCategory.MASK

    def test_mask_didchange(self) -> None:
        from llm_lsp_cli.lsp.transport import LogCategory, _classify_method

        assert _classify_method("textDocument/didChange") == LogCategory.MASK

    def test_unknown_defaults_to_mask(self) -> None:
        from llm_lsp_cli.lsp.transport import LogCategory, _classify_method

        assert _classify_method("unknown/randomMethod") == LogCategory.MASK

    @pytest.mark.parametrize(
        "method",
        ["$/progress"],
    )
    def test_all_skip_methods(self, method: str) -> None:
        from llm_lsp_cli.lsp.transport import LogCategory, _classify_method

        assert _classify_method(method) == LogCategory.SKIP

    @pytest.mark.parametrize(
        "method",
        ["window/logMessage", "workspace/configuration", "client/registerCapability"],
    )
    def test_all_daemon_methods(self, method: str) -> None:
        from llm_lsp_cli.lsp.transport import LogCategory, _classify_method

        assert _classify_method(method) == LogCategory.DAEMON


# =============================================================================
# 6. Test Class 8: _mask_text_content()
# =============================================================================


class TestMaskTextContent:
    """Tests for _mask_text_content() helper function."""

    def test_didopen_text_masked(self) -> None:
        from llm_lsp_cli.lsp.transport import _mask_text_content

        params: dict[str, Any] = {
            "textDocument": {
                "uri": "file:///a.py",
                "text": "def foo():\n    pass\n",
                "version": 1,
            },
        }
        _mask_text_content(params)
        assert params["textDocument"]["text"] == "... (text_len: 20)"
        assert params["textDocument"]["uri"] == "file:///a.py"  # URI preserved

    def test_didchange_text_masked(self) -> None:
        from llm_lsp_cli.lsp.transport import _mask_text_content

        params: dict[str, Any] = {
            "textDocument": {"uri": "file:///a.py", "version": 2},
            "contentChanges": [{"text": "hello world"}],
        }
        _mask_text_content(params)
        assert params["contentChanges"][0]["text"] == "... (text_len: 11)"

    def test_didchange_multiple_changes_masked(self) -> None:
        from llm_lsp_cli.lsp.transport import _mask_text_content

        params: dict[str, Any] = {
            "contentChanges": [
                {"text": "abc"},
                {"text": "xyz123"},
            ],
        }
        _mask_text_content(params)
        assert params["contentChanges"][0]["text"] == "... (text_len: 3)"
        assert params["contentChanges"][1]["text"] == "... (text_len: 6)"

    def test_empty_content_changes(self) -> None:
        from llm_lsp_cli.lsp.transport import _mask_text_content

        params: dict[str, Any] = {"contentChanges": []}
        _mask_text_content(params)
        assert params["contentChanges"] == []

    def test_missing_text_document(self) -> None:
        from llm_lsp_cli.lsp.transport import _mask_text_content

        params: dict[str, Any] = {"other": "data"}
        _mask_text_content(params)
        assert params == {"other": "data"}

    def test_missing_text_field_in_text_document(self) -> None:
        from llm_lsp_cli.lsp.transport import _mask_text_content

        params: dict[str, Any] = {"textDocument": {"uri": "file:///a.py"}}
        _mask_text_content(params)
        assert params["textDocument"] == {"uri": "file:///a.py"}

    def test_non_string_text_field(self) -> None:
        from llm_lsp_cli.lsp.transport import _mask_text_content

        params: dict[str, Any] = {"textDocument": {"text": 12345}}
        _mask_text_content(params)
        assert params["textDocument"]["text"] == 12345  # not masked

    def test_non_dict_params(self) -> None:
        from llm_lsp_cli.lsp.transport import _mask_text_content

        # Should not crash
        _mask_text_content("not a dict")  # type: ignore
        _mask_text_content(None)  # type: ignore


# =============================================================================
# 7. Test Class 9: _mask_diagnostics() with text fields
# =============================================================================


class TestMaskDiagnosticsTextFields:
    """Tests for _mask_diagnostics() extended with text content masking."""

    def test_didopen_masked_via_mask_diagnostics(self) -> None:
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "file:///test.py",
                    "text": "def hello():\n    print('world')\n",
                    "version": 1,
                }
            },
        }
        result = _mask_diagnostics(input_data)
        assert result["params"]["textDocument"]["text"] == "... (text_len: 32)"
        assert result["params"]["textDocument"]["uri"] == "file:///test.py"

    def test_didchange_masked_via_mask_diagnostics(self) -> None:
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "method": "textDocument/didChange",
            "params": {
                "textDocument": {"uri": "file:///test.py", "version": 2},
                "contentChanges": [{"text": "new content here"}],
            },
        }
        result = _mask_diagnostics(input_data)
        assert result["params"]["contentChanges"][0]["text"] == "... (text_len: 16)"

    def test_didopen_does_not_mutate_input(self) -> None:
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        original_text = "def hello():\n    print('world')\n"
        input_data: dict[str, Any] = {
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "file:///test.py",
                    "text": original_text,
                    "version": 1,
                }
            },
        }
        original_copy = copy.deepcopy(input_data)
        result = _mask_diagnostics(input_data)
        assert input_data == original_copy  # input not mutated
        assert result["params"]["textDocument"]["text"] != original_text  # result is masked

    def test_didchange_combined_arrays_and_text(self) -> None:
        """Test didChange with both text content and extra array fields."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "method": "textDocument/didChange",
            "params": {
                "textDocument": {"uri": "file:///test.py", "version": 2},
                "contentChanges": [{"text": "code here"}],
                "extraArray": [1, 2, 3, 4],
            },
        }
        result = _mask_diagnostics(input_data)
        # Text should be masked
        assert result["params"]["contentChanges"][0]["text"] == "... (text_len: 9)"
        # extraArray is not a known masked field, so it passes through
        assert result["params"]["extraArray"] == [1, 2, 3, 4]


# =============================================================================
# 8. Test Class 10: Three-Way Routing in _handle_message()
# =============================================================================


class TestThreeWayRouting:
    """Tests for three-way routing in _handle_message() via LogCategory."""

    @pytest.mark.asyncio
    async def test_skip_progress_only_diagnostic_logger(
        self, transport_with_trace: StdioTransport, mock_both_loggers: Any
    ) -> None:
        """$/progress should only go to diagnostic logger, not daemon logger."""
        mock_daemon, mock_diag = mock_both_loggers
        message = {
            "jsonrpc": "2.0",
            "method": "$/progress",
            "params": {"token": "t", "value": {"items": []}},
        }
        body = json.dumps(message).encode()
        await transport_with_trace._handle_message(body)
        mock_diag.debug.assert_called_once()
        # Check daemon logger was not called with the message data
        daemon_calls = [str(c) for c in mock_daemon.debug.call_args_list]
        assert not any("<--" in c for c in daemon_calls), f"Unexpected daemon log: {daemon_calls}"

    @pytest.mark.asyncio
    async def test_daemon_window_log_message_only_daemon_logger(
        self, transport_with_trace: StdioTransport, mock_both_loggers: Any
    ) -> None:
        """window/logMessage should only go to daemon logger."""
        mock_daemon, mock_diag = mock_both_loggers
        message = {
            "jsonrpc": "2.0",
            "method": "window/logMessage",
            "params": {"type": 3, "message": "Server ready"},
        }
        body = json.dumps(message).encode()
        await transport_with_trace._handle_message(body)
        daemon_calls = [str(c) for c in mock_daemon.debug.call_args_list]
        assert any("<--" in c for c in daemon_calls), f"Expected daemon log missing: {daemon_calls}"
        diag_calls = [str(c) for c in mock_diag.debug.call_args_list]
        assert not any("<--" in c for c in diag_calls), f"Unexpected diag log: {diag_calls}"

    @pytest.mark.asyncio
    async def test_daemon_workspace_configuration_only_daemon_logger(
        self, transport_with_trace: StdioTransport, mock_both_loggers: Any
    ) -> None:
        """workspace/configuration should only go to daemon logger."""
        mock_daemon, mock_diag = mock_both_loggers
        message = {
            "jsonrpc": "2.0",
            "method": "workspace/configuration",
            "params": {"items": [{"scopeUri": "", "section": "pyright"}]},
        }
        body = json.dumps(message).encode()
        await transport_with_trace._handle_message(body)
        daemon_calls = [str(c) for c in mock_daemon.debug.call_args_list]
        assert any("<--" in c for c in daemon_calls), f"Expected daemon log missing: {daemon_calls}"
        diag_calls = [str(c) for c in mock_diag.debug.call_args_list]
        assert not any("<--" in c for c in diag_calls), f"Unexpected diag log: {diag_calls}"

    @pytest.mark.asyncio
    async def test_mask_didchange_both_loggers_masked_text(
        self, transport_with_trace: StdioTransport, mock_both_loggers: Any
    ) -> None:
        """textDocument/didChange should go to both loggers with masked text in daemon."""
        mock_daemon, mock_diag = mock_both_loggers
        message = {
            "jsonrpc": "2.0",
            "method": "textDocument/didChange",
            "params": {
                "textDocument": {"uri": "file:///a.py", "version": 2},
                "contentChanges": [{"text": "x" * 100}],
            },
        }
        body = json.dumps(message).encode()
        await transport_with_trace._handle_message(body)
        mock_daemon.debug.assert_called()
        mock_diag.debug.assert_called_once()
        # Verify daemon.log output contains masked text (check all calls, not just last)
        daemon_args = [str(c) for c in mock_daemon.debug.call_args_list]
        assert any("... (text_len:" in c for c in daemon_args)
        all_daemon = " ".join(daemon_args)
        assert "x" * 100 not in all_daemon  # raw text NOT in daemon.log

    @pytest.mark.asyncio
    async def test_mask_unknown_method_both_loggers(
        self, transport_with_trace: StdioTransport, mock_both_loggers: Any
    ) -> None:
        """Unknown methods should be treated as MASK (both loggers)."""
        mock_daemon, mock_diag = mock_both_loggers
        message = {
            "jsonrpc": "2.0",
            "method": "unknown/method",
            "params": {"data": "value"},
        }
        body = json.dumps(message).encode()
        await transport_with_trace._handle_message(body)
        mock_daemon.debug.assert_called()
        mock_diag.debug.assert_called_once()

    @pytest.mark.asyncio
    async def test_routing_unaffected_by_classification(
        self, mock_both_loggers: Any
    ) -> None:
        """Message routing should still deliver original (unmasked) params."""
        mock_daemon, mock_diag = mock_both_loggers
        transport = StdioTransport(command="echo", trace=True)
        handler_called = False
        received_params: dict[str, Any] = {}

        def notification_handler(params: dict[str, Any]) -> None:
            nonlocal handler_called, received_params
            handler_called = True
            received_params = params

        transport.on_notification("textDocument/didOpen", notification_handler)
        message = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "file:///test.py",
                    "text": "def foo():\n    pass\n",
                    "version": 1,
                }
            },
        }
        body = json.dumps(message).encode()
        await transport._handle_message(body)
        # Handler receives original text, not masked
        assert handler_called
        assert received_params["textDocument"]["text"] == "def foo():\n    pass\n"


# =============================================================================
# 9. Test Class 11: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Cross-cutting edge cases spanning multiple functions."""

    def test_classify_empty_string(self) -> None:
        from llm_lsp_cli.lsp.transport import LogCategory, _classify_method

        assert _classify_method("") == LogCategory.MASK

    @pytest.mark.asyncio
    async def test_handle_message_no_method_field(
        self, transport_with_trace: StdioTransport, mock_both_loggers: Any
    ) -> None:
        """Response messages (no method) should not crash the routing logic."""
        mock_daemon, mock_diag = mock_both_loggers
        message = {"jsonrpc": "2.0", "id": 1, "result": {"items": []}}
        body = json.dumps(message).encode()
        await transport_with_trace._handle_message(body)
        # No crash - the key assertion
        # "" classifies as MASK, so both loggers are called
        mock_daemon.debug.assert_called()
        mock_diag.debug.assert_called_once()

    def test_mask_text_content_preserves_other_fields(self) -> None:
        """Only text is masked; all other textDocument fields preserved."""
        from llm_lsp_cli.lsp.transport import _mask_text_content

        params: dict[str, Any] = {
            "textDocument": {
                "uri": "file:///test.py",
                "languageId": "python",
                "version": 5,
                "text": "some code",
            }
        }
        _mask_text_content(params)
        assert params["textDocument"]["uri"] == "file:///test.py"
        assert params["textDocument"]["languageId"] == "python"
        assert params["textDocument"]["version"] == 5
        assert params["textDocument"]["text"] == "... (text_len: 9)"

    def test_didchange_with_non_dict_content_change(self) -> None:
        """contentChanges containing non-dict elements should not crash."""
        from llm_lsp_cli.lsp.transport import _mask_text_content

        params: dict[str, Any] = {
            "contentChanges": ["not a dict", {"text": "real"}],
        }
        _mask_text_content(params)
        # Non-dict element skipped; real dict masked
        assert params["contentChanges"][0] == "not a dict"
        assert params["contentChanges"][1]["text"] == "... (text_len: 4)"

    def test_skip_method_with_empty_params(self) -> None:
        """$/progress with empty params should still classify as SKIP."""
        from llm_lsp_cli.lsp.transport import LogCategory, _classify_method

        assert _classify_method("$/progress") == LogCategory.SKIP
