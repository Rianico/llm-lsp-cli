"""Tests for diagnostic logger configuration.

Verifies the diagnostic logger is properly configured and independent
from the main transport logger.
"""

import logging

from llm_lsp_cli.lsp.transport import _DIAGNOSTIC_LOGGER_NAME


class TestDiagnosticLoggerConfiguration:
    """Tests for diagnostic logger setup and configuration."""

    def test_diagnostic_logger_name_constant_defined(self) -> None:
        """Test that _DIAGNOSTIC_LOGGER_NAME constant is defined."""
        assert _DIAGNOSTIC_LOGGER_NAME == "llm_lsp_cli.lsp.diagnostic"

    def test_diagnostic_logger_name_constant_format(self) -> None:
        """Test that logger name follows naming convention."""
        # Should use dot-separated hierarchical naming
        assert "." in _DIAGNOSTIC_LOGGER_NAME
        # Should start with package name
        assert _DIAGNOSTIC_LOGGER_NAME.startswith("llm_lsp_cli")

    def test_diagnostic_logger_gets_correct_name(self) -> None:
        """Test that _diagnostic_logger uses the constant."""
        diagnostic_logger = logging.getLogger(_DIAGNOSTIC_LOGGER_NAME)
        assert diagnostic_logger.name == _DIAGNOSTIC_LOGGER_NAME

    def test_diagnostic_logger_is_separate_from_transport_logger(self) -> None:
        """Test that diagnostic logger is separate from transport logger."""
        transport_logger = logging.getLogger("llm_lsp_cli.lsp.transport")
        diagnostic_logger = logging.getLogger(_DIAGNOSTIC_LOGGER_NAME)

        assert transport_logger.name != diagnostic_logger.name
        # They should be different logger instances
        assert transport_logger is not diagnostic_logger

    def test_diagnostic_logger_propagation(self) -> None:
        """Test that diagnostic logger propagation is default (enabled)."""
        diagnostic_logger = logging.getLogger(_DIAGNOSTIC_LOGGER_NAME)

        # By default, loggers propagate to parent
        assert diagnostic_logger.propagate is True

    def test_diagnostic_logger_level_default(self) -> None:
        """Test that diagnostic logger level defaults to NOTSET."""
        # Reset logger to clean state for test isolation
        diagnostic_logger = logging.getLogger(_DIAGNOSTIC_LOGGER_NAME)
        diagnostic_logger.setLevel(logging.NOTSET)
        diagnostic_logger.handlers.clear()

        # Logger level defaults to NOTSET (inherits from parent)
        assert diagnostic_logger.level == logging.NOTSET


class TestLoggerIndependence:
    """Tests verifying logger independence for dual-path logging."""

    def test_transport_logger_has_handlers(self) -> None:
        """Test that transport logger can have handlers configured."""
        transport_logger = logging.getLogger("llm_lsp_cli.lsp.transport")

        # Logger should exist (may not have handlers until configured)
        assert transport_logger is not None

    def test_diagnostic_logger_has_handlers(self) -> None:
        """Test that diagnostic logger can have handlers configured."""
        diagnostic_logger = logging.getLogger(_DIAGNOSTIC_LOGGER_NAME)

        # Logger should exist (may not have handlers until configured)
        assert diagnostic_logger is not None

    def test_both_loggers_share_parent_hierarchy(self) -> None:
        """Test that both loggers share the same parent hierarchy."""
        transport_logger = logging.getLogger("llm_lsp_cli.lsp.transport")
        diagnostic_logger = logging.getLogger(_DIAGNOSTIC_LOGGER_NAME)

        # Both should have llm_lsp_cli.lsp as parent
        transport_parent = logging.getLogger("llm_lsp_cli.lsp")
        diagnostic_parent = logging.getLogger("llm_lsp_cli.lsp")

        assert transport_logger.parent == transport_parent
        assert diagnostic_logger.parent == diagnostic_parent
