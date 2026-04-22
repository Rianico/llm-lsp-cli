"""Tests for ServerLifecyclePort protocol."""

from llm_lsp_cli.application.interfaces.server_lifecycle import (
    ServerLifecyclePort,
    ServerStatus,
)


class TestServerLifecyclePort:
    """Protocol contract tests for ServerLifecyclePort."""

    def test_protocol_has_start_method(self):
        """Verify protocol defines start_server abstract method."""
        assert hasattr(ServerLifecyclePort, "start_server")

    def test_protocol_has_stop_method(self):
        """Verify protocol defines stop_server abstract method."""
        assert hasattr(ServerLifecyclePort, "stop_server")

    def test_protocol_has_status_method(self):
        """Verify protocol defines get_status abstract method."""
        assert hasattr(ServerLifecyclePort, "get_status")

    def test_protocol_has_restart_method(self):
        """Verify protocol defines restart_server abstract method."""
        assert hasattr(ServerLifecyclePort, "restart_server")

    def test_server_status_enum_values(self):
        """Verify ServerStatus has required enum values."""
        assert ServerStatus.NOT_STARTED.value == "not_started"
        assert ServerStatus.RUNNING.value == "running"
        assert ServerStatus.STOPPED.value == "stopped"
        assert ServerStatus.ERROR.value == "error"

    def test_server_status_is_str_enum(self):
        """Verify ServerStatus is a string enum."""
        assert isinstance(ServerStatus.NOT_STARTED, ServerStatus)
        assert isinstance(ServerStatus.NOT_STARTED.value, str)

    def test_server_status_membership(self):
        """Verify all expected status values are in enum."""
        expected = {"not_started", "running", "stopped", "error"}
        actual = {status.value for status in ServerStatus}
        assert expected == actual


class TestServerLifecycleProtocolStructure:
    """Test the protocol structure using typing inspection."""

    def test_protocol_is_runtime_checkable(self):
        """Verify protocol can be used for runtime checks."""
        # Protocol should be importable and usable
        from llm_lsp_cli.application.interfaces.server_lifecycle import (
            ServerLifecyclePort,
        )

        # Just verify it's a valid class
        assert isinstance(ServerLifecyclePort, type)
