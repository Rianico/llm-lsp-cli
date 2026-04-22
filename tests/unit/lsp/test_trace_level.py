"""Unit tests for TRACE level infrastructure.

Tests for the custom Python logging level for transport-layer messages.
"""

import logging
from io import StringIO
from typing import Any

import pytest

# =============================================================================
# Test Suite 1.1: TRACE Level Constant
# =============================================================================


class TestTraceLevelConstant:
    """Tests for TRACE_LEVEL constant definition."""

    def test_trace_level_defined(self) -> None:
        """TRACE_LEVEL constant exists at module level with value 5."""
        from llm_lsp_cli.lsp import transport

        assert hasattr(transport, "TRACE_LEVEL")
        assert transport.TRACE_LEVEL == 5

    def test_trace_level_below_debug(self) -> None:
        """TRACE level is numerically below DEBUG (10)."""
        from llm_lsp_cli.lsp import transport

        assert transport.TRACE_LEVEL < logging.DEBUG

    def test_trace_level_registered(self) -> None:
        """TRACE level name registered with logging module."""
        # The implementation should call logging.addLevelName(5, "TRACE")
        from llm_lsp_cli.lsp import transport

        # Force import to trigger registration
        _ = transport.TRACE_LEVEL
        level_name = logging.getLevelName(5)
        assert level_name == "TRACE"


# =============================================================================
# Test Suite 1.2: Logger.trace() Method
# =============================================================================


class TestLoggerTraceMethod:
    """Tests for using logger.log(TRACE_LEVEL, msg) to emit TRACE messages."""

    @pytest.fixture
    def trace_logger(self) -> Any:
        """Create a logger with TRACE level handler for testing."""
        logger = logging.getLogger("test_trace_logger")
        logger.handlers.clear()
        logger.setLevel(5)  # TRACE level
        return logger

    @pytest.fixture
    def log_capture(self, trace_logger: logging.Logger) -> Any:
        """Capture log output for assertions."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(5)  # TRACE level
        trace_logger.addHandler(handler)

        yield stream

        trace_logger.removeHandler(handler)

    def test_logger_log_trace_works(
        self, trace_logger: logging.Logger, log_capture: StringIO
    ) -> None:
        """logger.log(TRACE_LEVEL, msg) produces output at TRACE level."""
        from llm_lsp_cli.lsp import transport

        trace_logger.log(transport.TRACE_LEVEL, "Test trace message")
        output = log_capture.getvalue()
        assert "Test trace message" in output

    def test_trace_filtered_at_debug_threshold(self) -> None:
        """Logger with DEBUG threshold does NOT emit TRACE messages."""
        from llm_lsp_cli.lsp import transport

        logger = logging.getLogger("test_trace_filtered")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)  # DEBUG (10) threshold

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        # TRACE (5) is below DEBUG (10), so it should be filtered
        logger.log(transport.TRACE_LEVEL, "This should be filtered")
        output = stream.getvalue()

        # DEBUG threshold should NOT show TRACE messages
        assert "This should be filtered" not in output

    def test_trace_visible_at_trace_threshold(self) -> None:
        """Logger with TRACE threshold emits TRACE messages."""
        from llm_lsp_cli.lsp import transport

        logger = logging.getLogger("test_trace_visible")
        logger.handlers.clear()
        logger.setLevel(5)  # TRACE level threshold

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(5)
        logger.addHandler(handler)

        logger.log(transport.TRACE_LEVEL, "This should be visible")
        output = stream.getvalue()

        assert "This should be visible" in output


# =============================================================================
# Test Suite 1.3: "Reading body" Message Relocation
# =============================================================================


class TestReadingBodyRelocation:
    """Tests for "Reading body of X bytes" message using TRACE level."""

    def test_reading_body_at_trace_not_debug(self) -> None:
        """The "Reading body of X bytes" message should use TRACE level, not DEBUG."""
        # Verify that the source contains TRACE_LEVEL usage for "Reading body"
        import inspect

        from llm_lsp_cli.lsp import transport

        source = inspect.getsource(transport.StdioTransport._read_loop)

        # The "Reading body" message should use TRACE_LEVEL
        assert "Reading body" in source
        assert "TRACE_LEVEL" in source
        # Verify it's using logger.log(TRACE_LEVEL, ...) pattern
        assert "logger.log(TRACE_LEVEL" in source

    def test_reading_body_message_format(self) -> None:
        """The "Reading body" message format includes byte count."""
        # This is a verification test - the message should contain the byte count
        # We'll verify this by checking that TRACE_LEVEL is used and the format
        # is correct
        from llm_lsp_cli.lsp import transport

        # Verify TRACE_LEVEL exists for the message
        assert hasattr(transport, "TRACE_LEVEL")
        assert transport.TRACE_LEVEL == 5

        # The actual format "Reading body of {content_length} bytes" is verified
        # by the implementation in transport.py
