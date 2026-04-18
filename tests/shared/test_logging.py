"""Tests for LogContext and StructuredLogger."""

import logging
from io import StringIO

from llm_lsp_cli.shared.logging import LogContext, StructuredLogger


class TestStructuredLogger:
    """Test suite for StructuredLogger and LogContext."""

    def test_logger_includes_context(self) -> None:
        """StructuredLogger includes context in log entries."""
        # Arrange
        output = StringIO()
        handler = logging.StreamHandler(output)
        logger = StructuredLogger("test", handler)

        context = LogContext(
            request_id="test-123",
            component="TestComponent",
        )

        # Act
        logger.info("Test message", context=context)

        # Assert
        log_output = output.getvalue()
        assert "test-123" in log_output
        assert "TestComponent" in log_output

    def test_logger_exception_logging(self) -> None:
        """StructuredLogger logs exceptions with stack traces."""
        # Arrange
        output = StringIO()
        handler = logging.StreamHandler(output)
        logger = StructuredLogger("test", handler)

        context = LogContext(request_id="test-456")

        # Act
        try:
            raise ValueError("Test error")
        except ValueError:
            logger.exception("Error occurred", context=context)

        # Assert
        log_output = output.getvalue()
        assert "Error occurred" in log_output
        assert "Traceback" in log_output
        assert "ValueError" in log_output

    def test_log_context_serialization(self) -> None:
        """LogContext serializes to dictionary correctly."""
        # Arrange
        context = LogContext(
            request_id="test-789",
            component="TestComponent",
            metadata={"key": "value"},
        )

        # Act
        data = context.to_dict()

        # Assert
        assert data["request_id"] == "test-789"
        assert data["component"] == "TestComponent"
        assert data["metadata"]["key"] == "value"

    def test_logger_request_id_propagation(self) -> None:
        """StructuredLogger propagates request ID through calls."""
        # Arrange
        output = StringIO()
        handler = logging.StreamHandler(output)
        logger = StructuredLogger("test", handler)

        context = LogContext(request_id="propagate-test")

        # Act
        logger.info("First message", context=context)
        logger.debug("Second message", context=context)
        logger.warning("Third message", context=context)

        # Assert
        log_output = output.getvalue()
        lines = log_output.strip().split("\n")
        for line in lines:
            assert "propagate-test" in line
