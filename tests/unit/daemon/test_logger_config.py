"""Unit tests for _configure_logger_levels helper in daemon.py."""

import logging

import pytest

from llm_lsp_cli.daemon import _configure_logger_levels
from llm_lsp_cli.lsp.transport import TRACE_LEVEL


@pytest.fixture
def reset_loggers():
    """Reset all logger levels to NOTSET before and after each test.

    Using NOTSET ensures loggers inherit from their parents/root logger.
    """
    loggers = [
        "",  # root
        "llm-lsp-cli",
        "llm-lsp-cli.daemon",
        "llm_lsp_cli",
        "llm_lsp_cli.lsp",
        "llm_lsp_cli.lsp.transport",
    ]
    for name in loggers:
        logging.getLogger(name).setLevel(logging.NOTSET)
    yield
    for name in loggers:
        logging.getLogger(name).setLevel(logging.NOTSET)


class TestConfigureLoggerLevels:
    """Tests for _configure_logger_levels helper function."""

    def test_debug_mode_sets_debug_on_all_package_loggers(self, reset_loggers):  # noqa: ARG002
        """When trace=False, should set DEBUG on root and all package loggers."""
        _configure_logger_levels(trace=False)

        assert logging.getLogger().level == logging.DEBUG
        assert logging.getLogger("llm-lsp-cli").level == logging.DEBUG
        assert logging.getLogger("llm_lsp_cli").level == logging.DEBUG
        assert logging.getLogger("llm_lsp_cli.lsp").level == logging.DEBUG

    def test_trace_mode_sets_trace_on_transport_logger(self, reset_loggers):  # noqa: ARG002
        """When trace=True, should set TRACE_LEVEL on transport logger."""
        _configure_logger_levels(trace=True)

        assert logging.getLogger().level == logging.DEBUG
        assert logging.getLogger("llm-lsp-cli").level == logging.DEBUG
        assert logging.getLogger("llm_lsp_cli").level == logging.DEBUG
        assert logging.getLogger("llm_lsp_cli.lsp").level == logging.DEBUG
        assert logging.getLogger("llm_lsp_cli.lsp.transport").level == TRACE_LEVEL

    def test_trace_mode_overrides_transport_logger_level(self, reset_loggers):  # noqa: ARG002
        """When trace=True, TRACE_LEVEL should be set on transport (not DEBUG)."""
        _configure_logger_levels(trace=True)

        # Transport logger should have TRACE_LEVEL, not DEBUG
        transport_logger = logging.getLogger("llm_lsp_cli.lsp.transport")
        assert transport_logger.level == TRACE_LEVEL
        assert transport_logger.level != logging.DEBUG

    def test_each_logger_configured_only_once(self, reset_loggers):  # noqa: ARG002
        """Verify no duplicate logger.setLevel calls (the bug being fixed)."""
        import unittest.mock as mock

        # Track calls to setLevel for each logger
        call_counts = {}

        original_get_logger = logging.getLogger

        def tracking_get_logger(name=None):
            logger = original_get_logger(name)
            original_set_level = logger.setLevel

            def counting_set_level(level):
                key = name or "root"
                call_counts[key] = call_counts.get(key, 0) + 1
                return original_set_level(level)

            logger.setLevel = counting_set_level
            return logger

        with mock.patch.object(logging, "getLogger", tracking_get_logger):
            _configure_logger_levels(trace=True)

        # Each logger should be configured exactly once
        expected_loggers = [
            "root", "llm-lsp-cli", "llm_lsp_cli", "llm_lsp_cli.lsp", "llm_lsp_cli.lsp.transport"
        ]
        for logger_name in expected_loggers:
            count = call_counts.get(logger_name, 0)
            assert count == 1, (
                f"Logger {logger_name} was configured {count} times, expected 1"
            )
